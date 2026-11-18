@echo off
setlocal
cd /d "%~dp0"
if not exist "%LOCALAPPDATA%\NotebookConexion\1.3.0\.venv\Scripts\python.exe" (
  echo No se ha instalado Notebook Conexion. Primero ejecute INSTALAR_WINDOWS.cmd
  pause
  exit /b 1
)
"%LOCALAPPDATA%\NotebookConexion\1.3.0\.venv\Scripts\python.exe" -m notebook_conexion.desktop
if errorlevel 1 (
  echo Revise su instalacion. Ejecute DIAGNOSTICO_WINDOWS.cmd
  pause
)
