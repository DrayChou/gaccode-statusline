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

# 设置控制台编码
os.environ["PYTHONIOENCODING"] = "utf-8"

# 配置
API_BASE = "https://gaccode.com/api"
PROJECT_DIR = Path(__file__).parent  # scripts/gaccode.com目录
TOKEN_FILE = PROJECT_DIR / "api-token.txt"
CACHE_FILE = PROJECT_DIR / "statusline-cache.json"
CONFIG_FILE = PROJECT_DIR / "statusline-config.json"
SESSION_INFO_FILE = PROJECT_DIR / "session-info-cache.json"
BALANCE_CACHE_TIMEOUT = 60  # 余额缓存60秒
SUBSCRIPTION_CACHE_TIMEOUT = 3600  # 订阅信息缓存1小时

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
        return DEFAULT_CONFIG

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
            # 合并默认配置，确保所有选项都存在
            result = DEFAULT_CONFIG.copy()
            result.update(config)
            return result
    except Exception:
        return DEFAULT_CONFIG


def load_token():
    """加载API token"""
    if not TOKEN_FILE.exists():
        return None

    try:
        with open(TOKEN_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return None


def get_session_info():
    """获取Claude Code传入的session信息"""
    try:
        session_data = json.loads(sys.stdin.read())
        # 缓存session信息到本地文件
        cache_session_info(session_data)
        return session_data
    except:
        return {}


def cache_session_info(session_data):
    """缓存session信息到本地文件"""
    try:
        with open(SESSION_INFO_FILE, "w", encoding="utf-8") as f:
            json.dump(session_data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        # 缓存失败不影响主要功能，静默处理
        pass


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


def load_cache():
    """加载缓存数据"""
    if not CACHE_FILE.exists():
        return {"balance": None, "subscriptions": None}

    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            cache = json.load(f)

        result = {"balance": None, "subscriptions": None}
        current_time = datetime.now()

        # 检查余额缓存
        if cache.get("balance_timestamp"):
            balance_time = datetime.fromisoformat(cache["balance_timestamp"])
            if (current_time - balance_time).total_seconds() <= BALANCE_CACHE_TIMEOUT:
                result["balance"] = cache.get("balance_data")

        # 检查订阅缓存
        if cache.get("subscription_timestamp"):
            sub_time = datetime.fromisoformat(cache["subscription_timestamp"])
            if (current_time - sub_time).total_seconds() <= SUBSCRIPTION_CACHE_TIMEOUT:
                result["subscriptions"] = cache.get("subscription_data")

        return result
    except Exception:
        return {"balance": None, "subscriptions": None}


def save_cache(balance_data=None, subscription_data=None):
    """保存缓存数据"""
    try:
        # 读取现有缓存
        existing_cache = {}
        if CACHE_FILE.exists():
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                existing_cache = json.load(f)

        current_time = datetime.now().isoformat()

        # 更新余额数据
        if balance_data is not None:
            existing_cache["balance_data"] = balance_data
            existing_cache["balance_timestamp"] = current_time

        # 更新订阅数据
        if subscription_data is not None:
            existing_cache["subscription_data"] = subscription_data
            existing_cache["subscription_timestamp"] = current_time

        # 保存缓存
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(existing_cache, f)
    except Exception:
        pass


def fetch_balance_data(token):
    """获取余额数据"""
    headers = {"authorization": f"Bearer {token}", "content-type": "application/json"}

    try:
        balance_resp = requests.get(
            f"{API_BASE}/credits/balance", headers=headers, timeout=5
        )
        balance_resp.raise_for_status()
        return balance_resp.json()
    except requests.RequestException:
        return None


def fetch_subscription_data(token):
    """获取订阅数据"""
    headers = {"authorization": f"Bearer {token}", "content-type": "application/json"}

    try:
        subscription_resp = requests.get(
            f"{API_BASE}/subscriptions", headers=headers, timeout=5
        )
        subscription_resp.raise_for_status()
        return subscription_resp.json()
    except requests.RequestException:
        return None


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
        if last_refill_str.endswith('Z'):
            # UTC时间
            last_refill = datetime.fromisoformat(last_refill_str.replace('Z', '+00:00'))
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
            return "等待刷新"
        
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

    # 5. 目录信息 (放到secondary_parts)
    if config["show_directory"]:
        secondary_parts.append(f"Dir:{cyan}{dir_display}{reset}")

    # 6. Git信息 (放到secondary_parts)
    if config["show_git_branch"] and git_info:
        branch_text = f"{git_info['branch']}"
        if git_info["is_dirty"]:
            branch_text += "*"  # 标记有未提交更改
        secondary_parts.append(f"Git:{yellow}{branch_text}{reset}")

    # 获取GAC API数据
    token = load_token()
    is_claude = is_claude_model(session_info)
    if token and is_claude and (config["show_balance"] or config["show_subscription"]):
        # 获取缓存数据
        cached = load_cache()

        # 获取或更新余额数据
        if config["show_balance"]:
            balance_data = cached["balance"]
            if balance_data is None:
                balance_data = fetch_balance_data(token)
                if balance_data:
                    save_cache(balance_data=balance_data)

            if balance_data:
                try:
                    balance = balance_data["balance"]
                    credit_cap = balance_data["creditCap"]
                    balance_color = get_color_code(balance, [500, 1000])
                    
                    # 获取下一次刷新时间
                    last_refill = balance_data.get("lastRefill")
                    refill_rate = balance_data.get("refillRate", 0)
                    next_refill_time = calculate_next_refill_time(last_refill, refill_rate) if last_refill else "未知"

                    # 获取倍数信息
                    multiplier_info = get_multiplier_info(config)

                    # 构建balance显示字符串
                    balance_str = (
                        f"Balance:{balance_color}{balance}{reset}/{credit_cap}"
                    )
                    
                    # 添加下一次刷新时间
                    if next_refill_time != "未知":
                        balance_str += f" ({next_refill_time})"

                    # 如果在倍数时段内，添加倍数标记
                    if multiplier_info["active"]:
                        multiplier_mark = f"{multiplier_info['color']}[{multiplier_info['display']}]{reset}"
                        balance_str += f" {multiplier_mark}"

                    status_parts.append(balance_str)
                except Exception:
                    pass

        # 获取或更新订阅数据
        if config["show_subscription"]:
            subscription_data = cached["subscriptions"]
            if subscription_data is None:
                subscription_data = fetch_subscription_data(token)
                if subscription_data:
                    save_cache(subscription_data=subscription_data)

            if subscription_data and subscription_data.get("subscriptions"):
                try:
                    sub = subscription_data["subscriptions"][0]
                    end_date = format_date(sub["endDate"])
                    days_left = calculate_days_left(sub["endDate"])
                    days_color = get_color_code(days_left, [7, 14])
                    status_parts.append(
                        f"Expires:{days_color}{end_date}({days_left}d){reset}"
                    )
                except Exception:
                    pass

    # 根据布局配置输出
    if config["layout"] == "multi_line" and secondary_parts:
        print(" ".join(status_parts))
        print(" ".join(secondary_parts), end="")
    else:
        # 单行显示，将secondary_parts加到主要部分后面
        all_parts = status_parts + secondary_parts
        print(" ".join(all_parts), end="")


if __name__ == "__main__":
    display_status()
