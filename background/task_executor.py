#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
任务执行器守护进程 - 独立进程，定时执行后台任务
"""

import os
import sys
import json
import time
import signal
import argparse
import threading
from typing import Dict, Any, Optional, List, Callable
from pathlib import Path
from datetime import datetime, timedelta
import logging


class TaskExecutor:
    """后台任务执行器守护进程"""

    def __init__(self, platform: str, data_dir: Path, config: Dict[str, Any]):
        self.platform = platform
        self.data_dir = data_dir
        self.config = config
        self.running = False
        self.shutdown_event = threading.Event()

        # 初始化目录结构
        self.daemon_dir = data_dir / "daemons"
        self.task_dir = data_dir / "tasks"
        self.cache_dir = data_dir / "cache"

        for dir_path in [self.daemon_dir, self.task_dir, self.cache_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

        # 状态文件
        self.status_file = self.daemon_dir / f"{platform}.status"
        self.log_file = self.daemon_dir / f"{platform}.log"

        # 设置日志
        self._setup_logging()

        # 任务配置（将从平台实例获取）
        self.task_configs = {}
        self.platform_task_config = None

        # 任务统计 - 动态初始化，支持所有平台的不同任务配置
        self.task_stats = {}

        # 注册信号处理
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        if hasattr(signal, "SIGHUP"):
            signal.signal(signal.SIGHUP, self._signal_handler)

    def _setup_logging(self):
        """设置日志记录"""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
            handlers=[
                logging.FileHandler(self.log_file, encoding="utf-8"),
                logging.StreamHandler(sys.stdout),
            ],
        )
        self.logger = logging.getLogger(f"daemon-{self.platform}")

    def _signal_handler(self, signum, frame):
        """信号处理器"""
        self.logger.info(f"Received signal {signum}, initiating shutdown...")
        self.shutdown()

    def start(self):
        """启动守护进程"""
        self.logger.info(f"Starting daemon for platform {self.platform}")
        self.running = True

        # 更新状态
        self._update_status("starting")

        try:
            # 主循环
            self._main_loop()
        except Exception as e:
            self.logger.error(f"Fatal error in main loop: {e}")
            self._update_status("error", {"error": str(e)})
        finally:
            self.running = False
            self._update_status("stopped")
            self.logger.info("Daemon stopped")

    def shutdown(self):
        """优雅关闭"""
        self.logger.info("Initiating graceful shutdown...")
        self.shutdown_event.set()
        self.running = False

    def _main_loop(self):
        """主执行循环"""
        self.logger.info("Entering main loop")
        self._update_status("running")

        while self.running and not self.shutdown_event.is_set():
            try:
                # 检查并执行到期的任务
                self._check_and_run_tasks()

                # 更新状态
                self._update_status("running")

                # 短暂休眠，避免CPU占用过高
                if not self.shutdown_event.wait(30):  # 30秒间隔
                    continue
                else:
                    break

            except KeyboardInterrupt:
                self.logger.info("Received keyboard interrupt")
                break
            except Exception as e:
                self.logger.error(f"Error in main loop: {e}")
                time.sleep(60)  # 出错时等待更长时间

    def _check_and_run_tasks(self):
        """检查并运行到期的任务"""
        current_time = datetime.now()
        
        # 首次运行时初始化平台任务配置
        if not self.task_configs:
            platform_instance = self._get_platform_instance()
            if not platform_instance:
                self.logger.error("Failed to initialize platform instance for task configuration")
                return

        for task_name, task_config in self.task_configs.items():
            if not task_config.get("enabled", True):
                continue

            # 检查是否到了执行时间
            last_run = task_config["last_run"]
            if last_run is None:
                should_run = True
            else:
                last_run_time = datetime.fromisoformat(last_run)
                should_run = (
                    current_time - last_run_time
                ).total_seconds() >= task_config["interval"]

            if should_run:
                self._run_task(task_name)
                task_config["last_run"] = current_time.isoformat()

    def _run_task(self, task_name: str):
        """执行指定任务"""
        self.logger.info(f"Running task: {task_name}")

        try:
            # 动态初始化task_stats
            if task_name not in self.task_stats:
                self.task_stats[task_name] = {
                    "runs": 0,
                    "errors": 0,
                    "last_success": None,
                    "last_error": None
                }
            
            self.task_stats[task_name]["runs"] += 1

            # 根据任务类型调用相应的处理方法
            if task_name == "balance_check":
                self._task_balance_check()
            elif task_name == "refill_check":
                self._task_refill_check()
            elif task_name == "cache_cleanup":
                self._task_cache_cleanup()
            elif task_name == "multiplier_update":
                self._task_multiplier_update()
            else:
                # 尝试动态任务调度
                self._run_dynamic_task(task_name)

            # 记录成功
            self.task_stats[task_name]["last_success"] = datetime.now().isoformat()
            self.logger.info(f"Task {task_name} completed successfully")

        except Exception as e:
            # 记录错误
            self.task_stats[task_name]["errors"] += 1
            self.task_stats[task_name]["last_error"] = {
                "time": datetime.now().isoformat(),
                "error": str(e),
            }
            self.logger.error(f"Task {task_name} failed: {e}")

    def _task_balance_check(self):
        """余额检查任务（使用平台标准接口）"""
        platform_instance = self._get_platform_instance()
        if not platform_instance:
            raise Exception("Failed to create platform instance")

        # 调用平台标准方法
        method_name = self.platform_task_config['balance_check']['method']
        method = getattr(platform_instance, method_name)
        balance_data = method()

        if balance_data:
            # 保存余额数据到任务缓存
            task_cache_file = self.task_dir / f"{self.platform}_balance_task.json"
            cache_data = {
                "balance_data": balance_data,
                "cached_at": datetime.now().isoformat(),
                "source": "background_task",
            }

            with open(task_cache_file, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)

            self.logger.info(
                f"Balance check completed, balance: {balance_data.get('balance', 'unknown')}"
            )
        else:
            self.logger.warning("Balance check failed - no data returned")

    def _task_refill_check(self):
        """Refill检查任务（使用平台标准接口）"""
        # 检查任务是否启用
        if not self.platform_task_config['refill_check']['enabled']:
            self.logger.debug("Refill check disabled for this platform")
            return
            
        # 读取最新的余额数据
        task_cache_file = self.task_dir / f"{self.platform}_balance_task.json"
        if not task_cache_file.exists():
            self.logger.info("No balance data available, skipping refill check")
            return

        try:
            with open(task_cache_file, "r", encoding="utf-8") as f:
                cache_data = json.load(f)

            balance_data = cache_data.get("balance_data")
            if not balance_data:
                self.logger.warning("Invalid balance data in cache")
                return

            balance = balance_data.get("balance", 0)
            self.logger.info(f"Current balance: {balance}, checking if refill needed")

            # 使用平台标准接口执行refill检查
            platform_instance = self._get_platform_instance()
            if platform_instance:
                method_name = self.platform_task_config['refill_check']['method']
                method = getattr(platform_instance, method_name)
                method(balance_data)  # 传递余额数据给平台方法
                self.logger.info("Refill check delegated to platform")
            else:
                self.logger.error("Failed to create platform instance for refill")

        except Exception as e:
            self.logger.error(f"Error in refill check: {e}")

    def _task_cache_cleanup(self):
        """缓存清理任务（使用平台标准接口 + 默认清理）"""
        cleanup_count = 0

        # 1. 平台特定的缓存清理
        try:
            platform_instance = self._get_platform_instance()
            if platform_instance:
                method_name = self.platform_task_config['cache_cleanup']['method']
                method = getattr(platform_instance, method_name)
                method()  # 调用平台特定清理
                self.logger.debug("Platform-specific cache cleanup completed")
        except Exception as e:
            self.logger.warning(f"Platform cache cleanup failed: {e}")

        # 2. 默认的任务缓存清理
        for cache_file in self.task_dir.glob(f"{self.platform}_*.json"):
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    cache_data = json.load(f)

                cached_at_str = cache_data.get("cached_at")
                if cached_at_str:
                    cached_at = datetime.fromisoformat(cached_at_str)
                    age_hours = (datetime.now() - cached_at).total_seconds() / 3600

                    # 清理超过24小时的缓存
                    if age_hours > 24:
                        cache_file.unlink()
                        cleanup_count += 1

            except Exception:
                # 损坏的缓存文件直接删除
                cache_file.unlink()
                cleanup_count += 1

        if cleanup_count > 0:
            self.logger.info(f"Cleaned up {cleanup_count} expired cache files")

    def _import_platform_module(self):
        """动态导入平台模块"""
        try:
            # 添加项目根目录到path
            script_dir = Path(__file__).parent.parent
            
            if str(script_dir) not in sys.path:
                sys.path.insert(0, str(script_dir))

            # 根据平台名称导入对应模块
            if self.platform == "gaccode":
                from platforms.gaccode import GACCodePlatform
                return GACCodePlatform
            elif self.platform == "kimi":
                from platforms.kimi import KimiPlatform
                return KimiPlatform
            elif self.platform == "deepseek":
                from platforms.deepseek import DeepSeekPlatform
                return DeepSeekPlatform
            elif self.platform == "siliconflow":
                from platforms.siliconflow import SiliconFlowPlatform
                return SiliconFlowPlatform
            else:
                self.logger.error(f"Unsupported platform: {self.platform}")
                return None

        except ImportError as e:
            self.logger.error(f"Failed to import platform module: {e}")
            return None

    def _get_platform_instance(self):
        """获取平台实例（缓存单例）"""
        if hasattr(self, '_platform_instance') and self._platform_instance:
            return self._platform_instance
            
        try:
            platform_class = self._import_platform_module()
            if not platform_class:
                return None
                
            # 从配置中获取token和其他配置
            token = self.config.get("token", "")
            platform_config = self.config.get("platform_config", {})

            # 创建实例
            instance = platform_class(token, platform_config)

            # 初始化session（如果需要）
            if hasattr(instance, "_init_session"):
                instance._init_session()
            
            # 获取平台任务配置
            if hasattr(instance, 'get_background_task_config'):
                base_config = instance.get_background_task_config()
                # 合并配置，添加运行时状态
                for task_name, task_config in base_config.items():
                    self.task_configs[task_name] = {
                        **task_config,
                        "last_run": None
                    }
                self.platform_task_config = base_config
            
            # 缓存实例
            self._platform_instance = instance
            return instance

        except Exception as e:
            self.logger.error(f"Failed to create platform instance: {e}")
            return None

    def _task_multiplier_update(self):
        """倍率更新任务（GAC Code特有）"""
        platform_instance = self._get_platform_instance()
        if not platform_instance:
            raise Exception("Failed to create platform instance")

        # 调用平台的fetch_history_data方法来更新倍率
        history_data = platform_instance.fetch_history_data(5)
        if history_data:
            self.logger.info("Multiplier update completed via history data fetch")
        else:
            self.logger.warning("Multiplier update failed - no history data")
    
    def _run_dynamic_task(self, task_name: str):
        """运行动态任务（通过平台实例方法调用）"""
        if not self.platform_task_config or task_name not in self.platform_task_config:
            self.logger.warning(f"Unknown task: {task_name}")
            return
            
        platform_instance = self._get_platform_instance()
        if not platform_instance:
            raise Exception("Failed to create platform instance for dynamic task")
        
        method_name = self.platform_task_config[task_name]['method']
        if hasattr(platform_instance, method_name):
            method = getattr(platform_instance, method_name)
            result = method()
            self.logger.info(f"Dynamic task {task_name} completed via {method_name}")
        else:
            self.logger.error(f"Platform method {method_name} not found for task {task_name}")

    def _update_status(self, status: str, extra_data: Optional[Dict[str, Any]] = None):
        """更新守护进程状态"""
        status_data = {
            "platform": self.platform,
            "status": status,
            "pid": os.getpid(),
            "last_activity": datetime.now().isoformat(),
            "task_configs": self.task_configs,
            "task_stats": self.task_stats,
        }

        if extra_data:
            status_data.update(extra_data)

        try:
            with open(self.status_file, "w", encoding="utf-8") as f:
                json.dump(status_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to update status file: {e}")


def main():
    """守护进程入口点"""
    parser = argparse.ArgumentParser(description="后台任务执行器守护进程")
    parser.add_argument("--platform", required=True, help="平台名称")
    parser.add_argument("--data-dir", required=True, help="数据目录路径")
    parser.add_argument("--config", required=True, help="平台配置JSON")

    args = parser.parse_args()

    try:
        # 解析配置
        config = json.loads(args.config)
        data_dir = Path(args.data_dir)

        # 创建并启动守护进程
        executor = TaskExecutor(args.platform, data_dir, config)
        executor.start()

    except KeyboardInterrupt:
        print("\nReceived keyboard interrupt, exiting...")
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
