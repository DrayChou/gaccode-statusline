#!/bin/bash
# Multi-Platform Claude Code Launcher - Bash Wrapper  
# Calls the unified Python launcher

set -e

# 用户可以在这里修改项目路径，默认为脚本的父目录（项目根目录）
PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
LAUNCHER="$PROJECT_DIR/bin/launcher.py"

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

# Pure config-file architecture - no environment variables needed

# Pass all arguments to the Python launcher
exec $PYTHON_CMD "$LAUNCHER" "$@"