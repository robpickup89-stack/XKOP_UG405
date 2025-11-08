#!/bin/bash
# XKOP Tool Startup Script
# Run this script each time to start the XKOP client application

echo "=========================================="
echo "XKOP Tool - Starting Application"
echo "=========================================="
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR" || exit 1

echo "Working directory: $SCRIPT_DIR"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ ERROR: Virtual environment not found!"
    echo ""
    echo "Please create the virtual environment first:"
    echo "  python3 -m venv venv"
    echo "  source venv/bin/activate"
    echo "  pip install flask"
    echo ""
    exit 1
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Check if Flask is installed
if ! python -c "import flask" 2>/dev/null; then
    echo "❌ ERROR: Flask is not installed in the virtual environment!"
    echo ""
    echo "Please install Flask:"
    echo "  source venv/bin/activate"
    echo "  pip install flask"
    echo ""
    exit 1
fi

echo "✅ Virtual environment activated"
echo ""

# Check if app.py exists
if [ ! -f "app.py" ]; then
    echo "❌ ERROR: app.py not found in $SCRIPT_DIR"
    exit 1
fi

# Display startup information
echo "=========================================="
echo "Starting XKOP Client Application..."
echo "=========================================="
echo ""
echo "Flask web interface will be available at:"
echo "  http://0.0.0.0:5000"
echo "  http://localhost:5000"
echo ""
echo "Press Ctrl+C to stop the application"
echo ""
echo "=========================================="
echo ""

# Run the application
python app.py
