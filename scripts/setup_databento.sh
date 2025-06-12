#!/bin/bash
# Setup script for Databento API testing

echo "=== Databento Setup Script ==="

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install requirements
echo "Installing dependencies..."
pip install -r requirements_databento.txt

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "ERROR: .env file not found. Please create it with your API key."
    echo "Example: echo 'DATABENTO_API_KEY=your-key-here' > .env"
    exit 1
fi

# Run basic test
echo -e "\n=== Running basic connection test ==="
python tests/test_databento_api.py

echo -e "\n=== Setup complete! ==="
echo "To run comprehensive tests: source venv/bin/activate && python tests/test_databento_nq_options.py"
