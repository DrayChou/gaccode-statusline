# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 🚫 CRITICAL ARCHITECTURE RULE: PURE CONFIG-FILE-ONLY

**ABSOLUTE REQUIREMENT**: This project uses **PURE CONFIG-FILE-ONLY** architecture.

### Strict Rules:
- ❌ **NO environment variables** - All configuration must be in config files
- ❌ **NO command-line interfaces** - Users edit config files only  
- ❌ **NO runtime parameter passing** - Everything configured via files
- ❌ **NO fallback to environment variables** - Config file is the single source of truth
- ✅ **ONLY config file** - `data/config/config.json` is the sole configuration method

### Technical Exception: Multi-Platform Launcher
**IMPORTANT**: The `bin/launcher.py` contains a necessary technical exception:
- **WHY**: Claude Code requires environment variables (`ANTHROPIC_API_KEY`, `ANTHROPIC_BASE_URL`) to function
- **SCOPE**: Limited to launcher process only - does not affect core library modules
- **USER IMPACT**: Users still configure via config files only
- **ISOLATION**: Environment variables are set internally by launcher, not exposed to users

### Code Requirements:
- Remove ALL `os.environ.get()` calls from core modules (data/, platforms/, etc.)
- Remove ALL `export`/`$env:` references from user documentation
- Remove ALL argparse and CLI interfaces from core modules
- Remove ALL environment variable fallback logic from libraries
- Users configure EVERYTHING by editing `data/config/config.json`
- **EXCEPTION**: `bin/launcher.py` may set environment variables internally for Claude Code compatibility

## 🔒 CRITICAL SECURITY RULES: PRIVACY & API PROTECTION

### Privacy Protection Rule
**MANDATORY**: All code must be safe for public release with zero privacy leaks.

#### Privacy Requirements:
- ❌ **NO hardcoded credentials** - No real API keys, tokens, emails in any code/docs
- ❌ **NO sensitive data examples** - Use placeholder formats only (`sk-ant-xxx...`, `eyJhbG...`)
- ✅ **Complete data masking** - All logs must automatically filter sensitive information
- ✅ **Gitignore protection** - All config files, caches, logs excluded from version control
- ✅ **Documentation safety** - Only show sanitized examples with masked data

#### Implementation Requirements:
```python
# ❌ NEVER do this
api_key = "sk-ant-real-key-here"  # PRIVACY VIOLATION

# ✅ Always do this
api_key = config.get("api_key")   # Read from user config
log_message("API key", f"sk-ant-***{api_key[-4:]}")  # Auto-masked logging
```

### API Rate Limiting Rule  
**MANDATORY**: All external API calls must respect provider limits to prevent account suspension.

#### Rate Limiting Requirements:
- ⚠️ **GAC Code APIs**: Minimum 60 seconds between calls (prevent account ban)
- ⚠️ **Other APIs**: Follow documented rate limits or use conservative defaults
- ✅ **Intelligent fallback** - Use cached data when rate limited
- ✅ **User transparency** - Rate limiting should be invisible to users

#### Implementation Pattern:
```python
def api_call(self):
    # Check rate limit
    if (time.time() - self._last_request) < self._min_interval:
        return self._use_cached_data()  # Fallback to cache
    
    # Safe to make API call
    return self._make_api_request()
```

#### Critical Platform Limits:
- **GAC Code**: 60+ seconds interval (risk: account ban)
- **OpenAI**: 60 requests/minute (risk: temporary throttling)
- **Anthropic**: Follow tier limits (risk: rate limit errors)

## Project Overview

GAC Code Multi-Platform Status Line - A comprehensive Claude Code statusline plugin that supports multiple AI API platforms (GAC Code, Kimi, DeepSeek, SiliconFlow, Local Proxy) with real-time balance display, session mapping, and intelligent platform detection.

**Configuration Method**: Users edit `data/config/config.json` file ONLY.

## Core Architecture

### Multi-Platform System Design

The project implements a sophisticated multi-platform architecture with three key components:

#### 1. Platform Detection & Session Mapping
- **Optimized UUID-based Session Mapping**: Uses 2-digit hex prefix UUIDs (e.g., `01xxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`) for efficient platform identification
- **Session Flow**: Launcher scripts → Platform configuration → Session registration → Platform-specific API calls
- **Detection Priority**: 
  - **Priority 0**: Session Mappings query (`session-mappings.json` lookup for standard UUIDs)
  - **Priority 1**: UUID prefix detection (O(1) complexity, instant platform identification)
  - **Priority 2**: Explicit config (`platform_type`)
  - **Priority 3**: Token format analysis (traditional fallback)
  - **Priority 4**: Default GAC Code platform
- **Platform ID Mapping**: `01`=GAC Code, `02`=DeepSeek, `03`=Kimi, `04`=SiliconFlow, `05`=Local Proxy

#### 2. Platform Abstraction Layer  
Located in `platforms/`:
- **Base Interface** (`base.py`): Abstract base class defining platform contract
- **Platform Implementations**: Individual files for each API provider (`gaccode.py`, `kimi.py`, `deepseek.py`, `siliconflow.py`)
- **Platform Manager** (`manager.py`): Orchestrates platform detection and selection

#### 3. Unified Configuration & Caching System
```
data/
├── config/           # Configuration files
│   ├── platform-config.json     # Platform settings and API keys
│   └── statusline-config.json   # Display configuration
├── cache/            # Runtime cache files
│   ├── session-mappings.json    # UUID-to-platform mappings (AUTHORITATIVE)
│   ├── session-info-cache.json  # SHARED FILE - written by ALL Claude instances
│   └── balance-cache-*.json     # Platform-specific API cache (5min TTL)
└── logs/             # Structured logging output
    ├── platform-manager.log     # Platform detection logs
    ├── statusline.log           # Status display logs
    └── update_usage.log         # Usage tracking logs
```

**CRITICAL**: `session-info-cache.json` is updated by every running Claude Code instance and should NEVER be used for platform detection. Always use the session_id from stdin and query `session-mappings.json` for platform identification.

**SECURITY NOTICE**: All configuration files containing API keys and sensitive data are excluded from version control via `.gitignore`. Always verify sensitive information is properly masked in logs and debug output.

## Key Development Commands

### Platform Management

**Secure API Key Configuration**:
```bash
# Configuration File Method (ONLY supported method)
# Edit data/config/config.json to add API keys
# This is the only way to configure the system - no environment variables

# View platform status (keys are masked for security)
python platform_manager.py list

# Get specific platform key (masked output)
python platform_manager.py get-key deepseek

# Security Note: Never use command-line methods that expose keys in shell history
```

### Statusline Configuration
```bash
# Interactive configuration wizard
python config-statusline.py --interactive

# View current configuration
python config-statusline.py --show

# Set specific display options
python config-statusline.py --set show_git_branch true
python config-statusline.py --set layout multi_line
```

### Platform Launcher Usage
```powershell
# Windows PowerShell - Launch different platforms
.\bin\cc.mp.ps1 dp           # DeepSeek
.\bin\cc.mp.ps1 kimi         # Kimi
.\bin\cc.mp.ps1 sf           # SiliconFlow
.\bin\cc.mp.ps1 gc           # GAC Code
```

```bash
# Linux/Mac - Launch different platforms  
./bin/cc.mp.sh dp            # DeepSeek
./bin/cc.mp.sh kimi          # Kimi
./bin/cc.mp.sh sf            # SiliconFlow
```

### Testing & Debugging
```bash
# Test statusline directly (manual input)
echo '{"session_id":"test-uuid","model":{"display_name":"Test"}}' | python statusline.py

# Test optimized platform detection with 2-digit hex prefix
echo '{"session_id":"02abcdef-1234-5678-9012-123456789abc"}' | python statusline.py

# Test platform detection fallback
python -c "from platforms.manager import PlatformManager; print(PlatformManager().list_supported_platforms())"

# Test UUID prefix detection
python -c "from data.session_manager import detect_platform_from_session_id; print(detect_platform_from_session_id('02abcdef-1234-5678-9012-123456789abc'))"

# Debug session mappings (check for UTF-8 BOM issues)
cat data/cache/session-mappings.json
python -c "import json; print(json.load(open('data/cache/session-mappings.json', 'r', encoding='utf-8-sig')))"

# View live logs (sensitive data automatically masked)
tail -f data/logs/platform-manager.log
tail -f data/logs/statusline.log

# Test launcher in dry-run mode (no API calls)
python bin/launcher.py dp --dry-run
```

## Critical Architecture Concepts

### Configuration File Synchronization Architecture

**Two-Tier Configuration System**:
- **Source Configurations**: Various `launcher-config.json` files (user-editable templates)
- **Runtime Configuration**: Single `data/config/platform-config.json` (system-managed)

**Configuration Search Priority** (Launcher only):
1. **Current working directory**: `launcher-config.json`
2. **Caller script directory**: Via `LAUNCHER_SCRIPT_DIR` env var
3. **Launcher.py directory**: `bin/launcher-config.json`
4. **Project data/config**: `data/config/launcher-config.json`
5. **User home directory**: Backup locations

**Synchronization Flow**:
```
User edits: data/config/launcher-config.json
     ↓
Launcher finds config (priority-based search)
     ↓  
Launcher calls sync_configuration()
     ↓
Writes to: data/config/platform-config.json
     ↓
StatusLine reads: data/config/platform-config.json
```

### Session Mapping Flow (Optimized)
1. **Launcher Execution**: `cc.mp.ps1 dp` → Resolves `dp` to `deepseek` platform
2. **Configuration Sync**: Launcher searches for `launcher-config.json`, syncs to `data/config/platform-config.json`
3. **Optimized UUID Generation**: Creates 2-digit hex prefixed UUID (`02xxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` for DeepSeek)
4. **Dual Mapping Registration**: 
   - **Standard UUID**: For backward compatibility with existing sessions
   - **Prefixed UUID**: For instant O(1) platform detection
5. **Session Registration**: Stores UUID→platform mapping in `data/cache/session-mappings.json`
6. **Claude Launch**: Starts Claude Code with platform-prefixed session UUID
7. **Optimized Platform Detection**: 
   - **Fast Path**: Extract 2-digit hex prefix → instant platform identification
   - **Fallback Path**: Session mappings query → config lookup → token analysis
8. **API Calls**: Uses platform-specific API implementation for balance/subscription data

**Critical Note**: `session-info-cache.json` is a shared, actively updated file written by ALL running Claude Code instances. Platform detection must NEVER rely on this file as it contains data from whichever instance wrote to it last, not necessarily the current session.

### Usage Modes

**Mode 1: Full Launcher Mode** (Recommended)
- User runs: `./bin/cc.mp.ps1` or `python bin/launcher.py`
- Configuration: Edit `data/config/launcher-config.json`
- Sync: Automatic → `data/config/platform-config.json`
- Features: Platform-prefixed UUIDs, session management, multi-platform support

**Mode 2: Official Claude + StatusLine Mode** (Minimal)
- User runs: `claude` (official Claude Code)
- Configuration: Edit `data/config/platform-config.json` directly
- StatusLine: Auto-detects platform → fallback to GAC Code if none detected
- Features: Balance display, basic platform support

### Platform Detection Rules

**IMPORTANT**: Platform detection must follow these strict rules:

1. **UUID-based Session Mapping First**: Always check `data/cache/session-mappings.json` for session_id→platform mapping
2. **Configuration-based Detection Second**: Use `data/config/platform-config.json` for token retrieval
3. **Token Format Detection Last**: Only use token format analysis as final fallback

**PROHIBITED**: Never attempt platform detection based on model information:
- ❌ **DON'T** analyze model names like "kimi-k2-0905-preview" to detect platforms
- ❌ **DON'T** use model ID patterns for platform identification
- ❌ **DON'T** assume specific model names belong to specific platforms
- ❌ **DON'T** rely on `session-info-cache.json` for platform detection (shared file, race conditions)
- ❌ **DON'T** expose API keys in logs or debug output (security risk)

**REASON**: All platforms support multiple models. For example:
- SiliconFlow supports models with names unrelated to "siliconflow"
- Kimi supports various model names beyond "kimi-*"
- DeepSeek supports multiple model families
- Model-based detection creates false assumptions and bugs

**CORRECT APPROACH**:
```python
# Platform detection should be based on:
1. Session UUID mapping (primary)
2. Configuration file lookup (secondary) 
3. Token format analysis (fallback only)

# NOT based on:
model_id = session_info.get("model", {}).get("id", "")
if "kimi" in model_id:  # ❌ WRONG - Don't do this
    platform = "kimi"
```

### Authentication Architecture
- **API Key vs Auth Token**: Different platforms use different authentication methods
  - `api_key`: DeepSeek, SiliconFlow (`"api_key": "sk-..."`)
  - `auth_token`: Kimi/Moonshot (`"auth_token": "sk-..."`)
- **Config-Only Authentication**: All authentication managed via `data/config/config.json`
- **Launcher Internal Process**: Launcher reads config and sets environment variables internally for Claude Code compatibility

### Caching Strategy
- **Multi-tier Caching**: UI refresh (1s) → Balance cache (5min) → Subscription cache (1hr)
- **Platform-specific Files**: Each platform maintains separate cache files (`balance-cache-{platform}.json`)
- **Cache Invalidation**: Time-based expiration with graceful degradation on API failures

### Logging System
Located in `data/logger.py` - Provides unified structured logging:
- **Component-based**: Separate log files per component (platform-manager, statusline, etc.)
- **Structured Data**: JSON metadata with each log entry
- **Cross-platform**: PowerShell, Bash, and Python integration
- **Log Levels**: DEBUG, INFO, WARNING, ERROR

## Adding New Platforms

### 1. Create Platform Implementation
Create `platforms/your_platform.py`:
```python
from .base import BasePlatform
from typing import Dict, Any, Optional

class YourPlatform(BasePlatform):
    @property
    def name(self) -> str:
        return "YourPlatform"
    
    @property 
    def api_base(self) -> str:
        return "https://api.yourplatform.com"
        
    def detect_platform(self, session_info: Dict[str, Any], token: str) -> bool:
        # Platform-specific detection logic
        return token.startswith("your-prefix-")
        
    def fetch_balance_data(self) -> Optional[Dict[str, Any]]:
        # API call implementation
        
    def fetch_subscription_data(self) -> Optional[Dict[str, Any]]:
        # API call implementation
        
    def format_balance_display(self, balance_data: Dict[str, Any]) -> str:
        # Format for statusline display
```

### 2. Register Platform
Add to `platforms/manager.py`:
```python
from .your_platform import YourPlatform

class PlatformManager:
    def __init__(self):
        self._platform_classes = [
            GACCodePlatform,
            KimiPlatform, 
            DeepSeekPlatform,
            SiliconFlowPlatform,
            YourPlatform,  # Add here
        ]
```

### 3. Add Configuration
Update `data/config/launcher-config.json`:
```json
{
  "platforms": {
    "yourplatform": {
      "name": "Your Platform",
      "api_base_url": "https://api.yourplatform.com",
      "api_key": "",
      "model": "your-default-model",
      "enabled": false
    }
  },
  "aliases": {
    "yp": "yourplatform"
  }
}
```

## Common Issues & Solutions

### Platform Detection Failures
**Root Cause**: Session not launched via launcher scripts OR UTF-8 BOM in session mappings file
**Solutions**: 
1. Use any launcher interface: `launcher.py`, `cc.mp.ps1`, `cc.mp.sh`, or `cc.mp.bat` for multi-platform sessions
2. If session mappings file has UTF-8 BOM, use `utf-8-sig` encoding in Python
**Debug**: 
- Check if session UUID exists in `data/cache/session-mappings.json`
- Test direct lookup: `python -c "from platform_manager import PlatformManager; print(PlatformManager().get_session_config('YOUR-UUID'))"`
- Check for BOM: `python -c "with open('data/cache/session-mappings.json', 'rb') as f: print(f.read(3))"`

### Missing Balance Data
**Root Cause**: Platform-specific cache files not being created
**Debug Steps**:
1. Verify API key is set: `python platform_manager.py list`
2. Check platform detection logs: `tail -f data/logs/platform-manager.log`
3. Test API connectivity manually
4. Ensure proper authentication method (api_key vs auth_token)

### Configuration Sync Issues  
**Root Cause**: Configuration not properly synced from launcher to plugin
**Solution**: Launcher scripts automatically sync `data/config/launcher-config.json` → `data/config/platform-config.json`

## File Organization Patterns

### Configuration Files
- **Source**: `data/config/launcher-config.json` (user-editable)
- **Runtime**: `data/config/platform-config.json` (auto-synced)
- **Session State**: `data/cache/session-*.json` (runtime state)

### Platform Implementations
- **Interface**: `platforms/base.py` (abstract base)
- **Implementations**: `platforms/{platform}.py` (concrete implementations)  
- **Management**: `platforms/manager.py` (orchestration logic)

### Entry Points (Updated Architecture)
- **Main Statusline**: `statusline.py` (Claude Code integration point)
- **Configuration**: `config-statusline.py` (display settings management)
- **Platform Config**: `platform_manager.py` (API key management)
- **🆕 Unified Launcher**: `bin/launcher.py` (main implementation, ~300 lines)
- **📦 Wrapper Scripts**: `bin/cc.mp.*` (lightweight wrappers, 30-40 lines each)
  - `cc.mp.ps1`: PowerShell wrapper
  - `cc.mp.sh`: Bash wrapper
  - `cc.mp.bat`: Windows CMD wrapper (NEW)
- **🆕 Session Management**: `data/session_manager.py` (session state and resume functionality)

### Architecture Benefits
- **Single Source of Truth**: All launcher logic centralized in `launcher.py`
- **Cross-platform Consistency**: Identical behavior on all operating systems
- **Enhanced UUID Generation**: Platform-prefixed UUIDs for better identification
- **Integrated Session Resume**: Built-in `--continue` support for all platforms
- **Simplified Maintenance**: 90% reduction in code duplication

## Integration Points

### Claude Code Integration
The statusline integrates via Claude Code's status line configuration:
```json
{
  "statusLine": {
    "type": "command", 
    "command": "python /path/to/statusline.py",
    "refreshInterval": 1000
  }
}
```

### Session Information Flow
1. Claude Code passes session info via stdin (JSON format)
2. `statusline.py` reads and caches session info
3. Platform detection extracts `session_id` from session info
4. Platform-specific API calls fetch balance/subscription data
5. Formatted output returned to Claude Code for display

### External Dependencies
- **ccusage**: npm package for usage tracking (`npx ccusage`)
- **requests**: Python HTTP library for API calls
- **pathlib**: Modern path handling
- **json**: Configuration and data serialization

## Critical Reminders

### 🔒 Security & Privacy
**NEVER**:
- Include real API keys, tokens, emails in code or documentation
- Use hardcoded credentials in examples - always use placeholders
- Commit sensitive configuration files or cache data
- Skip data masking in logs or debug output
- Make frequent API calls without rate limiting

**ALWAYS**:
- Use placeholder formats in documentation (`sk-ant-xxx...`, `eyJhbG...`)
- Implement automatic sensitive data filtering in logs
- Respect API rate limits (GAC: 60+ second intervals)
- Use cached data when rate limited
- Audit code for privacy leaks before release

### 🚨 API Protection
**GAC Code Specific**:
- **CRITICAL**: 60 second minimum between API calls (risk: account ban)
- Use intelligent fallback to cached data when rate limited
- Monitor and log API call frequencies for debugging
- Never bypass rate limiting for "urgent" features

**Other Platforms**:
- Follow documented rate limits for each provider
- Implement conservative defaults when limits unknown
- Use exponential backoff for retry logic
- Cache API responses appropriately (balance TTL vs freshness)

### 🛠️ Development Guidelines  
**NEVER**:
- Use `--no-verify` to bypass commit hooks
- Disable tests instead of fixing them
- Commit code that doesn't compile
- Make assumptions - verify with existing code
- Create files unless absolutely necessary

**ALWAYS**:
- Commit working code incrementally
- Learn from existing implementations before coding
- Stop after 3 failed attempts and reassess approach
- Use unified caching and logging systems
- Follow existing code patterns and conventions