---
name: policy-monitor
description: Monitor and analyze government policies, regulations, and economic indicators. Invoke when user asks about policy changes, regulatory updates, government announcements, or policy impact on markets and sectors.
---

# Policy Monitor

Monitor and analyze government policies, regulations, and their market impact.

## 数据服务接口调用

本技能使用数据中心提供的数据服务接口获取政策分析数据。所有接口需要认证。

### 获取政策分析数据

```bash
curl -X GET "http://localhost:8000/api/analysis/policy" \
  -H "X-API-Key: $DATASERVICE_API_KEY" \
  -H "Content-Type: application/json"
```

**参数说明：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| category | string | 否 | 政策类别 (宏观经济/货币政策/产业政策) |
| limit | integer | 否 | 返回数量 (默认10, 最大100) |

**响应字段说明：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| policy_id | string | 政策ID |
| title | string | 政策标题 |
| summary | string | 政策摘要 |
| issuer | string | 发布机构 |
| category | string | 政策类别 |
| impact_level | string | 影响级别 (high/medium/low) |
| affected_sectors | array | 受影响行业 |
| affected_stocks | array | 受影响股票 |
| sentiment | string | 情绪倾向 (positive/negative/neutral) |
| publish_date | string | 发布日期 |

**响应示例：**
```json
{
  "success": true,
  "data": [
    {
      "policy_id": "POL001",
      "title": "国务院发布稳增长政策措施",
      "summary": "国务院常务会议部署稳经济一揽子政策措施",
      "issuer": "国务院",
      "category": "宏观经济",
      "impact_level": "high",
      "affected_sectors": ["基建", "房地产", "消费"],
      "affected_stocks": ["600000", "000001", "601318"],
      "sentiment": "positive"
    }
  ],
  "request_id": "req_abc123"
}
```

### 错误处理

| 错误码 | 说明 | 处理建议 |
|--------|------|----------|
| AUTHENTICATION_REQUIRED | 认证失败 | 检查API Key是否正确 |
| PERMISSION_DENIED | 权限不足 | 确认用户有 read:analysis 权限 |
| RATE_LIMIT_EXCEEDED | 请求频率超限 | 等待后重试 |

## 脚本调用方式

**注意**: 脚本需要从 backend 目录运行，使用完整相对路径。

```bash
python openfinance/agents/skills/builtin/policy-monitor/scripts/analyze.py --type monetary
python openfinance/agents/skills/builtin/policy-monitor/scripts/analyze.py --type fiscal
python openfinance/agents/skills/builtin/policy-monitor/scripts/analyze.py --type industrial
```

## 多轮交互机制

### 第一轮：政策类型选择

```
用户: 分析最近的宏观政策
助手: 我将为您分析最近的宏观政策动态。请选择您关注的政策类型：

📋 **政策类型**
1. 💰 货币政策
2. 📊 财政政策
3. 🏭 产业政策

请输入数字或直接说明您的关注点。
```

### 第二轮：政策影响分析

```
📋 **政策影响分析**

**影响程度**: 中等
**影响方向**: 正面

**受益板块**: 银行、房地产、基建
**承压板块**: 高耗能行业

是否继续获取投资建议？
```

### 第三轮：投资建议

```
💼 **投资建议**

**重点关注**: 银行股、基建链
**风险提示**: 政策落地节奏不确定性
```

## Policy Categories

| Category | Key Indicators | Update Frequency |
|----------|---------------|------------------|
| 货币政策 | 利率、存款准备金率 | 实时 |
| 财政政策 | 税收、政府支出 | 季度 |
| 产业政策 | 行业补贴、准入门槛 | 月度 |

## Response Guidelines

1. **Multi-Turn Interaction**: Guide user through policy analysis
2. **Timeliness**: Policy analysis must be current
3. **Objectivity**: Present facts before interpretation
4. **Credibility**: Always cite official sources

## 相关文档

- [数据服务接口文档](/api/datacenter)
- [智能分析服务](/api/analysis-service)
