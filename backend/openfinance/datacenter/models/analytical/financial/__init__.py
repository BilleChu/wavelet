"""
Financial Data Models.

Provides ADS models for financial statement data:
- Financial indicators
- Balance sheet
- Income statement
- Cash flow statement
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import Field, field_validator

from openfinance.datacenter.models.analytical.base import (
    ADSModel,
    ADSModelWithCode,
    ADSModelWithReportDate,
    DataQuality,
    ReportPeriod,
)


class ADSFinancialIndicatorModel(ADSModelWithCode, ADSModelWithReportDate):
    """
    Financial indicator data model.
    
    Key financial metrics derived from financial statements.
    Standardized naming convention:
    - Profitability: roe, roa, gross_margin, net_margin
    - Valuation: eps, bps, pe_ratio, pb_ratio
    - Solvency: debt_ratio, current_ratio, quick_ratio
    - Growth: revenue_yoy, net_profit_yoy
    """
    
    name: str | None = Field(None, description="Stock name")
    
    eps: float | None = Field(None, description="Earnings per share")
    bps: float | None = Field(None, description="Book value per share")
    
    roe: float | None = Field(None, description="Return on equity")
    roa: float | None = Field(None, description="Return on assets")
    
    gross_margin: float | None = Field(None, description="Gross profit margin")
    net_margin: float | None = Field(None, description="Net profit margin")
    operating_margin: float | None = Field(None, description="Operating profit margin")
    
    debt_ratio: float | None = Field(None, description="Debt to assets ratio")
    current_ratio: float | None = Field(None, description="Current ratio")
    quick_ratio: float | None = Field(None, description="Quick ratio")
    
    revenue: float | None = Field(None, description="Total revenue")
    net_profit: float | None = Field(None, description="Net profit")
    operating_profit: float | None = Field(None, description="Operating profit")
    
    revenue_yoy: float | None = Field(None, description="Revenue YoY growth")
    net_profit_yoy: float | None = Field(None, description="Net profit YoY growth")
    operating_profit_yoy: float | None = Field(None, description="Operating profit YoY growth")
    
    total_assets: float | None = Field(None, description="Total assets")
    total_equity: float | None = Field(None, description="Total equity")
    total_liabilities: float | None = Field(None, description="Total liabilities")
    
    @property
    def is_profitable(self) -> bool | None:
        """Check if company is profitable."""
        if self.net_profit is not None:
            return self.net_profit > 0
        return None
    
    @property
    def leverage_level(self) -> str | None:
        """Assess leverage level based on debt ratio."""
        if self.debt_ratio is None:
            return None
        if self.debt_ratio < 0.3:
            return "low"
        elif self.debt_ratio < 0.6:
            return "medium"
        else:
            return "high"


class ADSBalanceSheetModel(ADSModelWithCode, ADSModelWithReportDate):
    """
    Balance sheet data model.
    
    Assets = Liabilities + Equity
    
    Standardized structure following accounting standards.
    """
    
    name: str | None = Field(None, description="Stock name")
    
    total_assets: float | None = Field(None, description="Total assets")
    total_current_assets: float | None = Field(None, description="Total current assets")
    total_non_current_assets: float | None = Field(None, description="Total non-current assets")
    
    cash: float | None = Field(None, description="Cash and cash equivalents")
    accounts_receivable: float | None = Field(None, description="Accounts receivable")
    inventory: float | None = Field(None, description="Inventory")
    fixed_assets: float | None = Field(None, description="Fixed assets")
    intangible_assets: float | None = Field(None, description="Intangible assets")
    
    total_liabilities: float | None = Field(None, description="Total liabilities")
    total_current_liabilities: float | None = Field(None, description="Total current liabilities")
    total_non_current_liabilities: float | None = Field(None, description="Total non-current liabilities")
    
    short_term_debt: float | None = Field(None, description="Short-term debt")
    long_term_debt: float | None = Field(None, description="Long-term debt")
    accounts_payable: float | None = Field(None, description="Accounts payable")
    
    total_equity: float | None = Field(None, description="Total equity")
    paid_in_capital: float | None = Field(None, description="Paid-in capital")
    retained_earnings: float | None = Field(None, description="Retained earnings")
    
    @property
    def net_assets(self) -> float | None:
        """Calculate net assets (equity)."""
        return self.total_equity
    
    @property
    def working_capital(self) -> float | None:
        """Calculate working capital."""
        if self.total_current_assets and self.total_current_liabilities:
            return self.total_current_assets - self.total_current_liabilities
        return None
    
    @property
    def debt_to_equity(self) -> float | None:
        """Calculate debt to equity ratio."""
        if self.total_liabilities and self.total_equity and self.total_equity > 0:
            return self.total_liabilities / self.total_equity
        return None


class ADSIncomeStatementModel(ADSModelWithCode, ADSModelWithReportDate):
    """
    Income statement data model.
    
    Revenue - Expenses = Net Income
    
    Standardized structure following accounting standards.
    """
    
    name: str | None = Field(None, description="Stock name")
    
    total_revenue: float | None = Field(None, description="Total revenue")
    operating_revenue: float | None = Field(None, description="Operating revenue")
    other_revenue: float | None = Field(None, description="Other revenue")
    
    total_operating_cost: float | None = Field(None, description="Total operating cost")
    cost_of_goods_sold: float | None = Field(None, description="Cost of goods sold")
    selling_expenses: float | None = Field(None, description="Selling expenses")
    admin_expenses: float | None = Field(None, description="Administrative expenses")
    rd_expenses: float | None = Field(None, description="R&D expenses")
    finance_expenses: float | None = Field(None, description="Finance expenses")
    
    operating_profit: float | None = Field(None, description="Operating profit")
    total_profit: float | None = Field(None, description="Total profit")
    net_profit: float | None = Field(None, description="Net profit")
    net_profit_attr_parent: float | None = Field(None, description="Net profit attributable to parent")
    net_profit_attr_minority: float | None = Field(None, description="Net profit attributable to minority")
    
    income_tax: float | None = Field(None, description="Income tax expense")
    interest_expense: float | None = Field(None, description="Interest expense")
    
    basic_eps: float | None = Field(None, description="Basic earnings per share")
    diluted_eps: float | None = Field(None, description="Diluted earnings per share")
    
    @property
    def gross_profit(self) -> float | None:
        """Calculate gross profit."""
        if self.operating_revenue and self.cost_of_goods_sold:
            return self.operating_revenue - self.cost_of_goods_sold
        return None
    
    @property
    def gross_margin(self) -> float | None:
        """Calculate gross margin."""
        gross_profit = self.gross_profit
        if gross_profit and self.operating_revenue and self.operating_revenue > 0:
            return gross_profit / self.operating_revenue
        return None
    
    @property
    def operating_margin(self) -> float | None:
        """Calculate operating margin."""
        if self.operating_profit and self.operating_revenue and self.operating_revenue > 0:
            return self.operating_profit / self.operating_revenue
        return None
    
    @property
    def net_margin(self) -> float | None:
        """Calculate net margin."""
        if self.net_profit and self.total_revenue and self.total_revenue > 0:
            return self.net_profit / self.total_revenue
        return None


class ADSCashFlowModel(ADSModelWithCode, ADSModelWithReportDate):
    """
    Cash flow statement data model.
    
    Operating + Investing + Financing = Net Cash Change
    
    Standardized structure following accounting standards.
    """
    
    name: str | None = Field(None, description="Stock name")
    
    net_cash_from_operating: float | None = Field(None, description="Net cash from operating activities")
    net_cash_from_investing: float | None = Field(None, description="Net cash from investing activities")
    net_cash_from_financing: float | None = Field(None, description="Net cash from financing activities")
    
    net_cash_increase: float | None = Field(None, description="Net increase in cash")
    cash_at_beginning: float | None = Field(None, description="Cash at beginning of period")
    cash_at_end: float | None = Field(None, description="Cash at end of period")
    
    cash_received_from_sales: float | None = Field(None, description="Cash received from sales")
    cash_paid_for_goods: float | None = Field(None, description="Cash paid for goods and services")
    cash_paid_to_employees: float | None = Field(None, description="Cash paid to employees")
    taxes_paid: float | None = Field(None, description="Taxes paid")
    
    cash_paid_for_assets: float | None = Field(None, description="Cash paid for fixed assets")
    cash_received_from_assets: float | None = Field(None, description="Cash received from asset disposal")
    cash_paid_for_investments: float | None = Field(None, description="Cash paid for investments")
    
    cash_received_from_financing: float | None = Field(None, description="Cash received from financing")
    cash_paid_for_debt: float | None = Field(None, description="Cash paid for debt repayment")
    dividends_paid: float | None = Field(None, description="Dividends paid")
    
    free_cash_flow: float | None = Field(None, description="Free cash flow")
    
    @property
    def operating_cash_flow_positive(self) -> bool | None:
        """Check if operating cash flow is positive."""
        if self.net_cash_from_operating is not None:
            return self.net_cash_from_operating > 0
        return None
    
    @property
    def is_self_funding(self) -> bool | None:
        """Check if company is self-funding (positive operating, negative financing)."""
        if self.net_cash_from_operating is not None and self.net_cash_from_financing is not None:
            return self.net_cash_from_operating > 0 and self.net_cash_from_financing < 0
        return None
    
    @property
    def cash_flow_quality(self) -> str | None:
        """Assess cash flow quality."""
        if self.net_cash_from_operating is None or self.net_profit is None:
            return None
        if self.net_cash_from_operating > self.net_profit:
            return "high"
        elif self.net_cash_from_operating > 0:
            return "medium"
        else:
            return "low"
