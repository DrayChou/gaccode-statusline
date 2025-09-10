#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Session Mapping V2 - Directory-based session storage
会话映射 V2 - 基于目录的会话存储，消除读写竞争
"""

import json
import time
from pathlib import Path
from typing import Dict, Any, Optional
from contextlib import contextmanager

try:
    from .file_lock import safe_json_write, safe_json_read
    from .logger import log_message
except ImportError:
    import sys

    sys.path.insert(0, str(Path(__file__).parent))
    from file_lock import safe_json_write, safe_json_read
    from logger import log_message


class SessionMappingV2:
    """会话映射管理器 V2 - 目录式存储"""

    def __init__(self, cache_dir: Optional[Path] = None):
        """初始化会话映射管理器"""
        self.cache_dir = cache_dir or Path(__file__).parent / "cache"
        self.sessions_dir = self.cache_dir / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

        # 清理过期会话的时间间隔
        self.cleanup_interval = 3600  # 1小时
        self.session_ttl = 86400 * 7  # 7天

    def _get_session_file(self, session_id: str) -> Path:
        """获取会话文件路径"""
        # 使用前2位作为平台目录，便于按平台查找
        if len(session_id) >= 2:
            platform_prefix = session_id[:2].lower()
        else:
            platform_prefix = "00"  # 默认目录
            
        session_dir = self.sessions_dir / platform_prefix
        session_dir.mkdir(exist_ok=True)
        return session_dir / f"{session_id}.json"

    def set_session_platform(
        self, session_id: str, platform: str, metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """设置会话对应的平台"""
        session_file = self._get_session_file(session_id)

        # 检查是否已存在，保留created_at时间
        existing_data = safe_json_read(session_file, {})
        created_at = existing_data.get("created_at", time.time())

        session_data = {
            "platform": platform,
            "session_id": session_id,
            "created_at": created_at,
            "updated_at": time.time(),
            "last_active": time.time(),
            "metadata": metadata or {},
        }

        success = safe_json_write(session_file, session_data)

        if success:
            log_message(
                "session-mapping-v2",
                "DEBUG",
                f"Session mapping saved: {session_id} -> {platform}",
                {
                    "session_id": session_id[:8] + "...",
                    "platform": platform,
                    "file_path": str(session_file),
                },
            )
        else:
            log_message(
                "session-mapping-v2",
                "ERROR",
                f"Failed to save session mapping: {session_id}",
                {"platform": platform},
            )

        return success

    def update_session_info(
        self, session_id: str, session_info: Dict[str, Any], platform: Optional[str] = None
    ) -> bool:
        """更新会话的完整信息（包括详细session数据）"""
        session_file = self._get_session_file(session_id)

        # 读取现有数据
        existing_data = safe_json_read(session_file, {})
        
        # 如果没有现有数据，需要platform参数
        if not existing_data and not platform:
            log_message(
                "session-mapping-v2",
                "WARNING", 
                f"Cannot update session info without platform for new session: {session_id}",
            )
            return False

        # 确定平台
        current_platform = platform or existing_data.get("platform", "gaccode")
        created_at = existing_data.get("created_at", time.time())
        
        # 构建更新的session数据
        updated_data = {
            "platform": current_platform,
            "session_id": session_id,
            "created_at": created_at,
            "updated_at": time.time(),
            "last_active": time.time(),
            "metadata": existing_data.get("metadata", {}),
            "session_info": session_info
        }

        success = safe_json_write(session_file, updated_data)

        if success:
            log_message(
                "session-mapping-v2",
                "DEBUG",
                f"Session info updated: {session_id}",
                {
                    "session_id": session_id[:8] + "...",
                    "platform": current_platform,
                    "has_session_info": bool(session_info),
                },
            )
        else:
            log_message(
                "session-mapping-v2",
                "ERROR",
                f"Failed to update session info: {session_id}",
                {"platform": current_platform},
            )

        return success

    def get_session_platform(self, session_id: str) -> Optional[str]:
        """获取会话对应的平台"""
        session_file = self._get_session_file(session_id)

        if not session_file.exists():
            log_message(
                "session-mapping-v2",
                "DEBUG",
                f"Session mapping not found: {session_id}",
                {"session_id": session_id[:8] + "..."},
            )
            return None

        try:
            session_data = safe_json_read(session_file)
            if not session_data:
                return None

            platform = session_data.get("platform")

            # 检查会话是否过期
            created_at = session_data.get("created_at", 0)
            if time.time() - created_at > self.session_ttl:
                log_message(
                    "session-mapping-v2",
                    "INFO",
                    f"Session expired, removing: {session_id}",
                    {
                        "session_id": session_id[:8] + "...",
                        "age_hours": round((time.time() - created_at) / 3600, 1),
                    },
                )
                session_file.unlink(missing_ok=True)
                return None

            log_message(
                "session-mapping-v2",
                "DEBUG",
                f"Session mapping found: {session_id} -> {platform}",
                {"session_id": session_id[:8] + "...", "platform": platform},
            )

            return platform

        except Exception as e:
            log_message(
                "session-mapping-v2",
                "ERROR",
                f"Failed to read session mapping: {session_id}",
                {"error": str(e)},
            )
            return None

    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取完整的会话信息"""
        session_file = self._get_session_file(session_id)

        if not session_file.exists():
            return None

        return safe_json_read(session_file)

    def delete_session(self, session_id: str) -> bool:
        """删除会话映射"""
        session_file = self._get_session_file(session_id)

        try:
            if session_file.exists():
                session_file.unlink()
                log_message(
                    "session-mapping-v2",
                    "DEBUG",
                    f"Session mapping deleted: {session_id}",
                    {"session_id": session_id[:8] + "..."},
                )
                return True
            return False
        except Exception as e:
            log_message(
                "session-mapping-v2",
                "ERROR",
                f"Failed to delete session mapping: {session_id}",
                {"error": str(e)},
            )
            return False

    def cleanup_expired_sessions(self) -> int:
        """清理过期的会话映射"""
        cleaned_count = 0
        current_time = time.time()

        try:
            for platform_dir in self.sessions_dir.iterdir():
                if not platform_dir.is_dir():
                    continue

                for session_file in platform_dir.glob("*.json"):
                    try:
                        # 检查文件修改时间
                        file_age = current_time - session_file.stat().st_mtime
                        if file_age > self.session_ttl:
                            session_file.unlink()
                            cleaned_count += 1
                    except Exception:
                        # 删除无法处理的文件
                        session_file.unlink(missing_ok=True)
                        cleaned_count += 1

                # 删除空的平台目录
                try:
                    if not any(platform_dir.iterdir()):
                        platform_dir.rmdir()
                except Exception:
                    pass

            if cleaned_count > 0:
                log_message(
                    "session-mapping-v2",
                    "INFO",
                    f"Cleaned up {cleaned_count} expired sessions",
                )

        except Exception as e:
            log_message("session-mapping-v2", "ERROR", f"Session cleanup failed: {e}")

        return cleaned_count

    def list_sessions(
        self, platform: Optional[str] = None
    ) -> Dict[str, Dict[str, Any]]:
        """列出所有会话映射"""
        sessions = {}

        try:
            for platform_dir in self.sessions_dir.iterdir():
                if not platform_dir.is_dir():
                    continue

                for session_file in platform_dir.glob("*.json"):
                    try:
                        session_data = safe_json_read(session_file)
                        if session_data:
                            session_id = session_data.get("session_id")
                            session_platform = session_data.get("platform")

                            # 平台过滤
                            if platform and session_platform != platform:
                                continue

                            # 检查过期
                            created_at = session_data.get("created_at", 0)
                            if time.time() - created_at <= self.session_ttl:
                                sessions[session_id] = session_data
                    except Exception:
                        continue

        except Exception as e:
            log_message("session-mapping-v2", "ERROR", f"Failed to list sessions: {e}")

        return sessions

    def get_stats(self) -> Dict[str, Any]:
        """获取会话映射统计信息"""
        stats = {
            "total_sessions": 0,
            "platforms": {},
            "prefix_dirs": 0,
            "expired_sessions": 0,
        }

        current_time = time.time()

        try:
            for platform_dir in self.sessions_dir.iterdir():
                if not platform_dir.is_dir():
                    continue

                stats["prefix_dirs"] += 1

                for session_file in platform_dir.glob("*.json"):
                    try:
                        session_data = safe_json_read(session_file)
                        if session_data:
                            platform = session_data.get("platform", "unknown")
                            created_at = session_data.get("created_at", 0)

                            if current_time - created_at > self.session_ttl:
                                stats["expired_sessions"] += 1
                            else:
                                stats["total_sessions"] += 1
                                stats["platforms"][platform] = (
                                    stats["platforms"].get(platform, 0) + 1
                                )
                    except Exception:
                        stats["expired_sessions"] += 1

        except Exception as e:
            log_message(
                "session-mapping-v2", "ERROR", f"Failed to get session stats: {e}"
            )

        return stats


# 全局会话映射管理器实例
_session_mapping: Optional[SessionMappingV2] = None


def get_session_mapping() -> SessionMappingV2:
    """获取全局会话映射管理器实例"""
    global _session_mapping
    if _session_mapping is None:
        _session_mapping = SessionMappingV2()
    return _session_mapping


# 便捷函数
def set_session_platform(
    session_id: str, platform: str, metadata: Optional[Dict[str, Any]] = None
) -> bool:
    """便捷的设置会话平台函数"""
    return get_session_mapping().set_session_platform(session_id, platform, metadata)


def get_session_platform(session_id: str) -> Optional[str]:
    """便捷的获取会话平台函数"""
    return get_session_mapping().get_session_platform(session_id)


def cleanup_expired_sessions() -> int:
    """便捷的清理过期会话函数"""
    return get_session_mapping().cleanup_expired_sessions()


def update_session_info(
    session_id: str, session_info: Dict[str, Any], platform: Optional[str] = None
) -> bool:
    """便捷的更新会话完整信息函数"""
    return get_session_mapping().update_session_info(session_id, session_info, platform)


def detect_platform_from_session_id(session_id: str) -> Optional[str]:
    """
    从Session ID前缀快速检测平台（兼容旧系统）
    
    Args:
        session_id: Session ID (UUID格式)
        
    Returns:
        检测到的平台名称，无法检测则返回None
    """
    if not session_id or "-" not in session_id:
        log_message(
            "session-mapping-v2", "DEBUG", f"Invalid session ID format: {session_id}"
        )
        return None

    # 提取UUID第一段
    first_segment = session_id.split("-")[0]
    if len(first_segment) != 8:
        log_message(
            "session-mapping-v2",
            "DEBUG",
            f"Invalid UUID first segment length: {first_segment}",
        )
        return None

    # 平台ID映射（兼容旧系统）
    PLATFORM_IDS = {
        "gaccode": 1,
        "deepseek": 2,
        "kimi": 3,
        "siliconflow": 4,
        "local_proxy": 5,
    }
    ID_TO_PLATFORM = {v: k for k, v in PLATFORM_IDS.items()}

    # 提取前2位十六进制数字作为平台ID
    try:
        platform_id = int(first_segment[:2], 16)  # 只取前2位
        if platform_id in ID_TO_PLATFORM:
            platform = ID_TO_PLATFORM[platform_id]
            log_message(
                "session-mapping-v2",
                "DEBUG",
                f"Detected platform from session ID",
                {
                    "session_id": session_id[:8] + "...",
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
        "session-mapping-v2",
        "DEBUG",
        f"Unknown prefix in session ID first segment: {first_segment}",
    )
    return None


# 此模块为纯库文件，专注于会话映射功能
# 按照配置驱动架构设计，不提供命令行接口
# 通过Python接口使用会话映射功能
