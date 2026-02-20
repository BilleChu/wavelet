"""
Quant Factor Creator - AI-powered factor generation module.

This module provides functionality to create custom quantitative factors
based on natural language descriptions using LLM capabilities.
"""

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class FactorParameter:
    name: str
    param_type: str = "float"
    default: Any = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    description: str = ""
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "type": self.param_type,
            "default": self.default,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "description": self.description,
        }


@dataclass
class FactorCreationRequest:
    name: str
    description: str
    factor_type: str = "technical"
    category: str = "custom"
    lookback_period: int = 20
    parameters: list[FactorParameter] = field(default_factory=list)
    data_requirements: list[str] = field(default_factory=lambda: ["close"])
    tags: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "factor_type": self.factor_type,
            "category": self.category,
            "lookback_period": self.lookback_period,
            "parameters": [p.to_dict() for p in self.parameters],
            "data_requirements": self.data_requirements,
            "tags": self.tags,
        }


@dataclass
class GeneratedFactor:
    factor_id: str
    name: str
    code: str
    description: str
    factor_type: str
    category: str
    lookback_period: int
    parameters: dict[str, Any]
    validation_result: dict[str, Any]
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> dict:
        return {
            "factor_id": self.factor_id,
            "name": self.name,
            "code": self.code,
            "description": self.description,
            "factor_type": self.factor_type,
            "category": self.category,
            "lookback_period": self.lookback_period,
            "parameters": self.parameters,
            "validation": self.validation_result,
            "created_at": self.created_at.isoformat(),
        }


FACTOR_TEMPLATES = {
    "momentum": '''
def calculate_momentum(df, period=20):
    """
    Calculate momentum factor.
    
    Momentum is calculated as the percentage change over the lookback period.
    
    Args:
        df: DataFrame with 'close' column
        period: Lookback period in days
    
    Returns:
        Momentum value (percentage change)
    """
    close = df['close']
    if len(close) < period + 1:
        return None
    
    momentum = (close.iloc[-1] / close.iloc[-period - 1] - 1) * 100
    return momentum
''',
    "volatility": '''
def calculate_volatility(df, period=20):
    """
    Calculate volatility factor.
    
    Volatility is calculated as the annualized standard deviation of daily returns.
    
    Args:
        df: DataFrame with 'close' column
        period: Lookback period in days
    
    Returns:
        Annualized volatility
    """
    import numpy as np
    
    close = df['close']
    if len(close) < period + 1:
        return None
    
    returns = close.pct_change().dropna()
    volatility = returns.tail(period).std() * np.sqrt(252) * 100
    return volatility
''',
    "volume_ratio": '''
def calculate_volume_ratio(df, period=20):
    """
    Calculate volume ratio factor.
    
    Volume ratio compares current volume to average volume.
    
    Args:
        df: DataFrame with 'volume' column
        period: Lookback period for average calculation
    
    Returns:
        Volume ratio (current / average)
    """
    volume = df['volume']
    if len(volume) < period:
        return None
    
    avg_volume = volume.tail(period).mean()
    if avg_volume == 0:
        return None
    
    ratio = volume.iloc[-1] / avg_volume
    return ratio
''',
    "risk_adjusted_momentum": '''
def calculate_risk_adjusted_momentum(df, period=20):
    """
    Calculate risk-adjusted momentum factor.
    
    This factor measures momentum per unit of risk (volatility).
    
    Args:
        df: DataFrame with 'close' column
        period: Lookback period in days
    
    Returns:
        Risk-adjusted momentum (return / volatility)
    """
    import numpy as np
    
    close = df['close']
    if len(close) < period + 1:
        return None
    
    returns = close.pct_change().dropna()
    
    momentum = (close.iloc[-1] / close.iloc[-period - 1] - 1)
    volatility = returns.tail(period).std() * np.sqrt(252)
    
    if volatility == 0:
        return 0
    
    return momentum / volatility
''',
    "price_position": '''
def calculate_price_position(df, period=20):
    """
    Calculate price position factor.
    
    Measures where current price sits within the period range.
    
    Args:
        df: DataFrame with 'high', 'low', 'close' columns
        period: Lookback period in days
    
    Returns:
        Price position (0-1 scale)
    """
    high = df['high'].tail(period)
    low = df['low'].tail(period)
    close = df['close'].iloc[-1]
    
    period_high = high.max()
    period_low = low.min()
    
    if period_high == period_low:
        return 0.5
    
    position = (close - period_low) / (period_high - period_low)
    return position
''',
}


def generate_factor_id(name: str) -> str:
    """Generate a unique factor ID from name."""
    clean_name = re.sub(r'[^a-zA-Z0-9\u4e00-\u9fff]', '_', name.lower())
    clean_name = re.sub(r'_+', '_', clean_name).strip('_')
    
    chinese_to_pinyin = {
        '动量': 'momentum',
        '波动': 'volatility',
        '成交量': 'volume',
        '价格': 'price',
        '收益': 'return',
        '风险': 'risk',
        '反转': 'reversal',
        '趋势': 'trend',
        '价值': 'value',
        '质量': 'quality',
        '成长': 'growth',
    }
    
    for cn, en in chinese_to_pinyin.items():
        clean_name = clean_name.replace(cn, en)
    
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"factor_{clean_name}_{timestamp}"


def extract_parameters_from_description(description: str) -> list[FactorParameter]:
    """Extract potential parameters from natural language description."""
    parameters = []
    
    period_match = re.search(r'(\d+)\s*[天日]', description)
    if period_match:
        parameters.append(FactorParameter(
            name="period",
            param_type="int",
            default=int(period_match.group(1)),
            min_value=5,
            max_value=250,
            description="Lookback period in days",
        ))
    
    threshold_match = re.search(r'([0-9.]+)\s*[%％]', description)
    if threshold_match:
        parameters.append(FactorParameter(
            name="threshold",
            param_type="float",
            default=float(threshold_match.group(1)) / 100,
            min_value=0.001,
            max_value=1.0,
            description="Threshold value",
        ))
    
    return parameters


def detect_factor_type(description: str) -> tuple[str, str]:
    """Detect factor type and category from description."""
    description_lower = description.lower()
    
    type_keywords = {
        "technical": ["价格", "成交量", "均线", "macd", "rsi", "kdj", "布林", "技术", "动量", "波动"],
        "fundamental": ["财务", "盈利", "营收", "现金流", "资产负债", "roe", "pe", "pb"],
        "sentiment": ["情绪", "舆情", "新闻", "关注度", "讨论"],
        "alternative": ["另类", "卫星", "电商", "搜索"],
    }
    
    category_keywords = {
        "momentum": ["动量", "趋势", "涨跌", "收益"],
        "value": ["价值", "估值", "pe", "pb", "股息"],
        "quality": ["质量", "盈利能力", "财务健康"],
        "volatility": ["波动", "风险", "方差"],
        "liquidity": ["流动性", "成交量", "换手"],
        "growth": ["成长", "增长", "扩张"],
    }
    
    detected_type = "technical"
    for ftype, keywords in type_keywords.items():
        if any(kw in description_lower for kw in keywords):
            detected_type = ftype
            break
    
    detected_category = "custom"
    for cat, keywords in category_keywords.items():
        if any(kw in description_lower for kw in keywords):
            detected_category = cat
            break
    
    return detected_type, detected_category


def select_template(factor_type: str, category: str) -> str:
    """Select the most appropriate template based on factor type and category."""
    if category == "momentum":
        return FACTOR_TEMPLATES["momentum"]
    elif category == "volatility":
        return FACTOR_TEMPLATES["volatility"]
    elif "volume" in factor_type or "liquidity" in category:
        return FACTOR_TEMPLATES["volume_ratio"]
    elif "risk" in factor_type or "adjusted" in factor_type:
        return FACTOR_TEMPLATES["risk_adjusted_momentum"]
    elif "position" in factor_type or "range" in factor_type:
        return FACTOR_TEMPLATES["price_position"]
    else:
        return FACTOR_TEMPLATES["momentum"]


def generate_factor_code(
    request: FactorCreationRequest,
    template_code: str,
) -> str:
    """Generate complete factor code from request and template."""
    factor_id = generate_factor_id(request.name)
    
    params_str = ""
    if request.parameters:
        params_list = []
        for p in request.parameters:
            default_str = str(p.default) if p.default is not None else "None"
            params_list.append(f"{p.name}={default_str}")
        params_str = ", " + ", ".join(params_list)
    
    code = f'''"""
{request.name}

{request.description}

Factor ID: {factor_id}
Type: {request.factor_type}
Category: {request.category}
Lookback Period: {request.lookback_period} days
Created: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""

import numpy as np
import pandas as pd
from typing import Optional

from openfinance.quant.factors.base import FactorBase, FactorMetadata, ParameterDefinition
from openfinance.domain.models.quant import FactorType, FactorCategory


class {request.name.replace(" ", "").replace("-", "")}Factor(FactorBase):
    """
    {request.description}
    """
    
    def _default_metadata(self) -> FactorMetadata:
        return FactorMetadata(
            factor_id="{factor_id}",
            name="{request.name}",
            description="""{request.description}""",
            factor_type=FactorType.{request.factor_type.upper()},
            category=FactorCategory.{request.category.upper()},
            lookback_period={request.lookback_period},
            tags={request.tags if request.tags else []},
        )
    
    def _define_parameters(self) -> dict[str, ParameterDefinition]:
        return {{
{chr(10).join(f'            "{p.name}": ParameterDefinition(name="{p.name}", type="{p.param_type}", default={p.default}, min_value={p.min_value}, max_value={p.max_value}, description="{p.description}"),' for p in request.parameters) if request.parameters else '            # No custom parameters'}
        }}
    
    def _calculate(self, klines, **params) -> Optional[float]:
        """
        Calculate factor value.
        
        Args:
            klines: List of K-Line data
            **params: Factor parameters
        
        Returns:
            Calculated factor value or None
        """
        if len(klines) < self.lookback_period:
            return None
        
        # Extract price data
        close = np.array([k.close for k in klines])
        high = np.array([k.high for k in klines])
        low = np.array([k.low for k in klines])
        volume = np.array([k.volume for k in klines])
        
        # Get parameters
        period = params.get("period", self.lookback_period)
        
        # === Factor Calculation Logic ===
        # This is the core calculation - modify based on your factor logic
        
{template_code}
        
        return result


# Factor registration function
def get_factor():
    """Get factor instance for registration."""
    return {request.name.replace(" ", "").replace("-", "")}Factor()
'''
    
    return code


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
        result["errors"].append(f"Syntax error: {e}")
    
    required_imports = ["numpy", "pandas", "FactorBase"]
    for imp in required_imports:
        if imp not in code:
            result["warnings"].append(f"Missing import: {imp}")
    
    if "def _calculate" in code:
        result["logic_valid"] = True
    else:
        result["is_valid"] = False
        result["errors"].append("Missing _calculate method")
    
    result["imports_valid"] = True
    
    return result


async def create_factor_from_description(
    description: str,
    name: Optional[str] = None,
    context: Optional[dict[str, Any]] = None,
) -> GeneratedFactor:
    """
    Create a factor from natural language description.
    
    Args:
        description: Natural language description of the factor
        name: Optional factor name
        context: Additional context for factor creation
    
    Returns:
        GeneratedFactor with code and metadata
    """
    context = context or {}
    
    factor_type, category = detect_factor_type(description)
    parameters = extract_parameters_from_description(description)
    
    lookback_period = 20
    for p in parameters:
        if p.name == "period" and p.default:
            lookback_period = int(p.default)
    
    if not name:
        name_parts = description.split()[:3]
        name = "_".join(name_parts) if name_parts else "custom_factor"
    
    request = FactorCreationRequest(
        name=name,
        description=description,
        factor_type=factor_type,
        category=category,
        lookback_period=lookback_period,
        parameters=parameters,
        data_requirements=["close", "volume"],
        tags=[category, factor_type],
    )
    
    template_code = select_template(factor_type, category)
    
    code = generate_factor_code(request, template_code)
    
    validation_result = validate_factor_code(code)
    
    factor_id = generate_factor_id(name)
    
    return GeneratedFactor(
        factor_id=factor_id,
        name=name,
        code=code,
        description=description,
        factor_type=factor_type,
        category=category,
        lookback_period=lookback_period,
        parameters={p.name: p.default for p in parameters},
        validation_result=validation_result,
    )


async def create_factor_from_request(
    request: FactorCreationRequest,
) -> GeneratedFactor:
    """
    Create a factor from a structured request.
    
    Args:
        request: FactorCreationRequest with all parameters
    
    Returns:
        GeneratedFactor with code and metadata
    """
    template_code = select_template(request.factor_type, request.category)
    code = generate_factor_code(request, template_code)
    validation_result = validate_factor_code(code)
    
    factor_id = generate_factor_id(request.name)
    
    return GeneratedFactor(
        factor_id=factor_id,
        name=request.name,
        code=code,
        description=request.description,
        factor_type=request.factor_type,
        category=request.category,
        lookback_period=request.lookback_period,
        parameters={p.name: p.default for p in request.parameters},
        validation_result=validation_result,
    )


def get_available_templates() -> dict[str, str]:
    """Get list of available factor templates."""
    return {
        "momentum": "动量因子 - 计算价格变化率",
        "volatility": "波动率因子 - 计算收益率标准差",
        "volume_ratio": "成交量比 - 当前成交量与平均成交量比值",
        "risk_adjusted_momentum": "风险调整动量 - 收益率除以波动率",
        "price_position": "价格位置 - 当前价格在区间中的位置",
    }
