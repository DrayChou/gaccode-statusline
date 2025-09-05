#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Base platform interface for multi-platform statusline support
"""

from abc import ABC, abstractmethod
import json
from typing import Dict, Any, Optional
import requests


class BasePlatform(ABC):
    """Base platform interface for API balance queries"""

    def __init__(self, token: str, config: Dict[str, Any]):
        self.token = token
        self.config = config
        self._session = requests.Session()

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

    def make_request(self, endpoint: str, timeout: int = 5) -> Optional[Dict[str, Any]]:
        """Make API request with error handling"""
        from data.logger import log_message

        log_message(
            f"{self.name}-platform",
            "DEBUG",
            "Starting API request",
            {
                "platform": self.name,
                "endpoint": endpoint,
                "full_url": f"{self.api_base}{endpoint}",
                "timeout": timeout,
            },
        )

        try:
            url = f"{self.api_base}{endpoint}"
            headers = self.get_headers()

            log_message(
                f"{self.name}-platform",
                "DEBUG",
                "API request details",
                {
                    "platform": self.name,
                    "url": url,
                    "headers_keys": list(headers.keys()),
                    "timeout": timeout,
                },
            )

            response = self._session.get(url, headers=headers, timeout=timeout)

            log_message(
                f"{self.name}-platform",
                "DEBUG",
                "API response received",
                {
                    "platform": self.name,
                    "endpoint": endpoint,
                    "status_code": response.status_code,
                    "response_headers_keys": list(response.headers.keys()),
                },
            )

            response.raise_for_status()

            try:
                json_data = response.json()
                log_message(
                    f"{self.name}-platform",
                    "INFO",
                    "API JSON parsing successful",
                    {
                        "platform": self.name,
                        "endpoint": endpoint,
                        "response_type": type(json_data).__name__,
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

        except requests.exceptions.Timeout as timeout_error:
            log_message(
                f"{self.name}-platform",
                "ERROR",
                "API request timeout",
                {
                    "platform": self.name,
                    "endpoint": endpoint,
                    "timeout": timeout,
                    "error": str(timeout_error),
                },
            )
            return None

        except requests.exceptions.ConnectionError as conn_error:
            log_message(
                f"{self.name}-platform",
                "ERROR",
                "API connection error",
                {
                    "platform": self.name,
                    "endpoint": endpoint,
                    "url": url,
                    "error": str(conn_error),
                },
            )
            return None

        except requests.exceptions.HTTPError as http_error:
            log_message(
                f"{self.name}-platform",
                "ERROR",
                "API HTTP error",
                {
                    "platform": self.name,
                    "endpoint": endpoint,
                    "status_code": (
                        http_error.response.status_code
                        if http_error.response
                        else "unknown"
                    ),
                    "error": str(http_error),
                },
            )
            return None

        except requests.RequestException as req_error:
            log_message(
                f"{self.name}-platform",
                "ERROR",
                "API request exception",
                {
                    "platform": self.name,
                    "endpoint": endpoint,
                    "error_type": type(req_error).__name__,
                    "error": str(req_error),
                },
            )
            return None

        except Exception as e:
            log_message(
                f"{self.name}-platform",
                "ERROR",
                "API unexpected exception",
                {
                    "platform": self.name,
                    "endpoint": endpoint,
                    "error_type": type(e).__name__,
                    "error": str(e),
                },
            )
            return None
