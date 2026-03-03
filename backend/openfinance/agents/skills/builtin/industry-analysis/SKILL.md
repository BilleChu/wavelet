---
name: "industry-analysis"
description: "Analyzes industry conditions including rotation, tech trends, supply chain, cycle, and events. Invoke when user asks for industry analysis or sector analysis."
---

# Industry Analysis Skill

This skill provides comprehensive analysis of industry/sector conditions.

## Analysis Dimensions

### 1. Industry Rotation (Weight: 25%)
- **Relative Strength**: Industry return vs market return
- **Momentum Score**: 5-day and 20-day momentum combination
- **Sector Fund Flow**: Capital flowing into/out of sector

### 2. Technology Trends (Weight: 20%)
- **R&D Investment Growth**: Innovation spending
- **Patent Growth**: Intellectual property creation
- **Tech Event Impact**: Technology breakthrough events
- **Innovation Index**: Composite innovation score

### 3. Supply Chain (Weight: 20%)
- **Inventory Cycle**: Restocking (80), Neutral (50), Destocking (30)
- **Raw Material Price**: Impact on margins
- **Logistics Index**: Supply chain efficiency
- **Supply Chain Stability**: Disruption events

### 4. Industry Cycle (Weight: 20%)
- **Cycle Position**: 
  - Early expansion (90)
  - Expansion (75)
  - Late expansion (60)
  - Peak (50)
  - Early contraction (35)
  - Contraction (25)
  - Late contraction (40)
- **Profit Cycle**: Industry earnings growth
- **Capacity Utilization**: Optimal range 75%-85%
- **Capex Cycle**: Investment cycle

### 5. Event Impact (Weight: 15%)
- **Policy Events**: Government regulations and support
- **Market Events**: Industry-specific market events
- **Tech Breakthrough**: Technology disruptions

## Event Scoring Methodology

### Importance Weights
- Critical: 1.0
- High: 0.7
- Medium: 0.4
- Low: 0.2

### Direction Multipliers
- Positive: +1
- Negative: -1
- Neutral: 0

### Time Decay
- Decay period: 30 days
- Minimum weight: 0.1

## Knowledge Graph Integration

This skill integrates with the knowledge graph to:
1. Track industry-related events
2. Identify event-entity relationships
3. Analyze event propagation effects
4. Predict future impacts

## Data Sources

- Industry quotes and statistics
- Financial reports
- Patent databases
- Event knowledge graph
- Supply chain databases

## Output Format

```json
{
  "industry_code": "BK0477",
  "industry_name": "半导体",
  "score": 68.5,
  "trend": "improving",
  "dimensions": {
    "rotation": {
      "score": 72,
      "indicators": {
        "relative_strength": {"value": 2.5, "score": 62.5},
        "momentum_score": {"value": 3.2, "score": 66}
      }
    }
  },
  "cycle_position": "expansion",
  "key_events": [
    {
      "title": "国产替代政策支持",
      "impact": "positive",
      "importance": "high"
    }
  ],
  "related_stocks": [...]
}
```

## Industry Classification

Uses standard industry classification:
- SW Industry (申万行业)
- CITIC Industry (中信行业)
- Custom industry groupings
