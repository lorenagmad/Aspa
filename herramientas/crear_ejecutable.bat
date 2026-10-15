@echo off
rem Crea Aspa.exe (no necesita Python para ejecutarse). Resultado en la carpeta dist
cd /d "%~dp0\.."
if not exist .venv ( py -3 -m venv .venv 2>nul || python -m venv .venv )
call .venv\Scripts\activate.bat
python -m pip install -q --disable-pip-version-check -r requirements.txt pyinstaller
python herramientas\crear_ejecutable.py
pause
