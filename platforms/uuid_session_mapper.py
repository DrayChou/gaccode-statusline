#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UUID-based session-platform mapping system
基于自定义UUID session-id的精确平台映射
"""

import json
import os
import uuid
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import fcntl


class UUIDSessionMapper:
    """基于自定义UUID session-id的平台映射系统"""

    def __init__(self):
        self.project_dir = Path(__file__).parent.parent
        self.mapping_file = self.project_dir / "uuid-session-mapping.json"
        self.lock_file = self.project_dir / "uuid-mapping.lock"

    def generate_session_uuid(self) -> str:
        """生成新的session UUID"""
        return str(uuid.uuid4())

    def _load_mappings(self) -> Dict[str, Any]:
        """安全加载UUID映射文件"""
        if not self.mapping_file.exists():
            return {"sessions": {}, "created": datetime.now().isoformat()}

        try:
            with open(self.mapping_file, "r", encoding="utf-8-sig") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {"sessions": {}, "created": datetime.now().isoformat()}

    def _save_mappings(self, mappings: Dict[str, Any]) -> bool:
        """安全保存UUID映射文件"""
        try:
            mappings["last_updated"] = datetime.now().isoformat()

            # 原子保存
            temp_file = self.mapping_file.with_suffix(".tmp")
            with open(temp_file, "w", encoding="utf-8-sig") as f:
                json.dump(mappings, f, indent=2, ensure_ascii=False)

            temp_file.replace(self.mapping_file)
            return True
        except Exception:
            return False

    def register_session(
        self,
        session_uuid: str,
        platform_type: str,
        launcher_info: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """注册UUID session和平台的映射关系"""
        try:
            with open(self.lock_file, "w") as lock:
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX)

                mappings = self._load_mappings()

                session_info = {
                    "platform": platform_type,
                    "created_time": datetime.now().isoformat(),
                    "launcher_info": launcher_info or {},
                }

                mappings["sessions"][session_uuid] = session_info

                return self._save_mappings(mappings)

        except (OSError, IOError):
            return False

    def get_platform_by_uuid(self, session_uuid: str) -> Optional[str]:
        """根据UUID获取平台信息"""
        try:
            mappings = self._load_mappings()
            session_info = mappings.get("sessions", {}).get(session_uuid)
            if session_info:
                return session_info.get("platform")
        except Exception:
            pass

        return None

    def get_current_session_platform(self) -> Optional[str]:
        """获取当前session的平台信息"""
        try:
            # 读取当前session信息
            session_info_file = self.project_dir / "data/cache/session-info-cache.json"
            if not session_info_file.exists():
                return None

            with open(session_info_file, "r", encoding="utf-8-sig") as f:
                session_info = json.load(f)
                session_id = session_info.get("session_id")

                if session_id:
                    return self.get_platform_by_uuid(session_id)

        except (json.JSONDecodeError, IOError):
            pass

        return None

    def cleanup_old_sessions(self, max_sessions: int = 100) -> int:
        """清理旧的session映射，保留最新的N个"""
        try:
            with open(self.lock_file, "w") as lock:
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX)

                mappings = self._load_mappings()
                sessions = mappings.get("sessions", {})

                if len(sessions) <= max_sessions:
                    return 0

                # 按创建时间排序，保留最新的sessions
                sorted_sessions = sorted(
                    sessions.items(),
                    key=lambda x: x[1].get("created_time", ""),
                    reverse=True,
                )

                # 保留最新的max_sessions个
                keep_sessions = dict(sorted_sessions[:max_sessions])
                removed_count = len(sessions) - len(keep_sessions)

                mappings["sessions"] = keep_sessions
                self._save_mappings(mappings)

                return removed_count

        except Exception:
            return 0

    def list_active_sessions(self) -> Dict[str, Any]:
        """列出所有活跃的UUID session映射"""
        return self._load_mappings().get("sessions", {})

    def remove_session(self, session_uuid: str) -> bool:
        """移除指定的UUID session映射"""
        try:
            with open(self.lock_file, "w") as lock:
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX)

                mappings = self._load_mappings()
                sessions = mappings.get("sessions", {})

                if session_uuid in sessions:
                    del sessions[session_uuid]
                    mappings["sessions"] = sessions
                    return self._save_mappings(mappings)

        except Exception:
            pass

        return False

    def get_session_info(self, session_uuid: str) -> Optional[Dict[str, Any]]:
        """获取完整的session信息"""
        try:
            mappings = self._load_mappings()
            return mappings.get("sessions", {}).get(session_uuid)
        except Exception:
            return None


def detect_platform_from_uuid_session() -> Optional[str]:
    """便捷函数：从UUID session映射检测平台"""
    mapper = UUIDSessionMapper()
    return mapper.get_current_session_platform()


def get_uuid_session_detection_info() -> Dict[str, Any]:
    """获取UUID session检测的详细信息"""
    mapper = UUIDSessionMapper()

    try:
        session_info_file = mapper.project_dir / "data/cache/session-info-cache.json"
        if session_info_file.exists():
            with open(session_info_file, "r", encoding="utf-8-sig") as f:
                session_info = json.load(f)
                session_id = session_info.get("session_id")

                if session_id:
                    platform = mapper.get_platform_by_uuid(session_id)
                    session_mapping_info = mapper.get_session_info(session_id)

                    return {
                        "session_id": session_id,
                        "platform": platform,
                        "session_mapping_info": session_mapping_info,
                        "confidence": "highest" if platform else "none",
                        "source": "uuid_session_mapping",
                        "is_custom_uuid": len(session_id) == 36
                        and session_id.count("-") == 4,
                    }
    except Exception:
        pass

    return {
        "session_id": None,
        "platform": None,
        "confidence": "none",
        "source": "uuid_session_mapping",
    }
