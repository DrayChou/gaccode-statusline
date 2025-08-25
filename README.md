# GAC Code Status Line

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.7+-blue.svg)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)

A comprehensive and configurable statusline for Claude Code that displays GAC API balance, subscription information, and development context in real-time.

## ✨ Features

- 🔄 **Real-time Updates**: Displays current balance and subscription status
- 🎨 **Color-coded Status**: Visual indicators for balance and expiry warnings
- ⚡ **Multi-tier Caching**: 1-second UI refresh, 1-minute balance cache, 1-hour subscription cache
- 🔒 **Secure Token Management**: Local token storage with management tools
- 🖥️ **Cross-platform**: Works on Windows, macOS, and Linux
- 🎯 **Claude Code Integration**: Seamless integration with Claude Code statusline
- ⚙️ **Fully Configurable**: Customizable display components and layout
- 📊 **Rich Context**: Shows model, time, session cost, directory, Git branch
- 🌐 **Smart Layout**: Single-line or multi-line display options

## 📸 Screenshots

**Full Display (Single Line):**
```
Model:Claude-3.5-Sonnet Time:13:24:15 Cost:$3.75 Balance:2692/12000 Expires:09-13(19d) Dir:myproject Git:main*
```

**Multi-line Layout:**
```
Model:Claude-3.5-Sonnet Time:13:24:15 Cost:$3.75 Balance:2692/12000 Expires:09-13(19d)
Dir:/full/path/to/myproject Git:main*
```

**Color-coded Examples:**
| Status | Balance Display | Expires Display |
|--------|------------------|-----------------|
| 🟢 Healthy | `Balance:`<span style="color:green">**3500**</span>`/12000` | `Expires:`<span style="color:green">**09-25(30d)**</span> |
| 🟡 Warning | `Balance:`<span style="color:orange">**750**</span>`/12000` | `Expires:`<span style="color:orange">**09-18(10d)**</span> |
| 🔴 Critical | `Balance:`<span style="color:red">**350**</span>`/12000` | `Expires:`<span style="color:red">**09-15(3d)**</span> |

**Development Context Examples:**
```
# Clean repository
Dir:myproject Git:main

# Uncommitted changes  
Dir:myproject Git:main*

# Feature branch with changes
Dir:frontend-app Git:feature/login*

# Full path mode
Dir:/Users/developer/projects/myproject Git:main
```

**Session Cost Indicators:**
- `Cost:$3.75` - Real session cost with GAC API data
- `Cost:T2.45` - Mock cost when session data unavailable

**Minimal Configuration:**
```
Model:Claude-3.5-Sonnet Time:13:24:15 Balance:2692/12000
```

## 🚀 Quick Start

### Prerequisites

- Python 3.7+
- Claude Code installed
- GAC Code API access

### Installation

1. Clone this repository:
```bash
git clone https://github.com/DrayChou/gaccode-statusline.git
cd gaccode-statusline
```

2. Set your API token:
```bash
python set-gac-token.py set "your-gac-api-token"
```

3. Configure Claude Code by adding to your `.claude/settings.json`:
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

4. (Optional) Customize your display:
```bash
python config-statusline.py --interactive
```

5. Restart Claude Code to see your statusline!

## 📋 Commands

### Token Management
```bash
# Set a new token
python set-gac-token.py set "your-token-here"

# View current token status
python set-gac-token.py show

# Remove token
python set-gac-token.py remove
```

### Configuration Management
```bash
# Show current configuration
python config-statusline.py --show

# Interactive configuration wizard
python config-statusline.py --interactive

# Set specific options
python config-statusline.py --set show_git_branch true
python config-statusline.py --set layout multi_line
python config-statusline.py --set directory_full_path false

# Reset to defaults
python config-statusline.py --reset
```

## ⚙️ Configuration Options

The statusline is fully customizable through the configuration system:

| Option | Description | Default |
|--------|-------------|---------|
| `show_model` | Display AI model name | `true` |
| `show_time` | Display current time | `true` |
| `show_session_cost` | Display session cost | `true` |
| `show_directory` | Display current directory | `true` |
| `show_git_branch` | Display Git branch status | `true` |
| `show_balance` | Display account balance | `true` |
| `show_subscription` | Display subscription info | `true` |
| `show_session_duration` | Display session duration | `false` |
| `directory_full_path` | Show full path vs directory name | `true` |
| `layout` | `single_line` or `multi_line` | `single_line` |

## 🎨 Display Information

The statusline can display the following information:

**Core Information:**
- **Model**: AI model name (e.g., Claude-3.5-Sonnet)
- **Time**: Current time in HH:MM:SS format
- **Cost**: Session cost (real: $3.75, mock: T2.45)

**GAC API Data:**
- **Balance**: Current credits / Credit cap (e.g., 2692/12000)
- **Expires**: Subscription end date with days remaining (e.g., 09-13(19d))

**Development Context:**
- **Dir**: Current directory (full path or name only)
- **Git**: Current Git branch with dirty indicator (*) if uncommitted changes

### Color Coding
- 🟢 **Green**: Sufficient balance (>1000) / Time remaining (>14 days)
- 🟡 **Yellow**: Warning level (500-1000) / (7-14 days)
- 🔴 **Red**: Critical level (<500) / (<7 days)

## 🔧 Advanced Configuration

### Multi-tier Caching System
The statusline uses intelligent caching:
- **UI Refresh**: 1 second (real-time updates)
- **Balance Cache**: 1 minute (API rate limiting)
- **Subscription Cache**: 1 hour (infrequent changes)

Modify in `statusline.py`:
```python
BALANCE_CACHE_TIMEOUT = 60      # Balance cache in seconds
SUBSCRIPTION_CACHE_TIMEOUT = 3600  # Subscription cache in seconds
```

## 🛠️ Development

### File Structure
```
gaccode-statusline/
├── statusline.py           # Main statusline script
├── config-statusline.py   # Configuration management tool
├── set-gac-token.py       # Token management utility
├── README.md              # This file
├── SETUP_GUIDE.md         # Detailed setup guide
├── LICENSE                # MIT License
└── .gitignore            # Git ignore rules (protects sensitive files)
```

### Testing
```bash
# Test the statusline directly
echo '{}' | python statusline.py

# Test configuration system
python config-statusline.py --show

# Test with different layouts
python config-statusline.py --set layout multi_line
echo '{}' | python statusline.py
```

### Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes and test thoroughly
4. Commit: `git commit -am 'Add some feature'`
5. Push: `git push origin feature-name`
6. Create a Pull Request

## 🔧 Troubleshooting

### Statusline not showing?
1. Verify you're using a GAC Code model
2. Check token configuration: `python set-gac-token.py show`
3. Test API connectivity: `python statusline.py`
4. Restart Claude Code

### API call failures?
- Ensure your token is valid and not expired
- Check network connectivity
- Verify GAC Code API service status

### Display encoding issues?
- Ensure your terminal supports UTF-8 encoding
- On Windows, try running: `chcp 65001`

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [GAC Code](https://gaccode.com/) for providing the API
- [Claude Code](https://claude.ai/code) for the amazing development environment
- All contributors who help improve this tool

## 🤝 Support

If you find this project helpful, please consider:
- ⭐ Starring the repository
- 🐛 Reporting issues
- 💡 Suggesting new features
- 🔧 Contributing code improvements

---

**Disclaimer**: This is an unofficial tool for GAC Code API integration. Not affiliated with Anthropic or GAC Code.