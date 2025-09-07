#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unified Configuration Manager
统一配置管理器 - 整合所有配置文件和配置逻辑
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import sys

# Import data utilities
try:
    from data.file_lock import safe_json_write, safe_json_read
    from data.logger import log_message
except ImportError:
    # Fallback import for development
    sys.path.insert(0, str(Path(__file__).parent / "data"))
    from file_lock import safe_json_write, safe_json_read
    from logger import log_message


class ConfigManager:
    """统一配置管理器"""
    
    def __init__(self, project_dir: Optional[Path] = None):
        """初始化配置管理器"""
        self.project_dir = project_dir or Path(__file__).parent
        self.config_dir = self.project_dir / "data" / "config"
        self.unified_config_file = self.config_dir / "config.json"
        
        # 确保配置目录存在
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # 配置缓存
        self._config_cache: Optional[Dict[str, Any]] = None
        self._cache_timestamp: Optional[datetime] = None
        
        # 配置文件变更监听
        self._last_modified: Optional[float] = None
        
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置结构"""
        return {
            "version": "2.0",
            "last_updated": datetime.now().isoformat(),
            
            # 平台配置 (来自 launcher-config.json)
            "platforms": {
                "gaccode": {
                    "name": "GAC Code",
                    "api_base_url": "https://relay05.gaccode.com/claudecode",
                    "api_key": "",
                    "login_token": "",
                    "model": "",
                    "small_model": "",
                    "enabled": True
                },
                "kimi": {
                    "name": "Kimi",
                    "api_base_url": "https://api.moonshot.cn/anthropic",
                    "auth_token": "",
                    "model": "kimi-k2-0905-preview",
                    "small_model": "kimi-k2-0905-preview",
                    "enabled": True
                },
                "deepseek": {
                    "name": "DeepSeek",
                    "api_base_url": "https://api.deepseek.com/anthropic",
                    "api_key": "",
                    "model": "deepseek-chat",
                    "small_model": "deepseek-chat",
                    "enabled": True
                },
                "siliconflow": {
                    "name": "SiliconFlow",
                    "api_base_url": "https://api.siliconflow.cn/",
                    "api_key": "",
                    "model": "deepseek-ai/DeepSeek-V3.1",
                    "small_model": "deepseek-ai/DeepSeek-V3.1",
                    "enabled": True
                },
                "local_proxy": {
                    "name": "Local Proxy",
                    "api_base_url": "http://localhost:7601",
                    "api_key": "local-key",
                    "model": "deepseek-v3.1",
                    "small_model": "deepseek-v3.1",
                    "enabled": True,
                    "proxy_for": "deepseek"
                }
            },
            
            # 平台别名 (来自 launcher-config.json)
            "aliases": {
                "gc": "gaccode",
                "dp": "deepseek",
                "ds": "deepseek",
                "sc": "siliconflow",
                "sf": "siliconflow",
                "lp": "local_proxy",
                "kimi": "kimi",
                "local": "local_proxy"
            },
            
            # 启动器设置 (来自 launcher-config.json)
            "launcher": {
                "default_platform": "gaccode",  # Single Platform Mode 使用的默认平台
                "plugin_path": ".",
                "claude_executable": "claude",
                "git_bash_path": "bash.exe"
            },
            
            # 状态条显示设置 (来自 statusline-config.json)
            "statusline": {
                "show_model": True,
                "show_directory": True,
                "show_git_branch": True,
                "show_time": True,
                "show_session_duration": False,
                "show_session_cost": True,
                "show_balance": True,
                "show_subscription": True,
                "show_today_usage": True,
                "directory_full_path": True,
                "layout": "single_line"
            },
            
            # 倍率配置 (来自 statusline-config.json)
            "multiplier": {
                "enabled": True,
                "periods": [
                    {
                        "name": "peak_hour",
                        "start_time": "16:30",
                        "end_time": "18:30",
                        "multiplier": 5.0,
                        "display_text": "5X",
                        "weekdays_only": True,
                        "color": "red"
                    },
                    {
                        "name": "off_peak",
                        "start_time": "01:00",
                        "end_time": "10:00",
                        "multiplier": 0.8,
                        "display_text": "0.8X",
                        "weekdays_only": False,
                        "color": "green"
                    }
                ]
            },
            
            # 缓存设置
            "cache": {
                "balance_timeout": 60,
                "subscription_timeout": 3600,
                "usage_timeout": 600
            },
            
            # 日志设置
            "logging": {
                "level": "INFO",
                "enabled": True
            }
        }
    
    def _should_reload_config(self) -> bool:
        """检查是否需要重新加载配置"""
        if not self.unified_config_file.exists():
            return True
            
        if self._config_cache is None:
            return True
            
        # 检查文件修改时间
        current_mtime = self.unified_config_file.stat().st_mtime
        if self._last_modified is None or current_mtime > self._last_modified:
            return True
            
        return False
    
    def load_config(self) -> Dict[str, Any]:
        """加载配置"""
        if self._should_reload_config():
            if self.unified_config_file.exists():
                config = safe_json_read(self.unified_config_file)
                if config is None:
                    log_message("config", "ERROR", f"Failed to load config from {self.unified_config_file}")
                    config = self._get_default_config()
            else:
                log_message("config", "INFO", "Creating default configuration")
                config = self._get_default_config()
                self.save_config(config)
            
            self._config_cache = config
            self._last_modified = self.unified_config_file.stat().st_mtime if self.unified_config_file.exists() else None
            
        return self._config_cache.copy()
    
    def save_config(self, config: Dict[str, Any]) -> bool:
        """保存配置（带安全检查）"""
        config["last_updated"] = datetime.now().isoformat()
        
        # 安全检查：确保不保存明文密钥
        safe_config = self._sanitize_config_for_storage(config.copy())
        
        if safe_json_write(self.unified_config_file, safe_config):
            self._config_cache = config.copy()  # 缓存使用原始配置（包含密钥）
            self._last_modified = self.unified_config_file.stat().st_mtime
            log_message("config", "INFO", f"Configuration saved to {self.unified_config_file}")
            return True
        else:
            log_message("config", "ERROR", f"Failed to save configuration to {self.unified_config_file}")
            return False
    
    # 便捷访问方法
    def get_platforms(self) -> Dict[str, Any]:
        """获取平台配置"""
        return self.load_config().get("platforms", {})
    
    def get_platform(self, platform_id: str) -> Optional[Dict[str, Any]]:
        """获取特定平台配置"""
        platforms = self.get_platforms()
        return platforms.get(platform_id)
    
    def get_aliases(self) -> Dict[str, str]:
        """获取平台别名映射"""
        return self.load_config().get("aliases", {})
    
    def get_launcher_settings(self) -> Dict[str, Any]:
        """获取启动器设置"""
        return self.load_config().get("launcher", {})
    
    def get_statusline_settings(self) -> Dict[str, Any]:
        """获取状态条设置"""
        return self.load_config().get("statusline", {})
    
    def get_multiplier_config(self) -> Dict[str, Any]:
        """获取倍率配置"""
        return self.load_config().get("multiplier", {})
    
    def get_cache_settings(self) -> Dict[str, Any]:
        """获取缓存设置"""
        return self.load_config().get("cache", {})
    
    def resolve_platform_alias(self, alias: str) -> str:
        """解析平台别名"""
        aliases = self.get_aliases()
        return aliases.get(alias, alias)
    
    def get_platform_api_key(self, platform_id: str) -> Optional[str]:
        """获取平台API密钥 - 纯配置文件架构"""
        platform = self.get_platform(platform_id)
        if not platform:
            return None
            
        # 从配置文件获取凭证
        config_key = platform.get("api_key") or platform.get("auth_token") or platform.get("login_token")
        if config_key:
            log_message(
                "config", "DEBUG", 
                f"Using credentials from config file for {platform_id}",
                {"platform": platform_id, "source": "config_file"}
            )
            return config_key
            
        return None
    
    def update_platform_setting(self, platform_id: str, key: str, value: Any) -> bool:
        """更新平台设置"""
        config = self.load_config()
        if platform_id not in config.get("platforms", {}):
            return False
            
        config["platforms"][platform_id][key] = value
        return self.save_config(config)
    
    def update_statusline_setting(self, key: str, value: Any) -> bool:
        """更新状态条设置"""
        config = self.load_config()
        config.setdefault("statusline", {})[key] = value
        return self.save_config(config)
    
    def update_launcher_setting(self, key: str, value: Any) -> bool:
        """更新启动器设置"""
        config = self.load_config()
        config.setdefault("launcher", {})[key] = value
        return self.save_config(config)
    
    def set_default_platform(self, platform_id: str) -> bool:
        """设置默认平台
        
        Args:
            platform_id: 平台ID，如 'deepseek', 'kimi' 等
            
        Returns:
            设置是否成功
        """
        # 解析别名
        resolved_platform = self.resolve_platform_alias(platform_id)
        
        # 验证平台是否存在且启用
        platform_config = self.get_platform(resolved_platform)
        if not platform_config:
            log_message("config", "ERROR", f"Platform {resolved_platform} not found")
            return False
        
        if not platform_config.get("enabled", False):
            log_message("config", "WARNING", f"Platform {resolved_platform} is disabled")
        
        # 设置默认平台
        result = self.update_launcher_setting("default_platform", resolved_platform)
        
        if result:
            log_message(
                "config", "INFO", 
                f"Default platform set to {resolved_platform}",
                {"platform": resolved_platform, "alias": platform_id}
            )
        
        return result
    
    def get_effective_platform(self, session_id: Optional[str] = None) -> str:
        """获取有效平台（智能检测）
        
        根据优先级逐级检查：
        1. Session ID 映射 (Multi-Platform Mode)
        2. UUID 前缀 (Multi-Platform Mode) 
        3. 默认平台配置 (Single Platform Mode)
        4. GAC Code 默认 (Basic Mode)
        
        Args:
            session_id: 可选的Session ID
            
        Returns:
            有效的平台名称
        """
        # 优先级1: Session ID 映射
        if session_id:
            try:
                from pathlib import Path
                mapping_file = self.project_dir / "data" / "cache" / "session-mappings.json"
                if mapping_file.exists():
                    mappings = safe_json_read(mapping_file, {})
                    mapping_info = mappings.get(session_id, {})
                    mapped_platform = mapping_info.get("platform")
                    if mapped_platform:
                        return mapped_platform
                
                # 优先级2: UUID 前缀检测
                try:
                    sys.path.insert(0, str(self.project_dir / "data"))
                    from session_manager import detect_platform_from_session_id
                    prefix_platform = detect_platform_from_session_id(session_id)
                    if prefix_platform:
                        return prefix_platform
                except ImportError:
                    pass
            except Exception as e:
                log_message("config", "DEBUG", f"Session-based detection failed: {e}")
        
        # 优先级3: 默认平台配置
        launcher_settings = self.get_launcher_settings()
        default_platform = launcher_settings.get("default_platform", "gaccode")
        
        # 验证默认平台是否有效
        if default_platform != "gaccode":
            platform_config = self.get_platform(default_platform)
            api_key = self.get_platform_api_key(default_platform)
            
            if platform_config and platform_config.get("enabled") and api_key:
                return default_platform
        
        # 优先级4: 默认回退到 GAC Code
        return "gaccode"
    
    def migrate_legacy_configs(self) -> bool:
        """迁移旧版配置文件"""
        try:
            config = self.load_config()
            migrated = False
            
            # 迁移 launcher-config.json
            launcher_config_file = self.config_dir / "launcher-config.json"
            if launcher_config_file.exists():
                log_message("config", "INFO", "Migrating launcher-config.json")
                legacy_config = safe_json_read(launcher_config_file)
                if legacy_config:
                    # 合并平台配置
                    if "platforms" in legacy_config:
                        config["platforms"].update(legacy_config["platforms"])
                    # 合并别名
                    if "aliases" in legacy_config:
                        config["aliases"].update(legacy_config["aliases"])
                    # 合并设置
                    if "settings" in legacy_config:
                        launcher_settings = config.setdefault("launcher", {})
                        launcher_settings.update(legacy_config["settings"])
                    
                    migrated = True
            
            # 迁移 statusline-config.json
            statusline_config_file = self.config_dir / "statusline-config.json"
            if statusline_config_file.exists():
                log_message("config", "INFO", "Migrating statusline-config.json")
                legacy_config = safe_json_read(statusline_config_file)
                if legacy_config:
                    # 提取倍率配置
                    if "multiplier_config" in legacy_config:
                        config["multiplier"] = legacy_config["multiplier_config"]
                        del legacy_config["multiplier_config"]
                    
                    # 其余配置合并到statusline
                    config["statusline"].update(legacy_config)
                    migrated = True
            
            if migrated:
                self.save_config(config)
                log_message("config", "INFO", "Configuration migration completed")
                
            return migrated
            
        except Exception as e:
            log_message("config", "ERROR", f"Configuration migration failed: {e}")
            return False


# 全局配置管理器实例
_config_manager: Optional[ConfigManager] = None

def get_config_manager() -> ConfigManager:
    """获取全局配置管理器实例"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


    def _sanitize_config_for_storage(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """清理配置中的敏感信息，防止明文存储"""
        sensitive_keys = ['api_key', 'auth_token', 'login_token', 'password', 'secret']
        
        if "platforms" in config:
            for platform_name, platform_config in config["platforms"].items():
                if isinstance(platform_config, dict):
                    for key in sensitive_keys:
                        if key in platform_config and platform_config[key]:
                            # 如果密钥不为空，建议使用环境变量
                            log_message(
                                "config", "WARNING",
                                f"Detected API key in config for {platform_name}. Consider using environment variable {platform_name.upper()}_{key.upper()}"
                            )
                            # 不清空密钥，但记录警告
        
        return config

    def validate_api_key_format(self, key: str, platform: str) -> bool:
        """验证API密钥格式"""
        if not key:
            return False
            
        patterns = {
            'gaccode': r'^sk-ant-[a-zA-Z0-9-]+$',
            'deepseek': r'^sk-[a-zA-Z0-9]{32}$',
            'kimi': r'^sk-[a-zA-Z0-9]{48}$',
            'siliconflow': r'^sk-[a-zA-Z0-9]{48}$'
        }
        
        pattern = patterns.get(platform)
        if pattern:
            import re
            return bool(re.match(pattern, key))
        
        # 通用验证：至少20个字符，包含字母数字
        return len(key) >= 20 and any(c.isalnum() for c in key)


# 本模块采用配置驱动架构，不提供命令行接口
# 用户通过编辑 data/config/config.json 进行配置管理
# 使用方式：from config import get_config_manager
