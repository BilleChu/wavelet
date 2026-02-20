---
name: tech-indicator
description: Analyze technical indicators and chart patterns for trading signals. Invoke when user asks about stock technical analysis, MA, MACD, RSI, KDJ, Bollinger Bands, support/resistance levels, or trading signals.
---

# Technical Indicator Analysis

Expert analysis of technical indicators, chart patterns, and trading signals.

## 数据服务接口调用

本技能使用数据中心提供的数据服务接口获取技术分析数据。所有接口需要认证。

### 获取技术信号数据

```bash
curl -X GET "http://localhost:19100/api/dataservice/v1/analysis/tech/600000" \
  -H "X-API-Key: your_api_key" \
  -H "Content-Type: application/json"
```

**响应字段说明：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| stock_code | string | 股票代码 |
| stock_name | string | 股票名称 |
| price | float | 当前价格 |
| change_pct | float | 涨跌幅 (%) |
| rsi_14 | float | 14日RSI指标 |
| macd | object | MACD指标 (value, signal, hist) |
| kdj | object | KDJ指标 (k, d, j) |
| boll | object | 布林带 (upper, mid, lower) |
| trend_signal | string | 趋势信号 (bullish/bearish/neutral) |
| support_level | float | 支撑位 |
| resistance_level | float | 阻力位 |
| signals | array | 交易信号列表 |

**响应示例：**
```json
{
  "success": true,
  "data": {
    "stock_code": "600000",
    "stock_name": "浦发银行",
    "price": 8.52,
    "change_pct": 0.95,
    "rsi_14": 58.5,
    "macd": {"value": 0.025, "signal": 0.018, "hist": 0.007},
    "kdj": {"k": 62.3, "d": 55.8, "j": 75.3},
    "boll": {"upper": 8.85, "mid": 8.45, "lower": 8.05},
    "trend_signal": "bullish",
    "support_level": 8.20,
    "resistance_level": 8.80,
    "signals": [
      {"type": "MACD金叉", "strength": "medium", "description": "MACD金叉确认，短期趋势向好"}
    ]
  },
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

### 完整分析

```bash
python scripts/analyze.py --code 600519.SH --days 120
```

## 多轮交互机制

### 第一轮：股票确认

```
用户: 分析贵州茅台的技术指标
助手: 我将为您分析贵州茅台(600519.SH)的技术指标。

📊 **基本信息**
- 股票代码: 600519.SH
- 股票名称: 贵州茅台
- 当前价格: ¥1,680.00
- 今日涨跌: +2.35%

请问您需要哪种技术分析？
1. 📈 趋势分析 (MA, MACD)
2. 🔄 动量分析 (RSI, KDJ)
3. 📊 波动分析 (布林带)
4. 🎯 综合分析 (全部指标)
```

### 第二轮：技术指标展示

```
📊 **技术指标分析**

**趋势指标**
| 指标 | 当前值 | 信号 | 解读 |
|------|--------|------|------|
| MA5 | 1,665 | 多头 | 价格站上5日线 |
| MA20 | 1,645 | 多头 | 价格站上20日线 |
| MACD | 金叉 | 买入 | DIF上穿DEA |

**动量指标**
| 指标 | 当前值 | 信号 | 解读 |
|------|--------|------|------|
| RSI(14) | 62.5 | 中性 | 未超买超卖 |

是否继续分析关键价位？
```

### 第三轮：关键价位与信号

```
🎯 **关键价位分析**

**阻力位**: 1,720 / 1,750 / 1,800
**支撑位**: 1,665 / 1,645 / 1,620

**交易信号**: 🟢 买入
**信号强度**: ⭐⭐⭐⭐ (高)

是否需要更详细的交易策略？
```

### 第四轮：交易策略

```
📝 **交易策略建议**

**短线策略**: 回调至1,665附近入场
**止损价位**: 1,640 (-2.4%)
**目标价位**: 1,750 (+4.2%)

**风险提示**:
⚠️ RSI接近超买区域
⚠️ 关注成交量配合
```

## Indicator Reference

| Indicator | Buy Signal | Sell Signal | Neutral Zone |
|-----------|------------|-------------|--------------|
| RSI(14) | <30 (oversold) | >70 (overbought) | 40-60 |
| MACD | Golden cross | Death cross | Near zero |
| Bollinger | Price at lower band | Price at upper band | Near mid band |
| MA | Price above MA | Price below MA | Consolidating |

## Response Guidelines

1. **Multi-Turn Interaction**: Guide user through analysis steps
2. **Multi-Indicator**: Never rely on a single indicator
3. **Risk Management**: Always provide stop loss levels
4. **Disclaimer**: Technical analysis is probabilistic

## 相关文档

- [数据服务接口文档](/datacenter/docs)
- [智能分析服务](/api/dataservice/v1/services/analysis-service)
