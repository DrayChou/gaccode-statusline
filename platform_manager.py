#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simplified Multi-Platform Manager
精简的多平台管理器，整合配置管理和session映射
"""

import json
import sys
import uuid
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

# Import logger system and file lock utility
try:
    # Try absolute import first (for Pylance/static analysis)
    from data.logger import log_message
    from data.file_lock import safe_json_write, safe_json_read
except ImportError:
    # Fallback to sys.path manipulation for runtime
    sys.path.insert(0, str(Path(__file__).parent / "data"))
    from logger import log_message
    from file_lock import safe_json_write, safe_json_read


class PlatformManager:
    """精简的多平台管理器"""

    def __init__(self):
        self.project_dir = Path(__file__).parent
        self.data_dir = self.project_dir / "data"
        self.config_file = self.data_dir / "config" / "launcher-config.json"
        self.session_file = self.data_dir / "cache" / "session-mappings.json"

        # 确保目录存在
        (self.data_dir / "config").mkdir(parents=True, exist_ok=True)
        (self.data_dir / "cache").mkdir(parents=True, exist_ok=True)

    def get_default_config(self) -> Dict[str, Any]:
        """默认配置"""
        return {
            "platforms": {
                "gaccode": {
                    "name": "GAC Code",
                    "api_base_url": "https://gaccode.com/api",
                    "api_key": "",
                    "model": "claude-3-5-sonnet-20241022",
                    "small_model": "claude-3-5-haiku-20241022",
                    "enabled": False,
                },
                "kimi": {
                    "name": "Kimi (月之暗面)",
                    "api_base_url": "https://api.moonshot.cn/v1",
                    "api_key": "",
                    "model": "moonshot-v1-8k",
                    "small_model": "moonshot-v1-8k",
                    "enabled": False,
                },
                "deepseek": {
                    "name": "DeepSeek",
                    "api_base_url": "https://api.deepseek.com",
                    "api_key": "",
                    "model": "deepseek-chat",
                    "small_model": "deepseek-chat",
                    "enabled": False,
                },
                "siliconflow": {
                    "name": "SiliconFlow",
                    "api_base_url": "https://api.siliconflow.cn/v1",
                    "api_key": "",
                    "model": "deepseek-ai/deepseek-v3.1",
                    "small_model": "deepseek-ai/deepseek-v3.1",
                    "enabled": False,
                },
                "local_proxy": {
                    "name": "Local Proxy",
                    "api_base_url": "http://localhost:7601",
                    "api_key": "local-key",
                    "model": "deepseek-v3.1",
                    "small_model": "deepseek-v3.1",
                    "enabled": False,
                    "proxy_for": "deepseek",
                },
            },
            "aliases": {
                "gc": "gaccode",
                "dp": "deepseek",
                "ds": "deepseek",
                "sf": "siliconflow",
                "lp": "local_proxy",
                "local": "local_proxy",
            },
            "settings": {
                "default_platform": "gaccode",
                "created": datetime.now().isoformat(),
            },
        }

    def load_config(self) -> Dict[str, Any]:
        """加载配置"""
        log_message(
            "platform-manager",
            "DEBUG",
            "Loading platform configuration",
            {"config_file": str(self.config_file)},
        )

        if not self.config_file.exists():
            log_message(
                "platform-manager",
                "WARNING",
                "Configuration file not found, creating default config",
            )
            config = self.get_default_config()
            self.save_config(config)
            return config

        try:
            config = safe_json_read(self.config_file, {})
            if config:
                log_message(
                    "platform-manager",
                    "DEBUG",
                    "Platform configuration loaded successfully",
                )
                return config
            else:
                log_message(
                    "platform-manager",
                    "WARNING",
                    "Empty or invalid configuration file, using default config",
                )
                return self.get_default_config()
        except Exception as e:
            log_message(
                "platform-manager",
                "ERROR",
                "Failed to load configuration, using default config",
                {"error": str(e)},
            )
            return self.get_default_config()

    def save_config(self, config: Dict[str, Any]) -> bool:
        """保存配置（带文件锁定）"""
        try:
            # 确保settings存在
            if "settings" not in config:
                config["settings"] = {}
            config["settings"]["last_updated"] = datetime.now().isoformat()

            # 使用安全的文件写入（带锁定）
            success = safe_json_write(self.config_file, config)
            if success:
                log_message(
                    "platform-manager", "DEBUG", "Configuration saved successfully"
                )
            else:
                log_message(
                    "platform-manager", "ERROR", "Failed to write configuration file"
                )
            return success
        except Exception as e:
            log_message(
                "platform-manager",
                "ERROR",
                "Failed to save configuration",
                {"error": str(e)},
            )
            return False

    def resolve_platform_alias(self, platform_or_alias: str) -> str:
        """解析平台别名到实际平台名"""
        config = self.load_config()
        aliases = config.get("aliases", {})
        return aliases.get(platform_or_alias, platform_or_alias)

    def get_platform_config(self, platform: str) -> Optional[Dict[str, Any]]:
        """获取平台配置（支持别名）"""
        config = self.load_config()
        resolved_platform = self.resolve_platform_alias(platform)
        return config.get("platforms", {}).get(resolved_platform)

    # set_platform_key method removed for security reasons
    # Users should manually configure API keys in configuration files

    def get_enabled_platforms(self) -> Dict[str, Dict[str, Any]]:
        """获取启用的平台"""
        config = self.load_config()
        enabled = {}
        for platform, platform_config in config["platforms"].items():
            if platform_config.get("enabled") and platform_config.get("api_key"):
                enabled[platform] = platform_config
        return enabled

    def register_session(
        self,
        platform: str,
        session_uuid: str,
    ) -> bool:
        """注册session到平台的映射关系"""
        try:
            # 读取现有mappings
            mappings = safe_json_read(self.session_file, {})

            # 添加新的session映射，只存储平台名称
            mappings[session_uuid] = {
                "platform": platform,
                "created": datetime.now().isoformat(),
            }

            # 清理旧mappings（保留最近50个）
            if len(mappings) > 50:
                sorted_items = sorted(
                    mappings.items(),
                    key=lambda x: x[1].get("created", ""),
                    reverse=True,
                )
                mappings = dict(sorted_items[:50])
                log_message(
                    "platform-manager",
                    "DEBUG",
                    f"Cleaned old session mappings, kept {len(mappings)} recent entries",
                )

            # 安全保存mappings（带锁定）
            success = safe_json_write(self.session_file, mappings)
            if success:
                log_message(
                    "platform-manager",
                    "DEBUG",
                    f"Session {session_uuid} registered for platform {platform}",
                )
            else:
                log_message(
                    "platform-manager",
                    "ERROR",
                    f"Failed to register session {session_uuid}",
                )
            return success
        except Exception as e:
            log_message(
                "platform-manager",
                "ERROR",
                f"Failed to register session {session_uuid}: {e}",
            )
            return False

    def get_session_config(self, session_uuid: str) -> Optional[Dict[str, Any]]:
        """根据session UUID获取完整配置"""
        try:
            if not self.session_file.exists():
                log_message(
                    "platform-manager",
                    "DEBUG",
                    "Session mapping file not found",
                    {"file": str(self.session_file)},
                )
                return None

            # 使用安全的文件读取
            mappings = safe_json_read(self.session_file, {})
            session_config = mappings.get(session_uuid)

            if session_config:
                log_message(
                    "platform-manager",
                    "DEBUG",
                    f"Found session config for {session_uuid}",
                    {"platform": session_config.get("platform")},
                )
            else:
                log_message(
                    "platform-manager",
                    "DEBUG",
                    f"No session config found for {session_uuid}",
                )

            return session_config
        except Exception as e:
            log_message(
                "platform-manager",
                "ERROR",
                f"Failed to get session config for {session_uuid}: {e}",
            )
            return None

    def get_current_session_config(self) -> Optional[Dict[str, Any]]:
        """获取当前session的完整配置"""
        try:
            session_info_file = self.data_dir / "cache" / "session-info-cache.json"
            if not session_info_file.exists():
                log_message(
                    "platform-manager", "DEBUG", "Session info cache file not found"
                )
                return None

            # 使用安全的文件读取
            session_info = safe_json_read(session_info_file, {})
            session_id = session_info.get("session_id")

            if session_id:
                log_message(
                    "platform-manager",
                    "DEBUG",
                    f"Found current session ID: {session_id}",
                )
                return self.get_session_config(session_id)
            else:
                log_message("platform-manager", "DEBUG", "No session ID in cache file")
        except Exception as e:
            log_message(
                "platform-manager",
                "ERROR",
                f"Failed to get current session config: {e}",
            )

        return None

    def detect_platform_from_session(self) -> Optional[str]:
        """从当前session检测平台"""
        session_config = self.get_current_session_config()
        return session_config.get("platform") if session_config else None

    def generate_session_uuid(self) -> str:
        """生成新的session UUID"""
        return str(uuid.uuid4())

    def migrate_old_config(self) -> bool:
        """迁移旧的token文件"""
        old_token_file = self.project_dir / "api-token.txt"
        if old_token_file.exists():
            try:
                with open(old_token_file, "r", encoding="utf-8-sig") as f:
                    old_token = f.read().strip()
                if old_token:
                    log_message(
                        "platform-manager",
                        "INFO",
                        "Migrating old token file to new config system",
                    )
                    return self.set_platform_key("gaccode", old_token)
            except Exception as e:
                log_message(
                    "platform-manager", "ERROR", f"Failed to migrate old token: {e}"
                )
        return False

    def list_platforms(self) -> None:
        """列出所有平台状态"""
        config = self.load_config()
        print("Platform Status:")
        print("=" * 50)

        for platform, platform_config in config["platforms"].items():
            status = (
                "[OK]"
                if (platform_config.get("enabled") and platform_config.get("api_key"))
                else "[--]"
            )
            print(f"{status} {platform}: {platform_config['name']}")
            print(f"   URL: {platform_config['api_base_url']}")
            print(f"   Model: {platform_config['model']}")
            print(f"   Key: {'Set' if platform_config.get('api_key') else 'Not Set'}")
            print()


# 便捷函数
def get_platform_token(platform: str) -> Optional[str]:
    """获取平台token"""
    manager = PlatformManager()
    platform_config = manager.get_platform_config(platform)
    return platform_config.get("api_key") if platform_config else None


# 此模块为纯库文件，专注于平台管理功能
# 按照配置驱动架构设计，不提供命令行接口
# 用户通过修改配置文件管理平台设置，通过Python接口使用平台功能
