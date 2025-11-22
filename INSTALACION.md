# Guía de Instalación - Organizador de Escritorio

## Paso 1: Instalar Python

Si Python no está instalado en tu sistema, sigue estos pasos:

### Opción A: Instalación desde Microsoft Store (Recomendado)
1. Abre Microsoft Store
2. Busca "Python 3.12" o "Python 3.11"
3. Haz clic en "Obtener" o "Instalar"
4. Espera a que se complete la instalación

### Opción B: Instalación desde python.org
1. Ve a https://www.python.org/downloads/
2. Descarga la última versión de Python 3.x para Windows
3. Ejecuta el instalador
4. **IMPORTANTE**: Marca la casilla "Add Python to PATH" durante la instalación
5. Haz clic en "Install Now"

## Paso 2: Verificar la instalación

Abre PowerShell o CMD y ejecuta:
```bash
python --version
```

O si usas el launcher de Windows:
```bash
py --version
```

Deberías ver algo como: `Python 3.12.x`

## Paso 3: Instalar las dependencias

Una vez que Python esté instalado, ejecuta uno de estos comandos:

**Si `python` funciona:**
```bash
python -m pip install -r requirements.txt
```

**Si solo `py` funciona:**
```bash
py -m pip install -r requirements.txt
```

**Si ninguno funciona, prueba con la ruta completa:**
```bash
C:\Users\[TuUsuario]\AppData\Local\Programs\Python\Python3XX\python.exe -m pip install -r requirements.txt
```

## Paso 4: Ejecutar la aplicación

Una vez instaladas las dependencias:

**Con `python`:**
```bash
python organizador_escritorio.py
```

**Con `py`:**
```bash
py organizador_escritorio.py
```

## Solución de problemas

### Error: "pip no se reconoce"
- Asegúrate de que Python esté instalado
- Usa `python -m pip` en lugar de solo `pip`
- Verifica que Python esté en el PATH del sistema

### Error: "No module named 'PyQt5'"
- Ejecuta: `python -m pip install PyQt5`
- O: `py -m pip install PyQt5`

### La ventana no aparece
- Verifica que no haya errores en la consola
- Asegúrate de que tu sistema tenga soporte para ventanas transparentes
- Intenta ejecutar como administrador

## Nota importante

Si tienes problemas con la instalación, puedes usar Python desde la Microsoft Store que se instala automáticamente y se agrega al PATH.


