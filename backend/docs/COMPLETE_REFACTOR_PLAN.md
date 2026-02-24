# 数据模型层完整重构方案（包含知识图谱）

## 一、现状全面分析

### 1.1 现有文件结构

```
datacenter/
├── models/
│   ├── orm.py                    # SQLAlchemy ORM 模型（动态加载）
│   ├── analytical/               # ADS 模型和 Repository
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── repository.py
│   │   ├── service.py
│   │   ├── market/
│   │   ├── quant/
│   │   ├── financial/
│   │   ├── sentiment/
│   │   ├── macro/
│   │   ├── meta/
│   │   └── shareholder/
│   └── financial.py             # 财务数据模型（临时创建）

domain/
├── metadata/                   # 元数据加载和注册
│   ├── base.py
│   ├── loader.py
│   ├── registry.py
│   └── config/                # YAML 配置文件
│       ├── entity_types.yaml
│       ├── relation_types.yaml
│       ├── factor_types.yaml
│       └── ...
├── types/                     # 实体和关系类型
│   ├── entity.py               # 实体类型（动态加载）
│   └── relation.py            # 关系类型（动态加载）
└── models/                    # 领域模型
    ├── base.py
    ├── quant.py
    ├── agent.py
    ├── chat.py
    ├── analysis.py
    └── ...
```

### 1.2 主要问题

#### 问题 1：数据结构不一致

| 数据类型 | ORM 模型字段 | ADS 模型字段 | 知识图谱 | 问题 |
|---------|---------------|--------------|---------|------|
| K 线 | `StockDailyQuoteModel.close` | `ADSKLineModel.close` | 无 | 字段名相同，但类型不同 |
| 因子 | `FactorDataModel.factor_value` | `ADSFactorModel.value` | 无 | 字段名不同 |
| 财务指标 | `StockFinancialIndicatorModel.net_profit` | `ADSFinancialIndicatorModel.net_profit` | 无 | 字段名相同，但类型不同 |
| 实体 | 动态加载 | 无 | EntityType | 实体类型与数据模型分离 |
| 关系 | 动态加载 | 无 | RelationType | 关系类型与数据模型分离 |

#### 问题 2：重复定义

```python
# orm.py
class FactorDataModel(Base):
    factor_id: Mapped[str]
    factor_value: Mapped[float]

# analytical/quant/__init__.py
class ADSFactorModel(ADSModel):
    factor_id: str
    value: float
```
同一份数据在两个地方定义。

#### 问题 3：硬编码

```python
# repository.py
query = select(StockDailyQuoteModel).where(
    StockDailyQuoteModel.code == code
)

# service.py
from openfinance.datacenter.models.orm import StockDailyQuoteModel
```
表名和字段名硬编码在代码中，难以维护。

#### 问题 4：职责不清

- `service.py` 既是 Service 层，又包含了 Repository 的逻辑
- `repository.py` 和 `service.py` 功能重叠
- 缺少明确的分层架构

#### 问题 5：知识图谱与数据模型分离

- 实体类型（EntityType）和关系类型（RelationType）动态加载
- 但与 ORM 模型和 ADS 模型没有关联
- 缺少统一的实体和关系管理

#### 问题 6：高耦合

- 各层直接依赖具体实现，违反依赖倒置原则
- 新增数据源需要修改多处代码

---

## 二、重构方案

### 2.1 设计原则

1. **单一数据源**：ORM 模型作为唯一数据源
2. **配置驱动**：通过配置文件管理表结构、字段映射、实体类型、关系类型
3. **类型安全**：使用类型注解和 Pydantic 验证
4. **低耦合**：各层通过接口通信，不直接依赖具体实现
5. **高内聚**：每个模块职责单一明确
6. **分层清晰**：明确区分 Model、Mapper、Repository、Service、Persistence、Knowledge Graph 层
7. **知识图谱集成**：实体和关系类型与数据模型关联

### 2.2 新架构设计

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Configuration Layer                      │
│  ┌─────────────────────────────────────────────────────┐  │
│  │  models_config.yaml (表结构配置)            │  │
│  │  - 表名、字段定义、主键、索引            │  │
│  │  - ORM 模型映射                              │  │
│  │  - ADS 模型映射                              │  │
│  │  - 字段转换规则                              │  │
│  │  - 数据源配置                                │  │
│  └─────────────────────────────────────────────────────┘  │
│  ┌─────────────────────────────────────────────────────┐  │
│  │  entity_config.yaml (实体类型配置)          │  │
│  │  - 实体类型定义                              │  │
│  │  - 实体属性                                  │  │
│  │  - 搜索字段                                  │  │
│  └─────────────────────────────────────────────────────┘  │
│  ┌─────────────────────────────────────────────────────┐  │
│  │  relation_config.yaml (关系类型配置)        │  │
│  │  - 关系类型定义                              │  │
│  │  - 源类型和目标类型                        │  │
│  │  - 关系属性                                  │  │
│  └─────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────────┐
│                    Model Layer                             │
│  ┌─────────────────────────────────────────────────────┐  │
│  │  ORM Models (SQLAlchemy)                     │  │
│  │  - 继承自 Base                              │  │
│  │  - 使用 Mapped, mapped_column                 │  │
│  │  - 定义表结构（__tablename__, __table_args__）│  │
│  │  - 唯一数据源                                │  │
│  └─────────────────────────────────────────────────────┘  │
│  ┌─────────────────────────────────────────────────────┐  │
│  │  ADS Models (Pydantic)                        │  │
│  │  - 继承自 ADSModel                          │  │
│  │  - 字段映射到 ORM 模型                     │  │
│  │  - 提供计算属性和验证方法                 │  │
│  │  - 用于 API 响应和量化分析                 │  │
│  └─────────────────────────────────────────────────────┘  │
│  ┌─────────────────────────────────────────────────────┐  │
│  │  Entity Models (知识图谱实体)                  │  │
│  │  - 继承自 EntityModel                      │  │
│  │  - 定义实体属性                              │  │
│  │  - 关联到数据模型                            │  │
│  └─────────────────────────────────────────────────────┘  │
│  ┌─────────────────────────────────────────────────────┐  │
│  │  Relation Models (知识图谱关系)                │  │
│  │  - 继承自 RelationModel                     │  │
│  │  - 定义关系属性                              │  │
│  │  - 关联到实体和数据模型                      │  │
│  └─────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────────┐
│                  Mapping Layer                           │
│  ┌─────────────────────────────────────────────────────┐  │
│  │  ModelMapper (ORM ↔ ADS 转换)              │  │
│  │  - to_ads(): ORM → ADS                          │  │
│  │  - to_orm(): ADS → ORM                          │  │
│  │  - 使用配置中的字段映射                         │  │
│  │  - 支持类型转换和验证                       │  │
│  └─────────────────────────────────────────────────────┘  │
│  ┌─────────────────────────────────────────────────────┐  │
│  │  EntityMapper (数据模型 ↔ 实体转换)          │  │
│  │  - to_entity(): 数据模型 → 实体                 │  │
│  │  - from_entity(): 实体 → 数据模型             │  │
│  │  - 使用配置中的实体映射                       │  │
│  └─────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────────┐
│                Repository Layer                         │
│  ┌─────────────────────────────────────────────────────┐  │
│  │  BaseRepository (通用 CRUD)                    │  │
│  │  - find_by_id(), find_all(), save()            │  │
│  │  - 使用 ORM 模型，不硬编码 SQL            │  │
│  │  - 支持分页和过滤                           │  │
│  └─────────────────────────────────────────────────────┘  │
│  ┌─────────────────────────────────────────────────────┐  │
│  │  MarketRepository (市场数据)                   │  │
│  │  - find_kline_by_code()                        │  │
│  │  - find_kline_by_date()                        │  │
│  │  - save_kline_batch()                          │  │
│  └─────────────────────────────────────────────────────┘  │
│  ┌─────────────────────────────────────────────────────┐  │
│  │  FinancialRepository (财务数据)                 │  │
│  │  - find_income_statement_by_code()              │  │
│  │  - find_balance_sheet_by_code()                │  │
│  │  - find_dividend_data_by_code()                │  │
│  │  - save_financial_batch()                      │  │
│  └─────────────────────────────────────────────────────┘  │
│  ┌─────────────────────────────────────────────────────┐  │
│  │  EntityRepository (实体数据)                   │  │
│  │  - find_entity_by_id()                        │  │
│  │  - find_entity_by_type()                      │  │
│  │  - save_entity_batch()                          │  │
│  └─────────────────────────────────────────────────────┘  │
│  ┌─────────────────────────────────────────────────────┐  │
│  │  RelationRepository (关系数据)                 │  │
│  │  - find_relation_by_id()                       │  │
│  │  - find_relation_by_entities()                  │  │
│  │  - save_relation_batch()                        │  │
│  └─────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────────┐
│                Service Layer                            │
│  ┌─────────────────────────────────────────────────────┐  │
│  │  BaseService (业务逻辑)                      │  │
│  │  - 组合多个 Repository 操作                     │  │
│  │  - 提供业务方法                             │  │
│  │  - 数据验证和转换                           │  │
│  └─────────────────────────────────────────────────────┘  │
│  ┌─────────────────────────────────────────────────────┐  │
│  │  MarketService (市场数据服务)                   │  │
│  │  - get_stock_quote()                         │  │
│  │  - get_kline_data()                          │  │
│  │  - get_stock_quotes()                         │  │
│  └─────────────────────────────────────────────────────┘  │
│  ┌─────────────────────────────────────────────────────┐  │
│  │  FinancialService (财务数据服务)                 │  │
│  │  - get_financial_indicators()                 │  │
│  │  - get_latest_income_statement()              │  │
│  │  - get_latest_balance_sheet()                │  │
│  │  - get_dividend_history()                    │  │
│  └─────────────────────────────────────────────────────┘  │
│  ┌─────────────────────────────────────────────────────┐  │
│  │  KnowledgeGraphService (知识图谱服务)            │  │
│  │  - get_entity_by_id()                        │  │
│  │  - get_entity_by_type()                      │  │
│  │  - get_relations_by_entity()                  │  │
│  │  - get_entity_graph()                         │  │
│  │  - get_related_entities()                      │  │
│  └─────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────────┐
│                Persistence Layer                        │
│  ┌─────────────────────────────────────────────────────┐  │
│  │  ModelPersistence (基于配置的持久化)            │  │
│  │  - save(table_name, data)                      │  │
│  │  - 使用配置中的表结构和字段映射             │  │
│  │  - 支持 UPSERT/INSERT/UPDATE 模式          │  │
│  │  - 批量处理和重试                           │  │
│  │  - ORM 模型支持                               │  │
│  └─────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 2.3 文件结构

```
datacenter/
├── models/
│   ├── config/
│   │   ├── __init__.py
│   │   ├── models_config.yaml      # 模型配置文件
│   │   ├── entity_config.yaml    # 实体类型配置
│   │   ├── relation_config.yaml   # 关系类型配置
│   │   └── loader.py            # 配置加载器
│   ├── orm/
│   │   ├── __init__.py
│   │   ├── base.py              # Base 类
│   │   ├── market.py            # 市场数据模型
│   │   ├── financial.py          # 财务数据模型
│   │   ├── factor.py            # 因子数据模型
│   │   ├── entity.py            # 实体数据模型
│   │   ├── relation.py          # 关系数据模型
│   │   └── __all__.py
│   ├── ads/
│   │   ├── __init__.py
│   │   ├── base.py              # ADS 基础类
│   │   ├── market.py            # 市场 ADS 模型
│   │   ├── financial.py          # 财务 ADS 模型
│   │   ├── factor.py            # 因子 ADS 模型
│   │   ├── entity.py            # 实体 ADS 模型
│   │   ├── relation.py          # 关系 ADS 模型
│   │   └── __all__.py
│   ├── mapper/
│   │   ├── __init__.py
│   │   ├── base.py              # 映射器基类
│   │   ├── market.py            # 市场数据映射
│   │   ├── financial.py          # 财务数据映射
│   │   ├── factor.py            # 因子数据映射
│   │   ├── entity.py            # 实体数据映射
│   │   ├── relation.py          # 关系数据映射
│   │   └── __all__.py
│   ├── repository/
│   │   ├── __init__.py
│   │   ├── base.py              # Repository 基类
│   │   ├── market.py            # 市场数据 Repository
│   │   ├── financial.py          # 财务数据 Repository
│   │   ├── factor.py            # 因子数据 Repository
│   │   ├── entity.py            # 实体数据 Repository
│   │   ├── relation.py          # 关系数据 Repository
│   │   └── __all__.py
│   └── service/
│       ├── __init__.py
│       ├── base.py              # Service 基类
│       ├── market.py            # 市场数据服务
│       ├── financial.py          # 财务数据服务
│       ├── factor.py            # 因子数据服务
│       ├── knowledge_graph.py    # 知识图谱服务
│       └── __all__.py
└── persistence.py

domain/
├── metadata/
│   ├── __init__.py
│   ├── base.py              # 元数据基类
│   ├── registry.py          # 元数据注册表
│   ├── loader.py            # 元数据加载器
│   └── config/             # 元数据配置文件
│       ├── entity_types.yaml
│       ├── relation_types.yaml
│       ├── factor_types.yaml
│       └── ...
├── types/
│   ├── __init__.py
│   ├── entity.py            # 实体类型（从配置加载）
│   ├── relation.py           # 关系类型（从配置加载）
│   └── __all__.py
└── models/                    # 领域模型（保持不变）
    ├── base.py
    ├── quant.py
    ├── agent.py
    ├── chat.py
    ├── analysis.py
    └── ...
```

---

## 三、详细设计

### 3.1 配置文件 (models_config.yaml)

```yaml
models:
  stock_daily_quote:
    table_name: stock_daily_quote
    schema: openfinance
    primary_key: [code, trade_date]
    orm_model: StockDailyQuoteModel
    ads_model: ADSKLineModel
    entity_model: StockEntity
    field_mappings:
      code:
        orm_field: code
        ads_field: code
        entity_field: code
        type: string
        required: true
      trade_date:
        orm_field: trade_date
        ads_field: trade_date
        entity_field: trade_date
        type: date
        required: true
      open:
        orm_field: open
        ads_field: open
        type: float
      high:
        orm_field: high
        ads_field: high
        type: float
      low:
        orm_field: low
        ads_field: low
        type: float
      close:
        orm_field: close
        ads_field: close
        type: float
      volume:
        orm_field: volume
        ads_field: volume
        type: integer
      amount:
        orm_field: amount
        ads_field: amount
        type: float
      change:
        orm_field: change
        ads_field: change
        type: float
      change_pct:
        orm_field: change_pct
        ads_field: change_pct
        type: float
      turnover_rate:
        orm_field: turnover_rate
        ads_field: turnover_rate
        type: float
      market_cap:
        orm_field: market_cap
        ads_field: market_cap
        type: float

  factor_data:
    table_name: factor_data
    schema: openfinance
    primary_key: [factor_id, code, trade_date]
    orm_model: FactorDataModel
    ads_model: ADSFactorModel
    field_mappings:
      factor_id:
        orm_field: factor_id
        ads_field: factor_id
        type: string
        required: true
      code:
        orm_field: code
        ads_field: code
        type: string
        required: true
      trade_date:
        orm_field: trade_date
        ads_field: trade_date
        type: date
        required: true
      factor_name:
        orm_field: factor_name
        ads_field: factor_name
        type: string
      factor_category:
        orm_field: factor_category
        ads_field: factor_type
        type: string
      factor_value:
        orm_field: factor_value
        ads_field: value
        type: float
      factor_rank:
        orm_field: factor_rank
        ads_field: value_rank
        type: integer
      factor_percentile:
        orm_field: factor_percentile
        ads_field: value_percentile
        type: float

  income_statement:
    table_name: income_statement
    schema: openfinance
    primary_key: [code, report_date, report_period]
    orm_model: IncomeStatementModel
    ads_model: ADSIncomeStatementModel
    entity_model: CompanyEntity
    field_mappings:
      code:
        orm_field: code
        ads_field: code
        entity_field: code
        type: string
        required: true
      report_date:
        orm_field: report_date
        ads_field: report_date
        type: date
        required: true
      report_period:
        orm_field: report_period
        ads_field: period
        type: string
        default: quarterly
      total_revenue:
        orm_field: total_revenue
        ads_field: total_revenue
        type: float
      operating_profit:
        orm_field: operating_profit
        ads_field: operating_profit
        type: float
      net_profit:
        orm_field: net_profit
        ads_field: net_profit
        type: float
      net_profit_attr_parent:
        orm_field: net_profit_attr_parent
        ads_field: net_profit_attr_parent
        type: float
      basic_eps:
        orm_field: basic_eps
        ads_field: basic_eps
        type: float
      diluted_eps:
        orm_field: diluted_eps
        ads_field: diluted_eps
        type: float

  balance_sheet:
    table_name: balance_sheet
    schema: openfinance
    primary_key: [code, report_date, report_period]
    orm_model: BalanceSheetModel
    ads_model: ADSBalanceSheetModel
    entity_model: CompanyEntity
    field_mappings:
      code:
        orm_field: code
        ads_field: code
        entity_field: code
        type: string
        required: true
      report_date:
        orm_field: report_date
        ads_field: report_date
        type: date
        required: true
      report_period:
        orm_field: report_period
        ads_field: period
        type: string
        default: quarterly
      total_assets:
        orm_field: total_assets
        ads_field: total_assets
        type: float
      total_liabilities:
        orm_field: total_liabilities
        ads_field: total_liabilities
        type: float
      total_equity:
        orm_field: total_equity
        ads_field: total_equity
        type: float
      net_equity_attr:
        orm_field: net_equity_attr
        ads_field: net_equity_attr
        type: float
      current_assets:
        orm_field: current_assets
        ads_field: current_assets
        type: float
      current_liabilities:
        orm_field: current_liabilities
        ads_field: current_liabilities
        type: float
      cash:
        orm_field: cash
        ads_field: cash
        type: float
      inventory:
        orm_field: inventory
        ads_field: inventory
        type: float

  dividend_data:
    table_name: dividend_data
    schema: openfinance
    primary_key: [code, report_year]
    orm_model: DividendDataModel
    ads_model: ADSDividendDataModel
    entity_model: CompanyEntity
    field_mappings:
      code:
        orm_field: code
        ads_field: code
        entity_field: code
        type: string
        required: true
      report_year:
        orm_field: report_year
        ads_field: report_year
        type: string
        required: true
      ex_date:
        orm_field: ex_date
        ads_field: ex_date
        type: date
      dividend_per_share:
        orm_field: dividend_per_share
        ads_field: dividend_per_share
        type: float
      bonus_per_share:
        orm_field: bonus_per_share
        ads_field: bonus_per_share
        type: float
      transfer_per_share:
        orm_field: transfer_per_share
        ads_field: transfer_per_share
        type: float
      total_dividend:
        orm_field: total_dividend
        ads_field: total_dividend
        type: float
      dividend_yield:
        orm_field: dividend_yield
        ads_field: dividend_yield
        type: float
```

### 3.2 实体配置文件 (entity_config.yaml)

```yaml
entities:
  company:
    entity_id: company
    display_name: 公司
    description: 上市公司实体
    category: business
    searchable_fields: [code, name, industry]
    list_fields: [code, name, industry, market]
    properties:
      code:
        type: string
        required: true
        description: 股票代码
      name:
        type: string
        required: true
        description: 公司名称
      industry:
        type: string
        description: 所属行业
      market:
        type: string
        description: 所属市场
      list_date:
        type: date
        description: 上市日期
    relations:
      - relation_type: belongs_to
        target_type: industry
        cardinality: many-to-one
      - relation_type: listed_on
        target_type: market
        cardinality: many-to-one

  industry:
    entity_id: industry
    display_name: 行业
    description: 行业分类实体
    category: classification
    searchable_fields: [name, code]
    list_fields: [name, code]
    properties:
      name:
        type: string
        required: true
        description: 行业名称
      code:
        type: string
        required: true
        description: 行业代码
    relations:
      - relation_type: has_member
        target_type: company
        cardinality: one-to-many

  market:
    entity_id: market
    display_name: 市场
    description: 交易市场实体
    category: classification
    searchable_fields: [name, code]
    list_fields: [name, code]
    properties:
      name:
        type: string
        required: true
        description: 市场名称
      code:
        type: string
        required: true
        description: 市场代码
    relations:
      - relation_type: has_member
        target_type: company
        cardinality: one-to-many

  concept:
    entity_id: concept
    display_name: 概念
    description: 概念分类实体
    category: classification
    searchable_fields: [name, code]
    list_fields: [name, code]
    properties:
      name:
        type: string
        required: true
        description: 概念名称
      code:
        type: string
        required: true
        description: 概念代码
    relations:
      - relation_type: has_member
        target_type: company
        cardinality: many-to-many
```

### 3.3 关系配置文件 (relation_config.yaml)

```yaml
relations:
  belongs_to:
    relation_id: belongs_to
    display_name: 属于
    description: 实体归属关系
    source_types: [company]
    target_types: [industry, market]
    cardinality: many-to-one
    properties:
      start_date:
        type: date
        description: 关系开始日期
      end_date:
        type: date
        description: 关系结束日期

  has_member:
    relation_id: has_member
    display_name: 包含
    description: 实体包含关系
    source_types: [industry, concept]
    target_types: [company]
    cardinality: one-to-many
    properties:
      weight:
        type: float
        description: 权重
      rank:
        type: integer
        description: 排序

  competes_with:
    relation_id: competes_with
    display_name: 竞争
    description: 竞争关系
    source_types: [company]
    target_types: [company]
    cardinality: many-to-many
    properties:
      competition_level:
        type: string
        description: 竞争程度

  supplies_to:
    relation_id: supplies_to
    display_name: 供应
    description: 供应链关系
    source_types: [company]
    target_types: [company]
    cardinality: many-to-many
    properties:
      supply_type:
        type: string
        description: 供应类型
```

### 3.4 ORM 模型 (models/orm/entity.py)

```python
"""
Entity and Relation ORM Models

统一的实体和关系 ORM 模型，继承自 Base
"""
from datetime import date
from typing import Optional

from sqlalchemy import (
    String, Date, Numeric, Integer,
    Index, UniqueConstraint, ForeignKey
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from openfinance.infrastructure.database.database import Base


class EntityModel(Base):
    """实体 ORM 模型"""
    __tablename__ = "entity"
    __table_args__ = (
        UniqueConstraint(
            "entity_id", "entity_type",
            name="uq_entity_id_type"
        ),
        {"schema": "openfinance"},
    )
    
    entity_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(20), primary_key=True)
    
    name: Mapped[Optional[String(200)]] = mapped_column(String(200), nullable=True)
    code: Mapped[Optional[String(20)]] = mapped_column(String(20), nullable=True)
    
    properties: Mapped[Optional[dict]] = mapped_column(nullable=True)
    
    created_at: Mapped[date] = mapped_column(Date, default=date.today)
    updated_at: Mapped[date] = mapped_column(Date, default=date.today)


class RelationModel(Base):
    """关系 ORM 模型"""
    __tablename__ = "relation"
    __table_args__ = (
        UniqueConstraint(
            "source_entity_id", "source_entity_type",
            "target_entity_id", "target_entity_type",
            "relation_type",
            name="uq_relation"
        ),
        {"schema": "openfinance"},
    )
    
    source_entity_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    source_entity_type: Mapped[str] = mapped_column(String(20), primary_key=True)
    target_entity_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    target_entity_type: Mapped[str] = mapped_column(String(20), primary_key=True)
    relation_type: Mapped[str] = mapped_column(String(50), primary_key=True)
    
    properties: Mapped[Optional[dict]] = mapped_column(nullable=True)
    
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    
    created_at: Mapped[date] = mapped_column(Date, default=date.today)
    updated_at: Mapped[date] = mapped_column(Date, default=date.today)
```

### 3.5 ADS 实体模型 (models/ads/entity.py)

```python
"""
Entity ADS Models

统一的实体 ADS 模型，继承自 ADSModel
"""
from datetime import date
from typing import Any, Optional

from pydantic import Field

from openfinance.datacenter.models.ads.base import ADSModel


class CompanyEntityModel(ADSModel):
    """公司实体 ADS 模型"""
    
    entity_id: str = Field(..., description="实体 ID")
    entity_type: str = Field(default="company", description="实体类型")
    
    code: str = Field(..., description="股票代码")
    name: str = Field(..., description="公司名称")
    industry: Optional[str] = Field(None, description="所属行业")
    market: Optional[str] = Field(None, description="所属市场")
    list_date: Optional[date] = Field(None, description="上市日期")
    
    properties: dict[str, Any] = Field(
        default_factory=dict,
        description="实体属性"
    )
    
    @property
    def is_listed(self) -> bool:
        """是否已上市"""
        return self.list_date is not None


class IndustryEntityModel(ADSModel):
    """行业实体 ADS 模型"""
    
    entity_id: str = Field(..., description="实体 ID")
    entity_type: str = Field(default="industry", description="实体类型")
    
    name: str = Field(..., description="行业名称")
    code: str = Field(..., description="行业代码")
    
    properties: dict[str, Any] = Field(
        default_factory=dict,
        description="实体属性"
    )


class RelationEntityModel(ADSModel):
    """关系实体 ADS 模型"""
    
    source_entity_id: str = Field(..., description="源实体 ID")
    source_entity_type: str = Field(..., description="源实体类型")
    target_entity_id: str = Field(..., description="目标实体 ID")
    target_entity_type: str = Field(..., description="目标实体类型")
    relation_type: str = Field(..., description="关系类型")
    
    properties: dict[str, Any] = Field(
        default_factory=dict,
        description="关系属性"
    )
    
    start_date: Optional[date] = Field(None, description="关系开始日期")
    end_date: Optional[date] = Field(None, description="关系结束日期")
```

### 3.6 实体映射器 (models/mapper/entity.py)

```python
"""
Entity Mapper

提供数据模型和实体之间的转换
"""
from typing import Any, Type, TypeVar

from openfinance.datacenter.models.orm.entity import EntityModel, RelationModel
from openfinance.datacenter.models.orm.market import StockDailyQuoteModel
from openfinance.datacenter.models.orm.financial import IncomeStatementModel
from openfinance.datacenter.models.ads.entity import (
    CompanyEntityModel,
    IndustryEntityModel,
    RelationEntityModel,
)
from openfinance.datacenter.models.config.loader import ModelConfig

T = TypeVar("T", bound=object)


class EntityMapper:
    """实体映射器"""
    
    @staticmethod
    def stock_to_company_entity(orm_obj: StockDailyQuoteModel) -> CompanyEntityModel:
        """股票 ORM → 公司实体转换"""
        return CompanyEntityModel(
            entity_id=orm_obj.code,
            entity_type="company",
            code=orm_obj.code,
            name=orm_obj.name or "",
            industry=None,
            market=None,
            list_date=None,
            properties={},
        )
    
    @staticmethod
    def financial_to_company_entity(orm_obj: IncomeStatementModel) -> CompanyEntityModel:
        """财务 ORM → 公司实体转换"""
        return CompanyEntityModel(
            entity_id=orm_obj.code,
            entity_type="company",
            code=orm_obj.code,
            name=None,
            industry=None,
            market=None,
            list_date=orm_obj.report_date,
            properties={},
        )
    
    @staticmethod
    def orm_to_relation_entity(orm_obj: RelationModel) -> RelationEntityModel:
        """关系 ORM → 关系实体转换"""
        return RelationEntityModel(
            source_entity_id=orm_obj.source_entity_id,
            source_entity_type=orm_obj.source_entity_type,
            target_entity_id=orm_obj.target_entity_id,
            target_entity_type=orm_obj.target_entity_type,
            relation_type=orm_obj.relation_type,
            properties=orm_obj.properties or {},
            start_date=orm_obj.start_date,
            end_date=orm_obj.end_date,
        )
    
    @staticmethod
    def relation_to_orm(ads_obj: RelationEntityModel) -> RelationModel:
        """关系实体 → 关系 ORM 转换"""
        return RelationModel(
            source_entity_id=ads_obj.source_entity_id,
            source_entity_type=ads_obj.source_entity_type,
            target_entity_id=ads_obj.target_entity_id,
            target_entity_type=ads_obj.target_entity_type,
            relation_type=ads_obj.relation_type,
            properties=ads_obj.properties,
            start_date=ads_obj.start_date,
            end_date=ads_obj.end_date,
        )
```

### 3.7 实体 Repository (models/repository/entity.py)

```python
"""
Entity Repository

提供实体和关系的 CRUD 操作
"""
from typing import Optional, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from openfinance.datacenter.models.orm.entity import EntityModel, RelationModel
from openfinance.datacenter.models.repository.base import BaseRepository


class EntityRepository(BaseRepository[EntityModel]):
    """实体 Repository"""
    
    async def find_by_id(
        self,
        entity_id: str,
        entity_type: str,
    ) -> Optional[EntityModel]:
        """按实体 ID 和类型查询"""
        session = await self._get_session()
        
        query = select(EntityModel).where(
            EntityModel.entity_id == entity_id,
            EntityModel.entity_type == entity_type
        )
        
        result = await session.execute(query)
        records = result.scalars().all()
        
        return records[0] if records else None
    
    async def find_by_type(
        self,
        entity_type: str,
        limit: int = 100,
    ) -> List[EntityModel]:
        """按实体类型查询"""
        session = await self._get_session()
        
        query = select(EntityModel).where(
            EntityModel.entity_type == entity_type
        ).order_by(EntityModel.created_at.desc()).limit(limit)
        
        result = await session.execute(query)
        return result.scalars().all()
    
    async def save_batch(
        self,
        records: List[EntityModel],
    ) -> int:
        """批量保存实体"""
        session = await self._get_session()
        
        for record in records:
            session.merge(record)
        
        await session.commit()
        return len(records)


class RelationRepository(BaseRepository[RelationModel]):
    """关系 Repository"""
    
    async def find_by_source(
        self,
        source_entity_id: str,
        source_entity_type: str,
        limit: int = 100,
    ) -> List[RelationModel]:
        """按源实体查询关系"""
        session = await self._get_session()
        
        query = select(RelationModel).where(
            RelationModel.source_entity_id == source_entity_id,
            RelationModel.source_entity_type == source_entity_type
        ).order_by(RelationModel.created_at.desc()).limit(limit)
        
        result = await session.execute(query)
        return result.scalars().all()
    
    async def find_by_entities(
        self,
        source_entity_id: str,
        source_entity_type: str,
        target_entity_id: str,
        target_entity_type: str,
        relation_type: str,
    ) -> Optional[RelationModel]:
        """按源实体和目标实体查询关系"""
        session = await self._get_session()
        
        query = select(RelationModel).where(
            RelationModel.source_entity_id == source_entity_id,
            RelationModel.source_entity_type == source_entity_type,
            RelationModel.target_entity_id == target_entity_id,
            RelationModel.target_entity_type == target_entity_type,
            RelationModel.relation_type == relation_type,
        )
        
        result = await session.execute(query)
        records = result.scalars().all()
        
        return records[0] if records else None
    
    async def save_batch(
        self,
        records: List[RelationModel],
    ) -> int:
        """批量保存关系"""
        session = await self._get_session()
        
        for record in records:
            session.merge(record)
        
        await session.commit()
        return len(records)
```

### 3.8 知识图谱 Service (models/service/knowledge_graph.py)

```python
"""
Knowledge Graph Service

提供知识图谱的业务逻辑
"""
from typing import Optional, List

from openfinance.datacenter.models.ads.entity import (
    CompanyEntityModel,
    IndustryEntityModel,
    RelationEntityModel,
)
from openfinance.datacenter.models.repository.entity import EntityRepository, RelationRepository
from openfinance.datacenter.models.mapper.entity import EntityMapper


class KnowledgeGraphService:
    """知识图谱服务"""
    
    def __init__(self):
        self._entity_repo = EntityRepository()
        self._relation_repo = RelationRepository()
        self._mapper = EntityMapper()
    
    async def get_entity_by_id(
        self,
        entity_id: str,
        entity_type: str,
    ) -> Optional[CompanyEntityModel | IndustryEntityModel]:
        """获取实体"""
        orm_record = await self._entity_repo.find_by_id(
            entity_id=entity_id,
            entity_type=entity_type,
        )
        
        if not orm_record:
            return None
        
        if entity_type == "company":
            return self._mapper.orm_to_company_entity(orm_record)
        elif entity_type == "industry":
            return IndustryEntityModel(
                entity_id=orm_record.entity_id,
                entity_type="industry",
                name=orm_record.name or "",
                code=orm_record.code or "",
                properties=orm_record.properties or {},
            )
        
        return None
    
    async def get_entities_by_type(
        self,
        entity_type: str,
        limit: int = 100,
    ) -> List[CompanyEntityModel | IndustryEntityModel]:
        """按类型获取实体列表"""
        orm_records = await self._entity_repo.find_by_type(
            entity_type=entity_type,
            limit=limit,
        )
        
        if entity_type == "company":
            return [self._mapper.orm_to_company_entity(r) for r in orm_records]
        elif entity_type == "industry":
            return [
                IndustryEntityModel(
                    entity_id=r.entity_id,
                    entity_type="industry",
                    name=r.name or "",
                    code=r.code or "",
                    properties=r.properties or {},
                )
                for r in orm_records
            ]
        
        return []
    
    async def get_relations_by_entity(
        self,
        source_entity_id: str,
        source_entity_type: str,
        limit: int = 100,
    ) -> List[RelationEntityModel]:
        """获取实体的关系"""
        orm_records = await self._relation_repo.find_by_source(
            source_entity_id=source_entity_id,
            source_entity_type=source_entity_type,
            limit=limit,
        )
        return [self._mapper.orm_to_relation_entity(r) for r in orm_records]
    
    async def get_entity_graph(
        self,
        entity_id: str,
        entity_type: str,
        depth: int = 2,
    ) -> dict:
        """获取实体关系图"""
        result = {
            "entity": await self.get_entity_by_id(entity_id, entity_type),
            "relations": await self.get_relations_by_entity(entity_id, entity_type),
            "depth": depth,
        }
        return result
    
    async def get_related_entities(
        self,
        entity_id: str,
        entity_type: str,
        relation_types: List[str] | None = None,
        limit: int = 100,
    ) -> dict:
        """获取相关实体"""
        relations = await self.get_relations_by_entity(entity_id, entity_type)
        
        if relation_types:
            relations = [r for r in relations if r.relation_type in relation_types]
        
        return {
            "source_entity": await self.get_entity_by_id(entity_id, entity_type),
            "relations": relations[:limit],
        }
    
    async def save_entity(
        self,
        entity: CompanyEntityModel | IndustryEntityModel,
    ) -> int:
        """保存实体"""
        if entity.entity_type == "company":
            orm_record = self._mapper.company_to_orm_entity(entity)
        else:
            return 0
        
        return await self._entity_repo.save_batch([orm_record])
    
    async def save_relation(
        self,
        relation: RelationEntityModel,
    ) -> int:
        """保存关系"""
        orm_record = self._mapper.relation_to_orm(relation)
        return await self._relation_repo.save_batch([orm_record])
```

---

## 四、迁移计划

### 阶段 1：创建新文件结构（3-4 天）
1. 创建 `models/config/` 目录和配置文件
2. 创建 `models/orm/entity.py`
3. 创建 `models/ads/entity.py`
4. 创建 `models/mapper/entity.py`
5. 创建 `models/repository/entity.py`
6. 创建 `models/service/knowledge_graph.py`
7. 创建 `domain/metadata/config/` 目录和配置文件

### 阶段 2：更新现有代码（4-6 天）
1. 更新 `persistence.py` 使用新的配置系统
2. 更新执行器使用新的 Service 层
3. 更新采集器使用新的 Service 层
4. 删除旧的 `analytical/` 目录
5. 更新 `domain/types/` 使用新的配置系统

### 阶段 3：测试验证（2-3 天）
1. 运行现有测试
2. 验证数据完整性
3. 验证知识图谱功能

---

## 五、优势

1. **高内聚**：每个模块职责单一明确
2. **低耦合**：各层通过接口通信，不直接依赖具体实现
3. **配置驱动**：表结构、字段映射、实体类型、关系类型通过配置管理
4. **类型安全**：使用类型注解和 Pydantic 验证
5. **易于扩展**：新增数据源只需添加配置和模型
6. **减少硬编码**：表名、字段名从配置读取
7. **分层清晰**：明确区分 Model、Mapper、Repository、Service、Persistence、Knowledge Graph 层
8. **数据一致性**：ORM 模型作为唯一数据源，ADS 模型用于 API 响应，实体模型用于知识图谱
9. **知识图谱集成**：实体和关系类型与数据模型关联，支持图谱查询

---

**请确认此重构方案是否可以执行？**
