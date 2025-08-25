#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试状态栏脚本
"""

import subprocess
import json
import sys
import os

# 设置控制台编码
os.environ['PYTHONIOENCODING'] = 'utf-8'

def test_statusline():
    """测试状态栏脚本"""
    print("测试GAC状态栏脚本...")
    
    # 模拟Claude Code传入的session数据
    mock_session = {
        "model": {
            "id": "gaccode-claude-3-5-sonnet",
            "displayName": "Claude 3.5 Sonnet (GAC)"
        },
        "workingDirectory": "C:\\Users\\dray\\.claude",
        "sessionId": "test-session"
    }
    
    try:
        # 调用状态栏脚本
        result = subprocess.run(
            ["python", "scripts/gaccode.com/statusline.py"],
            input=json.dumps(mock_session),
            text=True,
            capture_output=True,
            cwd="C:\\Users\\dray\\.claude"
        )
        
        if result.returncode == 0:
            print(f"[SUCCESS] 状态栏输出: {result.stdout}")
        else:
            print(f"[ERROR] 脚本执行失败: {result.stderr}")
            
    except Exception as e:
        print(f"[ERROR] 测试失败: {e}")

def show_usage():
    """显示使用说明"""
    print("\n🔧 GAC状态栏配置完成!")
    print("\n📋 使用说明:")
    print("1. 设置API Token:")
    print("   python scripts/gaccode.com/set-gac-token.py set 'your-token-here'")
    print("\n2. 查看当前配置:")
    print("   python scripts/gaccode.com/set-gac-token.py show")
    print("\n3. 测试状态栏:")
    print("   python scripts/gaccode.com/test-statusline.py")
    print("\n4. 重启Claude Code生效")
    print("\n✨ 状态栏将显示:")
    print("   💰2692/12000 📅09-13(19天)")
    print("\n📍 注意:")
    print("   - 状态栏仅在使用gaccode模型时显示")
    print("   - 数据每5分钟缓存一次，减少API调用")
    print("   - 颜色编码：红色(紧急) 黄色(警告) 绿色(正常)")

if __name__ == "__main__":
    test_statusline()
    show_usage()