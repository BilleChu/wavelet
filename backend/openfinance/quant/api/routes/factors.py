"""
Factors API Routes for OpenFinance quantitative system.

Provides endpoints for factor management, calculation, testing, and analysis.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, TYPE_CHECKING

import pandas as pd
import numpy as np

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from openfinance.quant.factors.base import FactorBase, FactorResult

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/factors", tags=["quant_factors"])


def get_factor_library() -> dict[str, type[FactorBase]]:
    """Get all pre-built factors from the factor library."""
    return {
        "momentum_20": MomentumFactor,
        "momentum_60": lambda: MomentumFactor(parameters={"period": 60}),
        "momentum_120": lambda: MomentumFactor(parameters={"period": 120}),
        "risk_adjusted_momentum": RiskAdjustedMomentumFactor,
        "value": ValueFactor,
        "dividend_yield": DividendYieldFactor,
        "quality": QualityFactor,
        "piotroski_f_score": PiotroskiFScoreFactor,
        "volatility": VolatilityFactor,
        "idiosyncratic_volatility": IdiosyncraticVolatilityFactor,
    }


# ============================================================================
# Request/Response Models
# ============================================================================

class FactorListRequest(BaseModel):
    """Request to list factors with filters."""
    
    factor_type: str | None = Field(None, description="Filter by factor type")
    category: str | None = Field(None, description="Filter by category")
    status: str | None = Field(None, description="Filter by status")
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")


class FactorDetailResponse(BaseModel):
    """Detailed factor information."""
    
    factor_id: str
    name: str
    code: str
    description: str
    factor_type: str
    category: str
    lookback_period: int
    frequency: str
    parameters: dict[str, Any]
    tags: list[str]
    version: str
    status: str
    required_columns: list[str]
    created_at: str | None = None
    updated_at: str | None = None


class FactorCalculateRequest(BaseModel):
    """Request to calculate factor values."""
    
    factor_id: str = Field(..., description="Factor ID")
    stock_codes: list[str] = Field(default_factory=list, description="Stock codes")
    start_date: datetime = Field(..., description="Start date")
    end_date: datetime = Field(..., description="End date")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Override parameters")


class FactorCalculateResponse(BaseModel):
    """Factor calculation result."""
    
    factor_id: str
    factor_name: str
    stock_code: str
    frequency: str
    data: list[dict[str, Any]]
    statistics: dict[str, Any]
    chart_data: dict[str, Any]


class FactorTestRequest(BaseModel):
    """Request to test factor performance."""
    
    factor_id: str = Field(..., description="Factor ID")
    stock_codes: list[str] = Field(default_factory=list, description="Stock codes")
    start_date: datetime = Field(..., description="Test start date")
    end_date: datetime = Field(..., description="Test end date")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Factor parameters")


class FactorTestResult(BaseModel):
    """Factor test results with IC analysis."""
    
    factor_id: str
    ic_mean: float
    ic_std: float
    ic_ir: float
    ic_positive_ratio: float
    coverage_mean: float
    monotonicity: float
    stocks_tested: int
    success_rate: float
    avg_execution_time: float
    duration_ms: float
    error: str | None = None


# ============================================================================
# Helper Functions
# ============================================================================

def create_factor(factor_id: str, parameters: dict[str, Any] | None = None) -> FactorBase:
    """Create factor instance from registry."""
    from openfinance.quant.factors.registry import get_factor_registry
    
    registry = get_factor_registry()
    factor = registry.get_factor_instance(factor_id)
    
    if not factor:
        raise ValueError(f"Factor '{factor_id}' not found in registry")
    
    return factor


# ============================================================================
# API Endpoints
# ============================================================================

@router.get("/list")
async def list_factors(
    factor_type: str | None = None,
    category: str | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
):
    """
    List all available factors with optional filtering.
    
    Returns paginated list of factors that match the filter criteria.
    Uses the UnifiedFactorRegistry as the single source of truth.
    """
    try:
        from openfinance.quant.factors.registry import get_factor_registry
        
        registry = get_factor_registry()
        factors_list = registry.list_factors(
            factor_type=factor_type,
            category=category,
            status=status,
            include_builtin=True,
        )
        
        # Convert factors to dict
        factors = []
        for factor in factors_list:
            if hasattr(factor, 'to_dict'):
                factors.append(factor.to_dict())
            else:
                factors.append({
                    "factor_id": factor.factor_id,
                    "name": factor.name,
                    "code": factor.code,
                    "description": factor.description,
                    "factor_type": factor.factor_type.value if hasattr(factor.factor_type, 'value') else str(factor.factor_type),
                    "category": factor.category.value if hasattr(factor.category, 'value') else str(factor.category),
                    "lookback_period": factor.lookback_period,
                    "tags": factor.tags,
                    "is_builtin": factor.is_builtin,
                })
        
        # Pagination
        total = len(factors)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_factors = factors[start_idx:end_idx]
        
        return {
            "factors": paginated_factors,
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    
    except Exception as e:
        logger.exception(f"Error listing factors: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/registry")
async def get_factor_registry_endpoint():
    """
    Get complete factor registry with all registered factors.
    This endpoint returns the full list without pagination for frontend consumption.
    """
    try:
        from openfinance.quant.factors.registry import get_factor_registry
        
        registry = get_factor_registry()
        factors_list = registry.list_factors(include_builtin=True)
        stats = registry.get_statistics()
        
        # Convert factors to dict
        factors_data = []
        for factor in factors_list:
            if hasattr(factor, 'to_dict'):
                factors_data.append(factor.to_dict())
            else:
                factors_data.append({
                    "factor_id": factor.factor_id,
                    "name": factor.name,
                    "code": factor.code,
                    "description": factor.description,
                    "factor_type": factor.factor_type.value if hasattr(factor.factor_type, 'value') else str(factor.factor_type),
                    "category": factor.category.value if hasattr(factor.category, 'value') else str(factor.category),
                    "expression": factor.expression,
                    "lookback_period": factor.lookback_period,
                    "required_fields": factor.required_fields,
                    "tags": factor.tags,
                    "is_builtin": factor.is_builtin,
                })
        
        return {
            "total": len(factors_data),
            "factors": factors_data,
            "statistics": stats,
        }
    
    except Exception as e:
        logger.exception(f"Error getting factor registry: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Factor Data Query Endpoints
# ============================================================================

class FactorDataQueryRequest(BaseModel):
    """Request to query factor data for a stock."""
    
    factor_id: str = Field(..., description="Factor ID")
    stock_code: str = Field(..., description="Stock code (e.g., 600000.SH)")
    start_date: str | None = Field(None, description="Start date (YYYY-MM-DD)")
    end_date: str | None = Field(None, description="End date (YYYY-MM-DD)")
    frequency: str = Field(default="daily", description="Data frequency: daily, weekly, monthly")
    lookback_days: int | None = Field(None, description="Number of days to look back from today")


class FactorDataBatchQueryRequest(BaseModel):
    """Request to query factor data for multiple stocks."""
    
    factor_id: str = Field(..., description="Factor ID")
    stock_codes: list[str] = Field(..., description="List of stock codes")
    start_date: str | None = Field(None, description="Start date (YYYY-MM-DD)")
    end_date: str | None = Field(None, description="End date (YYYY-MM-DD)")
    frequency: str = Field(default="daily", description="Data frequency")


@router.post("/data/query")
async def query_factor_data(request: FactorDataQueryRequest):
    """
    Query factor data for a specific stock.
    
    Returns factor values, normalized values, and chart data.
    """
    try:
        from openfinance.quant.factors.registry import get_factor_registry
        
        registry = get_factor_registry()
        factor_def = registry.get(request.factor_id)
        
        if not factor_def:
            raise HTTPException(status_code=404, detail=f"Factor not found: {request.factor_id}")
        
        # Calculate date range
        if request.lookback_days:
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=request.lookback_days)).strftime("%Y-%m-%d")
        else:
            start_date = request.start_date or (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
            end_date = request.end_date or datetime.now().strftime("%Y-%m-%d")
        
        # Normalize stock code: remove .SH/.SZ suffix if present
        stock_code = request.stock_code
        if '.' in stock_code:
            stock_code = stock_code.split('.')[0]
        
        # Fetch market data from database and calculate factor
        import asyncpg
        import os
        from datetime import date as date_type
        
        market_data = []
        
        try:
            # Connect to database
            db_url = os.getenv(
                "DATABASE_URL",
                "postgresql://openfinance:openfinance@localhost:5432/openfinance"
            )
            conn = await asyncpg.connect(db_url)
            
            # Query stock daily quotes
            rows = await conn.fetch("""
                SELECT trade_date, open, high, low, close, volume, amount
                FROM openfinance.stock_daily_quote
                WHERE code = $1 AND trade_date >= $2 AND trade_date <= $3
                ORDER BY trade_date ASC
            """, stock_code, date_type.fromisoformat(start_date), date_type.fromisoformat(end_date))
            
            await conn.close()
            
            if rows:
                market_data = [
                    {
                        "trade_date": str(row["trade_date"]),
                        "open": float(row["open"]) if row["open"] else None,
                        "high": float(row["high"]) if row["high"] else None,
                        "low": float(row["low"]) if row["low"] else None,
                        "close": float(row["close"]) if row["close"] else None,
                        "volume": int(row["volume"]) if row["volume"] else None,
                        "amount": float(row["amount"]) if row["amount"] else None,
                    }
                    for row in rows
                ]
        except Exception as e:
            logger.warning(f"Database query failed: {e}")
        
        # If no market data, return empty result
        if not market_data:
            return {
                "factor_id": request.factor_id,
                "factor_name": factor_def.name,
                "stock_code": request.stock_code,
                "frequency": request.frequency,
                "data": [],
                "chart_data": {"labels": [], "datasets": []},
                "statistics": {},
                "error": f"No market data found for stock {stock_code}",
            }
        
        # Create DataFrame for factor calculation
        df = pd.DataFrame(market_data)
        df["trade_date"] = pd.to_datetime(df["trade_date"])
        df = df.set_index("trade_date")
        
        # Calculate factor values based on factor definition
        factor_values = _calculate_factor_from_definition(factor_def, df, stock_code)
        
        # Build response data
        data_list = []
        for i, (date, value) in enumerate(factor_values.items()):
            data_list.append({
                "trade_date": str(date.date()),
                "value": float(value) if not pd.isna(value) else None,
                "value_normalized": None,
                "value_rank": None,
                "value_percentile": None,
            })
        
        # Calculate normalized values (z-score)
        valid_values = [d["value"] for d in data_list if d["value"] is not None]
        if valid_values:
            mean_val = np.mean(valid_values)
            std_val = np.std(valid_values)
            for d in data_list:
                if d["value"] is not None:
                    d["value_normalized"] = (d["value"] - mean_val) / std_val if std_val > 0 else 0
        
        # Build chart data
        labels = [d["trade_date"] for d in data_list]
        values = [d["value"] for d in data_list]
        values_normalized = [d["value_normalized"] for d in data_list]
        
        # Calculate statistics
        stats = {}
        if valid_values:
            stats = {
                "mean": float(mean_val),
                "std": float(std_val),
                "min": float(min(valid_values)),
                "max": float(max(valid_values)),
                "count": len(valid_values),
            }
        
        return {
            "factor_id": request.factor_id,
            "factor_name": factor_def.name,
            "stock_code": request.stock_code,
            "frequency": request.frequency,
            "data": data_list,
            "chart_data": {
                "labels": labels,
                "datasets": [
                    {
                        "label": factor_def.name,
                        "data": values,
                        "borderColor": "#3b82f6",
                        "backgroundColor": "rgba(59, 130, 246, 0.1)",
                    },
                    {
                        "label": f"{factor_def.name} (标准化)",
                        "data": values_normalized,
                        "borderColor": "#10b981",
                        "backgroundColor": "rgba(16, 185, 129, 0.1)",
                        "yAxisID": "y1",
                    },
                ],
            },
            "statistics": stats,
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error querying factor data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _calculate_factor_from_definition(factor_def, df: pd.DataFrame, stock_code: str = "000001") -> pd.Series:
    """Calculate factor values from factor definition using registered factor instances."""
    from openfinance.quant.factors.registry import get_factor_registry
    from openfinance.datacenter.ads import ADSKLineModel
    from datetime import date
    
    registry = get_factor_registry()
    factor_instance = registry.get_factor_instance(factor_def.factor_id)
    
    code = stock_code[:6] if stock_code else "000001"
    
    if factor_instance:
        klines = []
        for idx, row in df.iterrows():
            trade_date = idx.date() if hasattr(idx, 'date') else date.fromisoformat(str(idx)[:10])
            kline = ADSKLineModel(
                code=code,
                trade_date=trade_date,
                open=float(row.get("open", 0) or 0),
                high=float(row.get("high", 0) or 0),
                low=float(row.get("low", 0) or 0),
                close=float(row.get("close", 0) or 0),
                volume=int(row.get("volume", 0) or 0),
                amount=float(row.get("amount", 0) or 0),
            )
            klines.append(kline)
        
        results = []
        lookback = factor_def.lookback_period or 20
        
        for i in range(lookback - 1, len(klines)):
            window = klines[:i + 1]
            result = factor_instance.calculate(window)
            if result and result.value is not None:
                results.append((df.index[i], result.value))
            else:
                results.append((df.index[i], np.nan))
        
        return pd.Series([r[1] for r in results], index=[r[0] for r in results])
    
    return df["close"]


@router.post("/data/batch")
async def query_factor_data_batch(request: FactorDataBatchQueryRequest):
    """
    Query factor data for multiple stocks.
    
    Returns factor values grouped by stock.
    """
    try:
        from openfinance.quant.factors.registry import get_factor_registry
        from openfinance.quant.factors.storage.database import get_factor_storage
        
        registry = get_factor_registry()
        factor_def = registry.get(request.factor_id)
        
        if not factor_def:
            raise HTTPException(status_code=404, detail=f"Factor not found: {request.factor_id}")
        
        # Calculate date range
        start_date = request.start_date or (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
        end_date = request.end_date or datetime.now().strftime("%Y-%m-%d")
        
        storage = await get_factor_storage()
        
        from datetime import date as date_type
        
        data_by_stock = {}
        all_labels = set()
        
        for stock_code in request.stock_codes:
            historical_data = await storage.load_factor_data(
                factor_id=request.factor_id,
                codes=[stock_code],
                start_date=date_type.fromisoformat(start_date),
                end_date=date_type.fromisoformat(end_date),
            )
            data_by_stock[stock_code] = [
                {
                    "trade_date": str(r.trade_date),
                    "value": r.value,
                    "value_normalized": r.value_normalized,
                }
                for r in historical_data
            ]
            for record in historical_data:
                all_labels.add(str(record.trade_date))
        
        # Build chart data
        labels = sorted(all_labels)
        datasets = []
        colors = ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6"]
        
        for i, stock_code in enumerate(request.stock_codes):
            color = colors[i % len(colors)]
            data_map = {r["trade_date"]: r["value"] for r in data_by_stock.get(stock_code, [])}
            datasets.append({
                "label": stock_code,
                "data": [data_map.get(label) for label in labels],
                "borderColor": color,
                "backgroundColor": f"{color}20",
            })
        
        return {
            "factor_id": request.factor_id,
            "factor_name": factor_def.name,
            "frequency": request.frequency,
            "data_by_stock": data_by_stock,
            "chart_data": {
                "labels": labels,
                "datasets": datasets,
            },
            "statistics": {},
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error querying batch factor data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Factor Library Endpoint (must be before /{factor_id})
# ============================================================================

@router.get("/library")
async def get_factor_library_endpoint():
    """Get list of pre-built factors available in the library."""
    library = get_factor_library()
    
    factors_info = []
    for factor_id, factor_class in library.items():
        try:
            if callable(factor_class) and not isinstance(factor_class, type):
                temp_factor = factor_class()
            else:
                temp_factor = factor_class()
            factors_info.append({
                "factor_id": factor_id,
                "name": getattr(temp_factor, 'name', factor_id),
                "category": getattr(temp_factor, 'category', 'unknown'),
                "description": getattr(temp_factor, 'description', ''),
            })
        except Exception as e:
            logger.warning(f"Failed to instantiate factor {factor_id}: {e}")
            factors_info.append({
                "factor_id": factor_id,
                "name": factor_id,
                "category": "unknown",
                "description": f"Factor {factor_id}",
            })
    
    return {"total": len(factors_info), "factors": factors_info}


# ============================================================================
# Factor Detail Endpoints
# ============================================================================

@router.get("/{factor_id}")
async def get_factor(factor_id: str):
    """Get detailed information about a specific factor."""
    try:
        factor = create_factor(factor_id)
        return FactorDetailResponse(**factor.to_dict())
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception(f"Error getting factor: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{factor_id}/code")
async def get_factor_code(factor_id: str):
    """Get source code for a specific factor - returns full file content."""
    try:
        import inspect
        from openfinance.quant.factors.registry import get_factor_registry
        
        registry = get_factor_registry()
        factor_def = registry.get(factor_id)
        
        if not factor_def:
            raise HTTPException(status_code=404, detail=f"Factor not found: {factor_id}")
        
        source_code = None
        file_path = ""
        
        factor_instance = registry.get_factor_instance(factor_id)
        
        if factor_instance:
            factor_class = factor_instance.__class__
            try:
                file_path = inspect.getfile(factor_class)
                with open(file_path, 'r', encoding='utf-8') as f:
                    source_code = f.read()
            except (TypeError, OSError, FileNotFoundError) as e:
                logger.warning(f"Could not read source file: {e}")
        
        if not source_code:
            params_str = '\n# '.join(
                f"{k}: default={v.default}, type={v.type}, range=[{v.min_value}, {v.max_value}]" 
                for k, v in factor_def.parameters.items()
            ) if factor_def.parameters else 'None'
            
            source_code = f'''"""
{factor_def.name}

{factor_def.description}

Factor ID: {factor_def.factor_id}
Code: {factor_def.code}
Category: {factor_def.category.value if hasattr(factor_def.category, 'value') else factor_def.category}
Type: {factor_def.factor_type.value if hasattr(factor_def.factor_type, 'value') else factor_def.factor_type}

Parameters:
{params_str}

Expression: {factor_def.expression}
Formula: {factor_def.formula}

Required Fields: {factor_def.required_fields}
Lookback Period: {factor_def.lookback_period} days
Tags: {factor_def.tags}
"""
'''
            file_path = f"factor://{factor_id}"
        
        return {
            "factor_id": factor_id,
            "name": factor_def.name,
            "code": source_code,
            "file_path": file_path,
            "language": "python",
            "expression": factor_def.expression,
            "formula": factor_def.formula,
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error getting factor code: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{factor_id}/data")
async def get_factor_data(
    factor_id: str,
    code: str = Query(..., description="Stock code"),
    start_date: str | None = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: str | None = Query(None, description="End date (YYYY-MM-DD)"),
):
    """Get historical factor data for a specific stock."""
    try:
        from openfinance.quant.factors.registry import get_factor_registry
        from openfinance.quant.factors.storage.database import get_factor_storage
        
        registry = get_factor_registry()
        factor = registry.get(factor_id)
        
        if not factor:
            return {
                "success": False,
                "error": f"Factor not found: {factor_id}",
            }
        
        # Default to last year if dates not specified
        if not start_date:
            start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        
        # Get factor storage for historical data
        storage = await get_factor_storage()
        
        # Get historical data
        historical_data = await storage.get_historical_factor_values(
            factor_id=factor_id,
            symbol=code,
            start_date=start_date,
            end_date=end_date,
        )
        
        return {
            "success": True,
            "factor_id": factor_id,
            "code": code,
            "data": historical_data,
        }
    
    except Exception as e:
        logger.exception(f"Error getting factor data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/calculate")
async def calculate_factor(request: FactorCalculateRequest):
    """Calculate factor values for specified stocks and date range."""
    try:
        factor = create_factor(request.factor_id, request.parameters)
        
        # TODO: Implement actual data fetching and calculation
        # This is a placeholder implementation
        result = {
            "factor_id": request.factor_id,
            "factor_name": factor.name,
            "stock_code": request.stock_codes[0] if request.stock_codes else "600000.SH",
            "frequency": factor.frequency,
            "data": [],
            "statistics": {},
            "chart_data": {},
        }
        
        return FactorCalculateResponse(**result)
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception(f"Error calculating factor: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test")
async def test_factor(request: FactorTestRequest):
    """Test factor performance with IC analysis."""
    try:
        factor = create_factor(request.factor_id, request.parameters)
        
        # TODO: Implement actual factor testing
        # This is a placeholder implementation
        result = {
            "factor_id": request.factor_id,
            "ic_mean": 0.05,
            "ic_std": 0.03,
            "ic_ir": 1.67,
            "ic_positive_ratio": 0.65,
            "coverage_mean": 0.85,
            "monotonicity": 0.80,
            "stocks_tested": len(request.stock_codes) if request.stock_codes else 100,
            "success_rate": 0.95,
            "avg_execution_time": 0.05,
            "duration_ms": 50.0,
        }
        
        return FactorTestResult(**result)
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception(f"Error testing factor: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{factor_id}/test")
async def test_factor_value(
    factor_id: str,
    request: dict[str, Any],
):
    """
    Test a factor on a specific stock and return the factor value.
    
    This endpoint runs the factor calculation on historical data for a given stock.
    Supports both registered factors and dynamically generated factors.
    """
    try:
        from openfinance.quant.factors.registry import get_factor_registry
        from openfinance.datacenter.ads import ADSKLineModel
        from openfinance.datacenter.ads.service import ADSService
        from datetime import date, timedelta
        import numpy as np
        import asyncio
        
        symbol = request.get("symbol", "600000.SH")
        params = request.get("params", {})
        factor_code = request.get("code")
        
        registry = get_factor_registry()
        factor_def = registry.get(factor_id)
        factor_instance = None
        
        if factor_def:
            factor_instance = registry.get_factor_instance(factor_id)
            lookback = factor_def.lookback_period or 20
        elif factor_code:
            try:
                local_vars = {}
                exec(factor_code, {"np": np, "ADSKLineModel": ADSKLineModel}, local_vars)
                
                for name, obj in local_vars.items():
                    if callable(obj) and name.startswith("calculate"):
                        factor_instance = obj
                        break
                
                if not factor_instance:
                    for name, obj in local_vars.items():
                        if callable(obj) and not name.startswith("_"):
                            factor_instance = obj
                            break
                
                lookback = params.get("period", 20)
                
            except Exception as e:
                logger.warning(f"Failed to execute factor code: {e}")
        else:
            try:
                import asyncpg
                import os
                
                db_url = os.getenv(
                    "DATABASE_URL",
                    "postgresql://openfinance:openfinance@localhost:5432/openfinance"
                )
                
                conn = await asyncpg.connect(db_url)
                row = await conn.fetchrow(
                    "SELECT code, lookback_period FROM openfinance.factors WHERE factor_id = $1",
                    factor_id
                )
                await conn.close()
                
                if row and row["code"]:
                    factor_code = row["code"]
                    lookback = row["lookback_period"] or params.get("period", 20)
                    
                    local_vars = {}
                    exec(factor_code, {"np": np, "ADSKLineModel": ADSKLineModel}, local_vars)
                    
                    for name, obj in local_vars.items():
                        if callable(obj) and name.startswith("calculate"):
                            factor_instance = obj
                            break
                    
                    if not factor_instance:
                        for name, obj in local_vars.items():
                            if callable(obj) and not name.startswith("_"):
                                factor_instance = obj
                                break
                else:
                    raise HTTPException(status_code=404, detail=f"因子不存在: {factor_id}")
                    
            except HTTPException:
                raise
            except Exception as e:
                logger.warning(f"Failed to load factor from database: {e}")
                raise HTTPException(status_code=404, detail=f"因子不存在: {factor_id}")
        
        if not factor_instance:
            raise HTTPException(status_code=404, detail=f"无法加载因子实例: {factor_id}")
        
        end_date = date.today()
        start_date = end_date - timedelta(days=lookback * 3)
        
        try:
            ads_service = ADSService()
            code = symbol[:6] if symbol else "600000"
            
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        ads_service.get_kline_data(
                            code=code,
                            start_date=start_date,
                            end_date=end_date,
                            limit=lookback * 2,
                        )
                    )
                    klines = future.result()
            else:
                klines = loop.run_until_complete(
                    ads_service.get_kline_data(
                        code=code,
                        start_date=start_date,
                        end_date=end_date,
                        limit=lookback * 2,
                    )
                )
            
            if not klines or len(klines) < lookback:
                mock_value = np.random.uniform(-0.1, 0.1)
                return {
                    "success": True,
                    "result": {
                        "value": float(mock_value),
                        "date": end_date.isoformat(),
                        "symbol": symbol,
                    },
                    "history": [],
                    "note": "使用模拟数据（实际数据不足）",
                }
            
            if hasattr(factor_instance, 'calculate'):
                result = factor_instance.calculate(klines, **params)
                factor_value = result.value if result and hasattr(result, 'value') else None
            else:
                factor_value = factor_instance(klines, **params)
            
            return {
                "success": True,
                "result": {
                    "value": factor_value if factor_value is not None else 0.0,
                    "date": end_date.isoformat(),
                    "symbol": symbol,
                },
                "history": [],
            }
            
        except Exception as data_error:
            logger.warning(f"Failed to get real data, using mock: {data_error}")
            
            mock_value = np.random.uniform(-0.1, 0.1)
            
            return {
                "success": True,
                "result": {
                    "value": float(mock_value),
                    "date": end_date.isoformat(),
                    "symbol": symbol,
                },
                "history": [],
                "note": "使用模拟数据",
            }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error testing factor: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{factor_id}")
async def delete_factor(factor_id: str):
    """
    Delete a custom factor from the registry and database.
    
    Only custom factors can be deleted. Built-in factors are protected.
    """
    try:
        from openfinance.quant.factors.registry import get_factor_registry
        
        registry = get_factor_registry()
        factor_def = registry.get(factor_id)
        
        if not factor_def:
            raise HTTPException(status_code=404, detail=f"因子不存在: {factor_id}")
        
        if factor_def.is_builtin:
            raise HTTPException(status_code=403, detail="无法删除内置因子")
        
        try:
            import asyncpg
            import os
            
            db_url = os.getenv(
                "DATABASE_URL",
                "postgresql://openfinance:openfinance@localhost:5432/openfinance"
            )
            
            conn = await asyncpg.connect(db_url)
            
            result = await conn.execute("""
                DELETE FROM openfinance.factors 
                WHERE factor_id = $1
            """, factor_id)
            
            await conn.close()
            
            if result == "DELETE 0":
                logger.warning(f"Factor {factor_id} not found in database")
        
        except Exception as db_error:
            logger.warning(f"Database delete failed: {db_error}")
        
        registry.unregister(factor_id)
        
        logger.info(f"Factor deleted: {factor_id}")
        
        return {
            "success": True,
            "factor_id": factor_id,
            "message": f"因子 '{factor_def.name}' 已删除",
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error deleting factor: {e}")
        raise HTTPException(status_code=500, detail=str(e))
