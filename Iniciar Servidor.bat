@echo off
title Servidor de Chat
set "PY_CMD=python"
python -c "import sys" >nul 2>&1
if %errorlevel% neq 0 (
    if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
        set "PY_CMD=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    ) else if exist "%LOCALAPPDATA%\Programs\Python\Launcher\py.exe" (
        set "PY_CMD=%LOCALAPPDATA%\Programs\Python\Launcher\py.exe"
    )
)

echo.
echo   Iniciando servidor de chat...
echo   No cierres esta ventana mientras el chat este activo.
echo.
"%PY_CMD%" "%~dp0servidor.py"
echo.
echo   El servidor se detuvo.
pause

