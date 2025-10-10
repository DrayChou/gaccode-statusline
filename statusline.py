#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Claude Code Status Line - GAC API Balance Display
显示 GAC API 余额和订阅信息
"""

import json
import sys
import os
import requests
import subprocess
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from platforms.manager import PlatformManager

# Import logger system and file lock utility
try:
    # Try absolute import first (for Pylance/static analysis)
    from data.logger import log_message
    from data.file_lock import safe_json_write, safe_json_read
    from cache import get_cache_manager
except ImportError:
    # Fallback to sys.path manipulation for runtime
    sys.path.insert(0, str(Path(__file__).parent / "data"))
    from logger import log_message
    from file_lock import safe_json_write, safe_json_read
    sys.path.insert(0, str(Path(__file__).parent))
    from cache import get_cache_manager

# 设置控制台编码
os.environ["PYTHONIOENCODING"] = "utf-8"

# 配置
API_BASE = "https://gaccode.com/api"
PROJECT_DIR = Path(__file__).parent  # scripts/gaccode.com目录
DATA_DIR = PROJECT_DIR / "data"
# TOKEN_FILE 已废弃 - 现在使用平台管理器从配置文件获取tokens
CACHE_FILE = DATA_DIR / "cache" / "statusline-cache.json"
CONFIG_FILE = DATA_DIR / "config" / "statusline-config.json"
SESSION_INFO_FILE = DATA_DIR / "cache" / "session-info-cache.json"
USAGE_CACHE_FILE = DATA_DIR / "cache" / "usage-cache.json"  # 新增：使用量缓存文件

# 确保目录存在
(DATA_DIR / "cache").mkdir(parents=True, exist_ok=True)
(DATA_DIR / "config").mkdir(parents=True, exist_ok=True)
BALANCE_CACHE_TIMEOUT = 60  # 余额缓存60秒
SUBSCRIPTION_CACHE_TIMEOUT = 3600  # 订阅信息缓存1小时
USAGE_CACHE_TIMEOUT = 600  # 使用量缓存10分钟

# 默认显示配置
DEFAULT_CONFIG = {
    "show_model": True,
    "show_directory": True,
    "show_git_branch": True,
    "show_time": True,
    "show_session_duration": False,
    "show_session_cost": True,
    "show_balance": True,
    "show_subscription": True,
    "show_today_usage": True,  # 新增：显示今日使用量
    "directory_full_path": True,
    "layout": "single_line",  # single_line 或 multi_line
    "multiplier_config": {
        "enabled": True,
        "periods": [
            {
                "name": "peak_hour",
                "start_time": "16:30",
                "end_time": "18:30",
                "multiplier": 5,
                "display_text": "5X",
                "weekdays_only": True,  # 仅工作日
                "color": "red",  # 红色显示
            },
            {
                "name": "off_peak",
                "start_time": "01:00",
                "end_time": "10:00",
                "multiplier": 0.8,
                "display_text": "0.8X",
                "weekdays_only": False,  # 所有日期
                "color": "green",  # 绿色显示
            },
        ],
    },
}


def load_config():
    """智能加载显示配置 - 优先使用统一配置管理器"""
    try:
        # 优先使用统一配置管理器
        from config import get_config_manager
        config_manager = get_config_manager()
        
        # 获取状态条配置
        statusline_config = config_manager.get_statusline_settings()
        
        # 获取倍率配置
        multiplier_config = config_manager.get_multiplier_config()
        
        # 合并配置
        result = DEFAULT_CONFIG.copy()
        result.update(statusline_config)
        if multiplier_config:
            result["multiplier_config"] = multiplier_config
            
        log_message(
            "statusline", "INFO", 
            "Configuration loaded from unified config manager",
            {
                "statusline_keys": list(statusline_config.keys()),
                "multiplier_enabled": multiplier_config.get("enabled", False)
            }
        )
        
        return result
        
    except Exception as e:
        log_message(
            "statusline", "WARNING", 
            f"Failed to load from unified config manager: {e}, falling back to legacy method"
        )
        
        # 回退到传统配置加载
        return load_legacy_config()


def load_legacy_config():
    """传统配置加载方法（回退方案）"""
    if not CONFIG_FILE.exists():
        log_message(
            "statusline",
            "DEBUG",
            "Config file not found, using default config",
            {"file": str(CONFIG_FILE)},
        )
        return DEFAULT_CONFIG

    try:
        config = safe_json_read(CONFIG_FILE, DEFAULT_CONFIG)
        if config:
            # 合并默认配置，确保所有选项都存在
            result = DEFAULT_CONFIG.copy()
            result.update(config)
            log_message("statusline", "DEBUG", "Legacy config loaded successfully")
            return result
        else:
            log_message(
                "statusline", "WARNING", "Config file empty or invalid, using defaults"
            )
            return DEFAULT_CONFIG
    except Exception as e:
        log_message(
            "statusline",
            "ERROR",
            f"Failed to load legacy config: {e}",
            {"file": str(CONFIG_FILE)},
        )
        return DEFAULT_CONFIG


# load_token() 函数已废弃 - 现在使用平台管理器获取tokens


def get_session_info():
    """获取Claude Code传入的session信息"""
    try:
        stdin_content = sys.stdin.read()
        if not stdin_content.strip():
            log_message("statusline", "WARNING", "Empty stdin content")
            return {}

        session_data = json.loads(stdin_content)
        log_message(
            "statusline",
            "DEBUG",
            "Session info parsed successfully",
            {
                "has_session_id": bool(session_data.get("session_id")),
                "has_model": bool(session_data.get("model")),
                "has_workspace": bool(session_data.get("workspace")),
            },
        )

        # 缓存session信息到本地文件
        cache_session_info(session_data)
        return session_data
    except json.JSONDecodeError as e:
        log_message("statusline", "ERROR", f"JSON decode error in session info: {e}")
        return {}
    except Exception as e:
        log_message("statusline", "ERROR", f"Failed to get session info: {e}")
        return {}


def cache_session_info(session_data):
    """缓存session信息到本地文件（双层存储架构）"""
    try:
        session_id = session_data.get("session_id")
        
        # 1. 更新"当前活跃session"标识文件（保持向后兼容）
        success_current = safe_json_write(SESSION_INFO_FILE, session_data)
        if success_current:
            log_message("statusline", "DEBUG", "Current session info cached successfully")
        else:
            log_message("statusline", "WARNING", "Failed to cache current session info")
        
        # 2. 更新sessions目录中的详细信息（多实例支持）
        if session_id:
            try:
                from data.session_mapping_v2 import update_session_info, get_session_platform, detect_platform_from_session_id
                
                # 尝试获取已知平台或检测平台
                platform = get_session_platform(session_id)
                if not platform:
                    platform = detect_platform_from_session_id(session_id)
                if not platform:
                    # 使用配置的默认平台，而不是硬编码gaccode
                    try:
                        from config import get_config_manager
                        config_manager = get_config_manager()
                        platform = config_manager.get_effective_platform()
                    except Exception as e:
                        log_message(
                            "statusline", "WARNING",
                            f"Failed to get effective platform, using fallback: {e}"
                        )
                        platform = "gaccode"  # 最后的兜底
                
                # 更新详细session信息
                success_detailed = update_session_info(session_id, session_data, platform)
                if success_detailed:
                    log_message(
                        "statusline", 
                        "DEBUG", 
                        f"Detailed session info updated for {platform}",
                        {"session_id": session_id[:8] + "...", "platform": platform}
                    )
                else:
                    log_message(
                        "statusline", 
                        "WARNING", 
                        f"Failed to update detailed session info",
                        {"session_id": session_id[:8] + "..."}
                    )
                    
            except Exception as e:
                log_message(
                    "statusline", 
                    "ERROR", 
                    f"Failed to update detailed session info: {e}",
                    {"session_id": session_id[:8] + "..." if session_id else "unknown"}
                )
        else:
            log_message("statusline", "WARNING", "No session_id found in session data")
            
    except Exception as e:
        # 缓存失败不影响主要功能，记录日志但不抛出异常
        log_message("statusline", "ERROR", f"Session cache error: {e}")


def is_claude_model(session_info):
    """检查是否使用Claude模型"""
    try:
        model_id = session_info.get("model", {}).get("id", "")
        return model_id.startswith("claude-")
    except:
        return False


def get_git_info(directory):
    """获取Git分支信息"""
    try:
        if not directory or not Path(directory).exists():
            return None

        # 切换到项目目录
        original_cwd = os.getcwd()
        os.chdir(directory)

        try:
            # 检查是否在Git仓库中
            subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                capture_output=True,
                check=True,
            )

            # 获取当前分支
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True,
                text=True,
                check=True,
            )
            branch = result.stdout.strip()

            # 检查是否有未提交的更改
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                check=True,
            )
            is_dirty = bool(result.stdout.strip())

            return {"branch": branch or "detached", "is_dirty": is_dirty}
        finally:
            os.chdir(original_cwd)

    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def get_current_time():
    """获取当前时间"""
    return datetime.now().strftime("%H:%M:%S")


def get_current_period(config):
    """检查当前时间是否在任何特殊倍率时段内"""
    multiplier_config = config.get("multiplier_config", {})

    # 如果功能未启用，返回None
    if not multiplier_config.get("enabled", True):
        return None

    now = datetime.now()
    current_time = now.time()
    current_weekday = now.weekday()  # 0=周一, 6=周日
    is_weekday = current_weekday < 5  # 周一到周五为工作日

    periods = multiplier_config.get("periods", [])

    # 遍历所有时段配置
    for period in periods:
        try:
            # 检查工作日限制
            if period.get("weekdays_only", False) and not is_weekday:
                continue

            # 从配置中获取时间段
            start_time_str = period.get("start_time", "00:00")
            end_time_str = period.get("end_time", "23:59")

            start_time = datetime.strptime(start_time_str, "%H:%M").time()
            end_time = datetime.strptime(end_time_str, "%H:%M").time()

            # 检查是否在时间段内
            if start_time <= current_time <= end_time:
                return period
        except Exception:
            # 如果解析时间失败，跳过这个时段
            continue

    return None


def get_color_by_name(color_name):
    """根据颜色名称获取ANSI颜色代码"""
    color_map = {
        "red": "\033[91m",  # 红色
        "green": "\033[92m",  # 绿色
        "yellow": "\033[93m",  # 黄色
        "blue": "\033[94m",  # 蓝色
        "magenta": "\033[95m",  # 洋红色
        "cyan": "\033[96m",  # 青色
        "white": "\033[97m",  # 白色
        "grey": "\033[90m",  # 灰色
    }
    return color_map.get(color_name, "\033[91m")  # 默认红色


def get_multiplier_info(config):
    """获取积分消耗倍数信息"""
    current_period = get_current_period(config)

    if current_period:
        multiplier = current_period.get("multiplier", 1)
        display_text = current_period.get("display_text", f"{multiplier}X")
        color_name = current_period.get("color", "red")
        color_code = get_color_by_name(color_name)

        return {
            "active": True,
            "multiplier": multiplier,
            "color": color_code,
            "display": display_text,
            "period_name": current_period.get("name", "unknown"),
        }

    return {
        "active": False,
        "multiplier": 1,
        "color": "",
        "display": "",
        "period_name": "normal",
    }


def calculate_session_duration(session_info):
    """计算会话时长"""
    try:
        # 使用简单的session时长估算
        # 实际实现可以基于session_info中的时间戳
        session_id = session_info.get("session_id", "")
        if session_id:
            # 这里可以实现基于session_id的时长计算
            # 如果无法获取真实数据，返回None而不是模拟数据
            return None
        return None
    except:
        return None


def format_session_cost(session_info):
    """格式化Session成本信息"""
    try:
        # 从session信息中提取成本信息
        cost_info = session_info.get("cost", {})
        if cost_info:
            total_cost = cost_info.get("total_cost_usd", 0)
            return f"${total_cost:.2f}"

        # 如果没有具体的成本信息，不显示
        return None
    except Exception:
        return None


def check_npx_available():
    """检查 npx 是否可用"""
    try:
        # Windows 上使用 npx.cmd
        subprocess.run(
            ["npx.cmd", "--version"], capture_output=True, check=True, timeout=10
        )
        return True
    except (
        subprocess.CalledProcessError,
        FileNotFoundError,
        subprocess.TimeoutExpired,
    ):
        return False


def _cleanup_old_usage_caches():
    """清理过期的使用量缓存文件"""
    try:
        cache_dir = DATA_DIR / "cache"
        if not cache_dir.exists():
            return
            
        today = datetime.now().strftime("%Y%m%d")
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
        
        # 删除超过2天的缓存文件（保留今天和昨天）
        for cache_file in cache_dir.glob("cache_usage_daily_*.json"):
            try:
                # 从文件名提取日期：cache_usage_daily_20250908.json
                filename = cache_file.name
                if filename.startswith("cache_usage_daily_") and filename.endswith(".json"):
                    date_str = filename[18:26]  # 提取 YYYYMMDD 部分
                    if date_str not in [today, yesterday]:
                        cache_file.unlink()
                        log_message("statusline", f"Cleaned up old usage cache: {filename}")
            except Exception:
                # 如果处理单个文件失败，继续处理其他文件
                continue
    except Exception:
        # 清理失败不影响主要功能
        pass


def get_today_usage():
    """获取今日使用量"""
    cache_manager = get_cache_manager()
    today = datetime.now().strftime("%Y%m%d")
    
    # 清理过期的缓存文件（保持缓存目录清洁）
    _cleanup_old_usage_caches()
    
    # 尝试从新缓存系统获取今日数据
    cache_entry = cache_manager.get('usage', f'daily_{today}')
    if cache_entry is not None:
        return cache_entry.data

    # 如果 npx 不可用，直接返回 None
    if not check_npx_available():
        return None

    try:
        # 异步更新缓存 - 不等待结果，直接返回当前缓存或 None
        # 直接调用库函数而不是启动子进程（更高效、更可靠）
        from update_usage import update_usage_cache
        import threading
        
        def async_update():
            try:
                update_usage_cache(today)
            except Exception:
                pass
        
        # 在后台线程中执行更新
        threading.Thread(target=async_update, daemon=True).start()
    except Exception:
        pass

    # 尝试从旧缓存文件获取数据（向后兼容，但必须验证是今天的数据）
    if USAGE_CACHE_FILE.exists():
        try:
            with open(USAGE_CACHE_FILE, "r", encoding="utf-8-sig") as f:
                cache_data = json.load(f)
                usage_data = cache_data.get("usage_data")
                if usage_data and usage_data.get("date") == today:
                    # 只有当数据确实是今天的时候才使用
                    # 迁移到新缓存系统
                    cache_manager.set('usage', f'daily_{today}', usage_data, 600)
                    return usage_data
        except Exception:
            pass

    return None


def load_cache():
    """加载缓存数据"""
    if not CACHE_FILE.exists():
        log_message(
            "statusline", "DEBUG", "Cache file not found", {"file": str(CACHE_FILE)}
        )
        return {"balance": None, "subscriptions": None}

    try:
        cache = safe_json_read(CACHE_FILE, {})
        if not cache:
            log_message("statusline", "DEBUG", "Empty cache file")
            return {"balance": None, "subscriptions": None}

        result = {"balance": None, "subscriptions": None}
        current_time = datetime.now()

        # 检查余额缓存
        if cache.get("balance_timestamp"):
            try:
                balance_time = datetime.fromisoformat(cache["balance_timestamp"])
                cache_age = (current_time - balance_time).total_seconds()
                if cache_age <= BALANCE_CACHE_TIMEOUT:
                    result["balance"] = cache.get("balance_data")
                    log_message(
                        "statusline",
                        "DEBUG",
                        f"Using balance cache, age: {cache_age:.1f}s",
                    )
            except ValueError as e:
                log_message("statusline", "WARNING", f"Invalid balance timestamp: {e}")

        # 检查订阅缓存
        if cache.get("subscription_timestamp"):
            try:
                sub_time = datetime.fromisoformat(cache["subscription_timestamp"])
                cache_age = (current_time - sub_time).total_seconds()
                if cache_age <= SUBSCRIPTION_CACHE_TIMEOUT:
                    result["subscriptions"] = cache.get("subscription_data")
                    log_message(
                        "statusline",
                        "DEBUG",
                        f"Using subscription cache, age: {cache_age:.1f}s",
                    )
            except ValueError as e:
                log_message(
                    "statusline", "WARNING", f"Invalid subscription timestamp: {e}"
                )

        return result
    except Exception as e:
        log_message("statusline", "ERROR", f"Failed to load cache: {e}")
        return {"balance": None, "subscriptions": None}


def load_platform_config():
    """加载平台配置文件"""
    platform_config_file = DATA_DIR / "config" / "config.json"

    if not platform_config_file.exists():
        log_message(
            "statusline",
            "WARNING",
            "Platform config file not found",
            {"file": str(platform_config_file)},
        )
        return {}

    try:
        config_data = safe_json_read(platform_config_file, {})
        if config_data:
            log_message(
                "statusline",
                "DEBUG",
                "Platform config loaded successfully",
                {
                    "platforms_count": len(config_data.get("platforms", {})),
                    "has_aliases": bool(config_data.get("aliases")),
                    "has_settings": bool(config_data.get("settings")),
                },
            )
        else:
            log_message(
                "statusline", "WARNING", "Platform config file empty or invalid"
            )

        return config_data
    except Exception as e:
        log_message(
            "statusline", "ERROR", "Failed to load platform config", {"error": str(e)}
        )
        return {}


def load_platform_cache(platform_name):
    """加载特定平台的缓存数据"""
    from datetime import datetime, timedelta
    cache_manager = get_cache_manager()
    result = {"balance": None, "subscriptions": None}
    
    # 获取余额缓存（TTL: 5分钟，最大有效期: 24小时）
    balance_entry = cache_manager.get('balance', f'{platform_name}_balance')
    if balance_entry:
        # 使用缓存条目的内置年龄检查，避免重复计算
        cache_age_hours = balance_entry.age_seconds / 3600
        max_cache_age_hours = 24  # 最大缓存24小时
        
        if cache_age_hours <= max_cache_age_hours:
            result["balance"] = balance_entry.data
            log_message(
                "statusline",
                "DEBUG", 
                f"Using {platform_name} balance cache",
                {
                    "remaining_seconds": balance_entry.remaining_seconds,
                    "cache_age_hours": round(cache_age_hours, 2),
                    "max_age_hours": max_cache_age_hours
                }
            )
        else:
            log_message(
                "statusline",
                "WARNING", 
                f"{platform_name} balance cache expired (too old)",
                {
                    "cache_age_hours": round(cache_age_hours, 2),
                    "max_age_hours": max_cache_age_hours,
                    "action": "cache_invalidated"
                }
            )
            # 删除过期缓存
            cache_manager.delete('balance', f'{platform_name}_balance')
    
    # 获取订阅缓存（TTL: 1小时）
    subscription_entry = cache_manager.get('subscription', f'{platform_name}_subscription')
    if subscription_entry:
        result["subscriptions"] = subscription_entry.data
        log_message(
            "statusline",
            "DEBUG",
            f"Using {platform_name} subscription cache",
            {"remaining_seconds": subscription_entry.remaining_seconds}
        )
    
    return result


def save_platform_cache(platform_name, balance_data=None, subscription_data=None):
    """保存特定平台的缓存数据（使用统一缓存）"""
    cache_manager = get_cache_manager()
    
    try:
        # 保存余额数据（TTL: 5分钟）
        if balance_data is not None:
            success = cache_manager.set('balance', f'{platform_name}_balance', balance_data, 300)
            if success:
                log_message("statusline", "DEBUG", f"Updated {platform_name} balance cache")
            else:
                log_message("statusline", "ERROR", f"Failed to save {platform_name} balance cache")

        # 保存订阅数据（TTL: 1小时）
        if subscription_data is not None:
            success = cache_manager.set('subscription', f'{platform_name}_subscription', subscription_data, 3600)
            if success:
                log_message("statusline", "DEBUG", f"Updated {platform_name} subscription cache")
            else:
                log_message("statusline", "ERROR", f"Failed to save {platform_name} subscription cache")
    except Exception as e:
        log_message(
            "statusline",
            "ERROR",
            f"Failed to save {platform_name} cache",
            {"error": str(e)},
        )


def save_cache(balance_data=None, subscription_data=None):
    """保存缓存数据（带文件锁定）"""
    try:
        # 读取现有缓存
        existing_cache = safe_json_read(CACHE_FILE, {})
        current_time = datetime.now().isoformat()

        # 更新余额数据
        if balance_data is not None:
            existing_cache["balance_data"] = balance_data
            existing_cache["balance_timestamp"] = current_time
            log_message("statusline", "DEBUG", "Updating balance cache")

        # 更新订阅数据
        if subscription_data is not None:
            existing_cache["subscription_data"] = subscription_data
            existing_cache["subscription_timestamp"] = current_time
            log_message("statusline", "DEBUG", "Updating subscription cache")

        # 安全保存缓存（带锁定）
        success = safe_json_write(CACHE_FILE, existing_cache)
        if not success:
            log_message("statusline", "ERROR", "Failed to write cache file")
    except Exception as e:
        log_message("statusline", "ERROR", f"Failed to save cache: {e}")


# fetch_balance_data() 和 fetch_subscription_data() 已废弃
# 现在使用各平台类的 fetch_balance_data() 和 fetch_subscription_data() 方法


def format_date(date_str):
    """格式化日期"""
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return dt.strftime("%m-%d")
    except:
        return date_str


def calculate_days_left(end_date_str):
    """计算剩余天数"""
    try:
        end_date = datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        days_left = (end_date - now).days
        return max(0, days_left)
    except:
        return 0


def calculate_next_refill_time(last_refill_str, refill_rate):
    """计算下一次刷新时间"""
    try:
        # 解析带时区的时间戳
        if last_refill_str.endswith("Z"):
            # UTC时间
            last_refill = datetime.fromisoformat(last_refill_str.replace("Z", "+00:00"))
        else:
            # 已有时区信息
            last_refill = datetime.fromisoformat(last_refill_str)

        # 获取当前UTC时间
        now = datetime.now(timezone.utc)

        # 计算下一次刷新时间：上次刷新时间 + 1小时
        next_refill_time = last_refill + timedelta(hours=1)

        # 计算剩余时间
        remaining_seconds = (next_refill_time - now).total_seconds()

        # 如果已经过了刷新时间，说明还没有开始新的周期
        if remaining_seconds < 0:
            # 计算过了多久
            overdue_seconds = abs(remaining_seconds)
            overdue_hours = int(overdue_seconds // 3600)
            overdue_minutes = int((overdue_seconds % 3600) // 60)

            if overdue_hours > 0:
                return f"overdue {overdue_hours}h{overdue_minutes}m"
            elif overdue_minutes > 0:
                return f"overdue {overdue_minutes}m"
            else:
                return "refreshing soon"

        # 转换为时分秒
        remaining_hours = int(remaining_seconds // 3600)
        remaining_minutes = int((remaining_seconds % 3600) // 60)
        remaining_seconds = int(remaining_seconds % 60)

        # 如果剩余时间不足1分钟，显示秒数
        if remaining_hours == 0 and remaining_minutes == 0:
            return f"{remaining_seconds}s"
        # 如果剩余时间不足1小时，显示分钟和秒数
        elif remaining_hours == 0:
            return f"{remaining_minutes}m{remaining_seconds}s"
        # 否则显示小时和分钟
        else:
            return f"{remaining_hours}h{remaining_minutes}m"
    except Exception as e:
        # 调试信息
        return "未知"


def get_color_code(value, thresholds):
    """根据阈值获取颜色代码"""
    if value <= thresholds[0]:
        return "\033[91m"  # 红色
    elif value <= thresholds[1]:
        return "\033[93m"  # 黄色
    else:
        return "\033[92m"  # 绿色


def collect_status_data(config, session_info):
    """收集状态显示需要的所有数据"""
    # 提取基本信息
    model_name = session_info.get("model", {}).get("display_name", "Unknown")
    current_dir = session_info.get("workspace", {}).get("current_dir", "")

    # 根据配置决定显示完整路径还是目录名
    if config["directory_full_path"]:
        dir_display = current_dir if current_dir else "Unknown"
    else:
        dir_display = Path(current_dir).name if current_dir else "Unknown"

    # 获取Git信息
    git_info = get_git_info(current_dir)

    # 获取时间信息
    current_time = get_current_time()
    session_duration = calculate_session_duration(session_info)
    
    return {
        'model_name': model_name,
        'current_dir': current_dir,
        'dir_display': dir_display,
        'git_info': git_info,
        'current_time': current_time,
        'session_duration': session_duration
    }

def get_color_scheme():
    """定义颜色方案"""
    return {
        'reset': "\033[0m",
        'green': "\033[32m",   # 模型
        'cyan': "\033[36m",    # 目录
        'yellow': "\033[33m",  # Git分支
        'purple': "\033[35m",  # 时间
        'blue': "\033[34m",    # 会话时长
        'magenta': "\033[95m"  # Session成本
    }

def format_basic_status(config, data, colors):
    """格式化基础状态信息（模型、时间、会话时长等）"""
    status_parts = []
    
    # 1. 模型信息
    if config["show_model"]:
        status_parts.append(f"Model:{colors['green']}{data['model_name']}{colors['reset']}")

    # 2. 当前时间
    if config["show_time"]:
        status_parts.append(f"Time:{colors['purple']}{data['current_time']}{colors['reset']}")

    # 3. 会话时长
    if config["show_session_duration"] and data['session_duration']:
        status_parts.append(f"Duration:{colors['blue']}{data['session_duration']}{colors['reset']}")
        
    return status_parts

def format_session_cost_info(config, session_info, colors):
    """格式化会话成本信息"""
    status_parts = []
    
    # Session成本
    if config["show_session_cost"]:
        session_cost = format_session_cost(session_info)
        if session_cost:
            status_parts.append(f"Cost:{colors['magenta']}{session_cost}{colors['reset']}")
    
    return status_parts


def format_usage_info(config, colors):
    """格式化今日使用量信息"""
    status_parts = []
    
    if config["show_today_usage"]:
        usage_data = get_today_usage()
        if usage_data:
            usage_cost = usage_data.get("total_cost", 0)
            if usage_cost > 0:
                usage_color = get_usage_color(usage_cost)
                status_parts.append(f"Today:{usage_color}${usage_cost:.2f}{colors['reset']}")
    
    return status_parts


def get_usage_color(usage_cost):
    """根据使用量返回对应的颜色代码"""
    if usage_cost >= 300:
        return "\033[38;5;196m"  # 红色 - 不朽 (Exotic)
    elif usage_cost >= 200:
        return "\033[38;5;208m"  # 橙色 - 传说 (Legendary)
    elif usage_cost >= 100:
        return "\033[38;5;128m"  # 紫色 - 神器 (Artifact)
    elif usage_cost >= 50:
        return "\033[38;5;201m"  # 品红 - 史诗 (Epic)
    elif usage_cost >= 20:
        return "\033[38;5;21m"  # 蓝色 - 稀有 (Rare)
    elif usage_cost >= 10:
        return "\033[38;5;117m"  # 浅蓝 - 卓越 (Exceptional)
    elif usage_cost >= 5:
        return "\033[38;5;34m"  # 绿色 - 精良 (Fine)
    elif usage_cost >= 2:
        return "\033[38;5;120m"  # 浅绿 - 优秀 (Uncommon)
    elif usage_cost >= 0.5:
        return "\033[38;5;255m"  # 白色 - 普通 (Common)
    else:
        return "\033[38;5;242m"  # 灰色 - 劣质 (Poor)


def format_secondary_status(config, data, colors):
    """格式化次要状态信息（目录、Git等）"""
    secondary_parts = []
    
    # 目录信息
    if config["show_directory"]:
        secondary_parts.append(f"Dir:{colors['cyan']}{data['dir_display']}{colors['reset']}")

    # Git信息
    if config["show_git_branch"] and data['git_info']:
        branch_text = f"{data['git_info']['branch']}"
        if data['git_info']["is_dirty"]:
            branch_text += "*"  # 标记有未提交更改
        secondary_parts.append(f"Git:{colors['yellow']}{branch_text}{colors['reset']}")
    
    return secondary_parts


def fetch_platform_balance_data(platform, config):
    """获取平台余额数据"""
    if not config["show_balance"]:
        return None
    
    cached = load_platform_cache(platform.name)
    balance_data = cached["balance"]
    
    log_message(
        "statusline",
        "DEBUG",
        f"Cache check for {platform.name}",
        {
            "platform": platform.name,
            "cache_hit": balance_data is not None,
            "cache_data_preview": (
                str(balance_data)[:100] + "..." if balance_data else None
            ),
        },
    )
    
    if balance_data is None:
        log_message(
            "statusline",
            "DEBUG",
            f"Cache miss, fetching balance from {platform.name} API",
            {"platform": platform.name, "reason": "no_cached_data"},
        )
        try:
            balance_data = platform.fetch_balance_data()
            if balance_data:
                log_message(
                    "statusline",
                    "INFO",
                    f"Successfully fetched {platform.name} balance data",
                    {
                        "platform": platform.name,
                        "balance_data_type": type(balance_data).__name__,
                        "balance_data_keys": (
                            list(balance_data.keys())
                            if isinstance(balance_data, dict)
                            else "not_dict"
                        ),
                    },
                )
                save_platform_cache(platform.name, balance_data=balance_data)
            else:
                log_message(
                    "statusline",
                    "WARNING",
                    f"{platform.name} API returned empty balance data",
                    {
                        "platform": platform.name,
                        "possible_causes": [
                            "Invalid API token",
                            "Network connectivity issues",
                            "API server errors",
                            "Rate limiting",
                        ],
                    },
                )
        except Exception as e:
            log_message(
                "statusline",
                "ERROR",
                f"{platform.name} balance API call failed",
                {"error": str(e)},
            )
    
    return balance_data


def fetch_platform_subscription_data(platform, config):
    """获取平台订阅数据"""
    if not config["show_subscription"]:
        return None
    
    cached = load_platform_cache(platform.name)
    subscription_data = cached["subscriptions"]
    
    if subscription_data is None:
        log_message(
            "statusline",
            "DEBUG",
            f"Fetching subscription info from {platform.name} API",
        )
        try:
            subscription_data = platform.fetch_subscription_data()
            if subscription_data:
                log_message(
                    "statusline",
                    "INFO",
                    f"Successfully fetched {platform.name} subscription data",
                )
                save_platform_cache(platform.name, subscription_data=subscription_data)
        except Exception as e:
            log_message(
                "statusline",
                "ERROR",
                f"{platform.name} subscription API call failed",
                {"error": str(e)},
            )
    
    return subscription_data


def ensure_background_tasks(platform):
    """确保平台的后台任务正在运行"""
    try:
        from background.daemon_manager import DaemonManager
        from pathlib import Path
        
        # 获取data目录
        data_dir = Path(__file__).parent / "data"
        daemon_manager = DaemonManager(data_dir)
        
        # 检查后台任务是否运行
        platform_name = platform.name.lower()
        if not daemon_manager.is_daemon_running(platform_name):
            log_message(
                "statusline",
                "INFO", 
                f"Auto-starting background tasks for {platform_name}",
                {"platform": platform_name, "auto_start": True}
            )
            
            # 获取平台配置
            from config import get_config_manager
            config_manager = get_config_manager()
            platform_config = config_manager.get_platform(platform_name)
            
            if platform_config and platform_config.get("enabled"):
                # 准备daemon配置
                daemon_config = {
                    "token": platform_config.get("auth_token") or platform_config.get("api_key") or platform_config.get("login_token"),
                    "platform_config": platform_config,
                    "api_base": platform.api_base,
                    "name": platform.name
                }
                
                # 启动daemon
                success = daemon_manager.start_daemon(platform_name, daemon_config)
                
                if success:
                    log_message(
                        "statusline",
                        "INFO",
                        f"Successfully auto-started background tasks for {platform_name}",
                        {"platform": platform_name}
                    )
                    # 设置平台的后台任务启用标志
                    platform._background_enabled = True
                else:
                    log_message(
                        "statusline", 
                        "WARNING",
                        f"Failed to auto-start background tasks for {platform_name}",
                        {"platform": platform_name}
                    )
            else:
                log_message(
                    "statusline",
                    "DEBUG", 
                    f"Platform {platform_name} not configured or disabled, skipping auto-start",
                    {"platform": platform_name}
                )
        else:
            # 后台任务已经在运行，设置标志
            platform._background_enabled = True
            
            # 检查健康状态
            def check_healthy():
                try:
                    status = daemon_manager.get_daemon_status(platform_name)
                    return status.get("running") == True
                except:
                    return False
            
            platform._is_background_healthy = check_healthy
                
    except Exception as e:
        log_message(
            "statusline",
            "ERROR",
            f"Error in background task auto-start: {e}",
            {"platform": getattr(platform, 'name', 'unknown'), "error": str(e)}
        )


def format_platform_data(platform, config, colors):
    """格式化平台相关数据显示"""
    status_parts = []
    
    # 自动启动后台任务
    ensure_background_tasks(platform)
    
    try:
        # 获取余额数据
        balance_data = fetch_platform_balance_data(platform, config)
        if balance_data:
            try:
                balance_display = platform.format_balance_display(balance_data)

                # 如果是GAC Code平台，添加倍数信息
                if platform.name == "gaccode":
                    multiplier_info = get_multiplier_info(config)
                    if multiplier_info["active"]:
                        multiplier_mark = f"{multiplier_info['color']}[{multiplier_info['display']}]{colors['reset']}"
                        balance_display += f" {multiplier_mark}"

                # 添加后台任务状态指示器（所有平台通用）
                try:
                    if hasattr(platform, 'format_background_task_status'):
                        background_status = platform.format_background_task_status()
                        if background_status:
                            balance_display += f" {background_status}"
                except Exception as e:
                    log_message(
                        "statusline",
                        "DEBUG",
                        f"Failed to get background task status: {e}",
                    )

                status_parts.append(balance_display)
            except Exception as e:
                log_message(
                    "statusline",
                    "ERROR",
                    f"Failed to format balance display: {e}",
                )
                status_parts.append("Balance:Error")
        else:
            # 检查是否是配置问题
            if hasattr(platform, 'has_valid_config') and not platform.has_valid_config():
                # 没有有效配置，不显示任何信息
                pass
            else:
                # 有配置但获取失败，显示错误
                status_parts.append("Balance:Error")
        
        # 获取订阅数据
        subscription_data = fetch_platform_subscription_data(platform, config)
        if subscription_data:
            try:
                subscription_display = platform.format_subscription_display(subscription_data)
                if subscription_display:  # 只有非空字符串才添加
                    status_parts.append(subscription_display)
            except Exception as e:
                log_message(
                    "statusline",
                    "ERROR",
                    f"Failed to format subscription display: {e}",
                )
        
    except Exception as e:
        log_message(
            "statusline",
            "ERROR",
            f"Error formatting platform data: {e}",
        )
    
    return status_parts


def detect_statusline_mode(config, session_info):
    """智能检测状态条运行模式
    
    Returns:
        tuple: (mode, platform_name, confidence)
        mode: 'multi_platform', 'single_platform', 'basic'
        platform_name: 检测到的平台名称
        confidence: 检测置信度 (0.0-1.0)
    """
    session_id = session_info.get("session_id")
    
    # 模式1: Multi-Platform Mode - 检查Session ID映射
    if session_id:
        try:
            # 检查session-mappings.json文件
            mapping_file = DATA_DIR / "cache" / "session-mappings.json"
            if mapping_file.exists():
                mappings = safe_json_read(mapping_file, {})
                if session_id in mappings:
                    mapping_info = mappings[session_id]
                    detected_platform = mapping_info.get("platform")
                    if detected_platform:
                        log_message(
                            "statusline", "INFO", 
                            f"Multi-Platform Mode detected via session mapping: {detected_platform}",
                            {"session_id": session_id, "platform": detected_platform}
                        )
                        return ("multi_platform", detected_platform, 1.0)
            
            # 检查UUID前缀
            from data.session_mapping_v2 import detect_platform_from_session_id
            prefix_platform = detect_platform_from_session_id(session_id)
            if prefix_platform:
                log_message(
                    "statusline", "INFO", 
                    f"Multi-Platform Mode detected via UUID prefix: {prefix_platform}",
                    {"session_id": session_id, "platform": prefix_platform}
                )
                return ("multi_platform", prefix_platform, 0.9)
                
        except Exception as e:
            log_message(
                "statusline", "DEBUG", 
                f"Session mapping check failed: {e}"
            )
    
    # 模式2: Single Platform Mode - 检查配置的默认平台
    try:
        from config import get_config_manager
        config_manager = get_config_manager()
        launcher_settings = config_manager.get_launcher_settings()
        default_platform = launcher_settings.get("default_platform")
        
        if default_platform and default_platform != "gaccode":
            platform_config = config_manager.get_platform(default_platform)
            if platform_config and platform_config.get("enabled"):
                # 验证平台有有效的API密钥
                api_key = config_manager.get_platform_api_key(default_platform)
                if api_key and api_key.strip():
                    log_message(
                        "statusline", "INFO", 
                        f"Single Platform Mode detected: {default_platform}",
                        {"default_platform": default_platform}
                    )
                    return ("single_platform", default_platform, 0.8)
    except Exception as e:
        log_message(
            "statusline", "DEBUG", 
            f"Default platform check failed: {e}"
        )
    
    # 模式3: Basic Mode - 检查配置的有效平台
    try:
        from config import get_config_manager
        config_manager = get_config_manager()

        # 使用有效平台检测，而不是固定检查GAC
        effective_platform = config_manager.get_effective_platform()
        if effective_platform and effective_platform != "none":
            platform_config = config_manager.get_platform(effective_platform)
            if platform_config and platform_config.get("enabled"):
                # 验证平台有有效的API密钥
                api_key = config_manager.get_platform_api_key(effective_platform)
                if api_key and api_key.strip():
                    log_message(
                        "statusline", "INFO",
                        f"Basic Mode detected - using {effective_platform} with balance",
                        {"session_id": session_id, "platform": effective_platform}
                    )
                    return ("basic", effective_platform, 0.5)

        # 模式4: Zero Configuration Mode - 无任何配置
        log_message(
            "statusline", "INFO",
            "Zero Configuration Mode detected - no balance display",
            {"session_id": session_id}
        )
        return ("zero_config", "none", 0.3)
            
    except Exception as e:
        log_message(
            "statusline", "DEBUG", 
            f"GAC Code config check failed: {e}"
        )
        
    # 默认回退到零配置模式
    log_message(
        "statusline", "INFO", 
        "Zero Configuration Mode detected - fallback",
        {"session_id": session_id}
    )
    return ("zero_config", "none", 0.2)


def get_platform_instance_for_mode(mode, platform_name, config, session_info):
    """根据检测模式获取平台实例
    
    Args:
        mode: 运行模式
        platform_name: 平台名称
        config: 配置信息
        session_info: 会话信息
        
    Returns:
        platform instance or None
    """
    try:
        platform_manager = PlatformManager()
        
        if mode == "multi_platform":
            # Multi-Platform模式：使用完整的平台检测流程
            platform = platform_manager.detect_platform(session_info, None, config)
        
        elif mode == "zero_config":
            # Zero Configuration模式：不显示余额信息
            log_message(
                "statusline", "INFO", 
                "Zero Configuration Mode - no platform instance needed"
            )
            return None
            
        elif mode == "single_platform" or mode == "basic":
            # Single Platform/Basic模式：直接创建指定平台实例
            from config import get_config_manager
            config_manager = get_config_manager()
            
            # 获取平台API密钥
            api_key = config_manager.get_platform_api_key(platform_name)
            platform_config = config_manager.get_platform(platform_name)
            
            if platform_config and platform_config.get("enabled"):
                # 合并配置
                merged_config = {**config, **platform_config}
                platform = platform_manager.get_platform_by_name(
                    platform_name, api_key, merged_config
                )
            else:
                log_message(
                    "statusline", "WARNING", 
                    f"Platform {platform_name} not configured or disabled"
                )
                platform = None
        
        else:
            platform = None
            
        if platform:
            log_message(
                "statusline", "INFO", 
                f"Platform instance created: {platform.name} (mode: {mode})",
                {"mode": mode, "platform": platform_name}
            )
        else:
            log_message(
                "statusline", "WARNING", 
                f"Failed to create platform instance for {platform_name} (mode: {mode})"
            )
            
        return platform
        
    except Exception as e:
        log_message(
            "statusline", "ERROR", 
            f"Error creating platform instance: {e}",
            {"mode": mode, "platform": platform_name}
        )
        return None


def get_platform_data(config, session_info):
    """智能获取平台数据 - 支持多种运行模式"""
    if not (config["show_balance"] or config["show_subscription"]):
        return []
    
    # 智能模式检测
    mode, platform_name, confidence = detect_statusline_mode(config, session_info)
    
    log_message(
        "statusline", "INFO", 
        f"Statusline mode detected: {mode} ({platform_name}, confidence: {confidence:.1f})",
        {
            "mode": mode, 
            "platform": platform_name, 
            "confidence": confidence,
            "session_id": session_info.get("session_id")
        }
    )
    
    # 根据模式获取平台实例
    platform = get_platform_instance_for_mode(mode, platform_name, config, session_info)
    
    if platform:
        try:
            return format_platform_data(platform, config, get_color_scheme())
        finally:
            # 确保平台实例被正确关闭
            platform.close()
    else:
        log_message(
            "statusline", "WARNING", 
            f"No platform instance available for mode {mode}",
            {"mode": mode, "platform": platform_name}
        )
        return []


def render_status_output(status_parts, secondary_parts, config):
    """渲染最终的状态输出"""
    # 根据布局配置输出
    if config["layout"] == "multi_line" and secondary_parts:
        print(" ".join(status_parts))
        print(" ".join(secondary_parts), end="")
    else:
        # 单行显示，将secondary_parts加到主要部分后面
        all_parts = status_parts + secondary_parts
        try:
            output = " ".join(all_parts)
            print(output, end="")
            log_message(
                "statusline",
                "DEBUG",
                "Status output generated successfully",
                {"parts_count": len(all_parts), "output_length": len(output)},
            )
        except UnicodeEncodeError as e:
            # 处理Windows控制台的编码问题
            log_message(
                "statusline", "WARNING", f"Unicode encoding error, cleaning output: {e}"
            )
            cleaned_parts = []
            for part in all_parts:
                if isinstance(part, str):
                    # 移除或替换非ASCII字符
                    part = part.encode("ascii", "ignore").decode("ascii")
                cleaned_parts.append(part)
            print(" ".join(cleaned_parts), end="")
        except Exception as e:
            log_message("statusline", "ERROR", f"Failed to output status: {e}")
            print("Status Error", end="")  # 简单的错误显示


def display_status():
    """显示状态信息"""
    try:
        # 获取配置和session信息
        config = load_config()
        session_info = get_session_info()

        # 收集所有需要的数据
        data = collect_status_data(config, session_info)
        colors = get_color_scheme()
        
        # 格式化各部分状态信息
        status_parts = []
        status_parts.extend(format_basic_status(config, data, colors))
        status_parts.extend(format_session_cost_info(config, session_info, colors))
        status_parts.extend(format_usage_info(config, colors))
        status_parts.extend(get_platform_data(config, session_info))
        
        # 格式化次要状态信息
        secondary_parts = format_secondary_status(config, data, colors)
        
        # 渲染输出
        render_status_output(status_parts, secondary_parts, config)
        
    except Exception as e:
        log_message("statusline", "ERROR", f"Critical error in display_status: {e}")
        print("Status Error", end="")



if __name__ == "__main__":
    display_status()
