# 📝 GAC Code 配置驱动架构指南

## 🎯 设计理念：**纯配置驱动，无命令依赖**

本项目采用**配置驱动**的设计理念：用户只需编辑配置文件，系统自动检测和适配，无需记忆任何命令。

## 📁 唯一配置入口

### 配置文件：`data/config/config.json`
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

## 🔧 用户操作方式

### ✅ **推荐方式：编辑配置文件**
```bash
# 1. 初始化配置（仅首次）
cp data/config/config.json.template data/config/config.json

# 2. 编辑配置文件
vim data/config/config.json    # 或使用任何文本编辑器
code data/config/config.json   # VS Code
notepad data/config/config.json # Windows记事本

# 3. 直接在配置文件中添加API密钥

# 4. 测试配置
echo '{"session_id":"test"}' | python statusline.py
```

### ❌ **不推荐：命令行接口**
```bash
# 这些方式违背了配置驱动的设计理念
python config.py --set-default-platform deepseek  # ❌ 复杂
python config.py --show                            # ❌ 不直观
python secure_config.py --audit                   # ❌ 记忆负担
```

## 🎭 四种使用模式（自动检测）

### 1. **零配置模式**
- **用户操作**：无需任何配置
- **系统行为**：自动显示基本信息，不显示余额
- **适用场景**：快速试用、无API密钥时

### 2. **基础模式** 
- **用户操作**：仅设置GAC Code API密钥
- **系统行为**：自动显示GAC Code余额
- **配置示例**：
```json
{
  "platforms": {
    "gaccode": {
      "api_key": "your-gac-api-key"
    }
  }
}
```

### 3. **单平台模式**
- **用户操作**：设置默认平台和对应API密钥  
- **系统行为**：始终显示指定平台余额
- **配置示例**：
```json
{
  "launcher": {
    "default_platform": "deepseek"
  },
  "platforms": {
    "deepseek": {
      "api_key": "your-deepseek-key"
    }
  }
}
```

### 4. **多平台模式**
- **用户操作**：配置多个平台，使用启动脚本
- **系统行为**：根据启动参数显示对应平台余额
- **使用方式**：
```bash
./bin/cc.mp.sh deepseek  # 使用DeepSeek
./bin/cc.mp.sh kimi      # 使用Kimi
```

## 🔒 安全配置（配置文件统一管理）

### 配置文件管理（统一方式）
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
    },
    "kimi": {
      "auth_token": "sk-your-kimi-token",
      "enabled": true
    },
    "siliconflow": {
      "api_key": "sk-your-sf-key",
      "enabled": true
    }
  }
}
```

### 配置原则
1. **配置文件**（唯一配置方式）
2. **GitIgnore保护**（防止意外提交）
3. **系统默认**（零配置模式）

## 🚀 快速开始

### 新用户（零配置）
1. 直接使用：`echo '{"session_id":"test"}' | python statusline.py`
2. 看到基本信息显示，无余额信息

### 有API密钥用户
1. 编辑配置文件：在 `data/config/config.json` 中添加API密钥
2. 测试：`echo '{"session_id":"test"}' | python statusline.py`  
3. 看到余额信息显示

### 多平台用户
1. 在配置文件中配置多个平台的API密钥
2. 使用启动脚本：`./bin/cc.mp.sh deepseek`
3. 享受多平台切换

## 📋 配置文件结构说明

```json
{
  "platforms": {
    // 平台配置：API地址、模型、启用状态
    "platform_name": {
      "name": "显示名称",
      "api_base_url": "API基地址", 
      "api_key": "your-key",   // 填入您的API密钥
      "model": "默认模型",
      "enabled": true
    }
  },
  "launcher": {
    // 启动器配置：默认平台、别名等
    "default_platform": "gaccode",
    "aliases": {
      "dp": "deepseek",
      "gc": "gaccode"
    }
  },
  "statusline": {
    // 显示配置：显示项目、布局等
    "show_balance": true,
    "show_model": true, 
    "layout": "single_line"
  },
  "cache": {
    // 缓存配置：TTL策略等
    "balance_ttl": 300,
    "subscription_ttl": 3600
  }
}
```

## ✨ 核心优势

1. **零学习成本** - 只需编辑一个配置文件
2. **智能自动适配** - 系统根据配置自动选择模式
3. **安全优先** - 配置文件gitignore保护策略
4. **向下兼容** - 现有配置无缝迁移
5. **无命令依赖** - 不需要记住任何命令参数

---

**记住**：编辑 `data/config/config.json`，系统自动工作！🎉