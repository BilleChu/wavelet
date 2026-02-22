"""
Policy Monitor Scripts.

Provides core analysis functions for policy monitoring.
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Any, Optional

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))

from openfinance.datacenter.models.analytical.service import get_ads_service

logger = logging.getLogger(__name__)


@dataclass
class PolicyImpact:
    """Policy impact analysis result."""
    policy_type: str
    impact_level: str
    affected_sectors: dict
    affected_stocks: list


async def analyze_policy(
    policy_type: str = "monetary",
    limit: int = 10,
) -> dict[str, Any]:
    """
    Analyze policy impact.
    
    Args:
        policy_type: Type of policy (monetary, fiscal, industrial)
        limit: Number of news to fetch
    
    Returns:
        Policy analysis result
    """
    service = get_ads_service()
    
    keyword_map = {
        "monetary": "货币政策",
        "fiscal": "财政政策",
        "industrial": "产业政策",
    }
    
    news = await service.get_news(keyword=keyword_map.get(policy_type, "政策"), limit=limit)
    
    affected_sectors = {
        "monetary": {
            "受益板块": ["银行", "房地产", "基建"],
            "承压板块": ["高耗能行业"],
        },
        "fiscal": {
            "受益板块": ["基建", "新能源", "科技"],
            "承压板块": [],
        },
        "industrial": {
            "受益板块": ["新能源", "半导体", "医药"],
            "承压板块": ["传统制造业"],
        },
    }
    
    return {
        "policy_type": policy_type,
        "affected_sectors": affected_sectors.get(policy_type, {}),
        "recent_news": [
            {
                "title": n.get("title", ""),
                "source": n.get("source", ""),
                "date": n.get("published_at", ""),
            }
            for n in news[:5]
        ],
    }


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Policy Monitor")
    parser.add_argument("--type", choices=["monetary", "fiscal", "industrial"],
                        default="monetary", help="Policy type")
    
    args = parser.parse_args()
    
    async def main():
        result = await analyze_policy(args.type)
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    
    asyncio.run(main())
