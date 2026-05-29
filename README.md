# Organizador de Escritorio

Aplicación de escritorio para Windows que organiza los archivos del escritorio en "casillas" personalizables, con soporte opcional para clasificación con IA local (Ollama).

## Características

- Casillas flotantes y arrastrables sobre el escritorio.
- Drag & drop de archivos hacia las casillas.
- Detección de colisiones y snap para alinear casillas entre sí.
- Personalización de tamaño, colores e iconos.
- Análisis de la paleta del fondo de pantalla para sugerir colores que combinen.
- Clasificación automática de archivos con un modelo local vía Ollama.
- Persistencia del estado entre sesiones.

## Stack

- Python 3
- PyQt5 (interfaz)
- Ollama (clasificación con IA local, opcional)
- PyInstaller (empaquetado)

## Requisitos

- Windows
- Python 3.10+
- (Opcional) [Ollama](https://ollama.com/) corriendo localmente para la clasificación con IA.

## Instalación

```bash
pip install -r requirements.txt
```

## Uso

```bash
python organizador_escritorio.py
```

Para generar un ejecutable:

```bash
pyinstaller "Organizador Escritorio.spec"
```

## Estructura

- `organizador_escritorio.py` — punto de entrada, ventanas y lógica principal.
- `organizador_storage.py` — persistencia del estado.
- `organizador_ollama.py` — cliente para Ollama.
- `organizador_utils.py` — utilidades (escritorio, wallpaper, paleta de colores, iconos).
