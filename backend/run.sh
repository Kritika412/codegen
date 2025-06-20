#!/bin/bash

# Activate virtual environment
source venv/bin/activate

# Run FastAPI development server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
