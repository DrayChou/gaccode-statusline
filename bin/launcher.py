#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Multi-Platform Claude Code Launcher
统一的Python启动器 - 支持所有平台和操作系统

用法:
    python launcher.py [platform] [--continue|-c] [additional-args...]

示例:
    python launcher.py dp              # 启动DeepSeek
    python launcher.py kimi --continue # 继续Kimi会话
    python launcher.py kimi -c         # 继续Kimi会话（简短形式）
    python launcher.py gc              # 启动GAC Code
"""

import sys
import os
import json
import shutil
import subprocess
import argparse
import uuid
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

# Add data directory to path for imports
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir.parent / "data"))

try:
    from logger import log_message

    sys.path.insert(0, str(script_dir.parent))
    from config import get_config_manager
    from session import get_session_manager
except ImportError as e:
    print(f"Failed to import required modules: {e}")
    print(
        "Please ensure unified modules (config.py, session.py, cache.py) are available"
    )
    sys.exit(1)


class SimpleLogger:
    """简化的日志提供者"""

    def __init__(self):
        pass

    def log(self, level: str, message: str, extra_data: Dict[str, Any] = None) -> None:
        # 屏蔽敏感信息
        safe_message = self._mask_sensitive_data(message)
        safe_extra_data = self._mask_sensitive_dict(extra_data or {})

        # 使用统一日志系统
        try:
            log_message("launcher", level, safe_message, safe_extra_data)
        except:
            pass  # 如果日志系统不可用，继续执行

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
        patterns = [
            (r"sk-[a-zA-Z0-9\-]{30,100}", lambda m: f"sk-***{m.group()[-4:]}"),
            (r"Bearer [a-zA-Z0-9+/=]{20,}", lambda m: f"Bearer ***{m.group().split()[-1][-4:]}"),
            (r"eyJ[a-zA-Z0-9+/=]{20,}", lambda m: f"jwt-***{m.group()[-4:]}"),
        ]
        result = text
        for pattern, replacement in patterns:
            result = re.sub(pattern, replacement, result)
        return result

    def _mask_sensitive_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """屏蔽字典中的敏感信息"""
        if not isinstance(data, dict):
            return data

        sensitive_keys = {
            "api_key",
            "auth_token",
            "login_token",
            "password",
            "secret",
            "private_key",
            "access_token",
            "refresh_token",
        }

        masked = {}
        for key, value in data.items():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                if isinstance(value, str) and len(value) > 4:
                    masked[key] = f"***{value[-4:]}"
                else:
                    masked[key] = "***"
            elif isinstance(value, dict):
                masked[key] = self._mask_sensitive_dict(value)
            else:
                masked[key] = value
        return masked


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
    """Claude Code多平台启动器（支持依赖注入）"""

    def __init__(self):
        self.script_dir = Path(__file__).parent
        # 使用统一管理器
        self.config_manager = get_config_manager()
        self.session_manager = get_session_manager()

        # 使用简化的日志提供者
        self.logger = SimpleLogger()

    def log(self, level: str, message: str, extra_data: Dict[str, Any] = None):
        """统一日志记录 - 通过注入的logger提供者"""
        self.logger.log(level, message, extra_data)

    def print_header(self):
        """打印启动器头部信息"""
        print(Colors.colorize("Multi-Platform Claude Launcher v4.0", Colors.MAGENTA))
        print(Colors.colorize("=" * 40, Colors.GRAY))
        print()

  
    def load_config(self) -> Dict[str, Any]:
        """加载配置文件 - 使用统一配置管理器"""
        config = self.config_manager.load_config()
        print(Colors.colorize("Using unified configuration system", Colors.GRAY))
        return config

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
            has_auth_token = platform_config.get("auth_token")

            # 检查是否有任何形式的认证凭证
            has_credentials = has_api_key or has_login_token or has_auth_token

            # GAC Code平台即使没有配置token也默认启用（会使用默认配置）
            if is_enabled and (has_credentials or name == "gaccode"):
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
                default_platform = config["launcher"].get("default_platform")
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

  
    def setup_environment(self, platform_config: Dict[str, Any]):
        """为Claude Code设置环境变量"""
        print(Colors.colorize("\nSetting up Claude Code environment...", Colors.CYAN))

        # 注意：不再依赖settings文件，直接清理和设置环境变量

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
            # Claude Code 默认模型环境变量
            "ANTHROPIC_DEFAULT_HAIKU_MODEL",
            "ANTHROPIC_DEFAULT_OPUS_MODEL",
            "ANTHROPIC_DEFAULT_SONNET_MODEL",
            # Claude Code 配置变量 (根据错误信息确认支持的)
            "CLAUDE_CODE_MAX_OUTPUT_TOKENS",
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

        # 为 Claude Code 设置新环境变量
        # 根据平台配置设置正确的认证变量，确保 api_key 和 auth_token 互斥

        # 调试：显示当前环境变量状态
        print(Colors.colorize(f"  -> Debug: ANTHROPIC_AUTH_TOKEN = {'[SET]' if os.environ.get('ANTHROPIC_AUTH_TOKEN') else '[NOT SET]'}", Colors.CYAN))
        print(Colors.colorize(f"  -> Debug: ANTHROPIC_API_KEY = {'[SET]' if os.environ.get('ANTHROPIC_API_KEY') else '[NOT SET]'}", Colors.CYAN))

        if platform_config.get("api_key"):
            # 设置 API Key 时，强制清理 AUTH TOKEN
            os.environ["ANTHROPIC_API_KEY"] = platform_config["api_key"]
            print(Colors.colorize(f"  -> Setting: ANTHROPIC_API_KEY = sk-***{platform_config['api_key'][-4:]}", Colors.GREEN))

            # 强制覆盖为空字符串，确保没有冲突
            os.environ["ANTHROPIC_AUTH_TOKEN"] = ""
            print(Colors.colorize(f"  -> Force clearing: ANTHROPIC_AUTH_TOKEN = [EMPTY]", Colors.YELLOW))

        elif platform_config.get("auth_token"):
            # 设置 Auth Token 时，强制清理 API KEY
            os.environ["ANTHROPIC_AUTH_TOKEN"] = platform_config["auth_token"]
            print(Colors.colorize(f"  -> Setting: ANTHROPIC_AUTH_TOKEN = ***{platform_config['auth_token'][-4:]}", Colors.GREEN))

            # 强制覆盖为空字符串，确保没有冲突
            os.environ["ANTHROPIC_API_KEY"] = ""
            print(Colors.colorize(f"  -> Force clearing: ANTHROPIC_API_KEY = [EMPTY]", Colors.YELLOW))
        # 注意：login_token 是 GAC Code 独有的用来查询余额的 token，不用于 Claude Code 认证

        os.environ["ANTHROPIC_BASE_URL"] = platform_config["api_base_url"]
        os.environ["ANTHROPIC_MODEL"] = platform_config["model"]
        os.environ["ANTHROPIC_SMALL_FAST_MODEL"] = platform_config["small_model"]

        # 设置Claude Code配置变量（从平台配置中读取，如果有的话）
        # 根据错误信息，CLAUDE_CODE_MAX_OUTPUT_TOKENS是官方支持的变量
        claude_code_config = platform_config.get("claude_code_config", {})

        if claude_code_config.get("max_output_tokens"):
            os.environ["CLAUDE_CODE_MAX_OUTPUT_TOKENS"] = str(
                claude_code_config["max_output_tokens"]
            )
            print(
                Colors.colorize(
                    f"  -> CLAUDE_CODE_MAX_OUTPUT_TOKENS: {claude_code_config['max_output_tokens']}",
                    Colors.GRAY,
                )
            )

        # Git Bash路径配置 (Windows) - 使用动态检测
        possible_git_bash_paths = []

        # 1. 检查环境变量指向的Git安装
        git_env_vars = [
            ("GIT_INSTALL_PATH", "Git/bin/bash.exe"),
            ("PROGRAMFILES", "Git/bin/bash.exe"),
            ("PROGRAMFILES(X86)", "Git/bin/bash.exe"),
            ("LOCALAPPDATA", "Programs/Git/bin/bash.exe"),
        ]

        for env_var, relative_path in git_env_vars:
            if env_var in os.environ:
                git_path = Path(os.environ[env_var]) / relative_path
                if git_path.exists():
                    possible_git_bash_paths.append(git_path)

        # 2. Scoop安装路径 (用户目录下)
        scoop_git = Path.home() / "scoop" / "apps" / "git" / "current" / "bin" / "bash.exe"
        if scoop_git.exists():
            possible_git_bash_paths.append(scoop_git)

        # 3. 常见安装位置 (作为fallback，但先检查是否存在)
        common_fallbacks = [
            Path("C:/Program Files/Git/bin/bash.exe"),
            Path("C:/Program Files (x86)/Git/bin/bash.exe"),
        ]
        possible_git_bash_paths.extend([p for p in common_fallbacks if p.exists()])

        # 4. 用户自定义安装路径
        user_install = Path.home() / "AppData" / "Local" / "Programs" / "Git" / "bin" / "bash.exe"
        if user_install.exists():
            possible_git_bash_paths.append(user_install)

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

        # 验证环境变量设置，确保没有冲突
        auth_conflict = False
        if "ANTHROPIC_API_KEY" in os.environ and "ANTHROPIC_AUTH_TOKEN" in os.environ:
            # 检查是否都非空
            api_key_val = os.environ.get("ANTHROPIC_API_KEY", "")
            auth_token_val = os.environ.get("ANTHROPIC_AUTH_TOKEN", "")
            if api_key_val and auth_token_val:  # 都非空才算冲突
                auth_conflict = True
                print(Colors.colorize("  [WARNING] Both ANTHROPIC_API_KEY and ANTHROPIC_AUTH_TOKEN are set!", Colors.RED))
                print(Colors.colorize("     This may cause authentication conflicts with Claude Code.", Colors.RED))

        if not auth_conflict:
            print(Colors.colorize("Claude Code environment configured", Colors.GREEN))

    def manage_session(self, selected_platform: str, continue_session: bool) -> str:
        """管理会话"""
        print(Colors.colorize("\nManaging session...", Colors.CYAN))

        if continue_session:
            print(Colors.colorize("Continue session mode enabled", Colors.CYAN))

        try:
            session = self.session_manager.create_session(
                selected_platform, continue_session
            )

            # 创建双UUID映射（向后兼容）
            prefixed_uuid = session.prefixed_uuid
            standard_uuid = session.standard_uuid

            print(
                Colors.colorize(
                    f"Created dual UUID mapping: {prefixed_uuid} <-> {standard_uuid} -> {selected_platform}",
                    Colors.GRAY,
                )
            )

            return session.session_id
        except Exception as e:
            self.log("ERROR", f"Session management failed: {e}", {"exception": str(e)})
            # 生成fallback session ID而不是完全失败
            fallback_id = f"fallback-{str(uuid.uuid4())}"
            self.log("WARNING", f"Using fallback session ID: {fallback_id}")
            return fallback_id

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
                    encoding="utf-8",
                    errors="replace",
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

        # 检查是否为带前缀的UUID（36位长度且第3位是'-'）
        if len(prefixed_session_id) == 36 and prefixed_session_id[2] == "-":
            # 移除前2位平台前缀，保留剩余部分作为标准UUID
            standard_uuid = prefixed_session_id[2:]
            return standard_uuid

        # 如果已经是标准UUID格式（没有平台前缀），直接返回
        if len(prefixed_session_id) == 36 and prefixed_session_id[2] != "-":
            return prefixed_session_id

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
        """创建双向UUID映射（优先使用V2目录式存储）"""
        try:
            # 使用SessionMappingV2系统
            from data.session_mapping_v2 import set_session_platform

            metadata = {
                "prefixed_uuid": prefixed_uuid,
                "standard_uuid": standard_uuid,
                "created": datetime.now().isoformat(),
                "launcher_version": "v2",
            }

            # 创建双向映射
            success1 = set_session_platform(prefixed_uuid, platform, metadata)
            success2 = set_session_platform(standard_uuid, platform, metadata)

            if success1 and success2:
                self.log(
                    "INFO",
                    f"Session mapping V2 created: {prefixed_uuid[:8]}... & {standard_uuid[:8]}... -> {platform}",
                )
                return True
            else:
                self.log("ERROR", f"SessionMapping V2 failed to create mappings", {})
                return False

        except Exception as e:
            self.log(
                "ERROR",
                f"Failed to create dual session mapping: {e}",
                {"exception": str(e)},
            )
            return False

    def launch_claude(
        self,
        session_id: str,
        continue_session: bool,
        remaining_args: List[str],
        platform_config: Dict[str, Any],
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

        # 注意：--settings参数经测试无效，无法覆盖系统环境变量
        # 我们完全依赖环境变量清理和PowerShell隔离来实现配置
        print(
            Colors.colorize(
                "Using environment variable isolation (no settings file dependency)",
                Colors.CYAN,
            )
        )

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
            # 调试：确认环境变量设置
            max_tokens = os.environ.get("CLAUDE_CODE_MAX_OUTPUT_TOKENS")
            if max_tokens:
                print(
                    Colors.colorize(
                        f"Debug: CLAUDE_CODE_MAX_OUTPUT_TOKENS={max_tokens} will be passed to Claude Code",
                        Colors.CYAN,
                    )
                )
            else:
                print(
                    Colors.colorize(
                        "Warning: CLAUDE_CODE_MAX_OUTPUT_TOKENS not found in environment!",
                        Colors.YELLOW,
                    )
                )

            # 使用智能环境变量设置方法
            clean_env = self._setup_subprocess_env(platform_config)

            # 显示环境变量设置信息
            if platform_config.get("api_key"):
                print(Colors.colorize(f"  -> Subprocess env override: ANTHROPIC_API_KEY=sk-***{platform_config['api_key'][-4:]}", Colors.GREEN))
                print(Colors.colorize(f"  -> Subprocess env override: ANTHROPIC_AUTH_TOKEN=[EMPTY]", Colors.YELLOW))
            elif platform_config.get("auth_token"):
                print(Colors.colorize(f"  -> Subprocess env override: ANTHROPIC_AUTH_TOKEN=***{platform_config['auth_token'][-4:]}", Colors.GREEN))
                print(Colors.colorize(f"  -> Subprocess env override: ANTHROPIC_API_KEY=[EMPTY]", Colors.YELLOW))
            print(Colors.colorize(f"  -> Subprocess env override: ANTHROPIC_BASE_URL={platform_config['api_base_url']}", Colors.CYAN))

            # 调试：显示关键环境变量
            print(Colors.colorize(f"  -> Debug: PATH exists: {'PATH' in clean_env}", Colors.CYAN))
            if 'PATH' in clean_env:
                print(Colors.colorize(f"  -> Debug: PATH length: {len(clean_env['PATH'])}", Colors.CYAN))

            # 测试命令是否真的存在
            cmd_path = shutil.which(claude_args[0])
            print(Colors.colorize(f"  -> Debug: which('{claude_args[0]}') = {cmd_path}", Colors.CYAN))

            # 如果找到了完整路径，使用完整路径
            if cmd_path:
                print(Colors.colorize(f"  -> Using full path: {cmd_path}", Colors.GREEN))
                claude_args[0] = cmd_path

            # 验证环境变量是否真的被设置
            print(Colors.colorize(f"  -> Final verification in subprocess env:", Colors.CYAN))
            print(Colors.colorize(f"     ANTHROPIC_API_KEY = {'[SET]' if clean_env.get('ANTHROPIC_API_KEY') else '[NOT SET]'}", Colors.CYAN))
            print(Colors.colorize(f"     ANTHROPIC_AUTH_TOKEN = {'[SET]' if clean_env.get('ANTHROPIC_AUTH_TOKEN') else '[NOT SET]'}", Colors.CYAN))
            print(Colors.colorize(f"     ANTHROPIC_BASE_URL = {clean_env.get('ANTHROPIC_BASE_URL', '[NOT SET]')}", Colors.CYAN))

            # 关键修复：临时修改settings.json文件
            print(Colors.colorize(f"  -> Temporarily modifying settings.json to clear env conflicts", Colors.YELLOW))
            backup_settings_path = self._modify_settings_json_temporarily(platform_config)

            try:
                result = subprocess.run(claude_args, env=clean_env, shell=(os.name == "nt"))
            finally:
                # 恢复原始settings.json
                if backup_settings_path and backup_settings_path.exists():
                    print(Colors.colorize(f"  -> Restoring original settings.json", Colors.GRAY))
                    self._restore_settings_json(backup_settings_path)
                    print(Colors.colorize(f"  -> Settings.json restored", Colors.GREEN))
            return result.returncode
        except FileNotFoundError:
            self.log("ERROR", "Claude Code executable not found", {})
            self.log("ERROR", "Please install Claude Code or check PATH", {})
            return 1
        except subprocess.CalledProcessError as e:
            self.log(
                "ERROR",
                f"Claude Code execution failed with exit code: {e.returncode}",
                {"exit_code": e.returncode},
            )
            return e.returncode
        except KeyboardInterrupt:
            self.log("INFO", "Interrupted by user")
            return 130
        except Exception as e:
            self.log("ERROR", f"Unexpected execution error: {e}", {"exception": str(e)})
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
            "-c", "--continue", action="store_true", help="Continue existing session"
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

        # 配置已由统一配置管理器处理，无需同步

        # 设置环境
        self.setup_environment(platform_config)

        # 管理会话
        session_id = self.manage_session(
            selected_platform, getattr(parsed_args, "continue")
        )

        # 创建session映射（session_id已经是正确的带前缀UUID）
        self._create_dual_session_mapping(session_id, session_id, selected_platform)

        # 显示会话信息
        print(Colors.colorize("Session ready", Colors.GREEN))
        print(Colors.colorize(f"   UUID: {session_id}", Colors.GREEN))
        print(Colors.colorize(f"   Standard UUID: {session_id}", Colors.GRAY))
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

        # 启动 Claude Code（传递带前缀的 UUID 用于平台检测）
        exit_code = self.launch_claude(
            session_id,
            getattr(parsed_args, "continue"),
            parsed_args.remaining_args,
            platform_config,
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

    def _create_settings_env_config(self, platform_config: Dict[str, Any]) -> Dict[str, str]:
        """Create environment configuration for settings.json"""
        env_config = {}

        # 设置认证信息
        if platform_config.get("api_key"):
            env_config.update({
                "ANTHROPIC_API_KEY": platform_config["api_key"],
                "ANTHROPIC_AUTH_TOKEN": ""
            })
        elif platform_config.get("auth_token"):
            env_config.update({
                "ANTHROPIC_AUTH_TOKEN": platform_config["auth_token"],
                "ANTHROPIC_API_KEY": ""
            })

        # 设置API基础URL
        if platform_config.get("api_base_url"):
            env_config["ANTHROPIC_BASE_URL"] = platform_config["api_base_url"]

        # 设置模型配置 - 重要的新增功能
        model = platform_config.get("model", "")
        if model:
            # 设置通用模型配置
            env_config["ANTHROPIC_MODEL"] = model
            env_config["ANTHROPIC_DEFAULT_HAIKU_MODEL"] = model
            env_config["ANTHROPIC_DEFAULT_SONNET_MODEL"] = model
            env_config["ANTHROPIC_DEFAULT_OPUS_MODEL"] = model
            env_config["ANTHROPIC_SMALL_FAST_MODEL"] = platform_config.get("small_model", model)

        return env_config

    def _setup_subprocess_env(self, platform_config: Dict[str, Any]) -> Dict[str, str]:
        """Setup subprocess environment variables"""
        clean_env = os.environ.copy()

        # 设置认证信息
        if platform_config.get("api_key"):
            clean_env["ANTHROPIC_API_KEY"] = platform_config["api_key"]
            clean_env["ANTHROPIC_AUTH_TOKEN"] = ""
        elif platform_config.get("auth_token"):
            clean_env["ANTHROPIC_AUTH_TOKEN"] = platform_config["auth_token"]
            clean_env["ANTHROPIC_API_KEY"] = ""

        # 设置API基础URL
        if platform_config.get("api_base_url"):
            clean_env["ANTHROPIC_BASE_URL"] = platform_config["api_base_url"]

        # 设置模型配置 - 确保所有模型环境变量都被正确设置
        model = platform_config.get("model", "")
        if model:
            clean_env["ANTHROPIC_MODEL"] = model
            clean_env["ANTHROPIC_DEFAULT_HAIKU_MODEL"] = model
            clean_env["ANTHROPIC_DEFAULT_SONNET_MODEL"] = model
            clean_env["ANTHROPIC_DEFAULT_OPUS_MODEL"] = model
            clean_env["ANTHROPIC_SMALL_FAST_MODEL"] = platform_config.get("small_model", model)

        # 设置Claude Code配置变量
        claude_code_config = platform_config.get("claude_code_config", {})
        if claude_code_config.get("max_output_tokens"):
            clean_env["CLAUDE_CODE_MAX_OUTPUT_TOKENS"] = str(claude_code_config["max_output_tokens"])

        return clean_env

    def _modify_settings_json_temporarily(self, platform_config: Dict[str, Any]) -> Optional[Path]:
        """Temporarily modify settings.json and return backup path"""
        user_settings_path = Path.home() / ".claude" / "settings.json"
        backup_settings_path = Path.home() / ".claude" / "settings.json.backup"

        if not user_settings_path.exists():
            return None

        try:
            # 备份原始settings.json
            shutil.copy2(user_settings_path, backup_settings_path)
            print(Colors.colorize(f"  -> Backed up settings.json to settings.json.backup", Colors.GRAY))

            # 读取并修改settings.json
            with open(user_settings_path, "r", encoding="utf-8") as f:
                settings_data = json.load(f)

            # 保存原始env配置用于调试
            original_env = settings_data.get("env", {})
            print(Colors.colorize(f"  -> Original env in settings.json: {list(original_env.keys())}", Colors.CYAN))

            # 设置正确的环境变量配置
            settings_data["env"] = self._create_settings_env_config(platform_config)

            # 写入修改后的settings.json
            with open(user_settings_path, "w", encoding="utf-8") as f:
                json.dump(settings_data, f, indent=2, ensure_ascii=False)

            print(Colors.colorize(f"  -> Updated env configuration in settings.json", Colors.GREEN))
            return backup_settings_path
        except Exception as e:
            print(Colors.colorize(f"  -> Warning: Failed to modify settings.json: {e}", Colors.RED))
            return None

    def _restore_settings_json(self, backup_settings_path: Optional[Path]):
        """Restore original settings.json from backup"""
        if backup_settings_path and backup_settings_path.exists():
            user_settings_path = Path.home() / ".claude" / "settings.json"
            shutil.move(backup_settings_path, user_settings_path)


def main():
    """主函数"""
    launcher = ClaudeLauncher()
    exit_code = launcher.run(sys.argv[1:])
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
