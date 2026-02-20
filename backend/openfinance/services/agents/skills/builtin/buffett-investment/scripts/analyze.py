"""
Buffett Investment Analysis Scripts.

Provides Warren Buffett-style investment analysis.
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
class MoatAnalysis:
    """Moat analysis result."""
    brand_power: float
    pricing_power: float
    switching_costs: float
    cost_advantage: float
    overall_score: float


@dataclass
class IntrinsicValue:
    """Intrinsic value calculation result."""
    intrinsic_value: float
    current_price: float
    margin_of_safety: float
    recommendation: str


async def analyze_moat(code: str) -> MoatAnalysis:
    """Analyze competitive moat."""
    service = get_ads_service()
    
    indicators = await service.get_financial_indicators(code, years=5)
    
    brand_power = 3.0
    pricing_power = 3.0
    switching_costs = 3.0
    cost_advantage = 3.0
    
    if indicators:
        latest = indicators[0]
        
        if latest.gross_margin > 50:
            pricing_power = 4.5
        elif latest.gross_margin > 30:
            pricing_power = 3.5
        
        if latest.roe > 20:
            brand_power = 4.5
        elif latest.roe > 15:
            brand_power = 3.5
    
    overall_score = (brand_power + pricing_power + switching_costs + cost_advantage) / 4
    
    return MoatAnalysis(
        brand_power=brand_power,
        pricing_power=pricing_power,
        switching_costs=switching_costs,
        cost_advantage=cost_advantage,
        overall_score=overall_score,
    )


async def calculate_intrinsic_value(code: str) -> Optional[IntrinsicValue]:
    """Calculate intrinsic value using DCF model."""
    service = get_ads_service()
    
    quote = await service.get_stock_quote(code)
    indicators = await service.get_financial_indicators(code, years=5)
    
    if not quote or not indicators:
        return None
    
    latest = indicators[0]
    
    free_cash_flow = latest.net_profit * 0.8 if latest.net_profit else 100
    growth_rate = 0.08
    discount_rate = 0.10
    
    terminal_value = free_cash_flow * (1 + growth_rate) / (discount_rate - growth_rate)
    intrinsic_value = (free_cash_flow + terminal_value) / (1 + discount_rate)
    
    intrinsic_per_share = intrinsic_value / 10
    
    current_price = quote.price if quote.price > 0 else 100
    margin_of_safety = (intrinsic_per_share - current_price) / current_price
    
    recommendation = "hold"
    if margin_of_safety > 0.25:
        recommendation = "buy"
    elif margin_of_safety < -0.25:
        recommendation = "sell"
    
    return IntrinsicValue(
        intrinsic_value=intrinsic_per_share,
        current_price=current_price,
        margin_of_safety=margin_of_safety,
        recommendation=recommendation,
    )


async def run_buffett_analysis(code: str) -> dict[str, Any]:
    """Run complete Buffett-style analysis."""
    service = get_ads_service()
    
    quote = await service.get_stock_quote(code)
    indicators = await service.get_financial_indicators(code, years=5)
    moat = await analyze_moat(code)
    intrinsic = await calculate_intrinsic_value(code)
    
    return {
        "code": code,
        "quote": {
            "name": quote.name if quote else "",
            "price": quote.price if quote else 0,
        },
        "indicators": [
            {
                "report_date": ind.report_date,
                "roe": ind.roe,
                "gross_margin": ind.gross_margin,
                "net_margin": ind.net_margin,
                "debt_ratio": ind.debt_ratio,
            }
            for ind in (indicators or [])[:4]
        ],
        "moat": {
            "brand_power": moat.brand_power,
            "pricing_power": moat.pricing_power,
            "switching_costs": moat.switching_costs,
            "cost_advantage": moat.cost_advantage,
            "overall_score": moat.overall_score,
        },
        "intrinsic_value": {
            "value": intrinsic.intrinsic_value if intrinsic else None,
            "current_price": intrinsic.current_price if intrinsic else None,
            "margin_of_safety": intrinsic.margin_of_safety if intrinsic else None,
            "recommendation": intrinsic.recommendation if intrinsic else "unknown",
        },
    }


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Buffett Investment Analysis")
    parser.add_argument("--code", required=True, help="Stock code")
    parser.add_argument("--analysis", choices=["full", "moat", "intrinsic", "management"],
                        default="full", help="Analysis type")
    
    args = parser.parse_args()
    
    async def main():
        if args.analysis == "moat":
            result = await analyze_moat(args.code)
            result = {"moat": result.__dict__}
        elif args.analysis == "intrinsic":
            result = await calculate_intrinsic_value(args.code)
            result = {"intrinsic_value": result.__dict__ if result else None}
        else:
            result = await run_buffett_analysis(args.code)
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    
    asyncio.run(main())
