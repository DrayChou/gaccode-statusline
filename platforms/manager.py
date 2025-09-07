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
    from config import get_config_manager
    from data.logger import log_message, log_platform_detection, log_error
    from data.session_manager import SessionManager, detect_platform_from_session_id
except ImportError:
    # Fallback to sys.path manipulation for runtime
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from config import get_config_manager

    sys.path.insert(0, str(Path(__file__).parent.parent / "data"))
    from logger import log_message, log_platform_detection, log_error
    from session_manager import SessionManager, detect_platform_from_session_id


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
        """优化的平台检测，优先使用Session ID前缀检测"""

        # 获取session_id
        session_id = session_info.get("session_id")
        log_message(
            "platform-manager",
            "DEBUG",
            "Starting optimized platform detection",
            {"session_id": session_id},
        )

        # 优先级0 - Session Mapping查询（处理标准UUID）
        if session_id:
            # 先查询session-mappings.json文件
            try:
                from pathlib import Path
                import json

                script_dir = Path(__file__).parent
                mapping_file = (
                    script_dir.parent / "data" / "cache" / "session-mappings.json"
                )

                if mapping_file.exists():
                    try:
                        with open(mapping_file, "r", encoding="utf-8-sig") as f:
                            mappings = json.load(f)

                        if session_id in mappings:
                            mapping_info = mappings[session_id]
                            detected_platform_name = mapping_info.get("platform")

                            if detected_platform_name:
                                log_message(
                                    "platform-manager",
                                    "INFO",
                                    f"Platform detected from session mapping: {detected_platform_name}",
                                    {
                                        "session_id": session_id,
                                        "detected_platform": detected_platform_name,
                                        "mapping_type": "session_mappings",
                                    },
                                )

                                # 获取平台配置并创建实例
                                platform_instance = self._create_platform_instance(
                                    detected_platform_name, token, config, session_id
                                )
                                if platform_instance:
                                    return platform_instance
                    except (json.JSONDecodeError, UnicodeDecodeError) as e:
                        log_message(
                            "platform-manager",
                            "WARNING",
                            f"Failed to parse session mappings: {e}",
                        )
            except Exception as e:
                log_message(
                    "platform-manager",
                    "DEBUG",
                    f"Session mapping lookup failed: {e}",
                )

        # 优先级1 - Session ID前缀检测（最快，O(1)复杂度）
        if session_id:
            detected_platform_name = detect_platform_from_session_id(session_id)
            if detected_platform_name:
                log_message(
                    "platform-manager",
                    "INFO",
                    f"Platform detected from session ID prefix: {detected_platform_name}",
                    {
                        "session_id": session_id,
                        "detected_platform": detected_platform_name,
                    },
                )

                # 获取平台配置并创建实例
                platform_instance = self._create_platform_instance(
                    detected_platform_name, token, config, session_id
                )
                if platform_instance:
                    log_platform_detection(
                        session_id,
                        platform_instance.name,
                        1.0,  # 最高置信度
                        "session_id_prefix",
                    )
                    return platform_instance
                else:
                    log_message(
                        "platform-manager",
                        "WARNING",
                        f"Failed to create platform instance for {detected_platform_name}",
                    )

        # 优先级2 - 配置文件显式指定
        config_manager = get_config_manager()
        platform_type = config.get("platform_type", "").lower()
        if platform_type:
            log_message(
                "platform-manager",
                "DEBUG",
                "Trying platform detection by config platform_type",
                {"platform_type": platform_type},
            )

            platform_instance = self._create_platform_instance(
                platform_type, token, config, session_id
            )
            if platform_instance:
                log_platform_detection(
                    session_id,
                    platform_instance.name,
                    0.9,
                    "config_platform_type",
                )
                return platform_instance

        # 优先级3 - 传统token格式检测
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
                    platform_config = config_manager.get_platform(platform_name)
                    if platform_config and platform_config.get("enabled"):
                        platform_token = platform_config.get(
                            "auth_token"
                        ) or platform_config.get("api_key")

                        if platform_token:
                            platform_with_token = platform_class(platform_token, config)
                            if platform_with_token.detect_platform(
                                session_info, platform_token
                            ):
                                log_platform_detection(
                                    session_id,
                                    platform_with_token.name,
                                    0.7,
                                    "traditional_with_config_token",
                                )
                                if platform:
                                    platform.close()
                                return platform_with_token
                            else:
                                platform_with_token.close()

                # 关闭不匹配的平台实例
                if platform:
                    platform.close()

            except Exception as e:
                log_message(
                    "platform-manager",
                    "ERROR",
                    f"Error during platform detection: {platform_class.__name__}",
                    {"error": str(e)},
                )
                # 清理资源
                if platform:
                    platform.close()
                if platform_with_token:
                    platform_with_token.close()

        # 优先级4 - 如果所有检测都失败，默认使用GAC Code平台
        log_message(
            "platform-manager",
            "INFO",
            "No platform detected, falling back to default GAC Code platform",
            {"session_id": session_id},
        )

        default_platform = self._create_platform_instance(
            "gaccode", token, config, session_id
        )
        if default_platform:
            log_platform_detection(
                session_id,
                default_platform.name,
                0.5,  # 较低置信度，因为是默认选择
                "default_fallback",
            )
            return default_platform

        return None

    def _create_platform_instance(
        self, platform_name: str, token: str, config: Dict[str, Any], session_id: str
    ) -> Optional[BasePlatform]:
        """
        根据平台名称创建平台实例

        Args:
            platform_name: 平台名称
            token: API token
            config: 配置信息
            session_id: Session ID

        Returns:
            平台实例或None
        """
        try:
            config_manager = get_config_manager()
            platform_config = config_manager.get_platform(platform_name)

            if not platform_config or not platform_config.get("enabled"):
                log_message(
                    "platform-manager",
                    "WARNING",
                    f"Platform {platform_name} not enabled or not configured",
                )
                return None

            # 根据平台类型选择正确的token字段
            if platform_name == "gaccode":
                platform_token = platform_config.get(
                    "login_token"
                ) or platform_config.get("api_key", token)
            else:
                platform_token = platform_config.get(
                    "auth_token"
                ) or platform_config.get("api_key", token)

            # 查找匹配的平台类
            for platform_class in self._platform_classes:
                try:
                    # 传递平台特定配置给平台实例
                    platform_specific_config = {**config, **platform_config}
                    temp_instance = platform_class(
                        platform_token, platform_specific_config
                    )
                    if temp_instance.name.lower() == platform_name:
                        log_message(
                            "platform-manager",
                            "INFO",
                            f"Created platform instance for {platform_name}",
                            {
                                "session_id": session_id,
                                "platform_name": platform_name,
                                "token_length": (
                                    len(platform_token) if platform_token else 0
                                ),
                                "platform_class": platform_class.__name__,
                            },
                        )
                        return temp_instance
                    else:
                        # 关闭不匹配的实例
                        temp_instance.close()
                except Exception as e:
                    log_message(
                        "platform-manager",
                        "ERROR",
                        f"Failed to create {platform_class.__name__} instance: {e}",
                    )
                    # 确保在异常情况下也清理资源
                    if 'temp_instance' in locals():
                        try:
                            temp_instance.close()
                        except:
                            pass  # 忽略清理时的异常

            log_message(
                "platform-manager",
                "WARNING",
                f"No platform class found for {platform_name}",
            )
            return None

        except Exception as e:
            log_message(
                "platform-manager",
                "ERROR",
                f"Error creating platform instance for {platform_name}: {e}",
                {"session_id": session_id},
            )
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
                    f"Failed to create platform {platform_class.__name__}: {e}",
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
                    f"Failed to get platform name for {cls.__name__}: {e}",
                )
        return platforms
