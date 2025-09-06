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

- **Python 3.7+** (Required - now used for unified launcher system)
- Claude Code installed
- API access for at least one supported platform
- Node.js and npm (for usage tracking feature)

### Installation

1. Clone this repository:
```bash
git clone https://github.com/DrayChou/gaccode-statusline.git
cd gaccode-statusline
```

2. **🔒 Secure API Key Configuration**:

**Method 1 - Configuration File (Recommended)**:
```bash
# Edit the configuration file directly for secure key storage
# File: examples/launcher-config.json
# Manually add your API keys to the platforms section

# Verify platform status after configuration
python platform_manager.py list
```

**Security Note**: Always edit configuration files directly rather than using command-line API key input to avoid exposing keys in shell history.

**Method 2 - Environment Variables (Advanced)**:
```bash
# Set environment variables for secure key storage
export DEEPSEEK_API_KEY="sk-your-deepseek-key-here"
export KIMI_API_KEY="sk-your-kimi-key-here"
export GAC_API_KEY="your-gac-login-token"

# Keys will be automatically detected from environment variables
python platform_manager.py list
```

**⚠️ Security Notice**: Never commit real API keys to version control. The `.gitignore` file excludes sensitive configuration files, but always verify before committing.

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

## 🎯 Unified Multi-Platform Launcher

### Architecture Overview

**NEW**: Unified Python launcher system replaces the old dual PowerShell/Bash scripts
- **Single Implementation**: `launcher.py` contains all launching logic (~300 lines)
- **Lightweight Wrappers**: Platform-specific scripts are now simple wrappers (30-40 lines each)
- **90% Maintenance Reduction**: From 2×400+ line scripts to unified codebase
- **Consistent Behavior**: Identical functionality across all platforms and operating systems
- **Proper UUID Generation**: Platform-prefixed UUIDs (e.g., `gac00000-xxxx-xxxx-xxxx-xxxxxxxxxxxx`)
- **Enhanced Session Management**: Integrated with SessionManager for `--continue` support

### Quick Launch Scripts

Use any of the convenient launcher interfaces:

**Direct Python Launcher (Cross-platform):**
```bash
# Direct usage with all features
python examples/launcher.py dp --continue
python examples/launcher.py kimi --continue
python examples/launcher.py gc --continue

# Dry-run mode for testing configuration
python examples/launcher.py dp --dry-run
```

**Wrapper Scripts (Platform-specific convenience):**
```powershell
# Windows PowerShell
.\examples\cc.mp.ps1 dp --continue
.\examples\cc.mp.ps1 kimi --continue
.\examples\cc.mp.ps1 gc --continue
```

```bash
# Linux/Mac Bash
./examples/cc.mp.sh dp --continue
./examples/cc.mp.sh kimi --continue
./examples/cc.mp.sh gc --continue
```

```cmd
# Windows Command Prompt
examples\cc.mp.bat dp --continue
examples\cc.mp.bat kimi --continue
examples\cc.mp.bat gc --continue
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

### How the Unified Launcher Works

1. **Wrapper Execution**: Any wrapper script (`cc.mp.ps1`, `cc.mp.sh`, `cc.mp.bat`) calls the unified Python launcher
2. **Python Processing**: `launcher.py` handles all logic:
   - Configuration loading from `examples/launcher-config.json`
   - Platform alias resolution (e.g., `dp` → `deepseek`)
   - Platform-prefixed UUID generation (e.g., `gac00000-...`, `deepseek-...`)
   - Environment variable setup for API keys and endpoints
   - Session mapping registration with complete platform configuration
   - Configuration synchronization to plugin directory
   - Claude Code process launch with custom session ID
3. **Session Management**: Integrated `--continue` support for resuming previous sessions
4. **Cross-platform**: Identical behavior on Windows, Linux, and macOS

The statusline plugin uses the session UUID to lookup platform configuration and display appropriate balance information.

**Benefits of Unified Architecture:**
- **Maintainability**: Single codebase eliminates duplicate logic
- **Reliability**: Consistent UUID format and session handling
- **Feature Parity**: All platforms get identical functionality
- **Easier Testing**: One implementation to test and debug

## 📋 Platform Management Commands

### API Key Management
```bash
# Check current API key status (secure - no key exposure)
python platform_manager.py get-key deepseek
python platform_manager.py get-key kimi
python platform_manager.py get-key gaccode

# Security Note: Configure API keys by editing examples/launcher-config.json directly
# Never use command-line methods that expose keys in shell history

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

The system uses an optimized UUID-based session mapping for 100% accurate platform detection:

**UUID Format Enhancement**:
- **Old Format**: `00000001-xxxx-xxxx-xxxx-xxxxxxxxxxxx` (8-digit platform prefix)
- **New Format**: `01xxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` (2-digit hex prefix + 6 random digits)
- **Benefits**: Space-efficient while maintaining UUID compliance

**Platform ID Mapping**:
- `01`: GAC Code
- `02`: DeepSeek  
- `03`: Kimi
- `04`: SiliconFlow
- `05`: Local Proxy

**Detection Flow**:
1. **Priority 0 - Session Mappings**: Query `session-mappings.json` for UUID→platform mapping (handles standard UUIDs)
2. **Priority 1 - Prefix Detection**: Extract 2-digit hex prefix for instant platform identification (O(1) complexity)
3. **Priority 2 - Configuration**: Use explicit platform_type from config
4. **Priority 3 - Token Format**: Traditional token analysis (fallback)
5. **Priority 4 - Default**: Fall back to GAC Code platform

**Mapping Process**:
1. Launcher generates platform-prefixed UUID
2. Registers complete configuration in `data/cache/session-mappings.json`
3. Configuration includes: platform, api_key, api_base_url, model, small_model
4. Statusline performs optimized lookup using session UUID
5. Displays platform-appropriate balance and subscription information

### Configuration Synchronization

- **Source**: `examples/launcher-config.json` (user-editable)
- **Target**: `scripts/gaccode.com/launcher-config.json` (plugin reads)
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
├── examples/                  # Unified launcher system
│   ├── launcher.py          # ⭐ NEW: Unified Python launcher (main implementation)
│   ├── cc.mp.ps1            # ✅ UPDATED: Lightweight PowerShell wrapper (~30 lines)
│   ├── cc.mp.sh             # ✅ UPDATED: Lightweight Bash wrapper (~30 lines)
│   ├── cc.mp.bat            # ⭐ NEW: Windows batch wrapper
│   ├── launcher-config.json # Platform configuration
│   └── session-mappings.json # Session UUID mappings
├── data/                      # Runtime data and caching
│   ├── session_manager.py   # ⭐ NEW: Session state management
│   ├── config/              # Configuration files
│   ├── cache/               # Runtime cache files
│   └── logs/                # Structured logging output
├── README.md                 # This documentation
└── LICENSE                  # MIT License
```

### Key Architecture Changes

**Old System** (Maintenance Heavy):
- `cc.mp.ps1`: 400+ lines of PowerShell logic
- `cc.mp.sh`: 400+ lines of Bash logic  
- Duplicated functionality, platform-specific bugs

**New System** (Unified & Maintainable):
- `launcher.py`: ~300 lines of unified Python logic
- `cc.mp.ps1`: ~30 lines PowerShell wrapper
- `cc.mp.sh`: ~30 lines Bash wrapper
- `cc.mp.bat`: ~30 lines batch wrapper
- Single source of truth, consistent behavior

## 🧪 Testing

### Test Individual Components
```bash
# Test statusline directly
echo '{}' | python statusline.py

# Test platform detection
python -c "from platforms.manager import PlatformManager; print(PlatformManager().list_supported_platforms())"

# Test unified launcher
python examples/launcher.py --help
python examples/launcher.py dp --dry-run

# Test wrapper scripts
.\examples\cc.mp.ps1 --help      # Windows PowerShell
./examples/cc.mp.sh --help       # Linux/Mac Bash
examples\cc.mp.bat --help        # Windows CMD
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
1. Verify you used a launcher script (`cc.mp.ps1`, `cc.mp.sh`, `cc.mp.bat`, or direct `launcher.py`)
2. Check if session UUID exists in mapping file: `cat data/cache/session-mappings.json`
3. Ensure configuration was synced to plugin directory
4. Verify Python 3.7+ is available (required for unified launcher)
5. Test direct launcher: `python examples/launcher.py dp --dry-run`
6. Check for UTF-8 BOM encoding issues in JSON files
7. Restart Claude Code if configuration was updated

**Session mapping debugging:**
```bash
# Check session mapping file encoding
python -c "with open('data/cache/session-mappings.json', 'rb') as f: print('BOM detected:' if f.read(3) == b'\xef\xbb\xbf' else 'No BOM')"

# Test UUID prefix detection
python -c "from data.session_manager import detect_platform_from_session_id; print(detect_platform_from_session_id('01abcdef-1234-5678-9012-123456789abc'))"

# List all session states
python data/session_manager.py test
```

**API call failures:**
1. Verify API key is correct and active
2. Check network connectivity
3. Ensure API endpoint is accessible
4. Review platform-specific API documentation
5. Check for authentication method mismatch (api_key vs auth_token)
6. Validate API key format and permissions

**Configuration security issues:**
1. Verify API keys are not logged or exposed in debug output
2. Check file permissions on configuration files (should be user-readable only)
3. Ensure sensitive data is masked in logs
4. Review `.gitignore` coverage for new sensitive files

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

**Security-aware debugging:**
- Sensitive information (API keys, tokens) is automatically masked in debug output
- Use `--dry-run` mode for testing without actual API calls
- Check `data/logs/` for structured logging with security filtering

```bash
# View security-filtered logs
tail -f data/logs/platform-manager.log
tail -f data/logs/statusline.log

# Test configuration without API calls
python examples/launcher.py dp --dry-run --debug
```

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

### Recently Completed ✅
- [x] **Unified Launcher Architecture** - Single Python implementation with lightweight wrappers
- [x] **Platform-prefixed UUIDs** - Proper UUID generation with platform identification
- [x] **Session Management Integration** - Enhanced `--continue` support
- [x] **Cross-platform Compatibility** - Consistent behavior on Windows, Linux, macOS
- [x] **90% Maintenance Reduction** - Eliminated duplicate logic across launcher scripts

### Upcoming Features 🚧
- [ ] Web dashboard for configuration management
- [ ] Additional platform integrations (OpenAI, Azure, etc.)
- [ ] Usage analytics and reporting
- [ ] Custom alerting and notifications
- [ ] Plugin marketplace distribution
- [ ] Launcher GUI for non-technical users

---

**Disclaimer**: This is an unofficial tool for multi-platform API integration. Not affiliated with Anthropic, GAC Code, DeepSeek, Moonshot AI, or SiliconFlow.