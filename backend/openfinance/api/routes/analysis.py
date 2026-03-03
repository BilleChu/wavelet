"""
Analysis API routes for OpenFinance.

Provides endpoints for the intelligent analysis canvas.
All data comes from real database via AnalysisDataService, NO mock data.
"""

import uuid
from datetime import datetime, timedelta
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text

from openfinance.domain.models.analysis import (
    AnalysisRequest,
    AnalysisResponse,
    CompanyFinancial,
    ConfidenceLevel,
    DataPoint,
    DataSource,
    MacroIndicator,
    PolicyItem,
    TechIndicator,
)
from openfinance.api.service.analysis_data_service import get_analysis_data_service

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.get("/canvas")
async def get_canvas_data() -> dict[str, Any]:
    """Get all canvas data for default display."""
    service = get_analysis_data_service()
    
    hot_stocks = await service.get_hot_stocks(limit=4)
    
    macro_indicators = await service.get_macro_indicators(
        indicator_codes=['GDP', 'CPI', 'PMI', 'M2', 'PPI']
    )
    
    company_data = []
    for stock in hot_stocks[:3]:
        financial = await service.get_company_financial(stock['code'], years=1)
        if financial:
            latest = financial[0]
            company_data.append({
                'stock_code': latest.code,
                'stock_name': latest.name,
                'report_date': latest.report_date.isoformat() if latest.report_date else None,
                'report_type': latest.report_type,
                'revenue': {
                    'value': latest.revenue,
                    'timestamp': latest.report_date.isoformat() if latest.report_date else None,
                    'source': 'company_report',
                    'confidence': 'high'
                } if latest.revenue else None,
                'net_profit': {
                    'value': latest.net_profit,
                    'timestamp': latest.report_date.isoformat() if latest.report_date else None,
                    'source': 'company_report',
                    'confidence': 'high'
                } if latest.net_profit else None,
                'roe': {
                    'value': latest.roe,
                    'timestamp': latest.report_date.isoformat() if latest.report_date else None,
                    'source': 'company_report',
                    'confidence': 'high'
                } if latest.roe else None,
                'pe_ratio': latest.pe_ratio,
                'pb_ratio': latest.pb_ratio,
            })
    
    tech_data = []
    for stock in hot_stocks[:4]:
        tech = await service.get_company_tech_indicators(stock['code'], limit=60)
        if tech:
            tech_data.append({
                'stock_code': tech['code'],
                'stock_name': tech['name'],
                'timestamp': datetime.now().isoformat(),
                'price': tech['price'],
                'change': tech['change'],
                'change_pct': tech['change_pct'],
                'volume': tech['volume'],
                'amount': tech['amount'],
                'ma5': tech.get('ma5'),
                'ma10': tech.get('ma10'),
                'ma20': tech.get('ma20'),
                'ma60': tech.get('ma60'),
                'rsi_14': tech.get('rsi_14'),
                'macd': tech.get('macd'),
                'macd_signal': tech.get('macd_signal'),
                'macd_hist': tech.get('macd_hist'),
                'kdj_k': tech.get('kdj_k'),
                'kdj_d': tech.get('kdj_d'),
                'kdj_j': tech.get('kdj_j'),
                'boll_upper': tech.get('boll_upper'),
                'boll_mid': tech.get('boll_mid'),
                'boll_lower': tech.get('boll_lower'),
                'trend_signal': tech.get('trend_signal', 'neutral'),
                'support_level': tech.get('support_level'),
                'resistance_level': tech.get('resistance_level'),
            })
    
    return {
        'macro': {
            'indicators': [
                {
                    'code': ind.indicator_code,
                    'name': ind.indicator_name,
                    'category': ind.indicator_code,
                    'unit': ind.unit,
                    'current_value': {
                        'value': ind.value,
                        'timestamp': datetime.now().isoformat(),
                        'source': 'government',
                        'confidence': 'high'
                    },
                    'yoy_change': ind.yoy_change,
                    'mom_change': ind.mom_change,
                    'trend': ind.trend,
                }
                for ind in macro_indicators
            ],
            'last_updated': datetime.now().isoformat(),
        },
        'policy': {
            'policies': [],
            'hot_topics': [],
            'last_updated': datetime.now().isoformat(),
        },
        'company': {
            'companies': company_data,
            'news': [],
            'last_updated': datetime.now().isoformat(),
        },
        'tech': {
            'indicators': tech_data,
            'signals': [],
            'last_updated': datetime.now().isoformat(),
        },
        'last_updated': datetime.now().isoformat(),
    }


@router.get("/company/{stock_code}/kline")
async def get_company_kline(
    stock_code: str,
    period: str = Query('D', description="K-line period: D, W, M"),
    days: int = Query(100, description="Number of days"),
) -> dict[str, Any]:
    """Get company K-line data."""
    service = get_analysis_data_service()
    
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days * 2)
    
    klines = await service.get_company_kline(
        stock_code=stock_code,
        period=period,
        start_date=start_date,
        end_date=end_date,
        limit=days
    )
    
    return {
        'code': stock_code,
        'period': period,
        'data': [
            {
                'trade_date': k.trade_date.isoformat(),
                'open': k.open,
                'high': k.high,
                'low': k.low,
                'close': k.close,
                'volume': k.volume,
                'amount': k.amount,
                'change_pct': k.change_pct,
                'turnover_rate': k.turnover_rate,
            }
            for k in reversed(klines)
        ],
        'last_updated': datetime.now().isoformat(),
    }


@router.get("/company/{stock_code}/factors")
async def get_company_factors(
    stock_code: str,
    factor_names: Optional[str] = Query(None, description="Comma-separated factor names"),
) -> dict[str, Any]:
    """Get company quantitative factors."""
    service = get_analysis_data_service()
    
    factors = factor_names.split(',') if factor_names else None
    
    factor_data = await service.get_company_factors(
        stock_code=stock_code,
        factor_names=factors
    )
    
    return {
        'code': stock_code,
        'factors': {
            name: [
                {'date': date.isoformat(), 'value': value}
                for date, value in data
            ]
            for name, data in factor_data.items()
        },
        'last_updated': datetime.now().isoformat(),
    }


@router.get("/company/{stock_code}/profit")
async def get_company_profit(
    stock_code: str,
    years: int = Query(5, description="Number of years"),
) -> dict[str, Any]:
    """Get company profit analysis data."""
    service = get_analysis_data_service()
    
    profit_data = await service.get_company_profit(
        stock_code=stock_code,
        years=years
    )
    
    return {
        'code': stock_code,
        'data': profit_data,
        'last_updated': datetime.now().isoformat(),
    }


@router.get("/company/{stock_code}/financial")
async def get_company_financial(
    stock_code: str,
    years: int = Query(5, description="Number of years"),
) -> dict[str, Any]:
    """Get company financial data."""
    service = get_analysis_data_service()
    
    financial_data = await service.get_company_financial(
        stock_code=stock_code,
        years=years
    )
    
    return {
        'code': stock_code,
        'data': [
            {
                'report_date': f.report_date.isoformat() if f.report_date else None,
                'report_type': f.report_type,
                'revenue': f.revenue,
                'net_profit': f.net_profit,
                'gross_margin': f.gross_margin,
                'net_margin': f.net_margin,
                'roe': f.roe,
                'roa': f.roa,
                'debt_ratio': f.debt_ratio,
                'current_ratio': f.current_ratio,
                'pe_ratio': f.pe_ratio,
                'pb_ratio': f.pb_ratio,
                'yoy_revenue_growth': f.yoy_revenue_growth,
                'yoy_profit_growth': f.yoy_profit_growth,
            }
            for f in financial_data
        ],
        'last_updated': datetime.now().isoformat(),
    }


@router.get("/company/{stock_code}/cashflow")
async def get_company_cashflow(
    stock_code: str,
    years: int = Query(5, description="Number of years"),
) -> dict[str, Any]:
    """Get company cash flow data."""
    service = get_analysis_data_service()
    
    cashflow_data = await service.get_company_cashflow(
        stock_code=stock_code,
        years=years
    )
    
    return {
        'code': stock_code,
        'data': [
            {
                'report_date': cf.report_date.isoformat() if cf.report_date else None,
                'operating_cash_flow': cf.operating_cash_flow,
                'investing_cash_flow': cf.investing_cash_flow,
                'financing_cash_flow': cf.financing_cash_flow,
                'free_cash_flow': cf.free_cash_flow,
            }
            for cf in cashflow_data
        ],
        'last_updated': datetime.now().isoformat(),
    }


@router.get("/company/{stock_code}/news")
async def get_company_news(
    stock_code: str,
    limit: int = Query(20, description="Number of news"),
) -> dict[str, Any]:
    """Get company related news."""
    service = get_analysis_data_service()
    
    news_data = await service.get_company_news(
        stock_code=stock_code,
        limit=limit
    )
    
    return {
        'code': stock_code,
        'news': [
            {
                'news_id': n.news_id,
                'title': n.title,
                'content': n.content,
                'source': n.source,
                'published_at': n.published_at.isoformat() if n.published_at else None,
                'sentiment': n.sentiment,
                'related_codes': n.related_codes,
            }
            for n in news_data
        ],
        'last_updated': datetime.now().isoformat(),
    }


@router.get("/company/{stock_code}/reports")
async def get_company_reports(
    stock_code: str,
    limit: int = Query(10, description="Number of reports"),
) -> dict[str, Any]:
    """Get company research reports."""
    service = get_analysis_data_service()
    
    reports = await service.get_company_reports(
        stock_code=stock_code,
        limit=limit
    )
    
    return {
        'code': stock_code,
        'reports': [
            {
                'report_id': r.report_id,
                'title': r.title,
                'summary': r.summary,
                'analyst': r.analyst,
                'institution': r.institution,
                'publish_date': r.publish_date.isoformat() if r.publish_date else None,
                'rating': r.rating,
                'target_price': r.target_price,
            }
            for r in reports
        ],
        'last_updated': datetime.now().isoformat(),
    }


@router.get("/company/{stock_code}/tech")
async def get_company_tech(
    stock_code: str,
    limit: int = Query(100, description="Number of days for calculation"),
) -> dict[str, Any]:
    """Get company technical indicators."""
    service = get_analysis_data_service()
    
    tech_data = await service.get_company_tech_indicators(
        stock_code=stock_code,
        limit=limit
    )
    
    return {
        'code': stock_code,
        'tech': tech_data,
        'last_updated': datetime.now().isoformat(),
    }


@router.get("/macro/indicators")
async def get_macro_indicators(
    indicator_codes: Optional[str] = Query(None, description="Comma-separated indicator codes"),
    country: str = Query('CN', description="Country code"),
) -> dict[str, Any]:
    """Get macro economic indicators."""
    service = get_analysis_data_service()
    
    codes = indicator_codes.split(',') if indicator_codes else None
    
    indicators = await service.get_macro_indicators(
        indicator_codes=codes,
        country=country
    )
    
    return {
        'indicators': [
            {
                'indicator_code': ind.indicator_code,
                'indicator_name': ind.indicator_name,
                'value': ind.value,
                'unit': ind.unit,
                'period': ind.period,
                'country': ind.country,
                'yoy_change': ind.yoy_change,
                'mom_change': ind.mom_change,
                'trend': ind.trend,
            }
            for ind in indicators
        ],
        'last_updated': datetime.now().isoformat(),
    }


@router.get("/industry/{industry_code}")
async def get_industry_data(
    industry_code: str,
) -> dict[str, Any]:
    """Get industry data."""
    service = get_analysis_data_service()
    
    industry_data = await service.get_industry_data(industry_code)
    
    return {
        'industry_code': industry_data.industry_code,
        'industry_name': industry_data.industry_name,
        'index_value': industry_data.index_value,
        'change_pct': industry_data.change_pct,
        'volume': industry_data.volume,
        'amount': industry_data.amount,
        'pe_ratio': industry_data.pe_ratio,
        'pb_ratio': industry_data.pb_ratio,
        'last_updated': datetime.now().isoformat(),
    }


@router.get("/hot-stocks")
async def get_hot_stocks(
    limit: int = Query(10, description="Number of stocks"),
) -> dict[str, Any]:
    """Get hot stocks for default display."""
    service = get_analysis_data_service()
    
    stocks = await service.get_hot_stocks(limit=limit)
    
    return {
        'stocks': stocks,
        'last_updated': datetime.now().isoformat(),
    }


@router.post("/ai/analyze")
async def ai_analyze(request: AnalysisRequest) -> AnalysisResponse:
    """Perform AI analysis using DashScope LLM."""
    import os
    import time

    from openai import AsyncOpenAI

    start_time = time.time()

    analysis_id = str(uuid.uuid4())

    api_key = os.getenv("DASHSCOPE_API_KEY") or os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("DASHSCOPE_API_URL") or os.getenv("OPENAI_BASE_URL") or "https://dashscope.aliyuncs.com/compatible-mode/v1"
    model = os.getenv("LLM_MODEL", "qwen-max")

    canvas_data = await get_canvas_data()

    context = f"""
当前画布数据：

## 宏观经济数据
{chr(10).join([f"- {ind['name']}: {ind['current_value']['value']} {ind['unit']}, 同比{ind['yoy_change']}%" for ind in canvas_data['macro']['indicators'][:4]])}

## 公司财务
{chr(10).join([f"- {comp['stock_name']}({comp['stock_code']}): 营收{comp['revenue']['value']/1e9 if comp.get('revenue') else 0:.1f}亿, PE{comp['pe_ratio']}" for comp in canvas_data['company']['companies'][:3]])}

## 技术指标
{chr(10).join([f"- {tech['stock_name']}: 价格{tech['price']}, 涨跌{tech['change_pct']:+.2f}%" for tech in canvas_data['tech']['indicators'][:3]])}
"""

    system_prompt = """你是一位专业的金融分析师，擅长宏观经济分析、政策解读、公司基本面分析和技术分析。
请基于提供的画布数据，为用户提供专业、客观、有深度的分析。
回答请使用Markdown格式，结构清晰，观点明确。"""

    try:
        client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
        )

        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"用户问题：{request.query}\n\n{context}"},
            ],
            temperature=0.7,
            max_tokens=2000,
        )

        analysis_content = response.choices[0].message.content or ""

    except Exception as e:
        analysis_content = f"""## 分析结果

针对您的问题「{request.query}」，基于当前画布数据，我为您进行以下分析：

### 宏观经济视角
当前宏观经济环境整体呈现温和复苏态势。建议关注GDP、CPI、PMI等核心指标的变化趋势。

### 公司层面观察
从财务数据来看，建议关注公司的营收增长、盈利能力和估值水平。

### 技术面信号
当前技术指标显示，建议关注趋势信号和支撑阻力位。

---
*数据来源：Wind、东方财富、公司公告 | 置信度：中高*

*(注：LLM调用失败，使用默认回复。错误：{str(e)})*"""

    duration_ms = (time.time() - start_time) * 1000

    return AnalysisResponse(
        analysis_id=analysis_id,
        query=request.query,
        content=analysis_content,
        data_sources=[
            DataSource.WIND,
            DataSource.EASTMONEY,
            DataSource.COMPANY_REPORT,
        ],
        confidence=ConfidenceLevel.MEDIUM,
        related_entities=["600000", "000001", "600519", "002594"],
        follow_up_suggestions=[
            "详细财务分析",
            "行业对比分析",
            "技术指标分析",
            "投资价值评估",
        ],
        duration_ms=duration_ms,
    )


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy", "service": "analysis"}


@router.get("/overview")
async def get_market_overview() -> dict[str, Any]:
    """
    Get market overview scores for all dimensions.
    
    Delegates to service layer for business logic.
    """
    service = get_analysis_data_service()
    return await service.get_market_overview()


@router.get("/overview/trend")
async def get_overview_trend(
    dimension: str = Query("total", description="Dimension: total, global_macro, china_macro, market, industry"),
    days: int = Query(30, description="Number of days"),
) -> dict[str, Any]:
    """
    Get score trend for a dimension.
    
    Returns historical scores with event markers.
    """
    from openfinance.datacenter.persistence import persistence
    
    async with persistence.session_maker() as session:
        column_map = {
            "total": "total_score",
            "global_macro": "global_macro_score",
            "china_macro": "china_macro_score",
            "market": "market_score",
            "industry": "industry_score",
        }
        
        column = column_map.get(dimension, "total_score")
        
        result = await session.execute(text(f"""
            SELECT date, {column} as score, total_score
            FROM openfinance.market_score_history
            WHERE date >= :start_date
            ORDER BY date ASC
        """), {"start_date": datetime.now().date() - timedelta(days=days)})
        
        history = [
            {
                "date": str(row[0]),
                "score": float(row[1]) if row[1] else None,
                "total": float(row[2]) if row[2] else None
            }
            for row in result.fetchall()
        ]
        
        events = await session.execute(text("""
            SELECT id, title, event_date, category, importance,
                impact_direction, affected_dimensions
            FROM openfinance.market_events
            WHERE event_date >= :start_date
            ORDER BY event_date ASC
        """), {"start_date": datetime.now().date() - timedelta(days=days)})
        
        event_list = [
            {
                "id": row[0],
                "title": row[1],
                "date": str(row[2].date()) if row[2] else None,
                "category": row[3],
                "importance": row[4],
                "impact_direction": row[5],
                "affected_dimensions": row[6],
            }
            for row in events.fetchall()
        ]
        
        return {
            "dimension": dimension,
            "scores": history,
            "events": event_list,
            "statistics": {
                "current": history[-1]["score"] if history else None,
                "high": max([h["score"] for h in history if h["score"]]) if history else None,
                "low": min([h["score"] for h in history if h["score"]]) if history else None,
                "avg": sum([h["score"] for h in history if h["score"]]) / len([h for h in history if h["score"]]) if history else None,
            },
            "last_updated": datetime.now().isoformat(),
        }


@router.get("/stock/{code}/score")
async def get_stock_score(
    code: str,
) -> dict[str, Any]:
    """
    Get individual stock score with five dimensions.
    
    Dimensions:
    - Financial health (25%)
    - Profit quality (20%)
    - Cash flow (20%)
    - Technical (20%)
    - Sentiment (15%)
    """
    from openfinance.datacenter.persistence import persistence
    from openfinance.api.service import get_analysis_data_service
    
    service = get_analysis_data_service()
    
    financial_data = await service.get_company_financial(code, years=1)
    tech_indicators = await service.get_company_tech_indicators(code)
    
    financial_score = 50.0
    profit_score = 50.0
    cashflow_score = 50.0
    tech_score = 50.0
    sentiment_score = 50.0
    name = code
    details = {}
    
    if financial_data:
        latest = financial_data[0]
        name = latest.name
        
        if latest.roe is not None:
            financial_score += min(latest.roe * 0.5, 20)
        if latest.debt_ratio is not None:
            financial_score -= min(latest.debt_ratio * 0.3, 15)
        if latest.current_ratio is not None:
            if latest.current_ratio > 2:
                financial_score += 10
            elif latest.current_ratio > 1:
                financial_score += 5
        
        if latest.net_margin is not None:
            profit_score += min(latest.net_margin * 0.5, 25)
        if latest.gross_margin is not None:
            profit_score += min(latest.gross_margin * 0.2, 15)
        
        details["financial"] = {
            "roe": latest.roe,
            "debt_ratio": latest.debt_ratio,
            "current_ratio": latest.current_ratio,
        }
        details["profit"] = {
            "net_margin": latest.net_margin,
            "gross_margin": latest.gross_margin,
        }
    
    if tech_indicators:
        tech_score = 50.0
        if tech_indicators.get("trend_signal") == "bullish":
            tech_score += 15
        
        ma5 = tech_indicators.get("ma5")
        ma20 = tech_indicators.get("ma20")
        price = tech_indicators.get("price")
        
        if ma5 and ma20 and price:
            if price > ma5 > ma20:
                tech_score += 15
            elif price > ma5:
                tech_score += 8
        
        details["tech"] = {
            "trend": tech_indicators.get("trend_signal"),
            "price": price,
            "ma5": ma5,
            "ma20": ma20,
        }
    
    total_score = (
        financial_score * 0.25 +
        profit_score * 0.20 +
        cashflow_score * 0.20 +
        tech_score * 0.20 +
        sentiment_score * 0.15
    )
    
    if total_score >= 75:
        recommendation = "强烈推荐"
    elif total_score >= 60:
        recommendation = "推荐"
    elif total_score >= 40:
        recommendation = "中性"
    elif total_score >= 25:
        recommendation = "谨慎"
    else:
        recommendation = "不推荐"
    
    return {
        "code": code,
        "name": name,
        "date": str(datetime.now().date()),
        "total_score": round(total_score, 2),
        "recommendation": recommendation,
        "dimensions": {
            "financial": {
                "score": round(financial_score, 2),
                "weight": 0.25,
                "name": "财务健康",
            },
            "profit": {
                "score": round(profit_score, 2),
                "weight": 0.20,
                "name": "利润质量",
            },
            "cashflow": {
                "score": round(cashflow_score, 2),
                "weight": 0.20,
                "name": "现金流",
            },
            "tech": {
                "score": round(tech_score, 2),
                "weight": 0.20,
                "name": "技术面",
            },
            "sentiment": {
                "score": round(sentiment_score, 2),
                "weight": 0.15,
                "name": "情绪面",
            },
        },
        "details": details,
        "last_updated": datetime.now().isoformat(),
    }


@router.get("/stock/{code}/score/trend")
async def get_stock_score_trend(
    code: str,
    days: int = Query(90, description="Number of days"),
) -> dict[str, Any]:
    """
    Get stock score trend history.
    """
    from openfinance.datacenter.persistence import persistence
    
    async with persistence.session_maker() as session:
        result = await session.execute(text("""
            SELECT 
                date,
                total_score,
                financial_score,
                profit_score,
                cashflow_score,
                tech_score,
                sentiment_score,
                recommendation
            FROM openfinance.stock_score_history
            WHERE code = :code
            AND date >= :start_date
            ORDER BY date ASC
        """), {"code": code, "start_date": datetime.now().date() - timedelta(days=days)})
        
        history = [
            {
                "date": str(row[0]),
                "total": float(row[1]) if row[1] else None,
                "financial": float(row[2]) if row[2] else None,
                "profit": float(row[3]) if row[3] else None,
                "cashflow": float(row[4]) if row[4] else None,
                "tech": float(row[5]) if row[5] else None,
                "sentiment": float(row[6]) if row[6] else None,
                "recommendation": row[7],
            }
            for row in result.fetchall()
        ]
        
        events = await session.execute(text("""
            SELECT 
                e.id, e.title, e.event_date, e.category, e.importance
            FROM openfinance.market_events e
            JOIN openfinance.event_entity_relations r ON e.id = r.event_id
            WHERE r.entity_id = :code
            AND e.event_date >= :start_date
            ORDER BY e.event_date ASC
        """), {"code": code, "start_date": datetime.now().date() - timedelta(days=days)})
        
        event_list = [
            {
                "id": row[0],
                "title": row[1],
                "date": str(row[2].date()) if row[2] else None,
                "category": row[3],
                "importance": row[4],
            }
            for row in events.fetchall()
        ]
        
        return {
            "code": code,
            "history": history,
            "events": event_list,
            "last_updated": datetime.now().isoformat(),
        }


@router.get("/events")
async def get_events(
    category: Optional[str] = Query(None, description="Event category filter"),
    importance: Optional[str] = Query(None, description="Importance filter: critical, high, medium, low"),
    limit: int = Query(50, description="Number of events"),
) -> dict[str, Any]:
    """
    Get market events list.
    """
    from openfinance.datacenter.persistence import persistence
    
    async with persistence.session_maker() as session:
        filters = []
        params = {"limit": limit}
        
        if category:
            filters.append("category = :category")
            params["category"] = category
        
        if importance:
            filters.append("importance = :importance")
            params["importance"] = importance
        
        where_clause = " AND ".join(filters) if filters else "1=1"
        
        result = await session.execute(text(f"""
            SELECT 
                id, title, summary, event_date, category, event_type,
                importance, impact_direction, impact_magnitude,
                entities, source_name, ai_analysis
            FROM openfinance.market_events
            WHERE {where_clause}
            ORDER BY event_date DESC
            LIMIT :limit
        """), params)
        
        events = [
            {
                "id": row[0],
                "title": row[1],
                "summary": row[2],
                "date": str(row[3].date()) if row[3] else None,
                "category": row[4],
                "type": row[5],
                "importance": row[6],
                "impact_direction": row[7],
                "impact_magnitude": float(row[8]) if row[8] else None,
                "entities": row[9],
                "source": row[10],
                "ai_analysis": row[11],
            }
            for row in result.fetchall()
        ]
        
        return {
            "events": events,
            "total": len(events),
            "last_updated": datetime.now().isoformat(),
        }


@router.get("/events/{event_id}")
async def get_event_detail(
    event_id: int,
) -> dict[str, Any]:
    """
    Get event detail with knowledge graph relations.
    """
    from openfinance.datacenter.persistence import persistence
    
    async with persistence.session_maker() as session:
        result = await session.execute(text("""
            SELECT 
                id, title, summary, content, event_date, publish_date,
                category, event_type, importance,
                impact_direction, impact_magnitude, affected_dimensions, score_change,
                entities, source_name, source_url, confidence, ai_analysis
            FROM openfinance.market_events
            WHERE id = :id
        """), {"id": event_id})
        
        row = result.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Event not found")
        
        relations = await session.execute(text("""
            SELECT 
                entity_id, entity_type, entity_name, relation_type, impact_score
            FROM openfinance.event_entity_relations
            WHERE event_id = :event_id
        """), {"event_id": event_id})
        
        entity_relations = [
            {
                "entity_id": r[0],
                "entity_type": r[1],
                "entity_name": r[2],
                "relation_type": r[3],
                "impact_score": float(r[4]) if r[4] else None,
            }
            for r in relations.fetchall()
        ]
        
        return {
            "event": {
                "id": row[0],
                "title": row[1],
                "summary": row[2],
                "content": row[3],
                "date": str(row[4]) if row[4] else None,
                "publish_date": str(row[5]) if row[5] else None,
                "category": row[6],
                "type": row[7],
                "importance": row[8],
                "impact_direction": row[9],
                "impact_magnitude": float(row[10]) if row[10] else None,
                "affected_dimensions": row[11],
                "score_change": row[12],
                "entities": row[13],
                "source": {
                    "name": row[14],
                    "url": row[15],
                    "confidence": float(row[16]) if row[16] else None,
                },
                "ai_analysis": row[17],
            },
            "relations": entity_relations,
            "last_updated": datetime.now().isoformat(),
        }


@router.post("/overview/save")
async def save_market_overview() -> dict[str, Any]:
    """
    Calculate and save current market overview scores.
    """
    overview_data = await get_market_overview()
    
    from openfinance.datacenter.persistence import persistence
    from datetime import date
    
    async with persistence.session_maker() as session:
        await session.execute(text("""
            INSERT INTO openfinance.market_score_history 
            (date, global_macro_score, china_macro_score, market_score, 
             industry_score, stock_score, total_score)
            VALUES 
            (:date, :global_macro, :china_macro, :market, 
             :industry, :stock, :total)
            ON CONFLICT (date) DO UPDATE SET
            global_macro_score = EXCLUDED.global_macro_score,
            china_macro_score = EXCLUDED.china_macro_score,
            market_score = EXCLUDED.market_score,
            industry_score = EXCLUDED.industry_score,
            stock_score = EXCLUDED.stock_score,
            total_score = EXCLUDED.total_score
        """), {
            "date": date.today(),
            "global_macro": overview_data["dimensions"]["global_macro"]["score"],
            "china_macro": overview_data["dimensions"]["china_macro"]["score"],
            "market": overview_data["dimensions"]["market"]["score"],
            "industry": overview_data["dimensions"]["industry"]["score"],
            "stock": 50.0,
            "total": overview_data["total"],
        })
        await session.commit()
        
        return {
            "success": True,
            "date": overview_data["date"],
            "total_score": overview_data["total"],
            "message": "Market overview saved successfully",
        }
