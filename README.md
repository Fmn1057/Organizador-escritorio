# Organizador de Escritorio

Aplicación de escritorio para Windows que organiza los archivos del escritorio en **casillas flotantes** (carpetas con UI propia, arrastrables, colapsables y personalizables). Soporta drag & drop, snap entre casillas, paleta de colores derivada del fondo de pantalla y, opcionalmente, **comandos en lenguaje natural** vía un modelo local de Ollama.

## Requisitos

- **Windows 10 / 11**
- **Python 3.10** o superior
- (Opcional) **[Ollama](https://ollama.com/)** corriendo en `http://localhost:11434` con el modelo `llama3.2` descargado, si quieres usar comandos en lenguaje natural.

## Stack tecnológico

| Parte | Tecnología |
|--------|------------|
| **Interfaz** | **PyQt5** (`QWidget` frameless, drag & drop, `QListWidget`, `QFileIconProvider`). Las casillas son ventanas independientes, no hijas de un main window. |
| **Persistencia** | **JSON** en `Desktop/Organizador_Casillas/.posiciones.json`. Guarda posiciones, tamaños, colores, tipo de vista, estado expandido/colapsado y configuración del panel. |
| **Integración Windows** | `winreg` para leer la ruta real del escritorio y del wallpaper (`HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders` y `HKCU\Control Panel\Desktop`). `QFileIconProvider` para íconos del sistema. |
| **IA (opcional)** | **Ollama** local vía `urllib.request` (sin SDK externo). Prompt system define un esquema JSON estricto para acciones (`crear_casilla`, `mover_archivo`, `mover_tipo`, etc.). El cliente corre en un `QThread` (`OllamaWorker`) para no bloquear la UI. |
| **Empaquetado** | **PyInstaller** con `Organizador Escritorio.spec`. |

## Instalación y ejecución

```bash
pip install -r requirements.txt
python organizador_escritorio.py
```

Para generar un ejecutable autocontenido:

```bash
pyinstaller "Organizador Escritorio.spec"
```

El binario queda en `dist/Organizador Escritorio/`.

## Características principales

### Casillas

- Ventanas frameless con dos estados: **colapsado** (140x50 por defecto) y **expandido** (280x400).
- **Drag & drop** de archivos desde el explorador, otra casilla o el escritorio.
- **Snap / alineación**: cuando arrastras una casilla cerca de otra, se alinean automáticamente con una tolerancia de **10 px** (`SNAP_THRESHOLD`).
- **Detección de colisiones** al posicionar: si dos casillas ocuparían el mismo espacio, se reubican (hasta `MAX_COLLISION_ATTEMPTS = 50` intentos).
- **Dos vistas**: lista o cuadrícula, conmutables por menú contextual.
- **Tamaño de icono** configurable (16–64 px) con multiplicador de resolución (`DEFAULT_RESOLUTION_MULTIPLIER = 2.0`) para que se vean nítidos en pantallas HiDPI.
- **Velocidad de scroll** ajustable (porcentaje).
- **Redimensionado** desde cualquier esquina.

### Colores

- Lee el wallpaper actual desde el registro de Windows y extrae su paleta dominante con un análisis de colores (`analyze_image_colors`).
- Genera una paleta sugerida (`generate_color_palette`) para que las casillas combinen con el fondo del escritorio.
- Cada casilla puede tener un color personalizado vía `QColorDialog`.

### Comandos en lenguaje natural (opcional)

Si Ollama está corriendo y `llama3.2` instalado, puedes escribir cosas como:

- `crear casilla Juegos`
- `mover todos los rar del escritorio a Archivos Comprimidos`
- `renombrar casilla Trabajo a Proyectos`

El cliente envía el comando junto con un **contexto de las casillas actuales y los archivos del escritorio**, y el modelo responde con un JSON estricto que la app ejecuta. El prompt system es muy explícito sobre el esquema permitido (`crear_casilla`, `eliminar_casilla`, `renombrar_casilla`, `mover_archivo`, `mover_tipo`, `nada`).

Cómo dejar Ollama listo:

```bash
ollama serve
ollama pull llama3.2
```

Si Ollama no responde en `localhost:11434` (timeout de 3 s), la app sigue funcionando sin la pestaña de comandos.

## Estructura del proyecto

| Archivo | Función |
|---------|---------|
| `organizador_escritorio.py` | Punto de entrada. Define `CasillaVentana` y el panel principal. Constantes de UI (tamaños, snap, colisiones). |
| `organizador_storage.py` | `PersistenceManager`: lectura/escritura del JSON con posiciones, tamaños y configuraciones. Crea la carpeta base si no existe. |
| `organizador_ollama.py` | `OllamaClient` (cliente HTTP) + `OllamaWorker` (hilo Qt). Define el `SYSTEM_PROMPT` con el esquema de acciones. |
| `organizador_utils.py` | Utilidades: lectura del escritorio y wallpaper desde el registro, análisis de colores, generación de paleta, íconos, mover archivos con resolución de colisiones de nombre. |
| `requirements.txt` | `PyQt5==5.15.10`, `pyinstaller==6.3.0`. |
| `Organizador Escritorio.spec` | Configuración de PyInstaller. |

## Persistencia

El estado completo vive en:

```
%USERPROFILE%\Desktop\Organizador_Casillas\.posiciones.json
```

Esquema (resumido):

```json
{
  "casillas":        { "NombreCasilla": [x, y] },
  "tamanos":         { "NombreCasilla": [w, h] },
  "tamanos_iconos":  { "NombreCasilla": 24 },
  "tipos_vista":     { "NombreCasilla": "lista" },
  "estados":         { "NombreCasilla": "colapsado" },
  "configuraciones": { "NombreCasilla": { ... } },
  "colores":         { "NombreCasilla": "#3366cc" },
  "panel":           [x, y]
}
```

Cada cambio (mover, redimensionar, cambiar color) llama a `save()` inmediatamente, así que un cierre forzado no pierde estado.

## Decisiones de diseño

- **Casillas como ventanas independientes** (no hijas) — así pueden colocarse libremente sobre cualquier zona del escritorio sin depender de un contenedor.
- **JSON local en vez de SQLite** — el dataset es trivial (decenas de entradas), no hay concurrencia y un archivo legible facilita debugging.
- **Ollama local en vez de una API en la nube** — sin costo por token, sin enviar nombres de archivo/escritorio a servidores externos, funciona offline.
- **Cliente HTTP con `urllib`** en lugar de `requests` — evita una dependencia más en el ejecutable empaquetado.
- **Worker en `QThread`** — sin congelar la UI durante la inferencia del modelo.

## Limitaciones conocidas

- Solo Windows: usa `winreg` para escritorio y wallpaper.
- El análisis de la paleta del wallpaper falla silenciosamente si el wallpaper es un archivo que Qt no puede leer (algunos `.heic` antiguos).
- Sin tests automatizados.
