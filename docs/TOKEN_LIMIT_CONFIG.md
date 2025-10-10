# Claude Code Token 限制配置指南

## 问题描述

当使用 **DeepSeek V3.2 模型** 时，可能会遇到以下错误：

```
API Error: Claude's response exceeded the 32000 output token maximum.
To configure this behavior, set the CLAUDE_CODE_MAX_OUTPUT_TOKENS environment variable.
```

### 根本原因

1. **DeepSeek V3.2 模型特性**：擅长生成长代码，经常产生超过 32000 tokens 的响应
2. **Claude Code 客户端限制**：默认只接收 32000 tokens 的响应
3. **触发条件**：只有 DeepSeek V3.2 模型会触发此错误，其他模型不会

## 解决方案

### 自动配置（推荐）

项目已为 **所有使用 DeepSeek 模型的平台** 配置了合适的 token 限制：

- **DeepSeek 官方 API**（使用 deepseek-chat 模型）：64000 tokens
- **SiliconFlow**（使用 deepseek-ai/DeepSeek-V3.2 模型）：64000 tokens

使用 launcher 启动时会自动设置环境变量：

```bash
# DeepSeek官方API - 自动设置64000限制
python bin/launcher.py dp

# SiliconFlow平台 - 自动设置64000限制
python bin/launcher.py sf
```

### 为什么配置这些平台？

1. **DeepSeek 模型特性**：所有 DeepSeek 模型（官方 deepseek-chat 和 V3.2）都会生成长响应
2. **实证依据**：用户在实际使用中遇到了 token 超限错误
3. **完整覆盖**：确保所有使用 DeepSeek 模型的平台都不会遇到此问题

### 手动配置

如果其他平台也遇到类似错误，可以手动添加配置：

1. 打开 `data/config/config.json`
2. 找到对应的平台配置
3. 添加 `claude_code_config` 部分：

```json
{
  "platforms": {
    "your_platform": {
      "claude_code_config": {
        "max_output_tokens": 64000
      }
    }
  }
}
```

### 环境变量手动设置

如果需要临时设置，也可以直接设置环境变量：

```bash
# Windows PowerShell
$env:CLAUDE_CODE_MAX_OUTPUT_TOKENS = "64000"

# Linux/Mac
export CLAUDE_CODE_MAX_OUTPUT_TOKENS=64000
```

## 技术细节

- **错误来源**：Claude Code CLI 客户端，不是平台 API
- **默认限制**：32000 output tokens
- **配置方式**：环境变量 `CLAUDE_CODE_MAX_OUTPUT_TOKENS`
- **控制对象**：Claude Code 客户端的接收上限，不是 API 的输出限制
- **支持状态**：官方支持（基于错误信息确认）

## 关键理解

**`CLAUDE_CODE_MAX_OUTPUT_TOKENS` 不是平台 API 限制，而是 Claude Code 客户端的接收限制！**

- 当 DeepSeek V3.2 返回超过 32000 tokens 时，客户端拒绝继续接收
- 提高此限制让客户端能接收完整的长响应
- 这不影响其他平台的正常使用

## 故障排除

如果仍然遇到 token 限制错误：

1. 确认使用的是 DeepSeek 模型（官方 API 或 SiliconFlow）
2. 检查对应平台的配置是否正确加载
3. 验证环境变量是否设置成功
4. 考虑使用更简单的请求减少响应长度
