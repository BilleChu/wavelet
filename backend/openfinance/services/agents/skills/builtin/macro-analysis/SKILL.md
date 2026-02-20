---
name: macro-analysis
description: Analyze global macroeconomic data and trends. Invoke when user asks about GDP, CPI, PMI, M2, interest rates, economic indicators, or macroeconomic trends and forecasts.
---

# Macroeconomic Analysis

Expert analysis of global macroeconomic data, trends, and investment implications.

## 数据服务接口调用

本技能使用数据中心提供的数据服务接口获取宏观经济数据。所有接口需要认证。

### 获取宏观经济指标

```bash
curl -X GET "http://localhost:19100/api/dataservice/v1/analysis/macro" \
  -H "X-API-Key: your_api_key" \
  -H "Content-Type: application/json"
```

**参数说明：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| indicators | array | 否 | 指标代码列表 (GDP, CPI, PMI, M2, PPI, UNEMPLOYMENT) |
| start_date | string | 否 | 开始日期 (YYYY-MM-DD) |
| end_date | string | 否 | 结束日期 (YYYY-MM-DD) |

**响应示例：**
```json
{
  "success": true,
  "data": [
    {
      "code": "GDP",
      "name": "国内生产总值",
      "name_en": "GDP",
      "category": "经济增长",
      "unit": "亿元",
      "current_value": 320000.0,
      "previous_value": 310000.0,
      "yoy_change": 5.2,
      "mom_change": 1.2,
      "trend": "up"
    }
  ],
  "request_id": "req_abc123"
}
```

### 获取政策分析数据

```bash
curl -X GET "http://localhost:19100/api/dataservice/v1/analysis/policy?limit=10" \
  -H "X-API-Key: your_api_key"
```

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
| sentiment | string | 情绪倾向 |

### 错误处理

| 错误码 | 说明 | 处理建议 |
|--------|------|----------|
| AUTHENTICATION_REQUIRED | 认证失败 | 检查API Key是否正确 |
| PERMISSION_DENIED | 权限不足 | 确认用户有 read:analysis 权限 |
| RATE_LIMIT_EXCEEDED | 请求频率超限 | 等待后重试 |

## 脚本调用方式

### 完整分析

```bash
python scripts/analyze.py --country CN --analysis full
```

### 指标分析

```bash
python scripts/analyze.py --country CN --analysis indicators
```

### 经济周期分析

```bash
python scripts/analyze.py --country CN --analysis cycle
```

### 政策影响分析

```bash
python scripts/analyze.py --country CN --analysis policy
```

## 多轮交互机制

### 第一轮：确认分析范围

```
用户: 分析当前宏观经济形势
助手: 我将为您分析当前宏观经济形势。请选择您关注的重点：

📊 **可选分析维度**
1. 🇨🇳 中国经济 (GDP, CPI, PMI, M2等)
2. 🇺🇸 美国经济 (GDP, 非农, 美联储政策)
3. 🌏 全球经济 (主要经济体对比)
4. 📈 资产影响 (股市、债市、商品)

请输入数字或直接说明您的关注点。
```

### 第二轮：核心指标展示

```
📊 **中国宏观经济核心指标**

| 指标 | 当前值 | 前值 | 同比变化 | 趋势 |
|------|--------|------|----------|------|
| GDP增速 | 5.2% | 4.9% | +0.3% | ⬆️ |
| CPI | 0.1% | -0.2% | +0.3% | ⬆️ |
| PPI | -2.7% | -3.0% | +0.3% | ⬆️ |
| PMI(制造业) | 49.5 | 49.2 | +0.3 | ⬆️ |
| M2增速 | 9.7% | 10.0% | -0.3% | ⬇️ |

**核心观点**: 经济温和复苏，通胀低位企稳

是否继续深入分析某个指标？
```

### 第三轮：趋势分析

```
📈 **GDP增速趋势分析**

**近期走势**: 温和复苏
**驱动因素**: 消费复苏、出口回暖
**政策展望**: 财政货币政策持续发力

是否继续分析对市场的影响？
```

### 第四轮：投资建议

```
💼 **投资影响与建议**

**受益板块**: 基建、银行、消费
**承压板块**: 房地产、部分制造业

**资产配置建议**:
| 资产 | 建议 | 理由 |
|------|------|------|
| 股票 | 增配 | 估值低位，盈利改善 |
| 债券 | 中性 | 收益率已处低位 |

**风险提示**: 外部需求不确定性
```

## Indicator Reference

| 指标 | 含义 | 发布频率 | 市场关注点 |
|------|------|----------|-----------|
| GDP | 国内生产总值 | 季度 | 经济增速 |
| CPI | 消费者物价指数 | 月度 | 通胀水平 |
| PPI | 生产者物价指数 | 月度 | 工业通胀 |
| PMI | 采购经理人指数 | 月度 | 经济景气度 |
| M2 | 广义货币供应量 | 月度 | 流动性 |

## Response Guidelines

1. **Multi-Turn Interaction**: Guide user through analysis steps
2. **Be Data-Driven**: Always reference specific numbers
3. **Be Forward-Looking**: Provide outlook, not just history
4. **Be Actionable**: Give clear investment implications

## 相关文档

- [数据服务接口文档](/datacenter/docs)
- [智能分析服务](/api/dataservice/v1/services/analysis-service)
