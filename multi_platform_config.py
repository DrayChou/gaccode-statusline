#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Multi-platform configuration manager
多平台配置管理器，统一管理所有渠道的API keys和配置
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List
import fcntl
from datetime import datetime

# Import logger system
try:
    # Try absolute import first (for Pylance/static analysis)
    from data.logger import log_message
except ImportError:
    # Fallback to sys.path manipulation for runtime
    sys.path.insert(0, str(Path(__file__).parent / "data"))
    from logger import log_message


class MultiPlatformConfig:
    """多平台配置管理器"""

    def __init__(self):
        self.project_dir = Path(__file__).parent
        self.config_file = self.project_dir / "multi-platform-config.json"
        self.lock_file = self.project_dir / "config.lock"

        # 默认配置模板
        self.default_config = {
            "platforms": {
                "gaccode": {
                    "name": "GAC Code",
                    "api_base_url": "https://gaccode.com/api",
                    "api_key": "",
                    "model": "claude-3-5-sonnet-20241022",
                    "enabled": True,
                },
                "kimi": {
                    "name": "Kimi (月之暗面)",
                    "api_base_url": "https://api.moonshot.cn/v1",
                    "api_key": "",
                    "model": "moonshot-v1-8k",
                    "enabled": False,
                },
                "deepseek": {
                    "name": "DeepSeek",
                    "api_base_url": "https://api.deepseek.com",
                    "api_key": "",
                    "model": "deepseek-chat",
                    "enabled": False,
                },
                "siliconflow": {
                    "name": "SiliconFlow (硅基流动)",
                    "api_base_url": "https://api.siliconflow.cn/v1",
                    "api_key": "",
                    "model": "deepseek-ai/deepseek-v3.1",
                    "enabled": False,
                },
                "custom_proxy": {
                    "name": "Custom Proxy (本地代理)",
                    "api_base_url": "http://localhost:7601",
                    "api_key": "local-proxy-key",
                    "model": "deepseek-v3.1",
                    "enabled": True,
                    "proxy_for": "deepseek",  # 代理的实际平台
                },
            },
            "settings": {
                "default_platform": "gaccode",
                "auto_detect_platform": True,
                "cache_ttl_seconds": 3600,
                "created": datetime.now().isoformat(),
                "version": "1.0",
            },
        }

    def _load_config(self) -> Dict[str, Any]:
        """安全加载配置文件"""
        if not self.config_file.exists():
            return self.default_config.copy()

        try:
            with open(self.config_file, "r", encoding="utf-8-sig") as f:
                config = json.load(f)
                # 合并默认配置，确保所有字段都存在
                merged_config = self.default_config.copy()
                self._deep_merge(merged_config, config)
                return merged_config
        except (json.JSONDecodeError, IOError):
            return self.default_config.copy()

    def _deep_merge(self, target: Dict, source: Dict):
        """深度合并字典"""
        for key, value in source.items():
            if (
                key in target
                and isinstance(target[key], dict)
                and isinstance(value, dict)
            ):
                self._deep_merge(target[key], value)
            else:
                target[key] = value

    def _save_config(self, config: Dict[str, Any]) -> bool:
        """安全保存配置文件"""
        try:
            # 更新时间戳
            config["settings"]["last_updated"] = datetime.now().isoformat()

            # 原子保存
            temp_file = self.config_file.with_suffix(".tmp")
            with open(temp_file, "w", encoding="utf-8-sig") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

            temp_file.replace(self.config_file)
            return True
        except Exception:
            return False

    def get_platform_config(self, platform: str) -> Optional[Dict[str, Any]]:
        """获取指定平台的配置"""
        config = self._load_config()
        return config.get("platforms", {}).get(platform)

    def set_platform_config(
        self, platform: str, platform_config: Dict[str, Any]
    ) -> bool:
        """设置指定平台的配置"""
        try:
            with open(self.lock_file, "w") as lock:
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX)

                config = self._load_config()
                if "platforms" not in config:
                    config["platforms"] = {}

                config["platforms"][platform] = platform_config
                return self._save_config(config)

        except (OSError, IOError):
            return False

    def get_api_key(self, platform: str) -> Optional[str]:
        """获取指定平台的API key"""
        platform_config = self.get_platform_config(platform)
        if platform_config:
            return platform_config.get("api_key")
        return None

    def set_api_key(self, platform: str, api_key: str) -> bool:
        """设置指定平台的API key"""
        platform_config = self.get_platform_config(platform)
        if platform_config:
            platform_config["api_key"] = api_key
            return self.set_platform_config(platform, platform_config)
        return False

    def get_enabled_platforms(self) -> List[str]:
        """获取所有启用的平台列表"""
        config = self._load_config()
        enabled_platforms = []

        for platform, platform_config in config.get("platforms", {}).items():
            if platform_config.get("enabled", False) and platform_config.get("api_key"):
                enabled_platforms.append(platform)

        return enabled_platforms

    def get_default_platform(self) -> str:
        """获取默认平台"""
        config = self._load_config()
        default_platform = config.get("settings", {}).get("default_platform", "gaccode")

        # 确保默认平台是启用的
        enabled_platforms = self.get_enabled_platforms()
        if default_platform in enabled_platforms:
            return default_platform
        elif enabled_platforms:
            return enabled_platforms[0]
        else:
            return "gaccode"

    def set_default_platform(self, platform: str) -> bool:
        """设置默认平台"""
        try:
            with open(self.lock_file, "w") as lock:
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX)

                config = self._load_config()
                config["settings"]["default_platform"] = platform
                return self._save_config(config)

        except (OSError, IOError):
            return False

    def list_all_platforms(self) -> Dict[str, Any]:
        """列出所有平台配置"""
        config = self._load_config()
        platforms_info = {}

        for platform, platform_config in config.get("platforms", {}).items():
            platforms_info[platform] = {
                "name": platform_config.get("name", platform),
                "api_base_url": platform_config.get("api_base_url", ""),
                "model": platform_config.get("model", ""),
                "enabled": platform_config.get("enabled", False),
                "has_api_key": bool(platform_config.get("api_key", "")),
                "proxy_for": platform_config.get("proxy_for"),
            }

        return platforms_info

    def create_default_config(self) -> bool:
        """创建默认配置文件"""
        return self._save_config(self.default_config.copy())

    def migrate_from_old_token_file(self) -> bool:
        """从旧的api-token.txt文件迁移"""
        old_token_file = self.project_dir / "api-token.txt"
        if not old_token_file.exists():
            return False

        try:
            with open(old_token_file, "r", encoding="utf-8-sig") as f:
                old_token = f.read().strip()

            if old_token:
                # 假设旧token是GAC Code的
                return self.set_api_key("gaccode", old_token)
        except Exception:
            pass

        return False

    def export_config_for_platform(self, platform: str) -> Optional[Dict[str, str]]:
        """导出指定平台的环境变量配置"""
        platform_config = self.get_platform_config(platform)
        if not platform_config:
            return None

        env_vars = {
            "ANTHROPIC_API_KEY": platform_config.get("api_key", ""),
            "ANTHROPIC_BASE_URL": platform_config.get("api_base_url", ""),
            "ANTHROPIC_MODEL": platform_config.get("model", ""),
        }

        # 过滤空值
        return {k: v for k, v in env_vars.items() if v}


# 便捷函数
def get_platform_token(platform: str) -> Optional[str]:
    """便捷函数：获取平台token"""
    config = MultiPlatformConfig()
    return config.get_api_key(platform)


def get_current_platform_from_env() -> Optional[str]:
    """从环境变量推断当前平台"""
    config = MultiPlatformConfig()

    # 检查当前环境变量
    current_base_url = os.environ.get("ANTHROPIC_BASE_URL", "").lower()
    current_model = os.environ.get("ANTHROPIC_MODEL", "").lower()

    # 与配置中的平台进行匹配
    for platform, platform_config in config._load_config().get("platforms", {}).items():
        base_url = platform_config.get("api_base_url", "").lower()
        model = platform_config.get("model", "").lower()

        if base_url and base_url in current_base_url:
            return platform
        elif model and model in current_model:
            return platform

    return None


if __name__ == "__main__":
    # 命令行工具
    import sys

    config = MultiPlatformConfig()

    if len(sys.argv) < 2:
        print("Usage: python multi_platform_config.py <command> [args]")
        print("Commands: list, set-key, get-key, enable, disable, default")
        sys.exit(1)

    command = sys.argv[1]

    if command == "list":
        platforms = config.list_all_platforms()
        for platform, info in platforms.items():
            status = "✓" if info["enabled"] and info["has_api_key"] else "✗"
            print(f"{status} {platform}: {info['name']}")
            print(f"   URL: {info['api_base_url']}")
            print(f"   Model: {info['model']}")
            print(f"   API Key: {'Set' if info['has_api_key'] else 'Not set'}")
            print()

    elif command == "set-key" and len(sys.argv) == 4:
        platform, api_key = sys.argv[2], sys.argv[3]
        if config.set_api_key(platform, api_key):
            print(f"✓ API key set for {platform}")
        else:
            print(f"✗ Failed to set API key for {platform}")

    elif command == "get-key" and len(sys.argv) == 3:
        platform = sys.argv[2]
        api_key = config.get_api_key(platform)
        if api_key:
            print(f"{platform}: {api_key}")
        else:
            print(f"No API key set for {platform}")

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
