#!/bin/bash
# Multi-Platform Claude Code Launcher - Bash Wrapper  
# Calls the unified Python launcher

set -e

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
LAUNCHER="$SCRIPT_DIR/launcher.py"

# Check if Python is available
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    echo "❌ Python not found. Please install Python 3.7+ first."
    exit 1
fi

PYTHON_CMD="python3"
if ! command -v python3 &> /dev/null; then
    PYTHON_CMD="python"
fi

# Check if launcher exists
if [[ ! -f "$LAUNCHER" ]]; then
    echo "❌ Launcher script not found: $LAUNCHER"
    exit 1
fi

# Capture real current directory and set environment variables
export LAUNCHER_REAL_CWD="$(pwd)"
export LAUNCHER_SCRIPT_DIR="$SCRIPT_DIR"

# Pass all arguments to the Python launcher
exec $PYTHON_CMD "$LAUNCHER" "$@"