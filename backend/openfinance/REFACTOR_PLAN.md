# OpenFinance 重构迁移计划

## 一、重构目标

将现有代码按照**数据定义 → 数据抽取 → 数据加工 → 数据服务**的层次重新组织，实现：
- 高内聚低耦合
- 单一职责原则
- 清晰的依赖层次

## 二、新旧目录映射

### 2.1 数据定义层 (domain/)

| 新路径 | 旧路径 | 说明 |
|--------|--------|------|
| `domain/models/` | `models/` | Pydantic领域模型 |
| `domain/metadata/` | `metadata/` | 元数据定义 |
| `domain/schemas/` | `storage/generic_model.py` + `datacenter/models/orm.py` | ORM模型 |

### 2.2 数据抽取层 (extraction/)

| 新路径 | 旧路径 | 说明 |
|--------|--------|------|
| `extraction/collectors/` | `datacenter/collector/` | 数据采集器 |
| `extraction/providers/` | `datacenter/provider/` | 数据提供者 |
| `extraction/sources/` | `metadata/config/data_sources.yaml` | 数据源定义 |

### 2.3 数据加工层 (processing/)

| 新路径 | 旧路径 | 说明 |
|--------|--------|------|
| `processing/entity/` | `datacenter/processor/entity/` | 实体处理 |
| `processing/relation/` | `datacenter/processor/relation/` | 关系处理 |
| `processing/factors/` | `quant/factors/` | 因子计算 |
| `processing/strategy/` | `quant/strategy/` | 策略处理 |
| `processing/backtest/` | `quant/backtest/` | 回测引擎 |

### 2.4 数据服务层 (services/)

| 新路径 | 旧路径 | 说明 |
|--------|--------|------|
| `services/api/` | `api/` | REST API |
| `services/agents/` | `agents/` | AI Agent服务 |
| `services/storage/` | `storage/repository.py` | 存储服务 |
| `services/task/` | `datacenter/task/` | 任务服务 |
| `services/quality/` | `datacenter/quality/` | 质量服务 |

### 2.5 基础设施层 (infrastructure/)

| 新路径 | 旧路径 | 说明 |
|--------|--------|------|
| `infrastructure/logging/` | `core/logging_config.py` | 日志配置 |
| `infrastructure/config/` | `datacenter/config/` | 配置管理 |
| `infrastructure/database/` | `datacenter/database.py` | 数据库连接 |

## 三、迁移阶段

### 阶段1：创建新目录结构（不破坏现有功能）

1. 创建新的顶层目录：`domain/`, `extraction/`, `processing/`, `services/`, `infrastructure/`
2. 在各目录下创建 `__init__.py` 和子目录
3. 创建兼容性导入层，确保旧代码继续工作

### 阶段2：迁移数据定义层

1. 迁移 `models/` → `domain/models/`
2. 迁移 `metadata/` → `domain/metadata/`
3. 整合 `storage/generic_model.py` + `datacenter/models/orm.py` → `domain/schemas/`
4. 更新所有导入路径

### 阶段3：迁移数据抽取层

1. 迁移 `datacenter/collector/` → `extraction/collectors/`
2. 迁移 `datacenter/provider/` → `extraction/providers/`
3. 更新导入路径

### 阶段4：迁移数据加工层

1. 迁移 `datacenter/processor/` → `processing/entity/` + `processing/relation/`
2. 迁移 `quant/factors/` → `processing/factors/`
3. 迁移 `quant/strategy/` → `processing/strategy/`
4. 迁移 `quant/backtest/` → `processing/backtest/`
5. 更新导入路径

### 阶段5：迁移数据服务层

1. 迁移 `api/` → `services/api/`
2. 迁移 `agents/` → `services/agents/`
3. 迁移 `storage/repository.py` → `services/storage/`
4. 迁移 `datacenter/task/` → `services/task/`
5. 迁移 `datacenter/quality/` → `services/quality/`
6. 更新导入路径

### 阶段6：迁移基础设施层

1. 迁移 `core/` → `infrastructure/`
2. 迁移 `datacenter/config/` → `infrastructure/config/`
3. 迁移 `datacenter/database.py` → `infrastructure/database/`
4. 更新导入路径

### 阶段7：清理与验证

1. 删除旧的空目录
2. 删除兼容性导入层
3. 运行完整测试
4. 更新文档

## 四、兼容性策略

在迁移过程中，保留旧的导入路径作为兼容层：

```python
# 旧路径: openfinance/models/__init__.py
# 兼容层代码:
from openfinance.domain.models import *  # 重导出所有内容
import warnings
warnings.warn(
    "Importing from 'openfinance.models' is deprecated. "
    "Use 'openfinance.domain.models' instead.",
    DeprecationWarning,
    stacklevel=2
)
```

## 五、需要删除/整合的重复模块

### 5.1 ORM模型整合

| 模块 | 位置 | 处理方式 |
|------|------|----------|
| `EntityModel` | `datacenter/models/orm.py` | 整合到 `domain/schemas/entity.py` |
| `RelationModel` | `datacenter/models/orm.py` | 整合到 `domain/schemas/relation.py` |
| `FactorDataModel` | `datacenter/models/orm.py` | 整合到 `domain/schemas/factor.py` |
| `GenericEntityModel` | `storage/generic_model.py` | 作为主模型，删除旧模型 |
| `GenericRelationModel` | `storage/generic_model.py` | 作为主模型，删除旧模型 |
| `GenericFactorModel` | `storage/generic_model.py` | 作为主模型，删除旧模型 |
| `GenericStrategyModel` | `storage/generic_model.py` | 作为主模型，删除旧模型 |

### 5.2 引擎整合

| 模块 | 位置 | 处理方式 |
|------|------|----------|
| `EntityEngine` | `engine/entity_engine.py` | 迁移到 `services/storage/` |
| `RelationEngine` | `engine/relation_engine.py` | 迁移到 `services/storage/` |
| `FactorEngine` | `engine/factor_engine.py` | 迁移到 `processing/factors/` |
| `StrategyEngine` | `engine/strategy_engine.py` | 迁移到 `processing/strategy/` |

### 5.3 ADS层处理

`datacenter/ads/` 作为分析数据存储层，保留但重新组织：
- 模型定义 → `domain/models/`
- 服务层 → `services/storage/`
- 仓库层 → `services/storage/`

## 六、风险评估

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 导入路径变更导致运行时错误 | 高 | 使用兼容性导入层，逐步迁移 |
| 循环依赖 | 中 | 重新设计模块边界，使用依赖注入 |
| 测试覆盖不足 | 中 | 迁移前补充关键路径测试 |
| 文档过时 | 低 | 迁移后更新文档 |

## 七、执行时间表

| 阶段 | 预计时间 | 依赖 |
|------|----------|------|
| 阶段1：创建目录结构 | 0.5天 | 无 |
| 阶段2：迁移数据定义层 | 1天 | 阶段1 |
| 阶段3：迁移数据抽取层 | 1天 | 阶段2 |
| 阶段4：迁移数据加工层 | 1.5天 | 阶段3 |
| 阶段5：迁移数据服务层 | 1.5天 | 阶段4 |
| 阶段6：迁移基础设施层 | 0.5天 | 阶段5 |
| 阶段7：清理与验证 | 1天 | 阶段6 |
| **总计** | **7天** | - |

## 八、验证清单

- [ ] 所有API端点正常响应
- [ ] Agent对话功能正常
- [ ] 数据采集任务正常执行
- [ ] 因子计算功能正常
- [ ] 策略回测功能正常
- [ ] 知识图谱查询正常
- [ ] 无循环依赖警告
- [ ] 无废弃导入警告（最终）
