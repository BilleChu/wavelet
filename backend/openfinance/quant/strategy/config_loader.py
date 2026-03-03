"""
Strategy Configuration Loader.

Loads strategy configurations from YAML files and creates strategy instances.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import yaml

from openfinance.domain.models.quant import (
    Strategy,
    StrategyType,
    WeightMethod,
    FactorStatus,
)
from openfinance.quant.strategy.base import BaseStrategy, WeightMethod as BaseWeightMethod
from openfinance.quant.strategy.implementations import StrongStockStrategy

logger = logging.getLogger(__name__)


@dataclass
class StrategyFactorConfig:
    """Configuration for a single factor in the strategy."""
    
    factor_id: str
    name: str
    weight: float
    enabled: bool = True
    parameters: dict[str, Any] = field(default_factory=dict)
    description: str = ""


@dataclass
class StrategyPortfolioConfig:
    """Portfolio configuration for the strategy."""
    
    max_positions: int = 50
    position_size: float = 0.02
    weight_method: str = "equal_weight"
    rebalance_freq: str = "monthly"


@dataclass
class StrategyRiskConfig:
    """Risk management configuration."""
    
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    max_position_weight: float = 0.10
    min_position_weight: float = 0.01


@dataclass
class StrategySignalConfig:
    """Signal generation configuration."""
    
    min_signal_threshold: float = 0.0
    min_factors_required: int = 1
    normalization_method: str = "zscore"


@dataclass
class StrategyBacktestConfig:
    """Backtest configuration."""
    
    initial_capital: float = 1000000.0
    commission: float = 0.0003
    slippage: float = 0.0001
    benchmark: str = "000300"
    risk_free_rate: float = 0.03


@dataclass
class StrategyUniverseConfig:
    """Stock universe configuration."""
    
    min_market_cap: float = 0.0
    max_stocks: int = 500
    exclude_st: bool = True
    exclude_suspended: bool = True
    min_price: float = 0.0


@dataclass
class StrategyConfig:
    """Complete strategy configuration loaded from YAML."""
    
    strategy_id: str
    name: str
    code: str
    display_name: str
    description: str
    strategy_type: str
    version: str
    author: str
    tags: list[str]
    status: str
    
    factors: list[StrategyFactorConfig]
    portfolio: StrategyPortfolioConfig
    risk_management: StrategyRiskConfig
    signal_generation: StrategySignalConfig
    backtest: StrategyBacktestConfig
    universe: StrategyUniverseConfig
    
    metadata: dict[str, Any] = field(default_factory=dict)


class StrategyConfigLoader:
    """
    Loads strategy configurations from YAML files.
    
    Supports:
    - Loading from file path
    - Loading from directory (all YAML files)
    - Converting to Strategy domain model
    - Converting to BaseStrategy instance
    """
    
    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize the loader.
        
        Args:
            config_dir: Directory containing strategy config files
        """
        if config_dir is None:
            config_dir = Path(__file__).parent / "config"
        
        self.config_dir = Path(config_dir)
        self._configs: dict[str, StrategyConfig] = {}
    
    def load_from_file(self, file_path: Path) -> StrategyConfig:
        """
        Load a strategy configuration from a YAML file.
        
        Args:
            file_path: Path to the YAML file
        
        Returns:
            StrategyConfig instance
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        return self._parse_config(data)
    
    def load_all(self) -> dict[str, StrategyConfig]:
        """
        Load all strategy configurations from the config directory.
        
        Returns:
            Dictionary mapping strategy_id to StrategyConfig
        """
        if not self.config_dir.exists():
            logger.warning(f"Config directory does not exist: {self.config_dir}")
            return {}
        
        configs = {}
        
        for yaml_file in self.config_dir.glob("*.yaml"):
            try:
                config = self.load_from_file(yaml_file)
                configs[config.strategy_id] = config
                logger.info(f"Loaded strategy config: {config.strategy_id} from {yaml_file.name}")
            except Exception as e:
                logger.error(f"Failed to load strategy config from {yaml_file}: {e}")
        
        self._configs = configs
        return configs
    
    def get_config(self, strategy_id: str) -> Optional[StrategyConfig]:
        """
        Get a loaded strategy configuration by ID.
        
        Args:
            strategy_id: Strategy identifier
        
        Returns:
            StrategyConfig or None if not found
        """
        if not self._configs:
            self.load_all()
        
        return self._configs.get(strategy_id)
    
    def _parse_config(self, data: dict[str, Any]) -> StrategyConfig:
        """Parse YAML data into StrategyConfig."""
        
        factors = [
            StrategyFactorConfig(
                factor_id=f.get("factor_id", ""),
                name=f.get("name", ""),
                weight=f.get("weight", 1.0),
                enabled=f.get("enabled", True),
                parameters=f.get("parameters", {}),
                description=f.get("description", ""),
            )
            for f in data.get("factors", [])
        ]
        
        portfolio_data = data.get("portfolio", {})
        portfolio = StrategyPortfolioConfig(
            max_positions=portfolio_data.get("max_positions", 50),
            position_size=portfolio_data.get("position_size", 0.02),
            weight_method=portfolio_data.get("weight_method", "equal_weight"),
            rebalance_freq=portfolio_data.get("rebalance_freq", "monthly"),
        )
        
        risk_data = data.get("risk_management", {})
        risk = StrategyRiskConfig(
            stop_loss=risk_data.get("stop_loss"),
            take_profit=risk_data.get("take_profit"),
            max_position_weight=risk_data.get("max_position_weight", 0.10),
            min_position_weight=risk_data.get("min_position_weight", 0.01),
        )
        
        signal_data = data.get("signal_generation", {})
        signal = StrategySignalConfig(
            min_signal_threshold=signal_data.get("min_signal_threshold", 0.0),
            min_factors_required=signal_data.get("min_factors_required", 1),
            normalization_method=signal_data.get("normalization_method", "zscore"),
        )
        
        backtest_data = data.get("backtest", {})
        backtest = StrategyBacktestConfig(
            initial_capital=backtest_data.get("initial_capital", 1000000.0),
            commission=backtest_data.get("commission", 0.0003),
            slippage=backtest_data.get("slippage", 0.0001),
            benchmark=backtest_data.get("benchmark", "000300"),
            risk_free_rate=backtest_data.get("risk_free_rate", 0.03),
        )
        
        universe_data = data.get("universe", {})
        universe = StrategyUniverseConfig(
            min_market_cap=universe_data.get("min_market_cap", 0.0),
            max_stocks=universe_data.get("max_stocks", 500),
            exclude_st=universe_data.get("exclude_st", True),
            exclude_suspended=universe_data.get("exclude_suspended", True),
            min_price=universe_data.get("min_price", 0.0),
        )
        
        return StrategyConfig(
            strategy_id=data.get("strategy_id", ""),
            name=data.get("name", ""),
            code=data.get("code", ""),
            display_name=data.get("display_name", ""),
            description=data.get("description", ""),
            strategy_type=data.get("strategy_type", "multi_factor"),
            version=data.get("version", "1.0.0"),
            author=data.get("author", "system"),
            tags=data.get("tags", []),
            status=data.get("status", "active"),
            factors=factors,
            portfolio=portfolio,
            risk_management=risk,
            signal_generation=signal,
            backtest=backtest,
            universe=universe,
            metadata=data.get("metadata", {}),
        )
    
    def to_domain_strategy(self, config: StrategyConfig) -> Strategy:
        """
        Convert StrategyConfig to domain Strategy model.
        
        Args:
            config: StrategyConfig instance
        
        Returns:
            Strategy domain model
        """
        factor_weights = {
            f.factor_id: f.weight
            for f in config.factors
            if f.enabled
        }
        
        return Strategy(
            strategy_id=config.strategy_id,
            name=config.name,
            code=config.code,
            description=config.description,
            strategy_type=StrategyType.MULTI_FACTOR,
            factors=[f.factor_id for f in config.factors if f.enabled],
            factor_weights=factor_weights,
            weight_method=WeightMethod.EQUAL,
            max_positions=config.portfolio.max_positions,
            rebalance_freq=config.portfolio.rebalance_freq,
            parameters={
                "stop_loss": config.risk_management.stop_loss,
                "take_profit": config.risk_management.take_profit,
                "min_signal_threshold": config.signal_generation.min_signal_threshold,
                "universe": {
                    "min_market_cap": config.universe.min_market_cap,
                    "max_stocks": config.universe.max_stocks,
                },
            },
            status=FactorStatus.ACTIVE,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
    
    def create_strategy_instance(
        self,
        config: StrategyConfig,
    ) -> BaseStrategy:
        """
        Create a strategy instance from configuration.
        
        Args:
            config: StrategyConfig instance
        
        Returns:
            BaseStrategy instance
        """
        if config.strategy_id == "strategy_strong_stock":
            return StrongStockStrategy(
                strategy_id=config.strategy_id,
                name=config.name,
                code=config.code,
                description=config.description,
                max_positions=config.portfolio.max_positions,
                rebalance_freq=config.portfolio.rebalance_freq,
                stop_loss=config.risk_management.stop_loss,
                take_profit=config.risk_management.take_profit,
                parameters={
                    f.factor_id: f.parameters
                    for f in config.factors
                    if f.enabled
                },
            )
        else:
            raise ValueError(f"Unknown strategy type: {config.strategy_id}")


_loader: Optional[StrategyConfigLoader] = None


def get_strategy_config_loader(
    config_dir: Optional[Path] = None,
) -> StrategyConfigLoader:
    """
    Get the global strategy config loader instance.
    
    Args:
        config_dir: Optional config directory path
    
    Returns:
        StrategyConfigLoader instance
    """
    global _loader
    if _loader is None:
        _loader = StrategyConfigLoader(config_dir)
    return _loader
