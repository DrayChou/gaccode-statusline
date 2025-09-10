#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Base platform interface for multi-platform statusline support
"""

from abc import ABC, abstractmethod
import json
from typing import Dict, Any, Optional
import requests
import time
from functools import wraps


class BasePlatform(ABC):
    """Base platform interface for API balance queries with retry and rate limiting"""

    def __init__(self, token: str, config: Dict[str, Any]):
        self.token = token
        self.config = config
        self._session = requests.Session()
        # 安全配置
        self._session.verify = True  # 强制SSL证书验证
        self._session.timeout = (5, 30)  # 连接超时5秒，读取超时30秒
        # 设置安全请求头
        self._session.headers.update(
            {
                "User-Agent": "GAC-Code-StatusLine/2.0",
                "Accept": "application/json",
                "Connection": "close",  # 防止连接复用泄露
            }
        )
        self._session_closed = False

        # Rate limiting and retry configuration
        self._last_request_time = 0
        self._min_request_interval = config.get(
            "rate_limit_interval", 60.0
        )  # seconds - default 1 minute
        self._max_retries = config.get("max_retries", 3)
        self._retry_delay = config.get("retry_delay", 2.0)  # seconds
        self._backoff_multiplier = config.get("backoff_multiplier", 2.0)

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensure session is closed"""
        self.close()

    def __del__(self):
        """Destructor - ensure session is closed"""
        self.close()

    def close(self):
        """Close the HTTP session"""
        if hasattr(self, "_session") and self._session and not self._session_closed:
            try:
                self._session.close()
                self._session_closed = True
            except Exception:
                # Ignore errors during cleanup
                pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Platform name"""
        pass

    @property
    @abstractmethod
    def api_base(self) -> str:
        """API base URL"""
        pass

    @abstractmethod
    def detect_platform(self, session_info: Dict[str, Any], token: str) -> bool:
        """Detect if this platform should be used"""
        pass

    @abstractmethod
    def fetch_balance_data(self) -> Optional[Dict[str, Any]]:
        """Fetch balance data from platform API"""
        pass

    @abstractmethod
    def fetch_subscription_data(self) -> Optional[Dict[str, Any]]:
        """Fetch subscription data from platform API"""
        pass

    @abstractmethod
    def format_balance_display(self, balance_data: Dict[str, Any]) -> str:
        """Format balance data for display"""
        pass

    @abstractmethod
    def format_subscription_display(self, subscription_data: Dict[str, Any]) -> str:
        """Format subscription data for display"""
        pass

    def get_headers(self) -> Dict[str, str]:
        """Get common headers for API requests"""
        return {
            "authorization": f"Bearer {self.token}",
            "content-type": "application/json",
        }

    def _rate_limit(self):
        """Apply rate limiting to API requests"""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_request_interval:
            sleep_time = self._min_request_interval - elapsed
            time.sleep(sleep_time)
        self._last_request_time = time.time()

    def _should_retry(self, exception: Exception, attempt: int) -> bool:
        """Determine if request should be retried based on exception type and attempt count"""
        if attempt >= self._max_retries:
            return False

        # Retry on specific exceptions
        retryable_exceptions = (
            requests.exceptions.Timeout,
            requests.exceptions.ConnectionError,
            requests.exceptions.HTTPError,
        )

        if isinstance(exception, requests.exceptions.HTTPError):
            # Retry on specific HTTP status codes
            if hasattr(exception, "response") and exception.response:
                status_code = exception.response.status_code
                # Retry on rate limiting (429) and server errors (5xx)
                return status_code == 429 or 500 <= status_code < 600

        return isinstance(exception, retryable_exceptions)

    def _calculate_retry_delay(self, attempt: int) -> float:
        """Calculate delay before next retry using exponential backoff"""
        return self._retry_delay * (self._backoff_multiplier**attempt)

    def make_request(self, endpoint: str, timeout: int = 5) -> Optional[Dict[str, Any]]:
        """Make API request with cross-process locking and rate limiting"""
        from data.logger import log_message
        from data.api_lock import api_request_lock

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

        # Use cross-process API locking
        with api_request_lock(
            self.name, endpoint, self._min_request_interval
        ) as can_proceed:
            if not can_proceed:
                log_message(
                    f"{self.name}-platform",
                    "INFO",
                    "API request blocked by cross-process rate limiting",
                    {
                        "platform": self.name,
                        "endpoint": endpoint,
                        "min_interval": self._min_request_interval,
                        "action": "using_cache_fallback",
                    },
                )
                return None  # 返回None，上层逻辑会使用缓存

            log_message(
                f"{self.name}-platform",
                "DEBUG",
                "Starting API request with retry mechanism",
                {
                    "platform": self.name,
                    "endpoint": endpoint,
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
                            "headers_keys": list(headers.keys()),
                            "timeout": timeout,
                        },
                    )

                    # 安全的HTTP请求
                    response = self._session.get(
                        url,
                        headers=headers,
                        timeout=timeout,
                        verify=True,  # 强制SSL验证
                        allow_redirects=False,  # 禁止自动重定向防止攻击
                    )

                    log_message(
                        f"{self.name}-platform",
                        "DEBUG",
                        "API response received",
                        {
                            "platform": self.name,
                            "endpoint": endpoint,
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
                            "API request successful",
                            {
                                "platform": self.name,
                                "endpoint": endpoint,
                                "response_type": type(json_data).__name__,
                                "attempt": attempt + 1,
                                "response_keys": (
                                    list(json_data.keys())
                                    if isinstance(json_data, dict)
                                    else "not_dict"
                                ),
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
                    f"API request failed after {self._max_retries + 1} attempts",
                    {
                        "platform": self.name,
                        "endpoint": endpoint,
                        "final_error": str(last_exception),
                        "error_type": type(last_exception).__name__,
                    },
                )

            return None
