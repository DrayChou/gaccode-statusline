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
except ImportError:
    # Fallback to sys.path manipulation for runtime
    sys.path.insert(0, str(Path(__file__).parent / "data"))
    from logger import log_message
    from file_lock import safe_json_write, safe_json_read

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
    """加载显示配置"""
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
            log_message("statusline", "DEBUG", "Config loaded successfully")
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
            f"Failed to load config: {e}",
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
    """缓存session信息到本地文件（带文件锁定）"""
    try:
        # 使用安全的文件写入（带锁定）
        success = safe_json_write(SESSION_INFO_FILE, session_data)
        if success:
            log_message("statusline", "DEBUG", "Session info cached successfully")
        else:
            log_message("statusline", "WARNING", "Failed to cache session info")
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


def get_today_usage():
    """获取今日使用量"""
    # 首先检查缓存文件是否存在
    if USAGE_CACHE_FILE.exists():
        try:
            with open(USAGE_CACHE_FILE, "r", encoding="utf-8-sig") as f:
                cache_data = json.load(f)
                cache_time = datetime.fromisoformat(cache_data.get("timestamp", ""))
                # 如果缓存未过期（5分钟），直接使用缓存
                if (datetime.now() - cache_time).total_seconds() <= USAGE_CACHE_TIMEOUT:
                    return cache_data.get("usage_data")
        except Exception:
            # 缓存文件损坏，删除它
            try:
                USAGE_CACHE_FILE.unlink()
            except Exception:
                pass

    # 如果 npx 不可用，直接返回 None
    if not check_npx_available():
        return None

    # 获取今日日期
    today = datetime.now().strftime("%Y%m%d")

    try:
        # 异步更新缓存 - 不等待结果，直接返回当前缓存或 None
        # 使用 subprocess.Popen 在后台运行
        subprocess.Popen(
            ["python", str(PROJECT_DIR / "update_usage.py"), today],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass

    # 返回当前的缓存数据（如果有的话）
    if USAGE_CACHE_FILE.exists():
        try:
            with open(USAGE_CACHE_FILE, "r", encoding="utf-8-sig") as f:
                cache_data = json.load(f)
                return cache_data.get("usage_data")
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
    platform_config_file = DATA_DIR / "config" / "launcher-config.json"

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
    platform_cache_file = DATA_DIR / "cache" / f"balance-cache-{platform_name}.json"

    if not platform_cache_file.exists():
        log_message(
            "statusline",
            "DEBUG",
            f"No cache file for {platform_name}",
            {"file": str(platform_cache_file)},
        )
        return {"balance": None, "subscriptions": None}

    try:
        cache = safe_json_read(platform_cache_file, {})
        if not cache:
            log_message("statusline", "DEBUG", f"Empty cache file for {platform_name}")
            return {"balance": None, "subscriptions": None}

        result = {"balance": None, "subscriptions": None}
        current_time = datetime.now()

        # 检查余额缓存（5分钟 = 300秒）
        if cache.get("balance_timestamp"):
            try:
                balance_time = datetime.fromisoformat(cache["balance_timestamp"])
                cache_age = (current_time - balance_time).total_seconds()
                if cache_age <= 300:  # 5分钟缓存
                    result["balance"] = cache.get("balance_data")
                    log_message(
                        "statusline",
                        "DEBUG",
                        f"Using {platform_name} balance cache",
                        {"cache_age_seconds": cache_age},
                    )
                else:
                    log_message(
                        "statusline",
                        "DEBUG",
                        f"{platform_name} balance cache expired",
                        {"cache_age_seconds": cache_age},
                    )
            except ValueError as e:
                log_message(
                    "statusline",
                    "WARNING",
                    f"Invalid {platform_name} balance timestamp: {e}",
                )

        # 检查订阅缓存
        if cache.get("subscription_timestamp"):
            try:
                subscription_time = datetime.fromisoformat(
                    cache["subscription_timestamp"]
                )
                cache_age = (current_time - subscription_time).total_seconds()
                if cache_age <= SUBSCRIPTION_CACHE_TIMEOUT:
                    result["subscriptions"] = cache.get("subscription_data")
                    log_message(
                        "statusline",
                        "DEBUG",
                        f"Using {platform_name} subscription cache",
                        {"cache_age_seconds": cache_age},
                    )
                else:
                    log_message(
                        "statusline",
                        "DEBUG",
                        f"{platform_name} subscription cache expired",
                        {"cache_age_seconds": cache_age},
                    )
            except ValueError as e:
                log_message(
                    "statusline",
                    "WARNING",
                    f"Invalid {platform_name} subscription timestamp: {e}",
                )

        return result
    except Exception as e:
        log_message(
            "statusline",
            "ERROR",
            f"Failed to load {platform_name} cache",
            {"error": str(e)},
        )
        return {"balance": None, "subscriptions": None}


def save_platform_cache(platform_name, balance_data=None, subscription_data=None):
    """保存特定平台的缓存数据（带文件锁定）"""
    platform_cache_file = DATA_DIR / "cache" / f"balance-cache-{platform_name}.json"

    try:
        # 加载现有缓存
        cache = safe_json_read(platform_cache_file, {})
        current_time = datetime.now().isoformat()

        # 更新余额数据
        if balance_data is not None:
            cache["balance_data"] = balance_data
            cache["balance_timestamp"] = current_time
            log_message(
                "statusline", "DEBUG", f"Updating {platform_name} balance cache"
            )

        # 更新订阅数据
        if subscription_data is not None:
            cache["subscription_data"] = subscription_data
            cache["subscription_timestamp"] = current_time
            log_message(
                "statusline", "DEBUG", f"Updating {platform_name} subscription cache"
            )

        # 安全写入文件（带锁定）
        success = safe_json_write(platform_cache_file, cache)
        if success:
            log_message(
                "statusline", "DEBUG", f"Successfully saved {platform_name} cache"
            )
        else:
            log_message(
                "statusline", "ERROR", f"Failed to write {platform_name} cache file"
            )
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


def display_status():
    """显示状态信息"""
    # 获取配置和session信息
    config = load_config()
    session_info = get_session_info()

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

    # 初始化状态栏部分
    status_parts = []
    secondary_parts = []  # 用于目录和Git信息

    # 颜色定义
    reset = "\033[0m"
    green = "\033[32m"  # 绿色 - 模型
    cyan = "\033[36m"  # 青色 - 目录
    yellow = "\033[33m"  # 黄色 - Git分支
    purple = "\033[35m"  # 紫色 - 时间
    blue = "\033[34m"  # 蓝色 - 会话时长
    magenta = "\033[95m"  # 洋红色 - Session成本

    # 1. 模型信息
    if config["show_model"]:
        status_parts.append(f"Model:{green}{model_name}{reset}")

    # 2. 当前时间
    if config["show_time"]:
        status_parts.append(f"Time:{purple}{current_time}{reset}")

    # 3. 会话时长 (如果有的话)
    if config["show_session_duration"] and session_duration:
        status_parts.append(f"Duration:{blue}{session_duration}{reset}")

    # 4. Session成本
    if config["show_session_cost"]:
        session_cost = format_session_cost(session_info)
        if session_cost:
            status_parts.append(f"Cost:{magenta}{session_cost}{reset}")

    # 5. 今日使用量
    if config["show_today_usage"]:
        usage_data = get_today_usage()
        if usage_data:
            usage_cost = usage_data.get("total_cost", 0)
            if usage_cost > 0:
                # 根据使用量设置颜色 - 新10级装备颜色方案
                if usage_cost >= 300:
                    usage_color = "\033[38;5;196m"  # 红色 - 不朽 (Exotic) #FF0000
                elif usage_cost >= 200:
                    usage_color = "\033[38;5;208m"  # 橙色 - 传说 (Legendary) #FF8C00
                elif usage_cost >= 100:
                    usage_color = "\033[38;5;128m"  # 紫色 - 神器 (Artifact) #800080
                elif usage_cost >= 50:
                    usage_color = "\033[38;5;201m"  # 品红 - 史诗 (Epic) #FF00FF
                elif usage_cost >= 20:
                    usage_color = "\033[38;5;21m"  # 蓝色 - 稀有 (Rare) #0000FF
                elif usage_cost >= 10:
                    usage_color = "\033[38;5;117m"  # 浅蓝 - 卓越 (Exceptional) #87CEEB
                elif usage_cost >= 5:
                    usage_color = "\033[38;5;34m"  # 绿色 - 精良 (Fine) #008000
                elif usage_cost >= 2:
                    usage_color = "\033[38;5;120m"  # 浅绿 - 优秀 (Uncommon) #98E088
                elif usage_cost >= 0.5:
                    usage_color = "\033[38;5;255m"  # 白色 - 普通 (Common) #FFFFFF
                else:
                    usage_color = "\033[38;5;242m"  # 灰色 - 劣质 (Poor) #6D6D6D
                status_parts.append(f"Today:{usage_color}${usage_cost:.2f}{reset}")

    # 6. 目录信息 (放到secondary_parts)
    if config["show_directory"]:
        secondary_parts.append(f"Dir:{cyan}{dir_display}{reset}")

    # 7. Git信息 (放到secondary_parts)
    if config["show_git_branch"] and git_info:
        branch_text = f"{git_info['branch']}"
        if git_info["is_dirty"]:
            branch_text += "*"  # 标记有未提交更改
        secondary_parts.append(f"Git:{yellow}{branch_text}{reset}")

    # 获取平台 API 数据 (使用新的平台管理器系统)
    if config["show_balance"] or config["show_subscription"]:
        # 从session信息中提取session_id
        session_id = session_info.get("session_id")
        log_message(
            "statusline",
            "DEBUG",
            "Starting platform detection",
            {"session_id": session_id},
        )

        # 尝试从配置文件获取token，提供检测用
        # 平台检测应该基于session_id映射，而不是model信息
        token_for_detection = None

        # 使用平台管理器检测平台
        platform_manager = PlatformManager()
        platform = platform_manager.detect_platform(
            session_info, token_for_detection, config
        )

        if platform:
            log_message(
                "statusline",
                "INFO",
                f"Platform detected: {platform.name}",
                {"session_id": session_id},
            )
        else:
            log_message(
                "statusline",
                "WARNING",
                "No platform detected",
                {"session_id": session_id},
            )

        if platform:
            try:
                # 使用平台特定的缓存数据
                cached = load_platform_cache(platform.name)
                log_message(
                    "statusline", "DEBUG", f"Checking {platform.name} platform cache"
                )

                # 获取或更新余额数据
                if config["show_balance"]:
                    balance_data = cached["balance"]
                    if balance_data is None:
                        log_message(
                            "statusline",
                            "DEBUG",
                            f"Cache miss, fetching balance from {platform.name} API",
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
                                        "balance_data_type": type(
                                            balance_data
                                        ).__name__,
                                        "balance_data_keys": (
                                            list(balance_data.keys())
                                            if isinstance(balance_data, dict)
                                            else "not_dict"
                                        ),
                                    },
                                )
                                save_platform_cache(
                                    platform.name, balance_data=balance_data
                                )
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

                    if balance_data:
                        try:
                            balance_display = platform.format_balance_display(
                                balance_data
                            )

                            # 如果是GAC Code平台，添加倍数信息
                            if platform.name == "gaccode":
                                multiplier_info = get_multiplier_info(config)
                                if multiplier_info["active"]:
                                    multiplier_mark = f"{multiplier_info['color']}[{multiplier_info['display']}]{reset}"
                                    balance_display += f" {multiplier_mark}"

                            status_parts.append(balance_display)
                        except Exception as e:
                            log_message(
                                "statusline",
                                "ERROR",
                                f"Failed to format balance display: {e}",
                            )
                            status_parts.append("Balance:Error")

                # 获取或更新订阅数据
                if config["show_subscription"]:
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
                                save_platform_cache(
                                    platform.name, subscription_data=subscription_data
                                )
                        except Exception as e:
                            log_message(
                                "statusline",
                                "ERROR",
                                f"{platform.name} subscription API call failed",
                                {"error": str(e)},
                            )

                    if subscription_data:
                        try:
                            subscription_display = platform.format_subscription_display(
                                subscription_data
                            )
                            if subscription_display:  # 只有非空字符串才添加
                                status_parts.append(subscription_display)
                        except Exception as e:
                            log_message(
                                "statusline",
                                "ERROR",
                                f"Failed to format subscription display: {e}",
                            )
            finally:
                # 确保平台实例被正确关闭
                if platform:
                    platform.close()

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


if __name__ == "__main__":
    display_status()
