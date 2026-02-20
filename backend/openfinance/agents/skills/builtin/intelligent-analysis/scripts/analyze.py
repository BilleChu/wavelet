"""
Intelligent Analysis Scripts.

Provides comprehensive multi-dimensional investment analysis.
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

from openfinance.datacenter.ads.service import get_ads_service

logger = logging.getLogger(__name__)


@dataclass
class AnalysisDimension:
    """Analysis dimension result."""
    name: str
    signal: str
    weight: float
    score: float
    details: dict


async def run_intelligent_analysis(code: str) -> dict[str, Any]:
    """
    Run comprehensive intelligent analysis.
    
    Args:
        code: Stock code
    
    Returns:
        Complete analysis result
    """
    service = get_ads_service()
    
    quote = await service.get_stock_quote(code)
    indicators = await service.get_financial_indicators(code, years=3)
    klines = await service.get_kline_data(code, limit=120)
    
    dimensions = []
    
    macro_signal = "neutral"
    macro_score = 0.0
    macro_weight = 0.20
    dimensions.append(AnalysisDimension(
        name="宏观环境",
        signal=macro_signal,
        weight=macro_weight,
        score=macro_score,
        details={"cycle": "recovery", "policy": "accommodative"},
    ))
    
    policy_signal = "neutral"
    policy_score = 0.0
    policy_weight = 0.20
    dimensions.append(AnalysisDimension(
        name="政策影响",
        signal=policy_signal,
        weight=policy_weight,
        score=policy_score,
        details={"impact": "medium", "direction": "positive"},
    ))
    
    fundamental_signal = "neutral"
    fundamental_score = 0.0
    fundamental_weight = 0.35
    
    if indicators:
        latest = indicators[0]
        if latest.roe > 15:
            fundamental_signal = "bullish"
            fundamental_score = 0.3
        elif latest.roe > 10:
            fundamental_signal = "neutral"
            fundamental_score = 0.1
    
    dimensions.append(AnalysisDimension(
        name="基本面",
        signal=fundamental_signal,
        weight=fundamental_weight,
        score=fundamental_score,
        details={"roe": indicators[0].roe if indicators else None, "pe": None},
    ))
    
    tech_signal = "neutral"
    tech_score = 0.0
    tech_weight = 0.25
    
    if klines and len(klines) > 20:
        prices = [k.close for k in klines if k.close]
        if prices:
            ma20 = np.mean(prices[-20:])
            if prices[-1] > ma20:
                tech_signal = "bullish"
                tech_score = 0.15
    
    dimensions.append(AnalysisDimension(
        name="技术面",
        signal=tech_signal,
        weight=tech_weight,
        score=tech_score,
        details={"trend": "up" if tech_signal == "bullish" else "neutral"},
    ))
    
    total_score = sum(d.score for d in dimensions)
    
    recommendation = "hold"
    if total_score > 0.3:
        recommendation = "buy"
    elif total_score < -0.1:
        recommendation = "sell"
    
    return {
        "code": code,
        "quote": {
            "name": quote.name if quote else "",
            "price": quote.price if quote else 0,
        },
        "dimensions": [
            {
                "name": d.name,
                "signal": d.signal,
                "weight": d.weight,
                "score": d.score,
                "details": d.details,
            }
            for d in dimensions
        ],
        "total_score": total_score,
        "recommendation": recommendation,
    }


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Intelligent Analysis")
    parser.add_argument("--code", required=True, help="Stock code")
    
    args = parser.parse_args()
    
    async def main():
        result = await run_intelligent_analysis(args.code)
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    
    asyncio.run(main())
