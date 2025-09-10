#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unified Session Manager
统一会话管理器 - 整合所有会话相关功能
"""

import json
import uuid
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
import sys
import os

# Import utilities
try:
    from data.file_lock import safe_json_write, safe_json_read
    from data.logger import log_message
    from cache import get_cache_manager
    from config import get_config_manager
except ImportError:
    # Fallback import for development
    sys.path.insert(0, str(Path(__file__).parent / "data"))
    from file_lock import safe_json_write, safe_json_read
    from logger import log_message

    sys.path.insert(0, str(Path(__file__).parent))
    from cache import get_cache_manager
    from config import get_config_manager


class SessionInfo:
    """会话信息数据结构"""

    def __init__(
        self, session_id: str, platform: str, created_at: Optional[datetime] = None
    ):
        self.session_id = session_id
        self.platform = platform
        self.created_at = created_at or datetime.now()
        self.last_used = datetime.now()
        self.metadata: Dict[str, Any] = {}

    @property
    def standard_uuid(self) -> str:
        """获取标准UUID（移除平台前缀）"""
        if self.is_prefixed_uuid:
            return self.session_id[2:]
        return self.session_id

    @property
    def prefixed_uuid(self) -> str:
        """获取带平台前缀的UUID"""
        if self.is_prefixed_uuid:
            return self.session_id

        platform_prefix = UnifiedSessionManager.PLATFORM_PREFIXES.get(
            self.platform, "01"
        )
        return f"{platform_prefix}{self.session_id[2:]}"

    @property
    def is_prefixed_uuid(self) -> bool:
        """检查是否为带前缀的UUID"""
        if len(self.session_id) != 36:
            return False
        return self.session_id[:2].isalnum() and self.session_id[2] == "-"

    @property
    def age_seconds(self) -> float:
        """会话年龄（秒）"""
        return (datetime.now() - self.created_at).total_seconds()

    @property
    def last_used_seconds(self) -> float:
        """最后使用时间（秒前）"""
        return (datetime.now() - self.last_used).total_seconds()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "session_id": self.session_id,
            "platform": self.platform,
            "created_at": self.created_at.isoformat(),
            "last_used": self.last_used.isoformat(),
            "metadata": self.metadata,
            "standard_uuid": self.standard_uuid,
            "prefixed_uuid": self.prefixed_uuid,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionInfo":
        """从字典创建会话信息"""
        session = cls(
            session_id=data["session_id"],
            platform=data["platform"],
            created_at=datetime.fromisoformat(data["created_at"]),
        )
        session.last_used = datetime.fromisoformat(data["last_used"])
        session.metadata = data.get("metadata", {})
        return session


class UnifiedSessionManager:
    """统一会话管理器"""

    # 平台前缀映射（2位十六进制）
    PLATFORM_PREFIXES = {
        "gaccode": "01",
        "deepseek": "02",
        "kimi": "03",
        "siliconflow": "04",
        "local_proxy": "05",
    }

    # 反向映射：前缀 -> 平台
    PREFIX_TO_PLATFORM = {v: k for k, v in PLATFORM_PREFIXES.items()}

    def __init__(self, data_dir: Optional[Path] = None):
        """初始化会话管理器"""
        self.data_dir = data_dir or Path(__file__).parent / "data"
        self.cache_dir = self.data_dir / "cache"
        self.sessions_dir = self.cache_dir / "sessions"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

        # 保留旧的映射文件路径用于数据迁移
        self.session_mappings_file = self.cache_dir / "session-mappings.json"

        # 获取依赖
        self.cache_manager = get_cache_manager()
        self.config_manager = get_config_manager()

    def _get_session_file_path(self, session_id: str) -> Path:
        """获取session文件路径（SessionMappingV2兼容）"""
        if len(session_id) >= 2:
            platform_prefix = session_id[:2].lower()
        else:
            platform_prefix = "00"
        
        session_dir = self.sessions_dir / platform_prefix
        session_dir.mkdir(exist_ok=True)
        return session_dir / f"{session_id}.json"

    def detect_platform_from_session_id(self, session_id: str) -> Optional[str]:
        """从session ID检测平台"""
        if not session_id or len(session_id) < 3:
            return None

        # 优先级1: UUID前缀检测（最快）
        if len(session_id) == 36 and session_id[2] == "-":
            prefix = session_id[:2].lower()
            platform = self.PREFIX_TO_PLATFORM.get(prefix)
            if platform:
                log_message(
                    "session",
                    "DEBUG",
                    f"Platform detected from UUID prefix: {platform}",
                )
                return platform

        # 优先级2: SessionMappingV2查找
        session_file = self._get_session_file_path(session_id)
        if session_file.exists():
            session_data = safe_json_read(session_file, {})
            platform = session_data.get("platform")
            if platform:
                log_message(
                    "session",
                    "DEBUG",
                    f"Platform detected from SessionMappingV2: {platform}",
                )
                return platform

        # 优先级3: 检查标准UUID对应的前缀UUID
        if len(session_id) == 36 and session_id[2] != "-":
            for prefix, platform in self.PREFIX_TO_PLATFORM.items():
                prefixed_uuid = f"{prefix}{session_id[2:]}"
                if prefixed_uuid in mappings.get("sessions", {}):
                    log_message(
                        "session",
                        "DEBUG",
                        f"Platform detected from prefixed UUID mapping: {platform}",
                    )
                    return platform

        log_message(
            "session", "DEBUG", f"No platform detected for session: {session_id[:8]}..."
        )
        return None

    def create_session(
        self, platform: str, continue_session: bool = False
    ) -> SessionInfo:
        """创建新会话或继续现有会话"""
        if continue_session:
            # 尝试继续最近的会话
            last_session = self.get_last_session(platform)
            if last_session:
                last_session.last_used = datetime.now()
                self._save_session(last_session)
                log_message(
                    "session",
                    "INFO",
                    f"Continuing session for {platform}: {last_session.session_id}",
                )
                return last_session

        # 创建新会话
        session_id = self._generate_session_id(platform)
        session = SessionInfo(session_id, platform)

        self._save_session(session)
        log_message(
            "session", "INFO", f"Created new session for {platform}: {session_id}"
        )

        return session

    def get_session(self, session_id: str) -> Optional[SessionInfo]:
        """获取会话信息（从SessionMappingV2格式）"""
        # 从SessionMappingV2目录结构读取
        session_file = self._get_session_file_path(session_id)
        
        if session_file.exists():
            session_data = safe_json_read(session_file, {})
            if session_data and "session_info" in session_data:
                return SessionInfo.from_dict(session_data["session_info"])
        
        # 兜底：从旧的映射文件加载（用于数据迁移）
        if self.session_mappings_file.exists():
            mappings = self._load_session_mappings()
            session_data = mappings.get("sessions", {}).get(session_id)
            if session_data:
                session = SessionInfo.from_dict(session_data)
                # 迁移到新格式
                self._save_session(session)
                log_message(
                    "session", "INFO", 
                    f"Migrated session to SessionMappingV2: {session_id[:8]}..."
                )
                return session

        return None

    def get_last_session(self, platform: str) -> Optional[SessionInfo]:
        """获取平台最后使用的会话（从SessionMappingV2格式）"""
        platform_prefix = self.PLATFORM_PREFIXES.get(platform)
        if not platform_prefix:
            return None
            
        platform_dir = self.sessions_dir / platform_prefix
        if not platform_dir.exists():
            return None
            
        # 扫描平台目录找到最新的session
        latest_session = None
        latest_time = 0
        
        for session_file in platform_dir.glob("*.json"):
            session_data = safe_json_read(session_file, {})
            if session_data.get("platform") == platform:
                last_active = session_data.get("last_active", 0)
                if last_active > latest_time:
                    latest_time = last_active
                    session_id = session_data.get("session_id")
                    if session_id:
                        latest_session = session_id
        
        if latest_session:
            return self.get_session(latest_session)
            
        return None

    def list_platform_sessions(
        self, platform: str, limit: int = 10
    ) -> List[SessionInfo]:
        """列出平台的会话历史"""
        mappings = self._load_session_mappings()
        sessions = []

        for session_id, session_data in mappings.get("sessions", {}).items():
            if session_data.get("platform") == platform:
                sessions.append(SessionInfo.from_dict(session_data))

        # 按最后使用时间排序
        sessions.sort(key=lambda s: s.last_used, reverse=True)
        return sessions[:limit]

    def cleanup_old_sessions(self, max_age_days: int = 30) -> int:
        """清理旧会话"""
        cutoff_time = datetime.now() - timedelta(days=max_age_days)
        mappings = self._load_session_mappings()

        sessions_to_remove = []
        for session_id, session_data in mappings.get("sessions", {}).items():
            try:
                last_used = datetime.fromisoformat(session_data["last_used"])
                if last_used < cutoff_time:
                    sessions_to_remove.append(session_id)
            except (KeyError, ValueError):
                # 无效数据也删除
                sessions_to_remove.append(session_id)

        # 删除旧会话
        for session_id in sessions_to_remove:
            del mappings["sessions"][session_id]
            # 清理缓存
            self.cache_manager.delete("session", f"info_{session_id}")

        if sessions_to_remove:
            mappings["last_cleanup"] = datetime.now().isoformat()
            self._save_session_mappings(mappings)
            log_message(
                "session", "INFO", f"Cleaned up {len(sessions_to_remove)} old sessions"
            )

        return len(sessions_to_remove)

    def get_session_stats(self) -> Dict[str, Any]:
        """获取会话统计信息"""
        mappings = self._load_session_mappings()
        sessions = mappings.get("sessions", {})

        # 按平台统计
        platform_counts = {}
        for session_data in sessions.values():
            platform = session_data.get("platform", "unknown")
            platform_counts[platform] = platform_counts.get(platform, 0) + 1

        # 活跃会话统计（24小时内）
        recent_cutoff = datetime.now() - timedelta(hours=24)
        active_sessions = 0

        for session_data in sessions.values():
            try:
                last_used = datetime.fromisoformat(session_data.get("last_used", ""))
                if last_used > recent_cutoff:
                    active_sessions += 1
            except (ValueError, TypeError):
                pass

        return {
            "total_sessions": len(sessions),
            "platform_counts": platform_counts,
            "active_sessions_24h": active_sessions,
            "mappings_file": str(self.session_mappings_file),
            "last_cleanup": mappings.get("last_cleanup"),
            "supported_platforms": list(self.PLATFORM_PREFIXES.keys()),
        }

    def _generate_session_id(self, platform: str) -> str:
        """生成平台特定的session ID"""
        # 生成标准UUID
        base_uuid = str(uuid.uuid4())

        # 获取平台前缀
        platform_prefix = self.PLATFORM_PREFIXES.get(platform, "01")

        # 创建带前缀的UUID
        prefixed_uuid = f"{platform_prefix}{base_uuid[2:]}"

        return prefixed_uuid

    def _save_session(self, session: SessionInfo) -> bool:
        """保存会话信息（使用SessionMappingV2格式）"""
        import time
        
        # 使用SessionMappingV2的目录结构
        session_file = self._get_session_file_path(session.session_id)
        
        # SessionMappingV2兼容的数据格式
        session_data = {
            "platform": session.platform,
            "session_id": session.session_id,
            "created_at": session.created_at.timestamp(),
            "updated_at": session.last_used.timestamp(),
            "last_active": time.time(),
            "metadata": session.metadata,
            "session_info": session.to_dict()  # 包含完整的session信息
        }
        
        # 保存到独立文件
        success = safe_json_write(session_file, session_data)
        
        # 如果是带前缀的UUID，也为标准UUID创建文件
        if session.is_prefixed_uuid and success:
            standard_session_file = self._get_session_file_path(session.standard_uuid)
            safe_json_write(standard_session_file, session_data)
            
        if success:
            # 禁用cache系统以避免重复存储
            # self.cache_manager.set("session", f"info_{session.session_id}", session.to_dict(), 3600)
            log_message(
                "session",
                "DEBUG", 
                f"Session saved to SessionMappingV2 format: {session.session_id[:8]}...",
                {"file": str(session_file)}
            )

        return success

    def _load_session_mappings(self) -> Dict[str, Any]:
        """加载会话映射数据"""
        if not self.session_mappings_file.exists():
            return {
                "version": "2.0",
                "created": datetime.now().isoformat(),
                "sessions": {},
                "platforms": {},
            }

        mappings = safe_json_read(self.session_mappings_file, {})
        if not mappings:
            return {
                "version": "2.0",
                "created": datetime.now().isoformat(),
                "sessions": {},
                "platforms": {},
            }

        return mappings

    def _save_session_mappings(self, mappings: Dict[str, Any]) -> bool:
        """保存会话映射数据"""
        mappings["last_updated"] = datetime.now().isoformat()
        return safe_json_write(self.session_mappings_file, mappings)

    def create_dual_uuid_mapping(self, platform: str) -> Tuple[str, str]:
        """创建双UUID映射（向后兼容）"""
        session = self.create_session(platform)

        prefixed_uuid = session.prefixed_uuid
        standard_uuid = session.standard_uuid

        log_message(
            "session",
            "INFO",
            f"Created dual UUID mapping: {prefixed_uuid} <-> {standard_uuid} -> {platform}",
        )

        return prefixed_uuid, standard_uuid


# 全局会话管理器实例
_session_manager: Optional[UnifiedSessionManager] = None


def get_session_manager() -> UnifiedSessionManager:
    """获取全局会话管理器实例"""
    global _session_manager
    if _session_manager is None:
        _session_manager = UnifiedSessionManager()
    return _session_manager


# 便捷函数
def create_session_for_platform(
    platform: str, continue_session: bool = False
) -> SessionInfo:
    """便捷函数：为指定平台创建或继续会话"""
    return get_session_manager().create_session(platform, continue_session)


def detect_platform_from_session_id(session_id: str) -> Optional[str]:
    """便捷函数：从session ID检测平台"""
    return get_session_manager().detect_platform_from_session_id(session_id)


def get_session_info(session_id: str) -> Optional[SessionInfo]:
    """便捷函数：获取会话信息"""
    return get_session_manager().get_session(session_id)


# 此模块为纯库文件，专注于会话管理功能
# 按照配置驱动架构设计，不提供命令行接口
# 用户通过修改配置文件和启动脚本管理会话，通过Python接口使用会话功能
