# 数据中心产品定位与架构设计文档

## 一、产品定位

### 1. 数据采集页面

**核心定位**: 数据源配置中心

**专注功能**:
- 数据源连接参数配置（API密钥、连接地址、认证信息）
- 采集规则配置（采集频率、数据范围、过滤条件）
- 数据格式转换配置（字段映射、数据清洗规则）
- 数据源健康状态监控

**不包含**:
- 任务调度逻辑
- 任务依赖管理
- 流程编排

### 2. 数据任务链路页面

**核心定位**: 数据处理流程编排中心

**专注功能**:
- 处理环节串联与编排
- 调度策略配置
- 任务依赖管理
- 监控告警
- 执行历史追踪

**不包含**:
- 数据源配置细节
- 具体采集逻辑实现

---

## 二、模块边界划分

### 分层架构

```
┌─────────────────────────────────────────────────────────────┐
│                    Application Layer                         │
│              (API endpoints, CLI commands)                   │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    Orchestration Layer                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              DAGEngine (统一任务编排)                 │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │           EnhancedScheduler (统一调度)               │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    Execution Layer                           │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────┐  │
│  │  TaskQueue     │  │  TaskManager   │  │ TriggerManager│  │
│  └────────────────┘  └────────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    Collection Layer                          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              BaseCollector (采集基类)                │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │           DataSourceAdapter (数据源适配器)           │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │           SourceConfigManager (配置管理)             │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    Processing Layer                          │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────┐  │
│  │ EntityRecognizer│  │RelationExtractor│  │DataProcessor │  │
│  └────────────────┘  └────────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    Infrastructure Layer                      │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────┐  │
│  │ TaskMonitor    │  │ Models/ORM     │  │ Config       │  │
│  └────────────────┘  └────────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 模块职责矩阵

| 模块 | 职责 | 依赖 | 对外接口 |
|------|------|------|---------|
| **collector** | 数据采集、数据源适配 | infrastructure | `BaseCollector`, `DataSourceAdapter` |
| **task** | 任务编排、调度、队列管理 | collector, infrastructure | `DAGEngine`, `EnhancedScheduler`, `TaskManager` |
| **processor** | 数据处理、实体识别 | infrastructure | `EntityRecognizer`, `DataProcessor` |
| **config** | 配置管理 | infrastructure | `SourceConfigManager`, `DAGConfigLoader` |

---

## 三、重构计划

### Phase 1: 清理重复代码

#### 1.1 删除重复调度器

**删除**: `collector/core/scheduler.py` 中的 `CollectionScheduler`

**保留**: `task/enhanced_scheduler.py` 中的 `EnhancedScheduler`

#### 1.2 删除重复DAG引擎

**删除**: `task/chain_engine.py` 中的 `TaskChainEngine`

**保留**: `task/dag_engine.py` 中的 `DAGEngine`

#### 1.3 统一任务定义

创建统一的 `TaskDefinition` 模型，替换以下重复定义：
- `CollectionConfig`
- `TaskDefinition` (task模块)
- `CollectionTaskDefinition` (pipeline模块)
- `ScheduleConfig`

### Phase 2: 创建配置管理中心

#### 2.1 数据源配置管理

```python
# config/source_config.py
class SourceConfigManager:
    """数据源配置管理中心"""
    
    async def get_source_config(self, source_id: str) -> SourceConfig:
        """获取数据源配置"""
        pass
    
    async def save_source_config(self, config: SourceConfig) -> str:
        """保存数据源配置"""
        pass
    
    async def test_connection(self, source_id: str) -> ConnectionTestResult:
        """测试数据源连接"""
        pass
    
    async def get_source_health(self, source_id: str) -> SourceHealth:
        """获取数据源健康状态"""
        pass
```

#### 2.2 DAG配置管理

```python
# config/dag_config.py (已存在，需增强)
class DAGConfigManager:
    """DAG配置管理中心"""
    
    async def get_dag_config(self, dag_id: str) -> DAGConfig:
        """获取DAG配置"""
        pass
    
    async def save_dag_config(self, config: DAGConfig) -> str:
        """保存DAG配置"""
        pass
    
    async def validate_dag_config(self, config: DAGConfig) -> ValidationResult:
        """验证DAG配置"""
        pass
```

### Phase 3: 统一监控服务

```python
# monitoring/unified_monitor.py
class UnifiedMonitor:
    """统一监控服务"""
    
    async def record_task_execution(
        self,
        task_id: str,
        status: TaskStatus,
        duration: float,
        error: str | None = None,
    ) -> None:
        """记录任务执行"""
        pass
    
    async def record_collection_result(
        self,
        source_id: str,
        result: CollectionResult,
    ) -> None:
        """记录采集结果"""
        pass
    
    async def create_alert(
        self,
        alert_type: AlertType,
        severity: AlertSeverity,
        message: str,
        source: str,
    ) -> Alert:
        """创建告警"""
        pass
    
    async def get_metrics(
        self,
        metric_type: str,
        time_range: TimeRange,
    ) -> list[Metric]:
        """获取指标"""
        pass
```

---

## 四、接口设计

### 4.1 数据采集接口

```python
# collector/interfaces.py
class ICollectionService(Protocol):
    """数据采集服务接口"""
    
    async def configure_source(
        self,
        source_type: str,
        config: dict[str, Any],
    ) -> SourceConfig:
        """配置数据源"""
        ...
    
    async def test_source(
        self,
        source_id: str,
    ) -> ConnectionTestResult:
        """测试数据源连接"""
        ...
    
    async def get_source_status(
        self,
        source_id: str,
    ) -> SourceStatus:
        """获取数据源状态"""
        ...
    
    async def list_sources(
        self,
        source_type: str | None = None,
    ) -> list[SourceConfig]:
        """列出数据源"""
        ...
```

### 4.2 任务链路接口

```python
# task/interfaces.py
class ITaskOrchestrationService(Protocol):
    """任务编排服务接口"""
    
    async def create_dag(
        self,
        config: DAGConfig,
    ) -> DAG:
        """创建DAG"""
        ...
    
    async def execute_dag(
        self,
        dag_id: str,
        context: dict[str, Any],
    ) -> ExecutionResult:
        """执行DAG"""
        ...
    
    async def schedule_dag(
        self,
        dag_id: str,
        schedule: ScheduleConfig,
    ) -> str:
        """调度DAG"""
        ...
    
    async def get_dag_status(
        self,
        dag_id: str,
    ) -> DAGStatus:
        """获取DAG状态"""
        ...
    
    async def get_execution_logs(
        self,
        dag_id: str,
        execution_id: str | None = None,
    ) -> list[ExecutionLog]:
        """获取执行日志"""
        ...
```

---

## 五、文件结构规划

### 重构后的目录结构

```
datacenter/
├── collector/                    # 数据采集层
│   ├── core/
│   │   ├── base_collector.py    # 采集基类
│   │   ├── batch_processor.py   # 批处理
│   │   └── orchestrator.py      # 采集器编排
│   ├── implementations/          # 具体采集器
│   └── interfaces.py            # 采集服务接口
│
├── task/                         # 任务编排层
│   ├── dag_engine.py            # DAG引擎 (统一)
│   ├── scheduler.py             # 调度器 (统一)
│   ├── manager.py               # 任务管理器
│   ├── queue.py                 # 任务队列
│   ├── trigger.py               # 触发器
│   └── interfaces.py            # 编排服务接口
│
├── processor/                    # 数据处理层
│   ├── entity/                  # 实体识别
│   ├── relation/                # 关系抽取
│   └── interfaces.py            # 处理服务接口
│
├── config/                       # 配置管理层
│   ├── source_config.py         # 数据源配置
│   ├── dag_config.py            # DAG配置
│   ├── dag_loader.py            # 配置加载器
│   └── dag_config.yaml          # DAG配置文件
│
├── monitoring/                   # 监控层
│   ├── unified_monitor.py       # 统一监控
│   ├── alerting.py              # 告警服务
│   └── metrics.py               # 指标收集
│
├── models/                       # 数据模型
│   ├── task.py                  # 任务模型
│   ├── source.py                # 数据源模型
│   └── execution.py             # 执行记录模型
│
└── pipeline/                     # 流水线层 (精简)
    ├── predefined_tasks.py      # 预定义任务
    └── knowledge_graph_integration.py
```

### 删除的文件

| 文件 | 原因 |
|------|------|
| `collector/core/scheduler.py` | 与 `task/scheduler.py` 重复 |
| `task/chain_engine.py` | 与 `task/dag_engine.py` 重复 |
| `pipeline/task_dag_manager.py` | 已删除 |
| `pipeline/builder.py` | 已删除 |
| `pipeline/registry.py` | 已删除 |

---

## 六、实施路径

### 阶段1: 清理重复代码 (1-2天)

1. 删除 `collector/core/scheduler.py`
2. 删除 `task/chain_engine.py`
3. 更新所有引用

### 阶段2: 创建配置管理中心 (2-3天)

1. 创建 `config/source_config.py`
2. 增强 `config/dag_config.py`
3. 创建配置API接口

### 阶段3: 统一监控服务 (1-2天)

1. 创建 `monitoring/unified_monitor.py`
2. 合并 `task/monitoring.py` 和 `pipeline/pipeline_monitor.py`

### 阶段4: 前端重构 (2-3天)

1. 重构数据采集页面，专注于配置
2. 增强任务链路页面，增加节点详情
3. 统一UI风格

### 阶段5: 测试与文档 (2-3天)

1. 编写单元测试
2. 编写集成测试
3. 更新API文档

---

## 七、质量保障

### 测试覆盖率要求

| 模块 | 单元测试覆盖率 | 集成测试 |
|------|---------------|---------|
| collector | ≥ 80% | 必须 |
| task | ≥ 80% | 必须 |
| config | ≥ 90% | 必须 |
| monitoring | ≥ 70% | 可选 |

### 性能指标

| 指标 | 目标值 |
|------|--------|
| DAG配置加载时间 | < 1s |
| 任务调度延迟 | < 100ms |
| 监控指标收集延迟 | < 50ms |
| 告警发送延迟 | < 1s |

---

## 八、风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 删除重复代码导致功能缺失 | 高 | 保留原有测试，确保功能迁移完整 |
| 接口变更影响前端 | 中 | 保持API兼容性，逐步迁移 |
| 配置迁移数据丢失 | 高 | 提供配置迁移脚本，备份原有配置 |
