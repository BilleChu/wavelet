"""
Example: Complete quantitative analysis workflow test.
Demonstrates end-to-end testing with real backend data.
"""

import pytest
from playwright.sync_api import Page, expect
from .test_helpers import QuantTestHelpers


def test_complete_quant_workflow(page: Page):
    """
    Complete end-to-end workflow test:
    1. Discover factors
    2. View factor details and data
    3. Create strategy
    4. Run backtest
    5. Analyze results with professional analytics
    
    This test validates the entire quant analysis pipeline.
    """
    
    print("\n" + "="*80)
    print("COMPLETE QUANTITATIVE ANALYSIS WORKFLOW TEST")
    print("="*80)
    
    helpers = QuantTestHelpers(page)
    backtest_id = None
    
    try:
        # ========== STEP 1: Factor Discovery ==========
        print("\n[STEP 1] Discovering factors from database...")
        
        helpers.navigate_to_quant_page()
        helpers.switch_tab('factors')
        
        # Count available factors
        factors = page.locator('[data-testid="factor-item"]').all()
        factor_count = len(factors)
        
        print(f"✓ Found {factor_count} factors in database")
        assert factor_count > 0, "No factors available"
        
        # Select first factor
        factors[0].click()
        page.wait_for_selector('[data-testid="factor-detail-panel"]', timeout=5000)
        
        # Extract factor info
        factor_name = page.locator('[data-testid="factor-name"]').text_content()
        factor_category = page.locator('[data-testid="factor-category"]').text_content()
        
        print(f"✓ Selected factor: {factor_name} ({factor_category})")
        
        # ========== STEP 2: Query Factor Data ==========
        print("\n[STEP 2] Querying historical factor data...")
        
        helpers.switch_tab('factor-data')
        
        # Enter stock code (Kweichow Moutai)
        page.fill('[data-testid="stock-code-input"]', '600519.SH')
        page.fill('[data-testid="start-date"]', '2023-01-01')
        page.fill('[data-testid="end-date"]', '2023-12-31')
        
        page.click('[data-testid="query-data-button"]')
        helpers.wait_for_loading_complete(timeout=15000)
        
        # Verify chart rendered
        helpers.assert_chart_rendered('[data-testid="factor-chart"]')
        
        # Count data points
        data_rows = helpers.count_table_rows('[data-testid="factor-data-table"]')
        
        print(f"✓ Retrieved {data_rows} data points for 600519.SH")
        assert data_rows > 0, "No factor data returned"
        
        # ========== STEP 3: Strategy Development ==========
        print("\n[STEP 3] Testing strategy signal generation...")
        
        helpers.navigate_to_quant_page()
        helpers.switch_tab('strategies')
        
        # Select first strategy
        strategies = page.locator('[data-testid="strategy-item"]').all()
        assert len(strategies) > 0, "No strategies available"
        
        strategies[0].click()
        page.wait_for_selector('[data-testid="strategy-detail-panel"]', timeout=5000)
        
        # Run strategy to get signals
        page.click('[data-testid="run-strategy-button"]')
        helpers.wait_for_loading_complete(timeout=30000)
        
        # Verify recommendations
        recommendations = page.locator('[data-testid="stock-recommendation"]').all()
        rec_count = len(recommendations)
        
        print(f"✓ Generated {rec_count} stock recommendations")
        assert rec_count > 0, "No recommendations generated"
        
        # Get top pick
        top_rec = recommendations[0]
        top_stock = top_rec.locator('[data-testid="stock-code"]').text_content()
        top_score = top_rec.locator('[data-testid="stock-score"]').text_content()
        
        print(f"✓ Top pick: {top_stock} (Score: {top_score})")
        
        # ========== STEP 4: Backtest Execution ==========
        print("\n[STEP 4] Running backtest with historical data...")
        
        helpers.navigate_to_quant_page()
        helpers.switch_tab('backtest')
        
        # Configure backtest
        page.select_option('[data-testid="strategy-select"]', 'momentum_strategy')
        helpers.fill_date_range('2023-01-01', '2023-06-30')  # 6 months
        page.fill('[data-testid="initial-capital"]', '1000000')
        
        # Run backtest
        page.click('[data-testid="run-backtest-button"]')
        print("Waiting for backtest to complete (may take up to 60s)...")
        helpers.wait_for_loading_complete(timeout=60000)
        
        # Wait for results
        expect(page.locator('[data-testid="backtest-results"]')).to_be_visible(timeout=30000)
        
        # Verify equity curve
        helpers.assert_chart_rendered('[data-testid="equity-curve-chart"]')
        
        # Extract metrics
        total_return = helpers.get_metric_value('[data-testid="total-return"]')
        sharpe_ratio = helpers.get_metric_value('[data-testid="sharpe-ratio"]')
        max_drawdown = helpers.get_metric_value('[data-testid="max-drawdown"]')
        
        print(f"✓ Backtest Results:")
        print(f"  Total Return: {total_return}%")
        print(f"  Sharpe Ratio: {sharpe_ratio}")
        print(f"  Max Drawdown: {max_drawdown}%")
        
        assert total_return is not None, "Total return is missing"
        assert sharpe_ratio is not None, "Sharpe ratio is missing"
        assert max_drawdown is not None and max_drawdown < 0, "Max drawdown should be negative"
        
        # Count trades
        helpers.switch_tab('trades')
        trade_count = helpers.count_table_rows('[data-testid="trades-table"]')
        
        print(f"✓ Executed {trade_count} trades")
        assert trade_count > 0, "No trades recorded"
        
        # Get backtest ID for analytics
        backtest_id = helpers.extract_backtest_id_from_url()
        
        # ========== STEP 5: Professional Analytics ==========
        print("\n[STEP 5] Running professional analytics...")
        
        if backtest_id:
            helpers.navigate_to_analytics_page(backtest_id)
            
            # Test Performance Dashboard
            print("Testing Performance Metrics Dashboard...")
            performance_data = helpers.verify_performance_metrics(expected_min_metrics=25)
            
            print(f"✓ Verified {performance_data['total_metrics']} metrics across "
                  f"{len(performance_data['categories_found'])} categories")
            
            # Test Risk Analysis
            print("Testing Risk Analysis Panel...")
            helpers.switch_tab('risk')
            risk_data = helpers.verify_risk_analysis()
            
            if risk_data.get('var') and risk_data.get('cvar'):
                print(f"✓ VaR: {risk_data['var']:.2%}, CVaR: {risk_data['cvar']:.2%}")
            
            # Test Attribution Analysis
            print("Testing Attribution Analysis...")
            helpers.switch_tab('attribution')
            helpers.assert_chart_rendered('[data-testid="brinson-chart"]')
            
            factor_attributions = page.locator('[data-testid="factor-attribution-item"]').all()
            print(f"✓ Displayed {len(factor_attributions)} factor attributions")
            
            # Test Charts
            print("Testing Chart Analysis...")
            helpers.switch_tab('charts')
            helpers.assert_chart_rendered('[data-testid="equity-curve-chart"]')
            helpers.assert_chart_rendered('[data-testid="drawdown-chart"]')
            
            print("✓ All chart analysis validated")
        else:
            print("⚠ Skipping analytics - no backtest ID")
        
        # ========== SUMMARY ==========
        print("\n" + "="*80)
        print("WORKFLOW TEST SUMMARY")
        print("="*80)
        print(f"✓ Factors discovered: {factor_count}")
        print(f"✓ Factor data points: {data_rows}")
        print(f"✓ Stock recommendations: {rec_count}")
        print(f"✓ Backtest return: {total_return:.2f}%")
        print(f"✓ Backtest Sharpe: {sharpe_ratio:.2f}")
        print(f"✓ Trades executed: {trade_count}")
        if backtest_id:
            print(f"✓ Analytics verified: {performance_data['total_metrics']} metrics")
        print("="*80)
        print("✓ COMPLETE WORKFLOW TEST PASSED")
        print("="*80)
        
    except Exception as e:
        print(f"\n✗ Workflow test failed: {e}")
        
        # Take screenshot
        screenshot_path = helpers.take_screenshot('workflow_failure')
        print(f"Screenshot saved: {screenshot_path}")
        
        raise


@pytest.mark.integration
def test_api_data_consistency(page: Page, backend_url: str):
    """
    Test that frontend data matches backend API responses.
    Validates data integrity throughout the stack.
    """
    
    print("\n=== Testing API Data Consistency ===")
    
    import requests
    
    helpers = QuantTestHelpers(page)
    helpers.navigate_to_quant_page()
    helpers.switch_tab('factors')
    
    # Get factors from frontend
    frontend_factors = page.locator('[data-testid="factor-item"]').all()
    frontend_factor_names = [
        f.locator('[data-testid="factor-name"]').text_content() 
        for f in frontend_factors
    ]
    
    # Get factors from backend API
    response = requests.get(f'{backend_url}/api/quant/factors', timeout=5)
    api_factors = response.json().get('factors', [])
    api_factor_names = [f['name'] for f in api_factors]
    
    print(f"Frontend factors: {len(frontend_factor_names)}")
    print(f"Backend API factors: {len(api_factor_names)}")
    
    # Verify consistency
    assert len(frontend_factor_names) == len(api_factor_names), \
        "Factor count mismatch between frontend and backend"
    
    # Check names match
    for name in frontend_factor_names:
        assert name in api_factor_names, f"Factor '{name}' not found in backend API"
    
    print("✓ Frontend and backend data are consistent")


if __name__ == '__main__':
    # Can run standalone for debugging
    from playwright.sync_api import sync_playwright
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=100)
        context = browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = context.new_page()
        
        try:
            test_complete_quant_workflow(page)
            print("\n✓ Standalone test completed successfully!")
        except Exception as e:
            print(f"\n✗ Standalone test failed: {e}")
        finally:
            browser.close()
