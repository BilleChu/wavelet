"""
ADS-ORM Model Mappings.

Registers all ADS models with their corresponding ORM models.
This is the central configuration for ADS <-> ORM transformations.

Usage:
    from openfinance.datacenter.models.mappings import register_all_mappings
    
    # Register all mappings at startup
    register_all_mappings()
"""

from openfinance.datacenter.ads import (
    ADSKLineModel,
    ADSMoneyFlowModel,
    ADSOptionQuoteModel,
    ADSFutureQuoteModel,
    ADSStockBasicModel,
    ADSFinancialIndicatorModel,
    ADSBalanceSheetModel,
    ADSIncomeStatementModel,
    ADSCashFlowModel,
    ADSShareholderModel,
    ADSShareholderChangeModel,
    ADSInsiderTradingModel,
    ADSMarketSentimentModel,
    ADSNewsModel,
    ADSStockSentimentModel,
    ADSMacroEconomicModel,
    ADSInterestRateModel,
    ADSExchangeRateModel,
    ADSFactorModel,
    ADSSignalModel,
    ADSBacktestResultModel,
    ADSMetaModel,
    ADSFieldMetaModel,
)

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
)

from openfinance.datacenter.models.framework.transformer import register_ads_orm_mapping


def register_all_mappings() -> None:
    """Register all ADS-ORM mappings."""
    
    register_ads_orm_mapping(
        ads_model=ADSKLineModel,
        orm_model=StockDailyQuoteModel,
        model_id="kline",
        category="market",
        field_mappings={
            "turnover_rate": "turnover_rate",
            "collected_at": "updated_at",
        },
    )
    
    register_ads_orm_mapping(
        ads_model=ADSMoneyFlowModel,
        orm_model=StockMoneyFlowModel,
        model_id="money_flow",
        category="market",
        field_mappings={},
    )
    
    register_ads_orm_mapping(
        ads_model=ADSOptionQuoteModel,
        orm_model=OptionQuoteModel,
        model_id="option_quote",
        category="market",
        field_mappings={},
    )
    
    register_ads_orm_mapping(
        ads_model=ADSFutureQuoteModel,
        orm_model=FutureQuoteModel,
        model_id="future_quote",
        category="market",
        field_mappings={},
    )
    
    register_ads_orm_mapping(
        ads_model=ADSStockBasicModel,
        orm_model=StockBasicModel,
        model_id="stock_basic",
        category="market",
        field_mappings={},
    )
    
    register_ads_orm_mapping(
        ads_model=ADSFinancialIndicatorModel,
        orm_model=StockFinancialIndicatorModel,
        model_id="financial_indicator",
        category="financial",
        field_mappings={},
    )
    
    register_ads_orm_mapping(
        ads_model=ADSFactorModel,
        orm_model=FactorDataModel,
        model_id="factor",
        category="quant",
        field_mappings={
            "factor_category": "factor_type",
            "factor_value": "value",
            "factor_rank": "value_rank",
            "factor_percentile": "value_percentile",
            "collected_at": "calculated_at",
        },
    )
    
    register_ads_orm_mapping(
        ads_model=ADSNewsModel,
        orm_model=NewsModel,
        model_id="news",
        category="sentiment",
        field_mappings={},
    )
    
    register_ads_orm_mapping(
        ads_model=ADSMacroEconomicModel,
        orm_model=MacroEconomicModel,
        model_id="macro_economic",
        category="macro",
        field_mappings={},
    )


MAPPING_CONFIG: dict[str, dict[str, any]] = {
    "kline": {
        "ads_model": ADSKLineModel,
        "orm_model": "StockDailyQuoteModel",
        "category": "market",
        "field_mappings": {
            "turnover_rate": "turnover_rate",
            "collected_at": "updated_at",
        },
    },
    "money_flow": {
        "ads_model": ADSMoneyFlowModel,
        "orm_model": "StockMoneyFlowModel",
        "category": "market",
        "field_mappings": {},
    },
    "financial_indicator": {
        "ads_model": ADSFinancialIndicatorModel,
        "orm_model": "StockFinancialIndicatorModel",
        "category": "financial",
        "field_mappings": {},
    },
    "factor": {
        "ads_model": ADSFactorModel,
        "orm_model": "FactorDataModel",
        "category": "quant",
        "field_mappings": {
            "factor_category": "factor_type",
            "factor_value": "value",
            "factor_rank": "value_rank",
            "factor_percentile": "value_percentile",
        },
    },
    "news": {
        "ads_model": ADSNewsModel,
        "orm_model": "NewsModel",
        "category": "sentiment",
        "field_mappings": {},
    },
    "macro_economic": {
        "ads_model": ADSMacroEconomicModel,
        "orm_model": "MacroEconomicModel",
        "category": "macro",
        "field_mappings": {},
    },
}
