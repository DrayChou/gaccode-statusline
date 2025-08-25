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
from datetime import datetime, timezone
from pathlib import Path

# 设置控制台编码
os.environ['PYTHONIOENCODING'] = 'utf-8'

# 配置
API_BASE = "https://gaccode.com/api"
PROJECT_DIR = Path(__file__).parent  # 项目根目录
TOKEN_FILE = PROJECT_DIR / "api-token.txt"
CACHE_FILE = PROJECT_DIR / "statusline-cache.json"
CACHE_TIMEOUT = 45   # 45秒缓存

def load_token():
    """加载API token"""
    if not TOKEN_FILE.exists():
        return None
    
    try:
        with open(TOKEN_FILE, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except Exception:
        return None

def is_gaccode_provider():
    """检查是否为gaccode提供商"""
    # 读取Claude Code传入的session信息
    try:
        session_data = json.loads(sys.stdin.read())
        # 检查模型ID或其他标识符来判断是否为gaccode
        model_id = session_data.get('model', {}).get('id', '')
        # 这里可以根据实际的gaccode模型标识来判断
        return 'gaccode' in model_id.lower() or 'gac' in model_id.lower()
    except:
        # 如果无法读取session信息，默认检查token文件存在性
        return TOKEN_FILE.exists()

def load_cache():
    """加载缓存数据"""
    if not CACHE_FILE.exists():
        return None
    
    try:
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            cache = json.load(f)
            
        # 检查缓存是否过期
        cache_time = datetime.fromisoformat(cache.get('timestamp', ''))
        if (datetime.now() - cache_time).total_seconds() > CACHE_TIMEOUT:
            return None
            
        return cache
    except Exception:
        return None

def save_cache(data):
    """保存缓存数据"""
    try:
        cache_data = {
            'timestamp': datetime.now().isoformat(),
            'data': data
        }
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f)
    except Exception:
        pass

def fetch_api_data(token):
    """获取API数据"""
    headers = {
        'authorization': f'Bearer {token}',
        'content-type': 'application/json'
    }
    
    try:
        # 获取余额信息
        balance_resp = requests.get(f"{API_BASE}/credits/balance", headers=headers, timeout=5)
        balance_resp.raise_for_status()
        balance_data = balance_resp.json()
        
        # 获取订阅信息
        subscription_resp = requests.get(f"{API_BASE}/subscriptions", headers=headers, timeout=5)
        subscription_resp.raise_for_status()
        subscription_data = subscription_resp.json()
        
        return {
            'balance': balance_data,
            'subscriptions': subscription_data
        }
    except Exception as e:
        return None

def format_date(date_str):
    """格式化日期"""
    try:
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return dt.strftime('%m-%d')
    except:
        return date_str

def calculate_days_left(end_date_str):
    """计算剩余天数"""
    try:
        end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
        now = datetime.now(timezone.utc)
        days_left = (end_date - now).days
        return max(0, days_left)
    except:
        return 0

def get_color_code(value, thresholds):
    """根据阈值获取颜色代码"""
    if value <= thresholds[0]:
        return '\033[91m'  # 红色
    elif value <= thresholds[1]:
        return '\033[93m'  # 黄色
    else:
        return '\033[92m'  # 绿色

def display_status():
    """显示状态信息"""
    # 暂时去掉域名过滤，始终显示状态栏进行测试
    # if not is_gaccode_provider():
    #     return
    
    token = load_token()
    if not token:
        print("[WARN] 未配置GAC API Token", end='')
        return
    
    # 尝试从缓存加载数据
    cached = load_cache()
    if cached:
        data = cached['data']
    else:
        # 获取最新数据
        data = fetch_api_data(token)
        if not data:
            print("[ERROR] GAC API调用失败", end='')
            return
        save_cache(data)
    
    try:
        balance = data['balance']['balance']
        credit_cap = data['balance']['creditCap']
        
        # 获取订阅信息
        end_date = ""
        days_left = 0
        if data['subscriptions']['subscriptions']:
            sub = data['subscriptions']['subscriptions'][0]
            end_date = format_date(sub['endDate'])
            days_left = calculate_days_left(sub['endDate'])
        
        # 颜色编码
        reset = '\033[0m'
        balance_color = get_color_code(balance, [500, 1000])
        days_color = get_color_code(days_left, [7, 14])
        
        # 格式化输出 (使用ASCII字符避免编码问题)
        status_parts = []
        status_parts.append(f"Balance:{balance_color}{balance}{reset}/{credit_cap}")
        
        if end_date:
            status_parts.append(f"Expires:{days_color}{end_date}({days_left}d){reset}")
        
        print(" ".join(status_parts), end='')
        
    except Exception as e:
        print("[ERROR] 数据解析失败", end='')

if __name__ == "__main__":
    display_status()