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
import sys
import time
from pathlib import Path

# Import unified cache manager
try:
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from cache import get_cache_manager
except ImportError:
    get_cache_manager = None  # 向后兼容


class GACCodePlatform(BasePlatform):
    """GAC Code platform implementation with 30-minute time-segment caching"""

    def __init__(self, token: str, config: Dict[str, Any]):
        super().__init__(token, config)
        # 使用统一的data目录
        data_dir = Path(__file__).parent.parent / "data"
        cache_dir = data_dir / "cache"
        self._multiplier_cache_file = cache_dir / "gac-multiplier-segments.json"
        self._history_cache_file = cache_dir / "gac-history-cache.json"
        self._balance_cache_file = cache_dir / "balance-cache-gaccode.json"
        self._subscription_cache_file = cache_dir / "subscription-cache-gaccode.json"
        self._refill_cache_file = cache_dir / "gac-refill-cache.json"
        
        # GAC API 专用频率限制配置 - 防止被封杀  
        self._min_request_interval = 60.0  # GAC API 要求最少1分钟间隔
        
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
        login_token = self.config.get("login_token")
        if login_token:
            return {
                "accept": "*/*",
                "accept-language": "zh",
                "authorization": f"Bearer {login_token}",
                "content-type": "application/json",
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
            }
        else:
            # 回退到基础token（虽然可能无效）
            return {
                "accept": "*/*",
                "authorization": f"Bearer {self.token}",
                "content-type": "application/json",
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
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
            with open(cache_file, "r", encoding="utf-8-sig") as f:
                cache_data = json.load(f)

            # 使用内容中的时间戳而不是文件修改时间
            cached_at_str = cache_data.get("cached_at")
            if not cached_at_str:
                return False

            cached_at = datetime.fromisoformat(cached_at_str)
            current_time = datetime.now()
            age_seconds = (current_time - cached_at).total_seconds()

            return age_seconds < ttl_seconds
        except Exception:
            return False

    def _load_cache_data(self, cache_file: Path) -> Optional[Dict[str, Any]]:
        """加载缓存数据"""
        if not cache_file.exists():
            return None

        try:
            with open(cache_file, "r", encoding="utf-8-sig") as f:
                cache_data = json.load(f)
            return cache_data.get("data")
        except Exception:
            return None

    def _save_cache_data(
        self, cache_file: Path, data: Dict[str, Any], ttl_seconds: int
    ) -> None:
        """保存数据到缓存"""
        try:
            cache_data = {
                "data": data,
                "cached_at": datetime.now().isoformat(),
                "ttl": ttl_seconds,
            }
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass  # 缓存保存失败不影响主流程

    def fetch_balance_data(self) -> Optional[Dict[str, Any]]:
        """Fetch balance data from GAC Code API (5分钟缓存，失败时使用过期缓存)"""
        if get_cache_manager is not None:
            # 使用统一缓存系统
            cache_manager = get_cache_manager()

            # 尝试从缓存获取数据
            cache_entry = cache_manager.get("balance", "gaccode_balance")
            if cache_entry is not None:
                return cache_entry.data

            # 缓存未命中，调用API
            api_data = self.make_request("/credits/balance")
            if api_data:
                # 保存到缓存（5分钟TTL）
                cache_manager.set("balance", "gaccode_balance", api_data, 300)
                return api_data

            # API调用失败，尝试获取过期缓存数据
            # 注意：统一缓存系统会自动清理过期数据，但我们可以手动检查磁盘文件
            return self._get_fallback_cache_data()
        else:
            # 向后兼容的旧缓存逻辑
            if self._is_cache_valid(self._balance_cache_file, 300):
                cached_data = self._load_cache_data(self._balance_cache_file)
                if cached_data:
                    return cached_data

            # 缓存无效或不存在，调用API
            api_data = self.make_request("/credits/balance")
            if api_data:
                # 检查是否需要自动重置积分
                self._check_and_auto_refill(api_data)
                
                # 保存到缓存（5分钟TTL）
                self._save_cache_data(self._balance_cache_file, api_data, 300)
                return api_data

            # API调用失败，尝试使用过期缓存作为备选方案
            cached_data = self._load_cache_data(self._balance_cache_file)
            if cached_data:
                return cached_data

        return None

    def _get_fallback_cache_data(self) -> Optional[Dict[str, Any]]:
        """获取备用缓存数据（即使过期也返回）"""
        try:
            cached_data = self._load_cache_data(self._balance_cache_file)
            if cached_data:
                return cached_data
        except Exception:
            pass
        return None

    def fetch_subscription_data(self) -> Optional[Dict[str, Any]]:
        """Fetch subscription data from GAC Code API (5分钟缓存，失败时使用过期缓存)"""
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

        # API调用失败，尝试使用过期缓存作为备选方案
        cached_data = self._load_cache_data(self._subscription_cache_file)
        if cached_data:
            return cached_data

        return None

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
            with open(self._multiplier_cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"segments": {}, "last_updated": None}

    def _save_multiplier_cache(self, cache_data: Dict[str, Any]) -> None:
        """保存倍率缓存数据"""
        try:
            with open(self._multiplier_cache_file, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass  # 缓存保存失败不影响主流程

    def _should_update_history_cache(self) -> bool:
        """判断是否需要更新历史缓存（5分钟轮询，基于内容时间戳）"""
        if not self._history_cache_file.exists():
            return True

        try:
            with open(self._history_cache_file, "r", encoding="utf-8") as f:
                cache_data = json.load(f)

            cached_at_str = cache_data.get("cached_at")
            if not cached_at_str:
                return True

            cached_at = datetime.fromisoformat(cached_at_str)
            current_time = datetime.now()
            age_seconds = (current_time - cached_at).total_seconds()

            return age_seconds > 300  # 5分钟
        except Exception:
            return True

    def fetch_history_data(self, limit: int = 10) -> Optional[Dict[str, Any]]:
        """获取使用历史数据（带5分钟缓存）"""
        # 检查是否需要更新缓存
        if not self._should_update_history_cache():
            try:
                with open(self._history_cache_file, "r", encoding="utf-8") as f:
                    cached_data = json.load(f)
                return cached_data.get("data")
            except Exception:
                pass  # 缓存读取失败，继续API调用

        # 调用API获取最新数据
        api_data = self.make_request(f"/credits/history?limit={limit}")
        if api_data:
            # 更新历史缓存
            try:
                cache_data = {
                    "data": api_data,
                    "cached_at": datetime.now().isoformat(),
                    "ttl": 300,  # 5分钟TTL
                }
                with open(self._history_cache_file, "w", encoding="utf-8") as f:
                    json.dump(cache_data, f, ensure_ascii=False, indent=2)
            except Exception:
                pass  # 缓存保存失败不影响返回

            # 更新倍率时间段缓存
            self._update_multiplier_segments_from_history(api_data)
            return api_data

        # API调用失败，尝试使用已有缓存
        try:
            with open(self._history_cache_file, "r", encoding="utf-8") as f:
                cached_data = json.load(f)
            return cached_data.get("data")
        except Exception:
            return None

    def _update_multiplier_segments_from_history(
        self, history_data: Dict[str, Any]
    ) -> None:
        """根据历史数据更新倍率时间段缓存"""
        if not history_data or "history" not in history_data:
            return

        cache_data = self._load_multiplier_cache()
        updated = False

        for record in history_data["history"]:
            if record.get("reason") != "usage" or "details" not in record:
                continue

            # 解析倍率
            details = record["details"]
            multiplier_match = re.search(
                r"Time Multiplier\((\d+)\s*-\s*([^)]+)\)", details
            )
            if not multiplier_match:
                continue

            multiplier_value = int(multiplier_match.group(1))

            # 解析记录时间
            try:
                created_at = datetime.fromisoformat(
                    record["createdAt"].replace("Z", "+00:00")
                )
                beijing_time = created_at.astimezone(timezone(timedelta(hours=8)))
                segment_id = self._get_time_segment_id(beijing_time)

                # 更新对应时间段的倍率
                cache_data["segments"][segment_id] = {
                    "multiplier": multiplier_value,
                    "updated_at": datetime.now().isoformat(),
                    "source_time": beijing_time.isoformat(),
                    "source": "api_history",
                }
                updated = True

            except Exception:
                continue  # 解析失败跳过该记录

        if updated:
            cache_data["last_updated"] = datetime.now().isoformat()
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

        segment_info = cache_data.get("segments", {}).get(current_segment)
        if segment_info:
            return {
                "multiplier": segment_info["multiplier"],
                "updated_at": segment_info["updated_at"],
                "source": segment_info.get("source", "cache"),
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
            multiplier_value = cached_multiplier["multiplier"]
            return {
                "is_active": multiplier_value > 1,
                "value": multiplier_value,
                "is_time_based": False,
                "source": f"segment_cache({cached_multiplier['source']})",
            }

        # 2. 缓存无数据，触发历史数据获取（会自动更新缓存）
        history_data = self.fetch_history_data(5)

        # 3. 再次检查缓存（可能已被更新）
        cached_multiplier = self._get_current_multiplier_from_cache()
        if cached_multiplier:
            multiplier_value = cached_multiplier["multiplier"]
            return {
                "is_active": multiplier_value > 1,
                "value": multiplier_value,
                "is_time_based": False,
                "source": f"segment_cache_fresh({cached_multiplier['source']})",
            }

        # 4. 直接从API历史记录解析（备选方案）
        if history_data and "history" in history_data:
            for record in history_data["history"]:
                if record.get("reason") == "usage" and "details" in record:
                    details = record["details"]
                    multiplier_match = re.search(
                        r"Time Multiplier\((\d+)\s*-\s*([^)]+)\)", details
                    )
                    if multiplier_match:
                        multiplier_value = int(multiplier_match.group(1))
                        return {
                            "is_active": multiplier_value > 1,
                            "value": multiplier_value,
                            "is_time_based": False,
                            "source": "api_direct",
                        }

        # 5. 最后回退到传统时间段判断
        if self._is_high_multiplier_hours():
            return {
                "is_active": True,
                "value": 2,  # 传统时间段默认倍率
                "is_time_based": True,
                "source": "time_fallback",
            }

        return {
            "is_active": False,
            "value": 1,
            "is_time_based": True,
            "source": "time_fallback",
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

    def make_request(self, endpoint: str, method: str = "GET", data: Dict[str, Any] = None, timeout: int = 5) -> Optional[Dict[str, Any]]:
        """Make API request with support for GET and POST methods"""
        from data.logger import log_message

        # Check if session is still available
        if self._session_closed or not self._session:
            log_message(
                f"{self.name}-platform",
                "ERROR", 
                "Cannot make request: session is closed"
            )
            return None
        
        url = f"{self.api_base}{endpoint}"
        headers = self.get_headers()
        
        log_message(
            f"{self.name}-platform",
            "DEBUG",
            f"Starting {method} API request with retry mechanism",
            {
                "platform": self.name,
                "endpoint": endpoint,
                "method": method,
                "full_url": url,
                "timeout": timeout,
                "max_retries": self._max_retries,
            },
        )
        
        last_exception = None
        
        for attempt in range(self._max_retries + 1):
            try:
                # Apply rate limiting
                self._rate_limit()
                
                log_message(
                    f"{self.name}-platform",
                    "DEBUG",
                    f"API request attempt {attempt + 1}/{self._max_retries + 1}",
                    {
                        "platform": self.name,
                        "url": url,
                        "method": method,
                        "timeout": timeout,
                    },
                )

                # Make HTTP request based on method
                if method.upper() == "POST":
                    response = self._session.post(
                        url, 
                        headers=headers, 
                        json=data,
                        timeout=timeout,
                        verify=True,
                        allow_redirects=False
                    )
                else:
                    response = self._session.get(
                        url, 
                        headers=headers, 
                        timeout=timeout,
                        verify=True,
                        allow_redirects=False
                    )

                log_message(
                    f"{self.name}-platform",
                    "DEBUG",
                    "API response received",
                    {
                        "platform": self.name,
                        "endpoint": endpoint,
                        "method": method,
                        "status_code": response.status_code,
                        "attempt": attempt + 1,
                    },
                )

                response.raise_for_status()

                # Success - parse JSON and return
                try:
                    json_data = response.json()
                    log_message(
                        f"{self.name}-platform",
                        "INFO",
                        f"{method} API request successful",
                        {
                            "platform": self.name,
                            "endpoint": endpoint,
                            "method": method,
                            "response_type": type(json_data).__name__,
                            "attempt": attempt + 1,
                        },
                    )
                    return json_data
                except json.JSONDecodeError as json_error:
                    log_message(
                        f"{self.name}-platform",
                        "ERROR",
                        "API JSON parsing failed",
                        {
                            "platform": self.name,
                            "endpoint": endpoint,
                            "method": method,
                            "status_code": response.status_code,
                            "response_text": response.text[:200],
                            "json_error": str(json_error),
                        },
                    )
                    return None

            except Exception as e:
                last_exception = e
                
                # Check if we should retry
                if not self._should_retry(e, attempt):
                    break
                
                # Calculate delay before retry
                if attempt < self._max_retries:
                    delay = self._calculate_retry_delay(attempt)
                    log_message(
                        f"{self.name}-platform",
                        "WARNING",
                        f"Request failed, retrying in {delay:.1f}s",
                        {
                            "platform": self.name,
                            "endpoint": endpoint,
                            "method": method,
                            "attempt": attempt + 1,
                            "error": str(e),
                            "error_type": type(e).__name__,
                            "retry_delay": delay,
                        },
                    )
                    time.sleep(delay)
                else:
                    break
        
        # All retries exhausted - log final error
        if last_exception:
            log_message(
                f"{self.name}-platform",
                "ERROR",
                f"{method} API request failed after {self._max_retries + 1} attempts",
                {
                    "platform": self.name,
                    "endpoint": endpoint,
                    "method": method,
                    "final_error": str(last_exception),
                    "error_type": type(last_exception).__name__,
                },
            )
        
        return None

    def _check_and_auto_refill(self, balance_data: Dict[str, Any]) -> None:
        """检查余额并在需要时自动重置积分"""
        try:
            balance = balance_data.get("balance", 0)
            if balance <= 0 and self._should_auto_refill():
                self._perform_refill()
        except Exception:
            pass  # 自动重置失败不影响主流程

    def _should_auto_refill(self) -> bool:
        """判断是否应该进行自动重置（优先检查API，备选本地缓存）"""
        # 优先使用API检查今日是否已有重置记录
        if not self._check_today_refill_from_api():
            return True  # API检查显示今日没有重置记录，允许重置
        
        # API显示已有重置记录，禁止重复重置
        return False

    def _check_today_refill_from_api(self) -> bool:
        """通过API检查今日是否已有重置记录（遵守频率限制）"""
        try:
            # 检查上次API调用时间，防止过于频繁的请求
            current_time = time.time()
            if (current_time - self._last_request_time) < 60.0:  # 1分钟限制
                # 距离上次请求不足1分钟，使用缓存检查
                return self._check_today_refill_from_cache()
            
            # 调用工单历史API，获取最近的记录
            tickets_data = self.make_request("/tickets?page=1&limit=10")
            if not tickets_data or "tickets" not in tickets_data:
                return False  # API失败，默认为没有记录
            
            today = datetime.now().date()
            
            # 检查每个工单是否为今日的积分重置请求
            for ticket in tickets_data["tickets"]:
                if (ticket.get("categoryId") == 3 and 
                    ticket.get("title") == "请求重置积分"):
                    
                    # 解析创建时间
                    created_at_str = ticket.get("createdAt")
                    if created_at_str:
                        try:
                            created_at = datetime.fromisoformat(
                                created_at_str.replace("Z", "+00:00")
                            )
                            # 转换为北京时间进行比较
                            beijing_time = created_at.astimezone(timezone(timedelta(hours=8)))
                            ticket_date = beijing_time.date()
                            
                            if ticket_date == today:
                                return True  # 找到今日的重置记录
                        except Exception:
                            continue  # 时间解析失败，跳过该记录
            
            return False  # 没有找到今日的重置记录
            
        except Exception:
            # API调用失败或频率限制，回退到本地缓存检查
            return self._check_today_refill_from_cache()
    
    def _check_today_refill_from_cache(self) -> bool:
        """从本地缓存检查今日是否已重置（备选方案）"""
        today = datetime.now().date().isoformat()
        
        if self._refill_cache_file.exists():
            try:
                with open(self._refill_cache_file, "r", encoding="utf-8-sig") as f:
                    refill_data = json.load(f)
                last_refill_date = refill_data.get("last_refill_date")
                return last_refill_date == today  # 返回是否为今日
            except Exception:
                return False  # 缓存读取失败，默认为没有记录
        
        return False  # 无缓存记录

    def _perform_refill(self) -> bool:
        """执行积分重置操作"""
        try:
            # 调用积分重置API
            refill_data = {
                "categoryId": 3,
                "title": "请求重置积分",
                "description": "",
                "language": "zh"
            }
            
            response = self.make_request("/tickets", method="POST", data=refill_data)
            if response and response.get("message") == "工单创建成功":
                # 更新本地缓存记录（备用）
                self._update_refill_cache()
                return True
            
            return False
        except Exception:
            return False

    def _update_refill_cache(self) -> None:
        """更新重置记录缓存"""
        try:
            today = datetime.now().date().isoformat()
            refill_record = {
                "last_refill_date": today,
                "refill_count": 1,
                "updated_at": datetime.now().isoformat()
            }
            
            with open(self._refill_cache_file, "w", encoding="utf-8") as f:
                json.dump(refill_record, f, ensure_ascii=False, indent=2)
        except Exception:
            pass  # 缓存更新失败不影响重置操作
