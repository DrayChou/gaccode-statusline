#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GAC API Token 管理工具
"""

import sys
import os
from pathlib import Path

# 设置控制台编码
os.environ['PYTHONIOENCODING'] = 'utf-8'

PROJECT_DIR = Path(__file__).parent  # 项目根目录
TOKEN_FILE = PROJECT_DIR / "api-token.txt"

def set_token(token):
    """设置token"""
    # 确保项目目录存在
    PROJECT_DIR.mkdir(parents=True, exist_ok=True)
    
    # 保存token
    with open(TOKEN_FILE, 'w', encoding='utf-8') as f:
        f.write(token.strip())
    
    print(f"[SUCCESS] GAC API Token已保存到 {TOKEN_FILE}")

def show_token():
    """显示当前token状态"""
    if TOKEN_FILE.exists():
        with open(TOKEN_FILE, 'r', encoding='utf-8') as f:
            token = f.read().strip()
        
        # 只显示前10个和后4个字符
        if len(token) > 14:
            masked_token = token[:10] + "..." + token[-4:]
        else:
            masked_token = token
            
        print(f"[INFO] 当前已配置token: {masked_token}")
    else:
        print("[WARN] 未配置GAC API Token")

def remove_token():
    """删除token"""
    if TOKEN_FILE.exists():
        TOKEN_FILE.unlink()
        print("[SUCCESS] GAC API Token已删除")
    else:
        print("[WARN] 未配置GAC API Token")

def main():
    if len(sys.argv) < 2:
        print("GAC API Token 管理工具")
        print()
        print("用法:")
        print("  python set-gac-token.py set <token>     # 设置token")
        print("  python set-gac-token.py show            # 显示当前token")
        print("  python set-gac-token.py remove          # 删除token")
        print()
        show_token()
        return
    
    command = sys.argv[1].lower()
    
    if command == "set":
        if len(sys.argv) != 3:
            print("[ERROR] 请提供token: python set-gac-token.py set <token>")
            return
        set_token(sys.argv[2])
    
    elif command == "show":
        show_token()
    
    elif command == "remove":
        remove_token()
    
    else:
        print(f"[ERROR] 未知命令: {command}")
        print("支持的命令: set, show, remove")

if __name__ == "__main__":
    main()