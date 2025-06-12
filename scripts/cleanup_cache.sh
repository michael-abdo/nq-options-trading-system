#!/bin/bash
# Cleanup script for Python cache files
# Run this before deployment or when needed

echo "Python Cache Cleanup Script"
echo "=========================="

# Function to count files
count_files() {
    find . -name "*.pyc" -type f 2>/dev/null | wc -l
}

# Function to count directories
count_dirs() {
    find . -name "__pycache__" -type d 2>/dev/null | wc -l
}

echo "Current cache status:"
echo "  .pyc files: $(count_files)"
echo "  __pycache__ directories: $(count_dirs)"
echo ""

read -p "Do you want to clean Python cache files? (y/N) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Cleaning Python cache files..."

    # Remove .pyc files
    find . -name "*.pyc" -type f -delete 2>/dev/null

    # Remove __pycache__ directories
    find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null

    # Remove .pytest_cache directories
    find . -name ".pytest_cache" -type d -exec rm -rf {} + 2>/dev/null

    # Remove .mypy_cache directories
    find . -name ".mypy_cache" -type d -exec rm -rf {} + 2>/dev/null

    echo ""
    echo "Cleanup complete!"
    echo "  Remaining .pyc files: $(count_files)"
    echo "  Remaining __pycache__ directories: $(count_dirs)"
else
    echo "Cleanup cancelled."
fi

echo ""
echo "Note: Python will recreate cache files as needed."
