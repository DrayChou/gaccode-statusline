#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GLM platform implementation
"""

from typing import Dict, Any, Optional
from .base import BasePlatform
from datetime import datetime, timezone, timedelta
import json
import sys
import time
from pathlib import Path

# Import unified cache manager
try:
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from cache import get_cache_manager
except ImportError:
    get_cache_manager = None


class GLMPlatform(BasePlatform):
    """GLM platform implementation for balance and subscription queries"""

    def __init__(self, token: str, config: Dict[str, Any]):
        super().__init__(token, config)
        # 使用统一的data目录
        data_dir = Path(__file__).parent.parent / "data"
        cache_dir = data_dir / "cache"
        self._balance_cache_file = cache_dir / "balance-cache-glm.json"
        self._subscription_cache_file = cache_dir / "subscription-cache-glm.json"

        # GLM API 专用频率限制配置
        self._min_request_interval = 30.0  # GLM API 要求最少30秒间隔

    @property
    def name(self) -> str:
        return "glm"

    @property
    def api_base(self) -> str:
        return "https://bigmodel.cn/api"

    def get_headers(self) -> Dict[str, str]:
        """Get headers for GLM API requests"""
        # GLM API使用JWT login_token
        login_token = self.config.get("login_token")
        if not login_token:
            raise ValueError("GLM platform requires login_token configuration")

        return {
            "accept": "application/json, text/plain, */*",
            "authorization": login_token,  # 直接使用完整的JWT token
            "content-type": "application/json",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
        }

    def has_valid_config(self) -> bool:
        """Check if GLM platform has valid configuration"""
        login_token = self.config.get("login_token")
        return bool(login_token and login_token.strip())

    def detect_platform(self, session_info: Dict[str, Any], token: str) -> bool:
        """Detect GLM platform"""
        # 平台检测应该通过session-mappings.json进行，这里只作为fallback
        # 检查token格式作为最后的手段
        if token and token.startswith("eyJhbGciOiJIUzUxMiJ9"):
            return True
        return False

  
    def fetch_balance_data(self) -> Optional[Dict[str, Any]]:
        """Fetch balance data from GLM API"""
        # 检查配置
        if not self.has_valid_config():
            return None

        # 尝试从缓存获取数据
        if get_cache_manager is not None:
            cache_manager = get_cache_manager()
            cache_entry = cache_manager.get("balance", "glm_balance")
            if cache_entry is not None:
                cache_entry.data["_data_source"] = "unified_cache"
                return cache_entry.data

        # 调用API获取最新数据
        api_data = self.make_request("/biz/account/query-customer-account-report")
        if api_data:
            # 保存到缓存（5分钟TTL）
            if get_cache_manager is not None:
                cache_manager = get_cache_manager()
                cache_manager.set("balance", "glm_balance", api_data, 300)
            api_data["_data_source"] = "direct_api"
            return api_data

        return None

    def fetch_subscription_data(self) -> Optional[Dict[str, Any]]:
        """Fetch subscription data from GLM API with persistent cache fallback"""
        # 检查配置
        if not self.has_valid_config():
            # 即使配置无效，也尝试返回缓存的订阅数据
            if get_cache_manager is not None:
                cache_manager = get_cache_manager()
                cache_entry = cache_manager.get("subscription", "glm_subscription")
                if cache_entry is not None:
                    cache_entry.data["_data_source"] = "fallback_cache"
                    return cache_entry.data
            return None

        # 尝试从缓存获取数据（仅在缓存未过期时）
        if get_cache_manager is not None:
            cache_manager = get_cache_manager()
            cache_entry = cache_manager.get("subscription", "glm_subscription")
            if cache_entry is not None:
                cache_entry.data["_data_source"] = "unified_cache"
                return cache_entry.data

        # 调用API获取最新数据
        api_data = self.make_request("/biz/subscription/list")
        if api_data:
            # 检查API响应是否包含有效订阅数据
            if isinstance(api_data, dict) and api_data.get("data") and api_data.get("success") is not False:
                # 保存到缓存（1小时TTL）
                if get_cache_manager is not None:
                    cache_manager = get_cache_manager()
                    cache_manager.set("subscription", "glm_subscription", api_data, 3600)
                api_data["_data_source"] = "direct_api"
                return api_data
            # 如果API返回错误，尝试使用缓存的订阅数据
            elif get_cache_manager is not None:
                cache_manager = get_cache_manager()
                cache_entry = cache_manager.get("subscription", "glm_subscription", ignore_ttl=True)
                if cache_entry is not None:
                    cache_entry.data["_data_source"] = "fallback_cache"
                    return cache_entry.data

        # 最后的备用方案：尝试使用过期的缓存数据
        if get_cache_manager is not None:
            cache_manager = get_cache_manager()
            cache_entry = cache_manager.get("subscription", "glm_subscription", ignore_ttl=True)
            if cache_entry is not None:
                cache_entry.data["_data_source"] = "expired_cache"
                return cache_entry.data

        return None

    def format_balance_display(self, balance_data: Dict[str, Any]) -> str:
        """Format GLM balance for display"""
        # 检查API返回的错误
        if balance_data.get("code") == 401:
            return f"\033[91m401\033[0m"
        elif balance_data.get("success") == False:
            code = balance_data.get("code", "ERROR")
            return f"\033[91m{code}\033[0m"

        # 检查是否有错误信息
        if "error" in balance_data:
            error_info = balance_data["error"]
            error_msg = error_info.get("message", "Unknown Error")
            error_code = error_info.get("code", "ERROR")
            return f"\033[91m{error_code}\033[0m"

        # GLM API 返回的数据结构
        if "data" not in balance_data:
            return f"\033[91mDATA_ERROR\033[0m"

        data = balance_data["data"]
        balance = data.get("availableBalance", 0)

        # 颜色代码
        if balance <= 0.1:
            color = "\033[91m"  # 红色
        elif balance <= 0.5:
            color = "\033[93m"  # 黄色
        else:
            color = "\033[92m"  # 绿色
        reset = "\033[0m"

        return f"{color}{balance:.6f}{reset}"

    def format_subscription_display(self, subscription_data: Dict[str, Any]) -> str:
        """Format GLM subscription for display with cache source awareness"""
        try:
            # GLM API 返回的数据结构
            if "data" not in subscription_data or not subscription_data["data"]:
                return ""

            subscriptions = subscription_data["data"]
            from datetime import datetime, timezone

            # 找到最合适的当前订阅
            current_subscription = None
            current_time = datetime.now(timezone.utc)

            for sub in subscriptions:
                # 只考虑有效且在当前周期的订阅
                if sub.get("status") != "VALID" or not sub.get("inCurrentPeriod"):
                    continue

                # 解析有效期限
                valid_str = sub.get("valid", "")
                if not valid_str:
                    continue

                try:
                    # 解析有效期限格式： "2025-09-18 14:51:18-2025-10-18 10:00:00"
                    if "-" in valid_str and " " in valid_str:
                        # 处理格式：YYYY-MM-DD HH:MM:SS-YYYY-MM-DD HH:MM:SS
                        # 分割出开始和结束部分
                        parts = valid_str.split("-")
                        if len(parts) >= 6:  # YYYY-MM-DD HH:MM:SS-YYYY-MM-DD HH:MM:SS
                            # 结束日期是最后三个部分
                            end_year = parts[-3]
                            end_month = parts[-2]
                            end_day = parts[-1].split(" ")[0]  # 去掉时间部分

                            end_date_str = f"{end_year}-{end_month}-{end_day}"
                            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)

                            # 检查是否未过期
                            if end_date >= current_time:
                                # 如果还没有找到订阅，或者这个订阅的结束时间更近，就选择它
                                if current_subscription is None or end_date < current_subscription.get("_end_date", datetime.max.replace(tzinfo=timezone.utc)):
                                    sub["_end_date"] = end_date
                                    current_subscription = sub
                except Exception:
                    continue

            if not current_subscription:
                return ""

            product_name = current_subscription.get("productName", "")
            next_renew_time = current_subscription.get("nextRenewTime", "")

            if not product_name or not next_renew_time:
                return ""

            # 格式化下次续费时间
            try:
                # 如果是日期格式 "2025-10-18"，简化为 "10-18"
                if "-" in next_renew_time:
                    renew_date = next_renew_time[5:]  # 去掉年份部分
                else:
                    # 如果是其他格式，尝试解析
                    renew_date = next_renew_time
            except:
                renew_date = next_renew_time

            # 检查数据源并添加相应标识
            data_source = subscription_data.get("_data_source", "direct_api")

            # 基础订阅信息显示
            base_display = f"Sub:{product_name}({renew_date})"

            # 根据数据源添加状态指示
            if data_source == "expired_cache":
                return f"{base_display}\033[90m[cache]\033[0m"  # 灰色表示过期缓存
            elif data_source == "fallback_cache":
                return f"{base_display}\033[93m[cache]\033[0m"   # 黄色表示API失败后的缓存
            elif data_source == "unified_cache":
                return f"{base_display}\033[92m[cache]\033[0m"   # 绿色表示有效缓存
            else:
                return base_display  # 直接API数据，无标识

        except Exception:
            return "Sub:Error"

    def make_request(
        self,
        endpoint: str,
        method: str = "GET",
        data: Dict[str, Any] = None,
        timeout: int = 10,
    ) -> Optional[Dict[str, Any]]:
        """Make API request with support for GET and POST methods"""
        from data.logger import log_message

        # Check if session is still available
        if self._session_closed or not self._session:
            log_message(
                f"{self.name}-platform",
                "ERROR",
                "Cannot make request: session is closed",
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
                        allow_redirects=False,
                    )
                else:
                    response = self._session.get(
                        url,
                        headers=headers,
                        timeout=timeout,
                        verify=True,
                        allow_redirects=False,
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

        # All retries exhausted - log final error and return error info
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

            # Return error information for display
            error_info = {
                "error": {
                    "code": self._get_error_code(last_exception),
                    "message": str(last_exception)
                }
            }
            return error_info

        return None

    def _get_error_code(self, exception) -> str:
        """Extract error code from exception"""
        import requests

        if isinstance(exception, requests.exceptions.HTTPError):
            status_code = exception.response.status_code
            if status_code == 401:
                return "401"
            elif status_code == 403:
                return "403"
            elif status_code == 429:
                return "429"
            elif status_code >= 500:
                return f"5{status_code % 100}"
            else:
                return str(status_code)
        elif isinstance(exception, requests.exceptions.ConnectionError):
            return "CONN"
        elif isinstance(exception, requests.exceptions.Timeout):
            return "TIMEOUT"
        elif isinstance(exception, ValueError) and "login_token" in str(exception):
            return "TOKEN"
        else:
            return "ERROR"

    # 重写基类的后台任务方法
    def get_background_task_config(self) -> Dict[str, Any]:
        """GLM平台特定的后台任务配置"""
        base_config = super().get_background_task_config()

        # 自定义GLM的任务配置
        base_config.update({
            "balance_check": {
                "interval": 300,  # 5分钟
                "enabled": True,
                "method": "fetch_balance_data"
            },
            "cache_cleanup": {
                "interval": 3600,  # 1小时
                "enabled": True,
                "method": "_cleanup_expired_cache"
            }
        })

        return base_config

    def _cleanup_expired_cache(self) -> None:
        """GLM特定的缓存清理"""
        import glob
        from pathlib import Path

        cache_dir = Path(__file__).parent.parent / "data" / "cache"
        cleaned_count = 0

        # 清理GLM特定的缓存文件
        glm_cache_patterns = [
            "balance-cache-glm.json",
            "subscription-cache-glm.json"
        ]

        for pattern in glm_cache_patterns:
            for cache_file in cache_dir.glob(pattern):
                try:
                    # 检查文件年龄
                    if cache_file.exists():
                        file_age = time.time() - cache_file.stat().st_mtime
                        # 清理超过6小时的缓存
                        if file_age > 6 * 3600:
                            cache_file.unlink()
                            cleaned_count += 1
                except Exception:
                    pass

        if cleaned_count > 0:
            print(f"GLM: Cleaned {cleaned_count} expired cache files")