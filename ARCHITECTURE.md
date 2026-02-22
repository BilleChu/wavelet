# OpenFinance 系统架构

> 版本: 3.1.0 | 更新日期: 2026-02-20

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
    
    subgraph 领域层
        Types[Unified Types]
        Models[Domain Models]
        Metadata[Metadata Registry]
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
    Agent --> Types
    Agent --> PG
    Agent --> RD
    KG --> NK
    Types --> Metadata
```

### 技术栈

| 层级 | 技术 | 版本 |
|------|------|------|
| 前端 | Next.js + React + TypeScript | 14.2.5 / 18.2.0 |
| UI | TailwindCSS + Radix UI | 3.4.1 |
| 图表 | ECharts + ReactFlow | 5.4.3 / 11.10.1 |
| Markdown | Streamdown | 2.3.0 |
| 后端 | FastAPI + Python | 0.109+ / 3.11+ |
| Agent | LangGraph + LangChain | 0.0.20+ |
| 数据库 | PostgreSQL + Redis + Neo4j | 15 / 7 / 5.15 |
| LLM | OpenAI / Anthropic / Qwen | GPT-4 / Claude / Qwen-Plus |

---

## 三、统一类型系统架构（新增）

### 3.1 设计理念

采用 **YAML驱动的类型定义**，实现单一数据源（Single Source of Truth），所有类型定义统一管理，自动生成代码层访问接口。

### 3.2 架构设计

```mermaid
flowchart TB
    subgraph 配置层["📝 配置层 (YAML)"]
        ET_YAML["entity_types.yaml<br/>实体类型定义"]
        RT_YAML["relation_types.yaml<br/>关系类型定义"]
        FT_YAML["factor_types.yaml<br/>因子类型定义"]
        ST_YAML["strategy_types.yaml<br/>策略类型定义"]
        TT_YAML["tool_types.yaml<br/>工具类型定义"]
        DS_YAML["data_sources.yaml<br/>数据源定义"]
    end
    
    subgraph 加载层["⚙️ 加载层"]
        LOADER["MetadataLoader<br/>YAML解析器"]
        REGISTRY["MetadataRegistry<br/>类型注册中心"]
    end
    
    subgraph 访问层["🔌 访问层 (domain/types)"]
        ENTITY["entity.py<br/>EntityType + 辅助函数"]
        RELATION["relation.py<br/>RelationType + 辅助函数"]
        CONVERTER["converters.py<br/>类型转换器"]
    end
    
    subgraph 消费层["📦 消费层"]
        ORM["ORM Models<br/>(datacenter/models/orm.py)"]
        PYDANTIC["Pydantic Models<br/>(domain/models/)"]
        API["API Routes<br/>(api/routes/)"]
    end
    
    ET_YAML --> LOADER
    RT_YAML --> LOADER
    FT_YAML --> LOADER
    ST_YAML --> LOADER
    TT_YAML --> LOADER
    DS_YAML --> LOADER
    
    LOADER --> REGISTRY
    REGISTRY --> ENTITY
    REGISTRY --> RELATION
    REGISTRY --> CONVERTER
    
    ENTITY --> ORM
    ENTITY --> PYDANTIC
    ENTITY --> API
    RELATION --> ORM
    RELATION --> PYDANTIC
    RELATION --> API
```

### 3.3 目录结构

```
domain/
├── metadata/
│   ├── config/                    # YAML配置 (单一数据源)
│   │   ├── entity_types.yaml      # 实体类型定义
│   │   ├── relation_types.yaml    # 关系类型定义
│   │   ├── factor_types.yaml      # 因子类型定义
│   │   ├── strategy_types.yaml    # 策略类型定义
│   │   ├── tool_types.yaml        # 工具类型定义
│   │   └── data_sources.yaml      # 数据源定义
│   ├── loader.py                  # YAML加载器
│   ├── registry.py                # 类型注册中心
│   └── base.py                    # 基础定义类
│
├── types/                         # 类型访问层 (从YAML动态加载)
│   ├── __init__.py                # 统一导出
│   ├── entity.py                  # EntityType + 辅助函数
│   ├── relation.py                # RelationType + 辅助函数
│   └── converters.py              # 类型转换器
│
└── models/                        # Pydantic业务模型
    ├── base.py                    # 基础模型
    ├── agent.py                   # Agent状态模型
    ├── chat.py                    # 聊天消息模型
    ├── tool.py                    # 工具定义模型
    ├── intent.py                  # 意图识别模型
    └── enums.py                   # 枚举定义
```

### 3.4 使用示例

```python
from openfinance.domain.types import (
    EntityType, RelationType,
    get_entity_label, get_relation_label,
    is_valid_entity_type, is_valid_relation_pair,
    to_pydantic, to_orm
)

# 获取实体类型枚举
entity_type = EntityType.COMPANY
print(entity_type.value)  # "company"

# 获取中文标签
label = get_entity_label("company")  # "公司"
relation_label = get_relation_label("belongs_to")  # "属于"

# 验证类型
is_valid = is_valid_entity_type("stock")  # True
is_valid_pair = is_valid_relation_pair("stock", "belongs_to", "industry")  # True

# 获取所有类型
all_entities = get_all_entity_types()
# ['company', 'stock', 'industry', 'concept', 'person', 'event', 'index', 'fund', 'investor', 'sector']
```

### 3.5 YAML配置示例

**entity_types.yaml:**
```yaml
entity_types:
  company:
    display_name: 公司
    category: core
    description: 上市公司或非上市公司实体
    properties:
      code:
        type: string
        required: true
        unique: true
      name:
        type: string
        required: true
    relations:
      belongs_to:
        target_types: [industry, sector]
      has_concept:
        target_types: [concept]
```

---

## 四、智能问答系统架构（更新）

### 4.1 流式响应架构

```mermaid
sequenceDiagram
    participant User as 用户
    participant FE as 前端
    participant API as FastAPI
    participant Loop as AgentLoop
    participant LLM as LLM服务
    participant Tool as 工具执行
    
    User->>FE: 发送问题
    FE->>API: POST /api/chat/stream
    API->>Loop: stream_process()
    
    loop 思考循环
        Loop->>LLM: 发送请求
        LLM-->>Loop: 思考内容
        Loop-->>API: SSE: thinking事件
        API-->>FE: SSE数据流
        FE-->>User: 显示思考过程
        
        alt 需要工具调用
            Loop->>Tool: 执行工具
            Tool-->>Loop: 工具结果
            Loop-->>API: SSE: tool_result事件
            API-->>FE: SSE数据流
            FE-->>User: 显示工具调用
        end
    end
    
    Loop->>LLM: 生成最终回复
    LLM-->>Loop: 流式内容
    Loop-->>API: SSE: content事件
    API-->>FE: SSE数据流
    FE-->>User: Markdown渲染
```

### 4.2 前端组件架构

```mermaid
flowchart TB
    subgraph 页面层
        PAGE["finchat/page.tsx<br/>主页面组件"]
    end
    
    subgraph 服务层
        SVC["FinchatServices<br/>API调用服务"]
    end
    
    subgraph 组件层
        MSG["MessageList<br/>消息列表组件"]
        INPUT["ChatInput<br/>输入框组件"]
        TOOL["ToolCallDisplay<br/>工具调用展示"]
        STREAM["StreamMarkdown<br/>流式Markdown渲染"]
    end
    
    subgraph UI组件
        BTN["Button<br/>按钮组件"]
        BADGE["Badge<br/>徽章组件"]
        CARD["Card<br/>卡片组件"]
    end
    
    PAGE --> MSG
    PAGE --> INPUT
    PAGE --> SVC
    
    MSG --> TOOL
    MSG --> STREAM
    
    TOOL --> BADGE
    TOOL --> CARD
    INPUT --> BTN
```

### 4.3 核心功能

| 功能 | 实现 | 描述 |
|------|------|------|
| 流式Markdown渲染 | Streamdown | 优雅处理不完整的Markdown内容 |
| 工具调用展示 | ToolCallDisplay | 显示工具名称、参数、结果 |
| Stop按钮 | StopButton | 停止生成，调用后端停止接口 |
| 思考过程展示 | ThinkingSteps | 显示AI思考过程 |
| 进度状态 | ProgressStages | 显示处理进度 |

### 4.4 工具调用事件流

```mermaid
sequenceDiagram
    participant Loop as AgentLoop
    participant FE as 前端
    
    Note over Loop: 工具执行前
    Loop->>FE: progress事件 (tool_name, tool_args, tool_call_id)
    FE->>FE: 创建工具调用记录
    
    Note over Loop: 工具执行中
    Loop->>Loop: 执行工具
    
    Note over Loop: 工具执行后
    Loop->>FE: tool_result事件 (tool_name, tool_result, tool_call_id)
    FE->>FE: 更新工具调用结果
    
    Note over FE: 展示工具调用
    FE->>FE: 渲染工具名称、参数、结果
```

---

## 五、数据中心架构

数据中心是系统的数据基础设施，采用三层架构设计：**数据采集层** → **数据加工层** → **数据服务层**。

### 5.1 整体架构

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

### 5.2 ORM模型架构

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
        date list_date
        decimal total_shares
        decimal circulating_shares
        decimal market_cap
        decimal pe_ratio
        decimal pb_ratio
        jsonb properties
    }
    
    StockDailyQuote {
        string code PK
        date trade_date PK
        string name
        decimal open
        decimal close
        decimal high
        decimal low
        decimal pre_close
        decimal change
        decimal change_pct
        bigint volume
        decimal amount
        decimal turnover_rate
        decimal amplitude
        decimal market_cap
        decimal circulating_market_cap
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

## 六、前端架构

### 6.1 页面结构

```
frontend/app/
├── page.tsx           # 首页
├── finchat/           # 智能问答
│   └── page.tsx       # 聊天页面
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

### 6.2 核心组件

```
frontend/components/
├── ui/                        # 基础UI组件
│   ├── button.tsx
│   ├── card.tsx
│   ├── badge.tsx
│   ├── dropdown-menu.tsx
│   └── StreamMarkdown.tsx     # 流式Markdown渲染
│
└── datacenter/                # 数据中心组件
    ├── TaskChainCanvas.tsx    # 任务链路可视化画布
    ├── TaskStatusFlow.tsx     # 任务状态流转图
    ├── TaskChainDetail.tsx    # 任务链路详情
    └── MonitoringDashboard.tsx # 监控仪表盘
```

### 6.3 服务层

```
frontend/services/
├── apiConfig.ts               # API配置
└── FinchatServices/
    └── index.ts               # 聊天服务
        ├── chatService.sendMessage()
        ├── chatService.streamMessage()
        ├── chatService.streamMessageWithCallbacks()
        └── chatService.stopGeneration()
```

---

## 七、部署架构

### Docker Compose 服务

| 服务 | 端口 | 说明 |
|------|------|------|
| backend | 8000 | FastAPI 应用 |
| frontend | 3000/3001 | Next.js 应用 |
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

## 八、设计决策

### 8.1 统一类型系统

**决策：** YAML驱动的类型定义 + 动态加载

**理由：**
- 单一数据源，避免类型定义重复
- 修改YAML后所有消费方自动更新
- 支持丰富的元数据（属性、关系、验证规则）
- 类型安全，提供Enum和验证函数

### 8.2 数据采集架构

**决策：** 配置驱动的采集器 + 编排器模式

**理由：**
- 新增数据源只需配置 YAML
- 统一的重试、限流、错误处理
- 支持并发采集与依赖管理
- 便于扩展和维护

### 8.3 任务调度架构

**决策：** DAG任务链 + 优先级队列

**理由：**
- 支持复杂的任务依赖关系
- 并行执行独立任务
- 优先级调度保证关键任务优先执行
- 断点续传支持

### 8.4 前端技术选择

**决策：** Next.js App Router + Server Components

**理由：**
- 更好的 SEO 支持
- 服务端渲染性能优化
- 流式响应支持

---

## 九、扩展性设计

### 水平扩展

- **无状态 API：** 后端服务可水平扩展
- **Redis 会话：** 支持多实例会话共享
- **数据库读写分离：** PostgreSQL 主从配置

### 插件化扩展

- **采集器插件：** 继承 `BaseCollector` 实现
- **处理器插件：** 继承 `DataProcessor` 实现
- **服务插件：** 在 `marketplace/` 注册新服务
- **类型扩展：** 在YAML配置中添加新类型

---

## 附录：快速参考

### 关键文件路径

| 功能 | 路径 |
|------|------|
| 类型定义配置 | `backend/openfinance/domain/metadata/config/*.yaml` |
| 类型访问层 | `backend/openfinance/domain/types/` |
| 类型加载器 | `backend/openfinance/domain/metadata/loader.py` |
| ORM模型 | `backend/openfinance/datacenter/models/orm.py` |
| Agent循环 | `backend/openfinance/agents/core/loop.py` |
| 聊天API | `backend/openfinance/api/routes/chat.py` |
| 前端聊天页 | `frontend/app/finchat/page.tsx` |
| 流式Markdown | `frontend/components/ui/StreamMarkdown.tsx` |
| 聊天服务 | `frontend/services/FinchatServices/index.ts` |

### 环境变量

```bash
DATABASE_URL=postgresql+asyncpg://openfinance:openfinance@localhost:5432/openfinance
REDIS_URL=redis://localhost:6379/0
DASHSCOPE_API_KEY=sk-...
LLM_MODEL=qwen-plus
```

### 启动命令

```bash
# 后端
cd backend && uvicorn openfinance.api.main:app --host 0.0.0.0 --port 8000 --reload

# 前端
cd frontend && npm run dev

# 数据库
docker run -d --name openfinance-postgres \
  -e POSTGRES_USER=openfinance \
  -e POSTGRES_PASSWORD=openfinance \
  -e POSTGRES_DB=openfinance \
  -p 5432:5432 \
  postgres:15-alpine
```

### API测试示例

```bash
# 健康检查
curl http://localhost:8000/api/health

# 智能问答（流式）
curl -X POST http://localhost:8000/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"query": "浦发银行股价", "user": {"ldap_id": "test"}}'

# 停止生成
curl -X POST http://localhost:8000/api/chat/stop \
  -H "Content-Type: application/json" \
  -d '{"user": {"ldap_id": "test"}}'

# 获取实体类型
curl http://localhost:8000/api/metadata/entity-types
```
