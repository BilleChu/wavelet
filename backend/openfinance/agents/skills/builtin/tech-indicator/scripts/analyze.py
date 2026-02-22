"""
Technical Indicator Analysis Scripts.

Provides core analysis functions for technical indicator analysis.
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Any, Optional

import numpy as np

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))

from openfinance.datacenter.models.analytical.service import get_ads_service

logger = logging.getLogger(__name__)


@dataclass
class TechSignal:
    """Technical signal data."""
    signal_type: str
    strength: str
    description: str
    value: Optional[float] = None


async def calculate_rsi(prices: list[float], period: int = 14) -> Optional[float]:
    """Calculate RSI indicator."""
    if len(prices) < period + 1:
        return None
    
    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    
    avg_gain = np.mean(gains[-period:])
    avg_loss = np.mean(losses[-period:])
    
    if avg_loss == 0:
        return 100.0
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return float(rsi)


async def calculate_macd(prices: list[float]) -> dict[str, float]:
    """Calculate MACD indicator."""
    if len(prices) < 26:
        return {"value": 0, "signal": 0, "hist": 0}
    
    ema12 = np.mean(prices[-12:])
    ema26 = np.mean(prices[-26:])
    macd = ema12 - ema26
    signal = macd * 0.8
    hist = macd - signal
    
    return {"value": float(macd), "signal": float(signal), "hist": float(hist)}


async def analyze_tech_indicators(
    code: str,
    days: int = 120,
) -> dict[str, Any]:
    """
    Analyze technical indicators for a stock.
    
    Args:
        code: Stock code
        days: Number of days for analysis
    
    Returns:
        Technical analysis result
    """
    service = get_ads_service()
    
    klines = await service.get_kline_data(code, limit=days)
    
    if not klines:
        return {"error": "No data available"}
    
    prices = [k.close for k in klines if k.close]
    
    if len(prices) < 20:
        return {"error": "Insufficient data for analysis"}
    
    rsi = await calculate_rsi(prices)
    macd = await calculate_macd(prices)
    
    signals = []
    
    if rsi is not None:
        if rsi < 30:
            signals.append(TechSignal("RSI超卖", "strong", f"RSI={rsi:.1f}，可能反弹", rsi))
        elif rsi > 70:
            signals.append(TechSignal("RSI超买", "strong", f"RSI={rsi:.1f}，可能回调", rsi))
    
    if macd["hist"] > 0:
        signals.append(TechSignal("MACD金叉", "medium", "MACD柱状图为正，短期趋势向好", macd["hist"]))
    elif macd["hist"] < 0:
        signals.append(TechSignal("MACD死叉", "medium", "MACD柱状图为负，短期趋势偏弱", macd["hist"]))
    
    latest = klines[-1]
    
    return {
        "code": code,
        "price": latest.close,
        "change_pct": latest.change_pct,
        "rsi_14": rsi,
        "macd": macd,
        "signals": [
            {
                "type": s.signal_type,
                "strength": s.strength,
                "description": s.description,
                "value": s.value,
            }
            for s in signals
        ],
        "trend_signal": "bullish" if len([s for s in signals if s.strength in ["strong", "medium"]]) > 0 else "neutral",
    }


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Technical Indicator Analysis")
    parser.add_argument("--code", required=True, help="Stock code")
    parser.add_argument("--days", type=int, default=120, help="Number of days")
    
    args = parser.parse_args()
    
    async def main():
        result = await analyze_tech_indicators(args.code, args.days)
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    
    asyncio.run(main())
