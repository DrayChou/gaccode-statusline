# GAC Code Project Structure

## 📁 Directory Structure

```
gaccode.com/
├── bin/                          # 🚀 Launcher Scripts
│   ├── launcher.py              # Main launcher implementation
│   ├── cc.mp.ps1                # PowerShell wrapper
│   ├── cc.mp.sh                 # Bash wrapper
│   └── cc.mp.bat                # Windows CMD wrapper
│
├── data/                        # 📊 Data & Configuration
│   ├── config/                  # Configuration files
│   │   ├── config.json.template # Configuration template
│   │   └── config.json         # Active configuration (gitignored)
│   ├── cache/                   # Runtime cache files
│   └── logs/                    # Application logs
│
├── platforms/                   # 🔌 Platform Implementations
│   ├── base.py                  # Abstract base platform
│   ├── manager.py               # Platform manager
│   ├── gaccode.py              # GAC Code platform
│   ├── kimi.py                 # Kimi platform
│   ├── deepseek.py             # DeepSeek platform
│   └── siliconflow.py          # SiliconFlow platform
│
├── examples/                    # 📋 Demo Configurations
│   ├── README.md               # Examples guide
│   ├── launcher-config.json    # Sample launcher config
│   └── launcher-config.template.json
│
├── docs/                       # 📖 Documentation
│   ├── *.md                    # Various guides
│   └── archives/               # Archived documentation
│
├── *.py                        # 🛠️ Core System Files
│   ├── statusline.py           # Main status line (Claude Code integration)
│   ├── config.py               # Unified configuration manager
│   ├── cache.py                # Unified cache system
│   ├── session.py              # Session management
│   ├── platform_manager.py     # Platform manager CLI
│   ├── config-statusline.py    # Status line configuration
│   └── setup-config.py         # Configuration setup script
│
└── Configuration Files
    ├── CLAUDE.md               # Project-specific Claude instructions
    ├── .gitignore              # Git ignore patterns
    └── PROJECT_STRUCTURE.md   # This file
```

## 🎯 Usage Modes

### 1. Zero Configuration Mode
- **Setup**: None required
- **Usage**: Direct Claude Code integration
- **Display**: Basic info only (no balance)

### 2. Basic Mode
- **Setup**: Configure GAC Code API key
- **Usage**: Direct Claude Code integration  
- **Display**: GAC Code balance + basic info

### 3. Single Platform Mode  
- **Setup**: Set default platform + API keys
- **Usage**: Direct Claude Code integration
- **Display**: Default platform balance + basic info

### 4. Multi-Platform Mode
- **Setup**: Configure multiple platforms
- **Usage**: Use `bin/launcher.py` or wrapper scripts
- **Display**: Dynamic platform balance based on launch parameters

## 🚀 Quick Start

### Initial Setup
```bash
# 1. Initialize configuration
python setup-config.py

# 2. Edit configuration file
# Add your API keys to data/config/config.json
```

### Launch Options
```bash
# Multi-Platform Mode
./bin/cc.mp.sh dp        # DeepSeek
./bin/cc.mp.sh kimi      # Kimi  
./bin/cc.mp.sh gc        # GAC Code

# Or direct launcher
python bin/launcher.py deepseek
```

### Configuration Management
所有配置通过编辑 `data/config/config.json` 完成：
```json
{
  "launcher": {
    "default_platform": "deepseek"  // 设置默认平台
  },
  "statusline": {
    "show_balance": true,            // 显示余额
    "layout": "single_line"          // 布局设置
  }
}
```

**配置验证**:
```bash
# 验证配置文件格式
python -c "import json; print('✅ Valid' if json.load(open('data/config/config.json')) else '❌ Invalid')"

# 测试基本功能
echo '{"session_id":"test"}' | python statusline.py
```

## 🔧 Key Components

- **📊 statusline.py**: Claude Code integration point with intelligent mode detection
- **⚙️ config.py**: Unified configuration system with validation
- **🗃️ cache.py**: Dual-layer caching (memory + disk) with TTL management  
- **🎭 session.py**: Session management with UUID prefix platform detection
- **🔌 platforms/**: Modular platform implementations following base interface
- **🚀 bin/launcher.py**: Multi-platform session launcher with config synchronization

## 📋 Features

✅ **Four Usage Modes**: Zero-config, Basic, Single Platform, Multi-Platform
✅ **Intelligent Mode Detection**: Automatic detection based on session context
✅ **Unified Configuration**: Single source of truth with template system
✅ **Performance Optimized**: O(1) UUID prefix detection + intelligent caching
✅ **Cross-Platform**: Windows, macOS, Linux support
✅ **Security-First**: API keys properly masked and gitignored
✅ **Extensible Architecture**: Easy to add new platforms