# OpenFinance 系统架构

> 版本: 3.0.0 | 更新日期: 2026-02-18

## 一、系统概述

OpenFinance 是基于大语言模型（LLM）的智能金融分析平台，提供智能问答、数据分析、量化研究等核心能力。

### 核心价值

| 能力 | 描述 |
|------|------|
| 智能分析 | 基于LLM的自然语言问答与深度分析 |
| 实时数据 | 多数据源接入，实时行情与财务数据 |
| 量化研究 | 因子研究、策略构建、回测评估 |
| 知识图谱 | 金融实体关系网络，支持关联分析 |

---

## 二、技术架构

### 分层架构

```mermaid
graph TB
    subgraph 表现层
        FE[Next.js 14 Frontend]
    end
    
    subgraph 网关层
        API[FastAPI Gateway]
        WS[WebSocket]
    end
    
    subgraph 业务层
        Agent[Agent Engine]
        Skill[Skills System]
        Quant[Quant Engine]
        KG[Knowledge Graph]
    end
    
    subgraph 数据层
        PG[(PostgreSQL)]
        RD[(Redis)]
        NK[(Neo4j)]
    end
    
    FE --> API
    FE --> WS
    API --> Agent
    API --> Skill
    API --> Quant
    API --> KG
    Agent --> PG
    Agent --> RD
    KG --> NK
```

### 技术栈

| 层级 | 技术 | 版本 |
|------|------|------|
| 前端 | Next.js + React + TypeScript | 14.2.5 / 18.2.0 |
| UI | TailwindCSS + Radix UI | 3.4.1 |
| 图表 | ECharts + ReactFlow | 5.4.3 / 11.10.1 |
| 后端 | FastAPI + Python | 0.109+ / 3.11+ |
| Agent | LangGraph + LangChain | 0.0.20+ |
| 数据库 | PostgreSQL + Redis + Neo4j | 15 / 7 / 5.15 |
| LLM | OpenAI / Anthropic | GPT-4 / Claude |

---

## 三、数据中心架构（核心）

数据中心是系统的数据基础设施，采用三层架构设计：**数据采集层** → **数据加工层** → **数据服务层**。

### 3.1 整体架构

```mermaid
flowchart TB
    subgraph 数据源层["📡 数据源层 (22+ 数据源)"]
        EM[东方财富]
        TS[Tushare]
        AK[AKShare]
        JN[金十数据]
        WN[Wind]
        XQ[雪球]
        SIN[新浪财经]
        EX[交易所]
    end
    
    subgraph 数据采集层["📥 数据采集层"]
        BC[BaseCollector<br/>采集器基类]
        BP[BatchProcessor<br/>批量处理器]
        CO[CollectionOrchestrator<br/>编排器]
        SCH[EnhancedScheduler<br/>调度器]
        TQ[TaskQueue<br/>任务队列]
        
        BC --> BP
        BP --> CO
        CO --> SCH
        SCH --> TQ
    end
    
    subgraph 数据加工层["⚙️ 数据加工层"]
        VAL[DataValidator<br/>数据验证]
        PROC[DataProcessor<br/>数据处理]
        ENT[EntityRecognizer<br/>实体识别]
        REL[RelationExtractor<br/>关系抽取]
        MON[Monitoring<br/>监控告警]
        CHAIN[TaskChainEngine<br/>任务链引擎]
        
        VAL --> PROC
        PROC --> ENT
        ENT --> REL
        PROC --> MON
        CHAIN --> MON
    end
    
    subgraph 数据服务层["📤 数据服务层"]
        ADS[ADSService<br/>分析数据服务]
        MKT[DataMarketplace<br/>数据市场]
        GW[DataGateway<br/>API网关]
        MCP[MCP Server<br/>微服务]
    end
    
    subgraph 存储层["💾 存储层"]
        PG[(PostgreSQL<br/>关系数据)]
        RD[(Redis<br/>缓存)]
        NK[(Neo4j<br/>知识图谱)]
    end
    
    EM --> BC
    TS --> BC
    AK --> BC
    JN --> BC
    WN --> BC
    XQ --> BC
    SIN --> BC
    EX --> BC
    
    TQ --> VAL
    VAL --> PROC
    PROC --> ADS
    PROC --> MKT
    ADS --> GW
    MKT --> GW
    GW --> MCP
    
    PROC --> PG
    PROC --> RD
    REL --> NK
```

### 3.2 数据采集层

#### 架构设计

```mermaid
flowchart LR
    subgraph 配置驱动
        YAML[YAML配置]
        ENV[环境变量]
    end
    
    subgraph 采集器框架
        BASE[BaseCollector]
        BATCH[BatchProcessor]
        ORCH[Orchestrator]
    end
    
    subgraph 调度系统
        SCHED[EnhancedScheduler]
        QUEUE[PriorityQueue]
        TRIGGER[TriggerManager]
    end
    
    subgraph 采集器实现
        MKT[MarketCollectors<br/>市场数据]
        FUND[FundamentalCollectors<br/>基本面]
        NEWS[NewsCollectors<br/>新闻数据]
        MACRO[MacroCollectors<br/>宏观数据]
        DERIV[DerivativeCollectors<br/>衍生品]
        FLOW[MoneyFlowCollectors<br/>资金流向]
    end
    
    YAML --> BASE
    ENV --> BASE
    BASE --> BATCH
    BATCH --> ORCH
    ORCH --> SCHED
    SCHED --> QUEUE
    SCHED --> TRIGGER
    
    QUEUE --> MKT
    QUEUE --> FUND
    QUEUE --> NEWS
    QUEUE --> MACRO
    QUEUE --> DERIV
    QUEUE --> FLOW
```

#### 核心组件

| 组件 | 文件路径 | 功能描述 |
|------|----------|----------|
| **BaseCollector** | `collector/core/base_collector.py` | 采集器抽象基类，定义统一接口 |
| **BatchProcessor** | `collector/core/batch_processor.py` | 泛型批量处理器，支持并发、重试、断点续传 |
| **CollectionOrchestrator** | `collector/core/orchestrator.py` | 多采集器协调编排，健康监控 |
| **EnhancedScheduler** | `task/enhanced_scheduler.py` | 优先级调度、指数退避重试、依赖管理 |
| **TaskQueue** | `task/queue.py` | 优先级任务队列，批量处理 |
| **TaskChainEngine** | `task/chain_engine.py` | DAG任务链编排，并行执行 |

#### 数据源支持

| 数据源 | 类别 | 支持数据类型 |
|--------|------|-------------|
| 东方财富 | market | 行情、K线、资金流向、龙虎榜 |
| Tushare | market | 股票、基金、期货、期权 |
| AKShare | market | 多品种市场数据 |
| 金十数据 | news | 财经快讯、新闻 |
| 新浪财经 | market | 实时行情、财务指标 |
| Wind | professional | 全品种专业数据 |
| 雪球 | social | 社交舆情 |
| 交易所 | official | 官方公告、行情 |

#### 数据类型

```mermaid
mindmap
  root((数据类型))
    市场数据
      股票行情
      指数行情
      ETF行情
      期货期权
      分时数据
    基本面
      财务报表
      财务指标
      估值数据
      股东信息
    资金流向
      主力资金
      北向资金
      龙虎榜
      融资融券
    新闻舆情
      财经新闻
      研报
      公告
      快讯
    宏观经济
      GDP/CPI
      利率汇率
      行业数据
    知识图谱
      公司实体
      行业概念
      关系网络
```

#### API端点

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/datacenter/sources` | GET | 获取数据源列表 |
| `/api/datacenter/data-types` | GET | 获取数据类型列表 |
| `/api/datacenter/tasks` | GET/POST | 任务管理 |
| `/api/datacenter/tasks/{id}/start` | PUT | 启动任务 |
| `/api/datacenter/tasks/{id}/pause` | PUT | 暂停任务 |
| `/api/datacenter/tasks/{id}/retry` | PUT | 重试任务 |
| `/api/datacenter/queue/start` | POST | 启动队列 |
| `/api/datacenter/queue/stop` | POST | 停止队列 |
| `/api/datacenter/init-default-tasks` | POST | 初始化默认任务 |
| `/api/datacenter/companies/preload` | POST | 公司预抓取 |
| `/api/datacenter/stocks/collect` | POST | 股票数据采集 |

### 3.3 数据加工层

#### 架构设计

```mermaid
flowchart TB
    subgraph 数据验证
        DV[DataValidator]
        DQ[DataQualityChecker]
    end
    
    subgraph 数据处理
        DP[DataProcessor]
        FM[FieldMapping]
        CV[Converters]
    end
    
    subgraph 实体识别
        ER[EntityRecognizer]
        LLM_ER[LLM EntityRecognizer]
        DICT[DictionaryMatcher]
    end
    
    subgraph 关系抽取
        RE[RelationExtractor]
        LLM_RE[LLM RelationExtractor]
    end
    
    subgraph 任务链编排
        CE[TaskChainEngine]
        CN[ChainNode]
        DG[DAG Executor]
    end
    
    subgraph 监控告警
        MM[MonitoringManager]
        MR[MetricRecorder]
        AR[AlertManager]
        RULE[AlertRules]
    end
    
    DV --> DP
    DQ --> DP
    DP --> FM
    FM --> CV
    CV --> ER
    ER --> LLM_ER
    ER --> DICT
    ER --> RE
    RE --> LLM_RE
    
    DP --> CE
    CE --> CN
    CN --> DG
    
    DP --> MM
    CE --> MM
    MM --> MR
    MR --> AR
    AR --> RULE
```

#### 核心组件

| 组件 | 文件路径 | 功能描述 |
|------|----------|----------|
| **DataValidator** | `ads/data_validator.py` | 数据完整性、一致性验证 |
| **EntityRecognizer** | `processor/entity/recognizer.py` | 规则+字典实体识别 |
| **LLMEntityRecognizer** | `processor/entity/llm_recognizer.py` | LLM增强实体识别 |
| **RelationExtractor** | `processor/relation/extractor.py` | 关系抽取 |
| **TaskChainEngine** | `task/chain_engine.py` | DAG任务链编排引擎 |
| **MonitoringManager** | `task/monitoring.py` | 任务监控与告警管理 |

#### 监控告警系统

```mermaid
flowchart LR
    subgraph 指标采集
        EXEC[执行指标]
        PERF[性能指标]
        ERR[错误指标]
    end
    
    subgraph 告警规则
        R1[高失败率告警]
        R2[慢执行告警]
        R3[高错误计数]
        R4[任务超时]
    end
    
    subgraph 告警处理
        CREATE[创建告警]
        NOTIFY[通知回调]
        RESOLVE[告警解决]
    end
    
    EXEC --> R1
    PERF --> R2
    ERR --> R3
    EXEC --> R4
    
    R1 --> CREATE
    R2 --> CREATE
    R3 --> CREATE
    R4 --> CREATE
    
    CREATE --> NOTIFY
    NOTIFY --> RESOLVE
```

#### 默认告警规则

| 规则 | 条件 | 严重级别 |
|------|------|----------|
| 高失败率 | 失败率 > 50% | ERROR |
| 慢执行 | 执行时间 > 60s | WARNING |
| 高错误计数 | 错误数 > 10 | ERROR |
| 任务超时 | 超时未完成 | WARNING |

#### API端点

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/datacenter/monitoring/summary` | GET | 监控摘要 |
| `/api/datacenter/monitoring/metrics` | GET | 指标列表 |
| `/api/datacenter/monitoring/alerts` | GET | 告警列表 |
| `/api/datacenter/monitoring/alerts/{id}/resolve` | PUT | 解决告警 |
| `/api/datacenter/monitoring/alerts/{id}/acknowledge` | PUT | 确认告警 |
| `/api/datacenter/monitoring/rules` | POST | 添加告警规则 |
| `/api/datacenter/chains` | GET/POST | 任务链管理 |
| `/api/datacenter/chains/{id}/execute` | POST | 执行任务链 |
| `/api/datacenter/canvas/data` | GET | Canvas可视化数据 |

### 3.4 数据服务层

#### 架构设计

```mermaid
flowchart TB
    subgraph 服务层
        ADS[ADSService<br/>分析数据服务]
        QDS[QuantDataService<br/>量化数据服务]
        GDS[GraphDataService<br/>图谱数据服务]
        UDS[UnifiedDataService<br/>统一服务入口]
    end
    
    subgraph 数据市场
        REG[ServiceRegistry<br/>服务注册中心]
        GW[DataGateway<br/>API网关]
        MON[ServiceMonitor<br/>服务监控]
        VER[VersionManager<br/>版本管理]
    end
    
    subgraph MCP微服务
        STOCK[StockDataService]
        NEWS[NewsDataService]
        GRAPH[GraphDataService]
    end
    
    subgraph 客户端
        API_CLIENT[API Client]
        MCP_CLIENT[MCP Client]
    end
    
    ADS --> UDS
    QDS --> UDS
    GDS --> UDS
    
    UDS --> REG
    REG --> GW
    GW --> MON
    MON --> VER
    
    UDS --> STOCK
    UDS --> NEWS
    UDS --> GRAPH
    
    API_CLIENT --> GW
    MCP_CLIENT --> STOCK
    MCP_CLIENT --> NEWS
    MCP_CLIENT --> GRAPH
```

#### 核心服务

| 服务 | 类别 | 端点 | 功能描述 |
|------|------|------|----------|
| **智能分析服务** | analysis | `/api/dataservice/v1/analysis/*` | 宏观分析、政策分析、公司洞察、技术信号 |
| **知识图谱服务** | graph | `/api/dataservice/v1/graph/*` | 实体查询、关系查询、事件查询、新闻关联 |
| **量化分析服务** | quant | `/api/dataservice/v1/quant/*` | 因子数据、回测结果、交易信号、投资组合 |

#### 服务端点详情

**智能分析服务 (analysis-service)**
| 端点 | 方法 | 描述 |
|------|------|------|
| `/analysis/macro` | GET | 宏观经济分析数据 |
| `/analysis/policy` | GET | 政策分析数据 |
| `/analysis/company/{code}` | GET | 公司洞察数据 |
| `/analysis/tech/{code}` | GET | 技术信号数据 |

**知识图谱服务 (graph-service)**
| 端点 | 方法 | 描述 |
|------|------|------|
| `/graph/entities` | GET | 实体查询（分页） |
| `/graph/relations` | GET | 关系查询 |
| `/graph/events` | GET | 事件查询 |
| `/graph/news` | GET | 新闻关联查询 |

**量化分析服务 (quant-service)**
| 端点 | 方法 | 描述 |
|------|------|------|
| `/quant/factors` | GET | 因子数据查询 |
| `/quant/backtest` | POST | 回测执行 |
| `/quant/signals` | GET | 交易信号查询 |
| `/quant/portfolio` | GET | 投资组合数据 |

#### MCP微服务架构

```mermaid
flowchart LR
    subgraph MCP Server
        CB[CircuitBreaker<br/>熔断器]
        RL[RateLimiter<br/>限流器]
        CACHE[ResponseCache<br/>响应缓存]
    end
    
    subgraph 服务注册
        META[ServiceMetadata]
        HEALTH[HealthChecker]
    end
    
    CLIENT[Client] --> CB
    CB --> RL
    RL --> CACHE
    CACHE --> HANDLER[ServiceHandler]
    
    HANDLER --> META
    HANDLER --> HEALTH
```

---

## 四、数据模型

### 4.1 核心实体模型

```mermaid
erDiagram
    Entity ||--o{ Relation : has
    Entity {
        string entity_id PK
        string entity_type
        string name
        string code
        json properties
        timestamp created_at
        timestamp updated_at
    }
    
    Relation {
        string relation_id PK
        string source_entity_id FK
        string target_entity_id FK
        string relation_type
        float weight
        json properties
    }
```

### 4.2 任务调度模型

```mermaid
erDiagram
    TaskChain ||--o{ ChainNode : contains
    TaskChain ||--o{ ChainEdge : has
    TaskChain ||--o{ DataTarget : outputs
    TaskChain ||--o{ TaskExecution : generates
    
    TaskChain {
        string chain_id PK
        string name
        string status
        json nodes
        json edges
        json context
        timestamp created_at
        timestamp started_at
        timestamp completed_at
    }
    
    TaskExecution {
        string execution_id PK
        string task_id FK
        string chain_id FK
        string status
        timestamp started_at
        timestamp completed_at
        int duration_ms
        json result
        string error
    }
    
    ScheduledTask {
        string task_id PK
        string task_name
        string task_type
        string schedule_type
        bool enabled
        int priority
        timestamp next_run
        timestamp last_run
    }
    
    MonitoringMetric {
        string metric_id PK
        string metric_type
        string metric_name
        decimal metric_value
        json labels
        timestamp recorded_at
    }
    
    Alert {
        string alert_id PK
        string alert_type
        string severity
        string title
        string message
        string status
        timestamp created_at
        timestamp resolved_at
    }
```

### 4.3 股票数据模型

```mermaid
erDiagram
    StockBasic ||--o{ StockDailyQuote : has
    StockBasic ||--o{ StockFinancialIndicator : has
    StockBasic ||--o{ StockMoneyFlow : has
    
    StockBasic {
        string code PK
        string name
        string industry
        string market
        string list_date
    }
    
    StockDailyQuote {
        string code FK
        date trade_date PK
        decimal open
        decimal close
        decimal high
        decimal low
        bigint volume
        decimal amount
    }
    
    StockFinancialIndicator {
        string code FK
        date report_date PK
        decimal pe_ratio
        decimal pb_ratio
        decimal roe
        decimal net_profit_margin
    }
    
    StockMoneyFlow {
        string code FK
        date trade_date PK
        decimal main_net_inflow
        decimal retail_net_inflow
        decimal north_net_inflow
    }
```

---

## 五、前端架构

### 5.1 页面结构

```
frontend/app/
├── page.tsx           # 首页
├── finchat/           # 智能问答
├── analysis/          # 数据分析
├── quant/             # 量化研究
│   └── builder/       # 策略构建器
├── knowledge-graph/   # 知识图谱
├── skills/            # 技能管理
│   └── marketplace/   # 技能市场
├── datacenter/        # 数据中心
│   ├── monitoring/    # 监控仪表盘
│   └── docs/          # 数据文档
└── entities/          # 实体管理
```

### 5.2 数据中心组件

```
frontend/components/datacenter/
├── TaskChainCanvas.tsx    # 任务链路可视化画布
├── TaskStatusFlow.tsx     # 任务状态流转图
├── TaskChainDetail.tsx    # 任务链路详情
└── MonitoringDashboard.tsx # 监控仪表盘
```

### 5.3 组件特性

**TaskChainCanvas** - 基于React Flow的可视化组件
- DAG任务节点拖拽展示
- 数据流向动画
- 实时状态更新
- 数据分发目标展示

**TaskStatusFlow** - 任务状态流转可视化
- 状态分布饼图
- 状态流转图
- 执行进度展示
- 异常状态高亮

**TaskChainDetail** - 任务链路详情面板
- 执行时间线
- 数据分发目标
- 错误日志查看
- 节点重试功能

---

## 六、部署架构

### Docker Compose 服务

| 服务 | 端口 | 说明 |
|------|------|------|
| backend | 19100/5678/9001 | FastAPI 应用 (API/Debug/Metrics) |
| frontend | 3000 | Next.js 应用 |
| postgres | 5432 | PostgreSQL 数据库 |
| redis | 6379 | Redis 缓存 |
| neo4j | 7474/7687 | Neo4j 图数据库 |

### 监控栈（可选）

| 服务 | 端口 | 说明 |
|------|------|------|
| prometheus | 9090 | 指标采集 |
| grafana | 3001 | 可视化面板 |
| loki | 3100 | 日志聚合 |

---

## 七、设计决策

### 7.1 数据采集架构选择

**决策：** 配置驱动的采集器 + 编排器模式

**理由：**
- 新增数据源只需配置 YAML
- 统一的重试、限流、错误处理
- 支持并发采集与依赖管理
- 便于扩展和维护

### 7.2 任务调度架构选择

**决策：** DAG任务链 + 优先级队列

**理由：**
- 支持复杂的任务依赖关系
- 并行执行独立任务
- 优先级调度保证关键任务优先执行
- 断点续传支持

### 7.3 数据服务架构选择

**决策：** MCP微服务 + API网关

**理由：**
- 服务解耦，独立扩展
- 熔断限流保护系统稳定性
- 统一的服务注册与发现
- 版本管理支持平滑升级

### 7.4 前端技术选择

**决策：** Next.js App Router + Server Components

**理由：**
- 更好的 SEO 支持
- 服务端渲染性能优化
- 流式响应支持

---

## 八、扩展性设计

### 水平扩展

- **无状态 API：** 后端服务可水平扩展
- **Redis 会话：** 支持多实例会话共享
- **数据库读写分离：** PostgreSQL 主从配置

### 插件化扩展

- **采集器插件：** 继承 `BaseCollector` 实现
- **处理器插件：** 继承 `DataProcessor` 实现
- **服务插件：** 在 `marketplace/` 注册新服务

---

## 附录：快速参考

### 关键文件路径

| 功能 | 路径 |
|------|------|
| 采集器基类 | `backend/openfinance/datacenter/collector/core/base_collector.py` |
| 批量处理器 | `backend/openfinance/datacenter/collector/core/batch_processor.py` |
| 任务链引擎 | `backend/openfinance/datacenter/task/chain_engine.py` |
| 监控模块 | `backend/openfinance/datacenter/task/monitoring.py` |
| 数据服务 | `backend/openfinance/datacenter/service/data_service.py` |
| 数据市场 | `backend/openfinance/datacenter/marketplace/` |
| 数据模型 | `backend/openfinance/datacenter/models.py` |
| 数据中心API | `backend/openfinance/api/routes/datacenter.py` |
| 扩展API | `backend/openfinance/api/routes/datacenter_extended.py` |
| 前端监控页 | `frontend/app/datacenter/monitoring/page.tsx` |

### 环境变量

```bash
DATABASE_URL=postgresql://openfinance:openfinance@postgres:5432/openfinance
REDIS_URL=redis://redis:6379/0
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=openfinance123
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

### 启动命令

```bash
# 完整环境
docker-compose up -d

# 仅后端
cd backend && uvicorn openfinance.api.main:app --reload --port 19100

# 仅前端
cd frontend && npm run dev

# 初始化默认任务
curl -X POST http://localhost:19100/api/datacenter/init-default-tasks

# 启动任务队列
curl -X POST http://localhost:19100/api/datacenter/queue/start
```

### API测试示例

```bash
# 获取数据中心概览
curl http://localhost:19100/api/datacenter/overview

# 获取数据源列表
curl http://localhost:19100/api/datacenter/sources

# 获取监控摘要
curl http://localhost:19100/api/datacenter/monitoring/summary

# 创建默认任务链
curl -X POST http://localhost:19100/api/datacenter/chains/default

# 获取知识图谱统计
curl http://localhost:19100/api/datacenter/knowledge-graph/stats

# 获取数据服务列表
curl http://localhost:19100/api/dataservice/v1/services
```
