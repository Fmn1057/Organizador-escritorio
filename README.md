# Organizador de Escritorio

Una aplicación de escritorio con interfaz transparente que te permite organizar tus archivos en casillas visuales. Cada casilla corresponde a una carpeta en tu escritorio.

## Características

- ✅ Interfaz completamente transparente para ver el fondo de escritorio
- ✅ **Casillas independientes**: Cada casilla es una ventana separada que puedes mover libremente
- ✅ **Ver contenido**: Cada casilla muestra un contador de archivos y puede expandirse para ver la lista completa
- ✅ **Abrir archivos**: Haz doble clic en cualquier archivo de la lista para abrirlo
- ✅ Crear casillas personalizadas con nombres
- ✅ Cada casilla crea automáticamente una carpeta correspondiente
- ✅ Arrastrar y soltar archivos directamente a las casillas
- ✅ Los archivos se mueven automáticamente a la carpeta de la casilla
- ✅ Las posiciones de las casillas se guardan automáticamente
- ✅ Panel de control compacto y movible
- ✅ Todas las ventanas se mantienen sobre otras aplicaciones

## Instalación

### Requisito previo: Python

**Si Python NO está instalado:**
- Opción 1: Instala desde Microsoft Store (busca "Python 3.12")
- Opción 2: Descarga desde https://www.python.org/downloads/
  - **IMPORTANTE**: Marca "Add Python to PATH" durante la instalación

### Instalación rápida (Windows)

1. **Doble clic en `instalar.bat`** - Este script instalará automáticamente las dependencias

2. **Doble clic en `ejecutar.bat`** - Para iniciar la aplicación

### Instalación manual

1. Asegúrate de tener Python 3.7 o superior instalado

2. Instala las dependencias:
```bash
python -m pip install -r requirements.txt
```

O si usas el launcher de Windows:
```bash
py -m pip install -r requirements.txt
```

**Nota**: Si `pip` no funciona, usa `python -m pip` en su lugar.

Para más ayuda, consulta `INSTALACION.md`

## Uso

1. Ejecuta la aplicación:
```bash
python organizador_escritorio.py
```

2. **Panel de control:**
   - Aparecerá un panel compacto en la esquina superior izquierda
   - Puedes moverlo arrastrándolo desde cualquier parte
   - Úsalo para crear nuevas casillas

3. **Crear una casilla:**
   - Escribe un nombre en el campo de texto (ej: "Trabajo", "Juegos", "Documentos")
   - Haz clic en "Crear" o presiona Enter
   - Se creará una casilla independiente y una carpeta en `Desktop/Organizador_Casillas/`
   - La casilla aparecerá en una posición predeterminada

4. **Mover casillas:**
   - **Cada casilla es independiente** - puedes moverla libremente por el escritorio
   - Arrastra cualquier casilla desde cualquier parte (excepto los botones)
   - Las posiciones se guardan automáticamente

5. **Ver archivos en las casillas:**
   - Cada casilla muestra un contador de archivos (ej: "3 archivos")
   - Haz clic en el botón **▼** (expandir) para ver la lista completa de archivos
   - Haz clic en **▲** (colapsar) para ocultar la lista y hacer la casilla más pequeña
   - **Doble clic** en cualquier archivo de la lista para abrirlo

6. **Organizar archivos:**
   - Arrastra cualquier archivo desde el Explorador de Windows
   - Suéltalo sobre la casilla deseada
   - El archivo se moverá automáticamente a la carpeta correspondiente
   - La lista de archivos se actualiza automáticamente

7. **Eliminar una casilla:**
   - Haz clic en el botón "×" en la esquina superior derecha de la casilla
   - Confirma la eliminación
   - Nota: La carpeta no se elimina, solo la casilla visual

8. **Controles del panel:**
   - **Minimizar (_)**: Minimiza el panel de control
   - **Cerrar (×)**: Cierra toda la aplicación y guarda las posiciones

## Ubicación de las carpetas

Las carpetas se crean en:
```
C:\Users\[TuUsuario]\Desktop\Organizador_Casillas\[NombreCasilla]
```

## Notas

- La ventana se mantiene siempre visible sobre otras aplicaciones
- Puedes mover la ventana arrastrándola desde cualquier parte
- La interfaz es semi-transparente para que puedas ver tu escritorio
- Si intentas mover un archivo con el mismo nombre, se agregará un número al final

## Requisitos

- Python 3.7+
- PyQt5
- Windows 10/11 (probado en Windows 10)

