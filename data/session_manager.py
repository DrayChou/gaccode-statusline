#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Session管理器 - 基于平台前缀的高效session ID管理
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

try:
    from .logger import log_message
    from .file_lock import safe_json_write, safe_json_read
except ImportError:
    import sys

    sys.path.insert(0, str(Path(__file__).parent))
    from logger import log_message
    from file_lock import safe_json_write, safe_json_read


class SessionManager:
    """Session ID管理器 - 支持平台前缀和会话延续"""

    # 平台ID映射（序号方案 - 简化UUID生成）
    PLATFORM_IDS = {
        "gaccode": 1,
        "deepseek": 2,
        "kimi": 3,
        "siliconflow": 4,
        "local_proxy": 5,
    }

    # 反向映射：ID -> 平台
    ID_TO_PLATFORM = {v: k for k, v in PLATFORM_IDS.items()}

    def __init__(self, state_file: Optional[Path] = None):
        """
        初始化Session管理器

        Args:
            state_file: session状态文件路径，默认使用项目根目录下的.session-state.json
        """
        if state_file is None:
            # 默认使用data/cache目录
            project_root = Path(__file__).parent.parent
            state_file = project_root / "data" / "cache" / "session-state.json"

        self.state_file = state_file
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

        log_message(
            "session-manager",
            "DEBUG",
            f"Initialized with state file: {self.state_file}",
        )

    def generate_session_id(self, platform: str) -> str:
        """
        生成符合UUID格式的带平台前缀的Session ID

        UUID格式: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
        我们将前2个字符替换为平台前缀

        Args:
            platform: 平台名称

        Returns:
            符合UUID格式的session ID，如: gac00000-xxxx-xxxx-xxxx-xxxxxxxxxxxx
        """
        if platform not in self.PLATFORM_IDS:
            log_message(
                "session-manager",
                "WARNING",
                f"Unknown platform: {platform}, using default ID",
            )
            platform_id = 999  # 默认ID
        else:
            platform_id = self.PLATFORM_IDS[platform]

        # 生成标准UUID
        base_uuid = uuid.uuid4()
        uuid_str = str(base_uuid)

        # 将UUID第一段的前2位替换为平台ID的十六进制表示
        uuid_parts = uuid_str.split("-")
        original_first = uuid_parts[0]
        platform_hex = f"{platform_id:02x}"  # 2位十六进制，如：01, 02, 03, 04, 05
        # 替换前2位，保持后6位
        uuid_parts[0] = platform_hex + original_first[2:]

        session_id = "-".join(uuid_parts)

        log_message(
            "session-manager",
            "INFO",
            f"Generated UUID-compliant session ID for {platform}",
            {
                "platform": platform,
                "session_id": session_id,
                "platform_id": platform_id,
                "platform_hex": platform_hex,
            },
        )

        return session_id

    def detect_platform_from_session_id(self, session_id: str) -> Optional[str]:
        """
        从Session ID前缀快速检测平台

        Args:
            session_id: Session ID (UUID格式)

        Returns:
            检测到的平台名称，无法检测则返回None
        """
        if not session_id or "-" not in session_id:
            log_message(
                "session-manager", "DEBUG", f"Invalid session ID format: {session_id}"
            )
            return None

        # 提取UUID第一段
        first_segment = session_id.split("-")[0]
        if len(first_segment) != 8:
            log_message(
                "session-manager",
                "DEBUG",
                f"Invalid UUID first segment length: {first_segment}",
            )
            return None

        # 提取前2位十六进制数字作为平台ID
        try:
            platform_id = int(first_segment[:2], 16)  # 只取前2位
            if platform_id in self.ID_TO_PLATFORM:
                platform = self.ID_TO_PLATFORM[platform_id]
                log_message(
                    "session-manager",
                    "DEBUG",
                    f"Detected platform from session ID",
                    {
                        "session_id": session_id,
                        "first_segment": first_segment,
                        "platform_id": platform_id,
                        "platform": platform,
                    },
                )
                return platform
        except (ValueError, IndexError):
            # 无法解析为十六进制数字或长度不足
            pass

        log_message(
            "session-manager",
            "DEBUG",
            f"Unknown prefix in session ID first segment: {first_segment}",
        )
        return None

    def save_session_state(self, platform: str, session_id: str) -> bool:
        """
        保存平台的最后使用session状态

        Args:
            platform: 平台名称
            session_id: Session ID

        Returns:
            保存是否成功
        """
        try:
            # 读取现有状态
            state = self._load_session_state()

            # 更新平台状态
            if platform not in state:
                state[platform] = {}

            state[platform].update(
                {
                    "last_session_id": session_id,
                    "last_used": datetime.now().isoformat(),
                    "created": state[platform].get(
                        "created", datetime.now().isoformat()
                    ),
                }
            )

            # 保存状态
            success = safe_json_write(self.state_file, state)
            if success:
                log_message(
                    "session-manager",
                    "INFO",
                    f"Saved session state for {platform}",
                    {"platform": platform, "session_id": session_id},
                )
            else:
                log_message(
                    "session-manager",
                    "ERROR",
                    f"Failed to save session state for {platform}",
                )

            return success

        except Exception as e:
            log_message(
                "session-manager",
                "ERROR",
                f"Error saving session state: {e}",
                {"platform": platform, "session_id": session_id},
            )
            return False

    def get_last_session_id(self, platform: str) -> Optional[str]:
        """
        获取平台最后使用的Session ID

        Args:
            platform: 平台名称

        Returns:
            最后使用的Session ID，如果没有则返回None
        """
        try:
            state = self._load_session_state()
            platform_state = state.get(platform, {})
            session_id = platform_state.get("last_session_id")

            if session_id:
                log_message(
                    "session-manager",
                    "DEBUG",
                    f"Found last session for {platform}",
                    {
                        "platform": platform,
                        "session_id": session_id,
                        "last_used": platform_state.get("last_used"),
                    },
                )
            else:
                log_message(
                    "session-manager", "DEBUG", f"No last session found for {platform}"
                )

            return session_id

        except Exception as e:
            log_message(
                "session-manager",
                "ERROR",
                f"Error getting last session: {e}",
                {"platform": platform},
            )
            return None

    def create_or_continue_session(
        self, platform: str, continue_session: bool = False
    ) -> str:
        """
        创建新session或继续上次的session

        Args:
            platform: 平台名称
            continue_session: 是否继续上次的session

        Returns:
            Session ID
        """
        if continue_session:
            last_session_id = self.get_last_session_id(platform)
            if last_session_id:
                # 更新最后使用时间
                self.save_session_state(platform, last_session_id)
                log_message(
                    "session-manager",
                    "INFO",
                    f"Continuing session for {platform}",
                    {"platform": platform, "session_id": last_session_id},
                )
                return last_session_id
            else:
                log_message(
                    "session-manager",
                    "INFO",
                    f"No previous session found for {platform}, creating new one",
                )

        # 创建新session
        session_id = self.generate_session_id(platform)
        self.save_session_state(platform, session_id)

        return session_id

    def _load_session_state(self) -> Dict[str, Any]:
        """
        加载session状态文件

        Returns:
            session状态字典
        """
        return safe_json_read(self.state_file, {})

    def cleanup_old_sessions(self, max_age_days: int = 30) -> int:
        """
        清理旧的session状态记录

        Args:
            max_age_days: 最大保留天数

        Returns:
            清理的session数量
        """
        try:
            state = self._load_session_state()
            current_time = datetime.now()
            cleaned_count = 0

            for platform, platform_state in list(state.items()):
                last_used_str = platform_state.get("last_used")
                if last_used_str:
                    try:
                        last_used = datetime.fromisoformat(last_used_str)
                        age_days = (current_time - last_used).days

                        if age_days > max_age_days:
                            del state[platform]
                            cleaned_count += 1
                            log_message(
                                "session-manager",
                                "DEBUG",
                                f"Cleaned old session for {platform}",
                                {"platform": platform, "age_days": age_days},
                            )
                    except ValueError:
                        # 无效的日期格式，删除
                        del state[platform]
                        cleaned_count += 1
                        log_message(
                            "session-manager",
                            "WARNING",
                            f"Removed invalid session state for {platform}",
                        )

            if cleaned_count > 0:
                success = safe_json_write(self.state_file, state)
                if success:
                    log_message(
                        "session-manager",
                        "INFO",
                        f"Cleaned {cleaned_count} old session states",
                    )
                else:
                    log_message(
                        "session-manager",
                        "ERROR",
                        "Failed to save cleaned session state",
                    )
                    return 0

            return cleaned_count

        except Exception as e:
            log_message("session-manager", "ERROR", f"Error during cleanup: {e}")
            return 0

    def list_session_states(self) -> Dict[str, Dict[str, Any]]:
        """
        列出所有平台的session状态

        Returns:
            平台session状态字典
        """
        return self._load_session_state()


# 便捷函数
def detect_platform_from_session_id(session_id: str) -> Optional[str]:
    """
    便捷函数：从Session ID检测平台
    """
    manager = SessionManager()
    return manager.detect_platform_from_session_id(session_id)


def create_session_for_platform(platform: str, continue_session: bool = False) -> str:
    """
    便捷函数：为指定平台创建或继续session
    """
    manager = SessionManager()
    return manager.create_or_continue_session(platform, continue_session)


# 此模块为纯库文件，专注于会话状态管理功能
# 按照配置驱动架构设计，不提供命令行接口
# 用户通过修改配置文件和启动脚本管理会话，通过Python接口使用会话功能
