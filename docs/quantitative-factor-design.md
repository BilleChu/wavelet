# Wavelet 量化因子评估体系设计文档

## 1. 概述

本文档详细描述 Wavelet 智能分析平台的量化因子评估体系，包括：
- 财联社事件数据采集与处理
- 全球宏观量化因子评估
- 中国宏观量化因子评估
- 股市大盘量化因子评估
- 行业指标量化因子评估

## 2. 财联社事件数据采集

### 2.1 数据源
- **来源**: 财联社电报 (https://www.cls.cn/telegraph)
- **采集频率**: 实时 (每分钟)
- **数据类型**: 快讯、公告、政策发布

### 2.2 事件分类
```yaml
event_categories:
  macro_global:
    - 美联储利率决议
    - 美国非农数据
    - 美国CPI/PPI数据
    - 欧洲央行政策
    - 国际贸易事件
    
  macro_china:
    - 中国GDP发布
    - CPI/PPI数据
    - PMI数据
    - 央行政策
    - 财政政策
    
  market:
    - 指数突破关键点位
    - 市场异常波动
    - 北向资金异动
    - 融资融券变化
    
  industry:
    - 行业政策
    - 技术突破
    - 供应链事件
    - 行业周期转折
    
  company:
    - 业绩公告
    - 重大重组
    - 高管变动
    - 股权变动
```

### 2.3 事件重要性评估
```python
importance_weights = {
    'critical': {  # 关键事件
        'weight': 1.0,
        'examples': ['美联储利率决议', '中国GDP发布', '重大政策发布'],
        'impact_duration': 30,  # 影响持续天数
    },
    'high': {  # 高重要性
        'weight': 0.7,
        'examples': ['美国非农数据', 'CPI数据', '行业重大政策'],
        'impact_duration': 14,
    },
    'medium': {  # 中等重要性
        'weight': 0.4,
        'examples': ['PMI数据', '行业数据', '公司公告'],
        'impact_duration': 7,
    },
    'low': {  # 低重要性
        'weight': 0.2,
        'examples': ['日常新闻', '市场评论'],
        'impact_duration': 3,
    },
}
```

### 2.4 数据库表设计
```sql
-- 市场事件表 (已存在，需扩展)
CREATE TABLE IF NOT EXISTS openfinance.market_events (
    id SERIAL PRIMARY KEY,
    event_id VARCHAR(100) UNIQUE NOT NULL,
    title VARCHAR(500) NOT NULL,
    summary TEXT,
    content TEXT,
    
    -- 时间信息
    event_date TIMESTAMP NOT NULL,
    publish_date TIMESTAMP,
    
    -- 分类
    category VARCHAR(50),  -- macro_global, macro_china, market, industry, company
    event_type VARCHAR(50),  -- policy, data, announcement, breaking
    
    -- 影响评估
    importance VARCHAR(20),  -- critical, high, medium, low
    impact_direction VARCHAR(20),  -- positive, negative, neutral
    impact_magnitude DECIMAL(5,2),  -- 影响幅度 0-100
    affected_dimensions JSONB,  -- 受影响的维度
    
    -- 关联实体
    entities JSONB,  -- 关联的股票、行业、概念
    
    -- 来源
    source_name VARCHAR(100),
    source_url VARCHAR(500),
    confidence DECIMAL(3,2),
    
    -- AI分析
    ai_analysis TEXT,
    score_change DECIMAL(5,2),  -- 评分变化
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 事件-实体关系表 (已存在)
CREATE TABLE IF NOT EXISTS openfinance.event_entity_relations (
    id SERIAL PRIMARY KEY,
    event_id INTEGER REFERENCES openfinance.market_events(id),
    entity_id VARCHAR(100),
    entity_type VARCHAR(50),
    entity_name VARCHAR(200),
    relation_type VARCHAR(50),
    impact_score DECIMAL(5,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 3. 全球宏观量化因子评估体系

### 3.1 评估指标

#### 3.1.1 美联储政策空间 (权重: 25%)
```python
fed_policy_indicators = {
    'fed_funds_rate': {
        'name': '联邦基金利率',
        'optimal_range': (2.0, 4.0),  # 最优区间
        'score_function': lambda x: 100 - abs(x - 3.0) * 15,  # 越接近3%越好
        'weight': 0.4,
    },
    'rate_change_direction': {
        'name': '利率变动方向',
        'values': {
            'cut': 80,  # 降息
            'hold': 60,  # 维持
            'hike': 40,  # 加息
        },
        'weight': 0.3,
    },
    'rate_change_expectation': {
        'name': '利率预期',
        'score_function': lambda expected, current: 70 if expected < current else 50,
        'weight': 0.3,
    },
}
```

#### 3.1.2 美国经济动能 (权重: 25%)
```python
us_economy_indicators = {
    'gdp_growth': {
        'name': '美国GDP增速',
        'optimal_range': (2.0, 3.5),
        'score_function': lambda x: min(100, max(0, x * 25)),
        'weight': 0.3,
    },
    'nonfarm_payroll': {
        'name': '非农就业',
        'optimal_range': (150000, 300000),
        'score_function': lambda x: 70 + (x - 200000) / 5000,
        'weight': 0.25,
    },
    'unemployment_rate': {
        'name': '失业率',
        'optimal_range': (3.5, 4.5),
        'score_function': lambda x: 100 - abs(x - 4.0) * 20,
        'weight': 0.25,
    },
    'consumer_confidence': {
        'name': '消费者信心指数',
        'optimal_range': (100, 120),
        'score_function': lambda x: min(100, x * 0.8),
        'weight': 0.2,
    },
}
```

#### 3.1.3 通胀水平 (权重: 20%)
```python
inflation_indicators = {
    'us_cpi': {
        'name': '美国CPI',
        'optimal_range': (2.0, 3.0),
        'score_function': lambda x: 100 - abs(x - 2.5) * 30,
        'weight': 0.4,
    },
    'us_core_cpi': {
        'name': '核心CPI',
        'optimal_range': (2.0, 2.5),
        'score_function': lambda x: 100 - abs(x - 2.25) * 25,
        'weight': 0.35,
    },
    'us_pce': {
        'name': 'PCE物价指数',
        'optimal_range': (2.0, 2.5),
        'score_function': lambda x: 100 - abs(x - 2.25) * 25,
        'weight': 0.25,
    },
}
```

#### 3.1.4 风险偏好 (权重: 15%)
```python
risk_appetite_indicators = {
    'vix': {
        'name': 'VIX恐慌指数',
        'optimal_range': (12, 20),
        'score_function': lambda x: max(0, 100 - x * 3),
        'weight': 0.4,
    },
    'credit_spread': {
        'name': '信用利差',
        'optimal_range': (1.0, 2.0),
        'score_function': lambda x: max(0, 100 - x * 30),
        'weight': 0.3,
    },
    'dollar_index': {
        'name': '美元指数',
        'optimal_range': (95, 105),
        'score_function': lambda x: 100 - abs(x - 100) * 2,
        'weight': 0.3,
    },
}
```

#### 3.1.5 全球贸易 (权重: 15%)
```python
global_trade_indicators = {
    'baltic_dry': {
        'name': '波罗的海干散货指数',
        'score_function': lambda x: min(100, x / 20),
        'weight': 0.4,
    },
    'global_pmI': {
        'name': '全球制造业PMI',
        'optimal_range': (50, 55),
        'score_function': lambda x: max(0, (x - 45) * 4),
        'weight': 0.35,
    },
    'trade_policy_uncertainty': {
        'name': '贸易政策不确定性',
        'score_function': lambda x: 100 - min(100, x),
        'weight': 0.25,
    },
}
```

### 3.2 综合评分公式
```python
def calculate_global_macro_score(indicators: dict) -> float:
    """
    全球宏观评分计算
    
    Score = Σ (Indicator_Score × Indicator_Weight × Category_Weight)
    """
    category_weights = {
        'fed_policy': 0.25,
        'us_economy': 0.25,
        'inflation': 0.20,
        'risk_appetite': 0.15,
        'global_trade': 0.15,
    }
    
    total_score = 0
    for category, weight in category_weights.items():
        category_score = calculate_category_score(indicators.get(category, {}))
        total_score += category_score * weight
    
    return round(total_score, 2)
```

## 4. 中国宏观量化因子评估体系

### 4.1 评估指标

#### 4.1.1 经济增长 (权重: 30%)
```python
china_growth_indicators = {
    'gdp_growth': {
        'name': 'GDP增速',
        'optimal_range': (5.0, 7.0),
        'score_function': lambda x: min(100, max(0, x * 15)),
        'weight': 0.35,
        'data_source': '国家统计局',
    },
    'industrial_value_added': {
        'name': '工业增加值',
        'optimal_range': (5.0, 8.0),
        'score_function': lambda x: min(100, max(0, x * 12)),
        'weight': 0.25,
    },
    'fixed_asset_investment': {
        'name': '固定资产投资',
        'optimal_range': (5.0, 10.0),
        'score_function': lambda x: min(100, max(0, x * 10)),
        'weight': 0.2,
    },
    'retail_sales': {
        'name': '社会消费品零售总额增速',
        'optimal_range': (6.0, 10.0),
        'score_function': lambda x: min(100, max(0, x * 10)),
        'weight': 0.2,
    },
}
```

#### 4.1.2 物价水平 (权重: 20%)
```python
china_price_indicators = {
    'cpi': {
        'name': 'CPI',
        'optimal_range': (1.5, 3.0),
        'score_function': lambda x: 100 - abs(x - 2.25) * 30,
        'weight': 0.4,
    },
    'ppi': {
        'name': 'PPI',
        'optimal_range': (0, 3.0),
        'score_function': lambda x: 100 - abs(x - 1.5) * 20,
        'weight': 0.35,
    },
    'core_cpi': {
        'name': '核心CPI',
        'optimal_range': (1.5, 2.5),
        'score_function': lambda x: 100 - abs(x - 2.0) * 25,
        'weight': 0.25,
    },
}
```

#### 4.1.3 制造业景气度 (权重: 20%)
```python
china_pmi_indicators = {
    'manufacturing_pmi': {
        'name': '制造业PMI',
        'optimal_range': (50, 55),
        'score_function': lambda x: max(0, (x - 45) * 4),
        'weight': 0.4,
    },
    'non_manufacturing_pmi': {
        'name': '非制造业PMI',
        'optimal_range': (52, 58),
        'score_function': lambda x: max(0, (x - 45) * 3.5),
        'weight': 0.3,
    },
    'new_orders_index': {
        'name': '新订单指数',
        'optimal_range': (50, 55),
        'score_function': lambda x: max(0, (x - 45) * 4),
        'weight': 0.3,
    },
}
```

#### 4.1.4 货币金融 (权重: 15%)
```python
china_monetary_indicators = {
    'm2_growth': {
        'name': 'M2增速',
        'optimal_range': (8.0, 12.0),
        'score_function': lambda x: 100 - abs(x - 10) * 8,
        'weight': 0.3,
    },
    'social_financing': {
        'name': '社会融资规模增量',
        'score_function': lambda x: min(100, x / 30000 * 100),
        'weight': 0.25,
    },
    'lpr_1y': {
        'name': '1年期LPR',
        'optimal_range': (3.0, 4.0),
        'score_function': lambda x: 100 - (x - 3.5) * 30,
        'weight': 0.25,
    },
    'credit_growth': {
        'name': '信贷增速',
        'optimal_range': (10.0, 15.0),
        'score_function': lambda x: min(100, x * 7),
        'weight': 0.2,
    },
}
```

#### 4.1.5 房地产市场 (权重: 15%)
```python
china_property_indicators = {
    'property_investment': {
        'name': '房地产开发投资增速',
        'optimal_range': (0, 8.0),
        'score_function': lambda x: max(0, 50 + x * 5),
        'weight': 0.3,
    },
    'property_sales': {
        'name': '商品房销售面积增速',
        'score_function': lambda x: max(0, 50 + x * 3),
        'weight': 0.3,
    },
    'new_home_price': {
        'name': '新房价格指数',
        'optimal_range': (100, 105),
        'score_function': lambda x: 100 - abs(x - 102.5) * 10,
        'weight': 0.2,
    },
    'land_purchases': {
        'name': '土地购置面积增速',
        'score_function': lambda x: max(0, 50 + x * 2),
        'weight': 0.2,
    },
}
```

## 5. 股市大盘量化因子评估体系

### 5.1 评估指标

#### 5.1.1 指数趋势 (权重: 25%)
```python
index_trend_indicators = {
    'ma_alignment': {
        'name': '均线排列',
        'values': {
            'bullish': 90,  # 多头排列 (MA5 > MA10 > MA20 > MA60)
            'neutral': 60,  # 混乱排列
            'bearish': 30,  # 空头排列
        },
        'weight': 0.35,
    },
    'price_vs_ma20': {
        'name': '价格与MA20关系',
        'score_function': lambda price, ma20: 70 + (price - ma20) / ma20 * 100,
        'weight': 0.25,
    },
    'trend_strength': {
        'name': '趋势强度 (ADX)',
        'score_function': lambda adx: min(100, adx * 1.5),
        'weight': 0.2,
    },
    'macd_signal': {
        'name': 'MACD信号',
        'values': {
            'golden_cross': 80,
            'above_zero': 65,
            'below_zero': 45,
            'death_cross': 30,
        },
        'weight': 0.2,
    },
}
```

#### 5.1.2 市场广度 (权重: 20%)
```python
market_breadth_indicators = {
    'advance_decline_ratio': {
        'name': '涨跌比',
        'score_function': lambda adv, dec: min(100, 50 + (adv - dec) / (adv + dec) * 100),
        'weight': 0.3,
    },
    'new_high_low_ratio': {
        'name': '创新高/新低比',
        'score_function': lambda highs, lows: min(100, 50 + (highs - lows) / max(1, highs + lows) * 50),
        'weight': 0.25,
    },
    'stocks_above_ma20': {
        'name': '站上MA20股票占比',
        'score_function': lambda pct: pct,
        'weight': 0.25,
    },
    'rising_sector_ratio': {
        'name': '上涨板块占比',
        'score_function': lambda pct: pct,
        'weight': 0.2,
    },
}
```

#### 5.1.3 成交量 (权重: 20%)
```python
volume_indicators = {
    'volume_trend': {
        'name': '成交量趋势',
        'score_function': lambda vol, ma_vol: min(100, 50 + (vol / ma_vol - 1) * 50),
        'weight': 0.3,
    },
    'volume_price_trend': {
        'name': '量价关系',
        'values': {
            'up_with_volume': 85,  # 量价齐升
            'up_with_low_volume': 60,  # 缩量上涨
            'down_with_volume': 35,  # 放量下跌
            'down_with_low_volume': 50,  # 缩量下跌
        },
        'weight': 0.3,
    },
    'turnover_rate': {
        'name': '换手率',
        'optimal_range': (2.0, 5.0),
        'score_function': lambda x: 100 - abs(x - 3.5) * 15,
        'weight': 0.2,
    },
    'market_sentiment_index': {
        'name': '市场情绪指数',
        'score_function': lambda x: x,
        'weight': 0.2,
    },
}
```

#### 5.1.4 资金流向 (权重: 20%)
```python
capital_flow_indicators = {
    'northbound_flow': {
        'name': '北向资金净流入',
        'score_function': lambda flow: min(100, max(0, 50 + flow / 1000000000 * 5)),
        'weight': 0.35,
    },
    'main_force_flow': {
        'name': '主力资金净流入',
        'score_function': lambda flow: min(100, max(0, 50 + flow / 10000000000 * 10)),
        'weight': 0.25,
    },
    'margin_balance': {
        'name': '融资余额变化',
        'score_function': lambda change: min(100, max(0, 50 + change * 10)),
        'weight': 0.2,
    },
    'etf_flow': {
        'name': 'ETF资金流向',
        'score_function': lambda flow: min(100, max(0, 50 + flow / 1000000000 * 5)),
        'weight': 0.2,
    },
}
```

#### 5.1.5 估值水平 (权重: 15%)
```python
valuation_indicators = {
    'market_pe': {
        'name': '市场PE',
        'optimal_range': (12, 18),
        'score_function': lambda x: 100 - abs(x - 15) * 5,
        'weight': 0.35,
    },
    'market_pb': {
        'name': '市场PB',
        'optimal_range': (1.5, 2.5),
        'score_function': lambda x: 100 - abs(x - 2) * 30,
        'weight': 0.25,
    },
    'pe_percentile': {
        'name': 'PE历史分位',
        'score_function': lambda pct: 100 - pct,
        'weight': 0.2,
    },
    'risk_premium': {
        'name': '股权风险溢价',
        'optimal_range': (2.0, 4.0),
        'score_function': lambda x: min(100, x * 25),
        'weight': 0.2,
    },
}
```

## 6. 行业指标量化因子评估体系

### 6.1 评估指标

#### 6.1.1 行业轮动 (权重: 25%)
```python
industry_rotation_indicators = {
    'relative_strength': {
        'name': '相对强度',
        'score_function': lambda industry_return, market_return: 50 + (industry_return - market_return) * 5,
        'weight': 0.35,
    },
    'momentum_score': {
        'name': '动量得分',
        'score_function': lambda returns_5d, returns_20d: 50 + returns_5d * 3 + returns_20d * 2,
        'weight': 0.3,
    },
    'sector_fund_flow': {
        'name': '板块资金流向',
        'score_function': lambda flow: min(100, max(0, 50 + flow / 1000000000 * 10)),
        'weight': 0.35,
    },
}
```

#### 6.1.2 技术发展趋势 (权重: 20%)
```python
tech_trend_indicators = {
    'rd_investment_growth': {
        'name': '研发投入增速',
        'score_function': lambda x: min(100, 50 + x * 3),
        'weight': 0.3,
    },
    'patent_growth': {
        'name': '专利申请增速',
        'score_function': lambda x: min(100, 50 + x * 2),
        'weight': 0.25,
    },
    'tech_event_impact': {
        'name': '技术事件影响',
        'score_function': lambda events: min(100, 50 + len(positive_events) * 10 - len(negative_events) * 10),
        'weight': 0.25,
    },
    'innovation_index': {
        'name': '创新指数',
        'score_function': lambda x: x,
        'weight': 0.2,
    },
}
```

#### 6.1.3 供应链波动 (权重: 20%)
```python
supply_chain_indicators = {
    'inventory_cycle': {
        'name': '库存周期',
        'values': {
            'restocking': 80,  # 补库存
            'neutral': 50,
            'destocking': 30,  # 去库存
        },
        'weight': 0.3,
    },
    'raw_material_price': {
        'name': '原材料价格变动',
        'score_function': lambda change: 50 - change * 5,  # 原材料价格上涨对下游不利
        'weight': 0.25,
    },
    'logistics_index': {
        'name': '物流指数',
        'score_function': lambda x: min(100, x),
        'weight': 0.25,
    },
    'supply_chain_stability': {
        'name': '供应链稳定性',
        'score_function': lambda disruptions: max(0, 100 - disruptions * 20),
        'weight': 0.2,
    },
}
```

#### 6.1.4 行业周期 (权重: 20%)
```python
industry_cycle_indicators = {
    'cycle_position': {
        'name': '周期位置',
        'values': {
            'early_expansion': 90,  # 早期扩张
            'expansion': 75,  # 扩张期
            'late_expansion': 60,  # 晚期扩张
            'peak': 50,  # 顶部
            'early_contraction': 35,  # 早期收缩
            'contraction': 25,  # 收缩期
            'late_contraction': 40,  # 晚期收缩
        },
        'weight': 0.35,
    },
    'profit_cycle': {
        'name': '盈利周期',
        'score_function': lambda profit_growth: min(100, max(0, 50 + profit_growth * 3)),
        'weight': 0.3,
    },
    'capacity_utilization': {
        'name': '产能利用率',
        'optimal_range': (75, 85),
        'score_function': lambda x: 100 - abs(x - 80) * 2,
        'weight': 0.2,
    },
    'capex_cycle': {
        'name': '资本开支周期',
        'score_function': lambda capex_growth: min(100, max(0, 50 + capex_growth * 2)),
        'weight': 0.15,
    },
}
```

#### 6.1.5 事件图谱关联 (权重: 15%)
```python
event_graph_indicators = {
    'policy_events': {
        'name': '政策事件影响',
        'score_function': lambda events: calculate_event_impact(events, 'policy'),
        'weight': 0.35,
    },
    'market_events': {
        'name': '市场事件影响',
        'score_function': lambda events: calculate_event_impact(events, 'market'),
        'weight': 0.3,
    },
    'tech_breakthrough': {
        'name': '技术突破事件',
        'score_function': lambda events: calculate_event_impact(events, 'tech'),
        'weight': 0.35,
    },
}

def calculate_event_impact(events: list, event_type: str) -> float:
    """
    计算事件对行业的影响得分
    
    Args:
        events: 事件列表
        event_type: 事件类型
    
    Returns:
        影响得分 (0-100)
    """
    filtered_events = [e for e in events if e['type'] == event_type]
    if not filtered_events:
        return 50
    
    total_impact = 0
    for event in filtered_events:
        importance_weight = {'critical': 1.0, 'high': 0.7, 'medium': 0.4, 'low': 0.2}
        direction = 1 if event['impact_direction'] == 'positive' else -1 if event['impact_direction'] == 'negative' else 0
        weight = importance_weight.get(event['importance'], 0.3)
        
        # 时间衰减因子
        days_ago = (datetime.now() - event['event_date']).days
        time_decay = max(0.1, 1 - days_ago / 30)
        
        total_impact += direction * weight * time_decay * 20
    
    return min(100, max(0, 50 + total_impact))
```

## 7. 数据采集任务配置

### 7.1 财联社事件采集任务
```yaml
# pipelines.yaml
- pipeline_id: collect_cls_events
  name: "财联社事件采集"
  schedule: "*/5 * * * *"  # 每5分钟
  tasks:
    - task_id: collect_cls_telegraph
      type: "collector"
      collector: "CLSNewsCollector"
      params:
        count: 100
    - task_id: extract_events
      type: "processor"
      processor: "EventExtractor"
      depends_on: [collect_cls_telegraph]
    - task_id: classify_events
      type: "processor"
      processor: "EventClassifier"
      depends_on: [extract_events]
    - task_id: save_events
      type: "writer"
      writer: "EventWriter"
      depends_on: [classify_events]
```

### 7.2 宏观数据采集任务
```yaml
- pipeline_id: collect_macro_data
  name: "宏观数据采集"
  schedule: "0 9 * * *"  # 每天早上9点
  tasks:
    - task_id: collect_china_macro
      type: "collector"
      collector: "ChinaMacroCollector"
    - task_id: collect_us_macro
      type: "collector"
      collector: "USMacroCollector"
    - task_id: calculate_macro_scores
      type: "processor"
      processor: "MacroScoreCalculator"
      depends_on: [collect_china_macro, collect_us_macro]
```

## 8. API接口设计

### 8.1 获取市场概览评分
```
GET /api/analysis/overview
```

### 8.2 获取维度详情
```
GET /api/analysis/overview/{dimension}
```

### 8.3 获取事件列表
```
GET /api/analysis/events?category={category}&start_date={start_date}&end_date={end_date}
```

### 8.4 获取事件详情
```
GET /api/analysis/events/{event_id}
```

## 9. 前端展示调整

### 9.1 概览页面
- 移除个股维度展示
- 保留四个维度：全球宏观、中国宏观、股市大盘、行业情况
- 每个维度展示评分、关键指标、相关事件

### 9.2 公司页面
- 保留个股分析功能
- 展示财务健康、利润质量、现金流、技术面、情绪面评分
