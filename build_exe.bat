@echo off
echo ========================================
echo Generando ejecutable .exe
echo ========================================
echo.

REM Verificar si PyInstaller está instalado
python -c "import PyInstaller" 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo PyInstaller no está instalado. Instalando...
    pip install pyinstaller
    if %ERRORLEVEL% NEQ 0 (
        echo ERROR: No se pudo instalar PyInstaller
        pause
        exit /b 1
    )
)

echo.
echo Limpiando compilaciones anteriores...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist "Organizador Escritorio.spec" del "Organizador Escritorio.spec"

echo.
echo Compilando aplicación...
echo.

REM Generar el ejecutable usando python -m PyInstaller
python -m PyInstaller --onefile ^
    --windowed ^
    --name "Organizador Escritorio" ^
    --clean ^
    organizador_escritorio.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: La compilación falló
    pause
    exit /b 1
)

echo.
echo ========================================
echo Compilación completada exitosamente!
echo ========================================
echo.
echo El ejecutable se encuentra en: dist\Organizador Escritorio.exe
echo.
pause

