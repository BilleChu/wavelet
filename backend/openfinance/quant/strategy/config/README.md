# 强势股策略配置文档

## 概述

本策略系统采用**配置驱动**的设计模式，所有策略参数均通过YAML配置文件定义，实现了策略与代码的解耦，便于管理和调整。

## 配置文件结构

### 配置文件位置
```
wavelet/backend/openfinance/quant/strategy/config/
├── strong_stock.yaml          # 强势股多因子策略
└── rsi_kdj_momentum.yaml      # RSI+KDJ动量策略
```

### 配置文件格式

每个策略配置文件包含以下主要部分：

#### 1. 基本信息
```yaml
strategy_id: strategy_strong_stock    # 策略唯一标识
name: 强势股多因子策略                  # 策略名称
code: strong_stock                    # 策略代码
display_name: Strong Stock Multi-Factor Strategy
description: 策略描述
strategy_type: multi_factor           # 策略类型
version: "1.0.0"                      # 版本号
author: system                        # 作者
tags: [momentum, relative_strength]   # 标签
status: active                        # 状态
```

#### 2. 因子配置
```yaml
factors:
  - factor_id: factor_momentum        # 因子ID
    name: 动量因子                      # 因子名称
    weight: 0.30                       # 因子权重
    enabled: true                      # 是否启用
    parameters:                        # 因子参数
      period: 20
    description: 因子描述
```

#### 3. 组合配置
```yaml
portfolio:
  max_positions: 30              # 最大持仓数量
  position_size: 0.02            # 单只股票仓位
  weight_method: equal_weight    # 权重方法
  rebalance_freq: weekly         # 调仓频率
```

#### 4. 风险管理
```yaml
risk_management:
  stop_loss: -0.08              # 止损线 (-8%)
  take_profit: 0.20             # 止盈线 (+20%)
  max_position_weight: 0.10     # 单只股票最大权重
  min_position_weight: 0.01     # 单只股票最小权重
```

#### 5. 信号生成
```yaml
signal_generation:
  min_signal_threshold: 0.5     # 最小信号阈值
  min_factors_required: 2       # 最少需要的因子数
  normalization_method: zscore  # 标准化方法
```

#### 6. 回测配置
```yaml
backtest:
  initial_capital: 1000000      # 初始资金
  commission: 0.0003            # 佣金率
  slippage: 0.0001              # 滑点
  benchmark: "000300"           # 基准指数
  risk_free_rate: 0.03          # 无风险利率
```

#### 7. 股票池配置
```yaml
universe:
  min_market_cap: 5000000000    # 最小市值
  max_stocks: 300               # 最大股票数
  exclude_st: true              # 排除ST股
  exclude_suspended: true       # 排除停牌股
  min_price: 2.0                # 最低价格
```

## 已实现的策略

### 1. 强势股多因子策略 (strategy_strong_stock)

**配置文件**: [strong_stock.yaml](file:///Users/binzhu/Projects/wavelet/backend/openfinance/quant/strategy/config/strong_stock.yaml)

**策略特点**:
- 4个核心因子：动量(30%) + 相对强度(30%) + 成交量强度(20%) + 趋势强度(20%)
- 周度调仓
- 严格风控：止损-8%，止盈+20%
- 最大持仓30只

**因子说明**:
- **动量因子**: 计算股价涨跌幅，捕捉价格动量
- **相对强度因子**: 使用线性回归计算趋势强度
- **成交量强度因子**: 分析成交量模式，识别资金流向
- **趋势强度因子**: 基于DMI指标计算趋势强度

### 2. RSI+KDJ动量策略 (strategy_rsi_kdj_momentum)

**配置文件**: [rsi_kdj_momentum.yaml](file:///Users/binzhu/Projects/wavelet/backend/openfinance/quant/strategy/config/rsi_kdj_momentum.yaml)

**策略特点**:
- 2个因子：RSI(50%) + KDJ(50%)
- 月度调仓
- 风控：止损-10%，止盈+15%
- 最大持仓50只

## 使用方法

### 1. 加载策略配置

```python
from openfinance.quant.strategy.config_loader import get_strategy_config_loader

# 获取配置加载器
loader = get_strategy_config_loader()

# 加载所有策略配置
configs = loader.load_all()

# 获取特定策略配置
config = loader.get_config("strategy_strong_stock")
```

### 2. 创建策略实例

```python
# 转换为域模型
strategy = loader.to_domain_strategy(config)

# 创建策略实例
strategy_instance = loader.create_strategy_instance(config)
```

### 3. 策略引擎自动加载

策略引擎初始化时会自动加载所有配置文件：

```python
from openfinance.quant.strategy.engine import StrategyEngine

engine = StrategyEngine()
# 自动加载配置文件中的策略

# 获取策略
strategy = engine.get_strategy("strategy_strong_stock")
```

### 4. 运行回测

```python
from openfinance.quant.backtest.engine import BacktestEngine
from openfinance.domain.models.quant import BacktestConfig

# 创建回测配置
backtest_config = BacktestConfig(
    strategy_id="strategy_strong_stock",
    start_date=date(2025, 1, 1),
    end_date=date(2025, 12, 31),
    initial_capital=1000000,
)

# 运行回测
backtest_engine = BacktestEngine()
result = await backtest_engine.run(
    strategy=strategy,
    config=backtest_config,
    price_data=price_data,
    factor_values=factor_values,
)
```

## 添加新策略

### 1. 创建配置文件

在 `backend/openfinance/quant/strategy/config/` 目录下创建新的YAML文件：

```yaml
version: "1.0"
metadata:
  namespace: openfinance
  description: 新策略描述

strategy_id: strategy_my_new_strategy
name: 我的新策略
code: my_new_strategy
display_name: My New Strategy
description: 策略详细描述
strategy_type: multi_factor
version: "1.0.0"
author: your_name
tags: [tag1, tag2]
status: active

factors:
  - factor_id: factor_1
    name: 因子1
    weight: 0.5
    enabled: true
    parameters:
      period: 20
      
  - factor_id: factor_2
    name: 因子2
    weight: 0.5
    enabled: true
    parameters:
      period: 14

portfolio:
  max_positions: 30
  position_size: 0.02
  weight_method: equal_weight
  rebalance_freq: weekly

risk_management:
  stop_loss: -0.08
  take_profit: 0.20
  max_position_weight: 0.10
  min_position_weight: 0.01

# ... 其他配置
```

### 2. 实现策略类（可选）

如果需要自定义策略逻辑，在 `implementations.py` 中添加新的策略类：

```python
@register_strategy(is_builtin=True)
class MyNewStrategy(BaseStrategy):
    def __init__(self, **kwargs):
        # 初始化逻辑
        pass
    
    def generate_signals(self, data, factor_values, date):
        # 信号生成逻辑
        pass
    
    def calculate_portfolio_weights(self, signals, prices, covariance_matrix):
        # 权重计算逻辑
        pass
```

### 3. 更新配置加载器

在 `config_loader.py` 的 `create_strategy_instance` 方法中添加新策略：

```python
def create_strategy_instance(self, config: StrategyConfig) -> BaseStrategy:
    if config.strategy_id == "strategy_strong_stock":
        return StrongStockStrategy(...)
    elif config.strategy_id == "strategy_my_new_strategy":
        return MyNewStrategy(...)
    else:
        raise ValueError(f"Unknown strategy type: {config.strategy_id}")
```

## 配置优势

### 1. 灵活性
- 无需修改代码即可调整策略参数
- 支持快速迭代和测试不同配置

### 2. 可维护性
- 配置与代码分离，便于管理
- 版本控制友好

### 3. 可扩展性
- 易于添加新策略
- 支持策略组合和继承

### 4. 可追溯性
- 配置文件记录了策略的所有参数
- 便于回测结果复现

## 前端集成

策略配置系统已完全集成到wavelet前端系统中：

### API端点
- `GET /api/quant/strategies` - 获取所有策略列表
- `GET /api/quant/strategies/{strategy_id}` - 获取策略详情
- `POST /api/quant/strategies/{strategy_id}/backtest` - 运行回测

### 前端页面
- 策略列表页面：显示所有可用策略
- 策略详情页面：查看策略配置和参数
- 回测页面：配置回测参数并运行

## 最佳实践

### 1. 参数调优
- 使用历史数据验证参数有效性
- 避免过度拟合
- 保持参数的合理性

### 2. 风险控制
- 设置合理的止损止盈
- 控制单只股票权重
- 注意行业集中度

### 3. 性能监控
- 定期评估策略表现
- 监控关键指标（夏普比率、最大回撤等）
- 及时调整参数

### 4. 文档维护
- 更新策略描述
- 记录参数调整原因
- 保存回测结果

## 技术支持

如有问题或建议，请联系开发团队。

---

**最后更新**: 2026-03-02
**版本**: 1.0.0
