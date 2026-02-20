---
name: quant-factor-creator
description: Create custom quantitative factors using LLM-powered code generation. Invoke when user wants to create new factors, build custom indicators, or design quantitative trading signals.
tags:
  - quant
  - factor
  - code-generation
  - llm
category: quant
version: "1.1.0"
author: OpenFinance Team
status: active
---

# Quant Factor Creator

AI-powered skill for creating custom quantitative factors. This skill enables users to describe their factor requirements in natural language and automatically generates production-ready factor code.

## Core Capabilities

1. **Natural Language Factor Design**: Describe your factor logic in plain language
2. **Code Generation**: Automatically generate Python factor code following best practices
3. **Parameter Extraction**: Extract configurable parameters from user requirements
4. **Validation**: Validate generated code for syntax and logic correctness
5. **Testing Integration**: Generate test cases for the factor

## Data Model

All factors use the standardized `ADSKLineModel` data model:

```python
from openfinance.datacenter.ads import ADSKLineModel

class ADSKLineModel:
    code: str           # Stock code (6-digit)
    trade_date: date    # Trading date
    open: float         # Opening price
    high: float         # Highest price
    low: float          # Lowest price
    close: float        # Closing price
    volume: int         # Trading volume
    amount: float       # Trading amount
    pre_close: float    # Previous closing price
    turnover: float     # Turnover rate
    amplitude: float    # Amplitude percentage
    change: float       # Price change
    change_pct: float   # Price change percentage
```

## Factor Creation Workflow

### Step 1: Requirement Collection

Collect the following information from the user:

| Parameter | Type | Description | Required |
|-----------|------|-------------|----------|
| factor_name | string | Unique name for the factor | Yes |
| description | string | Detailed description of factor logic | Yes |
| factor_type | enum | technical, fundamental, sentiment, alternative | Yes |
| category | enum | momentum, value, quality, volatility, liquidity, growth, custom | Yes |
| lookback_period | int | Number of days for calculation window | No |
| parameters | dict | Configurable parameters with defaults | No |
| data_requirements | list | Required data fields (close, volume, etc.) | No |

### Step 2: Code Generation

Generate factor code following the FactorBase template using ADSKLineModel:

```python
import numpy as np
from typing import Optional, List
from openfinance.datacenter.ads import ADSKLineModel

def calculate_factor(klines: List[ADSKLineModel], period: int = 20) -> Optional[float]:
    '''
    Factor calculation function.
    
    Args:
        klines: List of ADSKLineModel objects, sorted by date ascending (oldest first)
        period: Lookback period in days
    
    Returns:
        float: Factor value, or None if insufficient data
    '''
    if not klines or len(klines) < period + 1:
        return None
    
    # Extract data from ADSKLineModel
    close = np.array([k.close for k in klines])
    high = np.array([k.high for k in klines])
    low = np.array([k.low for k in klines])
    volume = np.array([k.volume for k in klines])
    
    # Add your calculation logic here
    # ...
    
    return result
```

### Step 3: Validation

Validate the generated code for:
- Syntax correctness
- Import validity
- Logic completeness
- Parameter handling
- Edge case coverage

### Step 4: Registration

Register the factor with the system:
1. Save factor code to database
2. Register in factor registry
3. Create metadata entry
4. Enable for strategy building

## API Endpoints

### Create Factor

```http
POST /api/quant/factors/create
Content-Type: application/json

{
  "name": "动量反转因子",
  "description": "基于价格动量的反转信号因子，计算过去N日收益率与波动率的比值",
  "factor_type": "technical",
  "category": "momentum",
  "lookback_period": 20,
  "parameters": {
    "period": {"type": "int", "default": 20, "min": 5, "max": 60},
    "threshold": {"type": "float", "default": 0.02, "min": 0.01, "max": 0.1}
  },
  "data_requirements": ["close", "volume"]
}
```

**Response:**
```json
{
  "success": true,
  "factor_id": "factor_momentum_reversal",
  "code": "def factor_momentum_reversal(klines, period=20, threshold=0.02):\n    ...",
  "validation": {
    "is_valid": true,
    "errors": [],
    "warnings": []
  },
  "metadata": {
    "factor_id": "factor_momentum_reversal",
    "name": "动量反转因子",
    "created_at": "2024-01-15T10:30:00Z"
  }
}
```

### Generate Factor from Description

```http
POST /api/quant/factor-creator/generate
Content-Type: application/json

{
  "description": "我想创建一个因子，计算股票过去20天的累计收益率，并除以同期波动率，得到风险调整后的动量指标",
  "context": {
    "investment_style": "momentum",
    "time_horizon": "short_term"
  }
}
```

**Response:**
```json
{
  "success": true,
  "suggested_name": "risk_adjusted_momentum",
  "generated_code": "...",
  "extracted_parameters": {
    "lookback_period": 20,
    "normalize": true
  },
  "explanation": "该因子计算风险调整后的动量，通过将累计收益率除以波动率来衡量单位风险收益..."
}
```

## Factor Templates

### Momentum Factor Template

```python
import numpy as np
from typing import Optional, List
from openfinance.datacenter.ads import ADSKLineModel

def calculate_factor(klines: List[ADSKLineModel], period: int = 20) -> Optional[float]:
    '''
    Momentum factor - calculates price change rate over period.
    
    Args:
        klines: List of ADSKLineModel objects, sorted by date ascending
        period: Lookback period in days
    
    Returns:
        float: Momentum value (e.g., 0.15 means 15% gain), or None if insufficient data
    '''
    if not klines or len(klines) < period + 1:
        return None
    
    close = np.array([k.close for k in klines])
    
    if len(close) < period + 1:
        return None
    
    current_close = close[-1]
    past_close = close[-(period + 1)]
    
    if past_close <= 0:
        return None
    
    momentum = (current_close / past_close) - 1.0
    return float(momentum)
```

### Volatility Factor Template

```python
import numpy as np
from typing import Optional, List
from openfinance.datacenter.ads import ADSKLineModel

def calculate_factor(klines: List[ADSKLineModel], period: int = 20) -> Optional[float]:
    '''
    Volatility factor - calculates annualized return volatility.
    
    Args:
        klines: List of ADSKLineModel objects, sorted by date ascending
        period: Lookback period in days
    
    Returns:
        float: Annualized volatility, or None if insufficient data
    '''
    if not klines or len(klines) < period + 1:
        return None
    
    close = np.array([k.close for k in klines])
    
    if len(close) < period + 1:
        return None
    
    returns = np.diff(close) / close[:-1]
    volatility = np.std(returns[-period:]) * np.sqrt(252)
    
    return float(volatility)
```

### Volume Ratio Factor Template

```python
import numpy as np
from typing import Optional, List
from openfinance.datacenter.ads import ADSKLineModel

def calculate_factor(klines: List[ADSKLineModel], period: int = 20) -> Optional[float]:
    '''
    Volume ratio factor - current volume vs average volume.
    
    Args:
        klines: List of ADSKLineModel objects, sorted by date ascending
        period: Lookback period in days
    
    Returns:
        float: Volume ratio, or None if insufficient data
    '''
    if not klines or len(klines) < period:
        return None
    
    volume = np.array([k.volume for k in klines])
    
    if len(volume) < period:
        return None
    
    avg_volume = np.mean(volume[-period:])
    
    if avg_volume <= 0:
        return None
    
    ratio = volume[-1] / avg_volume
    return float(ratio)
```

## Best Practices

1. **Naming Convention**: Use descriptive names like `momentum_20d`, `value_pe_ratio`
2. **Parameter Design**: Make parameters configurable with sensible defaults
3. **Error Handling**: Handle edge cases (insufficient data, missing values, zero division)
4. **Normalization**: Consider z-score normalization for cross-sectional comparison
5. **Documentation**: Include docstrings explaining the factor logic
6. **Data Model**: Always use `ADSKLineModel` for consistent data access

## Integration with Strategy Builder

Generated factors can be immediately used in strategy building:

```python
strategy = StrategyBuilder()
strategy.add_factor("factor_momentum_reversal", weight=0.3)
strategy.add_factor("factor_value", weight=0.3)
strategy.add_factor("factor_quality", weight=0.4)
strategy.set_rebalance_frequency("monthly")
strategy.set_max_positions(30)
```

## Related Skills

- `financial-analysis`: For fundamental factor data
- `tech-indicator`: For technical indicator calculations
- `macro-analysis`: For macro factor integration
