---
name: quant-strategy-creator
description: Create custom quantitative strategies using LLM-powered code generation. Invoke when user wants to create new strategies, build trading systems, or design portfolio management rules.
tags:
  - quant
  - strategy
  - code-generation
  - llm
  - portfolio
category: quant
version: "1.0.0"
author: OpenFinance Team
status: active
---

# Quant Strategy Creator

AI-powered skill for creating custom quantitative strategies. This skill enables users to describe their strategy requirements in natural language and automatically generates production-ready strategy code.

## Core Capabilities

1. **Natural Language Strategy Design**: Describe your strategy logic in plain language
2. **Code Generation**: Automatically generate Python strategy code following best practices
3. **Factor Integration**: Combine multiple factors with configurable weights
4. **Signal Generation**: Implement custom signal generation logic
5. **Portfolio Optimization**: Support various weighting methods

## Strategy Architecture

All strategies inherit from `BaseStrategy` and must implement:

```python
from openfinance.quant.strategy.base import (
    BaseStrategy,
    StrategyMetadata,
    StrategyType,
    WeightMethod,
    RebalanceFrequency,
)
from openfinance.quant.strategy.registry import register_strategy

@register_strategy
class CustomStrategy(BaseStrategy):
    """Strategy description."""
    
    def _default_metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            strategy_id="strategy_custom",
            name="Custom Strategy",
            description="Strategy description",
            strategy_type=StrategyType.MULTI_FACTOR,
            factor_ids=["factor_1", "factor_2"],
        )
    
    def generate_signals(self, data, factor_values=None, date=None) -> dict[str, float]:
        """Generate trading signals (-1 to 1)."""
        signals = {}
        # Signal generation logic
        return signals
    
    def calculate_portfolio_weights(self, signals, prices, covariance_matrix=None) -> dict[str, float]:
        """Calculate portfolio weights."""
        weights = {}
        # Weight calculation logic
        return weights
```

## Strategy Types

| Type | Description | Use Case |
|------|-------------|----------|
| single_factor | Single factor strategy | Simple momentum or value strategy |
| multi_factor | Multiple factor combination | Diversified factor investing |
| rule_based | Rule-based strategy | Technical trading rules |
| ml_based | Machine learning strategy | ML-driven predictions |

## Weight Methods

| Method | Description |
|--------|-------------|
| equal_weight | Equal weight across all positions |
| risk_parity | Risk parity allocation |
| mean_variance | Mean-variance optimization |
| black_litterman | Black-Litterman model |
| hierarchical_risk_parity | HRP allocation |
| custom | Custom weighting logic |

## Strategy Creation Workflow

### Step 1: Requirement Collection

Collect the following information:

| Parameter | Type | Description | Required |
|-----------|------|-------------|----------|
| strategy_name | string | Unique name for the strategy | Yes |
| description | string | Detailed description of strategy logic | Yes |
| strategy_type | enum | single_factor, multi_factor, rule_based, ml_based | Yes |
| factors | list | List of factor IDs to use | Yes |
| factor_weights | dict | Weight for each factor (should sum to 1) | No |
| weight_method | enum | Portfolio weighting method | No |
| rebalance_freq | enum | daily, weekly, monthly, quarterly | No |
| max_positions | int | Maximum number of positions | No |
| stop_loss | float | Stop loss threshold (e.g., 0.1 for 10%) | No |
| take_profit | float | Take profit threshold | No |

### Step 2: Code Generation

Generate strategy code following the template:

```python
@register_strategy
class MomentumValueStrategy(BaseStrategy):
    """
    Momentum + Value Multi-Factor Strategy
    
    Combines momentum and value factors with equal weights.
    Rebalances monthly with max 50 positions.
    """
    
    def _default_metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            strategy_id="strategy_momentum_value",
            name="Momentum + Value Strategy",
            description="Multi-factor strategy combining momentum and value signals",
            strategy_type=StrategyType.MULTI_FACTOR,
            factor_ids=["factor_momentum", "factor_value"],
            tags=["momentum", "value", "multi_factor"],
        )
    
    def generate_signals(self, data, factor_values=None, date=None) -> dict[str, float]:
        signals = {}
        
        if not factor_values:
            return signals
        
        momentum_scores = factor_values.get("factor_momentum", {})
        value_scores = factor_values.get("factor_value", {})
        
        for code in set(momentum_scores.keys()) & set(value_scores.keys()):
            momentum = momentum_scores.get(code, 0)
            value = value_scores.get(code, 0)
            
            # Combine signals with weights
            signal = 0.5 * momentum + 0.5 * value
            signals[code] = signal
        
        return signals
    
    def calculate_portfolio_weights(self, signals, prices, covariance_matrix=None) -> dict[str, float]:
        # Equal weight for top signals
        sorted_signals = sorted(signals.items(), key=lambda x: x[1], reverse=True)
        top_n = min(self.max_positions, len(sorted_signals))
        
        weights = {}
        for code, _ in sorted_signals[:top_n]:
            weights[code] = 1.0 / top_n
        
        return weights
```

### Step 3: Validation

Validate the generated code for:
- Syntax correctness
- Required method implementations
- Factor availability
- Parameter validity

### Step 4: Registration

Register the strategy with the system:
1. Save strategy code to `strategy/custom/` directory
2. Register in strategy registry
3. Create metadata entry
4. Enable for backtesting and live trading

## API Endpoints

### Create Strategy

```http
POST /api/quant/strategy-creator/generate
Content-Type: application/json

{
  "description": "创建一个动量+价值多因子策略，等权重组合，月度再平衡",
  "factors": ["factor_momentum", "factor_value"],
  "factor_weights": {"factor_momentum": 0.5, "factor_value": 0.5},
  "weight_method": "equal_weight",
  "rebalance_freq": "monthly",
  "max_positions": 50
}
```

**Response:**
```json
{
  "success": true,
  "strategy_id": "strategy_momentum_value",
  "code": "...",
  "validation": {
    "is_valid": true,
    "errors": [],
    "warnings": []
  }
}
```

### Save Strategy

```http
POST /api/quant/strategy-creator/save
Content-Type: application/json

{
  "strategy_id": "strategy_momentum_value",
  "name": "动量价值策略",
  "code": "...",
  "description": "多因子策略",
  "strategy_type": "multi_factor",
  "factors": ["factor_momentum", "factor_value"],
  "factor_weights": {"factor_momentum": 0.5, "factor_value": 0.5}
}
```

## Strategy Templates

### Single Factor Strategy

```python
@register_strategy
class SingleFactorStrategy(BaseStrategy):
    """Single factor strategy template."""
    
    def _default_metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            strategy_id="strategy_single_factor",
            name="Single Factor Strategy",
            strategy_type=StrategyType.SINGLE_FACTOR,
            factor_ids=["factor_id"],
        )
    
    def generate_signals(self, data, factor_values=None, date=None) -> dict[str, float]:
        if not factor_values:
            return {}
        return factor_values.get(self.factors[0], {})
    
    def calculate_portfolio_weights(self, signals, prices, covariance_matrix=None) -> dict[str, float]:
        sorted_signals = sorted(signals.items(), key=lambda x: x[1], reverse=True)
        top_n = min(self.max_positions, len(sorted_signals))
        return {code: 1.0/top_n for code, _ in sorted_signals[:top_n]}
```

### Multi-Factor Strategy

```python
@register_strategy
class MultiFactorStrategy(BaseStrategy):
    """Multi-factor strategy template."""
    
    def _default_metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            strategy_id="strategy_multi_factor",
            name="Multi-Factor Strategy",
            strategy_type=StrategyType.MULTI_FACTOR,
            factor_ids=["factor_1", "factor_2", "factor_3"],
        )
    
    def generate_signals(self, data, factor_values=None, date=None) -> dict[str, float]:
        signals = {}
        for factor_id, scores in (factor_values or {}).items():
            weight = self.factor_weights.get(factor_id, 1.0/len(self.factors))
            for code, score in scores.items():
                signals[code] = signals.get(code, 0) + weight * score
        return signals
    
    def calculate_portfolio_weights(self, signals, prices, covariance_matrix=None) -> dict[str, float]:
        sorted_signals = sorted(signals.items(), key=lambda x: x[1], reverse=True)
        top_n = min(self.max_positions, len(sorted_signals))
        return {code: 1.0/top_n for code, _ in sorted_signals[:top_n]}
```

## Best Practices

1. **Factor Selection**: Choose factors with low correlation for diversification
2. **Weight Allocation**: Consider factor IC and stability when setting weights
3. **Rebalancing**: Balance between transaction costs and signal decay
4. **Position Limits**: Set appropriate max_positions for liquidity
5. **Risk Management**: Implement stop-loss and take-profit rules
6. **Documentation**: Include clear docstrings explaining strategy logic

## Integration with Backtesting

Generated strategies can be immediately used for backtesting:

```python
from openfinance.quant.backtest import BacktestEngine

engine = BacktestEngine()
engine.load_strategy("strategy_momentum_value")
results = engine.run(
    start_date="2020-01-01",
    end_date="2024-01-01",
    initial_capital=1000000,
)
```

## Related Skills

- `quant-factor-creator`: For creating custom factors
- `financial-analysis`: For fundamental analysis
- `tech-indicator`: For technical indicators
