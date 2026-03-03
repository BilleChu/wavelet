"""
Implemented data collectors based on qstock functions.

This module provides concrete implementations of collectors that wrap
the existing qstock data acquisition functions into the standard
collector framework.
"""

from .derivative_collectors import (
    FutureDataCollector,
    ImpliedVolatilityCollector,
    OptionDataCollector,
    OptionGreeksCollector,
)
from .fundamental_collectors import (
    BalanceSheetCollector,
    DividendDataCollector,
    FinancialIndicatorCollector,
    IncomeStatementCollector,
    InstitutionalRatingCollector,
    MainBusinessCollector,
    StockValuationCollector,
    Top10HolderCollector,
)
from .industry_collectors import (
    ConceptDataCollector,
    ConceptMemberCollector,
    IndustryDataCollector,
    IndustryMemberCollector,
    EastMoneyIndustryListCollector,
    EastMoneyIndustryMemberCollector,
    EastMoneyStockIndustryCollector,
)
from .macro_collectors import (
    CPICollector,
    GDPCollector,
    InterbankRateCollector,
    LPRCollector,
    MoneySupplyCollector,
    PMICollector,
    PPICollector,
)
from .market_collectors import (
    IndexMemberCollector,
    IntradayDataCollector,
    KLineCollector,
    MarketRealtimeCollector,
    StockBillboardCollector,
    StockRealtimeCollector,
)
from .money_flow_collectors import (
    DailyMoneyFlowCollector,
    IntradayMoneyFlowCollector,
    NorthMoneyCollector,
    SectorMoneyFlowCollector,
)
from .news_collectors import (
    CCTVNewsCollector,
    CLSNewsCollector,
    JinshiNewsCollector,
)
from .financial_statement_collectors import (
    BatchBalanceSheetCollector,
    BatchCashFlowStatementCollector,
    BatchIncomeStatementCollector,
    BatchPerformanceForecastCollector,
    BatchPerformanceReportCollector,
)
from .research_report_collectors import (
    ResearchReportCollector,
    ResearchReportDetailCollector,
)

__all__ = [
    "MarketRealtimeCollector",
    "StockRealtimeCollector",
    "KLineCollector",
    "IntradayDataCollector",
    "StockBillboardCollector",
    "IndexMemberCollector",
    "InstitutionalRatingCollector",
    "Top10HolderCollector",
    "MainBusinessCollector",
    "FinancialIndicatorCollector",
    "StockValuationCollector",
    "DividendDataCollector",
    "IntradayMoneyFlowCollector",
    "DailyMoneyFlowCollector",
    "NorthMoneyCollector",
    "SectorMoneyFlowCollector",
    "LPRCollector",
    "MoneySupplyCollector",
    "CPICollector",
    "GDPCollector",
    "PPICollector",
    "PMICollector",
    "InterbankRateCollector",
    "JinshiNewsCollector",
    "CLSNewsCollector",
    "CCTVNewsCollector",
    "BalanceSheetCollector",
    "IncomeStatementCollector",
    "BatchBalanceSheetCollector",
    "BatchIncomeStatementCollector",
    "BatchCashFlowStatementCollector",
    "BatchPerformanceReportCollector",
    "BatchPerformanceForecastCollector",
    "ResearchReportCollector",
    "ResearchReportDetailCollector",
]
