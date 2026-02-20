---
name: intelligent-analysis
description: Comprehensive financial analysis integrating macro, policy, company, and technical perspectives. Invoke when user requests comprehensive investment analysis, multi-dimensional stock evaluation, or cross-domain financial insights.
---

# Intelligent Analysis

Comprehensive multi-dimensional investment analysis integrating macro, policy, fundamental, and technical perspectives.

## 数据服务接口调用

本技能使用数据中心提供的数据服务接口获取分析数据。所有接口需要认证，请在请求头中添加 `X-API-Key` 或 `Authorization: Bearer <token>`。

### 智能分析服务接口

#### 1. 获取宏观经济指标

```bash
curl -X GET "http://localhost:19100/api/dataservice/v1/analysis/macro" \
  -H "X-API-Key: your_api_key" \
  -H "Content-Type: application/json"
```

**参数说明：**
| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| indicators | array | 否 | 指标代码列表 (GDP, CPI, PMI, M2等) |
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
      "current_value": 320000.0,
      "yoy_change": 5.2,
      "trend": "up"
    }
  ],
  "request_id": "req_abc123"
}
```

#### 2. 获取政策分析数据

```bash
curl -X GET "http://localhost:19100/api/dataservice/v1/analysis/policy" \
  -H "X-API-Key: your_api_key"
```

**参数说明：**
| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| category | string | 否 | 政策类别 |
| limit | integer | 否 | 返回数量 (默认10, 最大100) |

#### 3. 获取公司洞察数据

```bash
curl -X GET "http://localhost:19100/api/dataservice/v1/analysis/company/600000" \
  -H "X-API-Key: your_api_key"
```

**响应字段：**
| 字段名 | 类型 | 说明 |
|--------|------|------|
| stock_code | string | 股票代码 |
| stock_name | string | 股票名称 |
| pe_ratio | float | 市盈率 |
| pb_ratio | float | 市净率 |
| roe | float | 净资产收益率 |
| ai_insight | string | AI洞察分析 |
| sentiment | string | 情绪倾向 |
| confidence | float | 置信度 |

#### 4. 获取技术信号数据

```bash
curl -X GET "http://localhost:19100/api/dataservice/v1/analysis/tech/600000" \
  -H "X-API-Key: your_api_key"
```

**响应字段：**
| 字段名 | 类型 | 说明 |
|--------|------|------|
| rsi_14 | float | 14日RSI |
| macd | object | MACD指标 |
| kdj | object | KDJ指标 |
| boll | object | 布林带 |
| trend_signal | string | 趋势信号 |
| signals | array | 交易信号列表 |

### 错误处理

| 错误码 | 说明 | 处理建议 |
|--------|------|----------|
| AUTHENTICATION_REQUIRED | 认证失败 | 检查API Key是否正确 |
| PERMISSION_DENIED | 权限不足 | 确认用户有 read:analysis 权限 |
| RATE_LIMIT_EXCEEDED | 请求频率超限 | 等待后重试 |
| INVALID_PARAMETER | 参数错误 | 检查参数格式 |

## 脚本调用方式

```bash
python scripts/analyze.py --code 600519.SH
```

## 多轮交互机制

### 第一轮：投资标的确认

```
用户: 综合分析贵州茅台的投资价值
助手: 我将为您进行贵州茅台(600519.SH)的综合投资分析。

📊 **基本信息**
- 股票代码: 600519.SH
- 股票名称: 贵州茅台
- 当前价格: ¥1,680.00

**分析框架**
1. 🌍 宏观环境
2. 📋 政策影响
3. 📊 基本面
4. 📈 技术面

是否开始分析？
```

### 第二轮：宏观与政策分析

```
🌍 **宏观环境分析**
- 经济周期: 复苏期
- 政策取向: 宽松

📋 **政策影响评估**
- 影响程度: 中等
- 影响方向: 中性偏正

**宏观结论**: 🟢 偏多 (权重20%)

是否继续基本面分析？
```

### 第三轮：基本面分析

```
📊 **基本面分析**

| 指标 | 数值 | 评价 |
|------|------|------|
| ROE | 31.2% | ⭐⭐⭐⭐⭐ |
| 毛利率 | 91.5% | ⭐⭐⭐⭐⭐ |

**基本面结论**: 🟢 偏多 (权重35%)

是否继续技术面分析？
```

### 第四轮：综合评估

```
🎯 **综合评估**

| 维度 | 信号 | 权重 | 得分 |
|------|------|------|------|
| 宏观 | 🟢 偏多 | 20% | +0.16 |
| 政策 | 🟡 中性 | 20% | 0.00 |
| 基本面 | 🟢 偏多 | 35% | +0.28 |
| 技术面 | 🟢 偏多 | 25% | +0.15 |

**投资建议**: 🟢 买入
**目标价**: ¥1,850 (+10%)
**止损价**: ¥1,600 (-5%)
```

## Signal Integration Matrix

| Domain | Weight | Confidence |
|--------|--------|------------|
| Macro | 20% | High/Med/Low |
| Policy | 20% | High/Med/Low |
| Fundamental | 35% | High/Med/Low |
| Technical | 25% | High/Med/Low |

## Response Guidelines

1. **Multi-Turn Interaction**: Guide user through all dimensions
2. **Comprehensive**: Cover all four analysis dimensions
3. **Integrated**: Synthesize signals
4. **Actionable**: Provide clear recommendations

## 相关文档

- [数据服务接口文档](/datacenter/docs)
- [知识图谱服务](/api/dataservice/v1/services/graph-service)
- [量化分析服务](/api/dataservice/v1/services/quant-service)
