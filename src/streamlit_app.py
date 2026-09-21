"""Interfaz web del chat con Streamlit.

Funciona como un cliente TCP más, igual que client.py: envía cada mensaje al
servidor por socket y muestra su respuesta. Si no hay un servidor escuchando,
arranca server.py en un hilo dentro de esta misma app (útil al desplegar).
"""

import socket
import threading
import time

import streamlit as st

import server
from config import SERVER_HOST, SERVER_PORT

BUFFER_SIZE = 1024
SOCKET_TIMEOUT_SECONDS = 5
STARTUP_TIMEOUT_SECONDS = 5
CONFIRMATION_PREFIX = "Mensaje recibido:"
# 250 caracteres ocupan como máximo 1000 bytes en UTF-8, dentro de los 1024 que lee el servidor.
MAX_MESSAGE_CHARS = 250


def server_is_up() -> bool:
    try:
        with socket.create_connection((SERVER_HOST, SERVER_PORT), timeout=1):
            return True
    except OSError:
        return False


@st.cache_resource
def ensure_server_running() -> None:
    """Arranca server.py en un hilo si no hay uno escuchando. Se ejecuta una sola vez por proceso."""
    if server_is_up():
        return

    threading.Thread(target=server.start_server, daemon=True).start()

    # Espera a que el servidor haga bind antes de aceptar el primer mensaje.
    deadline = time.monotonic() + STARTUP_TIMEOUT_SECONDS
    while not server_is_up() and time.monotonic() < deadline:
        time.sleep(0.2)


def send_to_chat_server(mensaje: str) -> str:
    """Abre una conexión TCP, envía el mensaje y devuelve la respuesta del servidor."""
    with socket.create_connection((SERVER_HOST, SERVER_PORT), timeout=SOCKET_TIMEOUT_SECONDS) as sock:
        sock.sendall(mensaje.encode("utf-8"))
        return sock.recv(BUFFER_SIZE).decode("utf-8")


def submit_message(mensaje: str) -> None:
    """Envía el mensaje al servidor y registra la respuesta en el historial de la sesión."""
    history = st.session_state.history
    history.append(("user", mensaje))

    try:
        respuesta = send_to_chat_server(mensaje)
    except OSError:
        history.append(("error", "No se pudo conectar con el servidor de chat."))
        return

    if respuesta.startswith(CONFIRMATION_PREFIX):
        history.append(("server", respuesta))
        if mensaje.lower() in server.EXIT_COMMANDS:
            history.append(("server", "Sesión finalizada. ¡Gracias por chatear!"))
    else:
        history.append(("error", respuesta or "El servidor no respondió."))


def render_message(kind: str, text: str) -> None:
    with st.chat_message("user" if kind == "user" else "assistant"):
        if kind == "error":
            st.error(text)
        else:
            # st.text muestra el contenido tal cual, sin interpretarlo como Markdown.
            st.text(text)


st.set_page_config(page_title="Chat TCP", page_icon="💬")
st.title("Chat TCP · SQLite")
st.caption("Cada mensaje viaja por un socket TCP al servidor, que lo guarda en SQLite.")
st.warning("Demo pública: no escribas datos personales ni sensibles. Los mensajes se guardan en la base del servidor.")

ensure_server_running()

if "history" not in st.session_state:
    st.session_state.history = []

# El input se procesa antes de dibujar el historial para que el mensaje nuevo aparezca en la misma pasada.
nuevo_mensaje = st.chat_input("Escribí tu mensaje...", max_chars=MAX_MESSAGE_CHARS)
if nuevo_mensaje and nuevo_mensaje.strip():
    submit_message(nuevo_mensaje.strip())    

for kind, text in st.session_state.history:
    render_message(kind, text)
