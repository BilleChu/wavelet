"""
Smoke tests for quantitative analysis pages.
Quick validation that core functionality is working.
"""

import pytest
from playwright.sync_api import Page, expect
from .test_helpers import QuantTestHelpers


@pytest.mark.smoke
def test_quant_page_loads(page: Page):
    """Test that quant page loads successfully"""
    
    print("\n=== Smoke Test: Page Load ===")
    
    helpers = QuantTestHelpers(page)
    helpers.navigate_to_quant_page()
    
    # Verify page title
    expect(page).to_have_title("量化分析 - OpenFinance", timeout=5000)
    
    # Verify main tabs exist
    expect(page.locator('[data-testid="factors-tab"]')).to_be_visible()
    expect(page.locator('[data-testid="strategies-tab"]')).to_be_visible()
    expect(page.locator('[data-testid="backtest-tab"]')).to_be_visible()
    
    print("✓ Quant page loaded successfully")


@pytest.mark.smoke
def test_factors_tab_accessible(page: Page):
    """Test that factors tab is accessible and shows data"""
    
    print("\n=== Smoke Test: Factors Tab ===")
    
    helpers = QuantTestHelpers(page)
    helpers.navigate_to_quant_page()
    
    # Switch to factors tab
    helpers.switch_tab('factors')
    
    # Verify factor list is visible
    expect(page.locator('[data-testid="factor-list"]')).to_be_visible(timeout=10000)
    
    # Count factors (should have at least 1)
    factors = page.locator('[data-testid="factor-item"]').all()
    factor_count = len(factors)
    
    print(f"✓ Found {factor_count} factors in database")
    assert factor_count > 0, "No factors available - database may not be initialized"


@pytest.mark.smoke
def test_strategies_tab_accessible(page: Page):
    """Test that strategies tab is accessible"""
    
    print("\n=== Smoke Test: Strategies Tab ===")
    
    helpers = QuantTestHelpers(page)
    helpers.navigate_to_quant_page()
    
    # Switch to strategies tab
    helpers.switch_tab('strategies')
    
    # Verify strategy list is visible
    expect(page.locator('[data-testid="strategy-list"]')).to_be_visible(timeout=10000)
    
    # Count strategies
    strategies = page.locator('[data-testid="strategy-item"]').all()
    strategy_count = len(strategies)
    
    print(f"✓ Found {strategy_count} strategies in database")
    assert strategy_count > 0, "No strategies available"


@pytest.mark.smoke
def test_backend_health(page: Page, backend_url: str):
    """Test that backend API is healthy"""
    
    print("\n=== Smoke Test: Backend Health ===")
    
    # Use requests to check health endpoint
    import requests
    
    try:
        response = requests.get(f'{backend_url}/api/quant/health', timeout=5)
        response.raise_for_status()
        
        health_data = response.json()
        
        assert health_data.get('status') == 'healthy'
        factors_available = int(health_data.get('factors_available', 0))
        
        print(f"✓ Backend healthy - Status: {health_data.get('status')}")
        print(f"✓ Factors available: {factors_available}")
        
        assert factors_available > 0, "No factors in database"
        
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Backend health check failed: {e}")


@pytest.mark.smoke
def test_database_has_data(page: Page, backend_url: str):
    """Test that database has minimum required data"""
    
    print("\n=== Smoke Test: Database Data ===")
    
    import requests
    
    try:
        # Check factors
        factors_response = requests.get(f'{backend_url}/api/quant/factors', timeout=5)
        factors_data = factors_response.json()
        factors_count = factors_data.get('total', 0)
        
        # Check stocks
        stocks_response = requests.get(f'{backend_url}/api/datacenter/stocks', timeout=5)
        stocks_data = stocks_response.json()
        stocks_count = len(stocks_data) if isinstance(stocks_data, list) else 0
        
        print(f"✓ Database status:")
        print(f"  - Factors: {factors_count}")
        print(f"  - Stocks: {stocks_count}")
        
        assert factors_count >= 5, f"Expected at least 5 factors, got {factors_count}"
        assert stocks_count > 0, "No stocks in database"
        
    except Exception as e:
        pytest.fail(f"Database check failed: {e}")
