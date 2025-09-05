#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Kimi platform implementation
"""

from typing import Dict, Any, Optional
from .base import BasePlatform


class KimiPlatform(BasePlatform):
    """Kimi platform implementation"""

    @property
    def name(self) -> str:
        return "kimi"

    @property
    def api_base(self) -> str:
        return "https://api.moonshot.cn/v1"

    def detect_platform(self, session_info: Dict[str, Any], token: str) -> bool:
        """Detect Kimi platform"""
        from data.logger import log_message

        log_message(
            "kimi-platform",
            "DEBUG",
            "Starting Kimi platform detection",
            {
                "token_prefix": (
                    token[:10] + "..." if token and len(token) > 10 else token
                ),
                "token_length": len(token) if token else 0,
            },
        )

        # 平台检测应该通过session-mappings.json进行，这里只作为fallback
        # 检查token格式作为最后的手段
        if token and token.startswith("sk-"):
            log_message(
                "kimi-platform",
                "INFO",
                "Kimi detected by token format",
                {"method": "token_prefix"},
            )
            return True

        log_message("kimi-platform", "DEBUG", "Kimi platform not detected")
        return False

    def fetch_balance_data(self) -> Optional[Dict[str, Any]]:
        """Fetch balance data from Kimi API"""
        from data.logger import log_message

        log_message(
            "kimi-platform",
            "DEBUG",
            "Starting Kimi balance fetch",
            {
                "endpoint": "/users/me/balance",
                "token_length": len(self.token) if self.token else 0,
                "token_prefix": (
                    self.token[:10] + "..."
                    if self.token and len(self.token) > 10
                    else self.token
                ),
            },
        )

        try:
            result = self.make_request("/users/me/balance")

            if result is None:
                log_message(
                    "kimi-platform",
                    "WARNING",
                    "Kimi balance API returned None",
                    {
                        "endpoint": "/users/me/balance",
                        "possible_cause": "API request failed or returned empty data",
                    },
                )
                return None

            log_message(
                "kimi-platform",
                "INFO",
                "Kimi balance API request successful",
                {
                    "endpoint": "/users/me/balance",
                    "response_keys": (
                        list(result.keys()) if isinstance(result, dict) else "not_dict"
                    ),
                    "response_code": (
                        result.get("code") if isinstance(result, dict) else None
                    ),
                    "response_status": (
                        result.get("status") if isinstance(result, dict) else None
                    ),
                },
            )

            return result

        except Exception as e:
            log_message(
                "kimi-platform",
                "ERROR",
                "Exception in Kimi balance fetch",
                {
                    "endpoint": "/users/me/balance",
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
            )
            return None

    def fetch_subscription_data(self) -> Optional[Dict[str, Any]]:
        """Kimi doesn't have subscription endpoint, return None"""
        # Kimi API 没有订阅信息接口
        return None

    def format_balance_display(self, balance_data: Dict[str, Any]) -> str:
        """Format Kimi balance for display"""
        from data.logger import log_message

        log_message(
            "kimi-platform",
            "DEBUG",
            "Starting Kimi balance formatting",
            {
                "balance_data_keys": (
                    list(balance_data.keys())
                    if isinstance(balance_data, dict)
                    else "not_dict"
                ),
                "balance_data_type": type(balance_data).__name__,
            },
        )

        try:
            if not isinstance(balance_data, dict):
                log_message(
                    "kimi-platform",
                    "WARNING",
                    "Balance data is not a dictionary",
                    {
                        "type": type(balance_data).__name__,
                        "value": str(balance_data)[:100],
                    },
                )
                return "KIMI.B:Error(InvalidData)"

            if balance_data.get("code") != 0 or not balance_data.get("status"):
                log_message(
                    "kimi-platform",
                    "WARNING",
                    "Kimi balance API error response",
                    {
                        "code": balance_data.get("code"),
                        "status": balance_data.get("status"),
                        "message": balance_data.get("message", "No message"),
                    },
                )
                return "KIMI.B:Error"

            data = balance_data["data"]
            log_message(
                "kimi-platform",
                "DEBUG",
                "Kimi balance data structure",
                {
                    "data_keys": (
                        list(data.keys()) if isinstance(data, dict) else "not_dict"
                    ),
                    "data_type": type(data).__name__,
                },
            )

            required_fields = ["available_balance", "voucher_balance", "cash_balance"]
            missing_fields = [field for field in required_fields if field not in data]

            if missing_fields:
                log_message(
                    "kimi-platform",
                    "WARNING",
                    "Missing required balance fields",
                    {
                        "missing_fields": missing_fields,
                        "available_fields": (
                            list(data.keys()) if isinstance(data, dict) else []
                        ),
                    },
                )
                return "KIMI.B:Error(MissingFields)"

            available_balance = data["available_balance"]
            voucher_balance = data["voucher_balance"]
            cash_balance = data["cash_balance"]

            log_message(
                "kimi-platform",
                "INFO",
                "Kimi balance data parsed successfully",
                {
                    "available_balance": available_balance,
                    "voucher_balance": voucher_balance,
                    "cash_balance": cash_balance,
                    "total_balance": available_balance + voucher_balance + cash_balance,
                },
            )

            # 颜色代码基于可用余额
            if available_balance <= 5:
                color = "\033[91m"  # 红色
            elif available_balance <= 20:
                color = "\033[93m"  # 黄色
            else:
                color = "\033[92m"  # 绿色
            reset = "\033[0m"

            # 格式化显示
            balance_str = f"KIMI.B:{color}¥{available_balance:.2f}{reset}"

            # 如果有代金券余额，显示详细信息
            if voucher_balance > 0:
                balance_str += f" (券:¥{voucher_balance:.2f}"
                if cash_balance != 0:
                    balance_str += f", 现金:¥{cash_balance:.2f}"
                balance_str += ")"
            elif cash_balance != available_balance:
                balance_str += f" (现金:¥{cash_balance:.2f})"

            log_message(
                "kimi-platform",
                "DEBUG",
                "Kimi balance formatting completed",
                {
                    "final_display": balance_str,
                    "color_used": (
                        "red"
                        if available_balance <= 5
                        else "yellow" if available_balance <= 20 else "green"
                    ),
                },
            )

            return balance_str

        except Exception as e:
            log_message(
                "kimi-platform",
                "ERROR",
                "Exception in Kimi balance formatting",
                {
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "balance_data_sample": (
                        str(balance_data)[:100] if balance_data else "None"
                    ),
                },
            )
            return f"KIMI.B:Error({str(e)[:20]})"

    def format_subscription_display(self, subscription_data: Dict[str, Any]) -> str:
        """Kimi doesn't have subscription info"""
        return ""

    def get_headers(self) -> Dict[str, str]:
        """Get Kimi API headers"""
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
