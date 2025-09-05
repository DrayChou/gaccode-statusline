#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Claude Code Status Line - Configuration Tool
状态栏配置工具
"""

import json
import sys
import os
import argparse
from pathlib import Path

# 设置控制台编码
os.environ["PYTHONIOENCODING"] = "utf-8"

# 配置
PROJECT_DIR = Path(__file__).parent  # scripts/gaccode.com目录
CONFIG_FILE = PROJECT_DIR / "statusline-config.json"

# 默认显示配置
DEFAULT_CONFIG = {
    "show_model": True,
    "show_directory": True,
    "show_git_branch": True,
    "show_time": True,
    "show_session_duration": False,
    "show_session_cost": True,
    "show_balance": True,
    "show_subscription": True,
    "directory_full_path": True,
    "layout": "single_line",  # single_line 或 multi_line
}


def load_config():
    """加载当前配置"""
    if not CONFIG_FILE.exists():
        return DEFAULT_CONFIG.copy()

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8-sig") as f:
            config = json.load(f)
            # 合并默认配置，确保所有选项都存在
            result = DEFAULT_CONFIG.copy()
            result.update(config)
            return result
    except Exception:
        return DEFAULT_CONFIG.copy()


def save_config(config):
    """保存配置"""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8-sig") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        print(f"配置已保存到: {CONFIG_FILE}")
        return True
    except Exception as e:
        print(f"保存配置失败: {e}")
        return False


def show_current_config():
    """显示当前配置"""
    config = load_config()

    print("当前状态栏配置:")
    print("=" * 50)
    print(f"显示模型名称:      {config['show_model']}")
    print(f"显示当前时间:      {config['show_time']}")
    print(f"显示会话时长:      {config['show_session_duration']}")
    print(f"显示会话成本:      {config['show_session_cost']}")
    print(f"显示目录信息:      {config['show_directory']}")
    print(f"显示Git分支:       {config['show_git_branch']}")
    print(f"显示账户余额:      {config['show_balance']}")
    print(f"显示订阅信息:      {config['show_subscription']}")
    print(f"显示完整目录路径:  {config['directory_full_path']}")
    print(f"显示布局:          {config['layout']}")
    print("=" * 50)


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
    parser = argparse.ArgumentParser(description="Claude Code 状态栏配置工具")
    parser.add_argument("--show", action="store_true", help="显示当前配置")
    parser.add_argument("--interactive", action="store_true", help="交互式配置")
    parser.add_argument("--reset", action="store_true", help="重置为默认配置")
    parser.add_argument(
        "--set", nargs=2, metavar=("KEY", "VALUE"), help="设置单个配置项"
    )

    args = parser.parse_args()

    if args.show:
        show_current_config()
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
        show_current_config()
        print("\n使用方法:")
        print("  python config-statusline.py --show          # 显示当前配置")
        print("  python config-statusline.py --interactive   # 交互式配置")
        print("  python config-statusline.py --reset         # 重置为默认配置")
        print("  python config-statusline.py --set KEY VALUE # 设置单个配置项")


if __name__ == "__main__":
    main()
