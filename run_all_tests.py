#!/usr/bin/env python3
"""
Test Runner and Report Generator
Author: KiddoTrack-Lite Team
Purpose: Run all unit tests and generate comprehensive reports
"""

import subprocess
import sys
import json
import datetime
from pathlib import Path


def run_tests_with_coverage():
    """Run all tests with coverage and generate reports."""
    
    # Test modules to run
    test_modules = [
        'test_geofence.py',
        'test_simulator.py', 
        'test_logger.py',
        'test_api.py',
        'test_config.py',
        'test_parent_console.py',
        'test_child_simulator.py'
    ]
    
    results = {}
    
    for module in test_modules:
        print(f"\n{'='*60}")
        print(f"Running tests for {module}")
        print('='*60)
        
        # Run pytest with verbose output and JSON report
        cmd = [
            sys.executable, '-m', 'pytest', 
            module, 
            '-v', 
            '--tb=short',
            '--json-report',
            f'--json-report-file=reports/{module}_report.json'
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            results[module] = {
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'success': result.returncode == 0
            }
            
            print(result.stdout)
            if result.stderr:
                print("STDERR:", result.stderr)
                
        except subprocess.TimeoutExpired:
            print(f"Test {module} timed out after 5 minutes")
            results[module] = {
                'returncode': -1,
                'stdout': '',
                'stderr': 'Test timed out',
                'success': False
            }
        except Exception as e:
            print(f"Error running {module}: {e}")
            results[module] = {
                'returncode': -1,
                'stdout': '',
                'stderr': str(e),
                'success': False
            }
    
    return results


def generate_summary_report(results):
    """Generate a summary report of all test results."""
    
    summary = {
        'timestamp': datetime.datetime.now().isoformat(),
        'total_modules': len(results),
        'passed_modules': sum(1 for r in results.values() if r['success']),
        'failed_modules': sum(1 for r in results.values() if not r['success']),
        'details': results
    }
    
    # Create reports directory
    Path('reports').mkdir(exist_ok=True)
    
    # Write summary report
    with open('reports/test_summary.json', 'w') as f:
        json.dump(summary, f, indent=2)
    
    # Generate markdown summary
    markdown_report = f"""# KiddoTrack-Lite Unit Test Summary Report

**Date:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Overall Results
- **Total Test Modules:** {summary['total_modules']}
- **Passed Modules:** {summary['passed_modules']}
- **Failed Modules:** {summary['failed_modules']}
- **Success Rate:** {(summary['passed_modules']/summary['total_modules']*100):.1f}%

## Module Details

"""
    
    for module, result in results.items():
        status = "✅ PASSED" if result['success'] else "❌ FAILED"
        markdown_report += f"### {module}\n"
        markdown_report += f"**Status:** {status}\n"
        markdown_report += f"**Exit Code:** {result['returncode']}\n"
        
        if not result['success'] and result['stderr']:
            markdown_report += f"**Error:** {result['stderr']}\n"
        
        markdown_report += "\n"
    
    with open('reports/test_summary.md', 'w') as f:
        f.write(markdown_report)
    
    return summary


def main():
    """Main function to run all tests and generate reports."""
    print("KiddoTrack-Lite Unit Test Runner")
    print("=" * 50)
    
    # Create reports directory
    Path('reports').mkdir(exist_ok=True)
    
    # Run all tests
    results = run_tests_with_coverage()
    
    # Generate summary
    summary = generate_summary_report(results)
    
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print('='*60)
    print(f"Total Modules: {summary['total_modules']}")
    print(f"Passed: {summary['passed_modules']}")
    print(f"Failed: {summary['failed_modules']}")
    print(f"Success Rate: {(summary['passed_modules']/summary['total_modules']*100):.1f}%")
    
    print(f"\nReports saved to 'reports/' directory")
    
    # Exit with error code if any tests failed
    if summary['failed_modules'] > 0:
        sys.exit(1)
    else:
        print("\n🎉 All tests passed!")
        sys.exit(0)


if __name__ == "__main__":
    main() 