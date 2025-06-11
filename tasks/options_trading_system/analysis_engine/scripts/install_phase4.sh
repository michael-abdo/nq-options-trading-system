#!/bin/bash
# Quick Phase 4 Dependency Installation Script
# This script helps install Phase 4 dependencies with proper error handling

set -e  # Exit on error

echo "=============================================="
echo "Phase 4 Dependency Installation"
echo "=============================================="
echo ""

# Check if we're in the right directory
if [ ! -f "requirements/phase4.txt" ]; then
    echo "❌ Error: requirements/phase4.txt not found!"
    echo "Please run this script from the analysis_engine directory."
    exit 1
fi

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check for Python
if ! command_exists python3; then
    echo "❌ Error: Python 3 is not installed!"
    echo "Please install Python 3.8 or higher."
    exit 1
fi

# Get Python version
PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "✅ Found Python $PYTHON_VERSION"

# Check for pip
if ! command_exists pip3; then
    echo "❌ Error: pip is not installed!"
    echo "Please install pip: python3 -m ensurepip"
    exit 1
fi

echo ""
echo "📦 Installation Options:"
echo "1) Phase 4 core dependencies only (recommended)"
echo "2) All optional dependencies (full features)"
echo "3) Development dependencies (for contributors)"
echo "4) Everything (core + optional + dev)"
echo "5) Check current dependencies status"
echo "6) Exit"
echo ""

read -p "Select an option (1-6): " choice

case $choice in
    1)
        echo ""
        echo "Installing Phase 4 core dependencies..."
        pip3 install -r requirements/phase4.txt
        echo ""
        echo "✅ Phase 4 core dependencies installed!"
        ;;
    2)
        echo ""
        echo "Installing all optional dependencies..."
        pip3 install -r requirements/optional.txt
        echo ""
        echo "✅ All optional dependencies installed!"
        ;;
    3)
        echo ""
        echo "Installing development dependencies..."
        if [ -f "requirements/dev.txt" ]; then
            pip3 install -r requirements/dev.txt
        else
            echo "Creating dev.txt first..."
            cat > requirements/dev.txt << 'EOF'
# Development Dependencies
pytest>=6.2.0
pytest-cov>=2.12.0
pytest-asyncio>=0.15.0
black>=21.6b0
mypy>=0.910
flake8>=3.9.0
isort>=5.9.0
pre-commit>=2.13.0
EOF
            pip3 install -r requirements/dev.txt
        fi
        echo ""
        echo "✅ Development dependencies installed!"
        ;;
    4)
        echo ""
        echo "Installing everything (core + optional + dev)..."
        pip3 install -r requirements/full.txt
        echo ""
        echo "✅ All dependencies installed!"
        ;;
    5)
        echo ""
        echo "Checking dependency status..."
        python3 scripts/check_dependencies.py
        ;;
    6)
        echo "Exiting..."
        exit 0
        ;;
    *)
        echo "Invalid option. Please select 1-6."
        exit 1
        ;;
esac

echo ""
echo "=============================================="
echo "Installation complete!"
echo ""
echo "Next steps:"
echo "1. Run 'python3 scripts/check_dependencies.py' to verify installation"
echo "2. Run tests to ensure everything works: python3 -m pytest tests/"
echo "3. Check the documentation: docs/FEATURE_MATRIX.md"
echo ""
echo "Remember: The system works perfectly without dependencies!"
echo "These packages only enhance functionality."
echo "=============================================="