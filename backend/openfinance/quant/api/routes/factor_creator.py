"""
Factor Creator API Routes for OpenFinance quantitative system.

Provides endpoints for AI-powered factor creation using the skill-based chat system.
"""

import json
import logging
import re
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from openfinance.api.routes.chat import get_chat_service, ChatMessage
from openfinance.agents.llm.client import get_llm_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/factor-creator", tags=["quant_factor_creator"])

SKILL_ID = "quant-factor-creator"


class FactorGenerateRequest(BaseModel):
    """Request to generate factor from natural language description."""
    
    description: str = Field(..., description="Natural language description of the factor")
    name: Optional[str] = Field(None, description="Optional factor name")
    context: Optional[dict[str, Any]] = Field(None, description="Additional context")


class FactorCreateRequest(BaseModel):
    """Request to create factor with structured parameters."""
    
    name: str = Field(..., description="Factor name")
    description: str = Field(..., description="Factor description")
    factor_type: str = Field(default="technical", description="Factor type")
    category: str = Field(default="custom", description="Factor category")
    lookback_period: int = Field(default=20, ge=1, le=500, description="Lookback period")
    parameters: Optional[dict[str, Any]] = Field(default=None, description="Factor parameters")
    data_requirements: list[str] = Field(default=["close"], description="Required data fields")
    tags: Optional[list[str]] = Field(default=None, description="Factor tags")


class FactorSaveRequest(BaseModel):
    """Request to save a generated factor."""
    
    factor_id: str = Field(..., description="Factor ID")
    name: str = Field(..., description="Factor name")
    code: str = Field(..., description="Factor Python code")
    description: str = Field(..., description="Factor description")
    factor_type: str = Field(default="technical")
    category: str = Field(default="custom")
    lookback_period: int = Field(default=20)
    parameters: Optional[dict[str, Any]] = Field(default=None)
    tags: Optional[list[str]] = Field(default=None)


class FactorGenerateResponse(BaseModel):
    """Response for factor generation."""
    
    success: bool
    factor_id: str
    name: str
    code: str
    description: str
    factor_type: str
    category: str
    lookback_period: int
    parameters: dict[str, Any]
    validation: dict[str, Any]
    explanation: str
    created_at: str


class TemplateListResponse(BaseModel):
    """Response for template list."""
    
    templates: dict[str, str]
    total: int


def extract_code_from_response(content: str) -> str:
    """Extract Python code from LLM response."""
    code_patterns = [
        r'```python\s*(.*?)\s*```',
        r'```\s*(.*?)\s*```',
        r'def\s+\w+\s*\([^)]*\):.*?(?=\n\n|\Z)',
    ]
    
    for pattern in code_patterns:
        match = re.search(pattern, content, re.DOTALL)
        if match:
            return match.group(1).strip() if match.lastindex else match.group(0).strip()
    
    return content


def extract_factor_info(content: str) -> dict[str, Any]:
    """Extract factor information from LLM response."""
    info = {
        "name": "",
        "description": "",
        "factor_type": "technical",
        "category": "custom",
        "lookback_period": 20,
        "parameters": {},
    }
    
    name_match = re.search(r'(?:因子名称|Factor Name|name)[：:]\s*(.+?)(?:\n|$)', content, re.IGNORECASE)
    if name_match:
        info["name"] = name_match.group(1).strip()
    
    desc_match = re.search(r'(?:因子描述|Description|description)[：:]\s*(.+?)(?:\n\n|\n[A-Z]|$)', content, re.DOTALL | re.IGNORECASE)
    if desc_match:
        info["description"] = desc_match.group(1).strip()
    
    type_match = re.search(r'(?:因子类型|Factor Type|type)[：:]\s*(\w+)', content, re.IGNORECASE)
    if type_match:
        info["factor_type"] = type_match.group(1).lower()
    
    category_match = re.search(r'(?:因子类别|Category|category)[：:]\s*(\w+)', content, re.IGNORECASE)
    if category_match:
        info["category"] = category_match.group(1).lower()
    
    period_match = re.search(r'(?:回看周期|Lookback Period|period)[：:]\s*(\d+)', content, re.IGNORECASE)
    if period_match:
        info["lookback_period"] = int(period_match.group(1))
    
    return info


def generate_factor_id(name: str) -> str:
    """Generate a unique factor ID from name."""
    clean_name = re.sub(r'[^a-zA-Z0-9\u4e00-\u9fff]', '_', name.lower())
    clean_name = re.sub(r'_+', '_', clean_name).strip('_')
    
    chinese_to_pinyin = {
        '动量': 'momentum', '波动': 'volatility', '成交量': 'volume',
        '价格': 'price', '收益': 'return', '风险': 'risk',
        '反转': 'reversal', '趋势': 'trend', '价值': 'value',
        '质量': 'quality', '成长': 'growth',
    }
    
    for cn, en in chinese_to_pinyin.items():
        clean_name = clean_name.replace(cn, en)
    
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"factor_{clean_name}_{timestamp}"


def validate_factor_code(code: str) -> dict[str, Any]:
    """Validate generated factor code."""
    result = {
        "is_valid": True,
        "syntax_valid": False,
        "imports_valid": False,
        "logic_valid": False,
        "errors": [],
        "warnings": [],
    }
    
    try:
        compile(code, "<string>", "exec")
        result["syntax_valid"] = True
    except SyntaxError as e:
        result["is_valid"] = False
        result["errors"].append(f"语法错误: 第{e.lineno}行 - {e.msg}")
    
    required_keywords = ["def", "return", "numpy", "np"]
    for kw in required_keywords:
        if kw not in code:
            result["warnings"].append(f"建议包含: {kw}")
    
    if "def _calculate" in code or "def calculate" in code:
        result["logic_valid"] = True
    else:
        result["is_valid"] = False
        result["errors"].append("缺少计算函数")
    
    result["imports_valid"] = True
    
    return result


def build_factor_prompt(description: str, name: Optional[str] = None, context: Optional[dict] = None) -> str:
    """Build prompt for factor generation."""
    prompt = f"""请根据以下描述创建一个量化因子：

因子描述：{description}

请生成完整的Python因子代码，根据因子类型选择合适的数据模型。因子可以使用单一数据源，也可以组合多个数据源。

## 数据模型说明

### 1. 行情数据模型 ADSKLineModel（技术因子）

```python
from openfinance.datacenter.models.analytical import ADSKLineModel

class ADSKLineModel:
    code: str               # 股票代码（6位）
    trade_date: date        # 交易日期
    open: float             # 开盘价
    high: float             # 最高价
    low: float              # 最低价
    close: float            # 收盘价
    volume: int             # 成交量
    amount: float           # 成交额
    pre_close: float        # 前收盘价
    change: float           # 涨跌额
    change_pct: float       # 涨跌幅
    turnover_rate: float    # 换手率
    amplitude: float        # 振幅
    market_cap: float       # 总市值
    circulating_market_cap: float  # 流通市值
```

### 2. 资金流向数据模型 ADSMoneyFlowModel（资金流因子）

```python
from openfinance.datacenter.models.analytical import ADSMoneyFlowModel

class ADSMoneyFlowModel:
    code: str               # 股票代码
    trade_date: date        # 交易日期
    main_net_inflow: float  # 主力净流入
    main_net_inflow_pct: float  # 主力净流入占比
    super_large_net_inflow: float  # 超大单净流入
    large_net_inflow: float    # 大单净流入
    medium_net_inflow: float   # 中单净流入
    small_net_inflow: float    # 小单净流入
    north_net_inflow: float    # 北向资金净流入
```

### 3. 财务指标数据模型 ADSFinancialIndicatorModel（基本面因子）

```python
from openfinance.datacenter.models.analytical import ADSFinancialIndicatorModel

class ADSFinancialIndicatorModel:
    code: str           # 股票代码
    report_date: date   # 报告期
    
    # 盈利能力指标
    roe: float          # 净资产收益率
    roa: float          # 总资产收益率
    gross_margin: float # 毛利率
    net_margin: float   # 净利率
    operating_margin: float  # 营业利润率
    
    # 每股指标
    eps: float          # 每股收益
    bps: float          # 每股净资产
    
    # 偿债能力指标
    debt_ratio: float   # 资产负债率
    current_ratio: float # 流动比率
    quick_ratio: float  # 速动比率
    
    # 成长能力指标
    revenue_yoy: float      # 营收同比增长
    net_profit_yoy: float   # 净利润同比增长
    operating_profit_yoy: float  # 营业利润同比增长
    
    # 规模指标
    revenue: float          # 营业收入
    net_profit: float       # 净利润
    operating_profit: float # 营业利润
    total_assets: float     # 总资产
    total_equity: float     # 净资产
```

### 4. 利润表数据模型 ADSIncomeStatementModel（收入利润因子）

```python
from openfinance.datacenter.models.analytical import ADSIncomeStatementModel

class ADSIncomeStatementModel:
    code: str               # 股票代码
    report_date: date       # 报告期
    total_revenue: float    # 营业总收入
    operating_revenue: float    # 营业收入
    cost_of_goods_sold: float   # 营业成本
    selling_expenses: float     # 销售费用
    admin_expenses: float       # 管理费用
    rd_expenses: float          # 研发费用
    finance_expenses: float     # 财务费用
    operating_profit: float     # 营业利润
    net_profit: float           # 净利润
    basic_eps: float            # 基本每股收益
```

### 5. 现金流数据模型 ADSCashFlowModel（现金流因子）

```python
from openfinance.datacenter.models.analytical import ADSCashFlowModel

class ADSCashFlowModel:
    code: str               # 股票代码
    report_date: date       # 报告期
    net_cash_from_operating: float   # 经营活动现金流净额
    net_cash_from_investing: float   # 投资活动现金流净额
    net_cash_from_financing: float   # 筹资活动现金流净额
    free_cash_flow: float            # 自由现金流
    dividends_paid: float            # 分红支付的现金
    cash_received_from_sales: float  # 销售商品收到的现金
```

### 6. 资产负债表数据模型 ADSBalanceSheetModel（资产负债因子）

```python
from openfinance.datacenter.models.analytical import ADSBalanceSheetModel

class ADSBalanceSheetModel:
    code: str               # 股票代码
    report_date: date       # 报告期
    total_assets: float         # 总资产
    total_current_assets: float # 流动资产合计
    cash: float                 # 货币资金
    accounts_receivable: float  # 应收账款
    inventory: float            # 存货
    fixed_assets: float         # 固定资产
    intangible_assets: float    # 无形资产
    total_liabilities: float    # 负债合计
    total_equity: float         # 所有者权益合计
    short_term_debt: float      # 短期借款
    long_term_debt: float       # 长期借款
```

### 7. 股东数据模型 ADSShareholderModel（股权因子）

```python
from openfinance.datacenter.models.analytical import ADSShareholderModel

class ADSShareholderModel:
    code: str               # 股票代码
    report_date: date       # 报告期
    shareholder_name: str       # 股东名称
    shareholder_type: str       # 股东类型: individual/institution/government
    shares_held: float          # 持股数量
    shares_ratio: float         # 持股比例
    shares_change: float        # 持股变动
    is_actual_controller: bool  # 是否实际控制人
    pledge_shares: float        # 质押股数
    pledge_ratio: float         # 质押比例
```

### 8. 股票情绪数据模型 ADSStockSentimentModel（情绪因子）

```python
from openfinance.datacenter.models.analytical import ADSStockSentimentModel

class ADSStockSentimentModel:
    code: str               # 股票代码
    trade_date: date        # 交易日期
    news_count: int             # 相关新闻数量
    positive_count: int         # 正面新闻数量
    negative_count: int         # 负面新闻数量
    overall_sentiment: float    # 综合情绪得分 [-1, 1]
    sentiment_momentum: float   # 情绪动量
    social_mentions: int        # 社交媒体提及数
    social_sentiment: float     # 社交情绪得分
    analyst_rating: str         # 分析师评级
    target_price: float         # 目标价
```

### 9. 市场情绪数据模型 ADSMarketSentimentModel（市场情绪因子）

```python
from openfinance.datacenter.models.analytical import ADSMarketSentimentModel

class ADSMarketSentimentModel:
    trade_date: date            # 交易日期
    market: str                 # 市场: sh/sz/all
    advance_count: int          # 上涨家数
    decline_count: int          # 下跌家数
    limit_up_count: int         # 涨停家数
    limit_down_count: int       # 跌停家数
    bull_strength: float        # 多头强度 [-1, 1]
    fear_greed_index: float     # 恐惧贪婪指数 [0, 100]
    north_net_inflow: float     # 北向资金净流入
    margin_balance: float       # 融资余额
```

### 10. 宏观经济数据模型 ADSMacroEconomicModel（宏观因子）

```python
from openfinance.datacenter.models.analytical import ADSMacroEconomicModel

class ADSMacroEconomicModel:
    trade_date: date            # 日期
    indicator_id: str           # 指标ID
    indicator_name: str         # 指标名称
    indicator_type: str         # 指标类型: leading/coincident/lagging
    country: str                # 国家代码
    value: float                # 指标值
    value_yoy: float            # 同比变化
    value_mom: float            # 环比变化
    consensus: float            # 市场一致预期
```

## 多数据源因子示例

当因子需要组合多个数据源时，函数签名应包含多个参数：

```python
from typing import Optional, List
from openfinance.datacenter.models.analytical import (
    ADSKLineModel,
    ADSFinancialIndicatorModel,
    ADSCashFlowModel,
)

def calculate_factor(
    klines: List[ADSKLineModel],
    financials: List[ADSFinancialIndicatorModel],
    cash_flows: List[ADSCashFlowModel],
    period: int = 8  # 季度数
) -> Optional[float]:
    '''
    多数据源因子计算
    
    Args:
        klines: 行情数据列表
        financials: 财务指标列表
        cash_flows: 现金流数据列表
        period: 回看周期（季度）
    
    Returns:
        float: 因子值
    '''
    # 数据验证
    if not financials or len(financials) < period:
        return None
    if not cash_flows or len(cash_flows) < period:
        return None
    
    # 计算逻辑...
    return result
```

## 重要说明

1. **分红相关因子**：使用 ADSCashFlowModel 的 `dividends_paid` 字段，或结合 ADSFinancialIndicatorModel 计算股息支付率(DPR)
2. **利润率因子**：使用 ADSFinancialIndicatorModel 的 `net_margin`, `gross_margin`, `roe` 等
3. **稳定性因子**：需要多期数据，计算标准差、变异系数等
4. **资金流因子**：使用 ADSMoneyFlowModel 的主力资金流向数据
5. **情绪因子**：使用 ADSStockSentimentModel 的情绪得分数据
6. **多数据源因子**：可组合行情、财务、资金流等多个数据源

## 代码格式要求

请按照以下格式输出：

## 因子信息
- 因子名称：xxx
- 因子描述：xxx
- 因子类型：xxx（technical/fundamental/sentiment/alternative/multi_source）
- 因子类别：xxx（momentum/value/quality/volatility/liquidity/growth/flow/custom）
- 回看周期：xxx（技术因子为天数，基本面因子为季度数）
- 数据模型：xxx（列出所有使用的数据模型）

## 因子代码
```python
import numpy as np
from typing import Optional, List
# 根据因子类型导入合适的数据模型
from openfinance.datacenter.models.analytical import ADSKLineModel  # 或其他模型

def calculate_factor(data: List, period: int = 20) -> Optional[float]:
    '''
    因子计算函数
    
    Args:
        data: 数据列表，按时间升序排列（最旧在前，最新在后）
        period: 回看周期
    
    Returns:
        float: 因子值，数据不足时返回None
    '''
    # 输入验证
    if not data or len(data) < period:
        return None
    
    # 计算逻辑
    # ...
    
    return result
```

## 使用说明
简要说明因子的使用方法和注意事项。
"""
    
    if name:
        prompt = prompt.replace("因子名称：xxx", f"因子名称：{name}")
    
    return prompt


@router.post("/generate", response_model=FactorGenerateResponse)
async def generate_factor(request: FactorGenerateRequest):
    """
    Generate a factor from natural language description using the skill-based chat system.
    """
    try:
        service = get_chat_service()
        llm_client = get_llm_client()
        
        skill = service.get_skill(SKILL_ID)
        if not skill:
            raise HTTPException(status_code=404, detail=f"Skill not found: {SKILL_ID}")
        
        prompt = build_factor_prompt(request.description, request.name, request.context)
        
        messages = []
        system_prompt = service.build_system_prompt(SKILL_ID, skill)
        messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        response = await llm_client.chat(messages)
        content = response if isinstance(response, str) else str(response)
        
        code = extract_code_from_response(content)
        factor_info = extract_factor_info(content)
        
        if not factor_info["name"]:
            factor_info["name"] = request.name or "自定义因子"
        if not factor_info["description"]:
            factor_info["description"] = request.description
        
        factor_id = generate_factor_id(factor_info["name"])
        validation_result = validate_factor_code(code)
        
        explanation = f"""该因子"{factor_info['name']}"已根据您的描述生成：

**因子类型**: {factor_info['factor_type']}
**因子类别**: {factor_info['category']}
**回看周期**: {factor_info['lookback_period']}天

**因子逻辑**:
{factor_info['description']}

**验证结果**: {'通过' if validation_result['is_valid'] else '存在问题'}
"""
        
        return FactorGenerateResponse(
            success=validation_result.get("is_valid", False),
            factor_id=factor_id,
            name=factor_info["name"],
            code=code,
            description=factor_info["description"],
            factor_type=factor_info["factor_type"],
            category=factor_info["category"],
            lookback_period=factor_info["lookback_period"],
            parameters=factor_info["parameters"],
            validation=validation_result,
            explanation=explanation,
            created_at=datetime.now().isoformat(),
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error generating factor: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate/stream")
async def generate_factor_stream(request: FactorGenerateRequest):
    """
    Generate a factor with streaming response using the skill-based chat system.
    
    Returns SSE events with:
    - status: processing status
    - content: streaming LLM response
    - result: final parsed factor data
    """
    try:
        service = get_chat_service()
        llm_client = get_llm_client()
        
        skill = service.get_skill(SKILL_ID)
        if not skill:
            raise HTTPException(status_code=404, detail=f"Skill not found: {SKILL_ID}")
        
        prompt = build_factor_prompt(request.description, request.name, request.context)
        
        async def generate():
            full_content = ""
            
            yield f"data: {json.dumps({'type': 'status', 'status': 'thinking', 'message': '正在分析因子需求...'}, ensure_ascii=False)}\n\n"
            
            messages = []
            system_prompt = service.build_system_prompt(SKILL_ID, skill)
            messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            yield f"data: {json.dumps({'type': 'status', 'status': 'generating', 'message': '正在生成因子代码...'}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'type': 'content_start'}, ensure_ascii=False)}\n\n"
            
            async for chunk in llm_client.stream(messages):
                full_content += chunk
                yield f"data: {json.dumps({'type': 'content', 'content': chunk}, ensure_ascii=False)}\n\n"
            
            yield f"data: {json.dumps({'type': 'content_end'}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'type': 'status', 'status': 'parsing', 'message': '正在解析因子信息...'}, ensure_ascii=False)}\n\n"
            
            code = extract_code_from_response(full_content)
            factor_info = extract_factor_info(full_content)
            
            if not factor_info["name"]:
                factor_info["name"] = request.name or "自定义因子"
            if not factor_info["description"]:
                factor_info["description"] = request.description
            
            factor_id = generate_factor_id(factor_info["name"])
            validation_result = validate_factor_code(code)
            
            explanation = f"""该因子"{factor_info['name']}"已根据您的描述生成：

**因子类型**: {factor_info['factor_type']}
**因子类别**: {factor_info['category']}
**回看周期**: {factor_info['lookback_period']}天

**因子逻辑**:
{factor_info['description']}

**验证结果**: {'通过' if validation_result['is_valid'] else '存在问题'}
"""
            
            result = {
                "success": validation_result.get("is_valid", False),
                "factor_id": factor_id,
                "name": factor_info["name"],
                "code": code,
                "description": factor_info["description"],
                "factor_type": factor_info["factor_type"],
                "category": factor_info["category"],
                "lookback_period": factor_info["lookback_period"],
                "parameters": factor_info["parameters"],
                "validation": validation_result,
                "explanation": explanation,
                "created_at": datetime.now().isoformat(),
            }
            
            yield f"data: {json.dumps({'type': 'result', 'data': result}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'type': 'status', 'status': 'complete', 'message': '因子生成完成'}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
        
        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error generating factor stream: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/create", response_model=FactorGenerateResponse)
async def create_factor(request: FactorCreateRequest):
    """
    Create a factor from structured parameters.
    """
    try:
        service = get_chat_service()
        llm_client = get_llm_client()
        
        skill = service.get_skill(SKILL_ID)
        if not skill:
            raise HTTPException(status_code=404, detail=f"Skill not found: {SKILL_ID}")
        
        prompt = f"""请根据以下参数创建一个量化因子：

因子名称：{request.name}
因子描述：{request.description}
因子类型：{request.factor_type}
因子类别：{request.category}
回看周期：{request.lookback_period}天
数据需求：{', '.join(request.data_requirements)}
"""
        
        if request.parameters:
            prompt += f"\n参数配置：{json.dumps(request.parameters, ensure_ascii=False)}"
        
        messages = []
        system_prompt = service.build_system_prompt(SKILL_ID, skill)
        messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        response = await llm_client.chat(messages)
        content = response if isinstance(response, str) else str(response)
        
        code = extract_code_from_response(content)
        factor_id = generate_factor_id(request.name)
        validation_result = validate_factor_code(code)
        
        explanation = f"""因子"{request.name}"已成功创建：

**因子ID**: {factor_id}
**因子类型**: {request.factor_type}
**因子类别**: {request.category}
**回看周期**: {request.lookback_period}天

**描述**:
{request.description}
"""
        
        return FactorGenerateResponse(
            success=validation_result.get("is_valid", False),
            factor_id=factor_id,
            name=request.name,
            code=code,
            description=request.description,
            factor_type=request.factor_type,
            category=request.category,
            lookback_period=request.lookback_period,
            parameters=request.parameters or {},
            validation=validation_result,
            explanation=explanation,
            created_at=datetime.now().isoformat(),
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error creating factor: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/save")
async def save_factor(request: FactorSaveRequest):
    """
    Save a generated factor to the registry and file system.
    
    The factor will be:
    1. Saved as a Python file in factors/indicators/custom/
    2. Registered in the factor registry
    3. Persisted to the database
    """
    try:
        from openfinance.quant.factors.registry import get_factor_registry
        from openfinance.quant.factors.base import FactorType, FactorCategory
        from pathlib import Path
        import re
        
        registry = get_factor_registry()
        
        custom_dir = Path(__file__).parent.parent.parent / "factors" / "indicators" / "custom"
        custom_dir.mkdir(parents=True, exist_ok=True)
        
        safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', request.factor_id.replace("factor_", ""))
        safe_name = re.sub(r'_+', '_', safe_name).strip('_')
        
        if not safe_name:
            import hashlib
            safe_name = hashlib.md5(request.factor_id.encode()).hexdigest()[:12]
        
        factor_file = custom_dir / f"{safe_name}.py"
        
        class_name = ''.join(word.capitalize() for word in safe_name.split('_'))
        
        factor_type_enum = FactorType.TECHNICAL
        if request.factor_type == "fundamental":
            factor_type_enum = FactorType.FUNDAMENTAL
        elif request.factor_type == "alternative":
            factor_type_enum = FactorType.ALTERNATIVE
        else:
            factor_type_enum = FactorType.CUSTOM
        
        category_enum = FactorCategory.CUSTOM
        category_map = {
            "momentum": FactorCategory.MOMENTUM,
            "volatility": FactorCategory.VOLATILITY,
            "value": FactorCategory.VALUE,
            "quality": FactorCategory.QUALITY,
            "growth": FactorCategory.GROWTH,
            "liquidity": FactorCategory.LIQUIDITY,
            "flow": FactorCategory.FLOW,
        }
        category_enum = category_map.get(request.category, FactorCategory.CUSTOM)
        
        calculation_logic = extract_calculation_logic(request.code)
        
        data_models = detect_data_models(request.code)
        required_fields = get_required_fields(data_models)
        
        imports = "from openfinance.datacenter.models.analytical import ADSKLineModel\n"
        if data_models:
            imports = f"from openfinance.datacenter.models.analytical import {', '.join(data_models)}\n"
        
        calculate_params = "klines: List[ADSKLineModel]"
        if "ADSFinancialIndicatorModel" in data_models:
            calculate_params += ",\n        financials: List[ADSFinancialIndicatorModel] = None"
        if "ADSCashFlowModel" in data_models:
            calculate_params += ",\n        cash_flows: List[ADSCashFlowModel] = None"
        if "ADSMoneyFlowModel" in data_models:
            calculate_params += ",\n        money_flows: List[ADSMoneyFlowModel] = None"
        if "ADSBalanceSheetModel" in data_models:
            calculate_params += ",\n        balance_sheets: List[ADSBalanceSheetModel] = None"
        if "ADSIncomeStatementModel" in data_models:
            calculate_params += ",\n        income_statements: List[ADSIncomeStatementModel] = None"
        if "ADSShareholderModel" in data_models:
            calculate_params += ",\n        shareholders: List[ADSShareholderModel] = None"
        if "ADSStockSentimentModel" in data_models:
            calculate_params += ",\n        sentiments: List[ADSStockSentimentModel] = None"
        if "ADSMacroEconomicModel" in data_models:
            calculate_params += ",\n        macro_data: List[ADSMacroEconomicModel] = None"
        
        factor_code = f'''"""
{request.name} - Custom Factor

{request.description}

Generated by AI Factor Creator
Data Models: {', '.join(data_models) if data_models else 'ADSKLineModel'}
"""

import numpy as np
from typing import Optional, List
{imports}from openfinance.quant.factors.base import (
    FactorBase,
    FactorMetadata,
    FactorType,
    FactorCategory,
)
from openfinance.quant.factors.registry import register_factor


@register_factor
class {class_name}Factor(FactorBase):
    """
    {request.name}
    
    {request.description}
    """
    
    def _default_metadata(self) -> FactorMetadata:
        return FactorMetadata(
            factor_id="{request.factor_id}",
            name="{request.name}",
            description="""{request.description}""",
            factor_type=FactorType.{factor_type_enum.name},
            category=FactorCategory.{category_enum.name},
            lookback_period={request.lookback_period},
            required_fields={required_fields},
            tags={request.tags or []},
            author="user",
        )
    
    def _calculate(self, {calculate_params}, **params) -> Optional[float]:
        \'\'\'Calculate factor value.\'\'\'
{calculation_logic}
'''

        with open(factor_file, "w", encoding="utf-8") as f:
            f.write(factor_code)
        
        logger.info(f"Saved factor file: {factor_file}")
        
        try:
            import importlib
            import sys
            
            module_name = f"openfinance.quant.factors.indicators.custom.{safe_name}"
            if module_name in sys.modules:
                importlib.reload(sys.modules[module_name])
            else:
                importlib.import_module(module_name)
            
            logger.info(f"Loaded factor module: {module_name}")
        except Exception as e:
            logger.warning(f"Failed to load factor module: {e}")
        
        try:
            import asyncpg
            import os
            
            db_url = os.getenv(
                "DATABASE_URL",
                "postgresql://openfinance:openfinance@localhost:5432/openfinance"
            )
            if "+asyncpg" in db_url:
                db_url = db_url.replace("+asyncpg", "")
            
            conn = await asyncpg.connect(db_url)
            
            await conn.execute("""
                INSERT INTO openfinance.factors 
                (factor_id, name, code, description, factor_type, category, lookback_period, parameters, tags, status, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, 'active', NOW(), NOW())
                ON CONFLICT (factor_id) DO UPDATE SET
                    name = EXCLUDED.name,
                    code = EXCLUDED.code,
                    description = EXCLUDED.description,
                    updated_at = NOW()
            """,
                request.factor_id,
                request.name,
                request.code,
                request.description,
                request.factor_type,
                request.category,
                request.lookback_period,
                request.parameters or {},
                request.tags or [],
            )
            
            await conn.close()
            
        except Exception as db_error:
            logger.warning(f"Database save failed: {db_error}")
        
        return {
            "success": True,
            "factor_id": request.factor_id,
            "message": f"因子 '{request.name}' 保存成功",
            "file_path": str(factor_file),
            "registered": True,
        }
    
    except Exception as e:
        logger.exception(f"Error saving factor: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def detect_data_models(code: str) -> list[str]:
    """Detect which data models are used in the factor code."""
    models = []
    model_patterns = {
        "ADSKLineModel": ["klines", "close", "open", "high", "low", "volume", "ADSKLineModel"],
        "ADSFinancialIndicatorModel": ["financial", "roe", "net_margin", "gross_margin", "eps", "ADSFinancialIndicatorModel"],
        "ADSCashFlowModel": ["cash_flow", "dividends_paid", "free_cash_flow", "ADSCashFlowModel"],
        "ADSMoneyFlowModel": ["money_flow", "main_net_inflow", "north_net_inflow", "ADSMoneyFlowModel"],
        "ADSBalanceSheetModel": ["balance_sheet", "total_assets", "total_liabilities", "ADSBalanceSheetModel"],
        "ADSIncomeStatementModel": ["income_statement", "total_revenue", "operating_profit", "ADSIncomeStatementModel"],
        "ADSShareholderModel": ["shareholder", "shares_held", "shares_ratio", "ADSShareholderModel"],
        "ADSStockSentimentModel": ["sentiment", "overall_sentiment", "news_count", "ADSStockSentimentModel"],
        "ADSMacroEconomicModel": ["macro", "indicator", "gdp", "cpi", "ADSMacroEconomicModel"],
    }
    
    code_lower = code.lower()
    for model, keywords in model_patterns.items():
        for keyword in keywords:
            if keyword.lower() in code_lower:
                if model not in models:
                    models.append(model)
                break
    
    if not models:
        models = ["ADSKLineModel"]
    
    return models


def get_required_fields(data_models: list[str]) -> list[str]:
    """Get required fields based on data models."""
    fields = []
    
    model_field_map = {
        "ADSKLineModel": ["close"],
        "ADSFinancialIndicatorModel": ["financial_data"],
        "ADSCashFlowModel": ["cash_flow"],
        "ADSMoneyFlowModel": ["money_flow"],
        "ADSBalanceSheetModel": ["balance_sheet"],
        "ADSIncomeStatementModel": ["income_statement"],
        "ADSShareholderModel": ["shareholder"],
        "ADSStockSentimentModel": ["sentiment"],
        "ADSMacroEconomicModel": ["macro"],
    }
    
    for model in data_models:
        if model in model_field_map:
            fields.extend(model_field_map[model])
    
    return fields if fields else ["close"]


def extract_calculation_logic(code: str) -> str:
    """Extract and format calculation logic from generated code."""
    base_indent = "        "
    
    try:
        lines = code.strip().split('\n')
        result_lines = []
        in_function = False
        function_indent = 0
        function_body_start = 0
        min_body_indent = float('inf')
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            if stripped.startswith('def ') and 'calculate' in stripped.lower():
                in_function = True
                function_indent = len(line) - len(line.lstrip())
                continue
            
            if in_function:
                if not stripped:
                    continue
                if stripped.startswith('#') and '"""' not in stripped and "'''" not in stripped:
                    continue
                if stripped.startswith('"""') or stripped.startswith("'''"):
                    continue
                
                current_indent = len(line) - len(line.lstrip())
                if current_indent > function_indent:
                    if current_indent < min_body_indent:
                        min_body_indent = current_indent
                        function_body_start = len(result_lines)
                
                result_lines.append((current_indent, stripped))
        
        if result_lines:
            formatted_lines = []
            for original_indent, content in result_lines:
                relative_indent = original_indent - min_body_indent
                if relative_indent < 0:
                    relative_indent = 0
                new_indent = base_indent + "    " * (relative_indent // 4)
                formatted_lines.append(f"{new_indent}{content}")
            return '\n'.join(formatted_lines)
    except Exception as e:
        logger.warning(f"Failed to extract calculation logic: {e}")
    
    return '\n'.join([
        f"{base_indent}if not klines or len(klines) < self.metadata.lookback_period:",
        f"{base_indent}    return None",
        f"{base_indent}close = np.array([k.close for k in klines])",
        f"{base_indent}period = params.get('period', self.metadata.lookback_period)",
        f"{base_indent}if len(close) < period:",
        f"{base_indent}    return None",
        f"{base_indent}return float((close[-1] / close[-period]) - 1)",
    ])


@router.get("/templates", response_model=TemplateListResponse)
async def get_factor_templates():
    """
    Get available factor templates.
    """
    templates = {
        "momentum": "动量因子 - 计算价格变化率",
        "volatility": "波动率因子 - 计算收益率标准差",
        "volume_ratio": "成交量比 - 当前成交量与平均成交量比值",
        "risk_adjusted_momentum": "风险调整动量 - 收益率除以波动率",
        "price_position": "价格位置 - 当前价格在区间中的位置",
    }
    
    return TemplateListResponse(
        templates=templates,
        total=len(templates),
    )


@router.post("/validate")
async def validate_factor_endpoint(code: str):
    """
    Validate factor Python code.
    """
    result = validate_factor_code(code)
    
    return {
        "success": True,
        "validation": result,
    }


@router.get("/suggestions")
async def get_factor_suggestions(
    factor_type: Optional[str] = None,
    category: Optional[str] = None,
):
    """
    Get factor creation suggestions based on type and category.
    """
    suggestions = {
        "momentum": {
            "recommended_parameters": {
                "period": {"type": "int", "default": 20, "min": 5, "max": 120},
                "normalize": {"type": "bool", "default": True},
            },
            "data_requirements": ["close"],
            "description_template": "计算过去{period}天的价格动量，衡量股票的趋势强度",
        },
        "volatility": {
            "recommended_parameters": {
                "period": {"type": "int", "default": 20, "min": 5, "max": 120},
                "annualize": {"type": "bool", "default": True},
            },
            "data_requirements": ["close"],
            "description_template": "计算过去{period}天的收益率波动率，衡量风险水平",
        },
        "value": {
            "recommended_parameters": {
                "metric": {"type": "str", "default": "pe", "options": ["pe", "pb", "ps", "ev_ebitda"]},
            },
            "data_requirements": ["close", "financial_data"],
            "description_template": "基于{metric}指标的价值因子",
        },
        "quality": {
            "recommended_parameters": {
                "metrics": {"type": "list", "default": ["roe", "roa", "net_margin"]},
            },
            "data_requirements": ["financial_data"],
            "description_template": "综合质量因子，结合盈利能力和财务健康指标",
        },
    }
    
    if factor_type and factor_type in suggestions:
        return {
            "success": True,
            "suggestions": suggestions[factor_type],
        }
    
    return {
        "success": True,
        "suggestions": suggestions,
        "available_types": list(suggestions.keys()),
    }
