#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cross-platform file locking utility
跨平台文件锁定工具 - 解决多Claude实例并发写入问题
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import Any, Dict, Optional
from contextlib import contextmanager

try:
    # Windows file locking
    import msvcrt
    HAS_MSVCRT = True
except ImportError:
    HAS_MSVCRT = False

try:
    # Unix file locking  
    import fcntl
    HAS_FCNTL = True
except ImportError:
    HAS_FCNTL = False


class FileLockError(Exception):
    """文件锁定异常"""
    pass


@contextmanager
def safe_file_lock(file_path: Path, mode: str = "w", encoding: str = "utf-8-sig", timeout: int = 5):
    """
    安全的文件锁定上下文管理器
    
    Args:
        file_path: 文件路径
        mode: 文件打开模式
        encoding: 文件编码
        timeout: 锁定超时时间（秒）
    
    Yields:
        file: 已锁定的文件对象
    
    Raises:
        FileLockError: 锁定失败或超时
    """
    if not HAS_MSVCRT and not HAS_FCNTL:
        # 如果没有锁定支持，使用普通文件操作但添加重试机制
        yield _fallback_file_operation(file_path, mode, encoding, timeout)
        return
    
    # 确保父目录存在
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    file_obj = None
    lock_acquired = False
    start_time = time.time()
    
    try:
        # 打开文件
        file_obj = open(file_path, mode, encoding=encoding)
        
        # 尝试获取锁
        while time.time() - start_time < timeout:
            try:
                if HAS_MSVCRT and os.name == 'nt':
                    # Windows文件锁定
                    msvcrt.locking(file_obj.fileno(), msvcrt.LK_NBLCK, 1)
                    lock_acquired = True
                    break
                elif HAS_FCNTL:
                    # Unix文件锁定
                    fcntl.flock(file_obj.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    lock_acquired = True
                    break
            except (IOError, OSError):
                # 锁定失败，等待短时间后重试
                time.sleep(0.1)
                continue
        
        if not lock_acquired:
            raise FileLockError(f"Failed to acquire lock on {file_path} within {timeout} seconds")
        
        yield file_obj
        
    finally:
        if file_obj:
            try:
                # 释放锁
                if lock_acquired:
                    if HAS_MSVCRT and os.name == 'nt':
                        msvcrt.locking(file_obj.fileno(), msvcrt.LK_UNLCK, 1)
                    elif HAS_FCNTL:
                        fcntl.flock(file_obj.fileno(), fcntl.LOCK_UN)
            except:
                pass  # 忽略释放锁的错误
            finally:
                file_obj.close()


def _fallback_file_operation(file_path: Path, mode: str, encoding: str, timeout: int):
    """
    备用文件操作（无锁定支持时的重试机制）
    """
    start_time = time.time()
    last_error = None
    
    while time.time() - start_time < timeout:
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            return open(file_path, mode, encoding=encoding)
        except (IOError, OSError) as e:
            last_error = e
            time.sleep(0.1)
            continue
    
    raise FileLockError(f"Failed to open {file_path} within {timeout} seconds: {last_error}")


def safe_json_write(file_path: Path, data: Dict[str, Any], timeout: int = 5) -> bool:
    """
    安全的JSON文件写入（带文件锁定）
    
    Args:
        file_path: 文件路径
        data: 要写入的数据
        timeout: 锁定超时时间
    
    Returns:
        bool: 写入是否成功
    """
    try:
        with safe_file_lock(file_path, "w", "utf-8-sig", timeout) as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        # 导入日志记录函数（避免循环导入）
        try:
            from .logger import log_message
            log_message("file-lock", "ERROR", f"Safe JSON write failed: {e}", {
                "file_path": str(file_path),
                "data_type": type(data).__name__,
                "timeout": timeout
            })
        except ImportError:
            print(f"Safe JSON write failed: {e}", file=sys.stderr)
        return False


def safe_json_read(file_path: Path, default: Optional[Dict[str, Any]] = None, timeout: int = 5) -> Dict[str, Any]:
    """
    安全的JSON文件读取（带重试机制）
    
    Args:
        file_path: 文件路径
        default: 默认值（文件不存在时返回）
        timeout: 读取超时时间
    
    Returns:
        Dict: 读取的数据或默认值
    """
    if not file_path.exists():
        return default or {}
    
    start_time = time.time()
    last_error = None
    
    while time.time() - start_time < timeout:
        try:
            with open(file_path, "r", encoding="utf-8-sig") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            # JSON格式错误，记录日志并返回默认值
            try:
                from .logger import log_message
                log_message("file-lock", "ERROR", f"JSON decode error in {file_path}: {e}")
            except ImportError:
                print(f"JSON decode error in {file_path}: {e}", file=sys.stderr)
            return default or {}
        except (IOError, OSError) as e:
            last_error = e
            time.sleep(0.1)
            continue
    
    # 超时后记录错误
    try:
        from .logger import log_message
        log_message("file-lock", "ERROR", f"Safe JSON read timeout: {last_error}", {
            "file_path": str(file_path),
            "timeout": timeout
        })
    except ImportError:
        print(f"Safe JSON read timeout: {last_error}", file=sys.stderr)
    
    return default or {}


if __name__ == "__main__":
    # 测试文件锁定功能
    test_file = Path("test_lock.json")
    test_data = {"test": "data", "timestamp": time.time()}
    
    print("Testing file locking...")
    
    # 测试写入
    if safe_json_write(test_file, test_data):
        print("[OK] Write test passed")
    else:
        print("[FAIL] Write test failed")
    
    # 测试读取
    read_data = safe_json_read(test_file)
    if read_data.get("test") == "data":
        print("[OK] Read test passed")
    else:
        print("[FAIL] Read test failed")
    
    # 清理测试文件
    try:
        test_file.unlink()
    except:
        pass
    
    print("File locking test completed")