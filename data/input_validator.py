#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Input Validation and Security Utilities
输入验证和安全工具 - 防止恶意输入和安全攻击

功能:
1. 路径遍历防护
2. 输入数据清理和验证
3. API密钥格式验证
4. URL安全性检查
5. JSON数据验证
6. 文件名安全性检查
"""

import os
import re
import json
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import ipaddress
import string

# Import logging
try:
    from .logger import log_message
except ImportError:
    from logger import log_message


class ValidationError(Exception):
    """验证错误"""
    pass


class SecurityViolationError(Exception):
    """安全违规错误"""
    pass


class InputValidator:
    """输入验证和安全工具类"""
    
    def __init__(self, project_root: Optional[Path] = None):
        """初始化验证器"""
        self.project_root = project_root or Path(__file__).parent.parent
        
        # 允许的路径前缀
        self.allowed_path_prefixes = [
            self.project_root,
            Path.home(),
            Path.cwd(),
            Path("/tmp") if os.name != "nt" else Path("C:/temp"),
            Path("C:/") if os.name == "nt" else Path("/")
        ]
        
        # 危险的路径模式
        self.dangerous_path_patterns = [
            r'\.\.',  # 目录遍历
            r'[/\\]\.',  # 隐藏文件
            r'\$\{[^}]*\}',  # 变量替换
            r'%[a-zA-Z0-9_]+%',  # Windows环境变量
            r'~[/\\]',  # 用户目录符号
            r'[<>|"*?]',  # Windows不允许的字符
        ]
        
        # 允许的文件扩展名
        self.allowed_extensions = {
            'config': {'.json', '.yaml', '.yml', '.toml', '.ini'},
            'data': {'.json', '.csv', '.txt', '.log'},
            'script': {'.py', '.sh', '.ps1', '.bat', '.cmd'},
            'executable': {'.exe', '.msi', '.deb', '.rpm', '.pkg'}
        }
        
        # API密钥模式
        self.api_key_patterns = {
            'openai': re.compile(r'^sk-[a-zA-Z0-9]{20,100}$'),
            'anthropic': re.compile(r'^sk-ant-[a-zA-Z0-9\-_]{20,100}$'),
            'deepseek': re.compile(r'^sk-[a-fA-F0-9]{32}$'),
            'generic': re.compile(r'^[a-zA-Z0-9\-_]{20,100}$'),
            'jwt': re.compile(r'^eyJ[a-zA-Z0-9+/=]+\.[a-zA-Z0-9+/=]+\.[a-zA-Z0-9+/=_-]*$')
        }
        
        # 安全的字符集
        self.safe_chars = {
            'filename': string.ascii_letters + string.digits + '.-_',
            'component_name': string.ascii_letters + string.digits + '-_',
            'platform_name': string.ascii_letters + string.digits + '_',
            'session_id': string.ascii_letters + string.digits + '-'
        }
    
    def validate_path_security(self, path: Union[str, Path], context: str = "path") -> Path:
        """验证路径安全性，防止路径遍历攻击"""
        if isinstance(path, str):
            path_obj = Path(path)
        else:
            path_obj = path
        
        path_str = str(path_obj)
        
        # 1. 检查危险模式
        for pattern in self.dangerous_path_patterns:
            if re.search(pattern, path_str):
                raise SecurityViolationError(
                    f"Dangerous path pattern detected in {context}: {pattern}"
                )
        
        # 2. 解析路径并检查遍历
        try:
            resolved_path = path_obj.resolve()
        except (OSError, ValueError) as e:
            raise ValidationError(f"Invalid path in {context}: {e}")
        
        # 3. 检查是否在允许的目录范围内
        is_allowed = False
        resolved_str = str(resolved_path)
        
        for allowed_prefix in self.allowed_path_prefixes:
            try:
                allowed_str = str(allowed_prefix.resolve())
                if resolved_str.startswith(allowed_str):
                    is_allowed = True
                    break
            except (OSError, ValueError):
                continue
        
        if not is_allowed:
            raise SecurityViolationError(
                f"Path outside allowed directories in {context}: {resolved_path}"
            )
        
        log_message("input-validator", "DEBUG", f"Path validation passed: {context}",
                   {"original": str(path), "resolved": str(resolved_path)})
        
        return resolved_path
    
    def validate_filename(self, filename: str, context: str = "filename") -> str:
        """验证文件名安全性"""
        if not filename or not filename.strip():
            raise ValidationError(f"Empty filename in {context}")
        
        filename = filename.strip()
        
        # 1. 检查长度
        if len(filename) > 255:
            raise ValidationError(f"Filename too long in {context}: {len(filename)} characters")
        
        # 2. 检查非法字符
        safe_chars = self.safe_chars['filename']
        for char in filename:
            if char not in safe_chars:
                raise ValidationError(
                    f"Unsafe character '{char}' in filename {context}: {filename}"
                )
        
        # 3. 检查保留名称（Windows）
        if os.name == "nt":
            reserved_names = {
                'CON', 'PRN', 'AUX', 'NUL',
                'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
                'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
            }
            base_name = filename.split('.')[0].upper()
            if base_name in reserved_names:
                raise ValidationError(
                    f"Reserved filename in {context}: {filename}"
                )
        
        # 4. 检查危险前缀
        dangerous_prefixes = ['.', '-', '_', '~']
        if any(filename.startswith(prefix) for prefix in dangerous_prefixes):
            log_message("input-validator", "WARNING", 
                      f"Potentially dangerous filename prefix in {context}: {filename}")
        
        return filename
    
    def validate_component_name(self, component: str) -> str:
        """验证组件名称（用于日志系统）"""
        if not component or not component.strip():
            raise ValidationError("Empty component name")
        
        component = component.strip()
        
        # 检查长度
        if len(component) > 50:
            raise ValidationError(f"Component name too long: {len(component)} characters")
        
        # 检查字符
        safe_chars = self.safe_chars['component_name']
        for char in component:
            if char not in safe_chars:
                raise ValidationError(
                    f"Invalid character '{char}' in component name: {component}"
                )
        
        return component
    
    def validate_platform_name(self, platform: str) -> str:
        """验证平台名称"""
        if not platform or not platform.strip():
            raise ValidationError("Empty platform name")
        
        platform = platform.strip().lower()
        
        # 检查长度
        if len(platform) > 30:
            raise ValidationError(f"Platform name too long: {len(platform)} characters")
        
        # 检查字符
        safe_chars = self.safe_chars['platform_name']
        for char in platform:
            if char not in safe_chars:
                raise ValidationError(
                    f"Invalid character '{char}' in platform name: {platform}"
                )
        
        # 检查知名平台
        known_platforms = {'gaccode', 'deepseek', 'kimi', 'siliconflow', 'local_proxy', 'openai', 'anthropic'}
        if platform not in known_platforms:
            log_message("input-validator", "WARNING", 
                      f"Unknown platform name: {platform}")
        
        return platform
    
    def validate_session_id(self, session_id: str) -> str:
        """验证Session ID格式"""
        if not session_id or not session_id.strip():
            raise ValidationError("Empty session ID")
        
        session_id = session_id.strip()
        
        # 检查长度
        if len(session_id) < 8 or len(session_id) > 100:
            raise ValidationError(f"Session ID length invalid: {len(session_id)} characters")
        
        # 检查UUID格式
        uuid_pattern = re.compile(r'^[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}$')
        if uuid_pattern.match(session_id):
            return session_id
        
        # 检查字符
        safe_chars = self.safe_chars['session_id']
        for char in session_id:
            if char not in safe_chars:
                raise ValidationError(
                    f"Invalid character '{char}' in session ID: {session_id}"
                )
        
        return session_id
    
    def validate_api_key(self, api_key: str, platform: str = "generic") -> Tuple[bool, str]:
        """验证API密钥格式"""
        if not api_key or not api_key.strip():
            return False, "API key is empty"
        
        api_key = api_key.strip()
        
        # 检查基本长度
        if len(api_key) < 10:
            return False, "API key too short"
        
        if len(api_key) > 500:
            return False, "API key too long"
        
        # 检查是否包含非法字符
        if re.search(r'[\s\n\r\t]', api_key):
            return False, "API key contains whitespace characters"
        
        # 平台特定验证
        if platform in self.api_key_patterns:
            pattern = self.api_key_patterns[platform]
            if not pattern.match(api_key):
                return False, f"API key format invalid for platform {platform}"
        
        # 检查常见的错误模式
        common_mistakes = [
            (r'^(Bearer\s+)', "API key should not include 'Bearer ' prefix"),
            (r'^(sk-\s+)', "API key should not have spaces after 'sk-'"),
            (r'["\']', "API key should not be quoted"),
            (r'^\$\{.*\}$', "API key appears to be an environment variable placeholder")
        ]
        
        for pattern, message in common_mistakes:
            if re.search(pattern, api_key):
                return False, message
        
        return True, "API key format is valid"
    
    def validate_url(self, url: str, context: str = "URL", allow_localhost: bool = True) -> str:
        """验证URL安全性"""
        if not url or not url.strip():
            raise ValidationError(f"Empty URL in {context}")
        
        url = url.strip()
        
        # 检查基本格式
        try:
            parsed = urllib.parse.urlparse(url)
        except Exception as e:
            raise ValidationError(f"Invalid URL format in {context}: {e}")
        
        # 检查协议
        allowed_schemes = {'http', 'https'}
        if parsed.scheme not in allowed_schemes:
            raise SecurityViolationError(
                f"Unsupported URL scheme in {context}: {parsed.scheme}"
            )
        
        # 检查主机名
        if not parsed.hostname:
            raise ValidationError(f"Missing hostname in {context}: {url}")
        
        hostname = parsed.hostname.lower()
        
        # 检查是否为内网IP（如果不允许localhost）
        if not allow_localhost:
            try:
                ip = ipaddress.ip_address(hostname)
                if ip.is_private or ip.is_loopback:
                    raise SecurityViolationError(
                        f"Private/loopback IP not allowed in {context}: {hostname}"
                    )
            except ipaddress.AddressValueError:
                # 不是IP地址，检查是否为localhost
                if hostname in ['localhost', '127.0.0.1', '0.0.0.0', '::1']:
                    raise SecurityViolationError(
                        f"Localhost not allowed in {context}: {hostname}"
                    )
        
        # 检查危险模式
        dangerous_patterns = [
            r'[<>"\']',  # HTML/JavaScript注入
            r'javascript:',  # JavaScript URL
            r'data:',  # Data URL
            r'file:',  # File URL
            r'ftp:',  # FTP URL
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                raise SecurityViolationError(
                    f"Dangerous URL pattern in {context}: {pattern}"
                )
        
        log_message("input-validator", "DEBUG", f"URL validation passed: {context}",
                   {"url": url, "hostname": hostname, "scheme": parsed.scheme})
        
        return url
    
    def validate_json_data(self, data: str, max_size: int = 1024*1024, context: str = "JSON data") -> Dict[str, Any]:
        """验证和解析JSON数据"""
        if not data or not data.strip():
            raise ValidationError(f"Empty JSON data in {context}")
        
        data = data.strip()
        
        # 检查大小
        if len(data) > max_size:
            raise ValidationError(f"JSON data too large in {context}: {len(data)} bytes")
        
        # 检查危险字符
        dangerous_patterns = [
            r'__[a-zA-Z_][a-zA-Z0-9_]*__',  # Python魔法方法
            r'\\[xuU][0-9a-fA-F]+',  # Unicode转义
            r'[\x00-\x1F\x7F-\x9F]',  # 控制字符
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, data):
                log_message("input-validator", "WARNING", 
                          f"Potentially dangerous pattern in JSON {context}: {pattern}")
        
        # 解析JSON
        try:
            parsed_data = json.loads(data)
        except json.JSONDecodeError as e:
            raise ValidationError(f"Invalid JSON format in {context}: {e}")
        
        # 递归检查数据结构
        self._validate_json_structure(parsed_data, context, depth=0)
        
        return parsed_data
    
    def _validate_json_structure(self, obj: Any, context: str, depth: int = 0, max_depth: int = 20):
        """递归验证JSON数据结构"""
        # 防止无限递归
        if depth > max_depth:
            raise ValidationError(f"JSON structure too deep in {context}: depth > {max_depth}")
        
        if isinstance(obj, dict):
            # 检查字典大小
            if len(obj) > 1000:
                raise ValidationError(f"JSON object too large in {context}: {len(obj)} keys")
            
            for key, value in obj.items():
                # 检查键名
                if not isinstance(key, str):
                    raise ValidationError(f"Non-string key in JSON {context}: {type(key)}")
                
                if len(key) > 100:
                    raise ValidationError(f"JSON key too long in {context}: {len(key)} characters")
                
                # 递归检查值
                self._validate_json_structure(value, f"{context}.{key}", depth + 1)
        
        elif isinstance(obj, list):
            # 检查数组大小
            if len(obj) > 10000:
                raise ValidationError(f"JSON array too large in {context}: {len(obj)} items")
            
            for i, item in enumerate(obj):
                self._validate_json_structure(item, f"{context}[{i}]", depth + 1)
        
        elif isinstance(obj, str):
            # 检查字符串长度
            if len(obj) > 10000:
                raise ValidationError(f"JSON string too long in {context}: {len(obj)} characters")
        
        elif isinstance(obj, (int, float)):
            # 检查数值范围
            if isinstance(obj, int) and abs(obj) > 10**15:
                raise ValidationError(f"JSON integer too large in {context}: {obj}")
        
        # bool, None 等类型不需要特别验证
    
    def sanitize_string(self, text: str, max_length: int = 1000, allow_unicode: bool = True) -> str:
        """清理和验证字符串输入"""
        if not isinstance(text, str):
            text = str(text)
        
        # 移除控制字符
        text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]', '', text)
        
        # 规范化空白字符
        text = re.sub(r'\s+', ' ', text).strip()
        
        # 检查长度
        if len(text) > max_length:
            text = text[:max_length]
            log_message("input-validator", "WARNING", 
                      f"String truncated to {max_length} characters")
        
        # 如果不允许Unicode，移除非-ASCII字符
        if not allow_unicode:
            text = re.sub(r'[^\x20-\x7E]', '', text)
        
        return text
    
    def validate_file_extension(self, filepath: Union[str, Path], 
                               allowed_category: str = "config") -> bool:
        """验证文件扩展名"""
        if isinstance(filepath, str):
            filepath = Path(filepath)
        
        extension = filepath.suffix.lower()
        
        if allowed_category not in self.allowed_extensions:
            raise ValidationError(f"Unknown file category: {allowed_category}")
        
        allowed = self.allowed_extensions[allowed_category]
        
        if extension not in allowed:
            raise ValidationError(
                f"File extension '{extension}' not allowed for category '{allowed_category}'. "
                f"Allowed: {', '.join(allowed)}"
            )
        
        return True
    
    def create_secure_temp_path(self, prefix: str = "gaccode", suffix: str = ".tmp") -> Path:
        """创建安全的临时文件路径"""
        import tempfile
        
        # 验证前缀和后缀
        prefix = self.sanitize_string(prefix, max_length=50, allow_unicode=False)
        suffix = self.sanitize_string(suffix, max_length=10, allow_unicode=False)
        
        # 创建临时文件
        temp_fd, temp_path = tempfile.mkstemp(prefix=prefix, suffix=suffix)
        os.close(temp_fd)  # 关闭文件描述符
        
        temp_path_obj = Path(temp_path)
        
        log_message("input-validator", "DEBUG", "Created secure temp path",
                   {"path": str(temp_path_obj)})
        
        return temp_path_obj


# 全局验证器实例
_input_validator = None

def get_input_validator(project_root: Optional[Path] = None) -> InputValidator:
    """获取输入验证器单例"""
    global _input_validator
    if _input_validator is None:
        _input_validator = InputValidator(project_root)
    return _input_validator


# 便捷函数
def validate_path(path: Union[str, Path], context: str = "path") -> Path:
    """验证路径安全性（便捷函数）"""
    return get_input_validator().validate_path_security(path, context)

def validate_filename(filename: str, context: str = "filename") -> str:
    """验证文件名安全性（便捷函数）"""
    return get_input_validator().validate_filename(filename, context)

def validate_api_key(api_key: str, platform: str = "generic") -> Tuple[bool, str]:
    """验证API密钥格式（便捷函数）"""
    return get_input_validator().validate_api_key(api_key, platform)

def sanitize_string(text: str, max_length: int = 1000) -> str:
    """清理字符串输入（便捷函数）"""
    return get_input_validator().sanitize_string(text, max_length)


# 此模块为纯库文件，专注于输入验证和安全功能
# 按照配置驱动架构设计，不提供命令行接口
# 开发者通过Python接口使用验证功能
