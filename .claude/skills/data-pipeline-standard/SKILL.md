---
name: "data-pipeline-standard"
description: "Guides standardized data pipeline implementation including collection, processing, storage, and service layers. Invoke when adding new data sources or reviewing data pipeline code."
---

# Data Pipeline Standard

This skill provides standardized guidelines for implementing data pipelines in the OpenFinance Data Center, covering the complete lifecycle from data collection to service delivery.

## Overview

The data pipeline follows a four-layer architecture:

```
┌─────────────────────────────────────────────────────────────┐
│                    Data Service Layer                        │
│         UnifiedDataService / QuantDataService                │
├─────────────────────────────────────────────────────────────┤
│                    Data Storage Layer                        │
│         PostgreSQL / Redis / Neo4j                           │
├─────────────────────────────────────────────────────────────┤
│                    Data Processing Layer                     │
│         Quality Checker / Validator / Lineage                │
├─────────────────────────────────────────────────────────────┤
│                    Data Collection Layer                     │
│         DataSourceAdapter / Collector / Pipeline             │
└─────────────────────────────────────────────────────────────┘
```

## 1. Data Collection Layer

### 1.1 DataSourceAdapter Interface

All new data sources MUST implement the `DataSourceAdapter` interface:

```python
from openfinance.datacenter.pipeline import DataSourceAdapter, AdapterConfig, AdapterCapability

class MyDataAdapter(DataSourceAdapter[MyDataModel]):
    """Adapter for MyData source."""
    
    def __init__(self, config: AdapterConfig | None = None):
        config = config or AdapterConfig(
            adapter_id="my_data",
            adapter_name="My Data Source",
            source_type="my_data",
            capabilities=[
                AdapterCapability.BATCH,
                AdapterCapability.HISTORICAL,
            ],
        )
        super().__init__(config)
    
    async def _initialize(self) -> None:
        # Initialize connections, sessions, etc.
        pass
    
    async def _close(self) -> None:
        # Release resources
        pass
    
    async def _health_check(self) -> bool:
        # Check if source is healthy
        return True
    
    async def _fetch_batch(self, params: dict[str, Any]) -> list[MyDataModel]:
        # Implement batch data fetching
        return []
```

### 1.2 Required Configuration

Every adapter MUST have:

| Field | Type | Description |
|-------|------|-------------|
| `adapter_id` | str | Unique identifier |
| `adapter_name` | str | Human-readable name |
| `source_type` | str | Data source type |
| `capabilities` | list | Supported capabilities |
| `timeout_seconds` | float | Request timeout |
| `max_retries` | int | Retry attempts |

### 1.3 Pipeline Integration

Use `PipelineBuilder` for complex collection workflows:

```python
from openfinance.datacenter import PipelineBuilder

async def create_collection_pipeline():
    builder = PipelineBuilder("my_data_collection")
    
    pipeline = (builder
        .source("fetch_data", fetch_handler)
        .transform("normalize", normalize_handler)
        .validate("validate", validate_handler)
        .sink("save", save_handler)
        .with_retry(3)
        .with_timeout(300)
        .build())
    
    return pipeline
```

## 2. Data Processing Layer

### 2.1 Data Quality Checking

All data MUST pass quality checks before storage:

```python
from openfinance.datacenter import DataQualityChecker, QualityDimension, QualityRule

checker = DataQualityChecker()

# Add custom rules
checker.add_rule(QualityRule(
    rule_id="my_field_completeness",
    name="My Field Completeness",
    dimension=QualityDimension.COMPLETENESS,
    field_name="my_field",
    threshold=0.95,  # 95% completeness required
))

# Check data
report = checker.check(data, source="my_data", data_type="my_type")
if not report.passed:
    raise DataQualityError(report)
```

### 2.2 Data Validation

Validate data schema and business rules:

```python
from openfinance.datacenter import DataValidator, ValidationRule

validator = DataValidator()

# Add validation rules
validator.add_rule(ValidationRule(
    rule_id="price_positive",
    name="Price Must Be Positive",
    field_name="price",
    rule_type="range",
    params={"min": 0, "exclusive_min": True},
))

# Validate
result = validator.validate(data_record)
if not result.valid:
    raise ValidationError(result.issues)
```

### 2.3 Data Lineage Tracking

Track data lineage for all transformations:

```python
from openfinance.datacenter import LineageTracker

tracker = LineageTracker()

# Record lineage
tracker.record_source("my_data_api", "My Data API")
tracker.record_transform("normalize", "Data Normalization", "my_data_api")
tracker.record_sink("my_table", "My Data Table", "normalize")

# Get lineage
lineage = tracker.get_lineage()
```

## 3. Data Storage Layer

### 3.1 Database Models

Define SQLAlchemy models in `models.py`:

```python
from sqlalchemy import Column, String, Float, DateTime, Integer
from openfinance.datacenter.database import Base

class MyDataModel(Base):
    __tablename__ = "my_data"
    
    id = Column(Integer, primary_key=True)
    code = Column(String(10), nullable=False, index=True)
    name = Column(String(50))
    value = Column(Float)
    collected_at = Column(DateTime, nullable=False)
    
    class Config:
        indexes = [
            ("code", "collected_at"),
        ]
```

### 3.2 Persistence

Use `DataPersistence` for storage operations:

```python
from openfinance.datacenter.persistence import DataPersistence

async def save_data(data: list[dict]):
    persistence = DataPersistence()
    
    # Batch insert with UPSERT
    await persistence.save_batch(
        data=data,
        model_class=MyDataModel,
        conflict_columns=["code", "collected_at"],
    )
```

### 3.3 Storage Requirements

| Requirement | Standard |
|-------------|----------|
| Batch Size | 500 records per batch |
| Upsert Strategy | ON CONFLICT DO UPDATE |
| Index Strategy | Composite indexes on query fields |
| Retention | Configurable per data type |

## 4. Data Service Layer

### 4.1 Service Implementation

Implement data services using `UnifiedDataService`:

```python
from openfinance.datacenter import UnifiedDataService, DataQuery

class MyDataService(UnifiedDataService):
    """Service for My Data."""
    
    async def get_data(self, query: DataQuery) -> list[dict]:
        # Implement data retrieval
        pass
    
    async def get_latest(self, code: str) -> dict | None:
        # Implement latest data retrieval
        pass
    
    async def get_history(
        self,
        code: str,
        start_date: str,
        end_date: str,
    ) -> list[dict]:
        # Implement historical data retrieval
        pass
```

### 4.2 API Endpoints

Expose data via FastAPI routes:

```python
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/my-data", tags=["my-data"])

@router.get("/{code}")
async def get_my_data(code: str):
    service = MyDataService()
    return await service.get_latest(code)

@router.get("/{code}/history")
async def get_history(
    code: str,
    start_date: str,
    end_date: str,
):
    service = MyDataService()
    return await service.get_history(code, start_date, end_date)
```

## 5. Data Model Management

### 5.1 Architecture Principles

Data models follow a layered architecture with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────┐
│                    Business Logic Layer                      │
│         Domain-specific models (quant, graph, market)        │
│         High cohesion by business domain                     │
├─────────────────────────────────────────────────────────────┤
│                    Data Architecture Layer                   │
│         ModelRegistry, ModelTransformer, SchemaManager       │
│         Generic framework, no business logic                 │
├─────────────────────────────────────────────────────────────┤
│                    Data Storage Layer                        │
│         SQLAlchemy ORM models                                │
│         Pure technical implementation                        │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 Model Registry

All models MUST be registered with the central registry:

```python
from openfinance.datacenter.models import ModelRegistry
from openfinance.datacenter.models.framework import register_model

# Method 1: Decorator registration
@register_model(
    category="market",
    model_id="stock_quote",
    orm_model=StockDailyQuoteModel,
    description="Stock daily quotes",
)
class StockQuote(BaseModel):
    code: str
    trade_date: date
    close: float | None = None

# Method 2: Explicit registration
registry = ModelRegistry.get_instance()
registry.register(
    model_class=StockQuote,
    category="market",
    model_id="stock_quote",
    orm_model=StockDailyQuoteModel,
    schema={
        "type": "object",
        "properties": {
            "code": {"type": "string"},
            "trade_date": {"type": "string", "format": "date"},
            "close": {"type": "number"},
        },
        "required": ["code", "trade_date"],
    },
)
```

### 5.3 Model Transformer

Use ModelTransformer for type conversions:

```python
from openfinance.datacenter.models import ModelTransformer, FieldMapping

# Create transformer with field mappings
transformer = ModelTransformer(
    source_type=StockQuote,  # Pydantic model
    target_type=StockDailyQuoteModel,  # ORM model
    field_mappings=[
        FieldMapping("code", "code"),
        FieldMapping("trade_date", "trade_date"),
        FieldMapping("close", "close"),
    ],
)

# Transform single object
orm_obj = transformer.transform(pydantic_obj)

# Transform batch
orm_objs = transformer.transform_batch(pydantic_objs)
```

### 5.4 Enumeration Management

All enumerations MUST be defined in `openfinance/models/enums.py`:

```python
from openfinance.models.enums import DataSource, DataType, EntityType

# Use standard enums
source = DataSource.EASTMONEY
data_type = DataType.STOCK_QUOTE

# Get enum values
values = get_enum_values("DataSource")
```

### 5.5 Model-Aware Collection

Use ModelAwareCollector for type-safe collection:

```python
from openfinance.datacenter.models.integration import ModelAwareCollector

class StockQuoteCollector(ModelAwareCollector[StockQuote]):
    def __init__(self):
        super().__init__(model_id="stock_quote", validate=True)
    
    async def _fetch_data(self, params: dict) -> list[dict]:
        # Fetch raw data
        return raw_data

# Usage
collector = StockQuoteCollector()
quotes = await collector.collect({"codes": ["600000"]})
# quotes is list[StockQuote] with validation applied
```

### 5.6 Model-Aware Persistence

Use ModelAwarePersistence for type-safe storage:

```python
from openfinance.datacenter.models.integration import ModelAwarePersistence

persistence = ModelAwarePersistence[StockQuote](
    model_id="stock_quote",
    session=db_session,
)

# Save typed models
count = await persistence.save(quotes, upsert=True)

# Query and return typed models
quotes = await persistence.query(filters={"code": "600000"})
```

### 5.7 Model-Aware Service

Use ModelAwareService for type-safe services:

```python
from openfinance.datacenter.models.integration import ModelAwareService

class StockQuoteService(ModelAwareService[StockQuote]):
    def __init__(self):
        super().__init__(
            model_id="stock_quote",
            cache_enabled=True,
            cache_ttl=300,
        )
    
    async def get_latest(self, code: str) -> StockQuote | None:
        # Implementation returns typed model
        pass
```

### 5.8 Model Registration Checklist

When adding a new model:

- [ ] Define Pydantic model in appropriate domain (`business/quant/`, `business/graph/`, `business/market/`)
- [ ] Define SQLAlchemy ORM model in `datacenter/models.py`
- [ ] Register model with ModelRegistry
- [ ] Configure field mappings if names differ
- [ ] Add JSON Schema for validation
- [ ] Create ModelTransformer if complex conversion needed
- [ ] Add unit tests for model and transformer

## 6. Monitoring and Observability

### 6.1 Metrics Collection

Use `MetricsCollector` for all operations:

```python
from openfinance.datacenter.monitoring import MetricsCollector

collector = MetricsCollector()

# Track collection
with collector.track_collection("my_data", "my_type"):
    data = await adapter.fetch(params)

# Record quality
collector.record_quality(QualityMetrics(
    data_source="my_data",
    data_type="my_type",
    overall_score=report.overall_score,
))
```

### 6.2 Alerting

Configure alerts for critical conditions:

```python
from openfinance.datacenter.monitoring import AlertManager, AlertRule, AlertSeverity

alert_manager = AlertManager()

alert_manager.add_rule(AlertRule(
    rule_id="my_data_failure",
    name="My Data Collection Failure",
    condition="failure_rate > 0.1",
    severity=AlertSeverity.HIGH,
))
```

## 7. Checklist for New Data Source

When adding a new data source, verify:

### Collection
- [ ] DataSourceAdapter implemented
- [ ] AdapterConfig defined
- [ ] Capabilities declared
- [ ] Health check implemented
- [ ] Retry logic configured
- [ ] Rate limiting applied

### Processing
- [ ] Quality rules defined
- [ ] Validation rules defined
- [ ] Lineage tracking enabled
- [ ] Error handling implemented

### Storage
- [ ] Database model defined
- [ ] Indexes created
- [ ] Persistence method implemented
- [ ] Retention policy defined

### Service
- [ ] DataService implemented
- [ ] API endpoints created
- [ ] Caching configured
- [ ] Documentation added

### Monitoring
- [ ] Metrics collected
- [ ] Alerts configured
- [ ] Logging standardized

## 8. File Structure

New data source should follow this structure:

```
backend/openfinance/datacenter/
├── adapters/
│   └── my_data_adapter.py      # DataSourceAdapter implementation
├── models.py                   # Add database model
├── persistence.py              # Add persistence method
├── service/
│   └── my_data_service.py      # DataService implementation
├── pipeline/templates/
│   └── my_data_pipeline.yaml   # Pipeline template
└── api/routes/
    └── my_data.py              # API routes
```

## 9. Common Patterns

### Pattern: Incremental Collection

```python
async def collect_incremental(last_update: datetime):
    adapter = MyDataAdapter()
    await adapter.initialize()
    
    params = {
        "start_time": last_update,
        "end_time": datetime.now(),
    }
    
    data = await adapter.fetch(params)
    
    report = checker.check(data, "my_data", "incremental")
    if not report.passed:
        logger.warning(f"Quality issues: {report.issues}")
    
    await save_data(data)
    return data
```

### Pattern: Parallel Collection

```python
async def collect_parallel(codes: list[str]):
    builder = PipelineBuilder("parallel_collection")
    
    pipeline = (builder
        .parallel("fetch_all", [
            lambda d, c: fetch_code(code)
            for code in codes
        ])
        .transform("merge", merge_results)
        .sink("save", save_all)
        .build())
    
    executor = PipelineExecutor()
    return await executor.execute(pipeline)
```

### Pattern: Streaming Collection

```python
async def collect_streaming():
    adapter = MyDataAdapter()
    await adapter.initialize()
    
    async for batch in adapter.fetch_streaming(params):
        report = checker.check(batch, "my_data", "streaming")
        if report.passed:
            await save_data(batch)
```

## 10. Error Handling Standards

All data operations MUST handle these error types:

| Error Type | Handling |
|------------|----------|
| `ConnectionError` | Retry with exponential backoff |
| `TimeoutError` | Log and retry, alert after max retries |
| `ValidationError` | Log and skip invalid records |
| `QualityError` | Log and optionally quarantine |
| `StorageError` | Retry, alert if persistent |

## 11. Testing Requirements

Every data source MUST have tests:

```python
# tests/test_my_data_adapter.py
import pytest
from openfinance.datacenter.adapters import MyDataAdapter

class TestMyDataAdapter:
    @pytest.mark.asyncio
    async def test_fetch_batch(self):
        adapter = MyDataAdapter()
        await adapter.initialize()
        
        data = await adapter.fetch({"codes": ["600000"]})
        
        assert len(data) > 0
        assert all(d.code == "600000" for d in data)
        
        await adapter.close()
    
    @pytest.mark.asyncio
    async def test_health_check(self):
        adapter = MyDataAdapter()
        await adapter.initialize()
        
        health = await adapter.health_check()
        
        assert health.is_healthy
```

---

Use this skill to:
1. Guide new data source implementation
2. Review existing data pipeline code
3. Validate compliance with standards
4. Identify missing components in data flows
