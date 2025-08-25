# GAC Code Status Line

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.7+-blue.svg)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)

A beautiful statusline for Claude Code that displays GAC API balance and subscription information in real-time.

## ✨ Features

- 🔄 **Real-time Updates**: Displays current balance and subscription status
- 🎨 **Color-coded Status**: Visual indicators for balance and expiry warnings
- ⚡ **Smart Caching**: 45-second cache to minimize API calls
- 🔒 **Secure Token Management**: Local token storage with management tools
- 🖥️ **Cross-platform**: Works on Windows, macOS, and Linux
- 🎯 **Claude Code Integration**: Seamless integration with Claude Code statusline

## 📸 Screenshot

```
Balance:2692/12000 Expires:09-13(19d)
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
    "refreshInterval": 60000
  }
}
```

4. Restart Claude Code to see your statusline!

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

### Testing
```bash
# Test the statusline directly
python statusline.py

# Test with mock data
echo '{"model":{"id":"gaccode-test"}}' | python statusline.py
```

## 🎨 Display Format

The statusline shows information in this format:
- `Balance:2692/12000` - Current balance / Credit cap
- `Expires:09-13(19d)` - Subscription end date (days remaining)

### Color Coding
- 🟢 **Green**: Sufficient balance (>1000) / Time remaining (>14 days)
- 🟡 **Yellow**: Warning level (500-1000) / (7-14 days)
- 🔴 **Red**: Critical level (<500) / (<7 days)

## ⚙️ Configuration

### Adjusting Cache Duration
Edit `statusline.py` and modify:
```python
CACHE_TIMEOUT = 45  # seconds
```

### Custom Refresh Interval
Modify `refreshInterval` in your Claude Code settings (milliseconds):
```json
"refreshInterval": 60000  # 60 seconds
```

## 🛠️ Development

### File Structure
```
gaccode-statusline/
├── statusline.py           # Main statusline script
├── set-gac-token.py       # Token management utility
├── README.md              # This file
├── SETUP_GUIDE.md         # Detailed setup guide
├── LICENSE                # MIT License
└── .gitignore            # Git ignore rules
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