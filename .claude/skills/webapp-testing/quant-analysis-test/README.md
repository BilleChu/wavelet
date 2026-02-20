# Quantitative Analysis Testing Skill

Production-level E2E testing for the quantitative analysis system with real backend database integration.

## What This Tests

✅ **Factor Management**
- Factor discovery and metadata validation
- Historical factor data queries from PostgreSQL
- Custom factor development and validation
- Factor IC/IR performance metrics

✅ **Strategy Development**
- Multi-factor strategy creation
- Signal generation with real-time data
- Stock recommendations and scoring
- Factor weight configuration

✅ **Backtest Execution**
- Full backtest workflow with historical K-line data
- Equity curve tracking
- Trade log persistence
- Performance metric calculation

✅ **Professional Analytics**
- 60+ performance metrics (Returns, Risk, Risk-Adjusted, Market Risk, Trading, Advanced)
- Risk analysis (VaR, CVaR, Stress Testing)
- Attribution analysis (Brinson, Factor, Sector)
- Rolling window analysis
- Monte Carlo simulation

## Quick Start

### Prerequisites

1. **Backend running** on `http://localhost:3000`
2. **Frontend running** on `http://localhost:5173`
3. **Database initialized** with factors and historical data

### Run All Tests

```bash
cd /Users/binzhu/Projects/wavelet
python frontend/tests/e2e/quant/run_tests.py
```

The test runner will:
- ✓ Check server health
- ✓ Verify database has data
- ✓ Execute all test scenarios
- ✓ Generate comprehensive report

## Test Coverage

### 1. Factor Library Validation
```python
# Tests factor discovery from database
test_quant_factor_library(page)
# Expected: 10+ factors displayed with metadata
```

### 2. Factor Data Query
```python
# Tests historical data retrieval
test_factor_data_query(page)
# Expected: 1 year of daily factor data for 600519.SH
```

### 3. Strategy Signals
```python
# Tests signal generation with real data
test_strategy_signals(page)
# Expected: 20+ stock recommendations
```

### 4. Backtest Execution
```python
# Tests complete backtest workflow
test_backtest_execution(page)
# Expected: Valid equity curve, trades, and metrics
```

### 5. Analytics Dashboard
```python
# Tests 60+ professional metrics
test_analytics_dashboard(page, backtest_id)
# Expected: All 6 metric categories displayed
```

### 6. Custom Factor Development
```python
# Tests custom factor lifecycle
test_custom_factor_workflow(page)
# Expected: Valid IC metrics and saved factor
```

## Debug Mode

### Run with Visible Browser
```bash
pytest frontend/tests/e2e/quant/test_quant_comprehensive.py --headed --slowmo=1000
```

### Screenshot on Failure
```bash
pytest frontend/tests/e2e/quant/test_quant_comprehensive.py --screenshot=only-on-failure
```

### Specific Test
```bash
pytest frontend/tests/e2e/quant/test_quant_comprehensive.py::test_analytics_dashboard -v
```

## Production Readiness Checklist

Before deploying to production, verify:

### Database Requirements
- [ ] At least 10 registered factors in `factors` table
- [ ] At least 3 predefined strategies
- [ ] Minimum 1 year of daily K-line data for all stocks
- [ ] Factor calculation results stored in database

### Backend Requirements
- [ ] Health endpoint returns `status: healthy`
- [ ] All analytics API endpoints responding <1s
- [ ] Cache hit rate >85%
- [ ] Thread pool execution working

### Frontend Requirements
- [ ] All pages load without errors
- [ ] Charts render correctly with sampling
- [ ] No TypeScript compilation errors
- [ ] Responsive design works on mobile

### Performance Benchmarks
- [ ] Factor list loading: <500ms
- [ ] Factor data query: <1s for 1 year
- [ ] Strategy signals: <2s
- [ ] Backtest execution: <30s for 1 year
- [ ] Analytics dashboard: <1s (cached)

## Common Issues

### Issue: "No factors available"
**Solution**: Initialize factor registry
```bash
curl http://localhost:3000/api/quant/factors/init
```

### Issue: "Database connection failed"
**Solution**: Check DATABASE_URL in `.env`
```bash
DATABASE_URL=postgresql://user:pass@localhost:5432/openfinance
docker-compose ps  # Verify postgres is running
```

### Issue: "Test timeout"
**Solution**: Increase timeout or reduce data range
```python
# In test file, change:
page.fill('[data-testid="end-date"]', '2023-06-30')  # Use 6 months instead of 1 year
```

## Test Reports

After running tests, check:
- Console output for detailed logs
- `/tmp/test_failure.png` for failure screenshots
- pytest exit code (0 = success)

Example output:
```
================================================================================
QUANTITATIVE ANALYSIS COMPREHENSIVE TEST SUITE
================================================================================

=== Testing Factor Library ===
✓ Found 15 factors in database
✓ Validated factor: Momentum (Category: momentum, Lookback: 20)

=== Testing Factor Data Query ===
✓ Retrieved 252 data points for 600519.SH
✓ First data point: 2023-01-03 = 0.0523

=== Testing Strategy Signals ===
✓ Found 5 strategies in database
✓ Strategy: Momentum Strategy with 3 factors
✓ Generated 25 stock recommendations
✓ Top pick: 600519.SH (Score: 1.85, Rank: 1)

=== Testing Backtest Execution ===
Waiting for backtest to complete...
✓ Backtest Results:
  Total Return: 0.1523
  Sharpe Ratio: 1.85
  Max Drawdown: -0.0823
✓ Executed 47 trades during backtest period

=== Testing Analytics Dashboard ===
Testing Performance Metrics...
  ✓ Returns: 6 metrics
  ✓ Risk: 6 metrics
  ✓ Risk-Adjusted: 5 metrics
  ✓ Market Risk: 4 metrics
  ✓ Trading: 5 metrics
  ✓ Advanced: 3 metrics
✓ Total metrics displayed: 29/60+
  VaR: 0.0234, CVaR: 0.0312
  ✓ Stress test scenarios: 5
  ✓ Factor attribution items: 7
✓ Analytics dashboard fully validated

=== Testing Custom Factor Development ===
✓ Code validation passed
  IC Mean: 0.0523, IC IR: 1.23
✓ Custom factor tested successfully

================================================================================
✓ ALL TESTS PASSED
================================================================================
```

## Integration with CI/CD

Add to your CI pipeline:

```yaml
# .github/workflows/test.yml
name: Quant Analysis Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_DB: openfinance
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
      
      - name: Install dependencies
        run: |
          cd backend && pip install -r requirements.txt
          cd frontend && npm install
      
      - name: Start servers
        run: |
          cd backend && uvicorn openfinance.api.main:app &
          cd frontend && npm run dev &
        shell: bash
      
      - name: Wait for servers
        run: |
          sleep 30
          curl http://localhost:3000/api/health
          curl http://localhost:5173
      
      - name: Run tests
        run: |
          python frontend/tests/e2e/quant/run_tests.py --skip-server-check
      
      - name: Upload screenshots
        if: failure()
        uses: actions/upload-artifact@v3
        with:
          name: test-failures
          path: /tmp/test_failure.png
```

## References

- **Playwright Docs**: https://playwright.dev/python/docs/intro
- **Test Files**: `/frontend/tests/e2e/quant/`
- **Skill Location**: `/.claude/skills/webapp-testing/quant-analysis-test/`
- **Backend API**: `/backend/openfinance/quant/api/`
- **Frontend Pages**: `/frontend/app/quant/`
