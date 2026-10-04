@echo off
title Cliente de Chat
set "PY_CMD=python"
python -c "import sys" >nul 2>&1
if %errorlevel% neq 0 (
    if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
        set "PY_CMD=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    ) else if exist "%LOCALAPPDATA%\Programs\Python\Launcher\py.exe" (
        set "PY_CMD=%LOCALAPPDATA%\Programs\Python\Launcher\py.exe"
    )
)

"%PY_CMD%" "%~dp0cliente.py"
if %errorlevel% neq 0 (
    echo.
    echo   ERROR: No se pudo abrir el cliente.
    echo   Asegurate de tener Python instalado.
    echo   Descargalo en: https://www.python.org/downloads/
    echo.
    pause
)
