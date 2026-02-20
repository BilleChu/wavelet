"""
Intent API Routes for OpenFinance.
"""

import logging
from typing import Any

from fastapi import APIRouter

from openfinance.models.intent import IntentType, Entity, EntityType

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/intent")
async def classify_intent(query: str) -> dict[str, Any]:
    """Classify the intent of a user query."""
    if "银行" in query or "股票" in query:
        intent_type = IntentType.STOCK_SEARCH
    elif "行业" in query:
        intent_type = IntentType.INDUSTRY_SEARCH
    elif "宏观" in query or "GDP" in query:
        intent_type = IntentType.MACRO_SEARCH
    elif "分析" in query:
        intent_type = IntentType.STOCK_ANALYSIS
    elif "巴菲特" in query or "达里奥" in query:
        intent_type = IntentType.ROLE_OPINION
    else:
        intent_type = IntentType.UNKNOWN

    return {
        "intent_type": intent_type.value,
        "confidence": 0.95,
        "entities": [],
    }


@router.get("/intent/types")
async def get_intent_types() -> dict[str, Any]:
    """Get all supported intent types."""
    return {
        "intent_types": [
            {"type": IntentType.STOCK_SEARCH.value, "description": "股票搜索"},
            {"type": IntentType.INDUSTRY_SEARCH.value, "description": "行业搜索"},
            {"type": IntentType.MACRO_SEARCH.value, "description": "宏观搜索"},
            {"type": IntentType.STOCK_ANALYSIS.value, "description": "股票分析"},
            {"type": IntentType.ROLE_OPINION.value, "description": "角色观点"},
        ]
    }
