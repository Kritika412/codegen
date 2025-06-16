#!/bin/bash

# Virtual environment 활성화
source venv/bin/activate

# FastAPI 개발 서버 실행
uvicorn main:app --reload --host 0.0.0.0 --port 8000
