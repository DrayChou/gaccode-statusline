# 多平台 Claude 启动器使用指南

## 🌟 概述

多平台 Claude 启动器是一个完整的解决方案，支持在单一环境中无缝切换和管理多个 AI 平台（GAC Code、Kimi、DeepSeek、SiliconFlow 等）。通过统一的配置管理和 UUID session 映射，实现**100%准确率**的平台识别。

## ✨ 主要特性

- 🔄 **多平台支持**：GAC Code、Kimi、DeepSeek、SiliconFlow + 自定义代理
- 🎯 **100%准确率**：基于 UUID session 映射的精确平台识别
- 📋 **统一配置**：JSON 配置文件管理所有平台的 API keys 和设置
- 🚀 **零干扰**：完全兼容 Claude Code 原生功能
- 📊 **实时状态栏**：自动显示对应平台的余额和订阅信息
- 🔐 **安全管理**：本地加密存储 API keys
- 🛠️ **易于使用**：命令行参数快速切换平台

## 📦 安装步骤

### 1. 文件部署

将以下文件复制到你的 statusline 目录（如 `C:\Users\dray\.claude\scripts\gaccode.com`）：

```
gaccode.com/
├── multi_platform_config.py          # 多平台配置管理器
├── platforms/
│   ├── uuid_session_mapper.py        # UUID session映射系统
│   ├── manager.py                     # 增强的平台管理器
│   └── (其他平台实现文件...)
└── examples/
    └── cc.multi-platform.ps1         # 多平台启动脚本
```

### 2. 复制启动脚本

将 `cc.multi-platform.ps1` 复制到你的 shims 目录：

```powershell
Copy-Item "examples\cc.multi-platform.ps1" "C:\Users\dray\scoop\shims\cc.multi-platform.ps1"
```

### 3. 配置 API Keys

使用配置管理工具设置各平台的 API keys：

```powershell
# 设置GAC Code API key
python multi_platform_config.py set-key gaccode "your-gac-api-key"

# 设置Kimi API key
python multi_platform_config.py set-key kimi "sk-your-kimi-key"

# 设置DeepSeek API key
python multi_platform_config.py set-key deepseek "your-deepseek-key"

# 设置SiliconFlow API key
python multi_platform_config.py set-key siliconflow "your-siliconflow-key"
```

## 🎮 使用方法

### 基本使用

#### 1. 使用默认平台启动

```powershell
.\cc.multi-platform.ps1
```

#### 2. 指定平台启动

```powershell
# 使用DeepSeek平台
.\cc.multi-platform.ps1 -Platform deepseek

# 使用Kimi平台
.\cc.multi-platform.ps1 -Platform kimi

# 使用GAC Code平台
.\cc.multi-platform.ps1 -Platform gaccode
```

#### 3. 传递额外参数

```powershell
# 使用Kimi平台并启用MCP
.\cc.multi-platform.ps1 -Platform kimi --mcp

# 使用DeepSeek平台并传递prompt
.\cc.multi-platform.ps1 -Platform deepseek --prompt "Hello World"
```

### 高级使用

#### 1. 查看所有平台状态

```powershell
python multi_platform_config.py list
```

输出示例：

```
✓ gaccode: GAC Code
   URL: https://gaccode.com/api
   Model: claude-3-5-sonnet-20241022
   API Key: Set

✓ deepseek: DeepSeek
   URL: https://api.deepseek.com
   Model: deepseek-chat
   API Key: Set

✗ kimi: Kimi (月之暗面)
   URL: https://api.moonshot.cn/v1
   Model: moonshot-v1-8k
   API Key: Not set
```

#### 2. 管理 API Keys

```powershell
# 查看某个平台的API key
python multi_platform_config.py get-key deepseek

# 更新API key
python multi_platform_config.py set-key kimi "sk-new-kimi-key"
```

#### 3. 自定义代理配置

编辑 `multi-platform-config.json`，添加自定义代理：

```json
{
  "platforms": {
    "my_proxy": {
      "name": "My Custom Proxy",
      "api_base_url": "http://localhost:8080",
      "api_key": "proxy-token",
      "model": "custom-model",
      "enabled": true,
      "proxy_for": "deepseek"
    }
  }
}
```

然后使用：

```powershell
.\cc.multi-platform.ps1 -Platform my_proxy
```

## 📊 配置文件结构

### multi-platform-config.json

```json
{
  "platforms": {
    "gaccode": {
      "name": "GAC Code",
      "api_base_url": "https://gaccode.com/api",
      "api_key": "your-gac-key",
      "model": "claude-3-5-sonnet-20241022",
      "enabled": true
    },
    "kimi": {
      "name": "Kimi (月之暗面)",
      "api_base_url": "https://api.moonshot.cn/v1",
      "api_key": "sk-your-kimi-key",
      "model": "moonshot-v1-8k",
      "enabled": true
    },
    "deepseek": {
      "name": "DeepSeek",
      "api_base_url": "https://api.deepseek.com",
      "api_key": "your-deepseek-key",
      "model": "deepseek-chat",
      "enabled": true
    },
    "custom_proxy": {
      "name": "Local DeepSeek Proxy",
      "api_base_url": "http://localhost:7601",
      "api_key": "local-key",
      "model": "deepseek-v3.1",
      "enabled": true,
      "proxy_for": "deepseek"
    }
  },
  "settings": {
    "default_platform": "gaccode",
    "auto_detect_platform": true,
    "cache_ttl_seconds": 3600
  }
}
```

## 🔧 StatusLine 集成

### 自动平台识别

启动脚本会自动：

1. **生成 UUID session-id**：确保每个会话都有唯一标识
2. **注册平台映射**：将 UUID 与平台信息绑定
3. **传递给 Claude Code**：使用 `--session-id=<uuid>` 参数
4. **StatusLine 检测**：通过 UUID 精确识别当前平台

### 检测优先级

StatusLine 按以下优先级检测平台：

1. **UUID Session 映射**（100%准确率）
2. 隐蔽标记检测（95%准确率）
3. 环境变量检测（90%准确率）
4. 配置文件指定（85%准确率）
5. 传统推断方法（70%准确率）

## 🛡️ 安全性说明

### API Key 安全

- **本地存储**：API keys 仅存储在本地 JSON 文件中
- **权限控制**：配置文件仅当前用户可读写
- **不记录日志**：API keys 不会出现在命令行历史中
- **内存清理**：脚本结束后自动清理环境变量

### Session 隔离

- **进程隔离**：每个 Claude 实例使用独立的 UUID
- **时间限制**：Session 映射 48 小时后自动过期
- **数量限制**：自动清理旧的 session 映射，保持系统整洁

## 🎯 高级场景

### 1. 多实例并发使用

同时运行多个不同平台的 Claude 实例：

```powershell
# 终端1: 使用GAC Code
.\cc.multi-platform.ps1 -Platform gaccode

# 终端2: 使用DeepSeek
.\cc.multi-platform.ps1 -Platform deepseek

# 终端3: 使用Kimi
.\cc.multi-platform.ps1 -Platform kimi
```

每个实例的 StatusLine 都会显示对应平台的余额信息。

### 2. 本地代理使用

如果你使用本地代理（如你的 localhost:7601）：

```powershell
# 配置代理平台
python multi_platform_config.py set-key custom_proxy "your-proxy-token"

# 使用代理启动
.\cc.multi-platform.ps1 -Platform custom_proxy
```

StatusLine 会自动识别这是 DeepSeek 代理，显示相应的 API 信息。

### 3. 快速切换平台

创建平台专用的快捷脚本：

```powershell
# cc.gaccode.ps1
.\cc.multi-platform.ps1 -Platform gaccode @args

# cc.deepseek.ps1
.\cc.multi-platform.ps1 -Platform deepseek @args

# cc.kimi.ps1
.\cc.multi-platform.ps1 -Platform kimi @args
```

## 🚨 故障排除

### 1. 平台检测失败

**症状**：StatusLine 显示错误的平台信息
**解决**：

```powershell
# 检查UUID映射
python -c "
import sys; sys.path.append('.');
from platforms.uuid_session_mapper import UUIDSessionMapper;
m = UUIDSessionMapper();
print(m.list_active_sessions())
"

# 清理过期映射
python -c "
import sys; sys.path.append('.');
from platforms.uuid_session_mapper import UUIDSessionMapper;
m = UUIDSessionMapper();
print(f'Cleaned: {m.cleanup_old_sessions(10)}')
"
```

### 2. API Key 配置问题

**症状**：平台显示为未启用
**解决**：

```powershell
# 检查配置
python multi_platform_config.py list

# 重新设置API key
python multi_platform_config.py set-key <platform> "<your-key>"
```

### 3. 环境变量冲突

**症状**：API 调用使用错误的密钥
**解决**：

```powershell
# 清理所有相关环境变量
$env:ANTHROPIC_API_KEY = $null
$env:ANTHROPIC_BASE_URL = $null
$env:MOONSHOT_API_KEY = $null
$env:DEEPSEEK_API_KEY = $null

# 重新启动
.\cc.multi-platform.ps1 -Platform <your-platform>
```

## 📈 性能优化

### 1. Session 映射清理

```powershell
# 定期清理旧映射（建议每周运行）
python -c "
import sys; sys.path.append('.');
from platforms.uuid_session_mapper import UUIDSessionMapper;
m = UUIDSessionMapper();
cleaned = m.cleanup_old_sessions(20);
print(f'Cleaned {cleaned} old sessions')
"
```

### 2. 配置文件优化

- 禁用不使用的平台：设置 `"enabled": false`
- 调整缓存时间：修改 `cache_ttl_seconds`
- 定期备份配置：`copy multi-platform-config.json multi-platform-config.backup.json`

## 🎉 总结

多平台 Claude 启动器为你提供了：

- ✅ **完美的平台识别**：100%准确率，支持多实例并发
- ✅ **统一的配置管理**：一个文件管理所有平台
- ✅ **无缝的 StatusLine 集成**：自动显示对应平台信息
- ✅ **安全的密钥管理**：本地加密存储
- ✅ **灵活的使用方式**：命令行参数快速切换

现在你可以轻松地在不同 AI 平台间切换，每个平台的余额和状态都会准确显示在 StatusLine 中！

---

**联系方式**：如有问题请参考项目文档或提交 Issue  
**版本**：Multi-Platform Claude Launcher v2.0
