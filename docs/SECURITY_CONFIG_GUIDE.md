# 安全配置指南 (Security Configuration Guide)

## 🔒 概览 (Overview)

GAC Code多平台系统的安全配置最佳实践，确保API密钥和敏感信息得到妥善保护。

## 🛡️ 安全配置原则

### 1. 分层安全防护
- **配置文件层**: 敏感信息不进入版本控制
- **环境变量层**: 推荐的密钥存储方式
- **运行时层**: 日志和调试输出中的敏感信息屏蔽
- **文件系统层**: 适当的文件权限设置

### 2. 数据分类
- **高敏感**: API密钥、登录令牌、身份验证信息
- **中敏感**: 配置文件路径、API端点、用户标识
- **低敏感**: 平台名称、模型名称、显示设置

## 🔑 API密钥管理

### 推荐方案：环境变量

**优势**:
- 不会意外提交到版本控制
- 支持不同环境的不同配置
- 操作系统级别的保护

**设置方法**:

```bash
# Linux/Mac
export DEEPSEEK_API_KEY="sk-your-deepseek-key-here"
export KIMI_API_KEY="sk-your-kimi-key-here"
export GAC_LOGIN_TOKEN="your-gac-login-token-here"
export SILICONFLOW_API_KEY="sk-your-sf-key-here"

# Windows PowerShell
$env:DEEPSEEK_API_KEY="sk-your-deepseek-key-here"
$env:KIMI_API_KEY="sk-your-kimi-key-here"
$env:GAC_LOGIN_TOKEN="your-gac-login-token-here"
$env:SILICONFLOW_API_KEY="sk-your-sf-key-here"

# Windows Command Prompt
set DEEPSEEK_API_KEY=sk-your-deepseek-key-here
set KIMI_API_KEY=sk-your-kimi-key-here
set GAC_LOGIN_TOKEN=your-gac-login-token-here
set SILICONFLOW_API_KEY=sk-your-sf-key-here
```

**使用环境变量配置平台**:

```bash
# 环境变量会被自动检测，无需手动设置
# 验证环境变量配置状态
python platform_manager.py list

# 重要安全提醒：
# 不要在命令行中直接传递API密钥，防止在shell历史中暴露
# 环境变量是最安全的配置方式
```

### 备选方案：配置文件

**仅适用于本地开发环境**，生产环境请使用环境变量。

**配置步骤**:

1. 编辑配置文件：
```bash
# 编辑主配置文件
nano examples/launcher-config.json
```

2. 安全的配置文件模板：
```json
{
  "platforms": {
    "deepseek": {
      "name": "DeepSeek",
      "api_base_url": "https://api.deepseek.com",
      "api_key": "sk-REPLACE-WITH-YOUR-ACTUAL-DEEPSEEK-KEY",
      "model": "deepseek-chat",
      "small_model": "deepseek-chat",
      "enabled": true
    },
    "gaccode": {
      "name": "GAC Code", 
      "api_base_url": "https://gaccode.com/api",
      "login_token": "REPLACE-WITH-YOUR-ACTUAL-GAC-TOKEN",
      "model": "claude-3-5-sonnet-20241022",
      "small_model": "claude-3-5-haiku-20241022",
      "enabled": true
    }
  }
}
```

3. 验证配置：
```bash
python platform_manager.py list
```

## 🔐 配置文件保护

### .gitignore 配置

项目已包含完整的`.gitignore`文件，确保敏感文件不会被提交：

```gitignore
# 敏感配置文件
data/config/platform-config.json
data/cache/session-mappings.json
examples/.session-state.json
launcher-config.json
session-mappings.json

# API相关文件
api-token.txt
*.key
*.token

# 缓存文件（可能包含敏感信息）
data/cache/balance-cache-*.json
data/cache/session-info-cache.json
statusline-cache.json
usage-cache.json

# 日志文件（可能包含调试信息）
*.log
logs/
data/logs/
```

### 文件权限设置

**Linux/Mac**:
```bash
# 设置配置文件为仅用户可读写
chmod 600 examples/launcher-config.json
chmod 600 data/config/platform-config.json

# 设置目录权限
chmod 700 data/config/
chmod 700 data/cache/
```

**Windows**:
```powershell
# 使用PowerShell设置文件权限（仅当前用户可访问）
icacls "examples\launcher-config.json" /inheritance:d
icacls "examples\launcher-config.json" /grant:r "%username%:(F)"
icacls "examples\launcher-config.json" /remove "Users"
```

## 🔍 安全审计

### 敏感信息检测

**检查配置文件是否包含真实密钥**:
```bash
# 搜索可能的API密钥模式
grep -r "sk-[a-zA-Z0-9]" . --exclude-dir=.git
grep -r "eyJ[a-zA-Z0-9]" . --exclude-dir=.git  # JWT令牌

# 检查是否有未被.gitignore覆盖的敏感文件
git ls-files | grep -E "\.(key|token|json)$"
```

**验证日志安全性**:
```bash
# 检查日志文件是否包含敏感信息
grep -r "sk-" data/logs/ || echo "No API keys found in logs"
grep -r "eyJ" data/logs/ || echo "No JWT tokens found in logs"
```

### 配置验证

**验证平台配置**:
```bash
# 检查平台配置状态（敏感信息已屏蔽）
python platform_manager.py list

# 测试平台连接性（dry-run模式，无实际API调用）
python examples/launcher.py dp --dry-run
python examples/launcher.py kimi --dry-run
```

## 📋 安全检查清单

### 部署前检查

- [ ] **环境变量配置**: API密钥通过环境变量设置
- [ ] **配置文件清理**: 移除配置文件中的真实API密钥
- [ ] **文件权限**: 敏感文件设置适当的访问权限
- [ ] **.gitignore验证**: 确保敏感文件被正确排除
- [ ] **日志审计**: 验证日志中无敏感信息泄露

### 运行时监控

- [ ] **API调用监控**: 监控API调用频率和错误率
- [ ] **权限检查**: 定期检查文件和目录权限
- [ ] **密钥轮换**: 定期更换API密钥
- [ ] **日志清理**: 定期清理包含敏感信息的旧日志

## 🚨 安全事件响应

### 密钥泄露处理

1. **立即撤销泄露的API密钥**
2. **生成新的API密钥**
3. **更新所有使用该密钥的配置**
4. **审查访问日志，确认是否有异常使用**
5. **强化安全措施，防止再次泄露**

### 配置泄露处理

1. **从版本控制中移除敏感配置**
2. **使用`git filter-branch`清理历史记录**
3. **更新所有相关的API密钥**
4. **通知团队成员更新本地配置**

## 🔧 故障排除

### 常见安全问题

**问题**: API密钥在日志中可见
**解决**: 检查日志屏蔽机制，确保敏感信息过滤器正常工作

**问题**: 配置文件被意外提交
**解决**: 使用`git rm --cached`移除，并更新`.gitignore`

**问题**: 环境变量不生效
**解决**: 确认环境变量在启动进程前设置，检查变量名是否正确

### 调试安全问题

```bash
# 检查环境变量
echo $DEEPSEEK_API_KEY | cut -c1-10  # 只显示前10个字符
env | grep -E "(DEEPSEEK|KIMI|GAC|SILICONFLOW)" | cut -d'=' -f1

# 验证配置加载
python -c "
from platform_manager import PlatformManager
pm = PlatformManager()
config = pm.get_platform_config('deepseek')
print('API key configured:', 'api_key' in config and len(config.get('api_key', '')) > 0)
"
```

## 📚 相关文档

- [快速开始指南](../快速开始.md) - 安全配置的基础步骤
- [多平台使用指南](MULTI_PLATFORM_USAGE_GUIDE.md) - 平台配置详情
- [故障排除文档](../README.md#🔧-troubleshooting) - 常见问题解决

---

**免责声明**: 本指南提供的安全建议仅供参考。在生产环境中，请根据您的具体安全要求和合规需求进行适当调整。