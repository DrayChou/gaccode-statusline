# Multi-Platform API Documentation

## 支持的平台列表

本项目支持以下 AI 平台的余额查询：

1. **GAC Code** - Claude 模型的代理服务
2. **Kimi (月之暗面)** - Moonshot AI 平台
3. **DeepSeek** - DeepSeek AI 平台
4. **SiliconFlow (硅基流动)** - SiliconFlow AI 平台

## 平台 API 文档

### 1. GAC Code Platform

**基础信息：**

- API Base URL: `https://gaccode.com/api/credits`
- 认证方式: JWT Bearer Token (login_token)
- 主要用于: Claude 模型

**请求头要求：**
```http
accept: */*
accept-language: zh
authorization: Bearer {login_token}
content-type: application/json
user-agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36
```

**API 接口：**

#### 查询余额

```http
GET https://gaccode.com/api/credits/balance
Authorization: Bearer {login_token}
Content-Type: application/json
```

**响应示例：**

```json
{
  "balance": 956,
  "creditCap": 12000,
  "refillRate": 300,
  "lastRefill": "2025-09-05T15:01:10.941Z"
}
```

#### 查询模型信息

```http
GET https://gaccode.com/api/credits/models
Authorization: Bearer {login_token}
Content-Type: application/json
```

**响应示例：**

```json
{
  "models": [
    {
      "id": 1,
      "modelName": "claude-code",
      "cost": -1,
      "description": "Variable cost model",
      "createdAt": "2025-05-22T20:53:57.000Z"
    }
  ]
}
```

#### 查询使用历史

```http
GET https://gaccode.com/api/credits/history
Authorization: Bearer {login_token}
Content-Type: application/json
```

**响应示例：**

```json
{
  "history": [
    {
      "userId": 28204,
      "amount": -9,
      "balanceAfter": 1052,
      "reason": "usage",
      "details": "Model: claude-code - Variable Cost Calculation",
      "createdAt": "2025-09-05T14:30:15.000Z"
    }
  ]
}
```

**响应示例：**

```json
{
  "subscriptions": [
    {
      "endDate": "2024-09-25T00:00:00Z",
      "status": "active"
    }
  ]
}
```

### 2. Kimi Platform (月之暗面)

**基础信息：**

- API Base URL: `https://api.moonshot.cn/v1`
- 认证方式: Bearer Token (通常以 `sk-` 开头)
- 主要用于: Moonshot 模型

**API 接口：**

#### 查询余额

```http
GET https://api.moonshot.cn/v1/users/me/balance
Authorization: Bearer {MOONSHOT_API_KEY}
Content-Type: application/json
```

**响应示例：**

```json
{
  "code": 0,
  "data": {
    "available_balance": 49.58894,
    "voucher_balance": 46.58893,
    "cash_balance": 3.00001
  },
  "scode": "0x0",
  "status": true
}
```

**响应字段说明：**

- `available_balance`: 可用余额，包括现金余额和代金券余额，当它小于等于 0 时，用户不可调用推理 API
- `voucher_balance`: 代金券余额，不会为负数
- `cash_balance`: 现金余额，可能为负数，代表用户欠费，当它为负数时，available_balance 为 voucher_balance 的值
- 单位: 人民币元（CNY）

### 3. DeepSeek Platform

**基础信息：**

- API Base URL: `https://api.deepseek.com`
- 认证方式: Bearer Token
- 主要用于: DeepSeek 模型

**API 接口：**

#### 查询余额

```http
GET https://api.deepseek.com/user/balance
Authorization: Bearer {token}
Content-Type: application/json
```

**响应示例：**

```json
{
  "is_available": true,
  "balance_infos": [
    {
      "currency": "USD",
      "total_balance": 25.5,
      "granted_balance": 20.0,
      "topped_up_balance": 5.5
    }
  ]
}
```

**响应字段说明：**

- `is_available`: 当前账户是否有余额可供 API 调用
- `balance_infos`: 余额详情数组
  - `currency`: 货币类型 (USD/CNY)
  - `total_balance`: 总余额
  - `granted_balance`: 赠送余额
  - `topped_up_balance`: 充值余额

### 4. SiliconFlow Platform (硅基流动)

**基础信息：**

- API Base URL: `https://api.siliconflow.cn/v1`
- 认证方式: Bearer Token
- 主要用于: SiliconFlow 模型

**API 接口：**

#### 获取用户信息（包含余额）

```http
GET https://api.siliconflow.cn/v1/user/info
Authorization: Bearer <token>
Content-Type: application/json
```

**响应示例：**

```json
{
  "code": 20000,
  "message": "OK",
  "status": true,
  "data": {
    "id": "userid",
    "name": "username",
    "image": "user_avatar_image_url",
    "email": "user_email_address",
    "isAdmin": false,
    "balance": "0.88",
    "status": "normal",
    "introduction": "",
    "role": "",
    "chargeBalance": "88.00",
    "totalBalance": "88.88"
  }
}
```

**响应字段说明：**

- `code`: 响应状态码，20000 表示成功
- `status`: 请求状态
- `data.totalBalance`: 总余额
- `data.balance`: 当前可用余额
- `data.chargeBalance`: 充值余额
- 单位: 人民币元（CNY）

## 平台检测规则

### 自动检测优先级

1. **配置文件显式指定** - `statusline-config.json` 中的 `platform_type` 字段
2. **API 连通性检测** - 通过试探性请求检测可用的 API 端点
3. **Token 格式检测** - 基于 token 格式判断平台
4. **模型 ID 检测** - 基于使用的模型判断平台

### 智能平台检测系统

由于 Claude Code 的 statusline 机制不直接提供 API endpoint URL 和当前使用的 API key，系统采用**四层智能检测机制**：

#### 检测方法及优先级

1. **配置文件分析 (权重 40%)**

   - 扫描 `~/.claude/settings.json`、`.claude/settings.json` 等配置文件
   - 检测环境变量：`ANTHROPIC_API_KEY`、`MOONSHOT_API_KEY` 等
   - 分析 `apiKeyHelper` 和 `apiBaseUrl` 配置

2. **Session 推断 (权重 30%)**

   - 基于模型 ID 判断：`claude-*` → GAC Code, `moonshot` → Kimi
   - 成本信息分析：不同平台的计费模式特征
   - 版本信息匹配

3. **进程分析 (权重 20%)**

   - 检测 Claude Code 进程的环境变量
   - 分析命令行参数中的 API URL
   - 监控进程打开的配置文件

4. **网络监听 (权重 10%)**
   - 监听到 `api.moonshot.cn`、`api.deepseek.com` 等域名的连接
   - IP 地址反向解析
   - 实时连接状态分析

#### 配置选项

```json
{
  "platform_detection": {
    "enable_config_analysis": true,
    "enable_process_analysis": false,
    "enable_network_monitoring": false,
    "confidence_threshold": 0.6
  }
}
```

#### 检测策略

- **保守策略**：仅使用配置文件和 session 推断（默认）
- **积极策略**：启用所有检测方法，包括进程和网络监听
- **调试模式**：生成详细的检测报告用于故障排除

### 检测规则详细说明

#### GAC Code 检测

- 模型 ID 以 `claude-` 开头
- 配置中 `platform_type` 为 `gaccode`

#### Kimi 检测

- Token 以 `sk-` 开头
- 模型 ID 包含 `moonshot`
- 配置中 `platform_type` 为 `kimi` 或 `moonshot`

#### DeepSeek 检测

- 模型 ID 包含 `deepseek`
- 配置中 `platform_type` 为 `deepseek`

#### SiliconFlow 检测

- 模型 ID 包含 `siliconflow` 或 `silicon`
- 配置中 `platform_type` 为 `siliconflow` 或 `silicon`

## 配置说明

### 显式指定平台

在 `statusline-config.json` 中添加：

```json
{
  "platform_type": "kimi",
  "show_balance": true,
  "show_subscription": true
}
```

支持的 `platform_type` 值：

- `gaccode` - GAC Code 平台
- `kimi` 或 `moonshot` - Kimi 平台
- `deepseek` - DeepSeek 平台
- `siliconflow` 或 `silicon` - SiliconFlow 平台

### Token 配置

使用对应平台的 token 设置工具：

```bash
# 编辑配置文件
nano data/config/config.json

# 配置格式示例:
{
  "platforms": {
    "gaccode": {
      "login_token": "your-gac-token",
      "enabled": true
    },
    "kimi": {
      "auth_token": "sk-your-kimi-token",
      "enabled": true
    },
    "deepseek": {
      "api_key": "your-deepseek-token",
      "enabled": true
    }
  }
}
```

## 显示格式

### 余额显示格式

**GAC Code（动态倍率）:**

```
# 普通时段
GAC.B:2692/12000 (45m30s)

# 2倍时段
GAC.B:1845/12000 2x (23m15s)

# 高倍率时段
GAC.B:1203/12000 5x (12m42s)

# 警告状态（API与时间段不匹配）
GAC.B:956/12000 !10x (8m15s)
```

**Kimi:**

```
Balance:¥49.59 (券:¥46.59, 现金:¥3.00)
```

**DeepSeek:**

```
Balance:$25.50
```

**SiliconFlow:**

```
Balance:¥88.88 (充值:¥88.00, 赠送:¥0.88)
```

### 颜色编码

所有平台统一的颜色编码规则：

- 🟢 **绿色**: 余额充足
- 🟡 **黄色**: 余额警告
- 🔴 **红色**: 余额不足

具体阈值根据平台和货币类型调整。

## 错误处理

当 API 调用失败时，显示格式：

- `Balance:Error` - 通用错误
- `Balance:Error(timeout)` - 超时错误
- `Balance:Unavailable` - 账户不可用

## 扩展新平台

要添加新平台支持：

1. 在 `platforms/` 目录创建新的平台实现文件
2. 继承 `BasePlatform` 类
3. 实现必要的抽象方法
4. 在 `platforms/manager.py` 中注册新平台
5. 更新本文档

示例实现可参考现有的 `gaccode.py`、`kimi.py`、`deepseek.py` 文件。
