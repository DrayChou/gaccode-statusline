# GAC Code Security Guide

## Quick Start

### 🚀 One-Command Security Setup
```bash
python security_setup.py
```

This interactive wizard will:
- Check your current security status
- Guide you through secure configuration
- Help migrate to environment variables
- Generate setup scripts automatically

### 🔍 Quick Security Check
```bash
python security_setup.py --quick
```

## Security Architecture

### Configuration File Priority

The system now uses **configuration files**, with secure file-based management:

```
Configuration Files → Defaults
```

### Supported Configuration Fields

| Platform | Configuration Field | Alternative Fields |
|----------|---------------------|--------------------|
| GAC Code | `api_key` | `login_token` |
| DeepSeek | `api_key` | |
| Kimi | `auth_token` | `api_key` |
| SiliconFlow | `api_key` | |
| Local Proxy | `api_key` | |

## Security Features

### 🛡️ Comprehensive Security System

1. **Configuration File Management**: Secure file-based credential storage
2. **Input Validation**: All inputs validated for security (path traversal, injection, etc.)
3. **Sensitive Data Masking**: API keys automatically masked in logs and output
4. **Secure File Handling**: Safe file operations with proper locking
5. **Security Auditing**: Automated security risk detection
6. **Configuration Migration**: Tools to migrate from plaintext to secure storage

### 🔐 Security Components

- **`data/security_manager.py`**: Core security management and auditing
- **`data/secure_config.py`**: Environment-first configuration loading
- **`data/input_validator.py`**: Comprehensive input validation and sanitization
- **Enhanced Logging**: Automatic sensitive data masking in all logs
- **Migration Tools**: Automated migration from config files to environment variables

## Migration Guide

### Method 1: Interactive Migration (Recommended)
```bash
# Full interactive migration wizard
python security_migration_tool.py --interactive

# Or use the simplified setup wizard
python security_setup.py
```

### Method 2: Quick Migration
```bash
# Generate migration script only
python security_migration_tool.py --migrate bash    # Linux/macOS
python security_migration_tool.py --migrate powershell  # Windows PowerShell
python security_migration_tool.py --migrate batch   # Windows CMD
```

### Method 3: Manual Configuration File Setup

#### Edit Configuration File
```bash
# Edit the main configuration file
nano data/config/config.json

# Configuration format:
{
  "platforms": {
    "gaccode": {
      "api_key": "your-gaccode-api-key",
      "login_token": "your-gaccode-login-token",
      "enabled": true
    },
    "deepseek": {
      "api_key": "your-deepseek-api-key",
      "enabled": true
    },
    "kimi": {
      "auth_token": "your-kimi-auth-token",
      "enabled": true
    },
    "siliconflow": {
      "api_key": "your-siliconflow-api-key",
      "enabled": true
    }
  }
}
```

#### Verify Configuration
```bash
# Check configuration status
python config.py --security-status
```

## Security Commands

### Configuration Management
```bash
# Check current security status
python config.py --security-status

# View configuration with sensitive data masked
python config.py --get-effective-config

# List platforms with authentication sources
python config.py --list-platforms
```

### Security Auditing
```bash
# Full security audit
python security_migration_tool.py --audit

# Clean sensitive data from logs
python security_migration_tool.py --clean-logs

# Fix file permissions
python security_migration_tool.py --fix-permissions
```

### Advanced Security Tools
```bash
# Generate environment template
python data/security_manager.py --generate-template

# Validate specific inputs
python data/input_validator.py --test-path "/some/path"
python data/input_validator.py --test-api-key "platform" "key"

# Clean specific log files
python data/logger.py --clean-logs
```

## Security Best Practices

### ✅ Recommended Practices

1. **Use Configuration Files**: Store all API keys in secure configuration files
2. **Regular Key Rotation**: Rotate API keys periodically
3. **Secure File Permissions**: Use restrictive permissions (600/700)
4. **Regular Audits**: Run security audits regularly
5. **Monitor Logs**: Check logs for credential leaks
6. **Version Control**: Never commit credentials to Git
7. **Backup Safely**: Encrypt backups containing sensitive data

### ❌ Avoid These Practices

1. **Insecure Storage**: Don't store API keys in version-controlled files
2. **Version Control**: Never commit files with API keys
3. **Log Exposure**: Don't log complete API keys
4. **Insecure Sharing**: Don't share credentials via insecure channels
5. **Weak Permissions**: Don't use overly permissive file permissions
6. **Hardcoded Keys**: Don't hardcode credentials in source code

## Troubleshooting

### Configuration Issues

**Problem**: "Configuration contains plaintext credentials"
```bash
# Solution: Ensure configuration files are properly secured
python security_setup.py --secure-config
```

**Problem**: "Platform not enabled or API key missing"
```bash
# Check current configuration
python config.py --get-effective-config

# Verify configuration file settings
python config.py --get-effective-config
```

**Problem**: "Security modules not available"
```bash
# Check if security files exist
python security_setup.py --quick

# If missing, ensure all security components are installed
ls data/security_manager.py data/secure_config.py data/input_validator.py
```

### Environment Variable Issues

**Problem**: Configuration not recognized
```bash
# Check configuration file syntax
python -m json.tool data/config/config.json

# Verify configuration is loaded
python data/secure_config.py --check-config
```

**Problem**: "API key format invalid"
```bash
# Test API key format
python data/input_validator.py --test-api-key "platform" "your-key"

# Check platform-specific requirements in the validation output
```

### Permission Issues

**Problem**: "File permissions too open"
```bash
# Fix automatically
python security_migration_tool.py --fix-permissions

# Or manually (Linux/macOS)
chmod 600 data/config/*.json
chmod 700 data/backups/
```

## Integration with Existing Systems

### Launcher Integration

The security system is fully integrated with existing launchers:

```bash
# All launchers automatically use secure configuration
python bin/launcher.py dp  # Uses configuration files
./examples/cc.mp.ps1 kimi  # PowerShell launcher with security
./examples/cc.mp.sh sf     # Bash launcher with security
```

### Statusline Integration

The statusline automatically:
- Uses secure configuration loading
- Masks sensitive data in displays
- Logs securely without exposing credentials

### Backward Compatibility

The security system maintains full backward compatibility:
- Configuration files are the primary method
- Secure file-based management
- No breaking changes to existing workflows

## Security Validation

### Verify Security Setup
```bash
# Run comprehensive security check
python security_setup.py --quick

# Check effective configuration
python config.py --get-effective-config

# Validate specific components
python data/secure_config.py --check-env
python data/input_validator.py --test-mask
```

### Expected Output

After successful configuration, you should see:
- ✅ No security warnings in logs
- ✅ Configuration files properly secured
- ✅ API keys masked in all outputs
- ✅ Security audit shows no critical issues

## Support and Updates

### Getting Help

1. **Quick Help**: Run `python security_setup.py` for interactive guidance
2. **Documentation**: Check `CLAUDE.md` for detailed project information
3. **Security Issues**: Run `python security_migration_tool.py --audit` for detailed analysis

### Regular Maintenance

```bash
# Monthly security audit
python security_migration_tool.py --audit

# Clean sensitive data from logs
python data/logger.py --clean-logs

# Update security configuration
python security_setup.py --quick
```

---

**Security Notice**: This security system addresses the critical vulnerabilities identified in the security audit, including:
- CVSS 9.1: Plain text API keys in config files → **Fixed with environment variables**
- JWT token exposure → **Fixed with comprehensive masking**
- Incomplete logging security → **Fixed with universal masking system**
- File permission issues → **Fixed with automatic permission management**
- Missing input validation → **Fixed with comprehensive validation system**

For questions or security concerns, refer to the interactive help system or the detailed documentation in `CLAUDE.md`.
