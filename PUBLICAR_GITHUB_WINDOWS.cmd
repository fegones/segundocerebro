@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
echo =======================================================
echo  SEGUNDO CEREBRO: PUBLICACION GITHUB
echo  Destino: https://github.com/fegones/segundocerebro
echo  Visibilidad: PUBLICO - contenido visible para todos
echo =======================================================
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\publicar_github_windows.ps1"
if errorlevel 1 (
  echo.
  echo No se completo la publicacion. Revise docs\PUBLICACION_GITHUB.md.
)
echo.
pause
