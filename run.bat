@echo off
setlocal
chcp 65001 >nul

set "SCRIPT_DIR=%~dp0"
set "PS_SCRIPT=%SCRIPT_DIR%launchers\run_windows.ps1"

if not exist "%PS_SCRIPT%" (
    echo [ERROR] No se encontro el archivo / Script not found: %PS_SCRIPT%
    pause
    exit /b 1
)

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%PS_SCRIPT%" %*
set "EXIT_CODE=%ERRORLEVEL%"

if %EXIT_CODE% neq 0 (
    echo.
    echo [!] Presione cualquier tecla para salir / Press any key to exit...
    pause >nul
)

exit /b %EXIT_CODE%
