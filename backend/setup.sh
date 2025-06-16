#!/bin/bash

# Virtual environment 생성 (없으면)
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "Virtual environment created"
fi

# Virtual environment 활성화
source venv/bin/activate

# 의존성 설치
pip install -r requirements.txt

echo "Backend dependencies installed!"
echo "Please update the .env file with your GitHub token and repository information"
echo "Then run: python3 main.py"
