#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一日志系统 - 基于 update_usage.py 的模式
支持PowerShell, Shell Script, Python的统一日志记录
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

# 获取项目根目录
PROJECT_DIR = Path(__file__).parent.parent
LOGS_DIR = PROJECT_DIR / "data" / "logs"

# 确保日志目录存在
LOGS_DIR.mkdir(parents=True, exist_ok=True)


def get_log_file(component: str) -> Path:
    """获取组件专用的日志文件路径"""
    return LOGS_DIR / f"{component}.log"


def log_message(component: str, level: str, message: str, extra_data: dict = None):
    """
    统一日志记录函数

    Args:
        component: 组件名称 (launcher, platform-manager, statusline等)
        level: 日志级别 (INFO, ERROR, DEBUG, WARNING)
        message: 日志消息
        extra_data: 额外的结构化数据
    """
    timestamp = datetime.now().isoformat()
    log_file = get_log_file(component)

    # 构建日志条目
    log_entry = f"{timestamp} [{level}] {message}"

    if extra_data:
        log_entry += f" | Data: {json.dumps(extra_data, ensure_ascii=False)}"

    # 写入日志文件
    try:
        with open(log_file, "a", encoding="utf-8-sig") as f:
            f.write(log_entry + "\n")
    except Exception as e:
        # 备用输出到stderr
        print(f"Failed to write log: {e}", file=sys.stderr)


def log_script_execution(
    component: str, script_path: str, args: list = None, env_vars: dict = None
):
    """记录脚本执行信息"""
    extra_data = {
        "script_path": str(script_path),
        "args": args or [],
        "env_vars": env_vars or {},
        "cwd": os.getcwd(),
    }
    log_message(component, "INFO", "Script execution started", extra_data)


def log_error(component: str, error: Exception, context: str = None):
    """记录错误信息"""
    import traceback

    extra_data = {
        "error_type": type(error).__name__,
        "error_message": str(error),
        "traceback": traceback.format_exc(),
        "context": context,
    }
    log_message(component, "ERROR", f"Error occurred: {str(error)}", extra_data)


def log_platform_detection(
    session_id: str, detected_platform: str, confidence: float, method: str
):
    """记录平台检测信息"""
    extra_data = {
        "session_id": session_id,
        "detected_platform": detected_platform,
        "confidence": confidence,
        "detection_method": method,
    }
    log_message(
        "platform-manager",
        "INFO",
        f"Platform detected: {detected_platform}",
        extra_data,
    )


def log_launcher_execution(platform: str, session_id: str, command: str, status: str):
    """记录启动器执行信息"""
    extra_data = {
        "platform": platform,
        "session_id": session_id,
        "command": command,
        "status": status,
    }
    log_message("launcher", "INFO", f"Launcher execution: {status}", extra_data)


# PowerShell/Shell脚本接口
if __name__ == "__main__":
    """
    命令行接口，供PowerShell和Shell脚本调用
    用法: python logger.py <component> <level> <message> [extra_json]
    """
    if len(sys.argv) < 4:
        print("Usage: python logger.py <component> <level> <message> [extra_json]")
        sys.exit(1)

    component = sys.argv[1]
    level = sys.argv[2]
    message = sys.argv[3]
    extra_data = None

    if len(sys.argv) > 4:
        try:
            extra_data = json.loads(sys.argv[4])
        except json.JSONDecodeError:
            pass

    log_message(component, level, message, extra_data)
