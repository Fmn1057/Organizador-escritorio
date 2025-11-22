@echo off
echo ========================================
echo Instalador del Organizador de Escritorio
echo ========================================
echo.

REM Intentar con python
where python >nul 2>&1
if %ERRORLEVEL% == 0 (
    echo Python encontrado. Instalando dependencias...
    python -m pip install -r requirements.txt
    if %ERRORLEVEL% == 0 (
        echo.
        echo ========================================
        echo Instalacion completada exitosamente!
        echo ========================================
        echo.
        echo Para ejecutar la aplicacion, usa:
        echo python organizador_escritorio.py
        pause
        exit /b 0
    )
)

REM Intentar con py launcher
where py >nul 2>&1
if %ERRORLEVEL% == 0 (
    echo Python launcher encontrado. Instalando dependencias...
    py -m pip install -r requirements.txt
    if %ERRORLEVEL% == 0 (
        echo.
        echo ========================================
        echo Instalacion completada exitosamente!
        echo ========================================
        echo.
        echo Para ejecutar la aplicacion, usa:
        echo py organizador_escritorio.py
        pause
        exit /b 0
    )
)

REM Si llegamos aqui, Python no esta instalado
echo.
echo ERROR: Python no se encuentra instalado o no esta en el PATH.
echo.
echo Por favor:
echo 1. Instala Python desde https://www.python.org/downloads/
echo 2. Asegurate de marcar "Add Python to PATH" durante la instalacion
echo 3. O instala Python desde Microsoft Store
echo.
echo Consulta INSTALACION.md para mas detalles.
echo.
pause


