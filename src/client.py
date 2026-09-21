"""Cliente de chat TCP: envía mensajes al servidor hasta que el usuario escribe 'éxito'."""

import socket
import sys

from config import SERVER_HOST, SERVER_PORT

EXIT_COMMANDS = ("éxito", "exito")
BUFFER_SIZE = 1024


def run_client(host: str = SERVER_HOST, port: int = SERVER_PORT) -> None:
    """Conecta al servidor y envía mensajes en bucle, mostrando cada respuesta."""
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        print(f"[CLIENTE] Conectando a {host}:{port}...")
        client_socket.connect((host, port))
        print("[CLIENTE] Conectado exitosamente. Escribe tus mensajes.")
        print("[INFO] Para salir y terminar la sesión, escribe 'éxito'.\n" + "-" * 50)

        while True:
            mensaje = input("Vos > ").strip()
            if not mensaje:
                continue

            client_socket.sendall(mensaje.encode("utf-8"))

            respuesta = client_socket.recv(BUFFER_SIZE).decode("utf-8")
            # Una respuesta vacía significa que el servidor cerró la conexión.
            if not respuesta:
                print("[CLIENTE] El servidor cerró la conexión.")
                break
            print(f"Servidor > {respuesta}")

            if mensaje.lower() in EXIT_COMMANDS:
                print("[CLIENTE] Sesión concluida. Cerrando conexión.")
                break

    except ConnectionRefusedError:
        print(f"[ERROR] No se pudo conectar al servidor en {host}:{port}. ¿Está encendido?", file=sys.stderr)
    except ConnectionResetError:
        print("[ERROR] El servidor cortó la conexión abruptamente.", file=sys.stderr)
    except KeyboardInterrupt:
        print("\n[CLIENTE] Cierre forzado por el usuario.")
    except Exception as e:
        print(f"[ERROR] Error inesperado en el cliente: {e}", file=sys.stderr)
    finally:
        client_socket.close()
        print("[CLIENTE] Socket cerrado.")


if __name__ == "__main__":
    run_client()
