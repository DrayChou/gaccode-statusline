# GAC API 状态栏配置指南

## ✅ 已完成的配置

### 1. 文件结构

```
.claude/
├── scripts/gaccode.com/
│   ├── statusline.py          # ✅ 状态栏主脚本
│   ├── set-gac-token.py       # ✅ Token管理工具
│   ├── api-token.txt          # ✅ API Token文件
│   └── statusline-cache.json  # ✅ 缓存文件
└── settings.json              # ✅ 已配置statusLine
```

### 2. settings.json 配置

```json
{
  "statusLine": {
    "type": "command",
    "command": "python scripts/gaccode.com/statusline.py",
    "padding": 1
  }
}
```

## 🚀 立即使用

### 1. 查看当前 Token 状态

```bash
python scripts/gaccode.com/set-gac-token.py show
```

### 2. 更换 Token（如需要）

```bash
python scripts/gaccode.com/set-gac-token.py set "your-new-token"
```

### 3. 重启 Claude Code

重启后即可看到状态栏显示：`Balance:444/12000 Expires:09-13(18d)`

## 📊 状态栏说明

### 显示格式

- `Balance:266/12000` - 当前余额/总额度
- `Expires:09-13(18d)` - 订阅到期日期(剩余天数)

### 颜色编码

- 🟢 **绿色**：余额充足(>1000) / 时间充足(>14 天)
- 🟡 **黄色**：余额警告(500-1000) / 时间警告(7-14 天)
- 🔴 **红色**：余额不足(<500) / 即将到期(<7 天)

### 智能显示

- ✅ 仅在使用 gaccode 模型时显示
- ✅ 5 分钟缓存，减少 API 调用
- ✅ 网络异常时显示错误提示

## 🔧 管理命令

```bash
# Token管理
python scripts/gaccode.com/set-gac-token.py show     # 查看当前token
python scripts/gaccode.com/set-gac-token.py set "xxx"  # 设置新token
python scripts/gaccode.com/set-gac-token.py remove  # 删除token

# 测试功能
python scripts/gaccode.com/test-statusline.py       # 完整测试
echo '{"model":{"id":"gaccode-test"}}' | python scripts/gaccode.com/statusline.py  # 直接测试
```

## 📝 注意事项

1. **Token 安全**: Token 存储在本地，可随时更换
2. **网络要求**: 需要能访问 gaccode.com API
3. **模型检测**: 只有在使用包含"gac"或"gaccode"的模型时才显示
4. **错误处理**: API 调用失败时显示 [ERROR] 提示

## 🎯 状态说明

- **正常工作**: 显示余额和到期信息
- **未配置 Token**: 显示 `[WARN] 未配置GAC API Token`
- **API 调用失败**: 显示 `[ERROR] GAC API调用失败`
- **数据解析失败**: 显示 `[ERROR] 数据解析失败`
- **非 GAC 模型**: 不显示任何内容

## 🔄 已完成测试

✅ Token 管理功能正常  
✅ API 调用成功  
✅ 数据解析正确  
✅ 缓存机制工作  
✅ 颜色编码显示  
✅ 错误处理完善

## 📞 故障排除

如果状态栏没有显示：

1. 确认使用的是包含"gac"的模型
2. 检查 Token 是否配置正确
3. 测试网络连接
4. 重启 Claude Code

配置已完成，重启 Claude Code 即可使用！
