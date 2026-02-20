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
    FinancialIndicatorCollector,
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
from .report_collectors import (
    BalanceSheetCollector,
    CashFlowStatementCollector,
    IncomeStatementCollector,
    PerformanceForecastCollector,
    PerformanceReportCollector,
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
    "CashFlowStatementCollector",
    "PerformanceReportCollector",
    "PerformanceForecastCollector",
    "IndustryMemberCollector",
    "ConceptMemberCollector",
    "IndustryDataCollector",
    "ConceptDataCollector",
    "OptionDataCollector",
    "OptionGreeksCollector",
    "ImpliedVolatilityCollector",
    "FutureDataCollector",
]
