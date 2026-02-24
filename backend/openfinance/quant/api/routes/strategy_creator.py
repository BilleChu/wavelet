"""
Strategy Creator API Routes.

Provides endpoints for AI-powered strategy creation and management.
"""

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from openfinance.quant.strategy.base import (
    StrategyType,
    WeightMethod,
    RebalanceFrequency,
)
from openfinance.api.routes.chat import get_chat_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/strategy-creator", tags=["strategy_creator"])

SKILL_ID = "quant-strategy-creator"


class StrategyGenerateRequest(BaseModel):
    """Request for strategy generation."""
    description: str = Field(..., description="Strategy description")
    name: Optional[str] = Field(None, description="Strategy name")
    strategy_type: str = Field("multi_factor", description="Strategy type")
    factors: list[str] = Field(default_factory=list, description="Factor IDs")
    factor_weights: dict[str, float] = Field(default_factory=dict, description="Factor weights")
    weight_method: str = Field("equal_weight", description="Weight method")
    rebalance_freq: str = Field("monthly", description="Rebalance frequency")
    max_positions: int = Field(50, description="Max positions")
    stop_loss: Optional[float] = Field(None, description="Stop loss")
    take_profit: Optional[float] = Field(None, description="Take profit")
    context: Optional[dict[str, Any]] = None


class StrategySaveRequest(BaseModel):
    """Request for saving a strategy."""
    strategy_id: str
    name: str
    code: str
    description: str
    strategy_type: str = "multi_factor"
    factors: list[str] = Field(default_factory=list)
    factor_weights: dict[str, float] = Field(default_factory=dict)
    weight_method: str = "equal_weight"
    rebalance_freq: str = "monthly"
    max_positions: int = 50
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    tags: list[str] = Field(default_factory=list)


class StrategyGenerateResponse(BaseModel):
    """Response for strategy generation."""
    success: bool
    strategy_id: str
    name: str
    code: str
    description: str
    strategy_type: str
    factors: list[str]
    factor_weights: dict[str, float]
    validation: dict[str, Any]
    explanation: str
    created_at: str


class TemplateListResponse(BaseModel):
    """Response for template list."""
    templates: dict[str, str]
    total: int


def generate_strategy_id(name: str) -> str:
    """Generate a unique strategy ID from name."""
    import hashlib
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    safe_name = re.sub(r'[^a-zA-Z0-9]', '_', name.lower())[:20]
    hash_part = hashlib.md5(f"{name}{timestamp}".encode()).hexdigest()[:6]
    return f"strategy_{safe_name}_{hash_part}"


def build_strategy_prompt(request: StrategyGenerateRequest) -> str:
    """Build prompt for strategy generation."""
    factors_str = ', '.join(request.factors) if request.factors else '自动选择'
    weights_str = json.dumps(request.factor_weights) if request.factor_weights else '等权重'
    stop_loss_str = str(request.stop_loss) if request.stop_loss else '无'
    take_profit_str = str(request.take_profit) if request.take_profit else '无'
    
    prompt = f"""请根据以下描述创建一个量化策略：

策略描述：{request.description}

## 策略配置

- 策略类型：{request.strategy_type}
- 使用因子：{factors_str}
- 因子权重：{weights_str}
- 权重方法：{request.weight_method}
- 再平衡频率：{request.rebalance_freq}
- 最大持仓数：{request.max_positions}
- 止损：{stop_loss_str}
- 止盈：{take_profit_str}

## 代码格式要求

请按照以下格式输出：

## 策略信息
- 策略名称：xxx
- 策略描述：xxx
- 策略类型：xxx
- 使用因子：xxx

## 策略代码
"""
    
    code_template = '''
```python
from typing import Optional
import pandas as pd
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
    """策略名称 - 策略描述"""
    
    def _default_metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            strategy_id="strategy_xxx",
            name="策略名称",
            description="策略描述",
            strategy_type=StrategyType.MULTI_FACTOR,
            factor_ids=["factor_1", "factor_2"],
            tags=["tag1", "tag2"],
        )
    
    def generate_signals(self, data, factor_values=None, date=None):
        """生成交易信号，返回股票代码到信号强度的映射"""
        signals = {}
        # 信号生成逻辑
        return signals
    
    def calculate_portfolio_weights(self, signals, prices, covariance_matrix=None):
        """计算组合权重，返回股票代码到权重的映射"""
        weights = {}
        # 权重计算逻辑
        return weights
```

## 使用说明
简要说明策略的使用方法和注意事项。
'''
    
    return prompt + code_template


def extract_code_from_response(response: str) -> str:
    """Extract Python code from LLM response."""
    code_pattern = r'```python\s*(.*?)\s*```'
    matches = re.findall(code_pattern, response, re.DOTALL)
    
    if matches:
        return matches[0].strip()
    
    code_lines = []
    in_code = False
    for line in response.split('\n'):
        if 'def ' in line or 'class ' in line or line.startswith('import ') or line.startswith('from '):
            in_code = True
        if in_code:
            code_lines.append(line)
    
    return '\n'.join(code_lines)


def extract_strategy_info(response: str) -> dict:
    """Extract strategy information from LLM response."""
    info = {
        "name": "",
        "description": "",
        "strategy_type": "multi_factor",
        "factors": [],
        "tags": [],
    }
    
    name_match = re.search(r'策略名称[：:]\s*(.+)', response)
    if name_match:
        info["name"] = name_match.group(1).strip()
    
    desc_match = re.search(r'策略描述[：:]\s*(.+)', response)
    if desc_match:
        info["description"] = desc_match.group(1).strip()
    
    type_match = re.search(r'策略类型[：:]\s*(.+)', response)
    if type_match:
        info["strategy_type"] = type_match.group(1).strip()
    
    factors_match = re.search(r'使用因子[：:]\s*(.+)', response)
    if factors_match:
        factors_str = factors_match.group(1).strip()
        info["factors"] = [f.strip() for f in factors_str.split(',') if f.strip()]
    
    return info


def validate_strategy_code(code: str) -> dict:
    """Validate strategy code."""
    errors = []
    warnings = []
    
    try:
        compile(code, '<string>', 'exec')
    except SyntaxError as e:
        errors.append(f"语法错误: {e}")
    
    if 'BaseStrategy' not in code:
        errors.append("策略必须继承 BaseStrategy")
    
    if 'generate_signals' not in code:
        errors.append("策略必须实现 generate_signals 方法")
    
    if 'calculate_portfolio_weights' not in code:
        errors.append("策略必须实现 calculate_portfolio_weights 方法")
    
    if 'register_strategy' not in code:
        warnings.append("建议使用 @register_strategy 装饰器")
    
    return {
        "is_valid": len(errors) == 0,
        "syntax_valid": len([e for e in errors if '语法' in e]) == 0,
        "errors": errors,
        "warnings": warnings,
    }


@router.post("/generate", response_model=StrategyGenerateResponse)
async def generate_strategy(request: StrategyGenerateRequest):
    """
    Generate a strategy using the skill-based chat system.
    """
    try:
        service = get_chat_service()
        
        skill = service.get_skill(SKILL_ID)
        if not skill:
            raise HTTPException(status_code=404, detail=f"Skill not found: {SKILL_ID}")
        
        prompt = build_strategy_prompt(request)
        
        response = await service.chat(
            query=prompt,
            skill_id=SKILL_ID,
            history=[],
            context=request.context or {},
            session_id=None,
        )
        
        content = response.get("content", "")
        code = extract_code_from_response(content)
        strategy_info = extract_strategy_info(content)
        
        if not strategy_info["name"]:
            strategy_info["name"] = request.name or "自定义策略"
        if not strategy_info["description"]:
            strategy_info["description"] = request.description
        
        strategy_id = generate_strategy_id(strategy_info["name"])
        validation_result = validate_strategy_code(code)
        
        explanation = f"""该策略"{strategy_info['name']}"已根据您的描述生成：

**策略类型**: {strategy_info['strategy_type']}
**使用因子**: {', '.join(strategy_info['factors']) if strategy_info['factors'] else '根据描述推断'}

**策略逻辑**:
{strategy_info['description']}

**验证结果**: {'通过' if validation_result['is_valid'] else '存在问题'}
"""
        
        return StrategyGenerateResponse(
            success=validation_result.get("is_valid", False),
            strategy_id=strategy_id,
            name=strategy_info["name"],
            code=code,
            description=strategy_info["description"],
            strategy_type=strategy_info["strategy_type"],
            factors=request.factors or strategy_info["factors"],
            factor_weights=request.factor_weights,
            validation=validation_result,
            explanation=explanation,
            created_at=datetime.now().isoformat(),
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error generating strategy: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate/stream")
async def generate_strategy_stream(request: StrategyGenerateRequest):
    """
    Generate a strategy with streaming response.
    """
    try:
        service = get_chat_service()
        
        skill = service.get_skill(SKILL_ID)
        if not skill:
            raise HTTPException(status_code=404, detail=f"Skill not found: {SKILL_ID}")
        
        prompt = build_strategy_prompt(request)
        
        async def generate():
            full_content = ""
            
            yield f"data: {json.dumps({'type': 'status', 'status': 'thinking', 'message': '正在分析策略需求...'}, ensure_ascii=False)}\n\n"
            
            messages = []
            system_prompt = service.build_system_prompt(SKILL_ID, skill, include_full_content=True)
            messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            if service.llm_client and hasattr(service.llm_client, "stream"):
                yield f"data: {json.dumps({'type': 'status', 'status': 'generating', 'message': '正在生成策略代码...'}, ensure_ascii=False)}\n\n"
                yield f"data: {json.dumps({'type': 'content_start'}, ensure_ascii=False)}\n\n"
                
                async for chunk in service.llm_client.stream(messages):
                    if isinstance(chunk, str):
                        full_content += chunk
                        yield f"data: {json.dumps({'type': 'content', 'content': chunk}, ensure_ascii=False)}\n\n"
            else:
                yield f"data: {json.dumps({'type': 'error', 'message': 'LLM client not configured'}, ensure_ascii=False)}\n\n"
                return
            
            yield f"data: {json.dumps({'type': 'content_end'}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'type': 'status', 'status': 'parsing', 'message': '正在解析策略信息...'}, ensure_ascii=False)}\n\n"
            
            code = extract_code_from_response(full_content)
            strategy_info = extract_strategy_info(full_content)
            
            if not strategy_info["name"]:
                strategy_info["name"] = request.name or "自定义策略"
            if not strategy_info["description"]:
                strategy_info["description"] = request.description
            
            strategy_id = generate_strategy_id(strategy_info["name"])
            validation_result = validate_strategy_code(code)
            
            explanation = f"""该策略"{strategy_info['name']}"已根据您的描述生成：

**策略类型**: {strategy_info['strategy_type']}
**使用因子**: {', '.join(strategy_info['factors']) if strategy_info['factors'] else '根据描述推断'}

**策略逻辑**:
{strategy_info['description']}

**验证结果**: {'通过' if validation_result['is_valid'] else '存在问题'}
"""
            
            result = {
                "success": validation_result.get("is_valid", False),
                "strategy_id": strategy_id,
                "name": strategy_info["name"],
                "code": code,
                "description": strategy_info["description"],
                "strategy_type": strategy_info["strategy_type"],
                "factors": request.factors or strategy_info["factors"],
                "factor_weights": request.factor_weights,
                "validation": validation_result,
                "explanation": explanation,
                "created_at": datetime.now().isoformat(),
            }
            
            yield f"data: {json.dumps({'type': 'result', 'data': result}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'type': 'status', 'status': 'complete', 'message': '策略生成完成'}, ensure_ascii=False)}\n\n"
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
        logger.exception(f"Error generating strategy stream: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/save")
async def save_strategy(request: StrategySaveRequest):
    """
    Save a generated strategy to the registry and file system.
    """
    try:
        from openfinance.quant.strategy.registry import get_strategy_registry
        from pathlib import Path
        import re
        
        registry = get_strategy_registry()
        
        custom_dir = Path(__file__).parent.parent / "strategy" / "custom"
        custom_dir.mkdir(parents=True, exist_ok=True)
        
        safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', request.strategy_id.replace("strategy_", ""))
        safe_name = re.sub(r'_+', '_', safe_name).strip('_')
        
        if not safe_name:
            import hashlib
            safe_name = hashlib.md5(request.strategy_id.encode()).hexdigest()[:12]
        
        strategy_file = custom_dir / f"{safe_name}.py"
        
        class_name = ''.join(word.capitalize() for word in safe_name.split('_'))
        
        strategy_type_name = "MULTI_FACTOR"
        if request.strategy_type == "single_factor":
            strategy_type_name = "SINGLE_FACTOR"
        elif request.strategy_type == "rule_based":
            strategy_type_name = "RULE_BASED"
        elif request.strategy_type == "ml_based":
            strategy_type_name = "ML_BASED"
        
        factor_weights_py = repr(request.factor_weights) if request.factor_weights else "{}"
        factors_py = repr(request.factors) if request.factors else "[]"
        tags_py = repr(request.tags) if request.tags else "[]"
        
        strategy_code = f'''"""
{request.name} - Custom Strategy

{request.description}

Generated by AI Strategy Creator
"""

from typing import Optional
import pandas as pd
from openfinance.quant.strategy.base import (
    BaseStrategy,
    StrategyMetadata,
    StrategyType,
    WeightMethod,
    RebalanceFrequency,
)
from openfinance.quant.strategy.registry import register_strategy


@register_strategy
class {class_name}Strategy(BaseStrategy):
    """
    {request.name}
    
    {request.description}
    """
    
    def _default_metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            strategy_id="{request.strategy_id}",
            name="{request.name}",
            description="""{request.description}""",
            strategy_type=StrategyType.{strategy_type_name},
            factor_ids={factors_py},
            tags={tags_py},
        )
    
    def generate_signals(self, data: dict[str, pd.DataFrame], factor_values: Optional[dict] = None, date=None) -> dict[str, float]:
        \'\'\'Generate trading signals.\'\'\'
        signals = {{}}
        
        if not factor_values:
            return signals
        
        # Combine factor signals with weights
        factor_weights = {factor_weights_py}
        
        for factor_id, scores in factor_values.items():
            weight = factor_weights.get(factor_id, 1.0 / len(factor_values))
            for code, score in scores.items():
                signals[code] = signals.get(code, 0) + weight * score
        
        return signals
    
    def calculate_portfolio_weights(self, signals: dict[str, float], prices: pd.DataFrame, covariance_matrix=None) -> dict[str, float]:
        \'\'\'Calculate portfolio weights.\'\'\'
        sorted_signals = sorted(signals.items(), key=lambda x: x[1], reverse=True)
        top_n = min({request.max_positions}, len(sorted_signals))
        
        weights = {{}}
        for code, _ in sorted_signals[:top_n]:
            weights[code] = 1.0 / top_n
        
        return weights
'''

        with open(strategy_file, "w", encoding="utf-8") as f:
            f.write(strategy_code)
        
        logger.info(f"Saved strategy file: {strategy_file}")
        
        try:
            import importlib
            import sys
            
            module_name = f"openfinance.quant.strategy.custom.{safe_name}"
            if module_name in sys.modules:
                importlib.reload(sys.modules[module_name])
            else:
                importlib.import_module(module_name)
            
            logger.info(f"Loaded strategy module: {module_name}")
        except Exception as e:
            logger.warning(f"Failed to load strategy module: {e}")
        
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
                INSERT INTO openfinance.strategies 
                (strategy_id, name, code, description, strategy_type, factors, factor_weights, tags, status, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 'active', NOW(), NOW())
                ON CONFLICT (strategy_id) DO UPDATE SET
                    name = EXCLUDED.name,
                    code = EXCLUDED.code,
                    description = EXCLUDED.description,
                    updated_at = NOW()
            """,
                request.strategy_id,
                request.name,
                request.code,
                request.description,
                request.strategy_type,
                request.factors,
                request.factor_weights,
                request.tags,
            )
            
            await conn.close()
            
        except Exception as db_error:
            logger.warning(f"Database save failed: {db_error}")
        
        return {
            "success": True,
            "strategy_id": request.strategy_id,
            "message": f"策略 '{request.name}' 保存成功",
            "file_path": str(strategy_file),
            "registered": True,
        }
    
    except Exception as e:
        logger.exception(f"Error saving strategy: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/templates", response_model=TemplateListResponse)
async def get_strategy_templates():
    """Get available strategy templates."""
    templates = {
        "single_factor": "单因子策略 - 使用单个因子生成信号",
        "multi_factor": "多因子策略 - 组合多个因子信号",
        "momentum_value": "动量价值策略 - 动量+价值因子组合",
        "trend_following": "趋势跟踪策略 - 基于趋势信号",
        "mean_reversion": "均值回归策略 - 价格回归均值",
    }
    
    return TemplateListResponse(templates=templates, total=len(templates))


@router.get("/suggestions")
async def get_strategy_suggestions(
    strategy_type: Optional[str] = None,
    factors: Optional[str] = None,
):
    """Get strategy suggestions based on parameters."""
    suggestions = {
        "recommended_factors": {
            "momentum": ["factor_momentum", "factor_rsi", "factor_macd"],
            "value": ["factor_value_pe", "factor_dividend_yield"],
            "quality": ["factor_quality_roe"],
            "volatility": ["factor_volatility", "factor_atr"],
        },
        "weight_methods": {
            "equal_weight": "等权重 - 简单平均分配",
            "risk_parity": "风险平价 - 按风险贡献分配",
            "mean_variance": "均值方差 - 优化组合",
        },
        "rebalance_freqs": {
            "daily": "每日再平衡",
            "weekly": "每周再平衡",
            "monthly": "每月再平衡",
            "quarterly": "每季度再平衡",
        },
    }
    
    return {
        "success": True,
        "suggestions": suggestions,
    }
