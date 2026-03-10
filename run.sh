#!/bin/bash
# OpenTree Git GUI Launcher for Linux/macOS
# Usage: ./run.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Try python3 first, then python
if command -v python3 &> /dev/null; then
    python3 -m opentree "$@"
elif command -v python &> /dev/null; then
    python -m opentree "$@"
else
    echo "Error: Python not found. Please install Python 3.11+"
    exit 1
fi
