@echo off
title Servidor de Inventario HW/SW (TCP)
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
echo   Iniciando Servidor de Consultas de Inventario (Puerto 5051)...
echo   No cierres esta ventana mientras el servidor este en uso.
echo.
"%PY_CMD%" "%~dp0servidor_inventario.py"
echo.
echo   El servidor se detuvo.
pause
