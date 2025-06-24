#!/bin/bash

# Create virtual environment (if it doesn't exist)
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "Virtual environment created"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Create logs directory
if [ ! -d "logs" ]; then
    echo "Creating logs directory..."
    mkdir logs
fi

echo ""
echo "✅ Backend dependencies installed successfully!"
echo ""
echo "📝 Next steps:"
echo "1. Update the .env file with your GitHub token and repository information"
echo "2. Run the application with: python main.py"
echo "   Or use the development server: ./run.sh"
echo ""
echo "📚 API Documentation will be available at:"
echo "   - Swagger UI: http://localhost:8000/docs"
echo "   - ReDoc: http://localhost:8000/redoc"
echo "   - Health Check: http://localhost:8000/api/health"
