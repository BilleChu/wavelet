"""
Test report generator for quantitative analysis E2E tests.
Generates HTML and JSON reports with detailed metrics.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List


class TestReportGenerator:
    """Generate comprehensive test reports"""
    
    def __init__(self):
        self.results = {
            'test_run': {
                'timestamp': datetime.now().isoformat(),
                'status': 'running',
                'total_tests': 0,
                'passed': 0,
                'failed': 0,
                'skipped': 0,
                'duration_seconds': 0,
            },
            'environment': {
                'frontend_url': '',
                'backend_url': '',
                'browser': '',
            },
            'database_status': {
                'factors_count': 0,
                'strategies_count': 0,
                'stocks_count': 0,
            },
            'test_results': [],
            'performance_metrics': {},
            'issues': [],
        }
    
    def add_test_result(self, test_name: str, status: str, duration: float, 
                       details: Dict[str, Any] = None):
        """Add individual test result"""
        
        result = {
            'name': test_name,
            'status': status,
            'duration_seconds': duration,
            'details': details or {},
            'timestamp': datetime.now().isoformat(),
        }
        
        self.results['test_results'].append(result)
        
        # Update counters
        self.results['test_run']['total_tests'] += 1
        if status == 'passed':
            self.results['test_run']['passed'] += 1
        elif status == 'failed':
            self.results['test_run']['failed'] += 1
        elif status == 'skipped':
            self.results['test_run']['skipped'] += 1
    
    def add_performance_metric(self, metric_name: str, value: float, unit: str):
        """Add performance metric"""
        
        self.results['performance_metrics'][metric_name] = {
            'value': value,
            'unit': unit,
            'timestamp': datetime.now().isoformat(),
        }
    
    def add_issue(self, issue_type: str, description: str, severity: str = 'medium'):
        """Add issue to report"""
        
        self.results['issues'].append({
            'type': issue_type,
            'description': description,
            'severity': severity,
            'timestamp': datetime.now().isoformat(),
        })
    
    def set_environment(self, frontend_url: str, backend_url: str, browser: str):
        """Set environment information"""
        
        self.results['environment'] = {
            'frontend_url': frontend_url,
            'backend_url': backend_url,
            'browser': browser,
        }
    
    def set_database_status(self, factors: int, strategies: int, stocks: int):
        """Set database status"""
        
        self.results['database_status'] = {
            'factors_count': factors,
            'strategies_count': strategies,
            'stocks_count': stocks,
        }
    
    def finalize(self, duration: float):
        """Finalize test run"""
        
        self.results['test_run']['duration_seconds'] = duration
        
        # Determine overall status
        if self.results['test_run']['failed'] > 0:
            self.results['test_run']['status'] = 'failed'
        elif self.results['test_run']['passed'] > 0:
            self.results['test_run']['status'] = 'passed'
        else:
            self.results['test_run']['status'] = 'skipped'
    
    def generate_json_report(self, output_path: str = '/tmp/quant_test_report.json'):
        """Generate JSON report"""
        
        path = Path(output_path)
        path.parent.mkdir(exist_ok=True)
        
        with open(path, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        print(f"\n✓ JSON report saved: {path}")
        return str(path)
    
    def generate_html_report(self, output_path: str = '/tmp/quant_test_report.html'):
        """Generate HTML report"""
        
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Quantitative Analysis Test Report</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            border-bottom: 3px solid #007bff;
            padding-bottom: 10px;
        }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }}
        .stat-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }}
        .stat-card.passed {{
            background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        }}
        .stat-card.failed {{
            background: linear-gradient(135deg, #eb3349 0%, #f45c43 100%);
        }}
        .stat-value {{
            font-size: 36px;
            font-weight: bold;
            margin: 10px 0;
        }}
        .stat-label {{
            font-size: 14px;
            opacity: 0.9;
        }}
        .section {{
            margin: 30px 0;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 8px;
        }}
        .test-result {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 15px;
            margin: 10px 0;
            background: white;
            border-radius: 6px;
            border-left: 4px solid #ddd;
        }}
        .test-result.passed {{
            border-left-color: #38ef7d;
        }}
        .test-result.failed {{
            border-left-color: #f45c43;
        }}
        .badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: bold;
        }}
        .badge.passed {{
            background: #d4edda;
            color: #155724;
        }}
        .badge.failed {{
            background: #f8d7da;
            color: #721c24;
        }}
        .timestamp {{
            color: #666;
            font-size: 12px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background: #f8f9fa;
            font-weight: 600;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Quantitative Analysis Test Report</h1>
        <p class="timestamp">Generated: {self.results['test_run']['timestamp']}</p>
        
        <div class="summary">
            <div class="stat-card">
                <div class="stat-value">{self.results['test_run']['total_tests']}</div>
                <div class="stat-label">Total Tests</div>
            </div>
            <div class="stat-card passed">
                <div class="stat-value">{self.results['test_run']['passed']}</div>
                <div class="stat-label">Passed</div>
            </div>
            <div class="stat-card failed">
                <div class="stat-value">{self.results['test_run']['failed']}</div>
                <div class="stat-label">Failed</div>
            </div>
            <div class="stat-card" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);">
                <div class="stat-value">{self.results['test_run']['duration_seconds']:.1f}s</div>
                <div class="stat-label">Duration</div>
            </div>
        </div>
        
        <div class="section">
            <h2>Environment</h2>
            <table>
                <tr>
                    <th>Frontend URL</th>
                    <td>{self.results['environment']['frontend_url']}</td>
                </tr>
                <tr>
                    <th>Backend URL</th>
                    <td>{self.results['environment']['backend_url']}</td>
                </tr>
                <tr>
                    <th>Browser</th>
                    <td>{self.results['environment']['browser']}</td>
                </tr>
            </table>
        </div>
        
        <div class="section">
            <h2>Database Status</h2>
            <table>
                <tr>
                    <th>Factors</th>
                    <td>{self.results['database_status']['factors_count']}</td>
                </tr>
                <tr>
                    <th>Strategies</th>
                    <td>{self.results['database_status']['strategies_count']}</td>
                </tr>
                <tr>
                    <th>Stocks</th>
                    <td>{self.results['database_status']['stocks_count']}</td>
                </tr>
            </table>
        </div>
        
        <div class="section">
            <h2>Performance Metrics</h2>
            <table>
                <tr>
                    <th>Metric</th>
                    <th>Value</th>
                    <th>Unit</th>
                </tr>
"""
        
        for metric_name, metric_data in self.results['performance_metrics'].items():
            html += f"""
                <tr>
                    <td>{metric_name}</td>
                    <td>{metric_data['value']:.2f}</td>
                    <td>{metric_data['unit']}</td>
                </tr>
"""
        
        html += """
            </table>
        </div>
        
        <div class="section">
            <h2>Test Results</h2>
"""
        
        for result in self.results['test_results']:
            status_class = 'passed' if result['status'] == 'passed' else 'failed'
            badge_class = 'passed' if result['status'] == 'passed' else 'failed'
            
            html += f"""
            <div class="test-result {status_class}">
                <div>
                    <strong>{result['name']}</strong>
                    <span class="badge {badge_class}">{result['status'].upper()}</span>
                </div>
                <div>{result['duration_seconds']:.2f}s</div>
            </div>
"""
        
        if self.results['issues']:
            html += """
        </div>
        
        <div class="section">
            <h2>Issues</h2>
            <table>
                <tr>
                    <th>Type</th>
                    <th>Description</th>
                    <th>Severity</th>
                </tr>
"""
            
            for issue in self.results['issues']:
                html += f"""
                <tr>
                    <td>{issue['type']}</td>
                    <td>{issue['description']}</td>
                    <td>{issue['severity']}</td>
                </tr>
"""
        
        html += """
            </table>
        </div>
    </div>
</body>
</html>
"""
        
        path = Path(output_path)
        path.parent.mkdir(exist_ok=True)
        
        with open(path, 'w') as f:
            f.write(html)
        
        print(f"✓ HTML report saved: {path}")
        return str(path)
    
    def print_summary(self):
        """Print summary to console"""
        
        print("\n" + "="*80)
        print("TEST RUN SUMMARY")
        print("="*80)
        print(f"Status: {self.results['test_run']['status'].upper()}")
        print(f"Total Tests: {self.results['test_run']['total_tests']}")
        print(f"Passed: {self.results['test_run']['passed']} ✓")
        print(f"Failed: {self.results['test_run']['failed']} ✗")
        print(f"Skipped: {self.results['test_run']['skipped']}")
        print(f"Duration: {self.results['test_run']['duration_seconds']:.1f}s")
        print("="*80)


# Convenience function
def generate_reports(results: Dict[str, Any], duration: float) -> TestReportGenerator:
    """Generate all report formats"""
    
    generator = TestReportGenerator()
    
    # Copy results
    generator.results = results
    generator.finalize(duration)
    
    # Generate reports
    generator.generate_json_report()
    generator.generate_html_report()
    generator.print_summary()
    
    return generator
