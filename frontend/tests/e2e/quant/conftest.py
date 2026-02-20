"""
Pytest fixtures for quantitative analysis E2E tests.
Provides common setup and teardown functionality.
"""

import pytest
from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext
import os
from pathlib import Path


@pytest.fixture(scope="session")
def browser():
    """Create browser instance for all tests"""
    
    with sync_playwright() as p:
        # Launch browser in headless mode by default
        headless = os.getenv('HEADED', 'false').lower() != 'true'
        
        browser = p.chromium.launch(
            headless=headless,
            slow_mo=int(os.getenv('SLOW_MO', '0')),
        )
        
        yield browser
        
        browser.close()


@pytest.fixture(scope="function")
def context(browser: Browser):
    """Create browser context for each test"""
    
    context = browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        ignore_https_errors=True,
        java_script_enabled=True,
    )
    
    yield context
    
    context.close()


@pytest.fixture(scope="function")
def page(context: BrowserContext):
    """Create page for each test"""
    
    page = context.new_page()
    
    # Set default timeout
    page.set_default_timeout(15000)
    
    yield page
    
    # Cleanup: Close page
    page.close()


@pytest.fixture(scope="session")
def base_url():
    """Get base URL from environment or use default"""
    return os.getenv('BASE_URL', 'http://localhost:5173')


@pytest.fixture(scope="session")
def backend_url():
    """Get backend API URL"""
    return os.getenv('BACKEND_URL', 'http://localhost:3000')


@pytest.fixture
def quant_page(page: Page, base_url: str):
    """Navigate to quant page and wait for ready state"""
    
    page.goto(f'{base_url}/quant')
    page.wait_for_load_state('networkidle')
    
    yield page


@pytest.fixture
def screenshot_on_failure(request):
    """Take screenshot on test failure"""
    
    yield
    
    # Check if test failed
    if request.node.rep_call.failed:
        page = request.getfixturevalue('page')
        
        # Create screenshots directory
        screenshots_dir = Path('/tmp/quant_test_failures')
        screenshots_dir.mkdir(exist_ok=True)
        
        # Take screenshot
        filename = f"{request.node.name}_failure.png"
        filepath = screenshots_dir / filename
        page.screenshot(path=str(filepath), full_page=True)
        
        print(f"\n✗ Test failed: {request.node.name}")
        print(f"✓ Screenshot saved: {filepath}")


def pytest_configure(config):
    """Configure pytest hooks"""
    
    # Enable screenshot on failure
    config.option.screenshot = 'only-on-failure'


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Add test report to fixtures"""
    
    outcome = yield
    rep = outcome.get_result()
    
    setattr(item, "rep_" + rep.when, rep)
    
    return rep
