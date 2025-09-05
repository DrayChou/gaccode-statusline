#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SiliconFlow platform implementation
"""

from typing import Dict, Any, Optional
from .base import BasePlatform
import sys
from pathlib import Path

# Import logger system
try:
    from data.logger import log_message
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent.parent / "data"))
    from logger import log_message


class SiliconFlowPlatform(BasePlatform):
    """SiliconFlow platform implementation"""

    @property
    def name(self) -> str:
        return "siliconflow"

    @property
    def api_base(self) -> str:
        return "https://api.siliconflow.cn/v1"

    def detect_platform(self, session_info: Dict[str, Any], token: str) -> bool:
        """Detect SiliconFlow platform"""
        log_message(
            "siliconflow-platform",
            "DEBUG",
            "Starting SiliconFlow platform detection",
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
                "siliconflow-platform",
                "INFO",
                "SiliconFlow detected by token format",
                {"method": "token_prefix", "token_prefix": token[:10] + "..."},
            )
            return True

        log_message(
            "siliconflow-platform", "DEBUG", "SiliconFlow platform not detected"
        )
        return False

    def fetch_balance_data(self) -> Optional[Dict[str, Any]]:
        """Fetch balance data from SiliconFlow API"""
        log_message(
            "siliconflow-platform",
            "DEBUG",
            "Starting SiliconFlow balance fetch",
            {
                "endpoint": "/user/info",
                "token_length": len(self.token) if self.token else 0,
                "token_prefix": (
                    self.token[:10] + "..."
                    if self.token and len(self.token) > 10
                    else self.token
                ),
            },
        )

        balance_data = self.make_request("/user/info")

        if balance_data:
            log_message(
                "siliconflow-platform",
                "INFO",
                "SiliconFlow balance data fetched successfully",
                {
                    "data_keys": list(balance_data.keys()),
                    "data_type": type(balance_data).__name__,
                    "has_data": "data" in balance_data,
                },
            )

            if isinstance(balance_data, dict) and "data" in balance_data:
                data = balance_data["data"]
                log_message(
                    "siliconflow-platform",
                    "DEBUG",
                    "SiliconFlow balance data structure",
                    {
                        "data_keys": (
                            list(data.keys()) if isinstance(data, dict) else "not_dict"
                        ),
                        "data_type": type(data).__name__,
                    },
                )
        else:
            log_message(
                "siliconflow-platform",
                "WARNING",
                "SiliconFlow balance API returned None",
                {"possible_cause": "API request failed or returned empty data"},
            )

        return balance_data

    def fetch_subscription_data(self) -> Optional[Dict[str, Any]]:
        """SiliconFlow doesn't have separate subscription endpoint"""
        return None

    def format_balance_display(self, balance_data: Dict[str, Any]) -> str:
        """Format SiliconFlow balance for display"""
        log_message(
            "siliconflow-platform",
            "DEBUG",
            "Starting SiliconFlow balance formatting",
            {
                "balance_data_keys": list(balance_data.keys()),
                "balance_data_type": type(balance_data).__name__,
            },
        )

        try:
            if balance_data.get("code") != 20000 or not balance_data.get("status"):
                log_message(
                    "siliconflow-platform",
                    "ERROR",
                    "SiliconFlow API returned error status",
                    {
                        "code": balance_data.get("code"),
                        "status": balance_data.get("status"),
                        "message": balance_data.get("message", "No message"),
                    },
                )
                return "SiliconFlow.B:Error"

            data = balance_data["data"]
            log_message(
                "siliconflow-platform",
                "DEBUG",
                "SiliconFlow balance data structure",
                {
                    "data_keys": (
                        list(data.keys()) if isinstance(data, dict) else "not_dict"
                    ),
                    "data_type": type(data).__name__,
                },
            )

            total_balance = float(data.get("totalBalance", 0))
            balance = float(data.get("balance", 0))
            charge_balance = float(data.get("chargeBalance", 0))

            log_message(
                "siliconflow-platform",
                "DEBUG",
                "SiliconFlow balance components",
                {
                    "total_balance": total_balance,
                    "balance": balance,
                    "charge_balance": charge_balance,
                },
            )

            # 颜色代码基于总余额
            if total_balance <= 5:
                color = "\033[91m"  # 红色
                color_name = "red"
            elif total_balance <= 20:
                color = "\033[93m"  # 黄色
                color_name = "yellow"
            else:
                color = "\033[92m"  # 绿色
                color_name = "green"
            reset = "\033[0m"

            # 格式化显示 - 显示总余额
            balance_str = f"SiliconFlow.B:{color}¥{total_balance:.2f}{reset}"

            # 如果有详细信息，显示分解
            if charge_balance > 0 or balance != total_balance:
                details = []
                if charge_balance > 0:
                    details.append(f"M:¥{charge_balance:.2f}")
                if balance > 0 and balance != charge_balance:
                    details.append(f"F:¥{balance:.2f}")

                if details:
                    balance_str += f" ({', '.join(details)})"

                log_message(
                    "siliconflow-platform",
                    "DEBUG",
                    "SiliconFlow balance details added",
                    {"details": details, "final_balance_str": balance_str},
                )

            log_message(
                "siliconflow-platform",
                "INFO",
                "SiliconFlow balance formatting completed",
                {
                    "final_display": balance_str,
                    "color_used": color_name,
                    "total_balance": total_balance,
                },
            )

            return balance_str
        except Exception as e:
            log_message(
                "siliconflow-platform",
                "ERROR",
                "SiliconFlow balance formatting failed",
                {"error": str(e), "error_type": type(e).__name__},
            )
            return f"SiliconFlow.B:Error({str(e)[:20]})"

    def format_subscription_display(self, subscription_data: Dict[str, Any]) -> str:
        """SiliconFlow doesn't have subscription info"""
        return ""
