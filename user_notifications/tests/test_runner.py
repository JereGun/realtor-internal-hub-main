"""
Test runner for notification system tests.

This module provides utilities for running notification system tests
with proper configuration and reporting.
"""

import os
import sys
import django
from django.conf import settings
from django.test.utils import get_runner
from django.core.management import execute_from_command_line


def setup_test_environment():
    """Set up the test environment with proper Django configuration."""
    
    # Configure Django settings for testing
    if not settings.configured:
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'real_estate_management.settings')
        django.setup()


def run_notification_tests(verbosity=2, pattern='test*.py', failfast=False):
    """
    Run all notification system tests.
    
    Args:
        verbosity (int): Test output verbosity level (0-3)
        pattern (str): Test file pattern to match
        failfast (bool): Stop on first test failure
        
    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    setup_test_environment()
    
    # Get the Django test runner
    TestRunner = get_runner(settings)
    test_runner = TestRunner(
        verbosity=verbosity,
        interactive=False,
        failfast=failfast,
        keepdb=False,
        reverse=False,
        debug_mode=False,
        debug_sql=False,
        parallel=1,
        tags=None,
        exclude_tags=None
    )
    
    # Define test modules to run
    test_modules = [
        'user_notifications.test_business_logic',
        'user_notifications.test_integration',
        'user_notifications.tests',  # Original tests
    ]
    
    # Run the tests
    failures = test_runner.run_tests(test_modules)
    
    return failures


def run_unit_tests_only(verbosity=2):
    """
    Run only unit tests (business logic tests).
    
    Args:
        verbosity (int): Test output verbosity level
        
    Returns:
        int: Exit code
    """
    setup_test_environment()
    
    TestRunner = get_runner(settings)
    test_runner = TestRunner(verbosity=verbosity, interactive=False)
    
    test_modules = ['user_notifications.test_business_logic']
    failures = test_runner.run_tests(test_modules)
    
    return failures


def run_integration_tests_only(verbosity=2):
    """
    Run only integration tests.
    
    Args:
        verbosity (int): Test output verbosity level
        
    Returns:
        int: Exit code
    """
    setup_test_environment()
    
    TestRunner = get_runner(settings)
    test_runner = TestRunner(verbosity=verbosity, interactive=False)
    
    test_modules = ['user_notifications.test_integration']
    failures = test_runner.run_tests(test_modules)
    
    return failures


def run_specific_test_class(test_class_path, verbosity=2):
    """
    Run a specific test class.
    
    Args:
        test_class_path (str): Full path to test class (e.g., 'user_notifications.test_business_logic.ContractExpirationCheckerTest')
        verbosity (int): Test output verbosity level
        
    Returns:
        int: Exit code
    """
    setup_test_environment()
    
    TestRunner = get_runner(settings)
    test_runner = TestRunner(verbosity=verbosity, interactive=False)
    
    failures = test_runner.run_tests([test_class_path])
    
    return failures


def run_with_coverage():
    """
    Run tests with coverage reporting.
    
    Returns:
        int: Exit code
    """
    try:
        import coverage
    except ImportError:
        print("Coverage.py not installed. Install with: pip install coverage")
        return 1
    
    # Start coverage
    cov = coverage.Coverage(
        source=['user_notifications'],
        omit=[
            '*/migrations/*',
            '*/test*.py',
            '*/venv/*',
            '*/virtualenv/*',
        ]
    )
    cov.start()
    
    # Run tests
    failures = run_notification_tests(verbosity=1)
    
    # Stop coverage and generate report
    cov.stop()
    cov.save()
    
    print("\n" + "="*50)
    print("COVERAGE REPORT")
    print("="*50)
    cov.report()
    
    # Generate HTML report
    try:
        cov.html_report(directory='htmlcov')
        print(f"\nHTML coverage report generated in 'htmlcov' directory")
    except Exception as e:
        print(f"Could not generate HTML report: {e}")
    
    return failures


def main():
    """Main entry point for test runner."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Run notification system tests')
    parser.add_argument(
        '--unit-only',
        action='store_true',
        help='Run only unit tests'
    )
    parser.add_argument(
        '--integration-only',
        action='store_true',
        help='Run only integration tests'
    )
    parser.add_argument(
        '--coverage',
        action='store_true',
        help='Run tests with coverage reporting'
    )
    parser.add_argument(
        '--verbosity',
        type=int,
        default=2,
        choices=[0, 1, 2, 3],
        help='Test output verbosity level'
    )
    parser.add_argument(
        '--failfast',
        action='store_true',
        help='Stop on first test failure'
    )
    parser.add_argument(
        '--test-class',
        type=str,
        help='Run specific test class (e.g., user_notifications.test_business_logic.ContractExpirationCheckerTest)'
    )
    
    args = parser.parse_args()
    
    # Set up environment
    setup_test_environment()
    
    # Run appropriate tests based on arguments
    if args.coverage:
        exit_code = run_with_coverage()
    elif args.unit_only:
        exit_code = run_unit_tests_only(args.verbosity)
    elif args.integration_only:
        exit_code = run_integration_tests_only(args.verbosity)
    elif args.test_class:
        exit_code = run_specific_test_class(args.test_class, args.verbosity)
    else:
        exit_code = run_notification_tests(
            verbosity=args.verbosity,
            failfast=args.failfast
        )
    
    # Print summary
    if exit_code == 0:
        print("\n" + "="*50)
        print("ALL TESTS PASSED!")
        print("="*50)
    else:
        print("\n" + "="*50)
        print(f"TESTS FAILED: {exit_code} failures")
        print("="*50)
    
    sys.exit(exit_code)


if __name__ == '__main__':
    main()