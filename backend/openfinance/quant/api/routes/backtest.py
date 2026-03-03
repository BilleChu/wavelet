"""
Backtest API Routes for OpenFinance quantitative system.

Provides endpoints for running backtests and retrieving results.
"""

import logging
import os
import uuid
from datetime import date, datetime, timedelta
from typing import Any, Optional

import pandas as pd
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field

from openfinance.quant.strategy.config_loader import StrategyConfigLoader
from openfinance.quant.backtest.engine import BacktestEngine, BacktestConfig
from openfinance.quant.backtest.report_generator import BacktestReportGenerator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/backtest", tags=["quant_backtest"])


class BacktestRunRequest(BaseModel):
    """Request for running a backtest."""
    
    strategy_id: str = Field(..., description="Strategy ID to backtest")
    start_date: str = Field(..., description="Start date (YYYY-MM-DD)")
    end_date: str = Field(..., description="End date (YYYY-MM-DD)")
    initial_capital: float = Field(default=1000000.0, description="Initial capital")
    benchmark: str = Field(default="000300", description="Benchmark index code")
    commission_rate: float = Field(default=0.0003, description="Commission rate")
    slippage: float = Field(default=0.001, description="Slippage rate")
    stock_codes: Optional[list[str]] = Field(default=None, description="Stock universe (optional)")


class BacktestStatusResponse(BaseModel):
    """Response for backtest status."""
    
    backtest_id: str
    status: str
    progress: float
    message: str
    created_at: str
    completed_at: Optional[str] = None


_backtest_results: dict[str, dict[str, Any]] = {}
_backtest_status: dict[str, BacktestStatusResponse] = {}


@router.get("/configs")
async def get_backtest_configs():
    """
    Get available backtest configurations.
    
    Returns default configuration options for backtests.
    """
    return {
        "benchmarks": [
            {"code": "000300", "name": "沪深300"},
            {"code": "000016", "name": "上证50"},
            {"code": "000905", "name": "中证500"},
            {"code": "000852", "name": "中证1000"},
            {"code": "399006", "name": "创业板指"},
        ],
        "default_params": {
            "initial_capital": 1000000.0,
            "commission_rate": 0.0003,
            "slippage": 0.001,
            "start_date": (date.today() - timedelta(days=365)).strftime("%Y-%m-%d"),
            "end_date": date.today().strftime("%Y-%m-%d"),
        },
        "date_presets": [
            {"label": "近1个月", "days": 30},
            {"label": "近3个月", "days": 90},
            {"label": "近6个月", "days": 180},
            {"label": "近1年", "days": 365},
            {"label": "近3年", "days": 1095},
            {"label": "近5年", "days": 1825},
        ],
    }


@router.post("/run")
async def run_backtest(request: BacktestRunRequest, background_tasks: BackgroundTasks):
    """
    Run a backtest for a strategy.
    
    This endpoint initiates a backtest and returns a backtest ID.
    The backtest runs asynchronously and results can be retrieved later.
    """
    try:
        backtest_id = f"bt_{uuid.uuid4().hex[:12]}"
        
        _backtest_status[backtest_id] = BacktestStatusResponse(
            backtest_id=backtest_id,
            status="pending",
            progress=0.0,
            message="Backtest initialized",
            created_at=datetime.now().isoformat(),
        )
        
        background_tasks.add_task(
            _run_backtest_task,
            backtest_id,
            request,
        )
        
        return {
            "backtest_id": backtest_id,
            "status": "pending",
            "message": "Backtest started. Use /backtest/{backtest_id}/status to check progress.",
        }
    
    except Exception as e:
        logger.exception(f"Error starting backtest: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{backtest_id}/status")
async def get_backtest_status(backtest_id: str):
    """
    Get the status of a running backtest.
    """
    if backtest_id not in _backtest_status:
        raise HTTPException(status_code=404, detail=f"Backtest not found: {backtest_id}")
    
    return _backtest_status[backtest_id]


@router.get("/{backtest_id}/results")
async def get_backtest_results(backtest_id: str):
    """
    Get the results of a completed backtest.
    
    Returns comprehensive backtest report including:
    - Executive summary
    - Performance metrics (60+ indicators)
    - Risk analysis
    - Drawdown analysis
    - Trade analysis
    - Benchmark comparison
    """
    if backtest_id not in _backtest_results:
        raise HTTPException(status_code=404, detail=f"Backtest results not found: {backtest_id}")
    
    return _backtest_results[backtest_id]


@router.get("/{backtest_id}/report")
async def get_backtest_report(backtest_id: str):
    """
    Get the detailed report of a completed backtest.
    
    Returns the full report with all metrics and analysis.
    """
    if backtest_id not in _backtest_results:
        raise HTTPException(status_code=404, detail=f"Backtest not found: {backtest_id}")
    
    result = _backtest_results[backtest_id]
    
    if result.get("status") != "completed":
        return {
            "backtest_id": backtest_id,
            "status": result.get("status", "unknown"),
            "message": "Backtest not yet completed",
        }
    
    return result.get("report", {})


@router.get("/history")
async def get_backtest_history(
    limit: int = Query(10, ge=1, le=100, description="Number of results to return"),
):
    """
    Get history of recent backtests.
    """
    results = []
    
    for bt_id, status in sorted(
        _backtest_status.items(),
        key=lambda x: x[1].created_at,
        reverse=True,
    )[:limit]:
        result = {
            "backtest_id": bt_id,
            "status": status.status,
            "created_at": status.created_at,
            "completed_at": status.completed_at,
        }
        
        if bt_id in _backtest_results and _backtest_results[bt_id].get("status") == "completed":
            report = _backtest_results[bt_id].get("report", {})
            summary = report.get("executive_summary", {})
            result["summary"] = {
                "total_return": summary.get("total_return"),
                "annual_return": summary.get("annual_return"),
                "sharpe_ratio": summary.get("sharpe_ratio"),
                "max_drawdown": summary.get("max_drawdown"),
                "grade": summary.get("grade"),
            }
        
        results.append(result)
    
    return {
        "total": len(results),
        "backtests": results,
    }


async def _run_backtest_task(backtest_id: str, request: BacktestRunRequest):
    """Background task to run backtest."""
    try:
        _backtest_status[backtest_id].status = "running"
        _backtest_status[backtest_id].message = "Loading strategy configuration..."
        _backtest_status[backtest_id].progress = 0.1
        
        from openfinance.quant.strategy.registry import get_strategy_registry
        from openfinance.quant.factors.registry import get_factor_registry
        
        strategy_registry = get_strategy_registry()
        factor_registry = get_factor_registry()
        
        strategy = strategy_registry.get(request.strategy_id)
        strategy_info = strategy_registry.get_info(request.strategy_id)
        
        if not strategy:
            config_loader = StrategyConfigLoader()
            strategy_config = config_loader.get_config(request.strategy_id)
            
            if not strategy_config:
                raise ValueError(f"Strategy not found: {request.strategy_id}")
            
            strategy = config_loader.to_domain_strategy(strategy_config)
            factor_ids = [f.factor_id for f in strategy_config.factors if f.enabled]
            strategy_name = strategy_config.name
        else:
            factor_ids = strategy_info.factor_ids if strategy_info else []
            strategy_name = strategy_info.name if strategy_info else request.strategy_id
        
        _backtest_status[backtest_id].message = "Preparing market data..."
        _backtest_status[backtest_id].progress = 0.2
        
        stock_codes = request.stock_codes or _get_default_stock_universe()
        market_data = await _fetch_market_data(
            stock_codes,
            request.start_date,
            request.end_date,
        )
        
        price_df = _convert_to_dataframe(market_data)
        
        _backtest_status[backtest_id].message = "Calculating factors..."
        _backtest_status[backtest_id].progress = 0.3
        
        factor_values = await _calculate_factors_from_ids(
            factor_ids,
            market_data,
            factor_registry,
        )
        
        _backtest_status[backtest_id].message = "Running backtest engine..."
        _backtest_status[backtest_id].progress = 0.5
        
        from openfinance.domain.models.quant import BacktestConfig as DomainBacktestConfig
        
        config = DomainBacktestConfig(
            backtest_id=backtest_id,
            strategy_id=request.strategy_id,
            start_date=datetime.strptime(request.start_date, "%Y-%m-%d"),
            end_date=datetime.strptime(request.end_date, "%Y-%m-%d"),
            initial_capital=request.initial_capital,
            commission=request.commission_rate,
            slippage=request.slippage,
            benchmark=request.benchmark,
        )
        
        engine = BacktestEngine()
        
        backtest_result = await engine.run(
            strategy=strategy,
            config=config,
            price_data=price_df,
            factor_values=factor_values,
        )
        
        _backtest_status[backtest_id].message = "Generating report..."
        _backtest_status[backtest_id].progress = 0.8
        
        report_generator = BacktestReportGenerator()
        report = report_generator.generate_report(
            result=backtest_result,
        )
        
        _backtest_status[backtest_id].status = "completed"
        _backtest_status[backtest_id].progress = 1.0
        _backtest_status[backtest_id].message = "Backtest completed successfully"
        _backtest_status[backtest_id].completed_at = datetime.now().isoformat()
        
        _backtest_results[backtest_id] = {
            "backtest_id": backtest_id,
            "status": "completed",
            "strategy_id": request.strategy_id,
            "strategy_name": strategy_name,
            "config": {
                "start_date": request.start_date,
                "end_date": request.end_date,
                "initial_capital": request.initial_capital,
                "benchmark": request.benchmark,
                "commission_rate": request.commission_rate,
                "slippage": request.slippage,
            },
            "report": report,
            "created_at": _backtest_status[backtest_id].created_at,
            "completed_at": _backtest_status[backtest_id].completed_at,
        }
        
    except Exception as e:
        logger.exception(f"Backtest {backtest_id} failed: {e}")
        _backtest_status[backtest_id].status = "failed"
        _backtest_status[backtest_id].message = f"Backtest failed: {str(e)}"
        _backtest_results[backtest_id] = {
            "backtest_id": backtest_id,
            "status": "failed",
            "error": str(e),
        }


def _get_default_stock_universe() -> list[str]:
    """Get default stock universe for backtesting."""
    return [
        "600000", "600004", "600006", "600007", "600008",
        "600009", "600010", "600011", "600012", "600015",
        "600016", "600017", "600018", "600019", "600020",
        "600028", "600029", "600030", "600031", "600033",
        "600035", "600036", "600037", "600038", "600039",
        "600048", "600050", "600056", "600058", "600059",
        "600060", "600061", "600062", "600063", "600064",
        "600066", "600067", "600068", "600069", "600070",
        "000001", "000002", "000004", "000005", "000006",
        "000007", "000008", "000009", "000010", "000011",
        "000012", "000014", "000016", "000017", "000019",
        "000020", "000021", "000022", "000023", "000025",
        "000026", "000027", "000028", "000029", "000030",
        "000031", "000032", "000033", "000034", "000035",
        "000036", "000037", "000038", "000039", "000040",
        "000042", "000043", "000045", "000046", "000048",
        "000049", "000050", "000551", "000552", "000553",
        "000554", "000555", "000557", "000558", "000559",
        "000560", "000561", "000562", "000563", "000564",
        "000565", "000566", "000567", "000568", "000569",
    ]


async def _fetch_market_data(
    stock_codes: list[str],
    start_date: str,
    end_date: str,
) -> dict[str, list]:
    """Fetch market data for backtesting."""
    import asyncpg
    from openfinance.datacenter.models.analytical import ADSKLineModel
    
    db_url = os.getenv(
        "DATABASE_URL",
        "postgresql://openfinance:openfinance@localhost:5432/openfinance"
    )
    if "+asyncpg" in db_url:
        db_url = db_url.replace("+asyncpg", "")
    
    market_data: dict[str, list] = {}
    
    try:
        conn = await asyncpg.connect(db_url)
        
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
        
        for code in stock_codes:
            rows = await conn.fetch("""
                SELECT trade_date, open, high, low, close, volume, amount
                FROM openfinance.stock_daily_quote
                WHERE code = $1 AND trade_date >= $2 AND trade_date <= $3
                ORDER BY trade_date ASC
            """, code[:6], start, end)
            
            if rows:
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
                market_data[code] = klines
        
        await conn.close()
        
    except Exception as e:
        logger.warning(f"Database query failed, using mock data: {e}")
        for code in stock_codes[:20]:
            market_data[code] = _generate_mock_klines(
                (datetime.strptime(end_date, "%Y-%m-%d").date() - 
                 datetime.strptime(start_date, "%Y-%m-%d").date()).days + 1,
                code,
            )
    
    return market_data


def _generate_mock_klines(days: int, code: str) -> list:
    """Generate mock K-Line data for testing."""
    from openfinance.datacenter.models.analytical import ADSKLineModel
    import random
    
    klines = []
    base_price = 10.0 + random.random() * 90
    random.seed(hash(code) % 2**32)
    
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


async def _calculate_factors_from_ids(
    factor_ids: list[str],
    market_data: dict[str, list],
    factor_registry: Any,
) -> dict[str, list]:
    """Calculate factor values for all stocks from factor IDs."""
    from openfinance.domain.models.quant import FactorValue
    import numpy as np
    
    factor_values: dict[str, list] = {}
    
    for factor_id in factor_ids:
        factor_instance = factor_registry.get_factor_instance(factor_id)
        
        if not factor_instance:
            logger.warning(f"Factor not found: {factor_id}")
            continue
        
        values_list: list[FactorValue] = []
        all_values = []
        
        for code, klines in market_data.items():
            if len(klines) < 30:
                continue
            
            result = factor_instance.calculate(klines)
            
            if result and result.value is not None:
                all_values.append((code, klines[-1].trade_date, result.value, result.value_normalized))
        
        if all_values:
            raw_values = np.array([v[2] for v in all_values])
            mean_val = np.nanmean(raw_values)
            std_val = np.nanstd(raw_values)
            
            for code, trade_date, value, value_normalized in all_values:
                zscore = (value - mean_val) / std_val if std_val > 0 else 0.0
                
                values_list.append(FactorValue(
                    factor_id=factor_id,
                    stock_code=code,
                    trade_date=trade_date,
                    value=value,
                    value_normalized=value_normalized,
                    zscore=zscore,
                ))
        
        factor_values[factor_id] = values_list
        logger.info(f"Calculated {len(values_list)} values for factor {factor_id}")
    
    return factor_values


async def _calculate_factors(
    strategy_config: Any,
    market_data: dict[str, list],
) -> dict[str, list]:
    """Calculate factor values for all stocks."""
    from openfinance.quant.factors.registry import get_factor_registry
    from openfinance.domain.models.quant import FactorValue
    
    factor_registry = get_factor_registry()
    factor_values: dict[str, list] = {}
    
    for factor_config in strategy_config.factors:
        factor_id = factor_config.factor_id
        factor_instance = factor_registry.get_factor_instance(factor_id)
        
        if not factor_instance:
            logger.warning(f"Factor not found: {factor_id}")
            continue
        
        values_list: list[FactorValue] = []
        
        for code, klines in market_data.items():
            if len(klines) < 30:
                continue
            
            result = factor_instance.calculate(klines)
            
            if result and result.value is not None:
                values_list.append(FactorValue(
                    factor_id=factor_id,
                    stock_code=code,
                    trade_date=klines[-1].trade_date,
                    value=result.value,
                    value_normalized=result.value_normalized,
                ))
        
        factor_values[factor_id] = values_list
    
    return factor_values


def _convert_to_dataframe(market_data: dict[str, list]) -> pd.DataFrame:
    """Convert market data dict to DataFrame for backtest engine."""
    import pandas as pd
    
    rows = []
    for code, klines in market_data.items():
        for kline in klines:
            rows.append({
                "stock_code": code,
                "trade_date": kline.trade_date,
                "open": kline.open,
                "high": kline.high,
                "low": kline.low,
                "close": kline.close,
                "volume": kline.volume,
                "amount": kline.amount,
            })
    
    if not rows:
        return pd.DataFrame(columns=["stock_code", "trade_date", "open", "high", "low", "close", "volume", "amount"])
    
    df = pd.DataFrame(rows)
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    return df
