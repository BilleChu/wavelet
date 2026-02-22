---
name: "buffett-investment"
description: "Performs Warren Buffett-style investment analysis with moat, management, and intrinsic value evaluation. Invoke when user asks for value investing analysis, Buffett methodology, or margin of safety assessment."
---

# Buffett Investment Analysis

Warren Buffett-style investment analysis methodology for evaluating potential investment opportunities.

## 数据服务接口调用

本技能使用数据中心提供的数据服务接口获取投资分析数据。所有接口需要认证。

### 获取公司洞察数据

```bash
curl -X GET "http://localhost:8000/api/analysis/company/600519" \
  -H "X-API-Key: $DATASERVICE_API_KEY" \
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
| sentiment | string | 情绪倾向 |
| confidence | float | 置信度 (0-1) |

**响应示例：**
```json
{
  "success": true,
  "data": {
    "stock_code": "600519",
    "stock_name": "贵州茅台",
    "industry": "白酒",
    "pe_ratio": 28.5,
    "pb_ratio": 8.2,
    "roe": 28.5,
    "net_margin": 50.9,
    "ai_insight": "贵州茅台品牌护城河深厚，盈利能力极强...",
    "sentiment": "positive",
    "confidence": 0.92
  },
  "request_id": "req_abc123"
}
```

### 查询知识图谱实体

```bash
curl -X GET "http://localhost:8000/api/graph/entities?keywords=茅台" \
  -H "X-API-Key: $DATASERVICE_API_KEY"
```

### 错误处理

| 错误码 | 说明 | 处理建议 |
|--------|------|----------|
| AUTHENTICATION_REQUIRED | 认证失败 | 检查API Key是否正确 |
| PERMISSION_DENIED | 权限不足 | 确认用户有 read:analysis 权限 |
| COMPANY_NOT_FOUND | 公司不存在 | 检查股票代码是否正确 |

## 脚本调用方式

**注意**: 脚本需要从 backend 目录运行，使用完整相对路径。

### 完整分析

```bash
python openfinance/agents/skills/builtin/buffett-investment/scripts/analyze.py --code 600519.SH --analysis full
```

### 护城河分析

```bash
python openfinance/agents/skills/builtin/buffett-investment/scripts/analyze.py --code 600519.SH --analysis moat
```

### 内在价值计算

```bash
python openfinance/agents/skills/builtin/buffett-investment/scripts/analyze.py --code 600519.SH --analysis intrinsic
```

### 管理层评估

```bash
python openfinance/agents/skills/builtin/buffett-investment/scripts/analyze.py --code 600519.SH --analysis management
```

## 多轮交互机制

### 第一轮：股票确认

```
用户: 用巴菲特的方法分析贵州茅台
助手: 我将使用巴菲特投资方法论为您分析贵州茅台(600519.SH)。

📊 **基本信息**
- 股票代码: 600519.SH
- 股票名称: 贵州茅台
- 当前价格: ¥1,680.00
- 市值: 21,000亿
- 市盈率(PE): 28.5
- 市净率(PB): 8.2

请问您是否继续进行完整的巴菲特式投资分析？
```

### 第二轮：财务数据展示

```
📊 **财务指标分析 (近5年)**

| 指标 | 2023 | 2022 | 2021 | 2020 | 2019 |
|------|------|------|------|------|------|
| ROE | 31.2% | 29.8% | 28.5% | 27.2% | 25.8% |
| 毛利率 | 91.5% | 90.8% | 89.9% | 88.7% | 87.5% |
| 净利率 | 52.3% | 51.2% | 50.1% | 48.8% | 47.2% |
| 资产负债率 | 28.5% | 26.8% | 25.2% | 23.5% | 22.1% |

✅ ROE持续高于15%，符合巴菲特标准
✅ 毛利率稳定在90%左右，定价能力强
✅ 负债率低，财务稳健

是否继续分析护城河和内在价值？
```

### 第三轮：护城河分析

```
🏰 **护城河分析**

| 护城河类型 | 评分 | 分析 |
|-----------|------|------|
| 品牌价值 | ⭐⭐⭐⭐⭐ | 国酒品牌，文化价值极高 |
| 定价权 | ⭐⭐⭐⭐⭐ | 持续提价能力，需求刚性 |
| 转换成本 | ⭐⭐⭐⭐ | 高端社交场景不可替代 |
| 成本优势 | ⭐⭐⭐⭐ | 规模效应，渠道控制力强 |

**护城河综合评分: 4.5/5** (极强)

是否继续计算内在价值？
```

### 第四轮：内在价值计算

```
💰 **内在价值计算**

**DCF模型参数:**
- 自由现金流: 650亿
- 增长率(前5年): 8%
- 增长率(后5年): 4%
- 折现率: 10%

**计算结果:**
- 内在价值: ¥2,100/股
- 当前价格: ¥1,680/股
- 安全边际: 20%

⚠️ 安全边际略低于25%的理想标准

**投资建议: 持有观望**
建议等待价格回调至¥1,575以下再考虑建仓
```

## Core Principles

1. **Circle of Competence**: Only analyze businesses you understand
2. **Moat Analysis**: Identify durable competitive advantages
3. **Management Quality**: Assess leadership integrity and capability
4. **Financial Strength**: Evaluate balance sheet and earnings quality
5. **Margin of Safety**: Buy only at significant discount to intrinsic value

## Analysis Framework

### 1. Business Quality (Moat Analysis)

Evaluate competitive advantages:
- **Brand Power**: Strong brand recognition and pricing power
- **Switching Costs**: High cost for customers to switch
- **Network Effects**: Value increases with more users
- **Cost Advantages**: Structural cost advantages vs competitors
- **Regulatory Moats**: Licenses, patents, regulatory barriers

### 2. Financial Strength

Key metrics to analyze:
- ROE (Return on Equity) > 15%
- ROA (Return on Assets) > 7%
- Debt/Equity < 0.5
- Current Ratio > 1.5

### 3. Management Evaluation

Assess management quality:
- **Capital Allocation**: How they deploy retained earnings
- **Shareholder Friendliness**: Dividends, buybacks, transparency
- **Integrity**: Honest communication, admits mistakes
- **Track Record**: Historical performance and decisions

### 4. Intrinsic Value Calculation

Use Discounted Cash Flow (DCF) method.

### 5. Margin of Safety

Target: > 25% margin of safety

## Key Metrics Reference

| Metric | Good Range | Warning Signs |
|--------|------------|---------------|
| ROE | >15% | <10% or declining |
| Gross Margin | Industry-specific | Declining trend |
| Net Margin | >10% | <5% |
| Debt/Equity | <1.0 | >2.0 |
| Current Ratio | >1.5 | <1.0 |
| P/E | <Industry avg | >Industry avg |

## Response Guidelines

1. **Multi-Turn Interaction**: Always confirm with user before proceeding
2. **Data Accuracy**: Use latest available financial data
3. **Context**: Compare with industry peers and historical trends
4. **Insight**: Go beyond numbers to explain business drivers
5. **Balance**: Present both positive and negative factors

## 相关文档

- [数据服务接口文档](/api/datacenter)
- [智能分析服务](/api/analysis-service)
- [知识图谱服务](/api/graph-service)
