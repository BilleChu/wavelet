"""
Analysis task executors for market scoring and events.

Includes:
- Market score calculation (based on quant factors)
- Market event collection (from news and announcements)
- Stock score calculation (for individual stocks)
"""

import logging
from datetime import datetime, timedelta, date as date_type
from typing import Any
from pathlib import Path

from .registry import (
    TaskExecutor,
    TaskCategory,
    TaskPriority,
    TaskParameter,
    TaskOutput,
    TaskProgress,
    task_executor,
)

logger = logging.getLogger(__name__)


@task_executor(
    task_type="market_score_calculation",
    name="市场评分计算",
    description="基于量化因子计算市场多维度评分并保存到数据库",
    category=TaskCategory.ANALYSIS,
    source="internal",
    priority=TaskPriority.HIGH,
    timeout=300.0,
    parameters=[
        TaskParameter(
            name="save_to_db",
            type="boolean",
            default=True,
            description="是否保存到数据库",
        ),
        TaskParameter(
            name="include_stock_scores",
            type="boolean",
            default=False,
            description="是否计算个股评分",
        ),
    ],
    output=TaskOutput(
        data_type="market_score",
        table_name="market_score_history",
        description="市场评分历史数据",
        fields=["date", "global_macro_score", "china_macro_score", "market_score", "industry_score", "total_score"],
    ),
    tags=["analysis", "scoring", "quant"],
)
class MarketScoreCalculationExecutor(TaskExecutor[Any]):
    """Executor for market score calculation based on quant factors."""
    
    def __init__(self):
        from openfinance.quant.factors.scoring_factors import (
            load_scoring_factors_from_config,
        )
        self._config_dir = Path(__file__).parent.parent.parent / "quant/factors/scoring_factors/config"
    
    async def collect(self, params: dict[str, Any], progress: TaskProgress) -> list[Any]:
        from openfinance.datacenter.persistence import persistence
        from openfinance.quant.factors.scoring_factors import ScoringFactorBase
        from sqlalchemy import text
        
        save_to_db = params.get("save_to_db", True)
        progress.details["source"] = "quant_factors"
        progress.details["config_dir"] = str(self._config_dir)
        
        factors = {}
        if self._config_dir.exists():
            for f in load_scoring_factors_from_config(str(self._config_dir)):
                factors[f.factor_id] = f
        
        progress.details["factors_loaded"] = len(factors)
        
        async with persistence.session_maker() as session:
            global_indicators = await self._fetch_global_macro_indicators(session)
            china_indicators = await self._fetch_china_macro_indicators(session)
            market_indicators = await self._fetch_market_indicators(session)
            industry_indicators = await self._fetch_industry_indicators(session)
            
            progress.details["indicators"] = {
                "global_macro": len(global_indicators),
                "china_macro": len(china_indicators),
                "market": len(market_indicators),
                "industry": len(industry_indicators),
            }
            
            global_macro_score = await self._calculate_dimension_score(
                factors, 
                ['factor_global_macro_policy', 'factor_global_macro_economy', 
                 'factor_global_macro_inflation', 'factor_global_macro_risk'],
                global_indicators
            )
            
            china_macro_score = await self._calculate_dimension_score(
                factors,
                ['factor_china_macro_growth', 'factor_china_macro_pmi',
                 'factor_china_macro_monetary', 'factor_china_macro_property'],
                china_indicators
            )
            
            market_score = await self._calculate_dimension_score(
                factors,
                ['factor_market_trend', 'factor_market_breadth',
                 'factor_market_volume', 'factor_market_capital_flow',
                 'factor_market_valuation'],
                market_indicators
            )
            
            industry_score = await self._calculate_dimension_score(
                factors,
                ['factor_industry_rotation', 'factor_industry_tech_trend',
                 'factor_industry_supply_chain', 'factor_industry_cycle',
                 'factor_industry_event'],
                industry_indicators
            )
            
            weights = {'global_macro': 0.25, 'china_macro': 0.30, 'market': 0.25, 'industry': 0.20}
            total_score = round(
                global_macro_score['score'] * weights['global_macro'] +
                china_macro_score['score'] * weights['china_macro'] +
                market_score['score'] * weights['market'] +
                industry_score['score'] * weights['industry'],
                2
            )
            
            result = {
                "date": str(date_type.today()),
                "total": total_score,
                "dimensions": {
                    "global_macro": global_macro_score,
                    "china_macro": china_macro_score,
                    "market": market_score,
                    "industry": industry_score,
                },
                "last_updated": datetime.now().isoformat(),
            }
            
            progress.details["scores"] = {
                "total": total_score,
                "global_macro": global_macro_score['score'],
                "china_macro": china_macro_score['score'],
                "market": market_score['score'],
                "industry": industry_score['score'],
            }
            
            return [result]
    
    async def validate(self, data: list[Any]) -> list[Any]:
        validated = []
        for item in data:
            if isinstance(item, dict) and 'date' in item and 'total' in item:
                validated.append(item)
        return validated
    
    async def save(self, data: list[Any], progress: TaskProgress) -> int:
        from openfinance.datacenter.persistence import persistence
        from sqlalchemy import text
        
        if not data:
            return 0
        
        saved = 0
        async with persistence.session_maker() as session:
            for item in data:
                try:
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
                        "date": item["date"],
                        "global_macro": item["dimensions"]["global_macro"]["score"],
                        "china_macro": item["dimensions"]["china_macro"]["score"],
                        "market": item["dimensions"]["market"]["score"],
                        "industry": item["dimensions"]["industry"]["score"],
                        "stock": 50.0,
                        "total": item["total"],
                    })
                    saved += 1
                except Exception as e:
                    logger.error(f"Failed to save market score: {e}")
            
            await session.commit()
        
        progress.saved_records = saved
        return saved
    
    async def _fetch_global_macro_indicators(self, session) -> dict:
        """Fetch global macro indicator values from database."""
        from sqlalchemy import text
        values = {}
        try:
            result = await session.execute(text("""
                SELECT indicator_code, value FROM openfinance.macro_economic
                WHERE indicator_code IN ('FED_FUNDS_RATE', 'US_GDP_GROWTH', 'US_UNEMPLOYMENT',
                    'US_CPI', 'US_CORE_CPI', 'VIX', 'DOLLAR_INDEX')
                ORDER BY period DESC
            """))
            for row in result.fetchall():
                if row[0] not in values:
                    values[row[0]] = float(row[1]) if row[1] else None
        except Exception as e:
            logger.warning(f"Failed to fetch global macro indicators: {e}")
        return values
    
    async def _fetch_china_macro_indicators(self, session) -> dict:
        """Fetch China macro indicator values from database."""
        from sqlalchemy import text
        values = {}
        try:
            result = await session.execute(text("""
                SELECT indicator_code, value FROM openfinance.macro_economic
                WHERE indicator_code IN ('GDP', 'CPI', 'PPI', 'PMI_MANUFACTURING', 
                    'PMI_NON_MANUFACTURING', 'M2', 'LPR_1Y', 'SOCIAL_FINANCING')
                ORDER BY period DESC
            """))
            for row in result.fetchall():
                if row[0] not in values:
                    values[row[0]] = float(row[1]) if row[1] else None
        except Exception as e:
            logger.warning(f"Failed to fetch China macro indicators: {e}")
        return values
    
    async def _fetch_market_indicators(self, session) -> dict:
        """Fetch market indicator values from database."""
        from sqlalchemy import text
        values = {}
        try:
            result = await session.execute(text("""
                SELECT code, close, ma_5, ma_10, ma_20, ma_60, volume
                FROM openfinance.stock_daily_quote
                WHERE code IN ('000001', '399001', '399006')
                AND trade_date = (SELECT MAX(trade_date) FROM openfinance.stock_daily_quote)
            """))
            quotes = result.fetchall()
            for quote in quotes:
                code, close, ma5, ma10, ma20, ma60, volume = quote
                if ma5 and ma10 and ma20 and ma60:
                    if ma5 > ma10 > ma20 > ma60:
                        values['MA_ALIGNMENT'] = 'bullish'
                    elif ma5 < ma10 < ma20 < ma60:
                        values['MA_ALIGNMENT'] = 'bearish'
                    else:
                        values['MA_ALIGNMENT'] = 'neutral'
                    break
            
            flow_result = await session.execute(text("""
                SELECT SUM(north_net_inflow) FROM openfinance.stock_money_flow
                WHERE trade_date = (SELECT MAX(trade_date) FROM openfinance.stock_money_flow)
            """))
            flow_row = flow_result.fetchone()
            if flow_row and flow_row[0]:
                values['NORTHBOUND_FLOW'] = float(flow_row[0])
        except Exception as e:
            logger.warning(f"Failed to fetch market indicators: {e}")
        return values
    
    async def _fetch_industry_indicators(self, session) -> dict:
        """Fetch industry indicators from database."""
        from sqlalchemy import text
        values = {}
        try:
            result = await session.execute(text("""
                SELECT industry_code, change_pct, amount
                FROM openfinance.industry_quote
                WHERE trade_date = (SELECT MAX(trade_date) FROM openfinance.industry_quote)
                ORDER BY amount DESC LIMIT 10
            """))
            industries = result.fetchall()
            if industries:
                rising = sum(1 for ind in industries if ind[1] and float(ind[1]) > 0)
                values['RISING_SECTOR_RATIO'] = (rising / len(industries)) * 100
                
                total_amount = sum(ind[2] or 0 for ind in industries)
                if total_amount > 0:
                    values['SECTOR_FUND_FLOW'] = total_amount
            
            kg_result = await session.execute(text("""
                SELECT e.entity_type, COUNT(*) as cnt
                FROM openfinance.entities e
                JOIN openfinance.relations r ON e.id = r.source_id OR e.id = r.target_id
                WHERE e.entity_type IN ('Industry', 'Sector', 'Concept')
                GROUP BY e.entity_type
            """))
            for row in kg_result.fetchall():
                if row[0] == 'Industry':
                    values['INNOVATION_INDEX'] = min(100, row[1] * 0.5)
            
            event_result = await session.execute(text("""
                SELECT 
                    SUM(CASE WHEN impact_direction = 'positive' THEN 1 ELSE 0 END) as positive,
                    SUM(CASE WHEN impact_direction = 'negative' THEN 1 ELSE 0 END) as negative
                FROM openfinance.market_events
                WHERE category = 'industry'
                AND event_date >= CURRENT_DATE - INTERVAL '30 days'
            """))
            event_row = event_result.fetchone()
            if event_row:
                positive, negative = event_row
                values['POLICY_EVENTS'] = 50 + (positive or 0) * 5 - (negative or 0) * 5
                values['MARKET_EVENTS'] = 50 + (positive or 0) * 3 - (negative or 0) * 3
        except Exception as e:
            logger.warning(f"Failed to fetch industry indicators: {e}")
        return values
    
    async def _calculate_dimension_score(
        self,
        factors: dict,
        factor_ids: list,
        indicator_values: dict
    ) -> dict:
        """Calculate dimension score from multiple factors."""
        factor_scores = {}
        key_indicators = []
        
        for factor_id in factor_ids:
            factor = factors.get(factor_id)
            if not factor:
                continue
            
            score = factor.calculate_from_indicators(indicator_values)
            if score is not None:
                factor_scores[factor_id] = score
                
                for code, ind_def in factor.get_indicator_definitions().items():
                    if code in indicator_values:
                        key_indicators.append({
                            'name': ind_def.name,
                            'value': indicator_values[code],
                            'factor': factor_id,
                        })
        
        avg_score = sum(factor_scores.values()) / len(factor_scores) if factor_scores else 50.0
        
        return {
            'score': round(avg_score, 2),
            'trend': 'flat',
            'change': 0.0,
            'key_indicators': key_indicators[:5],
            'factors': factor_scores,
        }


@task_executor(
    task_type="market_event_collection",
    name="市场事件采集",
    description="从新闻和公告中提取市场重要事件并保存到数据库",
    category=TaskCategory.ANALYSIS,
    source="eastmoney",
    priority=TaskPriority.HIGH,
    timeout=600.0,
    parameters=[
        TaskParameter(
            name="days_back",
            type="integer",
            default=7,
            description="获取最近N天的新闻",
        ),
        TaskParameter(
            name="importance_threshold",
            type="string",
            default="medium",
            description="重要性阈值: critical, high, medium, low",
        ),
        TaskParameter(
            name="use_ai_analysis",
            type="boolean",
            default=True,
            description="是否使用AI分析事件影响",
        ),
    ],
    output=TaskOutput(
        data_type="market_event",
        table_name="market_events",
        description="市场事件数据",
        fields=["title", "event_date", "category", "importance", "impact_direction"],
    ),
    tags=["analysis", "events", "news"],
)
class MarketEventCollectionExecutor(TaskExecutor[Any]):
    """Executor for market event collection from news."""
    
    def __init__(self):
        pass
    
    async def collect(self, params: dict[str, Any], progress: TaskProgress) -> list[Any]:
        from openfinance.datacenter.persistence import persistence
        from sqlalchemy import text
        import hashlib
        
        days_back = params.get("days_back", 7)
        use_ai = params.get("use_ai_analysis", True)
        
        progress.details["source"] = "news_analysis"
        progress.details["days_back"] = days_back
        
        events = []
        
        async with persistence.session_maker() as session:
            news_result = await session.execute(text("""
                SELECT news_id, title, content, source, published_at, category
                FROM openfinance.news
                WHERE published_at >= CURRENT_DATE - INTERVAL ':days days'
                ORDER BY published_at DESC
                LIMIT 100
            """), {"days": days_back})
            
            news_list = news_result.fetchall()
            progress.total_records = len(news_list)
            progress.details["news_count"] = len(news_list)
            
            for news in news_list:
                news_id, title, content, source, published_at, category = news
                
                importance = self._classify_importance(title, content)
                event_category = self._classify_category(title, content)
                impact_direction = self._predict_impact(title, content)
                
                event = {
                    "event_id": hashlib.md5(f"{news_id}_{title}".encode()).hexdigest()[:16],
                    "title": title,
                    "summary": content[:200] if content else "",
                    "content": content,
                    "event_date": published_at.date() if published_at else date_type.today(),
                    "publish_date": published_at,
                    "category": event_category,
                    "event_type": "news",
                    "importance": importance,
                    "impact_direction": impact_direction,
                    "impact_magnitude": 0.5 if importance in ["critical", "high"] else 0.3,
                    "source_name": source,
                    "entities": [],
                    "ai_analysis": None,
                }
                
                if use_ai:
                    event["ai_analysis"] = await self._ai_analyze_event(title, content)
                
                events.append(event)
        
        progress.details["events_collected"] = len(events)
        return events
    
    def _classify_importance(self, title: str, content: str) -> str:
        """Classify event importance based on keywords."""
        text = f"{title} {content}".lower()
        
        critical_keywords = ["暴跌", "暴涨", "熔断", "崩盘", "危机", "违约", "破产"]
        high_keywords = ["降息", "加息", "降准", "政策", "监管", "处罚", "重组", "并购"]
        medium_keywords = ["业绩", "财报", "分红", "增持", "减持", "回购"]
        
        for kw in critical_keywords:
            if kw in text:
                return "critical"
        
        for kw in high_keywords:
            if kw in text:
                return "high"
        
        for kw in medium_keywords:
            if kw in text:
                return "medium"
        
        return "low"
    
    def _classify_category(self, title: str, content: str) -> str:
        """Classify event category."""
        text = f"{title} {content}".lower()
        
        if any(kw in text for kw in ["央行", "美联储", "利率", "货币", "gdp", "cpi"]):
            return "macro"
        elif any(kw in text for kw in ["板块", "行业", "产业链"]):
            return "industry"
        elif any(kw in text for kw in ["公司", "业绩", "财报", "并购", "重组"]):
            return "company"
        elif any(kw in text for kw in ["政策", "监管", "法规"]):
            return "policy"
        
        return "market"
    
    def _predict_impact(self, title: str, content: str) -> str:
        """Predict impact direction."""
        text = f"{title} {content}".lower()
        
        positive_keywords = ["利好", "增长", "盈利", "突破", "创新高", "上涨", "增持", "回购"]
        negative_keywords = ["利空", "下跌", "亏损", "暴跌", "违约", "风险", "减持", "处罚"]
        
        positive_count = sum(1 for kw in positive_keywords if kw in text)
        negative_count = sum(1 for kw in negative_keywords if kw in text)
        
        if positive_count > negative_count:
            return "positive"
        elif negative_count > positive_count:
            return "negative"
        
        return "neutral"
    
    async def _ai_analyze_event(self, title: str, content: str) -> str:
        """Use AI to analyze event impact."""
        try:
            import os
            from openai import AsyncOpenAI
            
            api_key = os.getenv("DASHSCOPE_API_KEY") or os.getenv("OPENAI_API_KEY")
            base_url = os.getenv("DASHSCOPE_API_URL") or "https://dashscope.aliyuncs.com/compatible-mode/v1"
            model = os.getenv("LLM_MODEL", "qwen-max")
            
            if not api_key:
                return None
            
            client = AsyncOpenAI(api_key=api_key, base_url=base_url)
            
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一位专业的金融分析师。请用1-2句话分析这个事件对市场的影响。"
                    },
                    {
                        "role": "user",
                        "content": f"事件：{title}\n\n内容：{content[:500] if content else ''}"
                    }
                ],
                temperature=0.7,
                max_tokens=200,
            )
            
            return response.choices[0].message.content
        except Exception as e:
            logger.debug(f"AI analysis failed: {e}")
            return None
    
    async def validate(self, data: list[Any]) -> list[Any]:
        validated = []
        for item in data:
            if isinstance(item, dict) and item.get('title') and item.get('event_date'):
                validated.append(item)
        return validated
    
    async def save(self, data: list[Any], progress: TaskProgress) -> int:
        from openfinance.datacenter.persistence import persistence
        from sqlalchemy import text
        
        if not data:
            return 0
        
        saved = 0
        async with persistence.session_maker() as session:
            for event in data:
                try:
                    await session.execute(text("""
                        INSERT INTO openfinance.market_events
                        (title, summary, content, event_date, publish_date, category,
                         event_type, importance, impact_direction, impact_magnitude,
                         source_name, entities, ai_analysis)
                        VALUES
                        (:title, :summary, :content, :event_date, :publish_date, :category,
                         :event_type, :importance, :impact_direction, :impact_magnitude,
                         :source_name, :entities, :ai_analysis)
                        ON CONFLICT DO NOTHING
                    """), {
                        "title": event["title"],
                        "summary": event.get("summary", ""),
                        "content": event.get("content"),
                        "event_date": event["event_date"],
                        "publish_date": event.get("publish_date"),
                        "category": event["category"],
                        "event_type": event.get("event_type", "news"),
                        "importance": event["importance"],
                        "impact_direction": event["impact_direction"],
                        "impact_magnitude": event.get("impact_magnitude", 0.3),
                        "source_name": event.get("source_name", ""),
                        "entities": event.get("entities", []),
                        "ai_analysis": event.get("ai_analysis"),
                    })
                    saved += 1
                except Exception as e:
                    logger.error(f"Failed to save event: {e}")
            
            await session.commit()
        
        progress.saved_records = saved
        return saved


@task_executor(
    task_type="stock_score_calculation",
    name="个股评分计算",
    description="计算个股的多维度评分（财务、技术、情绪等）",
    category=TaskCategory.ANALYSIS,
    source="internal",
    priority=TaskPriority.NORMAL,
    timeout=600.0,
    parameters=[
        TaskParameter(
            name="codes",
            type="array",
            default=None,
            description="股票代码列表，为空则计算全部",
        ),
        TaskParameter(
            name="top_n",
            type="integer",
            default=100,
            description="计算市值前N只股票",
        ),
    ],
    output=TaskOutput(
        data_type="stock_score",
        table_name="stock_score_history",
        description="个股评分历史",
        fields=["code", "date", "total_score", "recommendation"],
    ),
    tags=["analysis", "scoring", "stocks"],
)
class StockScoreCalculationExecutor(TaskExecutor[Any]):
    """Executor for individual stock score calculation."""
    
    async def collect(self, params: dict[str, Any], progress: TaskProgress) -> list[Any]:
        from openfinance.datacenter.persistence import persistence
        from openfinance.api.service.analysis_data_service import get_analysis_data_service
        from sqlalchemy import text
        
        codes = params.get("codes")
        top_n = params.get("top_n", 100)
        
        progress.details["source"] = "quant_analysis"
        
        service = get_analysis_data_service()
        
        if not codes:
            async with persistence.session_maker() as session:
                result = await session.execute(text("""
                    SELECT code FROM openfinance.stock_basic
                    ORDER BY market_cap DESC NULLS LAST
                    LIMIT :limit
                """), {"limit": top_n})
                codes = [row[0] for row in result.fetchall()]
        
        progress.total_records = len(codes)
        progress.details["stocks_count"] = len(codes)
        
        scores = []
        for i, code in enumerate(codes):
            if i % 10 == 0:
                progress.processed_records = i
            
            try:
                financial_data = await service.get_company_financial(code, years=1)
                tech_indicators = await service.get_company_tech_indicators(code)
                
                score_data = self._calculate_stock_score(
                    code, 
                    financial_data, 
                    tech_indicators
                )
                scores.append(score_data)
            except Exception as e:
                logger.debug(f"Failed to calculate score for {code}: {e}")
        
        progress.details["scores_calculated"] = len(scores)
        return scores
    
    def _calculate_stock_score(
        self,
        code: str,
        financial_data: list,
        tech_indicators: dict
    ) -> dict:
        """Calculate stock score from multiple dimensions."""
        financial_score = 50.0
        profit_score = 50.0
        cashflow_score = 50.0
        tech_score = 50.0
        sentiment_score = 50.0
        name = code
        
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
            "date": str(date_type.today()),
            "total_score": round(total_score, 2),
            "financial_score": round(financial_score, 2),
            "profit_score": round(profit_score, 2),
            "cashflow_score": round(cashflow_score, 2),
            "tech_score": round(tech_score, 2),
            "sentiment_score": round(sentiment_score, 2),
            "recommendation": recommendation,
        }
    
    async def validate(self, data: list[Any]) -> list[Any]:
        validated = []
        for item in data:
            if isinstance(item, dict) and item.get('code') and item.get('total_score'):
                validated.append(item)
        return validated
    
    async def save(self, data: list[Any], progress: TaskProgress) -> int:
        from openfinance.datacenter.persistence import persistence
        from sqlalchemy import text
        
        if not data:
            return 0
        
        saved = 0
        async with persistence.session_maker() as session:
            for item in data:
                try:
                    await session.execute(text("""
                        INSERT INTO openfinance.stock_score_history
                        (code, date, total_score, financial_score, profit_score,
                         cashflow_score, tech_score, sentiment_score, recommendation)
                        VALUES
                        (:code, :date, :total_score, :financial_score, :profit_score,
                         :cashflow_score, :tech_score, :sentiment_score, :recommendation)
                        ON CONFLICT (code, date) DO UPDATE SET
                        total_score = EXCLUDED.total_score,
                        financial_score = EXCLUDED.financial_score,
                        profit_score = EXCLUDED.profit_score,
                        cashflow_score = EXCLUDED.cashflow_score,
                        tech_score = EXCLUDED.tech_score,
                        sentiment_score = EXCLUDED.sentiment_score,
                        recommendation = EXCLUDED.recommendation
                    """), {
                        "code": item["code"],
                        "date": item["date"],
                        "total_score": item["total_score"],
                        "financial_score": item["financial_score"],
                        "profit_score": item["profit_score"],
                        "cashflow_score": item["cashflow_score"],
                        "tech_score": item["tech_score"],
                        "sentiment_score": item["sentiment_score"],
                        "recommendation": item["recommendation"],
                    })
                    saved += 1
                except Exception as e:
                    logger.error(f"Failed to save stock score: {e}")
            
            await session.commit()
        
        progress.saved_records = saved
        return saved


@task_executor(
    task_type="financial_calendar_collection",
    name="金融日历数据采集",
    description="采集未来金融日历事件，包括经济指标发布、财报披露等",
    category=TaskCategory.ANALYSIS,
    source="cls",
    priority=TaskPriority.HIGH,
    timeout=600.0,
    parameters=[
        TaskParameter(
            name="days_forward",
            type="integer",
            default=30,
            description="获取未来N天的金融日历事件",
        ),
    ],
    output=TaskOutput(
        data_type="market_event",
        table_name="market_events",
        description="金融日历事件数据",
        fields=["title", "event_date", "category", "importance"],
    ),
    tags=["analysis", "calendar", "events"],
)
class FinancialCalendarCollectionExecutor(TaskExecutor[Any]):
    """Executor for financial calendar event collection from real data sources."""
    
    async def collect(self, params: dict[str, Any], progress: TaskProgress) -> list[Any]:
        from datetime import timedelta
        import hashlib
        import aiohttp
        import time
        
        days_forward = params.get("days_forward", 30)
        
        progress.details["source"] = "cls_jinshi_calendar"
        progress.details["days_forward"] = days_forward
        
        events = []
        today = date_type.today()
        
        cls_events = await self._fetch_cls_events(today, days_forward, progress)
        events.extend(cls_events)
        
        jinshi_events = await self._fetch_jinshi_events(today, days_forward, progress)
        events.extend(jinshi_events)
        
        for event in events:
            event_id = hashlib.md5(f"{event['title']}_{event['event_date']}".encode()).hexdigest()[:16]
            event["event_id"] = event_id
            event["publish_date"] = datetime.combine(event["event_date"], datetime.min.time())
            event["summary"] = event["title"]
            event["content"] = None
            event["event_type"] = "calendar"
            event["entities"] = []
            event["ai_analysis"] = None
        
        progress.total_records = len(events)
        progress.details["events_collected"] = len(events)
        
        return events
    
    async def _fetch_cls_events(
        self, 
        today: date_type, 
        days_forward: int,
        progress: TaskProgress
    ) -> list[dict]:
        """Fetch events from CLS (财联社) API."""
        import aiohttp
        import time
        import hashlib as hl
        
        events = []
        current_time = int(time.time())
        
        url = "https://www.cls.cn/nodeapi/telegraphList"
        
        text = f"app=CailianpressWeb&category=&lastTime={current_time}&last_time={current_time}&os=web&refresh_type=1&rn=100&sv=7.7.5"
        sha1 = hl.sha1(text.encode()).hexdigest()
        code = hl.md5(sha1.encode()).hexdigest()
        
        params = {
            "app": "CailianpressWeb",
            "category": "",
            "lastTime": current_time,
            "last_time": current_time,
            "os": "web",
            "refresh_type": "1",
            "rn": "100",
            "sv": "7.7.5",
            "sign": code,
        }
        
        headers = {
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://www.cls.cn/telegraph",
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, headers=headers, timeout=10) as response:
                    data = await response.json()
                
                if data.get("data") and data["data"].get("roll_data"):
                    for item in data["data"]["roll_data"]:
                        try:
                            ctime = item.get("ctime", "")
                            if isinstance(ctime, int):
                                published_at = datetime.fromtimestamp(ctime)
                            elif isinstance(ctime, str) and ctime:
                                published_at = datetime.strptime(ctime, "%Y-%m-%d %H:%M:%S")
                            else:
                                continue
                            
                            title = item.get("title", "") or item.get("content", "")[:100]
                            content = item.get("content", "")
                            
                            classification = self._classify_event(title, content)
                            
                            event_date = published_at.date()
                            if event_date < today or event_date > today + timedelta(days=days_forward):
                                continue
                            
                            events.append({
                                "title": title,
                                "event_date": event_date,
                                "category": classification['category'],
                                "importance": classification['importance'],
                                "impact_direction": classification['impact_direction'],
                                "impact_magnitude": 0.5 if classification['importance'] in ['critical', 'high'] else 0.3,
                                "source_name": "财联社",
                            })
                        except Exception as e:
                            logger.debug(f"Failed to parse CLS event: {e}")
                
                progress.details["cls_events"] = len(events)
                        
        except Exception as e:
            logger.warning(f"Failed to fetch CLS events: {e}")
            progress.details["cls_error"] = str(e)
        
        return events
    
    async def _fetch_jinshi_events(
        self,
        today: date_type,
        days_forward: int,
        progress: TaskProgress
    ) -> list[dict]:
        """Fetch events from Jinshi (金十数据) API."""
        import aiohttp
        import time
        
        events = []
        
        url = "https://flash-api.jin10.com/get_flash_list"
        
        params = {
            "channel": "-8200",
            "vip": "1",
            "t": str(int(time.time() * 1000)),
            "max_time": (today + timedelta(days=1)).strftime("%Y%m%d"),
        }
        
        headers = {
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://www.jin10.com/",
            "x-app-id": "bVBF4FyRTn5NJF5n",
            "x-version": "1.0.0",
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, headers=headers, timeout=10) as response:
                    data = await response.json()
                
                if data.get("data"):
                    for item in data["data"][:100]:
                        try:
                            content = item.get("data", {}).get("content", "")
                            if not content:
                                content = item.get("data", {}).get("pic", "")
                            
                            title = content[:100] if content else ""
                            if not title:
                                continue
                            
                            classification = self._classify_event(title, content)
                            
                            event_time = item.get("time", 0)
                            if event_time:
                                event_date = datetime.fromtimestamp(event_time).date()
                            else:
                                continue
                            
                            if event_date < today or event_date > today + timedelta(days=days_forward):
                                continue
                            
                            events.append({
                                "title": title,
                                "event_date": event_date,
                                "category": classification['category'],
                                "importance": classification['importance'],
                                "impact_direction": classification['impact_direction'],
                                "impact_magnitude": 0.5 if classification['importance'] in ['critical', 'high'] else 0.3,
                                "source_name": "金十数据",
                            })
                        except Exception as e:
                            logger.debug(f"Failed to parse Jinshi event: {e}")
                
                progress.details["jinshi_events"] = len(events)
                        
        except Exception as e:
            logger.warning(f"Failed to fetch Jinshi events: {e}")
            progress.details["jinshi_error"] = str(e)
        
        return events
    
    def _classify_event(self, title: str, content: str) -> dict:
        """Classify event by category, importance, and impact direction."""
        text = f"{title} {content}".lower()
        
        category = 'market'
        if any(kw in text for kw in ["央行", "美联储", "利率", "货币", "gdp", "cpi", "pmi", "m2", "社融"]):
            category = 'macro'
        elif any(kw in text for kw in ["板块", "行业", "产业链"]):
            category = 'industry'
        elif any(kw in text for kw in ["公司", "业绩", "财报", "并购", "重组"]):
            category = 'company'
        elif any(kw in text for kw in ["政策", "监管", "法规"]):
            category = 'policy'
        
        importance = 'low'
        if any(kw in text for kw in ["暴跌", "暴涨", "熔断", "崩盘", "危机", "违约", "破产"]):
            importance = 'critical'
        elif any(kw in text for kw in ["降息", "加息", "降准", "政策", "监管", "处罚", "重组", "并购"]):
            importance = 'high'
        elif any(kw in text for kw in ["业绩", "财报", "分红", "增持", "减持", "回购"]):
            importance = 'medium'
        
        impact_direction = 'neutral'
        positive_count = sum(1 for kw in ["利好", "增长", "盈利", "突破", "创新高", "上涨", "增持", "回购"] if kw in text)
        negative_count = sum(1 for kw in ["利空", "下跌", "亏损", "暴跌", "违约", "风险", "减持", "处罚"] if kw in text)
        
        if positive_count > negative_count:
            impact_direction = 'positive'
        elif negative_count > positive_count:
            impact_direction = 'negative'
        
        return {
            'category': category,
            'importance': importance,
            'impact_direction': impact_direction,
        }
    
    async def validate(self, data: list[Any]) -> list[Any]:
        validated = []
        for item in data:
            if isinstance(item, dict) and item.get('title') and item.get('event_date'):
                validated.append(item)
        return validated
    
    async def save(self, data: list[Any], progress: TaskProgress) -> int:
        from openfinance.datacenter.persistence import persistence
        from sqlalchemy import text
        
        if not data:
            return 0
        
        saved = 0
        async with persistence.session_maker() as session:
            for event in data:
                try:
                    await session.execute(text("""
                        INSERT INTO openfinance.market_events
                        (title, summary, content, event_date, publish_date, category,
                         event_type, importance, impact_direction, impact_magnitude,
                         source_name, entities, ai_analysis)
                        VALUES
                        (:title, :summary, :content, :event_date, :publish_date, :category,
                         :event_type, :importance, :impact_direction, :impact_magnitude,
                         :source_name, '[]'::jsonb, :ai_analysis)
                        ON CONFLICT DO NOTHING
                    """), {
                        "title": event["title"],
                        "summary": event.get("summary", ""),
                        "content": event.get("content"),
                        "event_date": event["event_date"],
                        "publish_date": event.get("publish_date"),
                        "category": event["category"],
                        "event_type": event.get("event_type", "calendar"),
                        "importance": event["importance"],
                        "impact_direction": event["impact_direction"],
                        "impact_magnitude": event.get("impact_magnitude", 0.3),
                        "source_name": event.get("source_name", "金融日历"),
                        "ai_analysis": event.get("ai_analysis"),
                    })
                    saved += 1
                except Exception as e:
                    logger.error(f"Failed to save calendar event: {e}")
            
            await session.commit()
        
        progress.saved_records = saved
        return saved


def register_analysis_executors():
    """Register all analysis executors."""
    from .registry import TaskRegistry
    
    TaskRegistry.register_class(MarketScoreCalculationExecutor)
    TaskRegistry.register_class(MarketEventCollectionExecutor)
    TaskRegistry.register_class(StockScoreCalculationExecutor)
    TaskRegistry.register_class(FinancialCalendarCollectionExecutor)
    
    logger.info("Registered 4 analysis executors")
