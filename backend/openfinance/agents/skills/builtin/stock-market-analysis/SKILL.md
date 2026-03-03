---
name: "stock-market-analysis"
description: "Analyzes stock market conditions including trend, breadth, volume, capital flow, and valuation. Invoke when user asks for market analysis or market overview."
---

# Stock Market Analysis Skill

This skill provides comprehensive analysis of stock market conditions.

## Analysis Dimensions

### 1. Index Trend (Weight: 25%)
- **MA Alignment**: Bullish (90), Neutral (60), Bearish (30)
- **Price vs MA20**: Above MA20 indicates strength
- **Trend Strength (ADX)**: Higher indicates stronger trend
- **MACD Signal**: Golden cross (80), Above zero (65), Below zero (45), Death cross (30)

### 2. Market Breadth (Weight: 20%)
- **Advance/Decline Ratio**: More advancers = stronger market
- **New High/Low Ratio**: More highs = stronger market
- **Stocks Above MA20**: Percentage indicates breadth
- **Rising Sector Ratio**: Sector participation

### 3. Volume Analysis (Weight: 20%)
- **Volume Trend**: Above average = higher interest
- **Volume-Price Relationship**: 
  - Up with volume (85): Healthy rally
  - Up with low volume (60): Weak rally
  - Down with volume (35): Panic selling
  - Down with low volume (50): Normal correction
- **Turnover Rate**: Optimal range 2%-5%
- **Market Sentiment Index**: Composite sentiment

### 4. Capital Flow (Weight: 20%)
- **Northbound Capital Flow**: Foreign investor sentiment
- **Main Force Flow**: Institutional activity
- **Margin Balance Change**: Leverage sentiment
- **ETF Flow**: Passive investment trends

### 5. Valuation Level (Weight: 15%)
- **Market PE**: Optimal range 12-18x
- **Market PB**: Optimal range 1.5-2.5x
- **PE Percentile**: Lower = more attractive
- **Equity Risk Premium**: Higher = more attractive

## Data Sources

- Exchange market data
- Capital flow data providers
- Index providers
- Valuation databases

## Scoring Methodology

Each indicator is scored on a 0-100 scale:
- **Score >= 70**: Bullish condition
- **Score 40-70**: Neutral condition
- **Score < 40**: Bearish condition

## Technical Indicators Used

- Moving Averages (MA5, MA10, MA20, MA60)
- MACD (12, 26, 9)
- ADX for trend strength
- Volume analysis

## Output Format

```json
{
  "score": 62.5,
  "trend": "up",
  "dimensions": {
    "trend": {
      "score": 70,
      "indicators": {
        "ma_alignment": {"value": "bullish", "score": 90},
        "macd_signal": {"value": "above_zero", "score": 65}
      }
    }
  },
  "support_levels": [...],
  "resistance_levels": [...],
  "key_events": [...]
}
```
