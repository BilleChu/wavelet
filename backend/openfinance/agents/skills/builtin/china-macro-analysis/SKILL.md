---
name: "china-macro-analysis"
description: "Analyzes China macroeconomic conditions including growth, PMI, monetary policy, and property market. Invoke when user asks for China macro analysis or market overview."
---

# China Macro Analysis Skill

This skill provides comprehensive analysis of China macroeconomic conditions.

## Analysis Dimensions

### 1. Economic Growth (Weight: 30%)
- **GDP Growth**: Optimal range 5.0%-7.0%
- **Industrial Value Added**: Optimal range 5.0%-8.0%
- **Fixed Asset Investment**: Optimal range 5.0%-10.0%
- **Retail Sales Growth**: Optimal range 6.0%-10.0%

### 2. Price Level (Weight: 20%)
- **CPI**: Optimal range 1.5%-3.0%
- **PPI**: Optimal range 0%-3.0%
- **Core CPI**: Optimal range 1.5%-2.5%

### 3. Manufacturing Sentiment (Weight: 20%)
- **Manufacturing PMI**: Above 50 indicates expansion
- **Non-Manufacturing PMI**: Above 50 indicates expansion
- **New Orders Index**: Above 50 indicates growth

### 4. Monetary & Financial (Weight: 15%)
- **M2 Growth**: Optimal range 8.0%-12.0%
- **Social Financing**: Higher indicates more credit
- **1Y LPR**: Lower rates support growth
- **Credit Growth**: Optimal range 10.0%-15.0%

### 5. Property Market (Weight: 15%)
- **Property Investment Growth**: Positive indicates recovery
- **Property Sales Growth**: Key indicator of demand
- **New Home Price Index**: Optimal range 100-105
- **Land Purchases Growth**: Forward-looking indicator

## Data Sources

- National Bureau of Statistics (NBS)
- People's Bank of China (PBOC)
- China Index Academy
- Market data providers

## Scoring Methodology

Each indicator is scored on a 0-100 scale:
- **Score >= 70**: Strong condition
- **Score 40-70**: Normal condition
- **Score < 40**: Weak condition

## Special Considerations

### Policy Impact Analysis
- Monitor PBOC policy announcements
- Track government stimulus measures
- Analyze regulatory changes impact

### Event Integration
- Connect with knowledge graph for policy events
- Time-decay for event impacts
- Importance weighting for events

## Output Format

```json
{
  "score": 58.5,
  "trend": "stable",
  "dimensions": {
    "growth": {
      "score": 55,
      "indicators": {
        "gdp": {"value": 5.2, "score": 78},
        "industrial_value_added": {"value": 4.5, "score": 54}
      }
    }
  },
  "policy_events": [...],
  "recommendations": [...]
}
```
