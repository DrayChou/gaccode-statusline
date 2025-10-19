# GAC Code Multi-Platform Status Line v2.0

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.7+-blue.svg)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)
![Architecture](https://img.shields.io/badge/architecture-Configuration%20Driven-green.svg)

**纯配置驱动**的多平台Claude Code状态栏插件，支持GAC Code、Kimi、DeepSeek、SiliconFlow等API平台。通过编辑配置文件即可管理所有功能，无需记忆任何命令。

> **🚨 重要通知**: 本项目已于2025年10月分拆为两个独立的专用组件：
> - **[cc-status](https://github.com/DrayChou/cc-status)** - 专用状态栏管理器，显示所有平台余额信息
> - **[cc-launcher](https://github.com/DrayChou/cc-launcher)** - 专用多平台启动器，支持会话管理
>
> **🎯 迁移建议**: 新的分离架构提供更好的维护性、专用功能和增强体验：
> - **cc-status**: 支持多平台同时显示、后台任务自动更新、丰富颜色系统
> - **cc-launcher**: 增强的会话管理、改进的平台切换、配置验证
>
> 本项目保留作为历史版本和参考实现，建议用户迁移到新组件。

## ✨ 核心特性

### 🎯 纯配置驱动设计
- **零命令记忆** - 用户只需编辑配置文件，系统自动工作
- **智能模式检测** - 根据配置自动适配四种使用模式
- **配置文件统一** - 安全的凭证管理，统一配置文件入口

### 🌐 多平台支持
- **GAC Code** - 国内Claude API服务
- **DeepSeek** - 深度求索AI平台  
- **Kimi** - 月之暗面Moonshot API
- **SiliconFlow** - 硅基流动AI平台
- **Local Proxy** - 本地代理支持

### 📊 实时状态显示
- **动态余额显示** - 实时账户余额和订阅信息
- **会话成本追踪** - 当前会话和今日使用量统计
- **智能颜色编码** - 余额状态和使用量等级可视化
- **多重缓存策略** - 1秒UI刷新，5分钟余额缓存，1小时订阅缓存

## 🚀 四种使用模式（自动检测）

项目根据配置自动检测并适配相应模式，用户无需手动切换：

### 1. 零配置模式 (Zero Config Mode)
- **触发条件**: 无任何API密钥配置
- **功能特性**: 显示基本会话信息，不显示余额
- **适用场景**: 快速试用、演示、无API密钥时

### 2. 基础模式 (Basic Mode)  
- **触发条件**: 仅配置GAC Code API密钥
- **功能特性**: 自动显示GAC Code余额信息
- **适用场景**: 单一GAC Code用户

### 3. 单平台模式 (Single Platform Mode)
- **触发条件**: 设置了默认平台和对应API密钥
- **功能特性**: 始终显示指定平台的余额信息
- **适用场景**: 主要使用一个平台的用户

### 4. 多平台模式 (Multi-Platform Mode)
- **触发条件**: 配置多个平台，使用启动脚本
- **功能特性**: 根据启动参数显示对应平台余额
- **适用场景**: 需要在多个平台间切换的用户

## 📦 安装配置

### 前置要求
- Python 3.7+
- Claude Code
- 至少一个支持平台的API密钥

### 快速安装

1. **克隆项目**
```bash
git clone https://github.com/DrayChou/gaccode-statusline.git
cd gaccode-statusline
```

2. **初始化配置**
```bash
python setup-config.py
```

3. **配置Claude Code状态栏**

编辑Claude Code配置文件 `~/.claude/settings.json`:
```json
{
  "statusLine": {
    "type": "command", 
    "command": "python /path/to/gaccode-statusline/statusline.py",
    "refreshInterval": 1000
  }
}
```

## ⚙️ 配置管理

### 唯一配置入口

所有配置通过单一文件管理：`data/config/config.json`

```json
{
  "platforms": {
    "gaccode": {
      "name": "GAC Code",
      "api_base_url": "https://relay05.gaccode.com/claudecode", 
      "api_key": "",
      "enabled": true
    },
    "deepseek": {
      "name": "DeepSeek",
      "api_base_url": "https://api.deepseek.com/anthropic",
      "api_key": "",
      "enabled": true  
    }
  },
  "launcher": {
    "default_platform": "gaccode"
  },
  "statusline": {
    "show_balance": true,
    "show_model": true,
    "layout": "single_line"
  }
}
```

### 安全的凭证管理

**配置方式：编辑配置文件（统一入口）**
```json
{
  "platforms": {
    "gaccode": {
      "api_key": "sk-your-gac-key",
      "enabled": true
    },
    "deepseek": {
      "api_key": "sk-your-deepseek-key",
      "enabled": true
    }
  }
}
```

**配置原则**
1. 配置文件（唯一配置方式）
2. 模板系统（快速初始化）
3. 系统默认（零配置模式）

## 🎯 使用方法

### 基础使用（推荐）
直接启动Claude Code即可，状态栏将根据配置自动显示相应信息：
```bash
claude
```

### 多平台切换
当需要使用不同平台时，使用启动脚本：
```bash
# 使用DeepSeek平台
./bin/cc.mp.sh deepseek

# 使用Kimi平台  
./bin/cc.mp.sh kimi

# 使用别名
./bin/cc.mp.sh dp  # DeepSeek
./bin/cc.mp.sh gc  # GAC Code
```

## 📋 状态栏显示示例

```bash
# GAC Code - 基础显示
Model:Claude-3.5-Sonnet Time:13:24:15 Cost:$3.75 GAC.B:2692/12000 Git:main

# DeepSeek - 单平台模式
Model:deepseek-v3.1 Time:13:24:15 Cost:¥2.15 Balance:¥45.60/¥100 Git:main

# Kimi - 多平台模式
Model:moonshot-v1-8k Time:13:24:15 Cost:¥1.85 Balance:¥23.40/¥50 Git:main
```

## 🎨 显示配置

编辑 `data/config/config.json` 中的 `statusline` 部分：

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `show_balance` | 显示账户余额 | `true` |
| `show_model` | 显示AI模型名称 | `true` |
| `show_directory` | 显示当前目录 | `true` |
| `show_git_branch` | 显示Git分支 | `true` |
| `show_time` | 显示当前时间 | `true` |
| `show_session_cost` | 显示会话成本 | `true` |
| `layout` | 布局方式 | `"single_line"` |

## 🔧 项目架构

### 配置驱动架构
- **配置入口**: `data/config/config.json`
- **核心模块**: 纯库文件，无CLI接口
- **启动脚本**: `bin/` 目录，保留必要的CLI接口
- **配置管理**: 统一配置文件管理所有设置

### 目录结构
```
gaccode-statusline/
├── statusline.py          # Claude Code集成入口
├── data/
│   ├── config/           # 配置文件目录
│   ├── cache/            # 运行时缓存
│   └── logs/             # 结构化日志
├── bin/                  # 启动脚本
│   ├── launcher.py      # 统一启动器
│   ├── cc.mp.sh         # Bash启动脚本
│   └── cc.mp.ps1        # PowerShell启动脚本  
├── platforms/           # 平台实现
├── config.py           # 配置管理（纯库）
├── cache.py            # 缓存管理（纯库）
├── session.py          # 会话管理（纯库）
└── setup-config.py     # 初始化脚本
```

## 🔒 安全特性

- **API密钥保护**: 配置文件gitignore保护，防止意外提交
- **敏感信息掩码**: 日志和调试输出自动掩码敏感数据
- **文件权限控制**: 配置文件仅用户可读
- **版本控制排除**: `.gitignore`自动排除敏感配置
- **输入验证**: 所有用户输入经过安全验证

## 🧪 测试验证

### 基础功能测试
```bash
# 测试状态栏基本功能
echo '{"session_id":"test"}' | python statusline.py

# 测试平台检测
echo '{"session_id":"02abcdef-1234-5678-9012-123456789abc"}' | python statusline.py
```

### 配置验证
```bash  
# 验证配置文件格式
python -c "import json; print('Config valid:', bool(json.load(open('data/config/config.json'))))"

# 测试配置文件加载
python -c "from config import get_config_manager; cm = get_config_manager(); print('Config loaded:', bool(cm.get_config()))"
```

## ❓ 常见问题

### Q: 状态栏不显示余额信息？
**A**: 检查以下几点：
1. API密钥是否正确配置（通过环境变量或配置文件）
2. 网络连接是否正常
3. 平台API服务是否可用
4. 配置文件格式是否正确

### Q: 如何切换到不同的AI平台？
**A**: 
1. **临时切换**: 使用启动脚本 `./bin/cc.mp.sh deepseek`
2. **永久切换**: 编辑配置文件修改 `launcher.default_platform`

### Q: 如何安全管理API密钥？
**A**: 编辑配置文件并确保不提交到版本控制：
```json
{
  "platforms": {
    "gaccode": {
      "api_key": "your-key",
      "enabled": true
    },
    "deepseek": {
      "api_key": "your-key",
      "enabled": true
    }
  }
}
```

### Q: 配置文件在哪里？
**A**: 所有配置集中在 `data/config/config.json`，这是唯一需要编辑的配置文件。

## 📈 版本更新

### v2.0 重大更新
- **纯配置驱动架构** - 移除所有不必要的CLI接口
- **统一配置管理** - 单一配置文件入口
- **智能模式检测** - 自动适配四种使用模式
- **增强安全性** - 配置文件保护，敏感信息防泄露
- **简化用户体验** - 零学习成本，编辑配置即可

### 迁移指南
从v1.x升级到v2.0：
1. 停止使用所有 `python xxx.py --command` 形式的命令
2. 将配置迁移到 `data/config/config.json`
3. 在配置文件中直接设置API密钥
4. 移除废弃的配置文件

## 🤝 支持与贡献

如果您觉得这个项目有帮助，请考虑：
- ⭐ Star这个仓库
- 🐛 报告问题和Bug
- 💡 提出新功能建议
- 🔧 贡献代码改进

## 📄 许可证

本项目采用MIT许可证 - 详见 [LICENSE](LICENSE) 文件

---

**设计理念**: 纯配置驱动，无命令依赖。用户只需编辑配置文件，系统自动工作！ 🎉