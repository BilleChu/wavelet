"""
Factor Calculation Engine.

Provides high-performance factor calculation with:
- Parallel processing
- Caching
- Batch calculation
"""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import date
from typing import Any, Callable

from .base import FactorResult
from .registry import get_factor_registry
from .data_source import get_data_source

logger = logging.getLogger(__name__)


@dataclass
class EngineConfig:
    """Configuration for the calculation engine."""
    
    max_workers: int = 4
    use_cache: bool = True
    save_to_db: bool = True
    progress_callback: Callable[[int, int], None] | None = None


class FactorEngine:
    """
    High-performance factor calculation engine.
    
    Features:
    - Parallel factor calculation across multiple stocks
    - Automatic caching
    - Database persistence
    """
    
    def __init__(self, config: EngineConfig | None = None):
        self.config = config or EngineConfig()
        self._registry = get_factor_registry()
        self._data_source = get_data_source()
        self._cache = None
        self._storage = None
        self._executor = ThreadPoolExecutor(max_workers=self.config.max_workers)
    
    async def initialize(self) -> None:
        """Initialize engine components."""
        if self.config.use_cache:
            from .storage.cache import get_factor_cache
            self._cache = await get_factor_cache()
        
        if self.config.save_to_db:
            from .storage.database import get_factor_storage
            self._storage = await get_factor_storage()
    
    async def calculate(
        self,
        factor_id: str,
        code: str,
        trade_date: date,
        params: dict[str, Any] | None = None,
    ) -> FactorResult | None:
        """
        Calculate factor for a single stock.
        
        Args:
            factor_id: Factor identifier
            code: Stock code
            trade_date: Trading date
            params: Factor parameters
        
        Returns:
            FactorResult or None if calculation fails
        """
        factor_def = self._registry.get(factor_id)
        if not factor_def:
            logger.error(f"Factor not found: {factor_id}")
            return None
        
        if self._cache:
            cached = await self._cache.get(factor_id, code, trade_date, params)
            if cached:
                return cached
        
        factor_instance = self._registry.get_factor_instance(factor_id)
        if not factor_instance:
            return None
        
        lookback = factor_def.lookback_period
        klines = await self._data_source.get_latest_klines(code, lookback * 2)
        
        if not klines:
            return None
        
        result = factor_instance.calculate(klines, **(params or {}))
        
        if result and self._cache:
            await self._cache.set(result, params)
        
        return result
    
    async def calculate_batch(
        self,
        factor_id: str,
        codes: list[str],
        trade_date: date,
        params: dict[str, Any] | None = None,
    ) -> list[FactorResult]:
        """
        Calculate factor for multiple stocks in parallel.
        
        Args:
            factor_id: Factor identifier
            codes: List of stock codes
            trade_date: Trading date
            params: Factor parameters
        
        Returns:
            List of FactorResult objects
        """
        results = []
        total = len(codes)
        completed = 0
        
        semaphore = asyncio.Semaphore(self.config.max_workers)
        
        async def calculate_one(code: str) -> FactorResult | None:
            nonlocal completed
            
            async with semaphore:
                try:
                    result = await self.calculate(factor_id, code, trade_date, params)
                    
                    completed += 1
                    if self.config.progress_callback:
                        self.config.progress_callback(completed, total)
                    
                    return result
                except Exception as e:
                    logger.error(f"Failed to calculate {factor_id} for {code}: {e}")
                    return None
        
        tasks = [calculate_one(code) for code in codes]
        task_results = await asyncio.gather(*tasks)
        
        results = [r for r in task_results if r is not None]
        
        if self._storage and results:
            await self._storage.save_factor_data_batch(results)
        
        return results
    
    async def calculate_universe(
        self,
        factor_id: str,
        trade_date: date,
        params: dict[str, Any] | None = None,
        universe: list[str] | None = None,
    ) -> dict[str, float]:
        """
        Calculate factor for entire universe.
        
        Args:
            factor_id: Factor identifier
            trade_date: Trading date
            params: Factor parameters
            universe: Optional list of stock codes
        
        Returns:
            Dictionary mapping stock codes to factor values
        """
        if universe is None:
            universe = await self._get_default_universe()
        
        results = await self.calculate_batch(factor_id, universe, trade_date, params)
        
        return {r.code: r.value for r in results if r.value is not None}
    
    async def _get_default_universe(self) -> list[str]:
        """Get default stock universe."""
        return [
            "600000.SH", "600004.SH", "600006.SH", "600007.SH", "600008.SH",
            "600009.SH", "600010.SH", "600011.SH", "600012.SH", "600015.SH",
        ]
    
    def close(self) -> None:
        """Close engine resources."""
        self._executor.shutdown(wait=False)


_engine: FactorEngine | None = None


async def get_factor_engine() -> FactorEngine:
    """Get the global factor engine instance."""
    global _engine
    if _engine is None:
        _engine = FactorEngine()
        await _engine.initialize()
    return _engine
