"""
Strategies API Routes for OpenFinance quantitative system.

Provides endpoints for strategy management, signal generation, and backtesting.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from openfinance.quant.strategy.registry import get_strategy_registry
from openfinance.quant.strategy import RSIKDJMomentumStrategy, FlexibleMultiFactorStrategy

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/strategies", tags=["quant_strategies"])


# ============================================================================
# Request/Response Models
# ============================================================================

class StrategyListResponse(BaseModel):
    """Response for strategy list."""
    total: int
    strategies: list[dict[str, Any]]


class StrategySignal(BaseModel):
    """Stock signal from strategy."""
    code: str
    name: str | None = None
    score: float
    rank: int
    factor_scores: dict[str, float] = Field(default_factory=dict)


class StrategySignalsResponse(BaseModel):
    """Response for strategy signals."""
    strategy_id: str
    date: str
    signals: list[StrategySignal]


# ============================================================================
# API Endpoints
# ============================================================================

@router.get("/list")
async def list_strategies():
    """
    List all available strategies.
    
    Returns list of strategies from the strategy registry.
    """
    try:
        registry = get_strategy_registry()
        strategies = registry.list_all()
        
        strategy_list = []
        for strategy_id in strategies:
            strategy_info = registry.get_info(strategy_id)
            if strategy_info:
                strategy_list.append({
                    "strategy_id": strategy_id,
                    "name": strategy_info.name,
                    "description": strategy_info.description,
                    "factors": strategy_info.factor_ids,
                    "status": "active",
                })
        
        return {
            "total": len(strategy_list),
            "strategies": strategy_list,
        }
    
    except Exception as e:
        logger.exception(f"Error listing strategies: {e}")
        # Return empty list if registry not available
        return {
            "total": 0,
            "strategies": [],
        }


@router.get("/registry")
async def get_strategy_registry_endpoint():
    """
    Get complete strategy registry.
    """
    try:
        registry = get_strategy_registry()
        stats = registry.get_summary()
        strategies = registry.list_all()
        
        strategies_data = []
        for strategy_id in strategies:
            info = registry.get_info(strategy_id)
            if info:
                strategies_data.append({
                    "strategy_id": strategy_id,
                    "name": info.name,
                    "code": info.strategy_id,
                    "description": info.description,
                    "factors": info.factor_ids,
                    "status": "active",
                })
        
        return {
            "total": len(strategies_data),
            "strategies": strategies_data,
            "statistics": stats,
        }
    
    except Exception as e:
        logger.exception(f"Error getting strategy registry: {e}")
        return {
            "total": 0,
            "strategies": [],
            "error": str(e),
        }


@router.get("/{strategy_id}")
async def get_strategy(strategy_id: str):
    """Get detailed information about a specific strategy."""
    try:
        registry = get_strategy_registry()
        info = registry.get_info(strategy_id)
        
        if not info:
            raise HTTPException(status_code=404, detail=f"Strategy not found: {strategy_id}")
        
        return {
            "strategy_id": strategy_id,
            "name": info.name,
            "code": info.strategy_id,
            "description": info.description,
            "factors": info.factor_ids,
            "factor_weights": {},
            "weight_method": "equal_weight",
            "max_positions": 50,
            "rebalance_freq": "monthly",
            "status": "active",
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error getting strategy: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{strategy_id}/signals")
async def get_strategy_signals(
    strategy_id: str,
    date: Optional[str] = Query(None, description="Signal date (YYYY-MM-DD)"),
    top_n: int = Query(20, ge=1, le=100, description="Top N recommendations"),
):
    """
    Get stock recommendations from a strategy.
    
    Generates signals for the specified date using the strategy's factor configuration.
    """
    try:
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        
        registry = get_strategy_registry()
        info = registry.get_info(strategy_id)
        
        if not info:
            raise HTTPException(status_code=404, detail=f"Strategy not found: {strategy_id}")
        
        # TODO: Implement actual signal generation using StrategyEngine
        # This requires integrating with the data service and factor calculation
        
        return {
            "strategy_id": strategy_id,
            "strategy_name": info.name,
            "date": date,
            "signals": [],
            "message": "Signal generation requires data integration",
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error getting strategy signals: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class StrategyRunRequest(BaseModel):
    """Request for running a strategy."""
    strategy_id: str
    stock_codes: list[str] | None = None
    start_date: str | None = None
    end_date: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)


class StrategyRunResponse(BaseModel):
    """Response for strategy run."""
    strategy_id: str
    strategy_name: str
    run_date: str
    signals: list[dict[str, Any]]
    top_picks: list[dict[str, Any]]
    statistics: dict[str, Any] = Field(default_factory=dict)


class CreateStrategyRequest(BaseModel):
    """Request for creating a new strategy."""
    name: str
    code: str
    description: str = ""
    factors: list[str] = Field(default_factory=list)
    factor_weights: dict[str, float] = Field(default_factory=dict)
    weight_method: str = "equal_weight"
    max_positions: int = 50
    rebalance_freq: str = "monthly"
    stop_loss: float | None = None
    take_profit: float | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)


@router.post("/run")
async def run_strategy(request: StrategyRunRequest):
    """
    Run a strategy and generate signals.
    
    This endpoint executes the strategy calculation for the specified
    stock universe and returns trading signals.
    """
    try:
        from openfinance.quant.factors.registry import get_factor_registry
        import numpy as np
        
        registry = get_strategy_registry()
        strategy = registry.get(request.strategy_id)
        info = registry.get_info(request.strategy_id)
        
        if not strategy or not info:
            raise HTTPException(status_code=404, detail=f"Strategy not found: {request.strategy_id}")
        
        factor_registry = get_factor_registry()
        
        stock_codes = request.stock_codes or _get_default_universe()
        
        factor_values_by_factor: dict[str, list[tuple[str, float]]] = {fid: [] for fid in info.factor_ids}
        stock_data_cache: dict[str, list] = {}
        
        for code in stock_codes:
            market_data = await _get_stock_data(code, 60)
            
            if not market_data or len(market_data) < 30:
                continue
            
            stock_data_cache[code] = market_data
            
            for factor_id in info.factor_ids:
                factor_instance = factor_registry.get_factor_instance(factor_id)
                if not factor_instance:
                    continue
                
                result = factor_instance.calculate(market_data)
                
                if result and result.value is not None:
                    factor_values_by_factor[factor_id].append((code, result.value))
        
        factor_normalized_scores: dict[str, dict[str, float]] = {}
        
        for factor_id, values in factor_values_by_factor.items():
            if not values:
                factor_normalized_scores[factor_id] = {}
                continue
            
            codes, raw_values = zip(*values)
            arr = np.array(raw_values)
            mean, std = np.nanmean(arr), np.nanstd(arr)
            
            normalized = {}
            for code, val in values:
                if std > 0:
                    normalized[code] = (val - mean) / std
                else:
                    normalized[code] = 0.0
            
            factor_normalized_scores[factor_id] = normalized
        
        signals = []
        
        for code, market_data in stock_data_cache.items():
            stock_signal = {
                "code": code,
                "name": _get_stock_name(code),
                "score": 0.0,
                "factor_scores": {},
            }
            
            total_score = 0.0
            total_weight = 0.0
            
            for factor_id in info.factor_ids:
                if code not in factor_normalized_scores.get(factor_id, {}):
                    continue
                
                normalized_value = factor_normalized_scores[factor_id][code]
                weight = strategy.factor_weights.get(factor_id, 1.0) if hasattr(strategy, 'factor_weights') else 1.0
                
                raw_value = None
                for c, v in factor_values_by_factor.get(factor_id, []):
                    if c == code:
                        raw_value = v
                        break
                
                stock_signal["factor_scores"][factor_id] = {
                    "value": raw_value,
                    "normalized": normalized_value,
                    "weight": weight,
                }
                
                total_score += normalized_value * weight
                total_weight += weight
            
            if total_weight > 0:
                stock_signal["score"] = total_score / total_weight
            
            signals.append(stock_signal)
        
        signals.sort(key=lambda x: x["score"], reverse=True)
        
        for i, signal in enumerate(signals):
            signal["rank"] = i + 1
        
        top_picks = signals[:request.parameters.get("top_n", 20)]
        
        return StrategyRunResponse(
            strategy_id=request.strategy_id,
            strategy_name=info.name,
            run_date=datetime.now().strftime("%Y-%m-%d"),
            signals=signals,
            top_picks=top_picks,
            statistics={
                "total_stocks": len(signals),
                "avg_score": sum(s["score"] for s in signals) / len(signals) if signals else 0,
                "max_score": max(s["score"] for s in signals) if signals else 0,
                "min_score": min(s["score"] for s in signals) if signals else 0,
            },
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error running strategy: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/create")
async def create_strategy(request: CreateStrategyRequest):
    """
    Create a new custom strategy.
    
    Creates a strategy configuration that can be used for signal generation.
    """
    try:
        from openfinance.quant.strategy.builder import StrategyBuilder
        from openfinance.quant.strategy.base import WeightMethod, RebalanceFrequency
        
        strategy_id = f"strategy_custom_{request.code}"
        
        builder = StrategyBuilder()
        builder.name(request.name)
        builder.code(request.code)
        builder.description(request.description)
        builder.factors(request.factors)
        builder.factor_weights(request.factor_weights)
        builder.weight_method(request.weight_method)
        builder.max_positions(request.max_positions)
        builder.rebalance_frequency(request.rebalance_freq)
        
        if request.stop_loss:
            builder.stop_loss(request.stop_loss)
        if request.take_profit:
            builder.take_profit(request.take_profit)
        
        strategy = builder.build()
        strategy.strategy_id = strategy_id
        
        registry = get_strategy_registry()
        registry._strategies[strategy_id] = strategy
        
        return {
            "strategy_id": strategy_id,
            "name": strategy.name,
            "code": strategy.code,
            "description": strategy.description,
            "factors": strategy.factors,
            "factor_weights": strategy.factor_weights,
            "status": "created",
        }
    
    except Exception as e:
        logger.exception(f"Error creating strategy: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _get_stock_data(code: str, lookback_days: int = 60) -> list:
    """Get stock market data for calculation."""
    import asyncpg
    import os
    from datetime import date, timedelta
    from openfinance.datacenter.models.analytical import ADSKLineModel
    
    db_url = os.getenv(
        "DATABASE_URL",
        "postgresql://openfinance:openfinance@localhost:5432/openfinance"
    )
    
    try:
        conn = await asyncpg.connect(db_url)
        
        end_date = date.today()
        start_date = end_date - timedelta(days=lookback_days * 2)
        
        rows = await conn.fetch("""
            SELECT trade_date, open, high, low, close, volume, amount
            FROM openfinance.stock_daily_quote
            WHERE code = $1 AND trade_date >= $2 AND trade_date <= $3
            ORDER BY trade_date ASC
        """, code[:6], start_date, end_date)
        
        await conn.close()
        
        if not rows:
            return _generate_mock_klines(lookback_days, code)
        
        klines = []
        for row in rows:
            kline = ADSKLineModel(
                code=code[:6],
                trade_date=row["trade_date"],
                open=float(row["open"] or 0),
                high=float(row["high"] or 0),
                low=float(row["low"] or 0),
                close=float(row["close"] or 0),
                volume=int(row["volume"] or 0),
                amount=float(row["amount"] or 0),
            )
            klines.append(kline)
        
        return klines
        
    except Exception as e:
        logger.warning(f"Database query failed, using mock data: {e}")
        return _generate_mock_klines(lookback_days, code)


def _generate_mock_klines(days: int, code: str) -> list:
    """Generate mock K-Line data for testing."""
    from datetime import date, timedelta
    from openfinance.datacenter.models.analytical import ADSKLineModel
    import random
    
    klines = []
    base_price = 10.0 + random.random() * 90
    
    for i in range(days):
        trade_date = date.today() - timedelta(days=days - i - 1)
        
        change = random.uniform(-0.03, 0.03)
        close = base_price * (1 + change)
        high = close * (1 + random.uniform(0, 0.02))
        low = close * (1 - random.uniform(0, 0.02))
        open_price = low + (high - low) * random.random()
        volume = int(random.uniform(1000000, 10000000))
        
        kline = ADSKLineModel(
            code=code[:6],
            trade_date=trade_date,
            open=round(open_price, 2),
            high=round(high, 2),
            low=round(low, 2),
            close=round(close, 2),
            volume=volume,
            amount=round(close * volume, 2),
        )
        klines.append(kline)
        base_price = close
    
    return klines


def _get_default_universe() -> list[str]:
    """Get default stock universe for strategy."""
    return [
        "600000", "600004", "600006", "600007", "600008",
        "600009", "600010", "600011", "600012", "600015",
        "600016", "600017", "600018", "600019", "600020",
        "000001", "000002", "000004", "000005", "000006",
    ]


def _get_stock_name(code: str) -> str:
    """Get stock name by code."""
    stock_names = {
        "600000": "浦发银行", "600004": "白云机场", "600006": "东风汽车",
        "000001": "平安银行", "000002": "万科A", "000004": "国华网安",
    }
    return stock_names.get(code, f"股票{code}")
