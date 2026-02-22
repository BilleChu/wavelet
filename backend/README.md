# OpenFinance Backend

基于LLM的智能金融分析平台。

## 架构设计

OpenFinance采用分层架构设计，按照**数据定义 → 数据抽取 → 数据加工 → 数据服务**的层次组织：

```
openfinance/
├── domain/              # 数据定义层
│   ├── models/          # Pydantic领域模型
│   ├── metadata/        # 元数据定义（实体类型、关系类型、因子类型等）
│   └── schemas/         # ORM模型
│
├── datacenter/          # 数据中心
│   ├── ads/             # 分析数据存储层
│   ├── collector/       # 数据采集器
│   ├── processor/       # 数据处理器
│   ├── provider/        # 数据提供者
│   ├── task/            # 任务管理
│   └── quality/         # 数据质量
│
├── quant/               # 量化分析
│   ├── factors/         # 因子计算
│   ├── strategy/        # 策略处理
│   ├── backtest/        # 回测引擎
│   └── analytics/       # 分析工具
│
├── agents/              # AI Agent服务
│   ├── core/            # 核心循环
│   ├── skills/          # 技能模块
│   ├── tools/           # 工具集
│   ├── llm/             # LLM客户端
│   └── session/         # 会话管理
│
├── api/                 # REST API
│   ├── routes/          # 路由定义
│   └── middleware/      # 中间件
│
├── services/            # 服务层
│   └── storage/         # 存储服务
│
└── infrastructure/      # 基础设施
    ├── config/          # 配置管理
    ├── database/        # 数据库连接
    └── logging/         # 日志配置
```

## 安装

```bash
cd backend
pip install -e .
```

## 运行

```bash
uvicorn openfinance.api.main:app --host 0.0.0.0 --port 8000 --reload
```

## 核心模块

### 1. 数据定义层 (domain/)

定义金融领域的核心模型和元数据：

- **models/**: Pydantic模型，用于API请求/响应
- **metadata/**: 实体类型、关系类型、因子类型、策略类型等元数据配置
- **schemas/**: SQLAlchemy ORM模型

### 2. 数据中心 (datacenter/)

数据采集、处理和存储：

- **collector/**: 股票行情、财务数据、宏观数据采集器
- **processor/**: 实体识别、关系抽取处理器
- **provider/**: 数据提供者接口
- **task/**: 定时任务和任务链管理

### 3. 量化分析 (quant/)

因子计算和策略回测：

- **factors/**: 技术指标因子（MA、MACD、RSI等）
- **strategy/**: 交易策略实现
- **backtest/**: 回测引擎和绩效评估

### 4. AI Agent (agents/)

智能对话和分析代理：

- **skills/**: 技能模块（巴菲特投资分析、宏观分析等）
- **tools/**: 内置工具（股票查询、公司信息、网络搜索等）
- **core/**: Agent循环处理引擎

## API端点

| 端点 | 描述 |
|------|------|
| `/api/health` | 健康检查 |
| `/api/chat` | 智能对话 |
| `/api/chat/stream` | 流式对话（SSE） |
| `/api/metadata/*` | 元数据查询 |
| `/api/graph/*` | 知识图谱 |
| `/api/quant/*` | 量化分析 |
| `/api/datacenter/*` | 数据中心 |
| `/api/skills` | 技能列表 |

## 环境配置

创建 `.env` 文件：

```env
# LLM配置
DASHSCOPE_API_KEY=your_api_key
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL=qwen-plus

# 数据库配置
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/openfinance
REDIS_URL=redis://localhost:6379/0

# Tavily配置（网络搜索）
TAVILY_API_KEY=your_tavily_key
```

## 技能开发

技能是Agent的扩展能力模块，位于 `agents/skills/builtin/`：

```markdown
---
name: my-skill
description: 技能描述
triggers:
  - 触发关键词
---

# 技能指南

技能的具体实现指南...
```

## 数据源配置

数据源定义在 `domain/metadata/config/data_sources.yaml`：

```yaml
- name: tushare
  type: api
  description: Tushare金融数据接口
  config:
    api_url: https://api.tushare.pro
```

## 测试

```bash
pytest tests/
```

## 许可证

MIT License
