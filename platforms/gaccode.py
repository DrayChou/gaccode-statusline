#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GAC Code platform implementation
"""

from typing import Dict, Any, Optional, Tuple
from .base import BasePlatform
from datetime import datetime, timezone, timedelta
import re
import json
import os
from pathlib import Path


class GACCodePlatform(BasePlatform):
    """GAC Code platform implementation with 30-minute time-segment caching"""
    
    def __init__(self, token: str, config: Dict[str, Any]):
        super().__init__(token, config)
        self._multiplier_cache_file = Path("data/cache/gac-multiplier-segments.json")
        self._history_cache_file = Path("data/cache/gac-history-cache.json")
        self._balance_cache_file = Path("data/cache/balance-cache-gaccode.json")
        self._subscription_cache_file = Path("data/cache/subscription-cache-gaccode.json")
        self._ensure_cache_directories()

    @property
    def name(self) -> str:
        return "gaccode"

    @property
    def api_base(self) -> str:
        return "https://gaccode.com/api"

    def get_headers(self) -> Dict[str, str]:
        """Get headers for GAC Code API requests"""
        # GAC Code API使用JWT login_token而不是api_key
        login_token = self.config.get('login_token')
        if login_token:
            return {
                "accept": "*/*",
                "accept-language": "zh",
                "authorization": f"Bearer {login_token}",
                "content-type": "application/json",
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
            }
        else:
            # 回退到基础token（虽然可能无效）
            return {
                "accept": "*/*",
                "authorization": f"Bearer {self.token}",
                "content-type": "application/json",
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
            }
    
    def detect_platform(self, session_info: Dict[str, Any], token: str) -> bool:
        """Detect GAC Code platform"""
        # 平台检测应该通过session-mappings.json进行，这里只作为fallback
        # 检查token格式作为最后的手段
        if token and token.startswith("sk-ant-"):
            return True
        return False

    def _is_cache_valid(self, cache_file: Path, ttl_seconds: int) -> bool:
        """检查缓存文件是否有效"""
        if not cache_file.exists():
            return False
        
        try:
            cache_mtime = cache_file.stat().st_mtime
            current_time = datetime.now().timestamp()
            return (current_time - cache_mtime) < ttl_seconds
        except Exception:
            return False
    
    def _load_cache_data(self, cache_file: Path) -> Optional[Dict[str, Any]]:
        """加载缓存数据"""
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            return cache_data.get('data')
        except Exception:
            return None
    
    def _save_cache_data(self, cache_file: Path, data: Dict[str, Any], ttl_seconds: int) -> None:
        """保存数据到缓存"""
        try:
            cache_data = {
                'data': data,
                'cached_at': datetime.now().isoformat(),
                'ttl': ttl_seconds
            }
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass  # 缓存保存失败不影响主流程
    
    def fetch_balance_data(self) -> Optional[Dict[str, Any]]:
        """Fetch balance data from GAC Code API (5分钟缓存)"""
        # 检查缓存是否有效（5分钟 = 300秒）
        if self._is_cache_valid(self._balance_cache_file, 300):
            cached_data = self._load_cache_data(self._balance_cache_file)
            if cached_data:
                return cached_data
        
        # 缓存无效或不存在，调用API
        api_data = self.make_request("/credits/balance")
        if api_data:
            # 保存到缓存（5分钟TTL）
            self._save_cache_data(self._balance_cache_file, api_data, 300)
        
        return api_data
    
    def fetch_subscription_data(self) -> Optional[Dict[str, Any]]:
        """Fetch subscription data from GAC Code API (5分钟缓存)"""
        # 检查缓存是否有效（5分钟 = 300秒）
        if self._is_cache_valid(self._subscription_cache_file, 300):
            cached_data = self._load_cache_data(self._subscription_cache_file)
            if cached_data:
                return cached_data
        
        # 缓存无效或不存在，调用API
        api_data = self.make_request("/subscriptions")
        if api_data:
            # 保存到缓存（5分钟TTL）
            self._save_cache_data(self._subscription_cache_file, api_data, 300)
        
        return api_data

    def fetch_subscription_data(self) -> Optional[Dict[str, Any]]:
        """Fetch subscription data from GAC Code API"""
        return self.make_request("/subscriptions")

    def _ensure_cache_directories(self) -> None:
        """确保缓存目录存在"""
        self._multiplier_cache_file.parent.mkdir(parents=True, exist_ok=True)
        self._history_cache_file.parent.mkdir(parents=True, exist_ok=True)
    
    def _get_time_segment_id(self, dt: datetime = None) -> str:
        """获取30分钟时间段ID
        
        Args:
            dt: 指定时间，默认为当前时间（北京时间）
            
        Returns:
            格式: "YYYY-MM-DD_HH_0" 或 "YYYY-MM-DD_HH_1"
            示例: "2025-09-05_14_0" (14:00-14:30), "2025-09-05_14_1" (14:31-14:59)
        """
        if dt is None:
            dt = datetime.now(timezone(timedelta(hours=8)))  # 北京时间
        
        # 确定时间段：0-30分钟为段0，31-59分钟为段1
        segment = 0 if dt.minute <= 30 else 1
        return f"{dt.strftime('%Y-%m-%d_%H')}_{segment}"
    
    def _load_multiplier_cache(self) -> Dict[str, Any]:
        """加载倍率缓存数据"""
        if not self._multiplier_cache_file.exists():
            return {"segments": {}, "last_updated": None}
        
        try:
            with open(self._multiplier_cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {"segments": {}, "last_updated": None}
    
    def _save_multiplier_cache(self, cache_data: Dict[str, Any]) -> None:
        """保存倍率缓存数据"""
        try:
            with open(self._multiplier_cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass  # 缓存保存失败不影响主流程
    
    def _should_update_history_cache(self) -> bool:
        """判断是否需要更新历史缓存（5分钟轮询）"""
        if not self._history_cache_file.exists():
            return True
        
        try:
            cache_mtime = self._history_cache_file.stat().st_mtime
            current_time = datetime.now().timestamp()
            return (current_time - cache_mtime) > 300  # 5分钟
        except Exception:
            return True
    
    def fetch_history_data(self, limit: int = 10) -> Optional[Dict[str, Any]]:
        """获取使用历史数据（带5分钟缓存）"""
        # 检查是否需要更新缓存
        if not self._should_update_history_cache():
            try:
                with open(self._history_cache_file, 'r', encoding='utf-8') as f:
                    cached_data = json.load(f)
                return cached_data.get('data')
            except Exception:
                pass  # 缓存读取失败，继续API调用
        
        # 调用API获取最新数据
        api_data = self.make_request(f"/credits/history?limit={limit}")
        if api_data:
            # 更新历史缓存
            try:
                cache_data = {
                    'data': api_data,
                    'cached_at': datetime.now().isoformat(),
                    'ttl': 300  # 5分钟TTL
                }
                with open(self._history_cache_file, 'w', encoding='utf-8') as f:
                    json.dump(cache_data, f, ensure_ascii=False, indent=2)
            except Exception:
                pass  # 缓存保存失败不影响返回
            
            # 更新倍率时间段缓存
            self._update_multiplier_segments_from_history(api_data)
        
        return api_data
    
    def _update_multiplier_segments_from_history(self, history_data: Dict[str, Any]) -> None:
        """根据历史数据更新倍率时间段缓存"""
        if not history_data or 'history' not in history_data:
            return
        
        cache_data = self._load_multiplier_cache()
        updated = False
        
        for record in history_data['history']:
            if record.get('reason') != 'usage' or 'details' not in record:
                continue
            
            # 解析倍率
            details = record['details']
            multiplier_match = re.search(r'Time Multiplier\((\d+)\s*-\s*([^)]+)\)', details)
            if not multiplier_match:
                continue
            
            multiplier_value = int(multiplier_match.group(1))
            
            # 解析记录时间
            try:
                created_at = datetime.fromisoformat(record['createdAt'].replace('Z', '+00:00'))
                beijing_time = created_at.astimezone(timezone(timedelta(hours=8)))
                segment_id = self._get_time_segment_id(beijing_time)
                
                # 更新对应时间段的倍率
                cache_data['segments'][segment_id] = {
                    'multiplier': multiplier_value,
                    'updated_at': datetime.now().isoformat(),
                    'source_time': beijing_time.isoformat(),
                    'source': 'api_history'
                }
                updated = True
                
            except Exception:
                continue  # 解析失败跳过该记录
        
        if updated:
            cache_data['last_updated'] = datetime.now().isoformat()
            self._save_multiplier_cache(cache_data)

    def format_balance_display(self, balance_data: Dict[str, Any]) -> str:
        """Format GAC Code balance for display"""
        try:
            balance = balance_data["balance"]
            credit_cap = balance_data["creditCap"]

            # 颜色代码
            if balance <= 500:
                color = "\033[91m"  # 红色
            elif balance <= 1000:
                color = "\033[93m"  # 黄色
            else:
                color = "\033[92m"  # 绿色
            reset = "\033[0m"

            # 检测倍率状态
            multiplier_info = self._detect_multiplier_status()
            
            # 获取下一次刷新时间
            last_refill = balance_data.get("lastRefill")
            next_refill_time = (
                self._calculate_next_refill_time(last_refill) if last_refill else "未知"
            )

            balance_str = f"GAC.B:{color}{balance}{reset}/{credit_cap}"
            
            # 添加倍率指示器
            if multiplier_info["is_active"]:
                multiplier_value = multiplier_info["value"]
                is_time_based = multiplier_info["is_time_based"]
                
                if is_time_based and not self._is_high_multiplier_hours():
                    # API显示倍率但时间段判断为非倍率 - 警告
                    balance_str += f"\033[91m!{multiplier_value}x\033[0m"  # 红色警告(使用!替代⚠避免编码问题)
                else:
                    # 根据倍率值选择颜色
                    if multiplier_value >= 5:
                        multiplier_color = "\033[95m"  # 紫色 - 高倍率
                    elif multiplier_value >= 2:
                        multiplier_color = "\033[93m"  # 黄色 - 中倍率
                    else:
                        multiplier_color = "\033[92m"  # 绿色 - 低倍率
                    balance_str += f"{multiplier_color}{multiplier_value}x\033[0m"
            
            if next_refill_time != "未知":
                balance_str += f" ({next_refill_time})"

            return balance_str
        except Exception:
            return "GAC.B:Error"

    def format_subscription_display(self, subscription_data: Dict[str, Any]) -> str:
        """Format GAC Code subscription for display"""
        try:
            if not subscription_data.get("subscriptions"):
                return ""

            sub = subscription_data["subscriptions"][0]
            end_date = self._format_date(sub["endDate"])
            days_left = self._calculate_days_left(sub["endDate"])

            # 颜色代码
            if days_left <= 7:
                color = "\033[91m"  # 红色
            elif days_left <= 14:
                color = "\033[93m"  # 黄色
            else:
                color = "\033[92m"  # 绿色
            reset = "\033[0m"

            return f"Expires:{color}{end_date}({days_left}d){reset}"
        except Exception:
            return "Expires:Error"

    def _calculate_next_refill_time(self, last_refill_str: str) -> str:
        """计算下一次刷新时间"""
        try:
            if last_refill_str.endswith("Z"):
                last_refill = datetime.fromisoformat(
                    last_refill_str.replace("Z", "+00:00")
                )
            else:
                last_refill = datetime.fromisoformat(last_refill_str)

            now = datetime.now(timezone.utc)
            next_refill_time = last_refill + timedelta(hours=1)
            remaining_seconds = (next_refill_time - now).total_seconds()

            if remaining_seconds < 0:
                overdue_seconds = abs(remaining_seconds)
                overdue_hours = int(overdue_seconds // 3600)
                overdue_minutes = int((overdue_seconds % 3600) // 60)

                if overdue_hours > 0:
                    return f"overdue {overdue_hours}h{overdue_minutes}m"
                elif overdue_minutes > 0:
                    return f"overdue {overdue_minutes}m"
                else:
                    return "refreshing soon"

            remaining_hours = int(remaining_seconds // 3600)
            remaining_minutes = int((remaining_seconds % 3600) // 60)
            remaining_seconds = int(remaining_seconds % 60)

            if remaining_hours == 0 and remaining_minutes == 0:
                return f"{remaining_seconds}s"
            elif remaining_hours == 0:
                return f"{remaining_minutes}m{remaining_seconds}s"
            else:
                return f"{remaining_hours}h{remaining_minutes}m"
        except Exception:
            return "未知"

    def _format_date(self, date_str: str) -> str:
        """格式化日期"""
        try:
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            return dt.strftime("%m-%d")
        except:
            return date_str

    def _calculate_days_left(self, end_date_str: str) -> int:
        """计算剩余天数"""
        try:
            end_date = datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            days_left = (end_date - now).days
            return max(0, days_left)
        except:
            return 0
    
    def _get_current_multiplier_from_cache(self) -> Optional[Dict[str, Any]]:
        """从缓存获取当前时间段的倍率"""
        current_segment = self._get_time_segment_id()
        cache_data = self._load_multiplier_cache()
        
        segment_info = cache_data.get('segments', {}).get(current_segment)
        if segment_info:
            return {
                'multiplier': segment_info['multiplier'],
                'updated_at': segment_info['updated_at'],
                'source': segment_info.get('source', 'cache')
            }
        return None
    
    def _detect_multiplier_status(self) -> Dict[str, Any]:
        """智能倍率检测（缓存优先 + API补充）
        
        Returns:
            Dict[str, Any]: {
                "is_active": bool,      # 是否有倍率
                "value": int,           # 倍率值 (1, 2, 5, 10等)
                "is_time_based": bool,  # 是否基于时间段判断
                "source": str           # 数据来源
            }
        """
        # 1. 优先从当前时间段缓存获取
        cached_multiplier = self._get_current_multiplier_from_cache()
        if cached_multiplier:
            multiplier_value = cached_multiplier['multiplier']
            return {
                "is_active": multiplier_value > 1,
                "value": multiplier_value,
                "is_time_based": False,
                "source": f"segment_cache({cached_multiplier['source']})"
            }
        
        # 2. 缓存无数据，触发历史数据获取（会自动更新缓存）
        history_data = self.fetch_history_data(5)
        
        # 3. 再次检查缓存（可能已被更新）
        cached_multiplier = self._get_current_multiplier_from_cache()
        if cached_multiplier:
            multiplier_value = cached_multiplier['multiplier']
            return {
                "is_active": multiplier_value > 1,
                "value": multiplier_value,
                "is_time_based": False,
                "source": f"segment_cache_fresh({cached_multiplier['source']})"
            }
        
        # 4. 直接从API历史记录解析（备选方案）
        if history_data and "history" in history_data:
            for record in history_data["history"]:
                if record.get("reason") == "usage" and "details" in record:
                    details = record["details"]
                    multiplier_match = re.search(r'Time Multiplier\((\d+)\s*-\s*([^)]+)\)', details)
                    if multiplier_match:
                        multiplier_value = int(multiplier_match.group(1))
                        return {
                            "is_active": multiplier_value > 1,
                            "value": multiplier_value,
                            "is_time_based": False,
                            "source": "api_direct"
                        }
        
        # 5. 最后回退到传统时间段判断
        if self._is_high_multiplier_hours():
            return {
                "is_active": True,
                "value": 2,  # 传统时间段默认倍率
                "is_time_based": True,
                "source": "time_fallback"
            }
        
        return {
            "is_active": False,
            "value": 1,
            "is_time_based": True,
            "source": "time_fallback"
        }
    
    def _is_high_multiplier_hours(self) -> bool:
        """判断当前是否为高倍率时段"""
        now = datetime.now(timezone(timedelta(hours=8)))  # 北京时间
        
        # 工作日 (周一到周五)
        if now.weekday() >= 5:  # 周六、周日
            return False
            
        # 高倍率时段: 9:00-12:00, 14:00-18:00
        hour = now.hour
        return (9 <= hour < 12) or (14 <= hour < 18)
