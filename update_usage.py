#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
异步更新今日使用量缓存
"""

import json
import subprocess
import sys
import traceback
from datetime import datetime, timedelta
from pathlib import Path

# 获取脚本所在目录
PROJECT_DIR = Path(__file__).parent
DATA_DIR = PROJECT_DIR / "data"
USAGE_CACHE_FILE = DATA_DIR / "cache" / "usage-cache.json"
LOCK_FILE = DATA_DIR / "cache" / "update_usage.lock"

# 确保目录存在
(DATA_DIR / "cache").mkdir(parents=True, exist_ok=True)
(DATA_DIR / "logs").mkdir(parents=True, exist_ok=True)
COOLDOWN_MINUTES = 30


def is_lock_valid():
    """检查锁文件是否有效（存在且未超过冷却时间）"""
    if not LOCK_FILE.exists():
        return False

    try:
        with open(LOCK_FILE, "r", encoding="utf-8-sig") as f:
            lock_time = datetime.fromisoformat(f.read().strip())

        # 如果锁文件超过冷却时间，则视为无效
        if datetime.now() - lock_time > timedelta(minutes=COOLDOWN_MINUTES):
            return False

        return True
    except Exception:
        # 锁文件损坏，视为无效
        return False


def create_lock():
    """创建锁文件"""
    try:
        with open(LOCK_FILE, "w", encoding="utf-8-sig") as f:
            f.write(datetime.now().isoformat())
        return True
    except Exception:
        return False


def remove_lock():
    """删除锁文件"""
    try:
        if LOCK_FILE.exists():
            LOCK_FILE.unlink()
    except Exception:
        pass


def update_usage_cache(today_date):
    """更新使用量缓存"""
    # 检查锁文件
    if is_lock_valid():
        # 记录跳过执行
        log_file = DATA_DIR / "logs" / "update_usage.log"
        with open(log_file, "a", encoding="utf-8-sig") as f:
            f.write(
                f"{datetime.now().isoformat()} - Skipped: Lock file exists and is valid\n"
            )
        return False

    # 创建锁文件
    if not create_lock():
        return False

    try:
        # Windows 上使用 npx.cmd
        cmd = ["npx.cmd", "ccusage", "daily", "--json", "--since", today_date]

        # 记录调试信息
        log_file = DATA_DIR / "logs" / "update_usage.log"
        with open(log_file, "a", encoding="utf-8-sig") as f:
            f.write(f"{datetime.now().isoformat()} - Running: {' '.join(cmd)}\n")

        # 调用 ccusage 获取今日使用量
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            timeout=600,  # 增加到 10 分钟超时
        )

        # 记录输出
        with open(log_file, "a", encoding="utf-8-sig") as f:
            f.write(
                f"{datetime.now().isoformat()} - ccusage output: {result.stdout[:500]}...\n"
            )

        # 解析 JSON 输出
        usage_data = json.loads(result.stdout)

        # 提取今日使用量
        if usage_data and usage_data.get("daily"):
            today_data = usage_data["daily"][0]
            usage = {
                "total_cost": today_data.get("totalCost", 0),
                "input_tokens": today_data.get("inputTokens", 0),
                "output_tokens": today_data.get("outputTokens", 0),
                "total_tokens": today_data.get("totalTokens", 0),
                "date": today_date,
            }

            # 保存到旧缓存文件（向后兼容）
            cache_data = {"timestamp": datetime.now().isoformat(), "usage_data": usage}
            with open(USAGE_CACHE_FILE, "w", encoding="utf-8-sig") as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            
            # 同时更新新缓存系统
            try:
                sys.path.insert(0, str(PROJECT_DIR))
                from cache import get_cache_manager
                cache_manager = get_cache_manager()
                cache_manager.set('usage', f'daily_{today_date}', usage, 600)
            except Exception as cache_error:
                # 新缓存系统失败不影响旧系统
                with open(log_file, "a", encoding="utf-8-sig") as f:
                    f.write(f"{datetime.now().isoformat()} - New cache system failed: {cache_error}\n")

            # 记录成功
            with open(log_file, "a", encoding="utf-8-sig") as f:
                f.write(f"{datetime.now().isoformat()} - Cache updated successfully (both systems)\n")

            return True
        else:
            with open(log_file, "a", encoding="utf-8-sig") as f:
                f.write(f"{datetime.now().isoformat()} - No daily data found\n")
    except Exception as e:
        # 记录详细错误信息到日志文件
        try:
            log_file = DATA_DIR / "logs" / "update_usage.log"
            with open(log_file, "a", encoding="utf-8-sig") as f:
                f.write(f"{datetime.now().isoformat()} - Error: {str(e)}\n")
                f.write(
                    f"{datetime.now().isoformat()} - Traceback: {traceback.format_exc()}\n"
                )
        except Exception:
            pass
        return False
    finally:
        # 无论成功或失败，都删除锁文件
        remove_lock()

    return False


# 此模块为纯库文件，专注于用量更新功能
# 按照配置驱动架构设计，不提供命令行接口
# 由statusline.py自动调用更新用量缓存
