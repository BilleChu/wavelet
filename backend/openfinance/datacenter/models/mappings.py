"""
ADS-ORM Model Mappings.

通过 YAML 配置自动加载所有模型映射关系。
字段映射通过 ADS 模型的 Field(alias=...) 处理。

Usage:
    from openfinance.datacenter.models.mappings import init_registry
    init_registry()
"""

from pathlib import Path

from openfinance.datacenter.models.analytical import ADSModelRegistry
from openfinance.datacenter.models.analytical.market import (
    ADSKLineModel,
    ADSMoneyFlowModel,
    ADSOptionQuoteModel,
    ADSFutureQuoteModel,
    ADSStockBasicModel,
)
from openfinance.datacenter.models.analytical.financial import (
    ADSFinancialIndicatorModel,
    ADSBalanceSheetModel,
    ADSIncomeStatementModel,
    ADSCashFlowModel,
)
from openfinance.datacenter.models.analytical.quant import ADSFactorModel
from openfinance.datacenter.models.analytical.sentiment import ADSNewsModel
from openfinance.datacenter.models.analytical.macro import ADSMacroEconomicModel

from openfinance.datacenter.models.orm import (
    StockDailyQuoteModel,
    StockMoneyFlowModel,
    StockFinancialIndicatorModel,
    FactorDataModel,
    NewsModel,
    MacroEconomicModel,
    OptionQuoteModel,
    FutureQuoteModel,
    StockBasicModel,
    IncomeStatementModel,
    BalanceSheetModel,
    CashFlowModel,
)

from openfinance.datacenter.models.analytical.base import DataCategory


_CONFIG_PATH = Path(__file__).parent / "config" / "data_types.yaml"

_MANUAL_REGISTRATIONS: dict[str, tuple[type, type, DataCategory, str]] = {
    "kline": (ADSKLineModel, StockDailyQuoteModel, DataCategory.MARKET, "股票K线数据"),
    "money_flow": (ADSMoneyFlowModel, StockMoneyFlowModel, DataCategory.MARKET, "资金流向数据"),
    "option_quote": (ADSOptionQuoteModel, OptionQuoteModel, DataCategory.MARKET, "期权行情数据"),
    "future_quote": (ADSFutureQuoteModel, FutureQuoteModel, DataCategory.MARKET, "期货行情数据"),
    "stock_basic": (ADSStockBasicModel, StockBasicModel, DataCategory.MARKET, "股票基本信息"),
    "financial_indicator": (ADSFinancialIndicatorModel, StockFinancialIndicatorModel, DataCategory.FINANCIAL, "财务指标数据"),
    "balance_sheet": (ADSBalanceSheetModel, BalanceSheetModel, DataCategory.FINANCIAL, "资产负债表"),
    "income_statement": (ADSIncomeStatementModel, IncomeStatementModel, DataCategory.FINANCIAL, "利润表"),
    "cash_flow": (ADSCashFlowModel, CashFlowModel, DataCategory.FINANCIAL, "现金流量表"),
    "factor": (ADSFactorModel, FactorDataModel, DataCategory.QUANT, "因子数据"),
    "news": (ADSNewsModel, NewsModel, DataCategory.SENTIMENT, "新闻数据"),
    "macro_economic": (ADSMacroEconomicModel, MacroEconomicModel, DataCategory.MACRO, "宏观经济数据"),
}


def init_registry(use_yaml: bool = True) -> None:
    """
    初始化模型注册中心。
    
    Args:
        use_yaml: 是否从 YAML 配置加载（默认 True）
    """
    registry = ADSModelRegistry.get_instance()
    
    if use_yaml and _CONFIG_PATH.exists():
        registry.load_all_from_yaml(str(_CONFIG_PATH))
    
    for model_id, (ads_model, orm_model, category, description) in _MANUAL_REGISTRATIONS.items():
        registry.register(
            model_id=model_id,
            category=category,
            model_class=ads_model,
            orm_model=orm_model,
            description=description,
        )


def register_all_mappings() -> None:
    """注册所有 ADS-ORM 映射（兼容旧接口）。"""
    init_registry()


MAPPING_CONFIG: dict[str, dict[str, str]] = {
    "kline": {"orm_model": "StockDailyQuoteModel", "category": "market"},
    "money_flow": {"orm_model": "StockMoneyFlowModel", "category": "market"},
    "option_quote": {"orm_model": "OptionQuoteModel", "category": "market"},
    "future_quote": {"orm_model": "FutureQuoteModel", "category": "market"},
    "stock_basic": {"orm_model": "StockBasicModel", "category": "market"},
    "financial_indicator": {"orm_model": "StockFinancialIndicatorModel", "category": "financial"},
    "balance_sheet": {"orm_model": "BalanceSheetModel", "category": "financial"},
    "income_statement": {"orm_model": "IncomeStatementModel", "category": "financial"},
    "cash_flow": {"orm_model": "CashFlowModel", "category": "financial"},
    "factor": {"orm_model": "FactorDataModel", "category": "quant"},
    "news": {"orm_model": "NewsModel", "category": "sentiment"},
    "macro_economic": {"orm_model": "MacroEconomicModel", "category": "macro"},
}
