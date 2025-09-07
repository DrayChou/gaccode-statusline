#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Secure Configuration Manager
安全配置管理器 - 环境变量优先，敏感数据保护
"""

import os
import json
import re
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

try:
    from .file_lock import safe_json_read, safe_json_write
    from .logger import log_message
except ImportError:
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from file_lock import safe_json_read, safe_json_write
    from logger import log_message


class SecureConfigLoader:
    """安全配置加载器 - 环境变量优先，敏感数据掩码"""
    
    # 敏感字段模式匹配
    SENSITIVE_PATTERNS = [
        r'api[_-]?key',
        r'auth[_-]?token', 
        r'login[_-]?token',
        r'access[_-]?token',
        r'secret[_-]?key',
        r'private[_-]?key',
        r'password',
        r'credential',
        r'bearer[_-]?token'
    ]
    
    # 已移除环境变量映射 - 纯配置文件架构
    
    def __init__(self, project_dir: Optional[Path] = None):
        """初始化安全配置加载器"""
        self.project_dir = project_dir or Path(__file__).parent.parent
        self.config_dir = self.project_dir / "data" / "config"
        self.config_file = self.config_dir / "config.json"
        self.template_file = self.config_dir / "config.json.template"
        
        # 创建安全的logger实例
        self.logger = logging.getLogger('secure_config')
    
    def _mask_sensitive_value(self, value: str) -> str:
        """掩码敏感值显示"""
        if not value or len(value) < 8:
            return "[MASKED]"
        
        if value.startswith(('sk-', 'Bearer ', 'eyJ')):
            # API密钥和JWT令牌特殊处理
            return f"{value[:8]}***{value[-4:]}"
        else:
            # 其他敏感值
            return f"{value[:3]}***{value[-3:]}"
    
    def _is_sensitive_key(self, key: str) -> bool:
        """检查字段是否为敏感信息"""
        key_lower = key.lower()
        return any(re.search(pattern, key_lower, re.IGNORECASE) 
                  for pattern in self.SENSITIVE_PATTERNS)
    
    def _mask_config_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """递归掩码配置数据中的敏感信息"""
        if isinstance(data, dict):
            masked_data = {}
            for key, value in data.items():
                if self._is_sensitive_key(key) and isinstance(value, str):
                    masked_data[key] = self._mask_sensitive_value(value)
                elif isinstance(value, (dict, list)):
                    masked_data[key] = self._mask_config_data(value)
                else:
                    masked_data[key] = value
            return masked_data
        elif isinstance(data, list):
            return [self._mask_config_data(item) for item in data]
        else:
            return data
    
    # 已移除环境变量加载功能 - 纯配置文件架构
    
    def _load_from_config_file(self) -> Dict[str, Any]:
        """从配置文件加载配置（不包含敏感信息）"""
        if not self.config_file.exists():
            log_message("secure_config", "WARNING", "Config file not found, using template")
            if self.template_file.exists():
                return safe_json_read(self.template_file, {})
            return {}
        
        try:
            config_data = safe_json_read(self.config_file, {})
            log_message(
                "secure_config", "INFO", 
                "Configuration loaded from file",
                {"config_file": str(self.config_file)}
            )
            return config_data
        except Exception as e:
            log_message("secure_config", "ERROR", f"Failed to load config file: {e}")
            return {}
    
    def get_platform_credentials(self, platform: str) -> Dict[str, str]:
        """安全获取平台凭证 - 纯配置文件"""
        config_data = self._load_from_config_file()
        platform_config = config_data.get('platforms', {}).get(platform, {})
        
        # 从配置文件获取所有配置
        credentials = {}
        for key, value in platform_config.items():
            if value:  # 只添加非空值
                credentials[key] = value
        
        return credentials
    
    def load_secure_config(self) -> Dict[str, Any]:
        """加载完整的安全配置"""
        base_config = self._load_from_config_file()
        
        # 为每个平台应用安全凭证加载
        if 'platforms' in base_config:
            for platform_name in base_config['platforms'].keys():
                secure_credentials = self.get_platform_credentials(platform_name)
                base_config['platforms'][platform_name].update(secure_credentials)
        
        return base_config
    
    def validate_config_security(self) -> Dict[str, Any]:
        """验证配置安全性"""
        security_report = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": "SECURE",
            "issues": [],
            "recommendations": []
        }
        
        # 检查配置文件是否包含敏感信息
        if self.config_file.exists():
            config_data = safe_json_read(self.config_file, {})
            
            for platform_name, platform_config in config_data.get('platforms', {}).items():
                for key, value in platform_config.items():
                    if self._is_sensitive_key(key) and value and isinstance(value, str):
                        security_report["overall_status"] = "CRITICAL"
                        security_report["issues"].append({
                            "severity": "CRITICAL",
                            "type": "EXPOSED_CREDENTIAL",
                            "location": f"platforms.{platform_name}.{key}",
                            "masked_value": self._mask_sensitive_value(value),
                            "description": f"Plain text credential found in config file"
                        })
                        
                        # 纯配置文件架构 - 无环境变量建议
                        security_report["recommendations"].append(
                            f"Secure {platform_name}.{key} in configuration file with proper permissions"
                        )
        
        # 已移除环境变量检查 - 纯配置文件架构
        
        return security_report
    
    def clean_config_file(self) -> bool:
        """清理配置文件中的敏感信息"""
        if not self.config_file.exists():
            return True
        
        try:
            config_data = safe_json_read(self.config_file, {})
            cleaned = False
            
            # 清理平台配置中的敏感信息
            for platform_name, platform_config in config_data.get('platforms', {}).items():
                for key in list(platform_config.keys()):
                    if self._is_sensitive_key(key) and platform_config[key]:
                        log_message(
                            "secure_config", "INFO",
                            f"Cleaning sensitive field {platform_name}.{key}",
                            {"platform": platform_name, "field": key}
                        )
                        platform_config[key] = ""
                        cleaned = True
            
            if cleaned:
                # 备份原文件
                backup_file = self.config_file.with_suffix('.json.backup')
                if backup_file.exists():
                    backup_file.unlink()
                self.config_file.rename(backup_file)
                
                # 写入清理后的配置
                safe_json_write(self.config_file, config_data)
                log_message(
                    "secure_config", "INFO",
                    "Configuration file cleaned, backup created",
                    {"backup_file": str(backup_file)}
                )
                
            return True
            
        except Exception as e:
            log_message("secure_config", "ERROR", f"Failed to clean config file: {e}")
            return False


# 全局实例
_secure_config_loader: Optional[SecureConfigLoader] = None

def get_secure_config_loader(project_dir: Optional[Path] = None) -> SecureConfigLoader:
    """获取安全配置加载器实例"""
    global _secure_config_loader
    if _secure_config_loader is None:
        _secure_config_loader = SecureConfigLoader(project_dir)
    return _secure_config_loader


def load_secure_platform_config(platform: str) -> Dict[str, str]:
    """便捷函数：安全加载平台配置"""
    loader = get_secure_config_loader()
    return loader.get_platform_credentials(platform)


# 此模块为纯库文件，专注于安全配置管理功能
# 按照配置驱动架构设计，不提供命令行接口
# 用户通过设置环境变量和修改配置文件管理凭证，通过Python接口使用安全功能