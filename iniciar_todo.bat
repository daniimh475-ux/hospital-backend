@echo off
REM Script para arrancar backend y app de escritorio juntos
REM Hospital - Entrega portable

cd /d %~dp0

REM Activar entorno virtual
call .venv\Scripts\activate.bat

REM Instalar dependencias si es necesario
pip install --upgrade pip
if exist backend\requirements.txt (
    pip install -r backend\requirements.txt
)



REM =============================================
REM  NO INICIAR BACKEND LOCAL EN PRODUCCIÓN
REM  El EXE/Tkinter usa:
REM  https://hospital-backend-o0on.onrender.com
REM =============================================

REM Si necesitas backend local, descomenta:
REM for /f "tokens=2" %%a in ('tasklist ^| findstr /i "uvicorn.exe"') do taskkill /PID %%a /F
REM start "Backend" cmd /c "uvicorn backend.main:app --port 8001"

REM Esperar 5 segundos para que el backend arranque
ping 127.0.0.1 -n 6 > nul


REM Generar el EXE de la app de escritorio (Tkinter)
REM Puedes comentar esta sección si ya tienes el EXE actualizado
if exist desktop_app\main.py (
    echo Generando EXE con PyInstaller...
    pyinstaller --noconfirm --onefile --windowed desktop_app\main.py
) else (
    echo ERROR: No se encontró desktop_app\main.py
    pause
    exit /b 1
)

REM Ejecutar la app de escritorio (main.exe)
if exist dist\main.exe (
    start /wait dist\main.exe
) else (
    echo ERROR: No se encontró dist\main.exe
    pause
    exit /b 1
)

REM Al cerrar main.exe, cerrar el backend
for /f "tokens=2" %%a in ('tasklist ^| findstr /i "uvicorn.exe"') do taskkill /PID %%a /F

exit /b 0
