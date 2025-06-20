@echo off

REM Create virtual environment (if it doesn't exist)
if not exist "venv" (
    python -m venv venv
    echo Virtual environment created
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Install dependencies
pip install -r requirements.txt

echo Backend dependencies installed!
echo Please update the .env file with your GitHub token and repository information
echo Then run: python main.py

pause