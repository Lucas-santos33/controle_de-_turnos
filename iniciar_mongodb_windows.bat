@echo off
cd /d "%~dp0"
python -m pip install -r requirements.txt
python testar_mongodb.py
echo.
pause
python app_mongodb.py
