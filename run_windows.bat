@echo off
cd /d "%~dp0"
if not exist venv\Scripts\python.exe python -m venv venv
call venv\Scripts\activate
pip install -r requirements.txt
python backend\seed.py
uvicorn backend.main:app --reload
pause
