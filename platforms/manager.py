#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Platform manager for detecting and managing different API platforms
"""

from typing import Dict, Any, Optional, List
from .base import BasePlatform
from .gaccode import GACCodePlatform
from .kimi import KimiPlatform
from .deepseek import DeepSeekPlatform
from .siliconflow import SiliconFlowPlatform
import sys
from pathlib import Path

# Import using relative imports from parent directory
try:
    # Try absolute import first
    from platform_manager import PlatformManager as ConfigManager
    from data.logger import log_message, log_platform_detection, log_error
except ImportError:
    # Fallback to sys.path manipulation for runtime
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from platform_manager import PlatformManager as ConfigManager

    sys.path.insert(0, str(Path(__file__).parent.parent / "data"))
    from logger import log_message, log_platform_detection, log_error


class PlatformManager:
    """Manager for handling multiple API platforms"""

    def __init__(self):
        self.platforms: List[BasePlatform] = []
        self._platform_classes = [
            GACCodePlatform,
            KimiPlatform,
            DeepSeekPlatform,
            SiliconFlowPlatform,
        ]

    def detect_platform(
        self, session_info: Dict[str, Any], token: str, config: Dict[str, Any]
    ) -> Optional[BasePlatform]:
        """Simplified platform detection using session mapping"""

        # 优先级1 - Session UUID映射检测（最高置信度）
        try:
            # 从session_info中获取session_id，而不是从文件读取
            session_id = session_info.get("session_id")
            log_message(
                "platform-manager",
                "DEBUG",
                "Starting platform detection",
                {"session_id": session_id},
            )

            if session_id:
                config_manager = ConfigManager()
                session_config = config_manager.get_session_config(session_id)

                if session_config:
                    platform_name = session_config["platform"]
                    log_message(
                        "platform-manager",
                        "DEBUG",
                        "Found session mapping",
                        {"session_id": session_id, "platform_name": platform_name},
                    )

                    # 根据platform名称获取完整配置
                    platform_config = config_manager.get_platform_config(platform_name)
                    if platform_config and platform_config.get("enabled"):
                        # 根据平台类型选择正确的token字段
                        if platform_name == "gaccode":
                            platform_token = platform_config.get("login_token") or platform_config.get("api_key", token)
                        else:
                            platform_token = platform_config.get("auth_token") or platform_config.get("api_key", token)

                        for platform_class in self._platform_classes:
                            try:
                                platform = platform_class(platform_token, config)
                                if platform.name.lower() == platform_name:
                                    log_platform_detection(
                                        session_id,
                                        platform.name,
                                        1.0,
                                        "UUID_session_mapping",
                                    )
                                    log_message(
                                        "platform-manager",
                                        "INFO",
                                        f"Platform instance created successfully",
                                        {
                                            "session_id": session_id,
                                            "platform_name": platform.name,
                                            "token_length": len(platform_token) if platform_token else 0,
                                            "token_prefix": platform_token[:10] + "..." if platform_token and len(platform_token) > 10 else platform_token,
                                            "platform_class": platform_class.__name__
                                        }
                                    )
                                    return platform
                                else:
                                    # 关闭不匹配的平台实例
                                    platform.close()
                            except Exception as e:
                                log_message(
                                    "platform-manager",
                                    "ERROR",
                                    f"Failed to create platform instance: {platform_class.__name__}",
                                    {"error": str(e)}
                                )
                    else:
                        log_message(
                            "platform-manager",
                            "WARNING",
                            "Platform not enabled in config",
                            {
                                "platform_name": platform_name,
                                "enabled": (
                                    platform_config.get("enabled")
                                    if platform_config
                                    else None
                                ),
                            },
                        )
                else:
                    log_message(
                        "platform-manager",
                        "DEBUG",
                        "No session mapping found",
                        {"session_id": session_id},
                    )
        except Exception as e:
            log_error("platform-manager", e, "UUID detection failed")

        # 优先级2 - 配置文件显式指定
        config_manager = ConfigManager()
        platform_type = config.get("platform_type", "").lower()
        if platform_type:
            log_message(
                "platform-manager",
                "DEBUG",
                "Trying platform detection by config platform_type",
                {"platform_type": platform_type},
            )
            
            # 根据platform名称获取完整配置和token
            platform_config = config_manager.get_platform_config(platform_type)
            if platform_config and platform_config.get("enabled"):
                # 根据平台类型选择正确的token字段
                if platform_type == "gaccode":
                    platform_token = platform_config.get("login_token") or platform_config.get("api_key", token)
                else:
                    platform_token = platform_config.get("auth_token") or platform_config.get("api_key", token)
                
                log_message(
                    "platform-manager",
                    "DEBUG",
                    "Found platform config, using token from config",
                    {
                        "platform_type": platform_type,
                        "token_length": len(platform_token) if platform_token else 0,
                        "token_prefix": platform_token[:10] + "..." if platform_token and len(platform_token) > 10 else platform_token,
                        "has_auth_token": bool(platform_config.get("auth_token")),
                        "has_api_key": bool(platform_config.get("api_key"))
                    }
                )
                
                for platform_class in self._platform_classes:
                    try:
                        platform = platform_class(platform_token, config)
                        if platform.name.lower() == platform_type:
                            log_platform_detection(
                                session_id,
                                platform.name,
                                0.9,
                                "config_platform_type",
                            )
                            return platform
                        else:
                            # 关闭不匹配的平台实例
                            platform.close()
                    except Exception as e:
                        log_message(
                            "platform-manager",
                            "ERROR",
                            f"Failed to create platform instance: {platform_class.__name__}",
                            {"error": str(e)}
                        )
            else:
                log_message(
                    "platform-manager",
                    "WARNING",
                    "Platform config not found or not enabled",
                    {
                        "platform_type": platform_type,
                        "has_config": bool(platform_config),
                        "enabled": platform_config.get("enabled") if platform_config else None
                    }
                )

        # 优先级3 - 传统session信息和token格式检测（带配置文件token获取）
        log_message(
            "platform-manager",
            "DEBUG",
            "Trying traditional platform detection with token format analysis",
        )
        
        for platform_class in self._platform_classes:
            platform = None
            platform_with_token = None
            
            try:
                # 先尝试用当前token检测
                platform = platform_class(token, config)
                if platform.detect_platform(session_info, token):
                    log_platform_detection(
                        session_id,
                        platform.name,
                        0.8,
                        "traditional_detection",
                    )
                    return platform
                    
                # 如果当前token为null，尝试从配置文件获取该平台的token
                if not token:
                    platform_name = platform.name.lower()
                    platform_config = config_manager.get_platform_config(platform_name)
                    if platform_config and platform_config.get("enabled"):
                        # 优先使用 auth_token，如果没有则使用 api_key
                        platform_token = platform_config.get(
                            "auth_token"
                        ) or platform_config.get("api_key")
                        
                        if platform_token:
                            log_message(
                                "platform-manager",
                                "DEBUG",
                                f"Trying {platform_name} detection with config token",
                                {
                                    "token_length": len(platform_token),
                                    "token_prefix": platform_token[:10] + "..."
                                }
                            )
                            
                            # 用配置文件的token重新创建平台实例并检测
                            platform_with_token = platform_class(platform_token, config)
                            if platform_with_token.detect_platform(session_info, platform_token):
                                log_platform_detection(
                                    session_id,
                                    platform_with_token.name,
                                    0.7,
                                    "traditional_with_config_token",
                                )
                                # 关闭第一个平台实例，返回第二个
                                if platform:
                                    platform.close()
                                return platform_with_token
                            else:
                                # 关闭第二个平台实例
                                platform_with_token.close()
                
                # 关闭不匹配的平台实例
                if platform:
                    platform.close()
                    
            except Exception as e:
                log_message(
                    "platform-manager",
                    "ERROR",
                    f"Error during platform detection: {platform_class.__name__}",
                    {"error": str(e)}
                )
                # 清理资源
                if platform:
                    platform.close()
                if platform_with_token:
                    platform_with_token.close()

        return None

    def get_platform_by_name(
        self, name: str, token: str, config: Dict[str, Any]
    ) -> Optional[BasePlatform]:
        """Get platform by name"""
        for platform_class in self._platform_classes:
            try:
                platform = platform_class(token, config)
                if platform.name.lower() == name.lower():
                    return platform
                else:
                    # 关闭不匹配的平台实例
                    platform.close()
            except Exception as e:
                log_message(
                    "platform-manager",
                    "ERROR",
                    f"Failed to create platform {platform_class.__name__}: {e}"
                )
        return None

    def list_supported_platforms(self) -> List[str]:
        """List all supported platform names"""
        platforms = []
        for cls in self._platform_classes:
            try:
                # 创建临时实例获取名称，然后立即关闭
                temp_platform = cls(None, {})
                platforms.append(temp_platform.name)
                temp_platform.close()
            except Exception as e:
                log_message(
                    "platform-manager",
                    "WARNING",
                    f"Failed to get platform name for {cls.__name__}: {e}"
                )
        return platforms
