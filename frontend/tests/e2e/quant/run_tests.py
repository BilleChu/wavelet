#!/usr/bin/env python3
"""
Test runner for quantitative analysis E2E tests.
Manages server lifecycle and executes comprehensive tests.
"""

import subprocess
import sys
import time
import requests
from pathlib import Path
from datetime import datetime


def check_server_health(url: str, timeout: int = 5) -> bool:
    """Check if server is healthy"""
    import requests
    
    try:
        response = requests.get(url, timeout=timeout)
        return response.status_code == 200
    except:
        return False


def wait_for_servers():
    """Wait for both backend and frontend to be ready"""
    print("Waiting for servers to be ready...")
    
    max_retries = 60
    retry_delay = 2
    
    for i in range(max_retries):
        backend_ready = check_server_health('http://localhost:3000/api/health')
        frontend_ready = check_server_health('http://localhost:5173')
        
        if backend_ready and frontend_ready:
            print("✓ Both servers are ready")
            return True
        
        print(f"  Waiting... ({i+1}/{max_retries}) - Backend: {'✓' if backend_ready else '✗'}, Frontend: {'✓' if frontend_ready else '✗'}")
        time.sleep(retry_delay)
    
    print("✗ Timeout waiting for servers")
    return False


def run_tests(test_file: str = None):
    """Run the comprehensive quant tests"""
    
    # Default test file
    if not test_file:
        test_file = str(Path(__file__).parent / 'test_quant_comprehensive.py')
    
    print(f"\nRunning tests: {test_file}")
    
    # Run pytest with verbose output
    cmd = [
        sys.executable, '-m', 'pytest',
        test_file,
        '-v',
        '--tb=short',
        '-s',
    ]
    
    result = subprocess.run(cmd)
    return result.returncode


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Run quant analysis E2E tests')
    parser.add_argument('--test-file', type=str, help='Specific test file to run')
    parser.add_argument('--skip-server-check', action='store_true', help='Skip server health check')
    parser.add_argument('--report', action='store_true', help='Generate HTML report')
    parser.add_argument('--smoke-only', action='store_true', help='Run only smoke tests')
    
    args = parser.parse_args()
    
    print("="*80)
    print("QUANTITATIVE ANALYSIS E2E TEST RUNNER")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    start_time = time.time()
    
    # Check if servers are running
    if not args.skip_server_check:
        if not wait_for_servers():
            print("\nError: Servers not ready. Please start servers first:")
            print("  Backend:  cd backend && uvicorn openfinance.api.main:app --reload")
            print("  Frontend: cd frontend && npm run dev")
            sys.exit(1)
    
    # Check database has data
    print("\nChecking database initialization...")
    
    try:
        response = requests.get('http://localhost:3000/api/quant/health', timeout=5)
        health = response.json()
        factors_count = int(health.get('factors_available', 0))
        
        if factors_count == 0:
            print("⚠ Warning: No factors in database. Tests may fail.")
            print("   Initialize factors by visiting: http://localhost:3000/api/quant/factors/init")
        else:
            print(f"✓ Database ready: {factors_count} factors available")
    except Exception as e:
        print(f"✗ Cannot connect to backend: {e}")
        sys.exit(1)
    
    # Build pytest command
    test_file = args.test_file or str(Path(__file__).parent / 'test_quant_comprehensive.py')
    
    cmd = [
        sys.executable, '-m', 'pytest',
        test_file,
        '-v',
        '--tb=short',
        '-s',
    ]
    
    # Add smoke-only marker if requested
    if args.smoke_only:
        cmd.insert(-1, '-m')
        cmd.insert(-1, 'smoke')
        print("\nRunning: SMOKE TESTS ONLY")
    
    # Run tests
    print(f"\nExecuting: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    
    duration = time.time() - start_time
    
    # Generate report if requested
    if args.report:
        print("\nGenerating reports...")
        from .report_generator import TestReportGenerator
        
        generator = TestReportGenerator()
        generator.set_environment(
            frontend_url='http://localhost:5173',
            backend_url='http://localhost:3000',
            browser='Chromium'
        )
        generator.set_database_status(
            factors=factors_count,
            strategies=0,  # Would need to query API
            stocks=0
        )
        generator.finalize(duration)
        
        generator.generate_json_report()
        generator.generate_html_report()
        generator.print_summary()
    
    # Summary
    print("\n" + "="*80)
    if result.returncode == 0:
        print("✓ ALL TESTS PASSED")
        print(f"Duration: {duration:.1f}s")
    else:
        print(f"✗ TESTS FAILED (exit code: {result.returncode})")
        print(f"Duration: {duration:.1f}s")
        print("\nCheck screenshots at: /tmp/quant_test_failures/")
    print("="*80)
    
    sys.exit(result.returncode)


if __name__ == '__main__':
    main()
