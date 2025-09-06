# GAC Code Multi-Platform Status Line

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.7+-blue.svg)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)

A comprehensive multi-platform statusline for Claude Code that supports GAC Code, Kimi, DeepSeek, SiliconFlow, and Local Proxy APIs. Displays balance, subscription information, and development context in real-time with automatic platform detection.

## ✨ Features

### Multi-Platform Support
- 🌐 **Multiple API Providers**: GAC Code, Kimi (月之暗面), DeepSeek, SiliconFlow, Local Proxy
- 🔄 **Auto Platform Detection**: UUID-based session mapping with 100% accuracy
- 🚀 **Quick Launch Scripts**: Simple alias-based launcher (e.g., `cc.mp.ps1 dp` for DeepSeek)
- 🔑 **Unified Configuration**: Single configuration file for all platforms

### Real-time Status Display
- 🔄 **Real-time Updates**: Displays current balance and subscription status
- 🎨 **Color-coded Status**: Visual indicators for balance and expiry warnings
- ⚡ **Multi-tier Caching**: 1-second UI refresh, 5-minute balance cache, 1-hour subscription cache
- 🕒 **Dynamic Multiplier Detection**: API-based multiplier detection with time-based fallback
- ⚠️ **Smart Warning System**: Red alerts when API/time-based multipliers mismatch
- 📊 **Rich Context**: Shows model, time, session cost, directory, Git branch
- 📈 **Usage Tracking**: Today's usage cost with gaming equipment rarity color coding

### Advanced Features
- 🔒 **Secure Management**: Local configuration with automatic sync to plugin
- 🖥️ **Cross-platform**: Works on Windows, macOS, and Linux
- 🎯 **Claude Code Integration**: Seamless statusline integration
- ⚙️ **Fully Configurable**: Customizable display components and layout
- 💾 **Session Caching**: Caches session information for improved performance

## 📸 Screenshots

**Multi-Platform Display Examples:**

```
# GAC Code - Normal Hours
Model:Claude-3.5-Sonnet Time:13:24:15 Cost:$3.75 Today:$74.47 GAC.B:2692/12000 (45m30s) Dir:myproject Git:main*

# GAC Code - 2x Multiplier Period
Model:Claude-3.5-Sonnet Time:16:45:15 Cost:$7.50 Today:$149.23 GAC.B:1845/12000 2x (23m15s) Dir:myproject Git:main*

# GAC Code - High Multiplier Warning
Model:Claude-3.5-Sonnet Time:20:30:15 Cost:$15.00 Today:$298.75 GAC.B:1203/12000 !5x (12m42s) Dir:myproject Git:main*

# DeepSeek
Model:deepseek-v3.1 Time:13:24:15 Cost:$2.15 Balance:¥45.60/¥100 Dir:myproject Git:main*

# Kimi (月之暗面)  
Model:moonshot-v1-8k Time:13:24:15 Cost:¥1.85 Balance:¥23.40/¥50 Dir:myproject Git:main*

# SiliconFlow
Model:deepseek-ai/deepseek-v3.1 Time:13:24:15 Cost:$1.95 Balance:$18.75/$30 Dir:myproject Git:main*
```

**Color-coded Status Examples:**
| Status | Balance Display | Multiplier Display | Expires Display |
|--------|------------------|--------------------|-----------------|
| 🟢 Healthy | `GAC.B:`<span style="color:green">**3500**</span>`/12000` | <span style="color:yellow">**2x**</span> | `Expires:`<span style="color:green">**09-25(30d)**</span> |
| 🟡 Warning | `GAC.B:`<span style="color:orange">**750**</span>`/12000` | <span style="color:purple">**5x**</span> | `Expires:`<span style="color:orange">**09-18(10d)**</span> |
| 🔴 Critical | `GAC.B:`<span style="color:red">**350**</span>`/12000` | <span style="color:red">**!10x**</span> | `Expires:`<span style="color:red">**09-15(3d)**</span> |

**Multiplier Color Coding:**
- 🟢 **Green** (1x): Regular hours
- 🟡 **Yellow** (2-4x): Medium multiplier periods  
- 🟣 **Purple** (5x+): High multiplier periods
- 🔴 **Red** (!Nx): Warning - API data conflicts with time-based detection

## 🚀 Quick Start

### Prerequisites

- Python 3.7+
- Claude Code installed
- API access for at least one supported platform
- Node.js and npm (for usage tracking feature)

### Installation

1. Clone this repository:
```bash
git clone https://github.com/DrayChou/gaccode-statusline.git
cd gaccode-statusline
```

2. Configure your API keys:
```bash
# Set API key for any platform (supports aliases)
python platform_manager.py set-key dp "your-deepseek-api-key"
python platform_manager.py set-key kimi "your-kimi-api-key"
python platform_manager.py set-key gc "your-gac-api-key"

# View platform status
python platform_manager.py list
```

3. Configure Claude Code statusline in `.claude/settings.json`:
```json
{
  "statusLine": {
    "type": "command",
    "command": "python /path/to/gaccode-statusline/statusline.py",
    "padding": 1,
    "refreshInterval": 1000
  }
}
```

4. (Optional) Customize display settings:
```bash
python config-statusline.py --interactive
```

## 🎯 Multi-Platform Launcher

### Quick Launch Scripts

Use the convenient launcher scripts in the `examples/` directory:

**Windows PowerShell:**
```powershell
# Launch DeepSeek
.\examples\cc.mp.ps1 dp

# Launch Kimi
.\examples\cc.mp.ps1 kimi

# Launch GAC Code
.\examples\cc.mp.ps1 gc

# Launch SiliconFlow
.\examples\cc.mp.ps1 sf

# Launch Local Proxy
.\examples\cc.mp.ps1 local
```

**Linux/Mac:**
```bash
# Launch DeepSeek
./examples/cc.mp.sh dp

# Launch Kimi
./examples/cc.mp.sh kimi

# Launch GAC Code  
./examples/cc.mp.sh gc
```

### Supported Platforms & Aliases

| Platform | Full Name | Aliases | API Base |
|----------|-----------|---------|-----------|
| **gaccode** | GAC Code | `gc` | `https://gaccode.com/api` |
| **kimi** | Kimi (月之暗面) | - | `https://api.moonshot.cn/v1` |
| **deepseek** | DeepSeek | `dp`, `ds` | `https://api.deepseek.com` |
| **siliconflow** | SiliconFlow | `sf` | `https://api.siliconflow.cn/v1` |
| **local_proxy** | Local Proxy | `lp`, `local` | `http://localhost:7601` |

### Configuration Management

All platform configurations are managed through `examples/launcher-config.json`:

```json
{
  "platforms": {
    "gaccode": {
      "name": "GAC Code",
      "api_base_url": "https://relay05.gaccode.com/claudecode",
      "api_key": "sk-ant-1234-...",
      "login_token": "eyJhbGciOiJIUzI1NiIs...",
      "model": "",
      "small_model": "",
      "enabled": true
    },
    "deepseek": {
      "name": "DeepSeek",
      "api_base_url": "https://api.deepseek.com/anthropic",
      "api_key": "sk-1234...",
      "model": "deepseek-chat",
      "small_model": "deepseek-chat",
      "enabled": true
    }
  },
  "aliases": {
    "gc": "gaccode",
    "dp": "deepseek",
    "ds": "deepseek"
  },
  "settings": {
    "default_platform": "gaccode",
    "plugin_path": "C:\\Users\\dray\\.claude\\scripts\\gaccode.com"
  }
}
```

### How It Works

1. **Configuration**: Launcher scripts read from `examples/launcher-config.json`
2. **Platform Selection**: Resolve aliases (e.g., `dp` → `deepseek`)
3. **Environment Setup**: Set appropriate API keys and endpoints
4. **Session Mapping**: Register UUID with complete platform configuration
5. **Plugin Sync**: Automatically sync configuration to plugin directory
6. **Claude Launch**: Start Claude Code with custom session ID

The statusline plugin then uses the session UUID to lookup platform configuration and display appropriate balance information.

## 📋 Platform Management Commands

### API Key Management
```bash
# Set API keys (supports aliases)
python platform_manager.py set-key dp "sk-deepseek-key"
python platform_manager.py set-key kimi "sk-kimi-key"
python platform_manager.py set-key gc "gac-api-key"

# View API key status
python platform_manager.py get-key deepseek
python platform_manager.py get-key dp

# List all platforms
python platform_manager.py list
```

### Configuration Management
```bash
# Show current statusline configuration
python config-statusline.py --show

# Interactive configuration wizard
python config-statusline.py --interactive

# Set specific options
python config-statusline.py --set show_git_branch true
python config-statusline.py --set layout multi_line
```

## ⚙️ Configuration Options

### Statusline Display Options

| Option | Description | Default |
|--------|-------------|---------|
| `show_model` | Display AI model name | `true` |
| `show_time` | Display current time | `true` |
| `show_session_cost` | Display session cost | `true` |
| `show_directory` | Display current directory | `true` |
| `show_git_branch` | Display Git branch status | `true` |
| `show_balance` | Display account balance | `true` |
| `show_subscription` | Display subscription info | `true` |
| `show_today_usage` | Display today's usage cost | `true` |
| `layout` | `single_line` or `multi_line` | `single_line` |

### Platform-Specific Display

Each platform has its own display format:

- **GAC Code**: USD currency, credit-based balance
- **DeepSeek**: RMB currency, balance_infos array structure  
- **Kimi**: RMB currency, Moonshot API format
- **SiliconFlow**: USD currency, standard balance format
- **Local Proxy**: Configurable, typically mirrors target platform

## 🎨 Color Coding System

### Balance Status Colors
- 🟢 **Green**: Healthy balance (sufficient funds)
- 🟡 **Yellow**: Warning level (moderate funds)  
- 🔴 **Red**: Critical level (low funds)

### Today's Usage (Gaming Equipment Rarity)
- 🔴 **Red** ($300+) - Exotic
- 🟠 **Orange** ($200-$299) - Legendary  
- 🟣 **Purple** ($100-$199) - Artifact
- 🟪 **Magenta** ($50-$99) - Epic
- 🔵 **Blue** ($20-$49) - Rare
- 🔷 **Light Blue** ($10-$19) - Exceptional
- 🟢 **Green** ($5-$9) - Fine
- 🟩 **Light Green** ($2-$4) - Uncommon
- ⚪ **White** ($0.5-$1.9) - Common
- ⚫ **Grey** (<$0.5) - Poor

## 🕒 Time-based Multipliers

The statusline supports configurable time-based multipliers for different platforms:

```json
{
  "multiplier_config": {
    "enabled": true,
    "periods": [
      {
        "name": "peak_hour",
        "start_time": "16:30",
        "end_time": "18:30",
        "multiplier": 5,
        "display_text": "5X",
        "weekdays_only": true,
        "color": "red"
      },
      {
        "name": "off_peak",
        "start_time": "01:00", 
        "end_time": "10:00",
        "multiplier": 0.8,
        "display_text": "0.8X",
        "weekdays_only": false,
        "color": "green"
      }
    ]
  }
}
```

## 📈 Usage Tracking

Integrates with `npx ccusage` for comprehensive usage tracking:

- **Automatic Updates**: Background fetching with timeout protection
- **Lock Mechanism**: Prevents concurrent updates
- **Color Coding**: Gaming equipment rarity system
- **Smart Caching**: Reduces API calls

Enable in configuration:
```json
{
  "show_today_usage": true
}
```

## 🔧 Advanced Features

### Session UUID Mapping

The system uses UUID-based session mapping for 100% accurate platform detection:

1. Launcher generates UUID and registers complete platform configuration
2. Configuration includes: platform, api_key, api_base_url, model, small_model
3. Statusline looks up session UUID to determine active platform
4. Displays platform-appropriate balance and subscription information

### Configuration Synchronization

- **Source**: `examples/launcher-config.json` (user-editable)
- **Target**: `scripts/gaccode.com/platform-config.json` (plugin reads)
- **Sync**: Automatic during launcher execution
- **Mapping**: `examples/session-mappings.json` ↔ `scripts/gaccode.com/session-mappings.json`

### Multi-tier Caching

- **UI Refresh**: 1 second (real-time updates)
- **Balance Cache**: 5 minutes (API rate limiting)
- **History Cache**: 5 minutes (multiplier detection)
- **Subscription Cache**: 1 hour (infrequent changes)
- **Session Cache**: Persistent until restart

## 🛠️ File Structure

```
gaccode-statusline/
├── statusline.py              # Main statusline script
├── platform_manager.py       # Unified platform configuration manager
├── config-statusline.py      # Display configuration tool
├── platforms/                 # Platform-specific implementations
│   ├── manager.py            # Platform detection manager
│   ├── base.py              # Base platform interface
│   ├── gaccode.py           # GAC Code implementation
│   ├── kimi.py              # Kimi implementation
│   ├── deepseek.py          # DeepSeek implementation
│   └── siliconflow.py       # SiliconFlow implementation
├── examples/                  # Launcher scripts and configuration
│   ├── cc.mp.ps1            # Windows PowerShell launcher
│   ├── cc.mp.sh             # Linux/Mac bash launcher
│   ├── launcher-config.json # Platform configuration
│   └── session-mappings.json # Session UUID mappings
├── README.md                 # This file
└── LICENSE                  # MIT License
```

## 🧪 Testing

### Test Individual Components
```bash
# Test statusline directly
echo '{}' | python statusline.py

# Test platform detection
python -c "from platforms.manager import PlatformManager; print(PlatformManager().list_supported_platforms())"

# Test launcher configuration
python examples/cc.mp.ps1 --help  # Windows
./examples/cc.mp.sh --help        # Linux/Mac
```

### Debug Session Mapping
```bash
# Check session mappings
cat examples/session-mappings.json
cat session-mappings.json

# Test platform configuration sync
python platform_manager.py list
```

## 🔧 Troubleshooting

### Common Issues

**Statusline not showing platform data:**
1. Verify API key is set: `python platform_manager.py list`
2. Check session mapping: Look for your session UUID in `session-mappings.json`
3. Ensure launcher was used to start Claude Code
4. Test API connectivity: `python statusline.py`

**Platform detection failures:**
1. Verify you used the launcher script (`cc.mp.ps1` or `cc.mp.sh`)
2. Check if session UUID exists in mapping file
3. Ensure configuration was synced to plugin directory
4. Restart Claude Code if configuration was updated

**API call failures:**
1. Verify API key is correct and active
2. Check network connectivity
3. Ensure API endpoint is accessible
4. Review platform-specific API documentation

**Display encoding issues:**
1. Ensure terminal supports UTF-8
2. On Windows: `chcp 65001`
3. Check Python locale settings

### Debug Mode

Enable debug output in `statusline.py`:
```python
DEBUG = True  # Set at top of file
```

This will show detailed platform detection and API call information.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [GAC Code](https://gaccode.com/) for the API service
- [Claude Code](https://claude.ai/code) for the development environment
- [DeepSeek](https://www.deepseek.com/) for their API
- [Kimi (月之暗面)](https://kimi.moonshot.cn/) for their Moonshot API
- [SiliconFlow](https://siliconflow.cn/) for their API service
- [ccusage](https://github.com/ryoppippi/ccusage) by ryoppippi for usage tracking
- All contributors and users who help improve this tool

## 🤝 Support

If you find this project helpful, please consider:

- ⭐ Starring the repository
- 🐛 Reporting issues
- 💡 Suggesting new features  
- 🔧 Contributing code improvements
- 📝 Improving documentation

## 🔮 Roadmap

- [ ] Web dashboard for configuration management
- [ ] Additional platform integrations (OpenAI, Azure, etc.)
- [ ] Usage analytics and reporting
- [ ] Custom alerting and notifications
- [ ] Plugin marketplace distribution

---

**Disclaimer**: This is an unofficial tool for multi-platform API integration. Not affiliated with Anthropic, GAC Code, DeepSeek, Moonshot AI, or SiliconFlow.