"""
Factor System Tests.

Unit tests for factor calculation and analysis.
"""

import unittest
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import numpy as np

from openfinance.quant.factors.base import (
    FactorBase,
    FactorCategory,
    FactorConfig,
    FactorMetadata,
    FactorResult,
    FactorType,
    NormalizeMethod,
    ParameterDefinition,
    ValidationResult,
)
from openfinance.quant.factors.registry import (
    FactorDefinition,
    UnifiedFactorRegistry,
    get_factor_registry,
)
from openfinance.quant.factors.analysis import (
    FactorNeutralizer,
    FactorCorrelationAnalyzer,
    FactorICAnalyzer,
    NeutralizationConfig,
)


class TestFactorBase(unittest.TestCase):
    """Tests for FactorBase class."""
    
    def test_factor_metadata_creation(self):
        """Test factor metadata creation."""
        metadata = FactorMetadata(
            factor_id="test_factor",
            name="Test Factor",
            description="A test factor",
            factor_type=FactorType.TECHNICAL,
            category=FactorCategory.MOMENTUM,
        )
        
        self.assertEqual(metadata.factor_id, "test_factor")
        self.assertEqual(metadata.name, "Test Factor")
        self.assertEqual(metadata.factor_type, FactorType.TECHNICAL)
        self.assertEqual(metadata.category, FactorCategory.MOMENTUM)
    
    def test_parameter_definition_validation(self):
        """Test parameter definition validation."""
        param = ParameterDefinition(
            name="period",
            type="int",
            default=14,
            min_value=5,
            max_value=50,
        )
        
        self.assertEqual(param.name, "period")
        self.assertEqual(param.default, 14)
        self.assertEqual(param.min_value, 5)
        self.assertEqual(param.max_value, 50)
    
    def test_factor_config_defaults(self):
        """Test factor config default values."""
        config = FactorConfig()
        
        self.assertEqual(config.lookback_period, 14)
        self.assertTrue(config.normalize)
        self.assertEqual(config.normalize_method, NormalizeMethod.ZSCORE)
    
    def test_factor_result_is_valid(self):
        """Test factor result validation."""
        result = FactorResult(
            factor_id="test",
            code="600000.SH",
            trade_date=date.today(),
            value=0.5,
        )
        
        self.assertTrue(result.is_valid)
        
        result_none = FactorResult(
            factor_id="test",
            code="600000.SH",
            trade_date=date.today(),
            value=None,
        )
        
        self.assertFalse(result_none.is_valid)


class TestFactorRegistry(unittest.TestCase):
    """Tests for UnifiedFactorRegistry."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.registry = UnifiedFactorRegistry()
    
    def test_registry_singleton(self):
        """Test registry singleton pattern."""
        registry1 = get_factor_registry()
        registry2 = get_factor_registry()
        
        self.assertIs(registry1, registry2)
    
    def test_list_factors(self):
        """Test listing factors."""
        factors = self.registry.list_factors()
        
        self.assertGreater(len(factors), 0)
    
    def test_get_factor(self):
        """Test getting a factor."""
        factor = self.registry.get("factor_rsi")
        
        self.assertIsNotNone(factor)
        self.assertEqual(factor.code, "rsi")
    
    def test_get_by_code(self):
        """Test getting factor by code."""
        factor = self.registry.get_by_code("rsi")
        
        self.assertIsNotNone(factor)
        self.assertEqual(factor.factor_id, "factor_rsi")
    
    def test_register_custom_factor(self):
        """Test registering a custom factor."""
        factor_def = self.registry.register(
            name="Custom Test Factor",
            code="custom_test",
            expression="close / sma(close, 20) - 1",
            description="A custom test factor",
            category=FactorCategory.CUSTOM,
        )
        
        self.assertEqual(factor_def.code, "custom_test")
        
        retrieved = self.registry.get_by_code("custom_test")
        self.assertIsNotNone(retrieved)
    
    def test_list_by_category(self):
        """Test listing factors by category."""
        momentum_factors = self.registry.list_by_category(FactorCategory.MOMENTUM)
        
        self.assertGreater(len(momentum_factors), 0)
    
    def test_search_factors(self):
        """Test searching factors."""
        results = self.registry.search("RSI")
        
        self.assertGreater(len(results), 0)
        self.assertIn("factor_rsi", results)


class TestFactorNeutralizer(unittest.TestCase):
    """Tests for FactorNeutralizer."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.neutralizer = FactorNeutralizer()
    
    def test_neutralize_empty(self):
        """Test neutralization with empty input."""
        result = self.neutralizer.neutralize({})
        
        self.assertEqual(result, {})
    
    def test_neutralize_basic(self):
        """Test basic neutralization."""
        factor_values = {
            "stock1": 0.5,
            "stock2": 0.3,
            "stock3": 0.7,
        }
        
        result = self.neutralizer.neutralize(factor_values)
        
        self.assertEqual(len(result), 3)
    
    def test_industry_neutralization(self):
        """Test industry neutralization."""
        factor_values = {
            "stock1": 0.5,
            "stock2": 0.3,
            "stock3": 0.7,
            "stock4": 0.2,
            "stock5": 0.8,
        }
        
        industry_map = {
            "stock1": "tech",
            "stock2": "tech",
            "stock3": "finance",
            "stock4": "finance",
            "stock5": "tech",
        }
        
        result = self.neutralizer.neutralize(
            factor_values,
            industry_map=industry_map,
        )
        
        self.assertEqual(len(result), 5)


class TestFactorCorrelationAnalyzer(unittest.TestCase):
    """Tests for FactorCorrelationAnalyzer."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.analyzer = FactorCorrelationAnalyzer()
    
    def test_calculate_correlation(self):
        """Test correlation calculation."""
        np.random.seed(42)
        
        factor1 = {f"stock{i}": np.random.randn() for i in range(100)}
        factor2 = {f"stock{i}": factor1[f"stock{i}"] * 0.8 + np.random.randn() * 0.2 for i in range(100)}
        
        result = self.analyzer.calculate_correlation(factor1, factor2)
        
        self.assertGreater(result.correlation, 0.5)
        self.assertGreater(result.sample_size, 50)
    
    def test_calculate_correlation_matrix(self):
        """Test correlation matrix calculation."""
        np.random.seed(42)
        
        factors = {
            "factor1": {f"stock{i}": np.random.randn() for i in range(50)},
            "factor2": {f"stock{i}": np.random.randn() for i in range(50)},
            "factor3": {f"stock{i}": np.random.randn() for i in range(50)},
        }
        
        matrix = self.analyzer.calculate_correlation_matrix(factors)
        
        self.assertIn("factor1", matrix)
        self.assertEqual(matrix["factor1"]["factor1"], 1.0)


class TestFactorICAnalyzer(unittest.TestCase):
    """Tests for FactorICAnalyzer."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.analyzer = FactorICAnalyzer()
    
    def test_calculate_ic(self):
        """Test IC calculation."""
        np.random.seed(42)
        
        factor_values = {f"stock{i}": np.random.randn() for i in range(100)}
        forward_returns = {f"stock{i}": factor_values[f"stock{i}"] * 0.1 + np.random.randn() * 0.05 for i in range(100)}
        
        result = self.analyzer.calculate_ic(factor_values, forward_returns)
        
        self.assertIsNotNone(result.ic)
        self.assertGreater(result.sample_size, 50)
    
    def test_calculate_ir(self):
        """Test IR calculation."""
        ic_series = []
        np.random.seed(42)
        
        for _ in range(20):
            factor_values = {f"stock{i}": np.random.randn() for i in range(50)}
            forward_returns = {f"stock{i}": factor_values[f"stock{i}"] * 0.1 + np.random.randn() * 0.05 for i in range(50)}
            
            ic_result = self.analyzer.calculate_ic(factor_values, forward_returns)
            ic_series.append(ic_result)
        
        ir_result = self.analyzer.calculate_ir(ic_series)
        
        self.assertIsNotNone(ir_result.mean_ic)
        self.assertIsNotNone(ir_result.ir)


if __name__ == "__main__":
    unittest.main()
