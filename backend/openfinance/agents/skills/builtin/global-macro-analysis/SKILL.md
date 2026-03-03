---
name: "global-macro-analysis"
description: "Analyzes global macroeconomic conditions including Fed policy, US economy, inflation, and risk appetite. Invoke when user asks for global macro analysis or market overview."
---

# Global Macro Analysis Skill

This skill provides comprehensive analysis of global macroeconomic conditions.

## Analysis Dimensions

### 1. Federal Reserve Policy Space (Weight: 25%)
- **Federal Funds Rate**: Optimal range 2.0%-4.0%
- **Rate Direction**: Cut (80), Hold (60), Hike (40)
- **Rate Expectation**: Based on futures market

### 2. US Economic Momentum (Weight: 25%)
- **GDP Growth**: Optimal range 2.0%-3.5%
- **Nonfarm Payroll**: Optimal range 150K-300K
- **Unemployment Rate**: Optimal range 3.5%-4.5%
- **Consumer Confidence**: Optimal range 100-120

### 3. Inflation Level (Weight: 20%)
- **US CPI**: Optimal range 2.0%-3.0%
- **Core CPI**: Optimal range 2.0%-2.5%
- **PCE Price Index**: Optimal range 2.0%-2.5%

### 4. Risk Appetite (Weight: 15%)
- **VIX Index**: Lower is better (optimal 12-20)
- **Credit Spread**: Optimal range 1.0%-2.0%
- **Dollar Index**: Optimal range 95-105

### 5. Global Trade (Weight: 15%)
- **Baltic Dry Index**: Higher indicates stronger trade
- **Global Manufacturing PMI**: Above 50 indicates expansion
- **Trade Policy Uncertainty**: Lower is better

## Data Sources

- Federal Reserve Economic Data (FRED)
- Bureau of Labor Statistics (BLS)
- Bureau of Economic Analysis (BEA)
- Market data providers

## Scoring Methodology

Each indicator is scored on a 0-100 scale:
- **Score >= 70**: Positive condition
- **Score 40-70**: Neutral condition
- **Score < 40**: Negative condition

The overall score is a weighted average of all dimension scores.

## Output Format

```json
{
  "score": 65.5,
  "trend": "improving",
  "dimensions": {
    "fed_policy": {
      "score": 60,
      "indicators": {
        "fed_funds_rate": {"value": 5.25, "score": 50},
        "rate_direction": {"value": "hold", "score": 60}
      }
    }
  },
  "key_events": [...],
  "recommendations": [...]
}
```

## Usage

To analyze global macro conditions:

1. Fetch latest economic indicators from data sources
2. Calculate scores for each indicator using factor configurations
3. Aggregate dimension scores with weights
4. Identify key events affecting the score
5. Generate analysis and recommendations
