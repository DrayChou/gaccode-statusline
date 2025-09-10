#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cross-process API request locking
跨进程API请求锁定 - 防止多个Claude实例并发API调用导致封号
"""

import time
import hashlib
from pathlib import Path
from contextlib import contextmanager
from typing import Optional, Dict, Any

try:
    from .file_lock import safe_file_lock, safe_json_write, safe_json_read
    from .logger import log_message
except ImportError:
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from file_lock import safe_file_lock, safe_json_write, safe_json_read
    from logger import log_message


class APILockManager:
    """API请求锁管理器 - 优化版，减少磁盘I/O"""
    
    def __init__(self, cache_dir: Optional[Path] = None):
        """初始化API锁管理器"""
        self.cache_dir = cache_dir or Path(__file__).parent / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.lock_dir = self.cache_dir / "api_locks"
        self.lock_dir.mkdir(parents=True, exist_ok=True)
        
        # 内存锁缓存，减少文件I/O
        self._memory_locks = {}
        self._memory_lock_timeout = 10  # 内存锁10秒过期
        
        # 默认API调用间隔配置
        self.default_intervals = {
            'gaccode': 60.0,      # GAC Code: 60秒（严格要求）
            'kimi': 30.0,         # Kimi: 30秒（保守策略）
            'deepseek': 30.0,     # DeepSeek: 30秒
            'siliconflow': 30.0,  # SiliconFlow: 30秒
            'default': 30.0       # 默认30秒
        }
    
    def _get_lock_file(self, platform: str, endpoint: str) -> Path:
        """获取特定平台和端点的锁文件路径"""
        # 使用平台名和端点生成唯一锁文件
        lock_key = f"{platform}_{endpoint}".replace("/", "_").replace(":", "_")
        return self.lock_dir / f"api_lock_{lock_key}.json"
    
    def _get_min_interval(self, platform: str) -> float:
        """获取平台的最小请求间隔"""
        return self.default_intervals.get(platform, self.default_intervals['default'])
    
    @contextmanager
    def api_request_lock(self, platform: str, endpoint: str, min_interval: Optional[float] = None):
        """
        API请求锁上下文管理器
        
        Args:
            platform: 平台名称
            endpoint: API端点
            min_interval: 最小请求间隔（秒），None则使用默认值
        
        Yields:
            bool: 是否可以执行API请求
        """
        lock_file = self._get_lock_file(platform, endpoint)
        interval = min_interval or self._get_min_interval(platform)
        
        log_message(
            "api-lock",
            "DEBUG",
            f"Checking API lock for {platform} {endpoint}",
            {
                "platform": platform,
                "endpoint": endpoint,
                "lock_file": str(lock_file),
                "min_interval": interval
            }
        )
        
        try:
            # 读取上次请求时间
            lock_data = safe_json_read(lock_file, {})
            last_request_time = lock_data.get('last_request_time', 0)
            current_time = time.time()
            elapsed = current_time - last_request_time
            
            log_message(
                "api-lock",
                "DEBUG",
                f"API rate limit check for {platform}",
                {
                    "platform": platform,
                    "endpoint": endpoint,
                    "elapsed_seconds": round(elapsed, 2),
                    "min_interval": interval,
                    "can_proceed": elapsed >= interval
                }
            )
            
            if elapsed < interval:
                # 需要等待
                wait_time = interval - elapsed
                log_message(
                    "api-lock",
                    "INFO",
                    f"API rate limit: waiting {wait_time:.1f}s for {platform}",
                    {
                        "platform": platform,
                        "endpoint": endpoint,
                        "wait_seconds": round(wait_time, 1),
                        "reason": "rate_limiting"
                    }
                )
                yield False  # 表示需要等待，不应执行API请求
                return
            
            # 可以执行请求，更新锁文件
            new_lock_data = {
                'last_request_time': current_time,
                'platform': platform,
                'endpoint': endpoint,
                'min_interval': interval,
                'updated_at': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            if safe_json_write(lock_file, new_lock_data):
                log_message(
                    "api-lock",
                    "DEBUG",
                    f"API lock updated for {platform}",
                    {
                        "platform": platform,
                        "endpoint": endpoint,
                        "next_allowed_time": time.strftime('%H:%M:%S', time.localtime(current_time + interval))
                    }
                )
                yield True  # 可以执行API请求
            else:
                log_message(
                    "api-lock",
                    "ERROR",
                    f"Failed to update API lock for {platform}",
                    {"platform": platform, "endpoint": endpoint}
                )
                yield False
                
        except Exception as e:
            log_message(
                "api-lock",
                "ERROR",
                f"API lock error for {platform}: {e}",
                {
                    "platform": platform,
                    "endpoint": endpoint,
                    "error": str(e),
                    "error_type": type(e).__name__
                }
            )
            # 出错时允许请求（降级处理）
            yield True
    
    def cleanup_old_locks(self, max_age_hours: int = 24):
        """清理过期的锁文件"""
        current_time = time.time()
        cleaned_count = 0
        
        for lock_file in self.lock_dir.glob("api_lock_*.json"):
            try:
                # 检查文件修改时间
                file_age = current_time - lock_file.stat().st_mtime
                if file_age > max_age_hours * 3600:
                    lock_file.unlink()
                    cleaned_count += 1
            except Exception as e:
                log_message(
                    "api-lock",
                    "WARNING",
                    f"Failed to cleanup lock file {lock_file}: {e}"
                )
        
        if cleaned_count > 0:
            log_message(
                "api-lock",
                "INFO",
                f"Cleaned up {cleaned_count} old API lock files"
            )
        
        return cleaned_count
    
    def get_lock_status(self) -> Dict[str, Any]:
        """获取当前锁状态"""
        current_time = time.time()
        locks = {}
        
        for lock_file in self.lock_dir.glob("api_lock_*.json"):
            try:
                lock_data = safe_json_read(lock_file, {})
                if lock_data:
                    platform = lock_data.get('platform', 'unknown')
                    endpoint = lock_data.get('endpoint', 'unknown')
                    last_request = lock_data.get('last_request_time', 0)
                    min_interval = lock_data.get('min_interval', 30)
                    
                    elapsed = current_time - last_request
                    remaining = max(0, min_interval - elapsed)
                    
                    locks[f"{platform}_{endpoint}"] = {
                        'platform': platform,
                        'endpoint': endpoint,
                        'last_request_time': last_request,
                        'elapsed_seconds': round(elapsed, 1),
                        'remaining_seconds': round(remaining, 1),
                        'can_request': elapsed >= min_interval,
                        'min_interval': min_interval
                    }
            except Exception:
                continue
        
        return locks


# 全局API锁管理器实例
_api_lock_manager: Optional[APILockManager] = None

def get_api_lock_manager() -> APILockManager:
    """获取全局API锁管理器实例"""
    global _api_lock_manager
    if _api_lock_manager is None:
        _api_lock_manager = APILockManager()
    return _api_lock_manager


def api_request_lock(platform: str, endpoint: str, min_interval: Optional[float] = None):
    """便捷的API请求锁装饰器/上下文管理器"""
    return get_api_lock_manager().api_request_lock(platform, endpoint, min_interval)


# 此模块为纯库文件，专注于API请求锁定功能
# 按照配置驱动架构设计，不提供命令行接口
# 用户通过Python接口使用API锁定功能