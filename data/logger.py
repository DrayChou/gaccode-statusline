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

import re
from pathlib import Path

# 获取项目根目录
PROJECT_DIR = Path(__file__).parent.parent
LOGS_DIR = PROJECT_DIR / "data" / "logs"

# 确保日志目录存在
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# 安全配置
MAX_COMPONENT_LENGTH = 50
ALLOWED_COMPONENT_CHARS = re.compile(r'^[a-zA-Z0-9_-]+$')


def get_log_file(component: str) -> Path:
    """获取组件专用的日志文件路径（带安全验证）"""
    # 安全验证：防止路径遍历攻击
    if not component or len(component) > MAX_COMPONENT_LENGTH:
        raise ValueError(f"Invalid component name: {component}")
    
    if not ALLOWED_COMPONENT_CHARS.match(component):
        raise ValueError(f"Component name contains invalid characters: {component}")
    
    # 防止目录遍历
    safe_component = os.path.basename(component)
    return LOGS_DIR / f"{safe_component}.log"


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

    # 安全掩码敏感信息
    safe_message = mask_sensitive_data(message)
    safe_extra_data = mask_sensitive_dict(extra_data or {})

    # 构建日志条目
    log_entry = f"{timestamp} [{level}] {safe_message}"

    if safe_extra_data:
        log_entry += f" | Data: {json.dumps(safe_extra_data, ensure_ascii=False)}"

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


def mask_sensitive_data(text: str) -> str:
    """屏蔽文本中的敏感信息 - 增强版"""
    if not isinstance(text, str):
        return text
        
    patterns = [
        # API Keys - Various formats
        (r'sk-[a-zA-Z0-9\-_]{20,100}', lambda m: f"sk-***{m.group()[-4:]}"),
        (r'api[_-]?key["\']?\s*[:=]\s*["\']([^"\']\S{15,})["\']', lambda m: f"api_key=\"***{m.group(1)[-4:]}\""),
        
        # Bearer Tokens
        (r'Bearer [a-zA-Z0-9+/=_-]{20,}', lambda m: f"Bearer ***{m.group().split()[-1][-4:]}"),
        (r'Authorization:\s*Bearer\s+([a-zA-Z0-9+/=_-]{20,})', lambda m: f"Authorization: Bearer ***{m.group(1)[-4:]}"),
        
        # JWT Tokens (starts with eyJ)
        (r'eyJ[a-zA-Z0-9+/=_-]{20,}', lambda m: f"jwt-***{m.group()[-8:]}"),
        
        # OpenAI style keys
        (r'sk-proj-[a-zA-Z0-9_-]{20,100}', lambda m: f"sk-proj-***{m.group()[-6:]}"),
        
        # Anthropic API keys
        (r'sk-ant-[a-zA-Z0-9_-]{20,100}', lambda m: f"sk-ant-***{m.group()[-6:]}"),
        
        # DeepSeek API keys
        (r'sk-[a-fA-F0-9]{32}', lambda m: f"sk-***{m.group()[-6:]}"),
        
        # Generic long tokens (be more specific to avoid false positives)
        (r'[a-zA-Z0-9+/=_-]{40,}(?=\s|$|[,;\}\]\)])', 
         lambda m: f"***{m.group()[-6:]}" if len(m.group()) > 40 else "***"),
        
        # Authorization headers  
        (r'(auth[a-z]*[_-]?token|access[_-]?token|refresh[_-]?token)["\']?\s*[:=]\s*["\']([^"\']\S{15,})["\']',
         lambda m: f"{m.group(1)}=\"***{m.group(2)[-4:]}\""),
        
        # Login tokens
        (r'login[_-]?token["\']?\s*[:=]\s*["\']([^"\']\S{15,})["\']',
         lambda m: f"login_token=\"***{m.group(1)[-4:]}\""),
        
        # Session IDs (UUIDs)
        (r'session[_-]?id["\']?\s*[:=]\s*["\']?([a-fA-F0-9-]{32,36})["\']?',
         lambda m: f"session_id=\"{m.group(1)[:8]}-***-{m.group(1)[-4:]}\""),
        
        # Credit card patterns
        (r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b', '****-****-****-****'),
        
        # Email addresses (partial masking)
        (r'([a-zA-Z0-9._%+-]+)@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', 
         lambda m: f"{m.group(1)[:2]}***@{m.group(2)}"),
        
        # Phone numbers
        (r'\b\+?[1-9]\d{1,14}\b', lambda m: f"***{m.group()[-4:]}"),
        
        # IP Addresses (partial masking for privacy)
        (r'\b(?:\d{1,3}\.){3}\d{1,3}\b', lambda m: f"{'.'.join(m.group().split('.')[:2])}.***.**"),
        
        # URLs with credentials
        (r'https?://([^:]+):([^@]+)@', lambda m: f"https://{m.group(1)[:3]}***:***@"),
        
        # Database connection strings
        (r'(password|pwd)[=:]([^;\s&"\']\S+)', lambda m: f"{m.group(1)}=***{m.group(2)[-2:]}"),
    ]
    
    result = text
    for pattern, replacement in patterns:
        try:
            if callable(replacement):
                result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
            else:
                result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        except Exception as e:
            # If regex fails, continue with other patterns
            continue
    
    return result


def mask_sensitive_dict(data: dict) -> dict:
    """屏蔽字典中的敏感信息 - 增强版"""
    if not isinstance(data, dict):
        return data
    
    # 扩展的敏感键名列表
    sensitive_keys = {
        'api_key', 'auth_token', 'login_token', 'password', 'secret', 'passwd',
        'private_key', 'access_token', 'refresh_token', 'client_secret',
        'api_secret', 'webhook_secret', 'encryption_key', 'session_token',
        'bearer_token', 'oauth_token', 'jwt_token', 'auth_key', 'token',
        'key', 'credential', 'credentials', 'auth', 'authentication',
        'session_id', 'user_id', 'client_id', 'app_secret', 'app_key',
        'database_url', 'db_password', 'db_pass', 'redis_url', 'mongo_url'
    }
    
    # 敏感值模式（用于检测看起来像密钥的值）
    sensitive_value_patterns = [
        r'^sk-[a-zA-Z0-9\-_]{20,}$',  # OpenAI style keys
        r'^eyJ[a-zA-Z0-9+/=_-]{20,}$',  # JWT tokens
        r'^[a-fA-F0-9]{32,64}$',  # Hex keys
        r'^[a-zA-Z0-9+/=]{32,}$',  # Base64-like keys
    ]
    
    def is_sensitive_value(value: str) -> bool:
        """检查值是否看起来像敏感信息"""
        if not isinstance(value, str) or len(value) < 15:
            return False
        
        for pattern in sensitive_value_patterns:
            if re.match(pattern, value):
                return True
        return False
    
    def mask_value(value, key_name: str = ""):
        """智能掩码值"""
        if isinstance(value, str):
            if len(value) > 4:
                if len(value) > 20:  # Long strings get more masking
                    return f"***{value[-4:]}"
                else:
                    return f"***{value[-2:]}"
            else:
                return "***"
        else:
            return "***"
    
    def process_value(key: str, value, depth: int = 0):
        """递归处理值"""
        # 防止无限递归
        if depth > 10:
            return value
        
        if isinstance(value, dict):
            return mask_sensitive_dict_recursive(value, depth + 1)
        elif isinstance(value, list):
            return [process_value(f"{key}[{i}]", item, depth + 1) for i, item in enumerate(value)]
        elif isinstance(value, str):
            # 总是对字符串应用文本掩码
            masked_text = mask_sensitive_data(value)
            return masked_text
        else:
            return value
    
    def mask_sensitive_dict_recursive(data: dict, depth: int = 0) -> dict:
        """递归掩码字典"""
        masked = {}
        
        for key, value in data.items():
            key_lower = key.lower()
            
            # 检查键名是否敏感
            is_key_sensitive = any(sensitive in key_lower for sensitive in sensitive_keys)
            
            # 检查值是否看起来敏感
            is_value_sensitive = isinstance(value, str) and is_sensitive_value(value)
            
            if is_key_sensitive or is_value_sensitive:
                masked[key] = mask_value(value, key)
            else:
                masked[key] = process_value(key, value, depth)
        
        return masked
    
    return mask_sensitive_dict_recursive(data)


def clean_log_file(log_file_path: str) -> bool:
    """清理日志文件中的敏感信息"""
    try:
        log_file = Path(log_file_path)
        if not log_file.exists():
            return False
        
        # 创建备份
        backup_file = log_file.with_suffix(f"{log_file.suffix}.backup")
        import shutil
        shutil.copy2(log_file, backup_file)
        
        # 读取并清理内容
        with open(log_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        cleaned_content = mask_sensitive_data(content)
        
        # 写回清理后的内容
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write(cleaned_content)
        
        log_message("logger", "INFO", f"Cleaned log file: {log_file}")
        return True
        
    except Exception as e:
        print(f"Failed to clean log file {log_file_path}: {e}", file=sys.stderr)
        return False


def clean_all_log_files() -> int:
    """清理所有日志文件中的敏感信息"""
    cleaned_count = 0
    
    for log_file in LOGS_DIR.glob("*.log"):
        if clean_log_file(str(log_file)):
            cleaned_count += 1
    
    log_message("logger", "INFO", f"Cleaned {cleaned_count} log files")
    return cleaned_count


# PowerShell/Shell脚本接口
if __name__ == "__main__":
    """
    命令行接口，供PowerShell和Shell脚本调用
    用法: 
        python logger.py <component> <level> <message> [extra_json]
        python logger.py --clean-logs  # 清理所有日志
        python logger.py --test-mask   # 测试掩码功能
    """
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python logger.py <component> <level> <message> [extra_json]")
        print("  python logger.py --clean-logs")
        print("  python logger.py --test-mask")
        sys.exit(1)
    
    # 特殊命令
    if sys.argv[1] == "--clean-logs":
        count = clean_all_log_files()
        print(f"Cleaned {count} log files")
        sys.exit(0)
    
    if sys.argv[1] == "--test-mask":
        test_data = {
            "api_key": "sk-1234567890abcdef1234567890abcdef",
            "auth_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test",
            "session_id": "550e8400-e29b-41d4-a716-446655440000",
            "email": "user@example.com",
            "password": "secret123"
        }
        
        print("Original:")
        print(json.dumps(test_data, indent=2))
        print("\nMasked:")
        print(json.dumps(mask_sensitive_dict(test_data), indent=2))
        sys.exit(0)
    
    # 常规日志记录
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
        except json.JSONDecodeError as e:
            print(f"Warning: Invalid JSON in extra_data: {e}", file=sys.stderr)
            extra_data = {"raw_data": sys.argv[4]}

    log_message(component, level, message, extra_data)
