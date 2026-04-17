@echo off
REM Script para generar el ejecutable .exe de la app de escritorio

REM Cambiar a la carpeta del proyecto
cd /d %~dp0

REM Activar entorno virtual
call .venv\Scripts\activate.bat

REM Instalar PyInstaller si no está instalado
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo Instalando PyInstaller...
    pip install pyinstaller
)

REM Generar el ejecutable (sin consola)
pyinstaller --onefile --noconsole desktop_app\main.py

REM Mostrar ubicación del .exe generado
if exist dist\main.exe (
    echo Ejecutable creado: dist\main.exe
) else (
    echo ERROR: No se generó el ejecutable.
)

pause
