# GAC Code 动态倍率检测系统

## 概述

GAC Code 平台实现了基于API历史记录的动态倍率检测系统，支持实时倍率监控和智能警告机制。

## 核心特性

### 🎯 动态倍率支持
- **支持任意倍率值**: 1x, 2x, 5x, 10x 等动态倍率
- **实时API检测**: 从最近usage记录解析实际倍率
- **时间段备选**: API无数据时回退到时间段判断

### ⚠️ 智能警告系统
- **数据冲突检测**: API显示倍率但时间段判断为非倍率时触发警告
- **视觉警告**: 红色`!Nx`标识提示倍率异常
- **准确性保障**: 以API数据为准，时间段判断为辅

### 🎨 色彩分级显示
- **绿色** (1x): 普通时段
- **黄色** (2-4x): 中等倍率时段
- **紫色** (≥5x): 高倍率时段  
- **红色** (!Nx): 警告状态（数据冲突）

## API接口详情

### 历史记录查询

**端点**: `GET /api/credits/history?limit=10`

**认证**: `Authorization: Bearer {login_token}`

**响应示例**:
```json
{
  "history": [
    {
      "reason": "usage",
      "details": "Model: claude-code - Variable Cost Calculation: (Base(2) + Size(4 per 30KB of 124.9KB)) × Sonnet Multiplier(1) × Time Multiplier(2 - Weekday 2x) = 12 credits.",
      "createdAt": "2025-09-05T08:45:45.709Z"
    }
  ]
}
```

### 倍率解析规则

从`details`字段提取倍率信息:

**正则表达式**: `Time Multiplier\((\d+)\s*-\s*([^)]+)\)`

**解析示例**:
- `Time Multiplier(2 - Weekday 2x)` → 倍率: 2
- `Time Multiplier(5 - High Peak)` → 倍率: 5  
- `Time Multiplier(1 - Regular Hours)` → 倍率: 1

## 检测逻辑

### 优先级机制

1. **API历史记录** (主要)
   - 查询最近5条usage记录
   - 解析最新的倍率信息
   - 数据可靠性最高

2. **时间段判断** (备选)
   - 工作日9-12点，14-18点
   - 默认2倍倍率
   - API无数据时使用

### 实现代码

```python
def _detect_multiplier_status(self) -> Dict[str, Any]:
    """检测倍率状态"""
    # 优先从API获取
    history_data = self.fetch_history_data(5)
    if history_data and "history" in history_data:
        for record in history_data["history"]:
            if record.get("reason") == "usage":
                details = record["details"]
                match = re.search(r'Time Multiplier\((\d+)\s*-\s*([^)]+)\)', details)
                if match:
                    multiplier_value = int(match.group(1))
                    return {
                        "is_active": multiplier_value > 1,
                        "value": multiplier_value,
                        "is_time_based": False,
                        "source": "api"
                    }
    
    # 回退到时间段判断
    if self._is_high_multiplier_hours():
        return {
            "is_active": True,
            "value": 2,  # 默认倍率
            "is_time_based": True, 
            "source": "time"
        }
    
    return {
        "is_active": False,
        "value": 1,
        "is_time_based": True,
        "source": "time"
    }
```

## 显示格式

### 状态栏显示

**正常倍率**:
```
GAC.B:2692/12000 2x (45m30s)
```

**高倍率**:
```
GAC.B:1203/12000 5x (12m42s)  
```

**警告状态**:
```
GAC.B:956/12000 !10x (8m15s)
```

### 颜色编码

| 倍率范围 | 颜色 | 示例 | 说明 |
|---------|------|------|------|
| 1x | 绿色 | - | 普通时段，无倍率加成 |
| 2-4x | 黄色 | `2x` | 中等倍率时段 |
| ≥5x | 紫色 | `5x` | 高倍率时段 |  
| !Nx | 红色 | `!10x` | 警告：API与时间段不匹配 |

## 配置选项

### 双Token认证

GAC Code需要配置两个Token:

```json
{
  "platforms": {
    "gaccode": {
      "api_key": "sk-ant-oat01-...",      // Claude Code API
      "login_token": "eyJhbGciOiJIUzI1..."  // GAC网站API
    }
  }
}
```

### 时间段配置

默认倍率时段（北京时间）:
- **工作日**: 周一至周五
- **时间段**: 09:00-12:00, 14:00-18:00  
- **默认倍率**: 2x

## 故障排除

### 常见问题

**倍率显示为Error**:
1. 检查`login_token`是否配置正确
2. 验证token是否过期
3. 确认网络连接正常

**显示!Nx警告**:
1. 这是正常功能，表示API数据与时间段判断不一致
2. 以API数据为准，时间段判断可能滞后
3. 如果持续出现，检查系统时间是否准确

**无倍率显示**:
1. 确认最近有usage记录
2. 检查API返回数据格式
3. 验证正则表达式匹配

## 自动积分重置功能

### 工单历史查询API

**端点**: `GET /api/tickets?page=1&limit=5`

**认证**: `Authorization: Bearer {login_token}`

**查询参数**:
- `page`: 页码（默认1）
- `limit`: 每页条数（默认10）

**响应示例**:
```json
{
  "tickets": [
    {
      "id": 60313,
      "categoryId": 3,
      "title": "请求重置积分",
      "status": "CLOSED",
      "createdAt": "2025-09-08T03:09:21.883Z",
      "category": {
        "key": "REQUEST_TO_REFILL_CREDIT"
      }
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 5,
    "total": 60,
    "pages": 3
  }
}
```

### 积分重置API

**端点**: `POST /api/tickets`

**认证**: `Authorization: Bearer {login_token}`

**请求体**:
```json
{
  "categoryId": 3,
  "title": "请求重置积分", 
  "description": "",
  "language": "zh"
}
```

**响应示例**:
```json
{
  "message": "工单创建成功",
  "ticket": {
    "id": 60313,
    "status": "CLOSED", 
    "category": {
      "key": "REQUEST_TO_REFILL_CREDIT"
    },
    "messages": [
      {
        "message": "🎉 恭喜！您的积分充值申请已自动批准。您的积分已重置！✅",
        "isFromSupport": true
      }
    ]
  }
}
```

### 自动重置触发条件

系统会在以下情况自动触发积分重置：

1. **余额检查**: 当前积分 ≤ 0
2. **时间限制**: 今日尚未执行过重置操作
3. **API可用性**: `login_token` 有效且网络连接正常

### 重置记录追踪

**API查询方式** (推荐):
- **查询端点**: `GET /api/tickets?page=1&limit=10`
- **过滤条件**: `categoryId=3` 且 `title="请求重置积分"`
- **时间判断**: 检查 `createdAt` 是否为今日
- **重置限制**: 每日最多1次自动重置

**本地缓存方式** (备选):
- **缓存文件**: `cache/gac-refill-cache.json`
- **记录格式**: `{"last_refill_date": "2025-09-08", "refill_count": 1}`
- **缓存TTL**: 24小时（基于日期对比）

## 技术实现

### 关键组件

- **平台类**: `platforms/gaccode.py`
- **API方法**: `fetch_history_data()`, `make_request()`
- **检测方法**: `_detect_multiplier_status()` 
- **显示方法**: `format_balance_display()`
- **重置方法**: `_should_auto_refill()`, `_perform_refill()`
- **查询方法**: `_check_today_refill_from_api()`, `_check_today_refill_from_cache()`

### 缓存策略

- **历史记录缓存**: 5分钟TTL
- **余额缓存**: 5分钟TTL
- **倍率检测**: 每次状态栏刷新时执行

### 频率限制保护

- **GAC API限制**: 所有GAC接口调用间隔最少1分钟
- **智能检测**: 距离上次请求不足1分钟时自动使用缓存
- **防封杀机制**: 严格遵守频率限制，避免账号被官方限制

### 错误处理

- API调用失败时自动回退到时间段判断
- 正则匹配失败时使用默认值
- 网络超时保护（5秒超时）
- 频率限制触发时使用本地缓存备选方案

## 未来扩展

### 计划功能

- [ ] 用户自定义倍率时段配置
- [ ] 历史倍率趋势分析
- [ ] 倍率变化通知机制
- [ ] 多时区支持
- [ ] 倍率统计报告
- [x] 自动积分重置功能
- [ ] 重置成功/失败通知机制

### API增强

- [ ] 支持倍率预测API
- [ ] 实时倍率变更推送
- [ ] 倍率历史统计接口
- [x] 积分重置API集成