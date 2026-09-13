@echo off
cd /d "%~dp0"
python app_profissional.py
if errorlevel 1 (
  echo.
  echo Nao foi possivel iniciar. Confirme se o Python esta instalado.
  pause
)
