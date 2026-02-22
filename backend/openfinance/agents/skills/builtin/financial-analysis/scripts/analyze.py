"""
Financial Analysis Scripts.

Provides core analysis functions for financial statement analysis.
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

from openfinance.datacenter.models.analytical.service import get_ads_service, FinancialIndicator

logger = logging.getLogger(__name__)


@dataclass
class FinancialHealth:
    """Financial health assessment."""
    profitability_score: float
    growth_score: float
    solvency_score: float
    efficiency_score: float
    overall_score: float
    assessment: str


async def analyze_financial_health(code: str, years: int = 5) -> FinancialHealth:
    """Analyze financial health of a company."""
    service = get_ads_service()
    
    indicators = await service.get_financial_indicators(code, years=years)
    quote = await service.get_stock_quote(code)
    
    if not indicators:
        return FinancialHealth(0, 0, 0, 0, 0, "数据不足")
    
    profitability_score = 0
    growth_score = 0
    solvency_score = 0
    efficiency_score = 0
    
    latest = indicators[0]
    
    if latest.roe > 20:
        profitability_score = 5
    elif latest.roe > 15:
        profitability_score = 4
    elif latest.roe > 10:
        profitability_score = 3
    else:
        profitability_score = 2
    
    if latest.debt_ratio < 30:
        solvency_score = 5
    elif latest.debt_ratio < 50:
        solvency_score = 4
    elif latest.debt_ratio < 70:
        solvency_score = 3
    else:
        solvency_score = 2
    
    if len(indicators) > 1:
        revenue_growth = (indicators[-1].revenue - indicators[0].revenue) / indicators[0].revenue if indicators[0].revenue > 0 else 0
        if revenue_growth > 0.5:
            growth_score = 5
        elif revenue_growth > 0.3:
            growth_score = 4
        elif revenue_growth > 0.1:
            growth_score = 3
        else:
            growth_score = 2
    
    overall_score = (profitability_score + growth_score + solvency_score + efficiency_score) / 4
    
    if overall_score >= 4:
        assessment = "优秀 - 财务状况健康"
    elif overall_score >= 3:
        assessment = "良好 - 财务状况稳定"
    elif overall_score >= 2:
        assessment = "一般 - 需要关注"
    else:
        assessment = "较差 - 风险较高"
    
    return FinancialHealth(
        profitability_score=profitability_score,
        growth_score=growth_score,
        solvency_score=solvency_score,
        efficiency_score=efficiency_score,
        overall_score=overall_score,
        assessment=assessment,
    )


async def run_financial_analysis(code: str) -> dict[str, Any]:
    """Run complete financial analysis."""
    service = get_ads_service()
    
    quote = await service.get_stock_quote(code)
    indicators = await service.get_financial_indicators(code, years=5)
    health = await analyze_financial_health(code)
    
    return {
        "code": code,
        "quote": {
            "name": quote.name if quote else "",
            "price": quote.price if quote else 0,
            "pe_ratio": quote.pe_ratio if quote else None,
            "pb_ratio": quote.pb_ratio if quote else None,
        },
        "indicators": [
            {
                "report_date": ind.report_date,
                "roe": ind.roe,
                "gross_margin": ind.gross_margin,
                "net_margin": ind.net_margin,
                "debt_ratio": ind.debt_ratio,
                "revenue": ind.revenue,
                "net_profit": ind.net_profit,
            }
            for ind in (indicators or [])
        ],
        "health": {
            "profitability_score": health.profitability_score,
            "growth_score": health.growth_score,
            "solvency_score": health.solvency_score,
            "overall_score": health.overall_score,
            "assessment": health.assessment,
        },
    }


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Financial Analysis")
    parser.add_argument("--code", required=True, help="Stock code")
    
    args = parser.parse_args()
    
    async def main():
        result = await run_financial_analysis(args.code)
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    
    asyncio.run(main())
