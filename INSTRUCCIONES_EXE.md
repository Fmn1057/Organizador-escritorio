# Instrucciones para Generar el Ejecutable .exe

## Paso 1: Instalar PyInstaller

Si aún no lo tienes instalado, ejecuta:

```bash
pip install pyinstaller
```

O simplemente ejecuta `build_exe.bat` que lo instalará automáticamente.

## Paso 2: Generar el Ejecutable

Ejecuta el archivo `build_exe.bat` desde la carpeta del proyecto.

Esto generará el archivo `Organizador Escritorio.exe` en la carpeta `dist\`.

## Paso 3: Configurar Inicio Automático

### Opción A: Usando el script proporcionado (Recomendado)

1. Primero genera el .exe siguiendo el Paso 2
2. Ejecuta `agregar_inicio.bat` para agregar la aplicación al inicio de Windows
3. Para remover del inicio, ejecuta `remover_inicio.bat`

### Opción B: Manualmente

1. Presiona `Win + R` y escribe: `shell:startup`
2. Esto abrirá la carpeta de inicio de Windows
3. Crea un acceso directo al archivo `Organizador Escritorio.exe` en esa carpeta

## Notas

- El ejecutable se genera en la carpeta `dist\`
- Puedes mover el .exe a cualquier ubicación, pero asegúrate de actualizar el acceso directo del inicio si lo mueves
- Si usas el script Python directamente (sin .exe), el script `agregar_inicio.bat` detectará automáticamente el script Python y lo usará

## Solución de Problemas

### El .exe no se genera
- Asegúrate de tener PyInstaller instalado: `pip install pyinstaller`
- Verifica que todas las dependencias estén instaladas: `pip install -r requirements.txt`

### La aplicación no inicia con Windows
- Verifica que el acceso directo esté en la carpeta de inicio
- Ejecuta `agregar_inicio.bat` nuevamente
- Verifica los permisos de la carpeta de inicio

### El .exe es muy grande
- Esto es normal, PyInstaller incluye Python y todas las dependencias
- El tamaño típico es de 50-100 MB aproximadamente

