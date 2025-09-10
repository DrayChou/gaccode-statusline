#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
平台后台任务集成接口 - 将后台任务系统与现有平台代码集成
"""

import json
import time
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime

from .daemon_manager import DaemonManager


class BackgroundTaskIntegration:
    """后台任务集成接口"""

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.task_dir = data_dir / "tasks"
        self.task_dir.mkdir(parents=True, exist_ok=True)
        self.daemon_manager = DaemonManager(data_dir)

    def ensure_background_tasks(self, platform: str, config: Dict[str, Any]) -> bool:
        """确保指定平台的后台任务正在运行"""
        return self.daemon_manager.ensure_daemon_running(platform, config)

    def get_cached_balance_from_background(
        self, platform: str
    ) -> Optional[Dict[str, Any]]:
        """从后台任务缓存获取余额数据（不触发API调用）"""
        cache_file = self.task_dir / f"{platform}_balance_task.json"

        if not cache_file.exists():
            return None

        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                cache_data = json.load(f)

            # 检查缓存时间（10分钟内的数据认为是有效的）
            cached_at_str = cache_data.get("cached_at")
            if cached_at_str:
                cached_at = datetime.fromisoformat(cached_at_str)
                age_seconds = (datetime.now() - cached_at).total_seconds()

                # 如果缓存超过10分钟，返回None让调用者决定如何处理
                if age_seconds > 600:
                    return None

            return cache_data.get("balance_data")

        except Exception:
            return None

    def get_background_task_status(self, platform: str) -> Dict[str, Any]:
        """获取后台任务状态信息"""
        return self.daemon_manager.get_daemon_status(platform)

    def is_background_task_healthy(self, platform: str) -> bool:
        """检查后台任务是否健康运行"""
        status = self.get_background_task_status(platform)
        return status.get("running", False)

    def restart_background_task(self, platform: str, config: Dict[str, Any]) -> bool:
        """重启后台任务"""
        # 先停止
        self.daemon_manager.stop_daemon(platform)
        time.sleep(2)
        # 再启动
        return self.daemon_manager.start_daemon(platform, config)


class PlatformBackgroundMixin:
    """平台基类的混入类，提供后台任务集成功能"""

    def __init_background_integration(self, data_dir: Path):
        """初始化后台任务集成（在平台__init__中调用）"""
        self._background_integration = BackgroundTaskIntegration(data_dir)
        self._background_enabled = True
        self._background_initialized = False

    def _ensure_background_tasks(self) -> bool:
        """确保后台任务正在运行"""
        if not hasattr(self, "_background_integration"):
            return False

        if not self._background_enabled:
            return False

        if not self._background_initialized:
            # 准备配置信息
            config = {
                "token": self.token,
                "platform_config": getattr(self, "config", {}),
            }

            # 启动后台任务
            success = self._background_integration.ensure_background_tasks(
                self.name, config
            )
            if success:
                self._background_initialized = True

            return success

        return True

    def _get_background_balance_data(self) -> Optional[Dict[str, Any]]:
        """从后台任务获取余额数据（非阻塞）"""
        if not hasattr(self, "_background_integration"):
            return None

        return self._background_integration.get_cached_balance_from_background(
            self.name
        )

    def _is_background_healthy(self) -> bool:
        """检查后台任务是否健康"""
        if not hasattr(self, "_background_integration"):
            return False

        return self._background_integration.is_background_task_healthy(self.name)

    def _restart_background_if_needed(self) -> bool:
        """如果需要的话重启后台任务"""
        if not hasattr(self, "_background_integration"):
            return False

        if not self._is_background_healthy():
            config = {
                "token": self.token,
                "platform_config": getattr(self, "config", {}),
            }
            return self._background_integration.restart_background_task(
                self.name, config
            )

        return True


def create_background_aware_fetch_balance(original_method):
    """装饰器：为平台的fetch_balance_data方法添加后台任务支持"""

    def wrapper(self):
        # 确保后台任务运行
        if hasattr(self, "_ensure_background_tasks"):
            self._ensure_background_tasks()

        # 尝试从后台任务获取数据
        if hasattr(self, "_get_background_balance_data"):
            background_data = self._get_background_balance_data()
            if background_data:
                return background_data

        # 后台数据不可用，调用原方法
        # 但要注意：如果是因为402错误导致的调用，这里可能仍然会失败
        # 这种情况下，用户需要等待后台任务完成refill
        try:
            return original_method(self)
        except Exception as e:
            # 如果原方法失败，尝试获取过期的缓存数据
            if hasattr(self, "_background_integration"):
                cache_file = (
                    self._background_integration.task_dir
                    / f"{self.name}_balance_task.json"
                )
                if cache_file.exists():
                    try:
                        with open(cache_file, "r", encoding="utf-8") as f:
                            cache_data = json.load(f)
                        expired_data = cache_data.get("balance_data")
                        if expired_data:
                            # 添加过期标记
                            expired_data["_from_expired_cache"] = True
                            return expired_data
                    except Exception:
                        pass

            # 最后的fallback：重新抛出原异常
            raise e

    return wrapper


# 便利函数，用于快速集成到现有平台
def enable_background_tasks_for_platform(platform_instance, data_dir: Path):
    """为现有平台实例启用后台任务支持"""
    # 添加后台集成功能
    platform_instance.__init_background_integration = (
        PlatformBackgroundMixin.__init_background_integration.__get__(platform_instance)
    )
    platform_instance._ensure_background_tasks = (
        PlatformBackgroundMixin._ensure_background_tasks.__get__(platform_instance)
    )
    platform_instance._get_background_balance_data = (
        PlatformBackgroundMixin._get_background_balance_data.__get__(platform_instance)
    )
    platform_instance._is_background_healthy = (
        PlatformBackgroundMixin._is_background_healthy.__get__(platform_instance)
    )
    platform_instance._restart_background_if_needed = (
        PlatformBackgroundMixin._restart_background_if_needed.__get__(platform_instance)
    )

    # 初始化后台集成
    platform_instance.__init_background_integration(data_dir)

    # 包装fetch_balance_data方法
    original_fetch_balance = platform_instance.fetch_balance_data
    platform_instance.fetch_balance_data = create_background_aware_fetch_balance(
        original_fetch_balance
    ).__get__(platform_instance)

    return platform_instance
