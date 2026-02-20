#!/usr/bin/env python3
"""
Quick validation script to verify test setup is complete.
Run this before executing tests to ensure everything is ready.
"""

import sys
from pathlib import Path


def check_file_exists(filepath: str, description: str) -> bool:
    """Check if file exists"""
    path = Path(filepath)
    if path.exists():
        print(f"✓ {description}: {path.name}")
        return True
    else:
        print(f"✗ {description} missing: {path.name}")
        return False


def validate_test_setup():
    """Validate complete test setup"""
    
    print("="*80)
    print("QUANTITATIVE ANALYSIS TEST SETUP VALIDATION")
    print("="*80)
    
    checks = []
    
    # Check test files
    print("\n1. Checking test files...")
    checks.append(check_file_exists(
        'frontend/tests/e2e/quant/conftest.py',
        'Pytest fixtures'
    ))
    checks.append(check_file_exists(
        'frontend/tests/e2e/quant/test_helpers.py',
        'Test helpers'
    ))
    checks.append(check_file_exists(
        'frontend/tests/e2e/quant/test_smoke.py',
        'Smoke tests'
    ))
    checks.append(check_file_exists(
        'frontend/tests/e2e/quant/test_quant_comprehensive.py',
        'Comprehensive tests'
    ))
    checks.append(check_file_exists(
        'frontend/tests/e2e/quant/test_example_workflow.py',
        'Workflow example'
    ))
    checks.append(check_file_exists(
        'frontend/tests/e2e/quant/report_generator.py',
        'Report generator'
    ))
    checks.append(check_file_exists(
        'frontend/tests/e2e/quant/run_tests.py',
        'Test runner'
    ))
    
    # Check configuration
    print("\n2. Checking configuration...")
    checks.append(check_file_exists(
        'pytest.ini',
        'Pytest config'
    ))
    
    # Check skill documentation
    print("\n3. Checking skill documentation...")
    checks.append(check_file_exists(
        '.claude/skills/webapp-testing/quant-analysis-test/SKILL.md',
        'Skill main doc'
    ))
    checks.append(check_file_exists(
        '.claude/skills/webapp-testing/quant-analysis-test/README.md',
        'Skill README'
    ))
    
    # Check imports
    print("\n4. Validating Python imports...")
    try:
        from playwright.sync_api import sync_playwright
        print("✓ Playwright installed")
        checks.append(True)
    except ImportError:
        print("✗ Playwright not installed - run: pip install playwright")
        checks.append(False)
    
    try:
        import pytest
        print("✓ Pytest installed")
        checks.append(True)
    except ImportError:
        print("✗ Pytest not installed - run: pip install pytest")
        checks.append(False)
    
    try:
        import requests
        print("✓ Requests installed")
        checks.append(True)
    except ImportError:
        print("✗ Requests not installed - run: pip install requests")
        checks.append(False)
    
    # Summary
    print("\n" + "="*80)
    passed = sum(checks)
    total = len(checks)
    
    if all(checks):
        print(f"✓ ALL CHECKS PASSED ({passed}/{total})")
        print("\nTest setup is complete and ready!")
        print("\nTo run tests:")
        print("  python frontend/tests/e2e/quant/run_tests.py")
    else:
        print(f"✗ SOME CHECKS FAILED ({passed}/{total})")
        print("\nPlease fix the issues above before running tests.")
        sys.exit(1)
    
    print("="*80)


if __name__ == '__main__':
    validate_test_setup()
