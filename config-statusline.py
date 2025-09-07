#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Claude Code Status Line - Configuration Tool
状态栏配置工具 - 支持多模式配置和智能设置
"""

import json
import sys
import os
import argparse
from pathlib import Path

# Import unified configuration manager
try:
    from config import get_config_manager
    from data.logger import log_message
except ImportError:
    # Fallback import for development
    sys.path.insert(0, str(Path(__file__).parent))
    from config import get_config_manager
    sys.path.insert(0, str(Path(__file__).parent / "data"))
    from logger import log_message

# 设置控制台编码
os.environ["PYTHONIOENCODING"] = "utf-8"

# 项目目录
PROJECT_DIR = Path(__file__).parent
DATA_DIR = PROJECT_DIR / "data"

# 确保目录存在
(DATA_DIR / "config").mkdir(parents=True, exist_ok=True)
(DATA_DIR / "cache").mkdir(parents=True, exist_ok=True)

# Configuration manager instance placeholder


# Legacy functions removed - now using unified config manager

def show_mode_examples():
    """显示模式使用示例"""
    print("\n=== Mode Examples ===")
    print("\n1. Basic Mode (GAC Code only):")
    print("   python config-statusline.py --mode basic")
    
    print("\n2. Single Platform Mode:")
    print("   python config-statusline.py --mode single:deepseek")
    print("   python config-statusline.py --mode single:kimi")
    print("   python config-statusline.py --mode single:sf")
    
    print("\n3. Multi-Platform Mode:")
    print("   python config-statusline.py --mode multi")
    print("   # Then use launcher scripts:")
    print("   .\\examples\\cc.mp.ps1 dp    # DeepSeek")
    print("   .\\examples\\cc.mp.ps1 kimi  # Kimi")
    
    print("\n4. Test mode detection:")
    print("   python config-statusline.py --test-mode 02abcdef-1234-5678-9012-123456789abc")
    print("")


def print_current_config():
    """打印当前配置"""
    config_manager = get_config_manager()
    config = config_manager.load_config()
    
    print("\n=== Current GAC Code Configuration ===")
    
    # 显示模式信息
    launcher_settings = config_manager.get_launcher_settings()
    default_platform = launcher_settings.get("default_platform", "gaccode")
    
    print(f"\nMode Configuration:")
    print(f"  Default Platform: {default_platform}")
    
    # 显示有效平台（模拟没有session_id的情况）
    effective_platform = config_manager.get_effective_platform()
    print(f"  Effective Platform (no session): {effective_platform}")
    
    # 显示平台配置状态
    print(f"\nPlatform Status:")
    platforms = config_manager.get_platforms()
    for platform_id, platform_config in platforms.items():
        enabled = platform_config.get("enabled", False)
        api_key = config_manager.get_platform_api_key(platform_id)
        has_key = bool(api_key and api_key.strip())
        
        status_icon = "✓" if enabled and has_key else "✗" if enabled else "-"
        key_status = "(key configured)" if has_key else "(no key)"
        enabled_status = "enabled" if enabled else "disabled"
        
        print(f"  {status_icon} {platform_id}: {enabled_status} {key_status}")
    
    # 显示状态条配置
    statusline_config = config_manager.get_statusline_settings()
    print("\nStatusLine Display Options:")
    for key in ["show_model", "show_directory", "show_git_branch", "show_time", 
                "show_session_duration", "show_session_cost", "show_balance", 
                "show_subscription", "show_today_usage"]:
        value = statusline_config.get(key, False)
        status = "✓" if value else "✗"
        print(f"  {status} {key}: {value}")
    
    print(f"\nLayout: {statusline_config.get('layout', 'single_line')}")
    print(f"Directory Full Path: {statusline_config.get('directory_full_path', True)}")
    
    # 显示倍率配置
    multiplier_config = config_manager.get_multiplier_config()
    if multiplier_config.get("enabled", True):
        print("\nMultiplier Configuration: Enabled")
        periods = multiplier_config.get("periods", [])
        for period in periods:
            name = period.get("name", "unknown")
            start = period.get("start_time", "")
            end = period.get("end_time", "")
            multiplier = period.get("multiplier", 1)
            display = period.get("display_text", f"{multiplier}X")
            weekdays_only = " (weekdays only)" if period.get("weekdays_only", False) else ""
            print(f"  - {name}: {start}-{end} = {display}{weekdays_only}")
    else:
        print("\nMultiplier Configuration: Disabled")
    
    print("")


def interactive_config():
    """交互式配置"""
    config = load_config()

    print("Claude Code 状态栏配置向导")
    print("=" * 50)

    options = [
        ("show_model", "显示模型名称"),
        ("show_time", "显示当前时间"),
        ("show_session_duration", "显示会话时长"),
        ("show_session_cost", "显示会话成本"),
        ("show_directory", "显示目录信息"),
        ("show_git_branch", "显示Git分支"),
        ("show_balance", "显示账户余额"),
        ("show_subscription", "显示订阅信息"),
    ]

    for key, desc in options:
        current = config[key]
        while True:
            response = (
                input(
                    f"{desc} [当前: {'是' if current else '否'}] (y/n/回车保持不变): "
                )
                .strip()
                .lower()
            )
            if response == "":
                break
            elif response in ["y", "yes", "是"]:
                config[key] = True
                break
            elif response in ["n", "no", "否"]:
                config[key] = False
                break
            else:
                print("请输入 y/n 或直接回车保持不变")

    # 目录路径配置
    if config["show_directory"]:
        current = config["directory_full_path"]
        while True:
            response = (
                input(
                    f"显示完整目录路径 [当前: {'是' if current else '否'}] (y/n/回车保持不变): "
                )
                .strip()
                .lower()
            )
            if response == "":
                break
            elif response in ["y", "yes", "是"]:
                config["directory_full_path"] = True
                break
            elif response in ["n", "no", "否"]:
                config["directory_full_path"] = False
                break
            else:
                print("请输入 y/n 或直接回车保持不变")

    # 布局配置
    current = config["layout"]
    while True:
        response = (
            input(f"显示布局 [当前: {current}] (single/multi/回车保持不变): ")
            .strip()
            .lower()
        )
        if response == "":
            break
        elif response in ["single", "single_line"]:
            config["layout"] = "single_line"
            break
        elif response in ["multi", "multi_line"]:
            config["layout"] = "multi_line"
            break
        else:
            print("请输入 single 或 multi 或直接回车保持不变")

    print("\n新配置预览:")
    print("-" * 30)
    for key, desc in options:
        print(f"{desc}: {'是' if config[key] else '否'}")
    print(f"显示完整目录路径: {'是' if config['directory_full_path'] else '否'}")
    print(f"显示布局: {config['layout']}")

    while True:
        confirm = input("\n确认保存配置? (y/n): ").strip().lower()
        if confirm in ["y", "yes", "是"]:
            if save_config(config):
                print("配置保存成功！")
            return
        elif confirm in ["n", "no", "否"]:
            print("配置未保存")
            return
        else:
            print("请输入 y/n")


def reset_config():
    """重置为默认配置"""
    if save_config(DEFAULT_CONFIG):
        print("配置已重置为默认值")


def main():
    parser = argparse.ArgumentParser(description="GAC Code Multi-Mode Configuration Tool")
    parser.add_argument("--show", action="store_true", help="Show current configuration")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive configuration mode")
    parser.add_argument("--reset", action="store_true", help="Reset to default configuration")
    parser.add_argument("--set", nargs=2, metavar=("KEY", "VALUE"), 
                       help="Set configuration value (e.g., --set show_balance true)")
    parser.add_argument("--mode", 
                       help="Quick setup mode (basic, single:<platform>, multi)")
    parser.add_argument("--set-default-platform", 
                       help="Set default platform for Single Platform Mode")
    parser.add_argument("--test-mode", 
                       help="Test mode detection for session ID")
    parser.add_argument("--examples", action="store_true", 
                       help="Show mode setup examples")

    args = parser.parse_args()

    if args.show:
        print_current_config()
    elif args.interactive:
        interactive_config()
    elif args.reset:
        reset_config()
    elif args.set:
        key, value = args.set
        config = load_config()
        if key not in config:
            print(f"错误: 未知的配置项 '{key}'")
            print("可用的配置项:")
            for k in config.keys():
                print(f"  {k}")
            return

        # 转换值类型
        if value.lower() in ["true", "yes", "1", "on"]:
            config[key] = True
        elif value.lower() in ["false", "no", "0", "off"]:
            config[key] = False
        else:
            config[key] = value

        if save_config(config):
            print(f"配置项 {key} 已设置为 {config[key]}")
    else:
        print_current_config()
        print("\n使用方法:")
        print("  python config-statusline.py --show          # 显示当前配置")
        print("  python config-statusline.py --interactive   # 交互式配置")
        print("  python config-statusline.py --reset         # 重置为默认配置")
        print("  python config-statusline.py --set KEY VALUE # 设置单个配置项")


def quick_setup_mode(mode_name):
    """快速设置特定模式
    
    Args:
        mode_name: 'basic', 'single:<platform>', 'multi'
    """
    config_manager = get_config_manager()
    
    if mode_name == 'basic':
        # 基础模式 - 重置为GAC Code默认
        config_manager.set_default_platform('gaccode')
        print("✓ Basic Mode configured (GAC Code default)")
        
    elif mode_name.startswith('single:'):
        # 单平台模式
        _, platform = mode_name.split(':', 1)
        platform = config_manager.resolve_platform_alias(platform)
        
        if config_manager.set_default_platform(platform):
            print(f"✓ Single Platform Mode configured ({platform})")
        else:
            print(f"✗ Failed to configure Single Platform Mode for {platform}")
            
    elif mode_name == 'multi':
        # 多平台模式 - 重置默认平台为gaccode，显示使用说明
        config_manager.set_default_platform('gaccode')
        print("✓ Multi-Platform Mode configured")
        print("Use launcher scripts:")
        print("  .\\examples\\cc.mp.ps1 dp    # DeepSeek")
        print("  .\\examples\\cc.mp.ps1 kimi  # Kimi") 
        print("  .\\examples\\cc.mp.ps1 sf    # SiliconFlow")
        
    else:
        print(f"Unknown mode: {mode_name}")
        print("Available modes: basic, single:<platform>, multi")


# 此文件已被废弃，不再提供命令行配置接口
# 按照纯配置驱动架构设计，用户应直接编辑 data/config/config.json 文件
# 如需要初始化配置，请参考 CONFIGURATION_GUIDE.md 指南
