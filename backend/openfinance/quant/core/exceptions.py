"""
Custom exceptions for quantitative analysis module.
"""


class QuantError(Exception):
    """Base exception for quant module."""
    pass


class FactorError(QuantError):
    """Exception raised for factor-related errors."""
    pass


class FactorCalculationError(FactorError):
    """Exception raised when factor calculation fails."""
    pass


class FactorValidationError(FactorError):
    """Exception raised when factor validation fails."""
    pass


class StrategyError(QuantError):
    """Exception raised for strategy-related errors."""
    pass


class StrategyConstructionError(StrategyError):
    """Exception raised when strategy construction fails."""
    pass


class BacktestError(QuantError):
    """Exception raised for backtest-related errors."""
    pass


class BacktestConfigurationError(BacktestError):
    """Exception raised when backtest configuration is invalid."""
    pass


class DataError(QuantError):
    """Exception raised for data-related errors."""
    pass


class DataNotAvailableError(DataError):
    """Exception raised when required data is not available."""
    pass


class InsufficientDataError(DataError):
    """Exception raised when there's insufficient data for calculation."""
    pass


class PerformanceMetricsError(QuantError):
    """Exception raised for performance metrics calculation errors."""
    pass


class RiskModelError(QuantError):
    """Exception raised for risk model errors."""
    pass
