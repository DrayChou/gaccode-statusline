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
    
    def __init__(self, session_id: str, platform: str, created_at: Optional[datetime] = None):
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
        
        platform_prefix = UnifiedSessionManager.PLATFORM_PREFIXES.get(self.platform, "01")
        return f"{platform_prefix}{self.session_id[2:]}"
    
    @property
    def is_prefixed_uuid(self) -> bool:
        """检查是否为带前缀的UUID"""
        if len(self.session_id) != 36:
            return False
        return self.session_id[:2].isalnum() and self.session_id[2] == '-'
    
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
            'session_id': self.session_id,
            'platform': self.platform,
            'created_at': self.created_at.isoformat(),
            'last_used': self.last_used.isoformat(),
            'metadata': self.metadata,
            'standard_uuid': self.standard_uuid,
            'prefixed_uuid': self.prefixed_uuid
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SessionInfo':
        """从字典创建会话信息"""
        session = cls(
            session_id=data['session_id'],
            platform=data['platform'],
            created_at=datetime.fromisoformat(data['created_at'])
        )
        session.last_used = datetime.fromisoformat(data['last_used'])
        session.metadata = data.get('metadata', {})
        return session


class UnifiedSessionManager:
    """统一会话管理器"""
    
    # 平台前缀映射（2位十六进制）
    PLATFORM_PREFIXES = {
        "gaccode": "01",
        "deepseek": "02", 
        "kimi": "03",
        "siliconflow": "04",
        "local_proxy": "05"
    }
    
    # 反向映射：前缀 -> 平台
    PREFIX_TO_PLATFORM = {v: k for k, v in PLATFORM_PREFIXES.items()}
    
    def __init__(self, data_dir: Optional[Path] = None):
        """初始化会话管理器"""
        self.data_dir = data_dir or Path(__file__).parent / "data"
        self.cache_dir = self.data_dir / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # 会话映射文件
        self.session_mappings_file = self.cache_dir / "session-mappings.json"
        
        # 获取依赖
        self.cache_manager = get_cache_manager()
        self.config_manager = get_config_manager()
    
    def detect_platform_from_session_id(self, session_id: str) -> Optional[str]:
        """从session ID检测平台"""
        if not session_id or len(session_id) < 3:
            return None
        
        # 优先级1: UUID前缀检测（最快）
        if len(session_id) == 36 and session_id[2] == '-':
            prefix = session_id[:2].lower()
            platform = self.PREFIX_TO_PLATFORM.get(prefix)
            if platform:
                log_message("session", "DEBUG", f"Platform detected from UUID prefix: {platform}")
                return platform
        
        # 优先级2: Session映射查找
        mappings = self._load_session_mappings()
        session_data = mappings.get("sessions", {}).get(session_id)
        if session_data:
            platform = session_data.get("platform")
            if platform:
                log_message("session", "DEBUG", f"Platform detected from session mapping: {platform}")
                return platform
        
        # 优先级3: 检查标准UUID对应的前缀UUID
        if len(session_id) == 36 and session_id[2] != '-':
            for prefix, platform in self.PREFIX_TO_PLATFORM.items():
                prefixed_uuid = f"{prefix}{session_id[2:]}"
                if prefixed_uuid in mappings.get("sessions", {}):
                    log_message("session", "DEBUG", f"Platform detected from prefixed UUID mapping: {platform}")
                    return platform
        
        log_message("session", "DEBUG", f"No platform detected for session: {session_id[:8]}...")
        return None
    
    def create_session(self, platform: str, continue_session: bool = False) -> SessionInfo:
        """创建新会话或继续现有会话"""
        if continue_session:
            # 尝试继续最近的会话
            last_session = self.get_last_session(platform)
            if last_session:
                last_session.last_used = datetime.now()
                self._save_session(last_session)
                log_message("session", "INFO", f"Continuing session for {platform}: {last_session.session_id}")
                return last_session
        
        # 创建新会话
        session_id = self._generate_session_id(platform)
        session = SessionInfo(session_id, platform)
        
        self._save_session(session)
        log_message("session", "INFO", f"Created new session for {platform}: {session_id}")
        
        return session
    
    def get_session(self, session_id: str) -> Optional[SessionInfo]:
        """获取会话信息"""
        # 尝试从缓存获取
        cache_entry = self.cache_manager.get('session', f'info_{session_id}')
        if cache_entry:
            return SessionInfo.from_dict(cache_entry.data)
        
        # 从映射文件加载
        mappings = self._load_session_mappings()
        session_data = mappings.get("sessions", {}).get(session_id)
        
        if session_data:
            session = SessionInfo.from_dict(session_data)
            # 缓存1小时
            self.cache_manager.set('session', f'info_{session_id}', session.to_dict(), 3600)
            return session
        
        return None
    
    def get_last_session(self, platform: str) -> Optional[SessionInfo]:
        """获取平台最后使用的会话"""
        mappings = self._load_session_mappings()
        platform_data = mappings.get("platforms", {}).get(platform, {})
        last_session_id = platform_data.get("last_session_id")
        
        if last_session_id:
            return self.get_session(last_session_id)
        
        return None
    
    def list_platform_sessions(self, platform: str, limit: int = 10) -> List[SessionInfo]:
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
            self.cache_manager.delete('session', f'info_{session_id}')
        
        if sessions_to_remove:
            mappings["last_cleanup"] = datetime.now().isoformat()
            self._save_session_mappings(mappings)
            log_message("session", "INFO", f"Cleaned up {len(sessions_to_remove)} old sessions")
        
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
            "supported_platforms": list(self.PLATFORM_PREFIXES.keys())
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
        """保存会话信息"""
        mappings = self._load_session_mappings()
        
        # 保存会话数据
        mappings.setdefault("sessions", {})[session.session_id] = session.to_dict()
        
        # 更新平台信息
        platform_data = mappings.setdefault("platforms", {}).setdefault(session.platform, {})
        platform_data["last_session_id"] = session.session_id
        platform_data["last_used"] = session.last_used.isoformat()
        
        # 如果是带前缀的UUID，也创建标准UUID的映射
        if session.is_prefixed_uuid:
            standard_uuid = session.standard_uuid
            mappings["sessions"][standard_uuid] = session.to_dict()
        
        success = self._save_session_mappings(mappings)
        
        if success:
            # 更新缓存
            self.cache_manager.set('session', f'info_{session.session_id}', session.to_dict(), 3600)
            if session.is_prefixed_uuid:
                self.cache_manager.set('session', f'info_{session.standard_uuid}', session.to_dict(), 3600)
        
        return success
    
    def _load_session_mappings(self) -> Dict[str, Any]:
        """加载会话映射数据"""
        if not self.session_mappings_file.exists():
            return {
                "version": "2.0",
                "created": datetime.now().isoformat(),
                "sessions": {},
                "platforms": {}
            }
        
        mappings = safe_json_read(self.session_mappings_file, {})
        if not mappings:
            return {
                "version": "2.0", 
                "created": datetime.now().isoformat(),
                "sessions": {},
                "platforms": {}
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
        
        log_message("session", "INFO", 
                   f"Created dual UUID mapping: {prefixed_uuid} <-> {standard_uuid} -> {platform}")
        
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
def create_session_for_platform(platform: str, continue_session: bool = False) -> SessionInfo:
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