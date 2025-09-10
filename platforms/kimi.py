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

        # Platform detection should be done via session-mappings.json, this is fallback only
        # Check token format as last resort
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
        import time

        log_message(
            "kimi-platform",
            "DEBUG",
            "Starting Kimi balance fetch",
            {
                "endpoint": "/users/me/balance",
                "api_base": self.api_base,
                "token_length": len(self.token) if self.token else 0,
                "token_prefix": (
                    self.token[:10] + "..."
                    if self.token and len(self.token) > 10
                    else self.token
                ),
                "rate_limit_interval": getattr(
                    self, "_min_request_interval", "not_set"
                ),
                "last_request_time": getattr(self, "_last_request_time", "not_set"),
                "current_time": time.time(),
            },
        )

        # Check rate limiting status
        if hasattr(self, "_last_request_time") and self._last_request_time > 0:
            elapsed = time.time() - self._last_request_time
            log_message(
                "kimi-platform",
                "DEBUG",
                "Rate limiting check",
                {
                    "elapsed_seconds": elapsed,
                    "min_interval": getattr(self, "_min_request_interval", "not_set"),
                    "can_make_request": elapsed
                    >= getattr(self, "_min_request_interval", 60),
                },
            )

        try:
            log_message(
                "kimi-platform",
                "DEBUG",
                "About to call make_request",
                {
                    "endpoint": "/users/me/balance",
                    "full_url": f"{self.api_base}/users/me/balance",
                },
            )

            result = self.make_request("/users/me/balance")

            log_message(
                "kimi-platform",
                "DEBUG",
                "make_request completed",
                {
                    "endpoint": "/users/me/balance",
                    "result_type": type(result).__name__,
                    "result_is_none": result is None,
                    "result_length": len(str(result)) if result else 0,
                },
            )

            if result is None:
                log_message(
                    "kimi-platform",
                    "WARNING",
                    "Kimi balance API returned None",
                    {
                        "endpoint": "/users/me/balance",
                        "possible_cause": "API request failed or returned empty data",
                        "session_closed": getattr(self, "_session_closed", "unknown"),
                        "session_exists": hasattr(self, "_session")
                        and self._session is not None,
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
                    "timestamp": time.time(),
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
                    "full_traceback": str(e),
                    "timestamp": time.time(),
                },
            )
            return None

    def fetch_subscription_data(self) -> Optional[Dict[str, Any]]:
        """Kimi doesn't have subscription endpoint, return None"""
        # Kimi API does not have subscription info endpoint
        return None

    def format_balance_display(self, balance_data: Dict[str, Any]) -> str:
        """Format Kimi balance for display"""
        from data.logger import log_message

        # Handle empty data case
        if balance_data is None:
            log_message(
                "kimi-platform",
                "INFO",
                "No balance data available for display",
                {"display": "nodata"},
            )
            return "KIMI.B:\033[90mNoData\033[0m"

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

            # Color codes based on available balance
            if available_balance <= 5:
                color = "\033[91m"  # Red
            elif available_balance <= 20:
                color = "\033[93m"  # Yellow
            else:
                color = "\033[92m"  # Green
            reset = "\033[0m"

            # Format display (use CNY instead of ¥ symbol to avoid encoding issues)
            balance_str = f"KIMI.B:{color}{available_balance:.2f}CNY{reset}"

            # Show voucher details if available (use English to avoid encoding issues)
            if voucher_balance > 0:
                balance_str += f" (V:{voucher_balance:.2f}"
                if cash_balance != 0:
                    balance_str += f", C:{cash_balance:.2f}"
                balance_str += ")"
            elif cash_balance != available_balance:
                balance_str += f" (C:{cash_balance:.2f})"

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
