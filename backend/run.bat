@echo off

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Run FastAPI development server
uvicorn main:app --reload --host 0.0.0.0 --port 8000