---
name: data-source-loader
description: Data source loading and management skill for querying, configuring, and testing data sources. Invoke when user needs to check data source status, configure new data sources, or test data connections.
triggers:
  - 数据源
  - 数据加载
  - 数据连接
  - 数据源配置
  - 数据源测试
  - data source
---

# Data Source Loader

数据源加载与管理技能，用于查询、配置和测试数据源连接。

## 功能概述

1. **数据源查询**: 查看所有可用数据源及其状态
2. **数据源配置**: 配置新的数据源连接
3. **数据源测试**: 测试数据源连接是否正常
4. **数据加载**: 从指定数据源加载数据

## 数据服务接口

### 1. 获取数据源列表

```bash
curl -X GET "http://localhost:8000/api/datacenter/sources" \
  -H "Content-Type: application/json"
```

**响应示例：**
```json
{
  "sources": [
    {
      "name": "tushare",
      "display_name": "Tushare",
      "category": "reference",
      "source_type": "api",
      "status": "active",
      "data_types": ["stock_quote", "financial_report", "macro_data"]
    }
  ],
  "total": 12
}
```

### 2. 获取数据源详情

```bash
curl -X GET "http://localhost:8000/api/datacenter/sources/{source_name}" \
  -H "Content-Type: application/json"
```

**响应字段：**
| 字段名 | 类型 | 说明 |
|--------|------|------|
| name | string | 数据源名称 |
| display_name | string | 显示名称 |
| category | string | 数据类别 |
| source_type | string | 源类型 (api/database/web/cache/llm) |
| endpoint | string | 端点地址 |
| rate_limit | integer | 请求频率限制 |
| timeout_ms | integer | 超时时间(毫秒) |
| data_types | array | 支持的数据类型 |
| status | string | 状态 (active/inactive/error) |

### 3. 测试数据源连接

```bash
curl -X POST "http://localhost:8000/api/datacenter/sources/{source_name}/test" \
  -H "Content-Type: application/json"
```

**响应示例：**
```json
{
  "success": true,
  "latency_ms": 156,
  "message": "Connection successful"
}
```

### 4. 从数据源加载数据

```bash
curl -X POST "http://localhost:8000/api/datacenter/load" \
  -H "Content-Type: application/json" \
  -d '{
    "source": "tushare",
    "data_type": "stock_quote",
    "params": {
      "code": "600000.SH",
      "start_date": "2024-01-01",
      "end_date": "2024-12-31"
    }
  }'
```

## 可用数据源

| 数据源 | 类型 | 支持数据类型 |
|--------|------|--------------|
| eastmoney | api | stock_quote, fund_quote, index_quote, financial_report, news |
| tushare | api | stock_quote, index_quote, financial_report, macro_data, factor_data |
| akshare | api | stock_quote, fund_quote, bond_quote, futures_quote, options_quote |
| sina_finance | api | news, announcement, research_report |
| cls | api | news, flash_news |
| national_bureau | web | gdp, cpi, ppi, pmi, industrial_production |
| world_bank | api | global_gdp, inflation, trade_data |
| postgres_local | database | stock_daily, stock_basic, factor_data, knowledge_graph |
| redis_cache | cache | cache, session, realtime_quote |

## 使用示例

### 示例1：查询数据源状态

```
用户: 查看所有数据源状态
助手: 我来为您查询所有数据源的状态。

📊 **数据源状态概览**

| 数据源 | 类型 | 状态 | 延迟 |
|--------|------|------|------|
| 东方财富 | api | ✅ 正常 | 45ms |
| Tushare | api | ✅ 正常 | 120ms |
| AKShare | api | ✅ 正常 | 85ms |
| 新浪财经 | api | ✅ 正常 | 32ms |
| 本地数据库 | database | ✅ 正常 | 5ms |
| Redis缓存 | cache | ✅ 正常 | 2ms |

共 12 个数据源，10 个正常，2 个未配置。
```

### 示例2：测试数据源连接

```
用户: 测试Tushare数据源连接
助手: 正在测试 Tushare 数据源连接...

🔍 **连接测试结果**

- 数据源: Tushare
- 端点: https://api.tushare.pro
- 状态: ✅ 连接成功
- 延迟: 156ms
- 可用数据类型: stock_quote, financial_report, macro_data

连接正常，可以正常使用。
```

### 示例3：从数据源加载数据

```
用户: 从Tushare加载浦发银行的股票行情数据
助手: 正在从 Tushare 加载浦发银行(600000.SH)的股票行情数据...

📈 **数据加载结果**

- 数据源: Tushare
- 股票: 浦发银行 (600000.SH)
- 数据类型: stock_quote
- 时间范围: 2024-01-01 ~ 2024-12-31
- 记录数: 242 条

**最新行情**
- 日期: 2024-12-20
- 收盘价: 8.52
- 涨跌幅: +1.2%
- 成交量: 125,000手

数据已加载完成，是否需要进一步分析？
```

## 错误处理

| 错误码 | 说明 | 处理建议 |
|--------|------|----------|
| SOURCE_NOT_FOUND | 数据源不存在 | 检查数据源名称是否正确 |
| CONNECTION_FAILED | 连接失败 | 检查网络连接和端点地址 |
| AUTHENTICATION_ERROR | 认证失败 | 检查API密钥或令牌配置 |
| RATE_LIMIT_EXCEEDED | 请求频率超限 | 等待后重试或升级配额 |
| TIMEOUT | 请求超时 | 增加超时时间或检查网络 |
| INVALID_PARAMS | 参数错误 | 检查请求参数格式 |

## 配置指南

### 配置新数据源

在 `domain/metadata/config/data_sources.yaml` 中添加：

```yaml
new_source:
  display_name: 新数据源
  category: reference
  description: 数据源描述
  version: "1.0.0"
  source_type: api
  endpoint: https://api.example.com
  auth_type: api_key
  rate_limit: 100
  timeout_ms: 10000
  data_types:
    - stock_quote
    - financial_report
```

### 环境变量配置

```env
# Tushare配置
TUSHARE_TOKEN=your_token

# OpenAI配置
OPENAI_API_KEY=your_key

# 数据库配置
DATABASE_URL=postgresql://user:pass@localhost:5432/db
```

## 脚本调用

**注意**: 脚本需要从 backend 目录运行，使用完整相对路径。

```bash
python openfinance/agents/skills/builtin/data-source-loader/scripts/load_data.py --source tushare --type stock_quote --code 600000.SH
```

## Response Guidelines

1. **状态优先**: 首先确认数据源状态
2. **错误友好**: 提供清晰的错误信息和解决建议
3. **性能透明**: 显示延迟和加载时间
4. **数据验证**: 验证加载的数据完整性
