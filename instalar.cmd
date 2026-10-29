@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  echo Instala Python 3.11 o posterior desde python.org, incluido el lanzador py.
  pause
  exit /b 1
)
py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)"
if errorlevel 1 (
  echo Se necesita Python 3.11 o posterior.
  pause
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" py -3 -m venv .venv
if errorlevel 1 goto fail
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto fail
echo Instalacion completada. Abre iniciar.cmd.
pause
exit /b 0
:fail
echo No se ha completado la instalacion. Revisa el mensaje anterior.
pause
exit /b 1
