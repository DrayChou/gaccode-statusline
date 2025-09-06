#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Multi-Platform Claude Code Launcher
统一的Python启动器 - 支持所有平台和操作系统

用法:
    python launcher.py [platform] [--continue] [additional-args...]

示例:
    python launcher.py dp              # 启动DeepSeek
    python launcher.py kimi --continue # 继续Kimi会话
    python launcher.py gc              # 启动GAC Code
"""

import sys
import os
import json
import shutil
import subprocess
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

# Add data directory to path for imports
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir.parent / "data"))

try:
    from session_manager import SessionManager
    from logger import log_message
    from file_lock import safe_json_write, safe_json_read
except ImportError as e:
    print(f"Failed to import required modules: {e}")
    print(
        "Please ensure the data/ directory contains session_manager.py, logger.py, and file_lock.py"
    )
    sys.exit(1)


class Colors:
    """ANSI颜色代码"""

    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    CYAN = "\033[0;36m"
    MAGENTA = "\033[0;35m"
    GRAY = "\033[0;37m"
    NC = "\033[0m"  # No Color

    @staticmethod
    def colorize(text: str, color: str) -> str:
        """在支持ANSI的终端中着色文本"""
        # Windows兼容性：避免emoji编码问题
        try:
            if os.name == "nt":  # Windows
                # Windows Terminal/PowerShell 7+ 支持ANSI
                return f"{color}{text}{Colors.NC}"
            return f"{color}{text}{Colors.NC}"
        except UnicodeEncodeError:
            # 移除emoji字符
            import re

            clean_text = re.sub(r"[^\x00-\x7F]+", "", text)  # 移除非ASCII字符
            return f"{color}{clean_text}{Colors.NC}"


class ClaudeLauncher:
    """Claude Code多平台启动器"""

    def __init__(self):
        self.script_dir = Path(__file__).parent
        self.config_file = self.script_dir / "launcher-config.json"
        self.session_mapping_file = self.script_dir / "session-mappings.json"

        # 日志系统
        self.logger_script = self.script_dir.parent / "data" / "logger.py"

    def log(self, level: str, message: str, extra_data: Dict[str, Any] = None):
        """统一日志记录 - 自动屏蔽敏感信息"""
        # 屏蔽敏感信息
        safe_message = self._mask_sensitive_data(message)
        safe_extra_data = self._mask_sensitive_dict(extra_data or {})

        # 使用Python日志系统
        log_message("launcher", level, safe_message, safe_extra_data)

        # 同时输出到控制台
        color = {
            "ERROR": Colors.RED,
            "WARNING": Colors.YELLOW,
            "INFO": Colors.CYAN,
            "DEBUG": Colors.GRAY,
        }.get(level, Colors.NC)

        print(Colors.colorize(safe_message, color))

    def _mask_sensitive_data(self, text: str) -> str:
        """屏蔽文本中的敏感信息"""
        import re

        # API密钥模式 (sk-xxx, Bearer xxx)
        patterns = [
            (
                r"sk-[a-zA-Z0-9\-]{30,100}",
                lambda m: f"sk-***{m.group()[-4:]}",
            ),  # 包含-字符
            (
                r"Bearer [a-zA-Z0-9+/=]{20,}",
                lambda m: f"Bearer ***{m.group().split()[-1][-4:]}",
            ),
            (
                r"eyJ[a-zA-Z0-9+/=._\-]{40,}",
                lambda m: f"***{m.group()[-8:]}",
            ),  # JWT tokens
            (
                r'"api_key":\s*"[^"]{10,}"',
                lambda m: f'"api_key": "***{m.group().split('"')[-2][-4:]}"',
            ),
            (
                r'"auth_token":\s*"[^"]{10,}"',
                lambda m: f'"auth_token": "***{m.group().split('"')[-2][-4:]}"',
            ),
            (
                r'"login_token":\s*"[^"]{10,}"',
                lambda m: f'"login_token": "***{m.group().split('"')[-2][-4:]}"',
            ),
        ]

        result = text
        for pattern, replacement in patterns:
            result = re.sub(pattern, replacement, result)

        return result

    def _mask_sensitive_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """屏蔽字典中的敏感信息"""
        if not data:
            return data

        safe_data = {}
        sensitive_keys = {"api_key", "auth_token", "login_token", "password", "secret"}

        for key, value in data.items():
            if (
                key.lower() in sensitive_keys
                and isinstance(value, str)
                and len(value) > 4
            ):
                safe_data[key] = f"***{value[-4:]}"
            elif isinstance(value, dict):
                safe_data[key] = self._mask_sensitive_dict(value)
            else:
                safe_data[key] = value

        return safe_data

    def print_header(self):
        """打印启动器头部信息"""
        print(Colors.colorize("Multi-Platform Claude Launcher v4.0", Colors.MAGENTA))
        print(Colors.colorize("=" * 40, Colors.GRAY))
        print()

    def _validate_path(self, path_str: str, description: str) -> Optional[Path]:
        """验证路径安全性，防止路径遍历攻击"""
        if not path_str:
            return None

        try:
            path = Path(path_str).resolve()

            # 检查路径是否包含危险的遍历模式
            if ".." in str(path) or path_str.startswith("/") and "../" in path_str:
                self.log(
                    "WARNING",
                    f"Potentially unsafe path detected in {description}: {path_str}",
                )
                return None

            # 确保路径在合理范围内（用户目录或程序目录下）
            allowed_prefixes = [
                Path.home(),
                Path.cwd(),
                self.script_dir.parent,  # Project root
                Path("C:/"),  # Windows drives
                Path("/"),  # Unix root (for cross-platform)
            ]

            if not any(
                str(path).startswith(str(prefix)) for prefix in allowed_prefixes
            ):
                self.log(
                    "WARNING",
                    f"Path outside allowed directories in {description}: {path}",
                )
                return None

            return path

        except (OSError, ValueError) as e:
            self.log(
                "WARNING", f"Invalid path in {description}: {path_str}, error: {e}"
            )
            return None

    def load_config(self) -> Dict[str, Any]:
        """加载配置文件 - 按优先级顺序查找"""
        # 定义查找顺序：
        # 1. 当前工作目录 (执行命令时所在的目录)
        # 2. 调用脚本所在目录 (通过环境变量或参数传递，这里先用当前目录)
        # 3. launcher.py所在目录 (examples/)
        # 4. 项目data/config目录 (gaccode.com/data/config/)

        # 构建查找路径列表，避免重复
        search_paths = []

        # 1. 真实的用户工作目录 (在Push-Location之前捕获) - 添加安全验证
        real_cwd = os.environ.get("LAUNCHER_REAL_CWD")
        if real_cwd:
            validated_cwd = self._validate_path(
                real_cwd, "LAUNCHER_REAL_CWD environment variable"
            )
            if validated_cwd:
                search_paths.append(
                    ("User working directory", validated_cwd / "launcher-config.json")
                )
        else:
            # Fallback: 使用当前目录（可能已被Push-Location改变）
            current_dir = Path.cwd()
            search_paths.append(
                ("Current directory (fallback)", current_dir / "launcher-config.json")
            )

        # 2. 调用脚本所在目录 (通过环境变量传递) - 添加安全验证
        script_dir = os.environ.get("LAUNCHER_SCRIPT_DIR")
        if script_dir:
            validated_script_dir = self._validate_path(
                script_dir, "LAUNCHER_SCRIPT_DIR environment variable"
            )
            if validated_script_dir:
                # 避免与真实工作目录重复
                real_current_dir = Path(real_cwd) if real_cwd else Path.cwd()
                if validated_script_dir != real_current_dir:
                    search_paths.append(
                        (
                            "Caller script directory",
                            validated_script_dir / "launcher-config.json",
                        )
                    )

        # 3. 项目data/config目录 (系统运行时配置，优先级高)
        data_config_dir = self.script_dir.parent / "data" / "config"
        search_paths.append(
            ("Project data/config directory", data_config_dir / "launcher-config.json")
        )

        # 4. launcher.py所在目录 (examples/ - 模板配置，最低优先级)
        real_current_dir = Path(real_cwd) if real_cwd else Path.cwd()
        caller_script_dir = Path(script_dir) if script_dir else None
        if self.script_dir not in [real_current_dir, caller_script_dir]:
            search_paths.append(
                (
                    "Launcher.py directory (examples template)",
                    self.script_dir / "launcher-config.json",
                )
            )

        # 备用路径：用户主目录
        user_config_paths = [
            Path.home()
            / ".claude"
            / "scripts"
            / "gaccode.com"
            / "data"
            / "config"
            / "launcher-config.json",
            Path.home()
            / ".claude"
            / "scripts"
            / "gaccode.com"
            / "examples"
            / "launcher-config.json",
        ]

        for backup_path in user_config_paths:
            search_paths.append(("User directory backup", backup_path))

        possible_paths = [path for _, path in search_paths]

        # 查找配置文件
        config_found = False
        for i, (description, path) in enumerate(search_paths, 1):
            if path.exists():
                self.config_file = path
                # 设置对应的session mapping文件位置
                if path.parent.name == "config":
                    # 如果在data/config目录下，session映射文件在data/cache下
                    self.session_mapping_file = (
                        path.parent.parent / "cache" / "session-mappings.json"
                    )
                else:
                    # 否则在同目录下
                    self.session_mapping_file = path.parent / "session-mappings.json"

                print(
                    Colors.colorize(
                        f"Using config from {description}: {path}", Colors.GRAY
                    )
                )
                config_found = True
                break

        if not config_found:
            self.log(
                "ERROR", f"Configuration file not found in any of these locations:"
            )
            for i, (description, path) in enumerate(search_paths, 1):
                print(f"  {i}. {description}: {path}")
            sys.exit(1)

        try:
            # 尝试UTF-8-sig编码以处理BOM
            try:
                with open(self.config_file, "r", encoding="utf-8-sig") as f:
                    return json.load(f)
            except UnicodeDecodeError:
                # 回退到UTF-8
                with open(self.config_file, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            self.log("ERROR", f"Failed to load configuration: {e}")
            sys.exit(1)

    def resolve_platform(
        self, platform: str, config: Dict[str, Any]
    ) -> tuple[str, Dict[str, Any]]:
        """解析平台别名并返回平台配置"""
        platforms = config["platforms"]
        aliases = config.get("aliases", {})

        # 解析别名
        resolved_platform = aliases.get(platform, platform)

        # 获取启用的平台
        enabled_platforms = {}
        for name, platform_config in platforms.items():
            is_enabled = platform_config.get("enabled")
            has_api_key = platform_config.get("api_key")
            has_login_token = platform_config.get("login_token")

            # GAC Code平台可以使用login_token，其他平台需要api_key
            # GAC Code平台即使没有配置token也默认启用（会使用默认配置）
            if is_enabled and (has_api_key or has_login_token or name == "gaccode"):
                enabled_platforms[name] = platform_config

        if resolved_platform and resolved_platform in enabled_platforms:
            return resolved_platform, enabled_platforms[resolved_platform]
        elif platform:
            self.log(
                "ERROR",
                f"Platform '{platform}' (resolved: {resolved_platform}) not enabled or not found",
            )
            print(Colors.colorize("Available platforms:", Colors.YELLOW))
            for name, platform_config in enabled_platforms.items():
                aliases_list = [k for k, v in aliases.items() if v == name]
                alias_text = (
                    f" (aliases: {', '.join(aliases_list)})" if aliases_list else ""
                )
                print(f"  - {name}{alias_text}: {platform_config['name']}")
            sys.exit(1)
        else:
            if enabled_platforms:
                # 使用默认平台
                default_platform = config["settings"].get("default_platform")
                if default_platform and default_platform in enabled_platforms:
                    print(
                        Colors.colorize(
                            f"No platform specified, using configured default: {default_platform}",
                            Colors.YELLOW,
                        )
                    )
                    return default_platform, enabled_platforms[default_platform]
                else:
                    # 选择第一个启用的平台
                    selected = list(enabled_platforms.keys())[0]
                    print(
                        Colors.colorize(
                            f"No platform specified, using: {selected}", Colors.YELLOW
                        )
                    )
                    return selected, enabled_platforms[selected]
            else:
                self.log(
                    "ERROR",
                    f"No platforms enabled. Please set API keys in {self.config_file}",
                )
                sys.exit(1)

    def sync_configuration(self, config: Dict[str, Any]):
        """同步配置到插件目录"""
        plugin_path = Path(config["settings"]["plugin_path"])
        if not plugin_path.is_absolute():
            plugin_path = self.script_dir / plugin_path

        # 确保插件目录存在
        if not plugin_path.exists():
            # 尝试查找gaccode.com目录
            parent_dir = self.script_dir.parent
            gaccode_dir = parent_dir / "gaccode.com"
            if gaccode_dir.exists():
                plugin_path = gaccode_dir
            else:
                self.log("ERROR", "Cannot find plugin directory")
                sys.exit(1)

        # 确保子目录存在
        config_dir = plugin_path / "data" / "config"
        cache_dir = plugin_path / "data" / "cache"
        config_dir.mkdir(parents=True, exist_ok=True)
        cache_dir.mkdir(parents=True, exist_ok=True)

        plugin_config_file = config_dir / "launcher-config.json"
        plugin_session_file = cache_dir / "session-mappings.json"

        print(
            Colors.colorize("Syncing configuration to plugin directory...", Colors.CYAN)
        )

        # 创建插件配置文件
        plugin_config = {
            "platforms": config["platforms"],
            "aliases": config.get("aliases", {}),
            "settings": {
                "default_platform": config["settings"].get("default_platform"),
                "last_updated": datetime.now().isoformat(),
            },
        }

        # 使用安全的文件写入（带锁定）
        if safe_json_write(plugin_config_file, plugin_config):
            print(Colors.colorize("   Plugin configuration synced", Colors.GREEN))
        else:
            self.log("ERROR", f"Failed to sync configuration to {plugin_config_file}")
            print(Colors.colorize("   Plugin configuration sync failed", Colors.RED))
        return plugin_session_file

    def setup_environment(self, platform_config: Dict[str, Any]):
        """设置环境变量"""
        print(Colors.colorize("\nSetting up environment...", Colors.CYAN))

        # 清理环境变量
        variables_to_clear = [
            # Claude Code 核心环境变量
            "ANTHROPIC_API_KEY",
            "ANTHROPIC_AUTH_TOKEN",
            "ANTHROPIC_BASE_URL",
            "ANTHROPIC_API_URL",
            "ANTHROPIC_API_VERSION",
            "ANTHROPIC_CUSTOM_HEADERS",
            "ANTHROPIC_DEFAULT_HEADERS",
            "ANTHROPIC_MODEL",
            "ANTHROPIC_SMALL_FAST_MODEL",
            "ANTHROPIC_SMALL_FAST_MODEL_AWS_REGION",
            "ANTHROPIC_TIMEOUT_MS",
            "ANTHROPIC_REQUEST_TIMEOUT",
            "ANTHROPIC_MAX_RETRIES",
            # 代理相关变量
            "HTTPS_PROXY",
            "HTTP_PROXY",
            # 其他AI平台环境变量
            "MOONSHOT_API_KEY",
            "DEEPSEEK_API_KEY",
            "SILICONFLOW_API_KEY",
            # 可能的其他相关变量
            "CLAUDE_API_KEY",
            "CLAUDE_AUTH_TOKEN",
            "CLAUDE_BASE_URL",
            "CLAUDE_MODEL",
        ]

        for var_name in variables_to_clear:
            if var_name in os.environ:
                print(Colors.colorize(f"  -> Clearing: {var_name}", Colors.GRAY))
                del os.environ[var_name]

        # 设置新环境变量
        os.environ["ANTHROPIC_API_KEY"] = platform_config["api_key"]
        os.environ["ANTHROPIC_BASE_URL"] = platform_config["api_base_url"]
        os.environ["ANTHROPIC_MODEL"] = platform_config["model"]
        os.environ["ANTHROPIC_SMALL_FAST_MODEL"] = platform_config["small_model"]

        # Git Bash路径配置 (Windows)
        # 尝试常见的Git Bash安装路径
        possible_git_bash_paths = [
            Path.home()
            / "scoop"
            / "apps"
            / "git"
            / "current"
            / "bin"
            / "bash.exe",  # Scoop
            Path("C:/Program Files/Git/bin/bash.exe"),  # Git for Windows 默认路径
            Path("C:/Program Files (x86)/Git/bin/bash.exe"),  # Git for Windows x86
            Path.home()
            / "AppData"
            / "Local"
            / "Programs"
            / "Git"
            / "bin"
            / "bash.exe",  # 用户安装
        ]

        for git_bash_path in possible_git_bash_paths:
            if git_bash_path.exists():
                os.environ["CLAUDE_CODE_GIT_BASH_PATH"] = str(git_bash_path)
                print(
                    Colors.colorize(
                        f"  -> CLAUDE_CODE_GIT_BASH_PATH set: {git_bash_path.name}",
                        Colors.GRAY,
                    )
                )
                break

        print(Colors.colorize("Environment configured", Colors.GREEN))

    def manage_session(self, selected_platform: str, continue_session: bool) -> str:
        """管理会话"""
        print(Colors.colorize("\nManaging session...", Colors.CYAN))

        if continue_session:
            print(Colors.colorize("Continue session mode enabled", Colors.CYAN))

        try:
            manager = SessionManager()
            session_id = manager.create_or_continue_session(
                selected_platform, continue_session
            )
            return session_id
        except Exception as e:
            self.log("ERROR", f"Session management failed: {e}")
            sys.exit(1)

    def _detect_claude_command(self) -> Optional[List[str]]:
        """智能检测Claude Code启动方式"""
        # 尝试不同的Claude Code启动方式
        claude_commands = [
            # 1. 直接的claude命令 (全局安装)
            ["claude"],
            # 2. npx claude (局部安装或fallback)
            ["npx", "@anthropic-ai/claude-code"],
            # 3. node直接调用 (备用方案)
            ["node", "-e", "require('@anthropic-ai/claude-code/cli')"],
            # 4. pnpx claude (pnpm用户)
            ["pnpx", "claude"],
            # 5. yarn claude (yarn用户)
            ["yarn", "claude"],
        ]

        for cmd in claude_commands:
            try:
                # 测试命令是否可用 - 运行 --version 检查
                test_cmd = cmd + ["--version"]
                result = subprocess.run(
                    test_cmd,
                    capture_output=True,
                    text=True,
                    timeout=10,
                    shell=(os.name == "nt"),  # Windows需要shell=True
                )

                if result.returncode == 0:
                    # 验证输出包含Claude Code相关信息
                    output = result.stdout.strip()
                    if "claude" in output.lower() or "anthropic" in output.lower():
                        print(
                            Colors.colorize(
                                f"Detected Claude Code via: {' '.join(cmd)}",
                                Colors.GRAY,
                            )
                        )
                        print(Colors.colorize(f"Version: {output}", Colors.GRAY))
                        return cmd

            except (
                subprocess.TimeoutExpired,
                subprocess.SubprocessError,
                FileNotFoundError,
            ):
                # 这个命令不可用，尝试下一个
                continue

        return None

    def _extract_standard_uuid(self, prefixed_session_id: str) -> str:
        """从2位平台ID前缀的session_id中提取标准UUID"""
        import uuid
        import hashlib

        parts = prefixed_session_id.split("-")
        if len(parts) == 5:
            first_part = parts[0]

            # 检查前2位是否是有效的平台ID (01-ff)
            if len(first_part) == 8:
                try:
                    platform_id = int(first_part[:2], 16)  # 取前2位
                    if 1 <= platform_id <= 255:  # 有效的2位十六进制范围
                        # 使用确定性转换，将前2位替换为标准十六进制
                        remaining_parts = "-".join(parts[1:])
                        hash_input = (
                            f"platform_id_{platform_id:02x}:{remaining_parts}".encode(
                                "utf-8"
                            )
                        )
                        hash_digest = hashlib.md5(hash_input).hexdigest()
                        standard_uuid = f"{hash_digest[:8]}-{remaining_parts}"
                        return standard_uuid
                except ValueError:
                    pass

        # 如果转换失败，生成新的标准UUID
        fallback_uuid = str(uuid.uuid4())
        self.log(
            "WARNING",
            f"Failed to convert {prefixed_session_id}, using new UUID: {fallback_uuid}",
        )
        return fallback_uuid

    def _create_dual_session_mapping(
        self, prefixed_uuid: str, standard_uuid: str, platform: str
    ):
        """创建双向UUID映射以解决statusline平台检测问题"""
        try:
            # 确定映射文件路径
            mapping_file = (
                self.script_dir.parent / "data" / "cache" / "session-mappings.json"
            )

            # 读取现有映射
            existing_mappings = safe_json_read(mapping_file, {})

            # 创建双向映射条目
            session_info = {
                "platform": platform,
                "created": datetime.now().isoformat(),
                "prefixed_uuid": prefixed_uuid,  # 存储原始带前缀UUID
                "standard_uuid": standard_uuid,  # 存储标准UUID
            }

            # 同时存储两种UUID格式的映射
            existing_mappings[prefixed_uuid] = session_info.copy()
            existing_mappings[standard_uuid] = session_info.copy()

            # 保存映射
            if safe_json_write(mapping_file, existing_mappings):
                self.log(
                    "DEBUG",
                    f"Created dual UUID mapping: {prefixed_uuid} <-> {standard_uuid} -> {platform}",
                )
            else:
                self.log(
                    "WARNING", f"Failed to create session mapping for {prefixed_uuid}"
                )

        except Exception as e:
            self.log("ERROR", f"Failed to create dual session mapping: {e}")

    def launch_claude(
        self, session_id: str, continue_session: bool, remaining_args: List[str]
    ):
        """启动Claude Code - 智能检测启动方式"""
        print(Colors.colorize("\nLaunching Claude Code...", Colors.MAGENTA))

        # 智能检测Claude启动命令
        claude_base_cmd = self._detect_claude_command()
        if not claude_base_cmd:
            self.log(
                "ERROR",
                "Claude Code not found. Please install via one of these methods:",
            )
            print("  1. npm install -g @anthropic-ai/claude-code")
            print("  2. Use npx: npx @anthropic-ai/claude-code")
            print("  3. Install via Scoop: scoop install claude-code")
            sys.exit(1)

        # 准备参数
        claude_args = claude_base_cmd.copy()

        # 如果是继续会话模式，传递 --continue；否则传递 --session-id
        if continue_session:
            claude_args.append("--continue")
        else:
            # 直接使用传入的标准UUID（已经在调用处转换过）
            claude_args.append(f"--session-id={session_id}")

        # 添加剩余参数
        claude_args.extend(remaining_args)

        command_string = " ".join(claude_args)
        print(Colors.colorize(f"Executing: {command_string}", Colors.GREEN))
        print(Colors.colorize("=" * 60, Colors.GRAY))

        # 执行Claude Code
        try:
            # Windows需要shell=True来正确执行.cmd文件和npm命令
            if os.name == "nt":
                result = subprocess.run(claude_args, shell=True)
            else:
                result = subprocess.run(claude_args)
            return result.returncode
        except Exception as e:
            self.log("ERROR", f"Execution failed: {e}")
            return 1

    def run(self, args: List[str]):
        """主运行逻辑"""
        self.print_header()

        # 解析参数
        parser = argparse.ArgumentParser(
            description="Multi-Platform Claude Code Launcher"
        )
        parser.add_argument(
            "platform", nargs="?", help="Platform name or alias (dp, kimi, gc, sf, lp)"
        )
        parser.add_argument(
            "--continue", action="store_true", help="Continue existing session"
        )
        parser.add_argument(
            "remaining_args", nargs="*", help="Additional arguments for Claude Code"
        )

        parsed_args = parser.parse_args(args)

        # 加载配置
        self.log("INFO", "Loading platform configuration...")
        config = self.load_config()

        # 解析平台
        selected_platform, platform_config = self.resolve_platform(
            parsed_args.platform, config
        )
        enabled_count = len(
            [
                p
                for p in config["platforms"].values()
                if p.get("enabled") and p.get("api_key")
            ]
        )

        print(
            Colors.colorize(
                f"Selected Platform: {platform_config['name']} ({selected_platform})",
                Colors.GREEN,
            )
        )
        print(Colors.colorize(f"   Enabled Platforms: {enabled_count}", Colors.GRAY))

        # 同步配置
        plugin_session_file = self.sync_configuration(config)

        # 设置环境
        self.setup_environment(platform_config)

        # 管理会话
        session_id = self.manage_session(
            selected_platform, getattr(parsed_args, "continue")
        )

        # 为了解决UUID映射问题，创建双向映射
        standard_uuid = self._extract_standard_uuid(session_id)
        self._create_dual_session_mapping(session_id, standard_uuid, selected_platform)

        # 显示会话信息
        print(Colors.colorize("Session ready", Colors.GREEN))
        print(Colors.colorize(f"   UUID: {session_id}", Colors.GREEN))
        print(Colors.colorize(f"   Standard UUID: {standard_uuid}", Colors.GRAY))
        print(Colors.colorize(f"   Platform: {selected_platform}", Colors.GREEN))
        print(Colors.colorize(f"   Model: {platform_config['model']}", Colors.GREEN))
        if getattr(parsed_args, "continue"):
            print(Colors.colorize("   Mode: Continue existing session", Colors.YELLOW))
        else:
            print(Colors.colorize("   Mode: New session", Colors.CYAN))

        # 配置摘要
        print(Colors.colorize("\nConfiguration Summary:", Colors.YELLOW))
        print(Colors.colorize(f"   Platform: {platform_config['name']}", Colors.NC))
        print(Colors.colorize(f"   Session: {session_id}", Colors.GRAY))
        print(Colors.colorize(f"   Model: {platform_config['model']}", Colors.GRAY))

        # 启动Claude Code（传递标准UUID避免重复转换）
        exit_code = self.launch_claude(
            standard_uuid, getattr(parsed_args, "continue"), parsed_args.remaining_args
        )

        # 清理和总结
        print(Colors.colorize("\n" + "=" * 60, Colors.GRAY))
        if exit_code == 0:
            print(Colors.colorize("Session completed successfully!", Colors.GREEN))
        else:
            print(
                Colors.colorize(
                    f"Claude Code exited with error code: {exit_code}", Colors.RED
                )
            )
        print(Colors.colorize(f"   Platform: {platform_config['name']}", Colors.NC))
        print(Colors.colorize(f"   UUID: {session_id}", Colors.GRAY))

        return exit_code


def main():
    """主函数"""
    launcher = ClaudeLauncher()
    exit_code = launcher.run(sys.argv[1:])
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
