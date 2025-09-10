#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
守护进程管理器 - 管理后台任务守护进程的启动、监控和停止
"""

import os
import sys
import json
import time
import signal
import subprocess
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime, timedelta
import psutil


class DaemonManager:
    """守护进程管理器"""

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.daemon_dir = data_dir / "daemons"
        self.daemon_dir.mkdir(parents=True, exist_ok=True)

    def get_daemon_files(self, platform: str) -> Dict[str, Path]:
        """获取守护进程相关文件路径"""
        return {
            "lock": self.daemon_dir / f"{platform}.lock",
            "pid": self.daemon_dir / f"{platform}.pid",
            "status": self.daemon_dir / f"{platform}.status",
            "log": self.daemon_dir / f"{platform}.log",
        }

    def is_daemon_running(self, platform: str) -> bool:
        """检查指定平台的守护进程是否正在运行"""
        files = self.get_daemon_files(platform)

        # 1. 检查锁文件是否存在
        if not files["lock"].exists():
            return False

        # 2. 检查PID文件是否存在
        if not files["pid"].exists():
            self._cleanup_daemon_files(platform)
            return False

        # 3. 读取PID并检查进程是否存在
        try:
            with open(files["pid"], "r", encoding="utf-8") as f:
                pid_data = json.load(f)
                pid = pid_data.get("pid")

            if pid and psutil.pid_exists(pid):
                # 进一步验证进程是否是我们的守护进程
                try:
                    proc = psutil.Process(pid)
                    # 检查进程名称或命令行参数来确认
                    cmdline = " ".join(proc.cmdline())
                    if "task_executor.py" in cmdline and platform in cmdline:
                        return True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            # PID无效，清理文件
            self._cleanup_daemon_files(platform)
            return False

        except Exception:
            self._cleanup_daemon_files(platform)
            return False

    def start_daemon(self, platform: str, config: Dict[str, Any]) -> bool:
        """启动指定平台的守护进程"""
        if self.is_daemon_running(platform):
            print(f"Daemon for platform {platform} is already running")
            return True

        files = self.get_daemon_files(platform)

        try:
            # 1. 创建锁文件
            lock_data = {
                "platform": platform,
                "locked_at": datetime.now().isoformat(),
                "locked_by": os.getpid(),
            }

            with open(files["lock"], "w", encoding="utf-8") as f:
                json.dump(lock_data, f, indent=2)

            # 2. 构建守护进程启动命令
            script_dir = Path(__file__).parent
            executor_script = script_dir / "task_executor.py"

            cmd = [
                sys.executable,
                str(executor_script),
                "--platform",
                platform,
                "--data-dir",
                str(self.data_dir),
                "--config",
                json.dumps(config),
            ]

            # 3. 启动守护进程（后台模式）
            log_file = open(files["log"], "a", encoding="utf-8")

            proc = subprocess.Popen(
                cmd,
                stdout=log_file,
                stderr=log_file,
                stdin=subprocess.DEVNULL,
                start_new_session=True,  # 创建新的进程组，避免信号传播
            )

            # 4. 记录PID信息
            pid_data = {
                "pid": proc.pid,
                "platform": platform,
                "started_at": datetime.now().isoformat(),
                "command": " ".join(cmd),
            }

            with open(files["pid"], "w", encoding="utf-8") as f:
                json.dump(pid_data, f, indent=2)

            # 5. 等待短暂时间确认启动成功
            time.sleep(2)
            if self.is_daemon_running(platform):
                print(
                    f"Daemon for platform {platform} started successfully (PID: {proc.pid})"
                )
                return True
            else:
                print(f"Failed to start daemon for platform {platform}")
                self._cleanup_daemon_files(platform)
                return False

        except Exception as e:
            print(f"Error starting daemon for platform {platform}: {e}")
            self._cleanup_daemon_files(platform)
            return False

    def stop_daemon(self, platform: str) -> bool:
        """停止指定平台的守护进程"""
        files = self.get_daemon_files(platform)

        if not files["pid"].exists():
            print(f"No daemon found for platform {platform}")
            return True

        try:
            # 读取PID
            with open(files["pid"], "r", encoding="utf-8") as f:
                pid_data = json.load(f)
                pid = pid_data.get("pid")

            if pid and psutil.pid_exists(pid):
                # 尝试优雅停止
                try:
                    proc = psutil.Process(pid)
                    proc.terminate()

                    # 等待进程结束
                    for i in range(10):  # 最多等待10秒
                        if not psutil.pid_exists(pid):
                            break
                        time.sleep(1)

                    # 如果仍然存在，强制杀死
                    if psutil.pid_exists(pid):
                        proc.kill()
                        time.sleep(1)

                    print(f"Daemon for platform {platform} stopped")

                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            # 清理文件
            self._cleanup_daemon_files(platform)
            return True

        except Exception as e:
            print(f"Error stopping daemon for platform {platform}: {e}")
            return False

    def get_daemon_status(self, platform: str) -> Dict[str, Any]:
        """获取守护进程状态信息"""
        files = self.get_daemon_files(platform)

        status = {
            "platform": platform,
            "running": False,
            "pid": None,
            "started_at": None,
            "last_activity": None,
            "task_stats": {},
            "error": None,
        }

        try:
            if self.is_daemon_running(platform):
                status["running"] = True

                # 读取PID信息
                if files["pid"].exists():
                    with open(files["pid"], "r", encoding="utf-8") as f:
                        pid_data = json.load(f)
                        status["pid"] = pid_data.get("pid")
                        status["started_at"] = pid_data.get("started_at")

                # 读取状态信息
                if files["status"].exists():
                    with open(files["status"], "r", encoding="utf-8") as f:
                        daemon_status = json.load(f)
                        status["last_activity"] = daemon_status.get("last_activity")
                        status["task_stats"] = daemon_status.get("task_stats", {})

        except Exception as e:
            status["error"] = str(e)

        return status

    def list_daemons(self) -> List[Dict[str, Any]]:
        """列出所有守护进程状态"""
        daemons = []

        # 遍历守护进程目录，查找所有平台
        for lock_file in self.daemon_dir.glob("*.lock"):
            platform = lock_file.stem
            status = self.get_daemon_status(platform)
            daemons.append(status)

        return daemons

    def cleanup_stale_daemons(self) -> int:
        """清理僵尸守护进程文件"""
        cleaned = 0

        for lock_file in self.daemon_dir.glob("*.lock"):
            platform = lock_file.stem
            if not self.is_daemon_running(platform):
                self._cleanup_daemon_files(platform)
                cleaned += 1

        return cleaned

    def _cleanup_daemon_files(self, platform: str) -> None:
        """清理指定平台的守护进程文件"""
        files = self.get_daemon_files(platform)

        for file_path in files.values():
            try:
                file_path.unlink(missing_ok=True)
            except Exception:
                pass

    def ensure_daemon_running(self, platform: str, config: Dict[str, Any]) -> bool:
        """确保指定平台的守护进程正在运行"""
        if not self.is_daemon_running(platform):
            return self.start_daemon(platform, config)
        return True


def main():
    """命令行工具入口"""
    import argparse

    parser = argparse.ArgumentParser(description="守护进程管理器")
    parser.add_argument(
        "command", choices=["start", "stop", "status", "list", "cleanup"]
    )
    parser.add_argument("--platform", help="平台名称")
    parser.add_argument("--data-dir", default="./data", help="数据目录")
    parser.add_argument("--config", help="平台配置JSON")

    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    manager = DaemonManager(data_dir)

    if args.command == "start":
        if not args.platform:
            print("Error: --platform is required for start command")
            return 1

        config = {}
        if args.config:
            config = json.loads(args.config)

        success = manager.start_daemon(args.platform, config)
        return 0 if success else 1

    elif args.command == "stop":
        if not args.platform:
            print("Error: --platform is required for stop command")
            return 1

        success = manager.stop_daemon(args.platform)
        return 0 if success else 1

    elif args.command == "status":
        if not args.platform:
            print("Error: --platform is required for status command")
            return 1

        status = manager.get_daemon_status(args.platform)
        print(json.dumps(status, indent=2, ensure_ascii=False))
        return 0

    elif args.command == "list":
        daemons = manager.list_daemons()
        print(json.dumps(daemons, indent=2, ensure_ascii=False))
        return 0

    elif args.command == "cleanup":
        cleaned = manager.cleanup_stale_daemons()
        print(f"Cleaned up {cleaned} stale daemon files")
        return 0


if __name__ == "__main__":
    sys.exit(main())
