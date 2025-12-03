@echo off
REM Script para iniciar el Organizador de Escritorio
REM Usado para el inicio automático de Windows

cd /d "%~dp0"

REM Prioridad 1: Ejecutable .exe
if exist "dist\Organizador Escritorio.exe" (
    start "" "dist\Organizador Escritorio.exe"
    exit /b 0
)

REM Prioridad 2: Python
where python >nul 2>&1
if %ERRORLEVEL% == 0 (
    python organizador_escritorio.py
    exit /b %ERRORLEVEL%
)

REM Prioridad 3: Python Launcher
where py >nul 2>&1
if %ERRORLEVEL% == 0 (
    py organizador_escritorio.py
    exit /b %ERRORLEVEL%
)

REM Error: Python no encontrado
echo ERROR: Python no se encuentra instalado o no está en el PATH.
pause

