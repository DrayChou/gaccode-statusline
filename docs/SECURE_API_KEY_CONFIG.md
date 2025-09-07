# 🔒 安全API密钥配置指南

## 安全原则

### 为什么不使用 `set-key` 命令？

**安全风险**：
- 命令行中的API密钥会被记录在shell历史中
- 进程列表中可能暴露敏感信息
- 其他用户可能通过系统监控工具看到密钥

**最佳实践**：
- ✅ 直接编辑配置文件
- ✅ 使用安全的文件权限设置
- ❌ 避免命令行传递密钥

## 推荐配置方法

### 方法 1：配置文件（推荐）

1. **复制配置模板**：
```bash
cp examples/launcher-config.template.json examples/launcher-config.json
```

2. **编辑配置文件**：
```json
{
  "platforms": {
    "gaccode": {
      "api_key": "",
      "login_token": "your-actual-gac-login-token",
      "enabled": true
    },
    "deepseek": {
      "api_key": "sk-your-actual-deepseek-key",
      "enabled": true
    },
    "kimi": {
      "auth_token": "sk-your-actual-kimi-key",
      "enabled": true
    }
  }
}
```

3. **验证配置**：
```bash
python platform_manager.py list
```

### 方法 2：使用配置文件模板（高级）

1. **复制配置模板**：
```bash
cp examples/launcher-config.template.json examples/launcher-config.json
```

2. **编辑配置文件填入真实密钥**：
```bash
# 编辑主配置文件
nano examples/launcher-config.json
```

3. **验证配置**：
```bash
python platform_manager.py list  # 验证配置状态
```

## 已移除的不安全命令

以下命令已被移除或废弃，不再推荐使用：

```bash
# ❌ 不安全 - 已废弃
python platform_manager.py set-key dp "sk-your-key"
python platform_manager.py set-key kimi "sk-your-key"
python platform_manager.py set-key gc "your-token"

# ❌ 不安全 - 已废弃
python multi_platform_config.py set-key platform "key"
```

## 安全验证命令

以下命令是安全的，不会暴露密钥：

```bash
# ✅ 安全 - 查看平台状态（密钥会被遮蔽）
python platform_manager.py list

# ✅ 安全 - 检查特定平台密钥状态
python platform_manager.py get-key deepseek
python platform_manager.py get-key kimi
python platform_manager.py get-key gaccode
```

## 配置文件安全

### 文件权限

确保配置文件只有用户可读：
```bash
# Linux/Mac
chmod 600 examples/launcher-config.json
chmod 600 data/config/launcher-config.json

# Windows
icacls examples\launcher-config.json /inheritance:r /grant:r "%USERNAME%:(R,W)"
```

### .gitignore 保护

配置文件已在 `.gitignore` 中被排除：
```gitignore
# API密钥和敏感配置文件
examples/launcher-config.json
data/config/launcher-config.json
data/cache/session-mappings.json
*.log
```

## 密钥获取指南

### GAC Code
1. 登录 [gaccode.com](https://gaccode.com)
2. 打开开发者工具 (F12)
3. 在 Network 面板找到 API 请求
4. 复制 Authorization Bearer token

### DeepSeek
1. 访问 [platform.deepseek.com](https://platform.deepseek.com)
2. 注册并登录账户
3. 在 API Keys 页面创建新密钥
4. 复制生成的 `sk-` 开头的密钥

### Kimi (月之暗面)
1. 访问 [platform.moonshot.cn](https://platform.moonshot.cn)
2. 注册并登录账户
3. 在控制台创建 API 密钥
4. 复制生成的密钥

### SiliconFlow
1. 访问 [cloud.siliconflow.cn](https://cloud.siliconflow.cn)
2. 注册并登录账户
3. 在 API 管理页面创建密钥
4. 复制生成的 `sk-` 开头的密钥

## 故障排除

### 密钥未被识别
```bash
# 检查配置文件格式
python -m json.tool examples/launcher-config.json

# 检查配置文件状态
python platform_manager.py get-key deepseek  # 已屏蔽显示
python config.py --get-effective-config      # 查看当前配置
```

### 权限问题
```bash
# 检查文件权限
ls -la examples/launcher-config.json  # Linux/Mac
icacls examples\launcher-config.json  # Windows
```

## 安全检查清单

- [ ] 从不在命令行中直接传递API密钥
- [ ] 配置文件权限设置为仅用户可读
- [ ] 敏感文件已添加到 `.gitignore`
- [ ] 定期轮换API密钥
- [ ] 监控API使用情况，及时发现异常
- [ ] 使用安全的配置文件管理系统

---

**记住**：保护您的API密钥就像保护您的密码一样重要。永远不要在公共场所或不安全的环境中暴露这些敏感信息。