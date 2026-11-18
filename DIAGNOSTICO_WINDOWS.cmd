@echo off
setlocal
cd /d "%~dp0"
if not exist "%LOCALAPPDATA%\NotebookConexion\1.3.0\.venv\Scripts\python.exe" (
  echo No existe entorno virtual. Ejecute INSTALAR_WINDOWS.cmd
  pause
  exit /b 1
)
"%LOCALAPPDATA%\NotebookConexion\1.3.0\.venv\Scripts\python.exe" -m notebook_conexion.selftest
"%LOCALAPPDATA%\NotebookConexion\1.3.0\.venv\Scripts\python.exe" -m notebook_conexion.cli --version
pause
