#!/bin/bash

# Create virtual environment (if it doesn't exist)
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "Virtual environment created"
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

echo "Backend dependencies installed!"
echo "Please update the .env file with your GitHub token and repository information"
echo "Then run: python3 main.py"
