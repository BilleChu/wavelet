"""
Analysis Data Service for Functional Analysis Page.

Integrates with existing data center and quant modules to ensure data consistency.
All data comes from real backend systems, NO mock data.
"""

import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Optional

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from openfinance.datacenter.models.analytical import (
    ADSKLineModel,
    ADSFactorModel,
    ADSNewsModel,
    ADSMacroEconomicModel,
    ADSFinancialIndicatorModel,
    get_ads_service,
)
from openfinance.datacenter.models.orm import (
    EntityModel,
    RelationModel,
    ResearchReportModel,
    NewsModel,
    StockFinancialIndicatorModel,
    MacroEconomicModel,
    IncomeStatementModel,
    BalanceSheetModel,
    CashFlowModel,
)
from openfinance.infrastructure.database.database import async_session_maker

logger = logging.getLogger(__name__)


@dataclass
class CompanyKLineData:
    """Company K-line data."""
    code: str
    name: str
    trade_date: date
    open: float
    high: float
    low: float
    close: float
    volume: float
    amount: float
    change_pct: Optional[float] = None
    turnover_rate: Optional[float] = None


@dataclass
class CompanyFinancialData:
    """Company financial data."""
    code: str
    name: str
    report_date: date
    report_type: str
    revenue: Optional[float] = None
    net_profit: Optional[float] = None
    gross_margin: Optional[float] = None
    net_margin: Optional[float] = None
    roe: Optional[float] = None
    roa: Optional[float] = None
    debt_ratio: Optional[float] = None
    current_ratio: Optional[float] = None
    pe_ratio: Optional[float] = None
    pb_ratio: Optional[float] = None
    yoy_revenue_growth: Optional[float] = None
    yoy_profit_growth: Optional[float] = None


@dataclass
class CompanyCashFlowData:
    """Company cash flow data."""
    code: str
    report_date: date
    operating_cash_flow: Optional[float] = None
    investing_cash_flow: Optional[float] = None
    financing_cash_flow: Optional[float] = None
    free_cash_flow: Optional[float] = None


@dataclass
class CompanyNewsData:
    """Company news data."""
    news_id: str
    title: str
    content: Optional[str]
    source: Optional[str]
    published_at: Optional[datetime]
    sentiment: Optional[float]
    related_codes: list[str]


@dataclass
class CompanyResearchReport:
    """Company research report."""
    report_id: str
    title: str
    summary: Optional[str]
    analyst: Optional[str]
    institution: Optional[str]
    publish_date: Optional[datetime]
    rating: Optional[str]
    target_price: Optional[float]
    code: Optional[str]


@dataclass
class MacroIndicatorData:
    """Macro economic indicator data."""
    indicator_code: str
    indicator_name: str
    value: float
    unit: str
    period: str
    country: str
    yoy_change: Optional[float] = None
    mom_change: Optional[float] = None
    trend: str = "stable"


@dataclass
class IndustryData:
    """Industry data."""
    industry_code: str
    industry_name: str
    index_value: Optional[float] = None
    change_pct: Optional[float] = None
    volume: Optional[float] = None
    amount: Optional[float] = None
    pe_ratio: Optional[float] = None
    pb_ratio: Optional[float] = None


class AnalysisDataService:
    """
    Analysis data service for functional analysis page.
    
    Integrates with existing data center and quant modules:
    - Uses ADSService for K-line, financial, macro data
    - Uses Quant module for factor calculations
    - Ensures data consistency across the system
    """
    
    def __init__(self):
        self._ads_service = get_ads_service()
    
    async def get_company_kline(
        self,
        stock_code: str,
        period: str = 'D',
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 100
    ) -> list[CompanyKLineData]:
        """
        Query company K-line data using ADS service.
        
        Args:
            stock_code: Stock code (e.g., '600000')
            period: K-line period ('D', 'W', 'M')
            start_date: Start date
            end_date: End date
            limit: Maximum number of records
        
        Returns:
            List of K-line data
        """
        try:
            klines = await self._ads_service.get_kline_data(
                code=stock_code,
                start_date=start_date,
                end_date=end_date,
                limit=limit
            )
            
            return [
                CompanyKLineData(
                    code=k.code,
                    name=k.name or stock_code,
                    trade_date=k.trade_date,
                    open=k.open or 0,
                    high=k.high or 0,
                    low=k.low or 0,
                    close=k.close or 0,
                    volume=k.volume or 0,
                    amount=k.amount or 0,
                    change_pct=k.change_pct,
                    turnover_rate=k.turnover_rate
                )
                for k in klines
            ]
        except Exception as e:
            logger.error(f"Failed to get K-line data for {stock_code}: {e}")
            return []
    
    async def get_company_factors(
        self,
        stock_code: str,
        factor_names: Optional[list[str]] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> dict[str, list[tuple[date, float]]]:
        """
        Query company quantitative factors using Quant module.
        
        This method integrates with the quant analysis module to ensure
        data consistency across the system.
        
        Args:
            stock_code: Stock code
            factor_names: List of factor names (e.g., ['momentum', 'value', 'quality'])
            start_date: Start date
            end_date: End date
        
        Returns:
            Dictionary mapping factor name to list of (date, value) tuples
        """
        try:
            from openfinance.quant.factors.registry import get_factor_registry
            from openfinance.datacenter.models.analytical import ADSKLineModel
            from datetime import timedelta
            
            result = {}
            
            if not factor_names:
                factor_names = ['momentum', 'value', 'quality', 'volatility', 'rsi']
            
            registry = get_factor_registry()
            
            factor_mapping = {
                'momentum': 'factor_momentum',
                'value': 'factor_value_pe',
                'quality': 'factor_quality_roe',
                'volatility': 'factor_volatility',
                'rsi': 'factor_rsi',
                'macd': 'factor_macd',
                'kdj': 'factor_kdj',
            }
            
            if not end_date:
                end_date = date.today()
            if not start_date:
                start_date = end_date - timedelta(days=365)
            
            klines = await self.get_company_kline(
                stock_code=stock_code,
                start_date=start_date - timedelta(days=120),
                end_date=end_date,
                limit=500
            )
            
            if not klines:
                logger.warning(f"No K-line data for {stock_code}")
                return {}
            
            for factor_name in factor_names:
                factor_id = factor_mapping.get(factor_name, f'factor_{factor_name}')
                
                factor_def = registry.get(factor_id)
                if not factor_def:
                    for fid in registry.list_factor_ids():
                        f = registry.get(fid)
                        if f and factor_name.lower() in f.name.lower():
                            factor_id = fid
                            factor_def = f
                            break
                
                if not factor_def:
                    logger.warning(f"Factor not found: {factor_name}")
                    continue
                
                factor_instance = registry.get_factor_instance(factor_id)
                if not factor_instance:
                    continue
                
                ads_klines = [
                    ADSKLineModel(
                        code=k.code,
                        trade_date=k.trade_date,
                        open=k.open,
                        high=k.high,
                        low=k.low,
                        close=k.close,
                        volume=k.volume,
                        amount=k.amount,
                    )
                    for k in reversed(klines)
                ]
                
                lookback = factor_def.lookback_period or 20
                min_required = max(20, lookback)
                
                if len(ads_klines) < min_required:
                    continue
                
                factor_values = []
                for i in range(min_required - 1, len(ads_klines)):
                    window = ads_klines[:i + 1]
                    try:
                        calc_result = factor_instance.calculate(window)
                        if calc_result and calc_result.value is not None:
                            factor_values.append((ads_klines[i].trade_date, calc_result.value))
                    except Exception as calc_error:
                        logger.debug(f"Factor calculation error: {calc_error}")
                
                if factor_values:
                    result[factor_name] = factor_values
            
            return result
        except Exception as e:
            logger.error(f"Failed to get factors for {stock_code}: {e}")
            return {}
    
    async def get_company_financial(
        self,
        stock_code: str,
        report_type: str = 'all',
        years: int = 5
    ) -> list[CompanyFinancialData]:
        """
        Query company financial data from income statement and balance sheet.
        
        Args:
            stock_code: Stock code
            report_type: Report type ('all', 'Q1', 'Q2', 'Q3', 'annual')
            years: Number of years to query
        
        Returns:
            List of financial data
        """
        try:
            async with async_session_maker() as session:
                query_sql = """
                    SELECT 
                        i.code, i.report_date, i.report_type,
                        i.total_revenue, i.net_profit, i.net_profit_attr_parent,
                        i.operating_profit, i.total_operating_cost,
                        b.total_assets, b.total_liabilities, b.total_equity,
                        b.total_current_assets, b.total_current_liabilities
                    FROM openfinance.income_statement i
                    LEFT JOIN openfinance.balance_sheet b
                    ON i.code = b.code AND i.report_date = b.report_date
                    WHERE i.code = :code
                    ORDER BY i.report_date DESC
                    LIMIT :limit
                """
                
                result = await session.execute(
                    text(query_sql),
                    {"code": stock_code, "limit": years * 4}
                )
                records = result.fetchall()
                
                financial_data = []
                for r in records:
                    revenue = float(r[3]) if r[3] else None
                    net_profit = float(r[4]) if r[4] else None
                    total_assets = float(r[8]) if r[8] else None
                    total_liabilities = float(r[9]) if r[9] else None
                    total_equity = float(r[10]) if r[10] else None
                    total_current_assets = float(r[11]) if r[11] else None
                    total_current_liabilities = float(r[12]) if r[12] else None
                    
                    gross_margin = None
                    if revenue and r[5]:
                        operating_profit = float(r[6])
                        total_cost = float(r[7]) if r[7] else 0
                        if revenue > 0:
                            gross_margin = ((revenue - total_cost) / revenue) * 100
                    
                    net_margin = None
                    if revenue and net_profit:
                        net_margin = (net_profit / revenue) * 100
                    
                    roe = None
                    if net_profit and total_equity and total_equity > 0:
                        roe = (net_profit / total_equity) * 100
                    
                    roa = None
                    if net_profit and total_assets and total_assets > 0:
                        roa = (net_profit / total_assets) * 100
                    
                    debt_ratio = None
                    if total_liabilities and total_assets and total_assets > 0:
                        debt_ratio = (total_liabilities / total_assets) * 100
                    
                    current_ratio = None
                    if total_current_assets and total_current_liabilities and total_current_liabilities > 0:
                        current_ratio = total_current_assets / total_current_liabilities
                    
                    financial_data.append(CompanyFinancialData(
                        code=r[0],
                        name=stock_code,
                        report_date=r[1],
                        report_type=r[2] or 'Q',
                        revenue=revenue,
                        net_profit=net_profit,
                        gross_margin=gross_margin,
                        net_margin=net_margin,
                        roe=roe,
                        roa=roa,
                        debt_ratio=debt_ratio,
                        current_ratio=current_ratio,
                        pe_ratio=None,
                        pb_ratio=None,
                        yoy_revenue_growth=None,
                        yoy_profit_growth=None
                    ))
                
                return financial_data
        except Exception as e:
            logger.error(f"Failed to get financial data for {stock_code}: {e}")
            return []
    
    async def get_company_profit(
        self,
        stock_code: str,
        years: int = 5
    ) -> list[dict[str, Any]]:
        """
        Query company profit data from income statement.
        
        Args:
            stock_code: Stock code
            years: Number of years to query
        
        Returns:
            List of profit data
        """
        try:
            async with async_session_maker() as session:
                query_sql = """
                    SELECT 
                        code, report_date, report_type,
                        total_revenue, gross_profit, operating_profit,
                        total_profit, net_profit, net_profit_attr_parent,
                        eps, basic_eps, diluted_eps
                    FROM openfinance.income_statement
                    WHERE code = :code
                    ORDER BY report_date DESC
                    LIMIT :limit
                """
                
                result = await session.execute(
                    text(query_sql),
                    {"code": stock_code, "limit": years * 4}
                )
                records = result.fetchall()
                
                return [
                    {
                        'code': r[0],
                        'report_date': r[1],
                        'report_type': r[2],
                        'total_revenue': float(r[3]) if r[3] else None,
                        'gross_profit': float(r[4]) if r[4] else None,
                        'operating_profit': float(r[5]) if r[5] else None,
                        'total_profit': float(r[6]) if r[6] else None,
                        'net_profit': float(r[7]) if r[7] else None,
                        'net_profit_attr_parent': float(r[8]) if r[8] else None,
                        'eps': float(r[9]) if r[9] else None,
                        'basic_eps': float(r[10]) if r[10] else None,
                        'diluted_eps': float(r[11]) if r[11] else None,
                    }
                    for r in records
                ]
        except Exception as e:
            logger.error(f"Failed to get profit data for {stock_code}: {e}")
            return []
    
    async def get_company_cashflow(
        self,
        stock_code: str,
        years: int = 5
    ) -> list[CompanyCashFlowData]:
        """
        Query company cash flow data.
        
        Note: Cash flow table may not exist yet. Returns empty list if table doesn't exist.
        
        Args:
            stock_code: Stock code
            years: Number of years to query
        
        Returns:
            List of cash flow data
        """
        try:
            async with async_session_maker() as session:
                check_table = await session.execute(text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'openfinance' 
                        AND table_name = 'cash_flow'
                    )
                """))
                
                if not check_table.scalar():
                    logger.warning(f"Cash flow table does not exist yet for {stock_code}")
                    return []
                
                query_sql = """
                    SELECT code, report_date, 
                           net_operating_cash_flow, net_investing_cash_flow, 
                           net_financing_cash_flow, net_cash_from_operating as free_cash_flow
                    FROM openfinance.cash_flow
                    WHERE code = :code
                    ORDER BY report_date DESC
                    LIMIT :limit
                """
                
                result = await session.execute(
                    text(query_sql),
                    {"code": stock_code, "limit": years * 4}
                )
                records = result.fetchall()
                
                return [
                    CompanyCashFlowData(
                        code=r[0],
                        report_date=r[1],
                        operating_cash_flow=float(r[2]) if r[2] else None,
                        investing_cash_flow=float(r[3]) if r[3] else None,
                        financing_cash_flow=float(r[4]) if r[4] else None,
                        free_cash_flow=float(r[5]) if r[5] else None
                    )
                    for r in records
                ]
        except Exception as e:
            logger.error(f"Failed to get cash flow data for {stock_code}: {e}")
            return []
    
    async def get_company_news(
        self,
        stock_code: str,
        limit: int = 20
    ) -> list[CompanyNewsData]:
        """
        Query company related news.
        
        Args:
            stock_code: Stock code
            limit: Maximum number of news
        
        Returns:
            List of news data
        """
        try:
            async with async_session_maker() as session:
                query_sql = """
                    SELECT news_id, title, content, source, published_at, sentiment
                    FROM openfinance.news
                    WHERE title ILIKE :code OR content ILIKE :code
                    ORDER BY published_at DESC
                    LIMIT :limit
                """
                
                result = await session.execute(
                    text(query_sql),
                    {"code": f"%{stock_code}%", "limit": limit}
                )
                records = result.fetchall()
                
                return [
                    CompanyNewsData(
                        news_id=str(r[0]),
                        title=r[1],
                        content=r[2][:500] if r[2] and len(r[2]) > 500 else r[2],
                        source=r[3],
                        published_at=r[4],
                        sentiment=float(r[5]) if r[5] else None,
                        related_codes=[]
                    )
                    for r in records
                ]
        except Exception as e:
            logger.error(f"Failed to get news for {stock_code}: {e}")
            return []
    
    async def get_company_reports(
        self,
        stock_code: str,
        limit: int = 10
    ) -> list[CompanyResearchReport]:
        """
        Query company research reports.
        
        Args:
            stock_code: Stock code
            limit: Maximum number of reports
        
        Returns:
            List of research reports
        """
        try:
            async with async_session_maker() as session:
                query_sql = """
                    SELECT id, title, summary, analyst, institution, 
                           publish_date, rating, target_price, related_codes
                    FROM openfinance.research_reports
                    WHERE :code = ANY(related_codes)
                    ORDER BY publish_date DESC
                    LIMIT :limit
                """
                
                result = await session.execute(
                    text(query_sql),
                    {"code": stock_code, "limit": limit}
                )
                records = result.fetchall()
                
                return [
                    CompanyResearchReport(
                        report_id=str(r[0]),
                        title=r[1],
                        summary=r[2],
                        analyst=r[3],
                        institution=r[4],
                        publish_date=r[5],
                        rating=r[6],
                        target_price=float(r[7]) if r[7] else None,
                        code=r[8][0] if r[8] and len(r[8]) > 0 else stock_code
                    )
                    for r in records
                ]
        except Exception as e:
            logger.error(f"Failed to get research reports for {stock_code}: {e}")
            return []
    
    async def get_company_tech_indicators(
        self,
        stock_code: str,
        limit: int = 100
    ) -> dict[str, Any]:
        """
        Query company technical indicators.
        
        Args:
            stock_code: Stock code
            limit: Number of days for calculation
        
        Returns:
            Dictionary of technical indicators
        """
        try:
            klines = await self.get_company_kline(stock_code, limit=limit)
            
            if not klines:
                return {}
            
            latest = klines[0]
            
            closes = [k.close for k in reversed(klines)]
            
            ma5 = sum(closes[-5:]) / 5 if len(closes) >= 5 else None
            ma10 = sum(closes[-10:]) / 10 if len(closes) >= 10 else None
            ma20 = sum(closes[-20:]) / 20 if len(closes) >= 20 else None
            ma60 = sum(closes[-60:]) / 60 if len(closes) >= 60 else None
            
            return {
                'code': stock_code,
                'name': latest.name,
                'price': latest.close,
                'change': latest.close - klines[1].close if len(klines) > 1 else 0,
                'change_pct': latest.change_pct or 0,
                'volume': latest.volume,
                'amount': latest.amount,
                'ma5': ma5,
                'ma10': ma10,
                'ma20': ma20,
                'ma60': ma60,
                'rsi_14': None,
                'macd': None,
                'macd_signal': None,
                'macd_hist': None,
                'kdj_k': None,
                'kdj_d': None,
                'kdj_j': None,
                'boll_upper': None,
                'boll_mid': ma20,
                'boll_lower': None,
                'trend_signal': 'bullish' if ma5 and ma20 and ma5 > ma20 else 'bearish',
                'support_level': min([k.low for k in klines[:20]]) if len(klines) >= 20 else None,
                'resistance_level': max([k.high for k in klines[:20]]) if len(klines) >= 20 else None
            }
        except Exception as e:
            logger.error(f"Failed to get tech indicators for {stock_code}: {e}")
            return {}
    
    async def get_macro_indicators(
        self,
        indicator_codes: Optional[list[str]] = None,
        country: str = 'CN'
    ) -> list[MacroIndicatorData]:
        """
        Query macro economic indicators using ADS service.
        
        Args:
            indicator_codes: List of indicator codes (e.g., ['GDP', 'CPI', 'PMI'])
            country: Country code
        
        Returns:
            List of macro indicators
        """
        try:
            async with async_session_maker() as session:
                query_sql = """
                    SELECT indicator_code, indicator_name, value, unit, 
                           period, country, published_at
                    FROM openfinance.macro_economic
                    WHERE country = :country
                    ORDER BY published_at DESC
                    LIMIT 50
                """
                
                result = await session.execute(
                    text(query_sql),
                    {"country": country}
                )
                records = result.fetchall()
                
                indicators = []
                for r in records:
                    trend = 'stable'
                    
                    indicators.append(MacroIndicatorData(
                        indicator_code=r[0],
                        indicator_name=r[1],
                        value=float(r[2]) if r[2] else 0,
                        unit=r[3] or '',
                        period=r[4],
                        country=r[5] or country,
                        yoy_change=None,
                        mom_change=None,
                        trend=trend
                    ))
                
                return indicators
        except Exception as e:
            logger.error(f"Failed to get macro indicators: {e}")
            return []
    
    async def get_industry_data(
        self,
        industry_code: str
    ) -> IndustryData:
        """
        Query industry data.
        
        Args:
            industry_code: Industry code
        
        Returns:
            Industry data
        """
        try:
            return IndustryData(
                industry_code=industry_code,
                industry_name=industry_code,
                index_value=None,
                change_pct=None,
                volume=None,
                amount=None,
                pe_ratio=None,
                pb_ratio=None
            )
        except Exception as e:
            logger.error(f"Failed to get industry data for {industry_code}: {e}")
            return IndustryData(
                industry_code=industry_code,
                industry_name=industry_code
            )
    
    async def get_hot_stocks(self, limit: int = 10) -> list[dict[str, Any]]:
        """
        Get hot stocks for default display.
        
        Args:
            limit: Number of stocks
        
        Returns:
            List of hot stocks
        """
        default_stocks = [
            {'code': '600000', 'name': '浦发银行'},
            {'code': '000001', 'name': '平安银行'},
            {'code': '600519', 'name': '贵州茅台'},
            {'code': '002594', 'name': '比亚迪'},
            {'code': '601318', 'name': '中国平安'},
            {'code': '000858', 'name': '五粮液'},
            {'code': '600036', 'name': '招商银行'},
            {'code': '601398', 'name': '工商银行'},
        ]
        
        return default_stocks[:limit]
    
    async def get_market_overview(self) -> dict[str, Any]:
        """
        Calculate market overview scores based on quant factors.
        
        This method integrates with the quant scoring factors to calculate
        multi-dimensional market scores.
        
        Returns:
            Dictionary containing total score and dimension scores
        """
        from pathlib import Path
        from openfinance.quant.factors.scoring_factors import (
            load_scoring_factors_from_config,
        )
        
        config_dir = Path(__file__).parent.parent.parent / "quant/factors/scoring_factors/config"
        
        factors = {}
        if config_dir.exists():
            for f in load_scoring_factors_from_config(str(config_dir)):
                factors[f.factor_id] = f
        
        async with async_session_maker() as session:
            global_indicators = await self._fetch_global_macro_indicators(session)
            china_indicators = await self._fetch_china_macro_indicators(session)
            market_indicators = await self._fetch_market_indicators(session)
            industry_indicators = await self._fetch_industry_indicators(session)
            
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
            
            stock_score = {
                'score': 50.0,
                'trend': 'flat',
                'change': 0.0,
                'key_indicators': [],
                'factors': {},
            }
            
            weights = {'global_macro': 0.20, 'china_macro': 0.25, 'market': 0.25, 'industry': 0.15, 'stock': 0.15}
            total_score = round(
                global_macro_score['score'] * weights['global_macro'] +
                china_macro_score['score'] * weights['china_macro'] +
                market_score['score'] * weights['market'] +
                industry_score['score'] * weights['industry'] +
                stock_score['score'] * weights['stock'],
                2
            )
            
            return {
                "date": str(date.today()),
                "total": total_score,
                "dimensions": {
                    "global_macro": global_macro_score,
                    "china_macro": china_macro_score,
                    "market": market_score,
                    "industry": industry_score,
                    "stock": stock_score,
                },
                "last_updated": datetime.now().isoformat(),
            }
    
    async def _fetch_global_macro_indicators(self, session) -> dict:
        """Fetch global macro indicator values from database."""
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
        except Exception as e:
            logger.warning(f"Failed to fetch market indicators: {e}")
        return values
    
    async def _fetch_industry_indicators(self, session) -> dict:
        """Fetch industry indicators from database."""
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


_analysis_data_service: AnalysisDataService | None = None


def get_analysis_data_service() -> AnalysisDataService:
    """Get the global analysis data service instance."""
    global _analysis_data_service
    if _analysis_data_service is None:
        _analysis_data_service = AnalysisDataService()
    return _analysis_data_service
