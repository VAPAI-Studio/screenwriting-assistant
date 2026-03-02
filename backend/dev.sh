#!/bin/bash
# Backend development server startup script

# Activate virtual environment
source venv/bin/activate

# Read PORT from .env file or default to 8000
if [ -f .env ]; then
    PORT=$(grep -E "^PORT=" .env | cut -d '=' -f2)
fi
PORT=${PORT:-8000}

echo "Starting backend server on port $PORT..."
echo "API will be available at: http://localhost:$PORT/api"
echo "API docs will be available at: http://localhost:$PORT/docs"
echo ""

# Run uvicorn with the configured port
uvicorn app.main:app --reload --port "$PORT"
