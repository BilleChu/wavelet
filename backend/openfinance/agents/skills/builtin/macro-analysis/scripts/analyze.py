"""
Macro Economic Analysis Scripts.

Provides core analysis functions for macroeconomic analysis.
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

from openfinance.datacenter.models.analytical.service import get_ads_service, MacroIndicator

logger = logging.getLogger(__name__)


@dataclass
class MacroAnalysis:
    """Macro analysis result."""
    country: str
    indicators: list[MacroIndicator]
    economic_cycle: str
    policy_stance: str
    outlook: str
    investment_implications: dict


async def get_macro_indicators(
    country: str = "CN",
    indicators: list[str] | None = None,
) -> list[MacroIndicator]:
    """
    Get macro economic indicators.
    
    Args:
        country: Country code
        indicators: List of indicator codes to fetch
    
    Returns:
        List of MacroIndicator objects
    """
    service = get_ads_service()
    
    if indicators is None:
        indicators = ["GDP", "CPI", "PPI", "PMI", "M2", "社会融资规模"]
    
    results = []
    
    try:
        macro_data = await service.get_macro_indicators(indicators, country)
        
        for item in macro_data:
            trend = "stable"
            if item.yoy_change is not None:
                if item.yoy_change > 0.5:
                    trend = "up"
                elif item.yoy_change < -0.5:
                    trend = "down"
            
            results.append(MacroIndicator(
                indicator_code=item.indicator_code,
                indicator_name=item.indicator_name,
                value=item.value,
                unit=item.unit,
                period=item.period,
                country=item.country,
                yoy_change=item.yoy_change,
            ))
    except Exception as e:
        logger.error(f"Failed to get macro indicators: {e}")
    
    return results


async def analyze_economic_cycle(
    country: str = "CN",
) -> dict[str, Any]:
    """
    Analyze current economic cycle.
    
    Args:
        country: Country code
    
    Returns:
        Economic cycle analysis
    """
    indicators = await get_macro_indicators(country)
    
    gdp_growth = None
    cpi = None
    pmi = None
    
    for ind in indicators:
        if ind.indicator_code == "GDP":
            gdp_growth = ind.value
        elif ind.indicator_code == "CPI":
            cpi = ind.value
        elif ind.indicator_code == "PMI":
            pmi = ind.value
    
    cycle = "unknown"
    if gdp_growth is not None:
        if gdp_growth > 6:
            cycle = "expansion"
        elif gdp_growth > 4:
            cycle = "recovery"
        elif gdp_growth > 2:
            cycle = "slowdown"
        else:
            cycle = "recession"
    
    policy_stance = "neutral"
    if cpi is not None:
        if cpi > 3:
            policy_stance = "tightening"
        elif cpi < 1:
            policy_stance = "accommodative"
    
    return {
        "country": country,
        "cycle": cycle,
        "policy_stance": policy_stance,
        "gdp_growth": gdp_growth,
        "cpi": cpi,
        "pmi": pmi,
    }


async def analyze_policy_impact(
    policy_type: str = "monetary",
    country: str = "CN",
) -> dict[str, Any]:
    """
    Analyze policy impact on markets.
    
    Args:
        policy_type: Type of policy (monetary, fiscal, industrial)
        country: Country code
    
    Returns:
        Policy impact analysis
    """
    service = get_ads_service()
    
    news = await service.get_news(keyword="货币政策" if policy_type == "monetary" else "财政政策", limit=10)
    
    affected_sectors = {
        "monetary": {
            "受益板块": ["银行", "房地产", "基建"],
            "承压板块": ["高耗能行业"],
        },
        "fiscal": {
            "受益板块": ["基建", "新能源", "科技"],
            "承压板块": [],
        },
    }
    
    return {
        "policy_type": policy_type,
        "country": country,
        "affected_sectors": affected_sectors.get(policy_type, {}),
        "recent_news": [
            {"title": item.get("title", ""), "date": item.get("published_at", "")}
            for item in news[:5]
        ],
    }


async def run_macro_analysis(
    country: str = "CN",
    analysis_type: str = "full",
) -> dict[str, Any]:
    """
    Run complete macro analysis.
    
    Args:
        country: Country code
        analysis_type: Type of analysis (full, indicators, cycle, policy)
    
    Returns:
        Complete analysis result
    """
    result = {"country": country}
    
    if analysis_type in ["full", "indicators"]:
        indicators = await get_macro_indicators(country)
        result["indicators"] = [
            {
                "code": ind.indicator_code,
                "name": ind.indicator_name,
                "value": ind.value,
                "unit": ind.unit,
                "trend": "stable",
                "yoy_change": ind.yoy_change,
            }
            for ind in indicators
        ]
    
    if analysis_type in ["full", "cycle"]:
        cycle = await analyze_economic_cycle(country)
        result["economic_cycle"] = cycle["cycle"]
        result["policy_stance"] = cycle["policy_stance"]
    
    if analysis_type in ["full", "policy"]:
        policy = await analyze_policy_impact("monetary", country)
        result["policy_impact"] = policy["affected_sectors"]
    
    return result


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Macro Economic Analysis")
    parser.add_argument("--country", default="CN", help="Country code")
    parser.add_argument("--analysis", choices=["full", "indicators", "cycle", "policy"],
                        default="full", help="Analysis type")
    
    args = parser.parse_args()
    
    async def main():
        result = await run_macro_analysis(args.country, args.analysis)
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    
    asyncio.run(main())
