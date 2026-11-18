@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
echo ===========================================================
echo   Notebook Conexion 1.3.0 - Instalacion guiada
 echo   Sin permisos de administrador y sin PyYAML / FastMCP
 echo ===========================================================
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\instalar_windows.ps1"
if errorlevel 1 (
    echo.
    echo La instalacion no se completo. Lea docs\SOLUCION_PROBLEMAS.md.
)
echo.
pause
