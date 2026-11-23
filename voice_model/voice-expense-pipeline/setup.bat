@echo off
REM One-time setup for Windows: create a virtual environment, install the core
REM requirements and run the offline smoke test.   Double-click or run: setup.bat
cd /d "%~dp0"
chcp 65001 >nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

where py >nul 2>nul
if %ERRORLEVEL%==0 (set PY=py -3) else (set PY=python)
%PY% --version

if not exist .venv (
  %PY% -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
  echo pip install failed. Check your internet connection and Python version ^(3.10-3.12^).
  exit /b 1
)

if not exist .env (
  copy .env.example .env >nul
  echo Created .env from .env.example
)

python scripts\smoke_test.py
echo.
echo Next steps:
echo   .venv\Scripts\activate
echo   pytest -q
echo   python -m voice_expense.cli text "I paid 80 pounds for coffee at Cilantro" --now 2026-11-20T14:00
