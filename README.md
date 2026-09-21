# Chat cliente-servidor con sockets y SQLite

Chat básico en Python: un servidor TCP recibe mensajes de uno o varios clientes, los guarda en una base SQLite y responde con `Mensaje recibido: <timestamp>`.

Incluye, como extra opcional, una interfaz web hecha con Streamlit que usa el mismo servidor.

## Arquitectura

```
client.py ─────────TCP──┐
                        ├──>  server.py  ──>  chat.db (SQLite)
streamlit_app.py ──TCP──┘
       ▲
       └── HTTP ── navegador
```

La interfaz web no toca la base de datos ni tiene lógica de chat: es un cliente TCP más, igual que `client.py`.

## Estructura

```
.
├── src/
│   ├── server.py            # Servidor TCP + persistencia en SQLite
│   ├── client.py            # Cliente de consola
│   ├── config.py            # Host, puerto y nombre de la base
│   └── streamlit_app.py     # Interfaz web opcional
├── requirements.txt         # Dependencias (solo para la interfaz web)
└── README.md
```

## Requisitos

- Python 3.10 o superior

## Instalación

El servidor y el cliente de consola usan solo la librería estándar de Python, así que **no necesitan instalación**. Este paso es solo para la interfaz web (Streamlit).

1. Ubicate en la carpeta raíz del proyecto.

2. Creá un entorno virtual:

   ```bash
   python -m venv .venv
   ```

3. Activalo:

   Windows (PowerShell / CMD):

   ```bash
   .venv\Scripts\activate
   ```

   Linux / macOS:

   ```bash
   source .venv/bin/activate
   ```

4. Instalá las dependencias:

   ```bash
   pip install -r requirements.txt
   ```

Cuando termines, podés salir del entorno virtual con `deactivate`.

## Uso

Abrí una terminal por cada proceso, ubicada en la carpeta raíz del proyecto (no dentro de `src/`). Para la interfaz web, activá antes el entorno virtual.

**1. Servidor** (siempre primero):

```bash
python src/server.py
```

**2. Cliente de consola:**

```bash
python src/client.py
```

Escribí mensajes y presioná Enter. Para terminar la sesión, escribí `éxito`.

**3. Interfaz web (opcional):**

```bash
streamlit run src/streamlit_app.py
```

Se abre en http://localhost:8501. Si el servidor ya está corriendo (paso 1), la interfaz lo usa; si no, arranca uno propio dentro de la app.

## Configuración

Los valores están en `src/config.py`:

| Constante     | Valor       | Descripción                         |
| ------------- | ----------- | ----------------------------------- |
| `SERVER_HOST` | `localhost` | Dirección donde escucha el servidor |
| `SERVER_PORT` | `5000`      | Puerto del servidor TCP             |
| `DB_NAME`     | `chat.db`   | Archivo de la base SQLite           |

## Ver los mensajes guardados

```bash
python -c "import sqlite3; [print(r) for r in sqlite3.connect('chat.db').execute('SELECT * FROM mensajes')]"
```

Cada fila tiene: `id`, `contenido`, `fecha_envio`, `ip_cliente`.

## Problemas frecuentes

- **`No se pudo vincular al puerto 5000`**: hay otro proceso usando el puerto. Cerralo o cambiá `SERVER_PORT` en `src/config.py`. Si la interfaz web ya arrancó su propio servidor, cerrá Streamlit antes de iniciar `src/server.py`.
- **`No se pudo conectar al servidor`**: el servidor no está encendido. Iniciá `src/server.py` antes que el cliente.
- **`ModuleNotFoundError: streamlit`**: falta activar el entorno virtual o instalar `requirements.txt`.

## Notas

- En la interfaz web, todos los mensajes se guardan con `ip_cliente = 127.0.0.1`, porque el servidor ve la conexión de la app y no la del navegador.
- El servidor atiende cada cliente en un hilo propio, así que varias sesiones pueden estar abiertas a la vez.
- El archivo `chat.db` se crea en la carpeta desde la que ejecutás los comandos (la raíz del proyecto, si seguís los pasos).

## Despliegue en la nube (adicional)

Esta sección es opcional y no forma parte de la consigna. Sirve para tener un link público con la demo web.

**Cómo funciona.** [Streamlit Community Cloud](https://share.streamlit.io) despliega apps directamente desde un repositorio de GitHub. Ese servicio ejecuta solo el script de Streamlit y no expone puertos TCP, así que `streamlit_app.py` arranca `server.py` en un hilo dentro de la misma app y se conecta a `localhost`.

**Pasos**

1. Subí el proyecto a un repositorio de GitHub, con `requirements.txt` en la raíz y el código en `src/`.
2. Entrá a https://share.streamlit.io e iniciá sesión con tu cuenta de GitHub.
3. Hacé clic en **New app** (arriba a la derecha) y elegí el repositorio, la rama y el archivo principal: `src/streamlit_app.py`.
4. Opcional: elegí un subdominio propio (la app queda en `https://<nombre>.streamlit.app`) y, en las opciones avanzadas, la versión de Python. Usá la misma con la que lo probaste en local.
5. Hacé clic en **Deploy**. La primera vez tarda unos minutos porque instala `requirements.txt`. Después, cada `git push` a esa rama vuelve a desplegar la app.

**Cómo probar la demo**

1. Escribí un mensaje: el servidor responde `Mensaje recibido: <timestamp>`.
2. Escribí `éxito`: la app muestra el aviso de cierre de sesión.

**Limitaciones**

- La base SQLite es efímera: los mensajes se pierden cuando la app se reinicia o se duerme por inactividad. Sirve para una demo, no como persistencia real.
- Todos los visitantes comparten el mismo servidor y la misma base.
- `ip_cliente` es siempre `127.0.0.1`.
- Como servidor y cliente corren en la misma máquina, la arquitectura cliente-servidor por red solo se ve corriendo el TP en local, con `server.py` y `client.py` en terminales separadas.
- Los nombres de botones y opciones de la plataforma pueden cambiar. Ante dudas, consultá la documentación de Streamlit Community Cloud.
