# Wavelet 智能分析页面改造计划 v2

## 一、项目概述

### 1.1 改造目标
将智能分析页面改造为以"Wavelet（小波变换）"为核心的金融市场分析平台，从多维度展示市场全景，提供智能评分、趋势图表、事件关联和LLM分析功能。

### 1.2 核心理念
- **Wavelet** = 金融市场的小波变换，捕捉市场的多尺度特征
- 从宏观到微观，层层递进的分析框架
- **数据可视化优先**：图表展示趋势，事件标注关键节点
- **知识图谱关联**：事件与实体的智能关联

---

## 二、页面整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                      Wavelet 智能分析平台                         │
├─────────────────────────────────────────────────────────────────┤
│  📊 市场概览仪表盘                                               │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  综合评分趋势图（带事件标注）                                  ││
│  │  100├─────────────────────────────────────────────────      ││
│  │   80├──────●━━━━━●━━━━━━━━━●━━━━━━━━━━━━━●━━━━━            ││
│  │   60├─────/│\────/│\────────────────────────               ││
│  │   40├──────┴──────┴────────────────────────────             ││
│  │     └──┬──────┬──────┬──────┬──────┬──────┬──→ 时间        ││
│  │        │      │      │      │      │      │                 ││
│  │     [降息] [PMI回升] [政策] [财报季] [事件]                  ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                  │
│  ┌─────────┬─────────┬─────────┬─────────┬─────────┐           │
│  │全球宏观  │中国宏观  │股市大盘  │行业情况  │个股情况  │           │
│  │  65分   │  72分   │  58分   │  70分   │  85分   │           │
│  │  📈+3   │  📉-2   │  📈+5   │  📊→   │  📈+8   │           │
│  └─────────┴─────────┴─────────┴─────────┴─────────┘           │
│  [LLM综合分析按钮]                                                │
├─────────────────────────────────────────────────────────────────┤
│  📈 维度详情区域（点击概览卡片展开）                               │
│  ├── 趋势图表 + 事件时间线                                        │
│  └── 知识图谱关联展示                                             │
├─────────────────────────────────────────────────────────────────┤
│  🤖 AI智能分析区域                                                │
└─────────────────────────────────────────────────────────────────┘
```

---

## 三、图表可视化设计

### 3.1 综合评分趋势图

#### 设计要点
- **主图**：折线图展示评分历史趋势（近30天/90天/1年）
- **事件标注**：在关键时间点标注重大事件
- **交互**：hover显示详情，点击事件跳转知识图谱

```typescript
interface ScoreTrendChart {
  scores: {
    date: string;
    total: number;
    dimensions: {
      global_macro: number;
      china_macro: number;
      market: number;
      industry: number;
      stock: number;
    };
  }[];
  events: ChartEvent[];
}

interface ChartEvent {
  id: string;
  date: string;
  title: string;
  type: 'policy' | 'economic' | 'market' | 'company' | 'global';
  importance: 'high' | 'medium' | 'low';
  impact: 'positive' | 'negative' | 'neutral';
  entities: string[];  // 关联实体ID
  description: string;
}
```

#### 视觉设计
```
评分趋势图
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
100 ┤
 80 ┤        ╭──╮        ╭────╮
 60 ┤    ╭───╯  ╰──╮  ╭──╯    ╰──╮
 40 ┤────╯          ╰──╯           ╰────
 20 ┤
    └──┬──────┬──────┬──────┬──────┬──────┬──→
       1/15   1/22   1/29   2/5    2/12   2/19

事件标注:
🔴 1/20 美联储降息25bp [全球宏观] ← 点击查看详情
🟢 1/25 中国PMI回升至50.5 [中国宏观]
🔵 2/1 春节后开门红 [股市大盘]
🟡 2/10 行业政策利好 [行业]
```

### 3.2 维度雷达图

```typescript
interface RadarChart {
  dimensions: string[];
  values: number[];          // 当前值
  previousValues: number[];  // 上期值（对比）
  benchmark?: number[];      // 基准值
}
```

```
        全球宏观
           65
            │
           ╱ ╲
          ╱   ╲
   行业情况─────中国宏观
    70    │     72
         ╱│╲
        ╱ │ ╲
       ╱  │  ╲
股市大盘───┼───个股情况
  58      │     85
          │
          
图例: ━━ 当前  ┄┄ 上期
```

### 3.3 维度详情趋势图

每个维度展示独立的趋势图，包含：

#### 3.3.1 全球宏观趋势图
```
全球宏观评分趋势
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
美联储利率 │ 美元指数 │ VIX恐慌指数 │ 大宗商品
    80 ┤    ╭────╮
    60 ┤╭───╯    ╰──╮      ╭──╮
    40 ┤╯           ╰──────╯  ╰────
       └──┬──────┬──────┬──────┬──→
         
事件: [美联储议息] [非农数据] [地缘政治]
```

#### 3.3.2 中国宏观趋势图
```
中国宏观评分趋势
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
GDP增速 │ CPI/PPI │ PMI │ M2/社融 │ 利率
    80 ┤        ╭──────╮
    60 ┤    ╭───╯      ╰──╮
    40 ┤────╯             ╰──────
       └──┬──────┬──────┬──────┬──→
         
事件: [央行降准] [PMI发布] [两会政策]
```

#### 3.3.3 股市大盘趋势图
```
股市大盘评分趋势
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
上证指数 │ 成交额 │ 涨跌比 │ 北向资金 │ 市场情绪
   100 ┤                    ╭────╮
    80 ┤        ╭──────╮╭──╯    ╰──╮
    60 ┤    ╭───╯      ╰╯          ╰──
    40 ┤────╯
       └──┬──────┬──────┬──────┬──────┬──→
         
事件: [突破3000点] [北向流入] [IPO暂停]
```

#### 3.3.4 行业趋势图
```
行业评分趋势（可切换行业）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
行业涨跌 │ 资金流向 │ 估值水平 │ 龙头表现
    80 ┤╭────╮      ╭──────╮
    60 ┤╯    ╰──────╯      ╰──────
    40 ┤
       └──┬──────┬──────┬──────┬──→
         
事件: [政策利好] [龙头业绩] [资金轮动]
```

#### 3.3.5 个股趋势图
```
个股评分趋势
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
财务健康 │ 利润质量 │ 现金流 │ 技术面 │ 情绪面
   100 ┤                              ╭──╮
    80 ┤        ╭──────╮      ╭──────╯  ╰
    60 ┤    ╭───╯      ╰──────╯
    40 ┤────╯
       └──┬──────┬──────┬──────┬──────┬──→
         
事件: [财报发布] [机构调研] [大宗交易] [研报覆盖]
```

---

## 四、事件关联系统

### 4.1 事件数据模型

```typescript
interface MarketEvent {
  id: string;
  title: string;
  summary: string;
  content?: string;
  
  // 时间信息
  eventDate: string;
  publishDate: string;
  
  // 分类
  category: 'global_macro' | 'china_macro' | 'market' | 'industry' | 'company';
  type: 'policy' | 'economic' | 'corporate' | 'market' | 'geopolitical';
  importance: 'critical' | 'high' | 'medium' | 'low';
  
  // 影响评估
  impact: {
    direction: 'positive' | 'negative' | 'neutral';
    magnitude: number;  // 1-10
    affectedDimensions: string[];
    scoreChange?: number;
  };
  
  // 知识图谱关联
  entities: {
    id: string;
    type: 'stock' | 'industry' | 'concept' | 'person' | 'organization';
    name: string;
    relation: string;
  }[];
  
  // 来源
  source: {
    name: string;
    url?: string;
    confidence: number;
  };
  
  // AI分析
  aiAnalysis?: string;
}
```

### 4.2 事件时间线组件

```
┌─────────────────────────────────────────────────────────────────┐
│  📅 事件时间线                                                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  2024年2月                                                       │
│  ├── 🔴 2/20 美联储降息25bp                                      │
│  │   └── 影响: 全球宏观+5分，股市大盘+3分                         │
│  │   └── 关联: [美联储] [美元] [全球市场]                         │
│  │                                                               │
│  ├── 🟢 2/15 中国PMI回升至50.5                                   │
│  │   └── 影响: 中国宏观+3分                                      │
│  │   └── 关联: [制造业] [经济复苏]                               │
│  │                                                               │
│  ├── 🔵 2/10 春节后开门红                                        │
│  │   └── 影响: 股市大盘+8分                                      │
│  │   └── 关联: [上证指数] [北向资金]                             │
│  │                                                               │
│  └── 🟡 2/5 行业政策利好                                         │
│      └── 影响: 行业情况+5分                                      │
│      └── 关联: [新能源] [光伏] [宁德时代]                         │
│                                                                  │
│  [加载更多]                                                      │
└─────────────────────────────────────────────────────────────────┘
```

### 4.3 知识图谱关联展示

```
┌─────────────────────────────────────────────────────────────────┐
│  🔗 事件关联图谱                                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│                    ┌──────────┐                                  │
│                    │ 美联储降息 │                                  │
│                    └────┬─────┘                                  │
│                         │                                        │
│          ┌──────────────┼──────────────┐                        │
│          ↓              ↓              ↓                        │
│    ┌──────────┐   ┌──────────┐   ┌──────────┐                  │
│    │ 美元下跌  │   │ 全球股市  │   │ 大宗商品  │                  │
│    └────┬─────┘   └────┬─────┘   └────┬─────┘                  │
│         │              │              │                         │
│         ↓              ↓              ↓                         │
│    ┌──────────┐   ┌──────────┐   ┌──────────┐                  │
│    │ 人民币升值│   │ A股上涨  │   │ 黄金上涨  │                  │
│    └──────────┘   └────┬─────┘   └──────────┘                  │
│                        │                                        │
│              ┌─────────┼─────────┐                              │
│              ↓         ↓         ↓                              │
│        ┌────────┐ ┌────────┐ ┌────────┐                        │
│        │贵州茅台│ │宁德时代│ │中国平安│                        │
│        └────────┘ └────────┘ └────────┘                        │
│                                                                  │
│  [查看完整图谱] [导出报告]                                        │
└─────────────────────────────────────────────────────────────────┘
```

### 4.4 事件详情卡片

```
┌─────────────────────────────────────────────────────────────────┐
│  📰 美联储降息25bp                                               │
├─────────────────────────────────────────────────────────────────┤
│  时间: 2024-02-20 03:00                                         │
│  类型: 全球宏观 > 货币政策                                       │
│  重要性: ⭐⭐⭐⭐⭐                                               │
│                                                                  │
│  📝 事件摘要:                                                    │
│  美联储宣布将联邦基金利率下调25个基点至4.75%-5.00%，              │
│  符合市场预期。鲍威尔表示通胀已取得进展，但需更多证据...           │
│                                                                  │
│  📊 影响评估:                                                    │
│  ┌────────────┬────────┬────────┐                               │
│  │ 维度       │ 影响   │ 变化   │                               │
│  ├────────────┼────────┼────────┤                               │
│  │ 全球宏观   │ 正面   │ +5分   │                               │
│  │ 股市大盘   │ 正面   │ +3分   │                               │
│  │ 行业情况   │ 中性   │ +1分   │                               │
│  └────────────┴────────┴────────┘                               │
│                                                                  │
│  🔗 关联实体:                                                    │
│  [美联储] [美元指数] [纳斯达克] [黄金] [原油]                     │
│  [贵州茅台] [宁德时代] [中国平安]                                │
│                                                                  │
│  🤖 AI分析:                                                      │
│  此次降息标志着美联储货币政策转向，全球流动性改善，               │
│  有利于风险资产估值修复。建议关注成长股和黄金资产...              │
│                                                                  │
│  [查看知识图谱] [相关新闻] [历史类似事件]                         │
└─────────────────────────────────────────────────────────────────┘
```

---

## 五、个股分析模块增强

### 5.1 个股概览评分卡（增强版）

```
┌─────────────────────────────────────────────────────────────────┐
│  📈 贵州茅台 (600519)                                            │
│  当前价: 1856.00  涨跌: +2.35%  市值: 2.33万亿                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  综合评分趋势                                                    │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│  100 ┤                              ╭──╮                        │
│   80 ┤        ╭──────╮      ╭──────╯  ╰───                      │
│   60 ┤    ╭───╯      ╰──────╯                                    │
│   40 ┤────╯                                                      │
│       └──┬──────┬──────┬──────┬──────┬──→                       │
│          1月    1月    2月    2月    2月                         │
│                                                                  │
│  事件: [财报发布] [分红方案] [机构调研]                          │
│                                                                  │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────┐       │
│  │ 财务健康  │ 利润质量  │ 现金流    │ 技术面    │ 情绪面    │       │
│  │   90分   │   85分   │   80分   │   75分   │   70分   │       │
│  │  ▲+2    │  ▲+5    │  ▼-3    │  ▲+8    │  ▼-5    │       │
│  └──────────┴──────────┴──────────┴──────────┴──────────┘       │
│                                                                  │
│  📊 各维度趋势                                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ 财务健康 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │    │
│  │ 利润质量 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │    │
│  │ 现金流   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │    │
│  │ 技术面   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │    │
│  │ 情绪面   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  📅 近期事件                                                     │
│  ├── 2/20 年报披露: 净利润646亿，同比+18%                        │
│  ├── 2/15 分红方案: 每10股派发现金红利259元                      │
│  └── 2/10 机构调研: 30家机构参与调研                             │
│                                                                  │
│  [AI投资建议] [详细分析] [知识图谱]                              │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 五维度详细分析

#### 财务健康度卡片
```
┌─────────────────────────────────────────────────────────────────┐
│  💰 财务健康度分析                                    评分: 90分  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ROE趋势                                                         │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│   30% ┤───────╮                                                 │
│   25% ┤       ╰──────╮                                          │
│   20% ┤              ╰──────╮                                   │
│   15% ┤                    ╰──────                              │
│        └──┬──────┬──────┬──────┬──→                            │
│           2021   2022   2023   2024                             │
│                                                                  │
│  关键指标                                                        │
│  ┌─────────────┬─────────┬─────────┬─────────┐                  │
│  │ 指标        │ 当前值   │ 行业均值 │ 评价    │                  │
│  ├─────────────┼─────────┼─────────┼─────────┤                  │
│  │ ROE         │ 25.6%   │ 15.2%   │ 优秀 ▲  │                  │
│  │ 资产负债率   │ 12.8%   │ 45.3%   │ 健康 ▲ │                  │
│  │ 毛利率      │ 68.4%   │ 35.2%   │ 优秀 ▲ │                  │
│  │ 流动比率    │ 8.5     │ 1.8     │ 优秀 ▲ │                  │
│  └─────────────┴─────────┴─────────┴─────────┘                  │
│                                                                  │
│  📅 相关事件                                                     │
│  • 2024/02/20 年报披露，ROE维持高位                              │
│  • 2023/10/25 三季报，财务指标稳健                               │
│                                                                  │
│  🤖 AI分析:                                                      │
│  公司财务状况极佳，ROE持续高于行业均值，负债率低，               │
│  流动性充裕。财务健康度在同行业中处于领先地位...                  │
└─────────────────────────────────────────────────────────────────┘
```

#### 技术面分析卡片
```
┌─────────────────────────────────────────────────────────────────┐
│  📈 技术面分析                                        评分: 75分  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  K线图 + 均线                                                    │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│  1900 ┤    ╭──╮     ╭──╮                                        │
│  1850 ┤╭───╯  ╰─────╯  ╰───╮                                    │
│  1800 ┤╯                  ╰────                                  │
│  1750 ┤                                                          │
│        └──┬──────┬──────┬──────┬──→                            │
│                                                                  │
│  ─── MA5  ─── MA20  ─── MA60                                    │
│                                                                  │
│  技术指标                                                        │
│  ┌─────────────┬─────────┬─────────────────────┐                │
│  │ 指标        │ 当前值   │ 信号               │                │
│  ├─────────────┼─────────┼─────────────────────┤                │
│  │ MA趋势      │ 多头排列 │ 看涨 📈            │                │
│  │ RSI(14)     │ 65      │ 偏强，未超买        │                │
│  │ MACD        │ 金叉    │ 看涨信号 📈        │                │
│  │ KDJ         │ 72      │ 偏强                │                │
│  │ 布林带      │ 中轨上方 │ 强势区域           │                │
│  └─────────────┴─────────┴─────────────────────┘                │
│                                                                  │
│  支撑位: 1800 / 1750    压力位: 1900 / 1950                      │
│                                                                  │
│  📅 关键K线事件                                                  │
│  • 2024/02/19 突破1850压力位，成交量放大                         │
│  • 2024/02/10 金叉形成，买入信号                                 │
│                                                                  │
│  🤖 AI分析:                                                      │
│  技术面整体偏强，均线多头排列，MACD金叉确认上涨趋势。             │
│  短期关注1900压力位突破情况，支撑位1800...                        │
└─────────────────────────────────────────────────────────────────┘
```

#### 情绪面分析卡片
```
┌─────────────────────────────────────────────────────────────────┐
│  📰 情绪面分析                                        评分: 70分  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  新闻情绪趋势                                                    │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│  正面 ┤    ╭──────╮      ╭──╮                                   │
│  中性 ┤╭───╯      ╰──────╯  ╰───                                │
│  负面 ┤╯                                                        │
│        └──┬──────┬──────┬──────┬──→                            │
│                                                                  │
│  情绪分布                                                        │
│  ┌─────────────────────────────────────────────┐                │
│  │ 正面 ████████████████████████ 60%           │                │
│  │ 中性 ████████████ 30%                       │                │
│  │ 负面 █████ 10%                               │                │
│  └─────────────────────────────────────────────┘                │
│                                                                  │
│  📰 近期新闻                                                     │
│  ┌─────────────────────────────────────────────┐                │
│  │ 😊 茅台年报超预期，净利润同比增长18%        │ 02/20          │
│  │ 😊 分红方案出炉，股息率达3.5%               │ 02/15          │
│  │ 😐 白酒板块整体回调                         │ 02/12          │
│  │ 😊 机构调研热情高涨，30家机构参与           │ 02/10          │
│  └─────────────────────────────────────────────┘                │
│                                                                  │
│  📊 机构评级                                                     │
│  ┌─────────────────────────────────────────────┐                │
│  │ 买入 ████████████████████ 20家  80%         │                │
│  │ 增持 █████ 3家  12%                         │                │
│  │ 中性 ███ 2家  8%                            │                │
│  └─────────────────────────────────────────────┘                │
│                                                                  │
│  🤖 AI分析:                                                      │
│  市场情绪整体偏正面，年报超预期提振信心，机构以买入评级          │
│  为主。需关注白酒板块整体走势对情绪的影响...                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## 六、后端API设计

### 6.1 评分趋势API

```python
@router.get("/api/analysis/overview/trend")
async def get_overview_trend(
    period: str = "30d",  # 30d, 90d, 1y
    dimensions: str = None
) -> OverviewTrendResponse:
    """
    获取市场概览评分趋势
    
    Returns:
        - scores: 各维度评分历史数据
        - events: 关键事件列表
        - statistics: 统计信息（均值、波动率等）
    """
    pass

@router.get("/api/analysis/stock/{code}/trend")
async def get_stock_trend(
    code: str,
    period: str = "90d"
) -> StockTrendResponse:
    """
    获取个股评分趋势
    
    Returns:
        - scores: 五维度评分历史
        - events: 相关事件
        - price: 股价走势
    """
    pass
```

### 6.2 事件API

```python
@router.get("/api/analysis/events")
async def get_events(
    category: str = None,
    start_date: str = None,
    end_date: str = None,
    importance: str = None,
    limit: int = 50
) -> List[EventResponse]:
    """
    获取事件列表
    """
    pass

@router.get("/api/analysis/events/{event_id}")
async def get_event_detail(event_id: str) -> EventDetailResponse:
    """
    获取事件详情，包含知识图谱关联
    """
    pass

@router.get("/api/analysis/events/{event_id}/graph")
async def get_event_graph(event_id: str) -> EventGraphResponse:
    """
    获取事件关联的知识图谱
    """
    pass

@router.post("/api/analysis/events")
async def create_event(event: EventCreateRequest) -> EventResponse:
    """
    创建事件（用于数据采集）
    """
    pass
```

### 6.3 知识图谱关联API

```python
@router.get("/api/analysis/entity/{entity_id}/events")
async def get_entity_events(
    entity_id: str,
    limit: int = 20
) -> List[EventResponse]:
    """
    获取实体关联的事件
    """
    pass

@router.get("/api/analysis/graph/event-impact")
async def get_event_impact_graph(
    event_id: str
) -> ImpactGraphResponse:
    """
    获取事件影响图谱
    
    Returns:
        - nodes: 受影响的实体节点
        - edges: 影响关系和程度
    """
    pass
```

---

## 七、数据库设计

### 7.1 评分历史表

```sql
CREATE TABLE openfinance.score_history (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    dimension VARCHAR(50) NOT NULL,  -- global_macro, china_macro, market, industry, stock
    score DECIMAL(5,2) NOT NULL,
    sub_scores JSONB,  -- 子维度评分
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(date, dimension)
);

-- 个股评分历史
CREATE TABLE openfinance.stock_score_history (
    id SERIAL PRIMARY KEY,
    code VARCHAR(10) NOT NULL,
    date DATE NOT NULL,
    total_score DECIMAL(5,2) NOT NULL,
    financial_score DECIMAL(5,2),
    profit_score DECIMAL(5,2),
    cashflow_score DECIMAL(5,2),
    tech_score DECIMAL(5,2),
    sentiment_score DECIMAL(5,2),
    details JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(code, date)
);
```

### 7.2 事件表

```sql
CREATE TABLE openfinance.market_events (
    id SERIAL PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    summary TEXT,
    content TEXT,
    
    event_date TIMESTAMP NOT NULL,
    publish_date TIMESTAMP,
    
    category VARCHAR(50) NOT NULL,  -- global_macro, china_macro, market, industry, company
    type VARCHAR(50) NOT NULL,      -- policy, economic, corporate, market, geopolitical
    importance VARCHAR(20) NOT NULL, -- critical, high, medium, low
    
    impact_direction VARCHAR(20),    -- positive, negative, neutral
    impact_magnitude DECIMAL(3,1),   -- 1-10
    affected_dimensions JSONB,
    score_change JSONB,
    
    entities JSONB,  -- 关联实体 [{id, type, name, relation}]
    
    source_name VARCHAR(200),
    source_url TEXT,
    confidence DECIMAL(3,2),
    
    ai_analysis TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 事件实体关联表
CREATE TABLE openfinance.event_entity_relations (
    id SERIAL PRIMARY KEY,
    event_id INTEGER REFERENCES openfinance.market_events(id),
    entity_id VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,  -- stock, industry, concept, person, organization
    entity_name VARCHAR(200),
    relation_type VARCHAR(100),
    impact_score DECIMAL(3,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 八、前端组件设计

### 8.1 组件结构

```
components/analysis/
├── Overview/
│   ├── index.tsx                    # 概览主组件
│   ├── ScoreTrendChart.tsx          # 评分趋势图（带事件标注）
│   ├── DimensionCard.tsx            # 维度卡片
│   ├── RadarChart.tsx               # 雷达图
│   └── EventTimeline.tsx            # 事件时间线
├── Events/
│   ├── EventCard.tsx                # 事件卡片
│   ├── EventDetail.tsx              # 事件详情
│   ├── EventGraph.tsx               # 事件关联图谱
│   └── EventFilter.tsx              # 事件筛选器
├── StockAnalysis/
│   ├── index.tsx                    # 个股分析主组件
│   ├── ScoreTrendChart.tsx          # 评分趋势图
│   ├── DimensionBreakdown.tsx       # 维度分解
│   ├── FinancialHealthCard.tsx      # 财务健康卡
│   ├── ProfitQualityCard.tsx        # 利润质量卡
│   ├── CashflowCard.tsx             # 现金流卡
│   ├── TechCard.tsx                 # 技术面卡
│   ├── SentimentCard.tsx            # 情绪面卡
│   └── StockEventTimeline.tsx       # 个股事件时间线
├── Graph/
│   ├── EventImpactGraph.tsx         # 事件影响图谱
│   └── EntityRelationGraph.tsx      # 实体关系图谱
└── common/
    ├── ScoreMeter.tsx               # 评分仪表
    ├── TrendIndicator.tsx           # 趋势指示器
    ├── EventMarker.tsx              # 事件标记
    ├── AIAnalysisPanel.tsx          # AI分析面板
    └── ChartTooltip.tsx             # 图表提示框
```

### 8.2 图表交互设计

```typescript
// 趋势图交互
interface TrendChartInteraction {
  // Hover事件
  onPointHover: (point: DataPoint) => {
    showTooltip: boolean;
    tooltipContent: React.ReactNode;
    highlightEvent: boolean;
  };
  
  // 点击事件标记
  onEventClick: (event: ChartEvent) => {
    showEventDetail: boolean;
    navigateToGraph: boolean;
  };
  
  // 时间范围选择
  onPeriodChange: (period: '7d' | '30d' | '90d' | '1y') => void;
  
  // 维度切换
  onDimensionToggle: (dimension: string, visible: boolean) => void;
}
```

---

## 九、实施计划

### Phase 1: 后端评分系统 (2天)
- [ ] 实现评分计算逻辑
- [ ] 创建评分历史表
- [ ] 实现评分趋势API
- [ ] 实现事件存储和查询API

### Phase 2: 前端概览模块 (2天)
- [ ] 实现评分趋势图组件
- [ ] 实现事件标注功能
- [ ] 实现雷达图组件
- [ ] 实现维度卡片组件

### Phase 3: 事件系统 (2天)
- [ ] 实现事件时间线组件
- [ ] 实现事件详情卡片
- [ ] 实现事件筛选器
- [ ] 集成知识图谱API

### Phase 4: 个股分析模块 (2天)
- [ ] 实现个股评分趋势图
- [ ] 实现五维度详细卡片
- [ ] 实现个股事件时间线
- [ ] 实现事件影响图谱

### Phase 5: LLM分析集成 (1天)
- [ ] 实现概览AI分析
- [ ] 实现事件AI分析
- [ ] 实现个股AI分析
- [ ] 优化Prompt模板

### Phase 6: 测试与优化 (1天)
- [ ] 功能测试
- [ ] 性能优化
- [ ] UI/UX优化
- [ ] 文档完善

---

## 十、关键技术点

### 10.1 图表库选择
- **ECharts** - 主图表库，支持丰富的图表类型和交互
- **React-ECharts** - React封装，便于组件化开发

### 10.2 事件标注实现
```typescript
// ECharts事件标注配置
const eventMarkPoint = {
  symbol: 'pin',
  symbolSize: 30,
  itemStyle: {
    color: (params: any) => {
      const event = events.find(e => e.date === params.name);
      return event?.impact === 'positive' ? '#52c41a' : 
             event?.impact === 'negative' ? '#ff4d4f' : '#faad14';
    }
  },
  label: {
    show: true,
    formatter: (params: any) => {
      const event = events.find(e => e.date === params.name);
      return event?.title.slice(0, 4);
    }
  },
  data: events.map(e => ({
    name: e.date,
    value: e.score,
    event: e
  }))
};
```

### 10.3 知识图谱集成
```typescript
// 使用现有知识图谱API
const fetchEventGraph = async (eventId: string) => {
  const event = await fetch(`/api/analysis/events/${eventId}`);
  const graph = await fetch(`/api/graph/entity/${event.entities[0].id}`);
  return {
    nodes: graph.nodes,
    edges: graph.edges,
    centerEvent: event
  };
};
```
