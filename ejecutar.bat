@echo off
echo Iniciando Organizador de Escritorio...
echo.

REM Intentar con python
where python >nul 2>&1
if %ERRORLEVEL% == 0 (
    python organizador_escritorio.py
    exit /b %ERRORLEVEL%
)

REM Intentar con py launcher
where py >nul 2>&1
if %ERRORLEVEL% == 0 (
    py organizador_escritorio.py
    exit /b %ERRORLEVEL%
)

REM Si llegamos aqui, Python no esta instalado
echo.
echo ERROR: Python no se encuentra instalado o no esta en el PATH.
echo.
echo Por favor ejecuta primero: instalar.bat
echo O consulta INSTALACION.md para mas detalles.
echo.
pause


