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

# Check if venv module is available
if ! python3 -m venv --help >/dev/null 2>&1; then
    echo "⚠️  venv module not found. Attempting to install..."
    echo ""

    # Try to install python3-venv (for Debian/Ubuntu systems)
    if command -v apt-get >/dev/null 2>&1; then
        echo "Installing python3-venv using apt-get..."
        sudo apt-get update
        sudo apt-get install -y python3-venv
    elif command -v yum >/dev/null 2>&1; then
        echo "Installing python3-venv using yum..."
        sudo yum install -y python3-venv
    elif command -v dnf >/dev/null 2>&1; then
        echo "Installing python3-venv using dnf..."
        sudo dnf install -y python3-venv
    else
        echo "❌ ERROR: Could not install venv automatically."
        echo "Please install python3-venv manually for your system."
        exit 1
    fi

    # Verify installation
    if ! python3 -m venv --help >/dev/null 2>&1; then
        echo "❌ ERROR: venv installation failed!"
        exit 1
    fi

    echo "✅ venv module installed successfully"
    echo ""
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv

    if [ $? -ne 0 ]; then
        echo "❌ ERROR: Failed to create virtual environment!"
        exit 1
    fi

    echo "✅ Virtual environment created"
    echo ""
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Check if Flask is installed
if ! python -c "import flask" 2>/dev/null; then
    echo "📦 Flask not found. Installing Flask..."
    echo ""
    pip install flask

    if [ $? -ne 0 ]; then
        echo "❌ ERROR: Failed to install Flask!"
        exit 1
    fi

    echo ""
    echo "✅ Flask installed successfully"
    echo ""
fi

echo "✅ Virtual environment activated"
echo ""

# Check if app.py exists
if [ ! -f "app.py" ]; then
    echo "❌ ERROR: app.py not found in $SCRIPT_DIR"
    exit 1
fi

# Kill any processes using ports 5000 and 8001-8020
echo "🔍 Checking for processes using ports 5000 and 8001-8020..."
echo ""

# Function to kill process on a specific port
kill_port() {
    local port=$1
    local pid=$(lsof -ti:$port 2>/dev/null)
    if [ ! -z "$pid" ]; then
        echo "  Killing process $pid on port $port"
        kill -9 $pid 2>/dev/null
        sleep 0.1
    fi
}

# Kill Flask port
kill_port 5000

# Kill XKOP ports (8001-8020)
for port in {8001..8020}; do
    kill_port $port
done

echo ""
echo "✅ Ports cleared"
echo ""

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
