---
name: financial-analysis
description: Analyze company financial statements, metrics, and performance. Invoke when user asks about company earnings, financial ratios, balance sheet analysis, income statement, cash flow, or fundamental analysis of specific stocks.
---

# Financial Analysis

Expert analysis of company financial statements, metrics, and investment recommendations.

## 数据服务接口调用

本技能使用数据中心提供的数据服务接口获取财务分析数据。所有接口需要认证。

### 获取公司洞察数据

```bash
curl -X GET "http://localhost:19100/api/dataservice/v1/analysis/company/600000" \
  -H "X-API-Key: your_api_key" \
  -H "Content-Type: application/json"
```

**响应字段说明：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| stock_code | string | 股票代码 |
| stock_name | string | 股票名称 |
| industry | string | 所属行业 |
| pe_ratio | float | 市盈率 |
| pb_ratio | float | 市净率 |
| roe | float | 净资产收益率 (%) |
| net_margin | float | 净利率 (%) |
| ai_insight | string | AI洞察分析 |
| sentiment | string | 情绪倾向 (positive/negative/neutral) |
| confidence | float | 置信度 (0-1) |

**响应示例：**
```json
{
  "success": true,
  "data": {
    "stock_code": "600000",
    "stock_name": "浦发银行",
    "industry": "银行",
    "pe_ratio": 5.2,
    "pb_ratio": 0.45,
    "roe": 12.5,
    "net_margin": 31.1,
    "ai_insight": "浦发银行作为股份制银行代表，估值处于历史低位...",
    "sentiment": "neutral",
    "confidence": 0.85
  },
  "request_id": "req_abc123"
}
```

### 错误处理

| 错误码 | 说明 | 处理建议 |
|--------|------|----------|
| AUTHENTICATION_REQUIRED | 认证失败 | 检查API Key是否正确 |
| PERMISSION_DENIED | 权限不足 | 确认用户有 read:analysis 权限 |
| COMPANY_NOT_FOUND | 公司不存在 | 检查股票代码是否正确 |

## 脚本调用方式

```bash
python scripts/analyze.py --code 600519.SH
```

## 多轮交互机制

### 第一轮：公司确认

```
用户: 分析贵州茅台的财务状况
助手: 我将为您分析贵州茅台(600519.SH)的财务状况。

📊 **公司概况**
- 股票代码: 600519.SH
- 股票名称: 贵州茅台
- 总市值: 21,000亿

请问您需要哪方面的财务分析？
1. 📈 盈利能力
2. 💰 成长性
3. 🏦 财务健康
4. 🎯 综合分析
```

### 第二轮：核心指标展示

```
📊 **核心财务指标**

| 指标 | 数值 | 评价 |
|------|------|------|
| ROE | 31.2% | ⭐⭐⭐⭐⭐ |
| 毛利率 | 91.5% | ⭐⭐⭐⭐⭐ |
| 净利率 | 52.3% | ⭐⭐⭐⭐⭐ |
| 资产负债率 | 28.5% | ⭐⭐⭐⭐⭐ |

是否继续深入分析？
```

### 第三轮：财务健康评估

```
🏥 **财务健康评估**

| 维度 | 评分 | 评价 |
|------|------|------|
| 盈利能力 | 5.0 | 优秀 |
| 成长性 | 4.5 | 优秀 |
| 偿债能力 | 5.0 | 优秀 |

**综合评分: 4.8/5** - 财务状况健康
```

## Key Metrics Reference

| Metric | Good Range | Warning Signs |
|--------|------------|---------------|
| ROE | >15% | <10% or declining |
| Gross Margin | Industry-specific | Declining trend |
| Net Margin | >10% | <5% |
| Debt/Equity | <1.0 | >2.0 |

## Response Guidelines

1. **Multi-Turn Interaction**: Guide user through analysis steps
2. **Data Accuracy**: Use latest available financial data
3. **Context**: Compare with industry peers
4. **Balance**: Present both positive and negative factors

## 相关文档

- [数据服务接口文档](/datacenter/docs)
- [智能分析服务](/api/dataservice/v1/services/analysis-service)
