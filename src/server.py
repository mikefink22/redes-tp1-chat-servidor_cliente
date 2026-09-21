"""Servidor de chat TCP que guarda cada mensaje recibido en SQLite."""

import socket
import time
import sqlite3
import sys
import threading
from datetime import datetime
from collections import defaultdict, deque

from config import DB_NAME, SERVER_HOST, SERVER_PORT

EXIT_COMMANDS = ("éxito", "exito")
TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"
BUFFER_SIZE = 1024
ACCEPT_TIMEOUT_SECONDS = 1.0


def current_timestamp() -> str:
    return datetime.now().strftime(TIMESTAMP_FORMAT)


def init_database(db_path: str = DB_NAME) -> None:
    """Crea la base de datos y la tabla 'mensajes' si no existen."""
    try:
        with sqlite3.connect(db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS mensajes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    contenido TEXT NOT NULL,
                    fecha_envio TEXT NOT NULL,
                    ip_cliente TEXT NOT NULL
                )
            """)
        print(f"[BD] Base de datos '{db_path}' inicializada correctamente.")
    except sqlite3.Error as e:
        print(f"[ERROR BD] No se pudo acceder o inicializar la base de datos: {e}", file=sys.stderr)
        # Sin base de datos el servidor no puede cumplir su función, así que no tiene sentido seguir.
        sys.exit(1)


def save_message(contenido: str, ip_cliente: str, fecha_envio: str, db_path: str = DB_NAME) -> bool:
    """Guarda un mensaje en la base de datos. Devuelve False si falla el acceso."""
    try:
        # Cada llamada abre su propia conexión: SQLite no comparte conexiones entre hilos.
        with sqlite3.connect(db_path) as conn:
            # Los placeholders (?) evitan inyección SQL con contenido arbitrario del cliente.
            conn.execute(
                "INSERT INTO mensajes (contenido, fecha_envio, ip_cliente) VALUES (?, ?, ?)",
                (contenido, fecha_envio, ip_cliente),
            )
        print(f"[BD] Mensaje guardado (IP: {ip_cliente}, Fecha: {fecha_envio}): {contenido}")
        return True
    except sqlite3.Error as e:
        print(f"[ERROR BD] Error al guardar mensaje de {ip_cliente}: {e}", file=sys.stderr)
        return False


def setup_server_socket(host: str = SERVER_HOST, port: int = SERVER_PORT) -> socket.socket:
    """Crea el socket TCP/IP del servidor, lo enlaza a host:port y lo deja escuchando."""
    try:
        # AF_INET = IPv4, SOCK_STREAM = TCP (flujo de bytes confiable y ordenado).
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # SO_REUSEADDR permite reiniciar el servidor sin esperar a que el SO libere el puerto (TIME_WAIT).
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # Falla con OSError si el puerto ya está en uso.
        server_socket.bind((host, port))

        # El argumento es el máximo de conexiones pendientes en cola antes de rechazar nuevas.
        server_socket.listen(5)

        # Timeout corto para que accept() no bloquee indefinidamente y Ctrl+C se procese también en Windows.
        server_socket.settimeout(ACCEPT_TIMEOUT_SECONDS)

        print(f"[SERVIDOR] Escuchando en {host}:{port}...")
        return server_socket
    except OSError as e:
        print(f"[ERROR SOCKET] No se pudo vincular al puerto {port} (¿puerto ocupado?): {e}", file=sys.stderr)
        sys.exit(1)


def handle_client_connection(client_socket: socket.socket, client_address: tuple) -> None:
    """Recibe mensajes de un cliente, los guarda y responde con la hora de recepción."""
    ip_cliente, puerto_cliente = client_address
    print(f"[CONEXIÓN] Cliente conectado desde {ip_cliente}:{puerto_cliente}")

    try:
        while True:
            # recv devuelve b"" cuando el cliente cierra la conexión.
            data = client_socket.recv(BUFFER_SIZE)
            if not data:
                print(f"[DESCONECTADO] El cliente {ip_cliente} cerró la conexión.")
                break

            mensaje = data.decode("utf-8").strip()
            timestamp = current_timestamp()

            if mensaje == CLEAR_HISTORY_COMMAND:
                # Comando especial: no se guarda como mensaje, borra toda la tabla.
                if clear_all_messages():
                    respuesta = "Historial borrado correctamente"
                else:
                    respuesta = "Error: no se pudo borrar el historial"
            elif is_rate_limited(ip_cliente):
                respuesta = (
                    f"Error: límite de {RATE_LIMIT_MAX_MESSAGES} mensajes cada "
                    f"{RATE_LIMIT_WINDOW_SECONDS}s alcanzado, esperá un momento"
                )

            # Si falla el guardado se informa al cliente en lugar de confirmar una recepción falsa.
            elif save_message(mensaje, ip_cliente, timestamp):
                respuesta = f"Mensaje recibido: {timestamp}"
            else:
                respuesta = "Error: no se pudo guardar el mensaje"
            client_socket.sendall(respuesta.encode("utf-8"))

            if mensaje.lower() in EXIT_COMMANDS:
                break

    except ConnectionResetError:
        print(f"[ADVERTENCIA] Conexión abortada abruptamente por el cliente {ip_cliente}.")
    except Exception as e:
        print(f"[ERROR] Ocurrió un fallo con el cliente {ip_cliente}: {e}", file=sys.stderr)
    finally:
        client_socket.close()
        print(f"[SOCKET] Socket cerrado para cliente {ip_cliente}.")


def accept_connections(server_socket: socket.socket) -> None:
    """Acepta clientes en bucle y atiende a cada uno en su propio hilo."""
    while True:
        try:
            client_socket, client_address = server_socket.accept()
        except socket.timeout:
            continue

        # Un hilo por cliente evita que una sesión abierta bloquee a las demás.
        # daemon=True: los hilos no impiden que el proceso termine con Ctrl+C.
        threading.Thread(
            target=handle_client_connection,
            args=(client_socket, client_address),
            daemon=True,
        ).start()


def start_server() -> None:
    """Inicializa la base de datos y el socket, y atiende clientes hasta Ctrl+C."""
    init_database()
    server_socket = setup_server_socket()

    try:
        accept_connections(server_socket)
    except KeyboardInterrupt:
        print("\n[SERVIDOR] Deteniendo servidor (Ctrl+C)...")
    finally:
        server_socket.close()
        print("[SERVIDOR] Servidor apagado correctamente.")

RATE_LIMIT_MAX_MESSAGES = 5
RATE_LIMIT_WINDOW_SECONDS = 10

_rate_limit_lock = threading.Lock()
_message_timestamps: dict[str, deque] = defaultdict(deque)

def is_rate_limited(ip_cliente: str) -> bool:
    '''Limita a 5 mensajes cada 10 segundos por cliente. Devuelve True si el cliente debe ser bloqueado temporalmente.'''
    now = time.monotonic()
    with _rate_limit_lock:
        timestamps = _message_timestamps[ip_cliente]
        while timestamps and now - timestamps[0] > RATE_LIMIT_WINDOW_SECONDS:
            timestamps.popleft()
        if len(timestamps) >= RATE_LIMIT_MAX_MESSAGES:
            return True
        timestamps.append(now)
        return False

CLEAR_HISTORY_COMMAND = "!borrar_historial"

def clear_all_messages(db_path: str = DB_NAME) -> bool:
    with sqlite3.connect(db_path) as conn:
        conn.execute("DELETE FROM mensajes")
        conn.execute("DELETE FROM sqlite_sequence WHERE name = 'mensajes'")
    return True


if __name__ == "__main__":
    start_server()
