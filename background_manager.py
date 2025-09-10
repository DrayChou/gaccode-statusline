#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
后台任务管理工具 - 用户友好的后台任务系统管理界面
"""

import sys
import json
import argparse
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime

# 导入后台任务模块
from background.daemon_manager import DaemonManager
from background.platform_integration import BackgroundTaskIntegration


class BackgroundManager:
    """后台任务管理器"""

    def __init__(self, data_dir: Path = None):
        if data_dir is None:
            data_dir = Path(__file__).parent / "data"

        self.data_dir = data_dir
        self.daemon_manager = DaemonManager(data_dir)
        self.integration = BackgroundTaskIntegration(data_dir)

        # 平台配置文件路径
        self.platform_config_file = data_dir / "config" / "config.json"

    def load_platform_configs(self) -> Dict[str, Any]:
        """加载平台配置"""
        if not self.platform_config_file.exists():
            return {}

        try:
            with open(self.platform_config_file, "r", encoding="utf-8-sig") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading platform config: {e}")
            return {}

    def get_platform_list(self) -> List[str]:
        """获取支持的平台列表"""
        configs = self.load_platform_configs()
        platforms = []

        if "platforms" in configs:
            for platform_key, platform_config in configs["platforms"].items():
                if platform_config.get("enabled", False):
                    platforms.append(platform_key)

        # 添加已知平台（兼容旧配置）
        if not platforms:
            platforms = ["gaccode"]  # 默认支持GAC Code

        return platforms

    def start_platform_daemon(self, platform: str) -> bool:
        """启动平台守护进程"""
        configs = self.load_platform_configs()

        # 准备平台配置
        platform_config = {}
        if "platforms" in configs and platform in configs["platforms"]:
            platform_config = configs["platforms"][platform]

        # 获取token
        token = ""
        if "api_key" in platform_config:
            token = platform_config["api_key"]
        elif "auth_token" in platform_config:
            token = platform_config["auth_token"]

        if not token:
            print(f"Error: No API token configured for platform {platform}")
            return False

        daemon_config = {"token": token, "platform_config": platform_config}

        return self.daemon_manager.start_daemon(platform, daemon_config)

    def stop_platform_daemon(self, platform: str) -> bool:
        """停止平台守护进程"""
        return self.daemon_manager.stop_daemon(platform)

    def get_platform_status(self, platform: str) -> Dict[str, Any]:
        """获取平台状态"""
        return self.daemon_manager.get_daemon_status(platform)

    def list_all_daemons(self) -> List[Dict[str, Any]]:
        """列出所有守护进程"""
        return self.daemon_manager.list_daemons()

    def cleanup_stale_daemons(self) -> int:
        """清理僵尸守护进程"""
        return self.daemon_manager.cleanup_stale_daemons()

    def get_task_cache_info(self, platform: str) -> Dict[str, Any]:
        """获取任务缓存信息"""
        task_dir = self.data_dir / "tasks"
        balance_cache = task_dir / f"{platform}_balance_task.json"

        info = {
            "platform": platform,
            "balance_cache_exists": balance_cache.exists(),
            "balance_cache_size": 0,
            "balance_data": None,
            "cached_at": None,
        }

        if balance_cache.exists():
            try:
                info["balance_cache_size"] = balance_cache.stat().st_size

                with open(balance_cache, "r", encoding="utf-8") as f:
                    cache_data = json.load(f)

                info["balance_data"] = cache_data.get("balance_data")
                info["cached_at"] = cache_data.get("cached_at")

            except Exception as e:
                info["error"] = str(e)

        return info

    def show_daemon_logs(self, platform: str, tail_lines: int = 20):
        """显示守护进程日志"""
        log_file = self.data_dir / "daemons" / f"{platform}.log"

        if not log_file.exists():
            print(f"No log file found for platform {platform}")
            return

        try:
            with open(log_file, "r", encoding="utf-8") as f:
                lines = f.readlines()

            # 显示最后N行
            if len(lines) > tail_lines:
                lines = lines[-tail_lines:]

            print(f"=== Last {len(lines)} lines of {platform} daemon log ===")
            for line in lines:
                print(line.rstrip())

        except Exception as e:
            print(f"Error reading log file: {e}")


def format_status_table(daemons: List[Dict[str, Any]]) -> None:
    """格式化状态表格显示"""
    if not daemons:
        print("No daemons found.")
        return

    # 表格头
    print(f"{'Platform':<12} {'Status':<10} {'PID':<8} {'Started':<20} {'Tasks':<15}")
    print("-" * 70)

    for daemon in daemons:
        platform = daemon.get("platform", "unknown")
        status = "Running" if daemon.get("running") else "Stopped"
        pid = str(daemon.get("pid", "N/A"))
        started = daemon.get("started_at", "N/A")

        # 格式化启动时间
        if started != "N/A":
            try:
                dt = datetime.fromisoformat(started)
                started = dt.strftime("%m-%d %H:%M:%S")
            except:
                pass

        # 任务统计
        task_stats = daemon.get("task_stats", {})
        task_summary = f"{len(task_stats)} tasks"

        print(f"{platform:<12} {status:<10} {pid:<8} {started:<20} {task_summary:<15}")


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(description="后台任务管理工具")
    parser.add_argument("--data-dir", help="数据目录路径", default=None)

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # start 命令
    start_parser = subparsers.add_parser("start", help="启动平台守护进程")
    start_parser.add_argument("platform", help="平台名称 (gaccode, kimi, deepseek等)")

    # stop 命令
    stop_parser = subparsers.add_parser("stop", help="停止平台守护进程")
    stop_parser.add_argument("platform", help="平台名称")

    # status 命令
    status_parser = subparsers.add_parser("status", help="查看守护进程状态")
    status_parser.add_argument(
        "platform", nargs="?", help="平台名称 (可选，不指定则显示所有)"
    )

    # list 命令
    list_parser = subparsers.add_parser("list", help="列出所有守护进程")

    # cleanup 命令
    cleanup_parser = subparsers.add_parser("cleanup", help="清理僵尸进程")

    # logs 命令
    logs_parser = subparsers.add_parser("logs", help="查看守护进程日志")
    logs_parser.add_argument("platform", help="平台名称")
    logs_parser.add_argument(
        "--tail", type=int, default=20, help="显示最后N行 (默认20)"
    )

    # cache 命令
    cache_parser = subparsers.add_parser("cache", help="查看任务缓存信息")
    cache_parser.add_argument("platform", help="平台名称")

    # platforms 命令
    platforms_parser = subparsers.add_parser("platforms", help="列出可用平台")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # 初始化管理器
    data_dir = Path(args.data_dir) if args.data_dir else None
    manager = BackgroundManager(data_dir)

    try:
        if args.command == "start":
            success = manager.start_platform_daemon(args.platform)
            if success:
                print(f"Successfully started daemon for {args.platform}")
                return 0
            else:
                print(f"Failed to start daemon for {args.platform}")
                return 1

        elif args.command == "stop":
            success = manager.stop_platform_daemon(args.platform)
            if success:
                print(f"Successfully stopped daemon for {args.platform}")
                return 0
            else:
                print(f"Failed to stop daemon for {args.platform}")
                return 1

        elif args.command == "status":
            if args.platform:
                status = manager.get_platform_status(args.platform)
                print(json.dumps(status, indent=2, ensure_ascii=False))
            else:
                daemons = manager.list_all_daemons()
                format_status_table(daemons)
            return 0

        elif args.command == "list":
            daemons = manager.list_all_daemons()
            format_status_table(daemons)
            return 0

        elif args.command == "cleanup":
            cleaned = manager.cleanup_stale_daemons()
            print(f"Cleaned up {cleaned} stale daemon files")
            return 0

        elif args.command == "logs":
            manager.show_daemon_logs(args.platform, args.tail)
            return 0

        elif args.command == "cache":
            cache_info = manager.get_task_cache_info(args.platform)
            print(json.dumps(cache_info, indent=2, ensure_ascii=False))
            return 0

        elif args.command == "platforms":
            platforms = manager.get_platform_list()
            print("Available platforms:")
            for platform in platforms:
                print(f"  - {platform}")
            return 0

    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
