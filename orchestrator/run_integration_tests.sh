#!/bin/bash
# Script to run the multi-agent integration tests

set -e  # Exit on error

# Display header
echo "====================================="
echo "  Multi-Agent Integration Test Suite"
echo "====================================="
echo ""

# Check for virtual environment
if [ -d "venv" ]; then
    echo "Using existing virtual environment..."
    source venv/bin/activate
else
    echo "Creating virtual environment..."
    python -m venv venv
    source venv/bin/activate
    echo "Installing dependencies..."
    pip install -r requirements.txt
fi

# Run the tests
echo ""
echo "Running integration tests..."
echo "-----------------------------------"
python -m pytest tests/ -v

# If a specific test is specified, run only that
if [ ! -z "$1" ]; then
    echo ""
    echo "Running specific test: $1"
    echo "-----------------------------------"
    python -m pytest "$1" -v
fi

echo ""
echo "====================================="
echo "  Test run complete"
echo "====================================="
