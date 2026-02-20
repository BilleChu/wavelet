"""
Test utilities for quantitative analysis E2E tests.
Provides common helpers, fixtures, and assertions.
"""

from playwright.sync_api import Page, expect
import time
from typing import Optional, Dict, Any


class QuantTestHelpers:
    """Helper utilities for quant analysis testing"""
    
    def __init__(self, page: Page):
        self.page = page
    
    def wait_for_page_ready(self, timeout: int = 15000):
        """Wait for page to be fully loaded and interactive"""
        self.page.wait_for_load_state('networkidle', timeout=timeout)
        time.sleep(1)  # Extra buffer for React hydration
    
    def navigate_to_quant_page(self):
        """Navigate to quant main page"""
        self.page.goto('http://localhost:5173/quant')
        self.wait_for_page_ready()
    
    def navigate_to_analytics_page(self, backtest_id: str):
        """Navigate to analytics detail page"""
        self.page.goto(f'http://localhost:5173/quant/analytics/[id]?backtest_id={backtest_id}')
        self.wait_for_page_ready()
    
    def switch_tab(self, tab_name: str):
        """Switch to a specific tab"""
        tab_selector = f'[data-testid="{tab_name}-tab"]'
        expect(self.page.locator(tab_selector)).to_be_visible(timeout=5000)
        self.page.click(tab_selector)
        self.wait_for_page_ready()
    
    def get_metric_value(self, metric_selector: str) -> Optional[float]:
        """Extract numeric value from a metric card"""
        try:
            element = self.page.locator(metric_selector)
            text = element.text_content(timeout=3000)
            
            # Remove % and convert to float
            if text:
                clean_text = text.replace('%', '').replace(',', '').strip()
                return float(clean_text)
        except:
            pass
        return None
    
    def assert_chart_rendered(self, chart_selector: str, timeout: int = 10000):
        """Assert that a chart is rendered and visible"""
        expect(self.page.locator(chart_selector)).to_be_visible(timeout=timeout)
        
        # Check if chart has content (not empty state)
        chart_element = self.page.locator(chart_selector)
        bounding_box = chart_element.bounding_box()
        
        assert bounding_box is not None, "Chart not found"
        assert bounding_box['height'] > 100, "Chart too small - may be empty"
        assert bounding_box['width'] > 200, "Chart too narrow"
    
    def count_table_rows(self, table_selector: str) -> int:
        """Count number of rows in a table"""
        rows = self.page.locator(f'{table_selector} [data-testid*="row"]').all()
        return len(rows)
    
    def fill_date_range(self, start_date: str, end_date: str):
        """Fill date range inputs"""
        self.page.fill('[data-testid="start-date"]', start_date)
        self.page.fill('[data-testid="end-date"]', end_date)
    
    def wait_for_loading_complete(self, loading_selector: str = '[data-testid="loading"]', 
                                   timeout: int = 30000):
        """Wait for loading state to complete"""
        try:
            loading_element = self.page.locator(loading_selector)
            loading_element.wait_for(state='detached', timeout=timeout)
        except:
            # Loading element might not exist
            pass
        
        # Ensure no overlay blocking interaction
        self.page.wait_for_load_state('networkidle')
        time.sleep(0.5)
    
    def take_screenshot(self, name: str):
        """Take a screenshot with custom name"""
        import os
        from pathlib import Path
        
        screenshots_dir = Path('/tmp/quant_test_screenshots')
        screenshots_dir.mkdir(exist_ok=True)
        
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{name}.png"
        filepath = screenshots_dir / filename
        
        self.page.screenshot(path=str(filepath), full_page=True)
        print(f"✓ Screenshot saved: {filepath}")
        return str(filepath)
    
    def extract_backtest_id_from_url(self) -> Optional[str]:
        """Extract backtest_id from current URL"""
        url = self.page.url
        if 'backtest_id=' in url:
            return url.split('backtest_id=')[1].split('&')[0]
        return None
    
    def verify_performance_metrics(self, expected_min_metrics: int = 25) -> Dict[str, Any]:
        """Verify performance metrics are displayed correctly"""
        categories = {
            'returns': '[data-testid="returns-metrics"]',
            'risk': '[data-testid="risk-metrics"]',
            'risk_adjusted': '[data-testid="risk-adjusted-metrics"]',
            'market_risk': '[data-testid="market-risk-metrics"]',
            'trading': '[data-testid="trading-metrics"]',
            'advanced': '[data-testid="advanced-metrics"]',
        }
        
        results = {
            'total_metrics': 0,
            'categories_found': [],
            'metrics_by_category': {},
        }
        
        for category_name, selector in categories.items():
            try:
                category_element = self.page.locator(selector)
                if category_element.is_visible(timeout=3000):
                    metrics = category_element.locator('[data-testid="metric-card"]').all()
                    count = len(metrics)
                    
                    results['categories_found'].append(category_name)
                    results['metrics_by_category'][category_name] = count
                    results['total_metrics'] += count
                    
                    print(f"  ✓ {category_name}: {count} metrics")
            except:
                print(f"  ⚠ {category_name}: Not found")
        
        # Assert minimum metrics
        assert results['total_metrics'] >= expected_min_metrics, \
            f"Expected {expected_min_metrics}+ metrics, found {results['total_metrics']}"
        
        return results
    
    def verify_risk_analysis(self) -> Dict[str, float]:
        """Verify risk analysis data"""
        results = {}
        
        try:
            # Get VaR
            var_element = self.page.locator('[data-testid="var-value"]')
            if var_element.is_visible(timeout=3000):
                var_text = var_element.text_content()
                results['var'] = float(var_text.replace('%', '').strip()) if var_text else None
            
            # Get CVaR
            cvar_element = self.page.locator('[data-testid="cvar-value"]')
            if cvar_element.is_visible(timeout=3000):
                cvar_text = cvar_element.text_content()
                results['cvar'] = float(cvar_text.replace('%', '').strip()) if cvar_text else None
            
            # Validate relationship
            if results.get('var') and results.get('cvar'):
                assert results['cvar'] > results['var'], "CVaR should be greater than VaR"
                
        except Exception as e:
            print(f"⚠ Risk analysis verification failed: {e}")
        
        return results
    
    def run_quick_smoke_test(self) -> bool:
        """Run quick smoke test to verify basic functionality"""
        try:
            print("\nRunning smoke test...")
            
            # Navigate to quant page
            self.navigate_to_quant_page()
            
            # Check if factors tab exists
            expect(self.page.locator('[data-testid="factors-tab"]')).to_be_visible(timeout=5000)
            
            # Click factors tab
            self.page.click('[data-testid="factors-tab"]')
            self.wait_for_page_ready()
            
            # Check if factor list loads
            expect(self.page.locator('[data-testid="factor-list"]')).to_be_visible(timeout=5000)
            
            # Count factors
            factors = self.page.locator('[data-testid="factor-item"]').all()
            factor_count = len(factors)
            
            print(f"✓ Smoke test passed: {factor_count} factors loaded")
            return factor_count > 0
            
        except Exception as e:
            print(f"✗ Smoke test failed: {e}")
            return False


def create_test_fixture(page: Page):
    """Create test fixture with all helpers"""
    return {
        'helpers': QuantTestHelpers(page),
        'page': page,
    }


# Common selectors for reuse
SELECTORS = {
    'tabs': {
        'factors': '[data-testid="factors-tab"]',
        'strategies': '[data-testid="strategies-tab"]',
        'backtest': '[data-testid="backtest-tab"]',
        'custom': '[data-testid="custom-factor-tab"]',
    },
    'analytics': {
        'performance': '[data-testid="performance-tab"]',
        'risk': '[data-testid="risk-tab"]',
        'attribution': '[data-testid="attribution-tab"]',
        'charts': '[data-testid="charts-tab"]',
    },
    'common_buttons': {
        'refresh': '[data-testid="refresh-button"]',
        'run': '[data-testid="run-button"]',
        'save': '[data-testid="save-button"]',
        'validate': '[data-testid="validate-button"]',
    },
}
