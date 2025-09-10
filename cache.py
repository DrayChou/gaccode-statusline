#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unified Cache Manager
统一缓存管理器 - 整合所有缓存逻辑和策略
"""

import json
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, Union, Callable, TypeVar, Generic
from datetime import datetime, timedelta
from dataclasses import dataclass
import sys
import threading
from contextlib import contextmanager

# Import utilities
try:
    from data.file_lock import safe_json_write, safe_json_read
    from data.logger import log_message
except ImportError:
    # Fallback import for development
    sys.path.insert(0, str(Path(__file__).parent / "data"))
    from file_lock import safe_json_write, safe_json_read
    from logger import log_message

T = TypeVar('T')


@dataclass
class CacheEntry:
    """缓存条目数据结构"""
    data: Any
    cached_at: datetime
    ttl_seconds: int
    
    @property
    def expires_at(self) -> datetime:
        """缓存过期时间"""
        return self.cached_at + timedelta(seconds=self.ttl_seconds)
    
    @property
    def is_expired(self) -> bool:
        """检查是否过期"""
        return datetime.now() > self.expires_at
    
    @property
    def age_seconds(self) -> float:
        """缓存年龄（秒）"""
        return (datetime.now() - self.cached_at).total_seconds()
    
    @property
    def remaining_seconds(self) -> float:
        """剩余有效时间（秒）"""
        return max(0, self.ttl_seconds - self.age_seconds)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'data': self.data,
            'cached_at': self.cached_at.isoformat(),
            'ttl': self.ttl_seconds,
            'expires_at': self.expires_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CacheEntry':
        """从字典创建缓存条目"""
        return cls(
            data=data['data'],
            cached_at=datetime.fromisoformat(data['cached_at']),
            ttl_seconds=data['ttl']
        )


class CacheManager:
    """统一缓存管理器"""
    
    def __init__(self, cache_dir: Optional[Path] = None):
        """初始化缓存管理器"""
        self.cache_dir = cache_dir or Path(__file__).parent / "data" / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # 内存缓存（热缓存）
        self._memory_cache: Dict[str, CacheEntry] = {}
        self._cache_lock = threading.RLock()
        
        # 预定义的缓存策略
        self.cache_strategies = {
            'balance': 300,        # 5分钟 - API余额信息
            'subscription': 3600,  # 1小时 - 订阅信息
            'usage': 600,         # 10分钟 - 使用量统计
            'session': 86400,     # 24小时 - 会话信息
            'config': 1800,       # 30分钟 - 配置信息
            'fast': 60,           # 1分钟 - 快速更新数据
            'slow': 7200,         # 2小时 - 缓慢更新数据
            'persistent': 604800,  # 7天 - 持久化数据
        }
    
    def _generate_cache_key(self, namespace: str, key: str, params: Optional[Dict[str, Any]] = None) -> str:
        """生成缓存键"""
        if params:
            # 对参数进行排序和哈希，确保一致性
            param_str = json.dumps(params, sort_keys=True, separators=(',', ':'))
            param_hash = hashlib.md5(param_str.encode()).hexdigest()[:8]
            return f"{namespace}:{key}:{param_hash}"
        return f"{namespace}:{key}"
    
    def _get_cache_file_path(self, cache_key: str) -> Path:
        """获取缓存文件路径"""
        # 将缓存键转换为安全的文件名
        safe_key = cache_key.replace(':', '_').replace('/', '_')
        return self.cache_dir / f"cache_{safe_key}.json"
    
    @contextmanager
    def _cache_lock_context(self):
        """缓存锁上下文管理器"""
        with self._cache_lock:
            yield
    
    def get(self, namespace: str, key: str, params: Optional[Dict[str, Any]] = None) -> Optional[CacheEntry]:
        """获取缓存条目"""
        cache_key = self._generate_cache_key(namespace, key, params)
        
        with self._cache_lock_context():
            # 先检查内存缓存
            if cache_key in self._memory_cache:
                entry = self._memory_cache[cache_key]
                if not entry.is_expired:
                    return entry
                else:
                    # 清理过期的内存缓存
                    del self._memory_cache[cache_key]
            
            # 检查磁盘缓存
            cache_file = self._get_cache_file_path(cache_key)
            if cache_file.exists():
                try:
                    cache_data = safe_json_read(cache_file)
                    if cache_data:
                        entry = CacheEntry.from_dict(cache_data)
                        if not entry.is_expired:
                            # 将有效数据加载到内存缓存
                            self._memory_cache[cache_key] = entry
                            return entry
                        else:
                            # 删除过期的磁盘缓存
                            cache_file.unlink(missing_ok=True)
                except Exception as e:
                    log_message("cache", "WARNING", f"Failed to read cache file {cache_file}: {e}")
            
            return None
    
    def set(self, namespace: str, key: str, data: Any, ttl_seconds: Optional[int] = None, params: Optional[Dict[str, Any]] = None) -> bool:
        """设置缓存条目"""
        import random
        cache_key = self._generate_cache_key(namespace, key, params)
        
        # 确定TTL，添加随机抖动防止缓存雪崩
        if ttl_seconds is None:
            base_ttl = self.cache_strategies.get(namespace, 300)  # 默认5分钟
        else:
            base_ttl = ttl_seconds
        
        # 添加±10%的随机抖动
        jitter_range = int(base_ttl * 0.1)
        jitter = random.randint(-jitter_range, jitter_range)
        final_ttl = max(60, base_ttl + jitter)  # 最小1分钟TTL
        
        entry = CacheEntry(data=data, cached_at=datetime.now(), ttl_seconds=final_ttl)
        
        with self._cache_lock_context():
            # 保存到内存缓存
            self._memory_cache[cache_key] = entry
            
            # 保存到磁盘缓存
            cache_file = self._get_cache_file_path(cache_key)
            return safe_json_write(cache_file, entry.to_dict())
    
    def delete(self, namespace: str, key: str, params: Optional[Dict[str, Any]] = None) -> bool:
        """删除缓存条目"""
        cache_key = self._generate_cache_key(namespace, key, params)
        
        with self._cache_lock_context():
            # 从内存缓存删除
            if cache_key in self._memory_cache:
                del self._memory_cache[cache_key]
            
            # 从磁盘删除
            cache_file = self._get_cache_file_path(cache_key)
            if cache_file.exists():
                try:
                    cache_file.unlink()
                    return True
                except Exception as e:
                    log_message("cache", "ERROR", f"Failed to delete cache file {cache_file}: {e}")
                    return False
            return True
    
    def clear_namespace(self, namespace: str) -> int:
        """清理命名空间下的所有缓存"""
        cleared_count = 0
        
        with self._cache_lock_context():
            # 清理内存缓存
            keys_to_delete = [key for key in self._memory_cache.keys() if key.startswith(f"{namespace}:")]
            for key in keys_to_delete:
                del self._memory_cache[key]
                cleared_count += 1
            
            # 清理磁盘缓存
            pattern = f"cache_{namespace}_*.json"
            for cache_file in self.cache_dir.glob(pattern):
                try:
                    cache_file.unlink()
                    cleared_count += 1
                except Exception as e:
                    log_message("cache", "WARNING", f"Failed to delete cache file {cache_file}: {e}")
        
        log_message("cache", "INFO", f"Cleared {cleared_count} cache entries from namespace '{namespace}'")
        return cleared_count
    
    def cleanup_expired(self) -> int:
        """清理所有过期缓存"""
        cleaned_count = 0
        
        with self._cache_lock_context():
            # 清理内存缓存
            expired_keys = [key for key, entry in self._memory_cache.items() if entry.is_expired]
            for key in expired_keys:
                del self._memory_cache[key]
                cleaned_count += 1
            
            # 清理磁盘缓存
            for cache_file in self.cache_dir.glob("cache_*.json"):
                try:
                    cache_data = safe_json_read(cache_file)
                    if cache_data:
                        entry = CacheEntry.from_dict(cache_data)
                        if entry.is_expired:
                            cache_file.unlink()
                            cleaned_count += 1
                except Exception:
                    # 删除无法解析的缓存文件
                    cache_file.unlink(missing_ok=True)
                    cleaned_count += 1
        
        if cleaned_count > 0:
            log_message("cache", "INFO", f"Cleaned up {cleaned_count} expired cache entries")
        return cleaned_count
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        with self._cache_lock_context():
            memory_count = len(self._memory_cache)
            disk_count = len(list(self.cache_dir.glob("cache_*.json")))
            
            # 统计各命名空间的缓存数量
            namespace_stats = {}
            for key in self._memory_cache.keys():
                namespace = key.split(':')[0]
                namespace_stats[namespace] = namespace_stats.get(namespace, 0) + 1
            
            return {
                'memory_cache_count': memory_count,
                'disk_cache_count': disk_count,
                'namespace_stats': namespace_stats,
                'cache_dir': str(self.cache_dir),
                'strategies': self.cache_strategies
            }
    
    # 便捷方法
    def cached(self, namespace: str, key: str, ttl_seconds: Optional[int] = None, params: Optional[Dict[str, Any]] = None):
        """缓存装饰器"""
        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            def wrapper(*args, **kwargs) -> T:
                # 尝试从缓存获取
                entry = self.get(namespace, key, params)
                if entry is not None:
                    log_message("cache", "DEBUG", f"Cache hit for {namespace}:{key}")
                    return entry.data
                
                # 缓存未命中，执行函数
                log_message("cache", "DEBUG", f"Cache miss for {namespace}:{key}, executing function")
                result = func(*args, **kwargs)
                
                # 保存到缓存
                self.set(namespace, key, result, ttl_seconds, params)
                return result
            return wrapper
        return decorator
    
    def get_or_set(self, namespace: str, key: str, factory: Callable[[], T], ttl_seconds: Optional[int] = None, params: Optional[Dict[str, Any]] = None) -> T:
        """获取缓存或设置新值"""
        entry = self.get(namespace, key, params)
        if entry is not None:
            return entry.data
        
        # 缓存未命中，使用工厂函数生成数据
        data = factory()
        self.set(namespace, key, data, ttl_seconds, params)
        return data


# 全局缓存管理器实例
_cache_manager: Optional[CacheManager] = None

def get_cache_manager() -> CacheManager:
    """获取全局缓存管理器实例"""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager


# 便捷函数
def cache_get(namespace: str, key: str, params: Optional[Dict[str, Any]] = None) -> Optional[Any]:
    """便捷的缓存获取函数"""
    entry = get_cache_manager().get(namespace, key, params)
    return entry.data if entry else None

def cache_set(namespace: str, key: str, data: Any, ttl_seconds: Optional[int] = None, params: Optional[Dict[str, Any]] = None) -> bool:
    """便捷的缓存设置函数"""
    return get_cache_manager().set(namespace, key, data, ttl_seconds, params)

def cache_delete(namespace: str, key: str, params: Optional[Dict[str, Any]] = None) -> bool:
    """便捷的缓存删除函数"""
    return get_cache_manager().delete(namespace, key, params)

def cache_clear(namespace: str) -> int:
    """便捷的缓存清理函数"""
    return get_cache_manager().clear_namespace(namespace)


# 此模块为纯库文件，专注于缓存管理功能
# 按照配置驱动架构设计，不提供命令行接口
# 用户通过修改配置文件管理缓存策略，通过Python接口使用缓存功能