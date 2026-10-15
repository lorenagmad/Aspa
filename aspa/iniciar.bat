@echo off
rem Corrector de examenes - doble clic para arrancar (Windows)
cd /d "%~dp0"
if not exist .venv (
  echo Preparando el entorno por primera vez, puede tardar un par de minutos...
  py -3 -m venv .venv 2>nul || python -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install -q --disable-pip-version-check -r requirements.txt
python app.py %*
if errorlevel 1 pause
