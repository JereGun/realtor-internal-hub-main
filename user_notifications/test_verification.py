"""
Test verification script for notification system tests.

This script verifies that all test files are properly structured
and can be imported without database access.
"""

import sys
import importlib
import inspect
from pathlib import Path


def verify_test_imports():
    """Verify that all test modules can be imported."""
    test_modules = [
        'user_notifications.test_business_logic',
        'user_notifications.test_integration',
        'user_notifications.test_settings',
        'user_notifications.test_runner'
    ]
    
    print("Verifying test module imports...")
    
    for module_name in test_modules:
        try:
            module = importlib.import_module(module_name)
            print(f"✅ {module_name} - Import successful")
        except ImportError as e:
            print(f"❌ {module_name} - Import failed: {e}")
            return False
        except Exception as e:
            print(f"⚠️  {module_name} - Import warning: {e}")
    
    return True


def verify_test_classes():
    """Verify that test classes are properly structured."""
    try:
        from user_notifications.test_business_logic import (
            ContractExpirationCheckerTest,
            InvoiceOverdueCheckerTest,
            RentIncreaseCheckerTest,
            NotificationServicesTest,
            NotificationLogTest,
            NotificationBatchTest
        )
        
        from user_notifications.test_integration import (
            ContractExpirationWorkflowTest,
            InvoiceOverdueWorkflowTest,
            RentIncreaseWorkflowTest,
            EmailNotificationTest,
            BatchNotificationWorkflowTest
        )
        
        test_classes = [
            ContractExpirationCheckerTest,
            InvoiceOverdueCheckerTest,
            RentIncreaseCheckerTest,
            NotificationServicesTest,
            NotificationLogTest,
            NotificationBatchTest,
            ContractExpirationWorkflowTest,
            InvoiceOverdueWorkflowTest,
            RentIncreaseWorkflowTest,
            EmailNotificationTest,
            BatchNotificationWorkflowTest
        ]
        
        print("\nVerifying test class structure...")
        
        for test_class in test_classes:
            class_name = test_class.__name__
            
            # Check if class has setUp method
            if hasattr(test_class, 'setUp'):
                print(f"✅ {class_name} - Has setUp method")
            else:
                print(f"⚠️  {class_name} - No setUp method")
            
            # Count test methods
            test_methods = [
                method for method in dir(test_class)
                if method.startswith('test_') and callable(getattr(test_class, method))
            ]
            
            print(f"   📊 {class_name} - {len(test_methods)} test methods")
            
            # Check for docstrings
            if test_class.__doc__:
                print(f"   📝 {class_name} - Has class docstring")
            else:
                print(f"   ⚠️  {class_name} - Missing class docstring")
        
        return True
        
    except ImportError as e:
        print(f"❌ Failed to import test classes: {e}")
        return False


def verify_test_methods():
    """Verify test method naming and structure."""
    try:
        from user_notifications.test_business_logic import ContractExpirationCheckerTest
        
        print("\nVerifying test method structure (sample)...")
        
        test_methods = [
            method for method in dir(ContractExpirationCheckerTest)
            if method.startswith('test_')
        ]
        
        for method_name in test_methods[:5]:  # Check first 5 methods
            method = getattr(ContractExpirationCheckerTest, method_name)
            
            if method.__doc__:
                print(f"✅ {method_name} - Has docstring")
            else:
                print(f"⚠️  {method_name} - Missing docstring")
            
            # Check method signature
            sig = inspect.signature(method)
            if 'self' in sig.parameters:
                print(f"✅ {method_name} - Proper method signature")
            else:
                print(f"❌ {method_name} - Invalid method signature")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to verify test methods: {e}")
        return False


def verify_test_utilities():
    """Verify test utility functions and mixins."""
    try:
        from user_notifications.test_settings import (
            NotificationTestMixin,
            get_test_settings,
            with_test_settings,
            with_email_backend,
            with_celery_eager
        )
        
        print("\nVerifying test utilities...")
        
        # Check test settings
        test_settings = get_test_settings()
        required_settings = [
            'DATABASES',
            'EMAIL_BACKEND',
            'CELERY_TASK_ALWAYS_EAGER'
        ]
        
        for setting in required_settings:
            if setting in test_settings:
                print(f"✅ Test setting {setting} - Present")
            else:
                print(f"❌ Test setting {setting} - Missing")
        
        # Check mixin methods
        mixin_methods = [
            'create_test_agent',
            'create_test_customer',
            'create_test_property',
            'create_test_contract',
            'create_test_invoice',
            'assert_notification_created',
            'assert_email_sent'
        ]
        
        for method_name in mixin_methods:
            if hasattr(NotificationTestMixin, method_name):
                print(f"✅ Mixin method {method_name} - Present")
            else:
                print(f"❌ Mixin method {method_name} - Missing")
        
        return True
        
    except ImportError as e:
        print(f"❌ Failed to import test utilities: {e}")
        return False


def count_test_coverage():
    """Count total test methods for coverage estimation."""
    try:
        from user_notifications import test_business_logic, test_integration
        
        print("\nCounting test coverage...")
        
        # Count unit tests
        unit_test_classes = [
            test_business_logic.ContractExpirationCheckerTest,
            test_business_logic.InvoiceOverdueCheckerTest,
            test_business_logic.RentIncreaseCheckerTest,
            test_business_logic.NotificationServicesTest,
            test_business_logic.NotificationLogTest,
            test_business_logic.NotificationBatchTest
        ]
        
        unit_test_count = 0
        for test_class in unit_test_classes:
            methods = [m for m in dir(test_class) if m.startswith('test_')]
            unit_test_count += len(methods)
            print(f"   {test_class.__name__}: {len(methods)} tests")
        
        # Count integration tests
        integration_test_classes = [
            test_integration.ContractExpirationWorkflowTest,
            test_integration.InvoiceOverdueWorkflowTest,
            test_integration.RentIncreaseWorkflowTest,
            test_integration.EmailNotificationTest,
            test_integration.BatchNotificationWorkflowTest
        ]
        
        integration_test_count = 0
        for test_class in integration_test_classes:
            methods = [m for m in dir(test_class) if m.startswith('test_')]
            integration_test_count += len(methods)
            print(f"   {test_class.__name__}: {len(methods)} tests")
        
        total_tests = unit_test_count + integration_test_count
        
        print(f"\n📊 Test Coverage Summary:")
        print(f"   Unit Tests: {unit_test_count}")
        print(f"   Integration Tests: {integration_test_count}")
        print(f"   Total Tests: {total_tests}")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to count test coverage: {e}")
        return False


def main():
    """Main verification function."""
    print("🧪 Notification System Test Verification")
    print("=" * 50)
    
    all_passed = True
    
    # Run verification steps
    steps = [
        ("Import Verification", verify_test_imports),
        ("Class Structure Verification", verify_test_classes),
        ("Method Structure Verification", verify_test_methods),
        ("Utility Verification", verify_test_utilities),
        ("Coverage Counting", count_test_coverage)
    ]
    
    for step_name, step_func in steps:
        print(f"\n🔍 {step_name}")
        print("-" * 30)
        
        try:
            result = step_func()
            if not result:
                all_passed = False
        except Exception as e:
            print(f"❌ {step_name} failed with error: {e}")
            all_passed = False
    
    # Final summary
    print("\n" + "=" * 50)
    if all_passed:
        print("✅ ALL VERIFICATIONS PASSED!")
        print("The notification system test suite is properly structured.")
        print("\nNext steps:")
        print("1. Run unit tests: python user_notifications/test_runner.py --unit-only")
        print("2. Run integration tests: python user_notifications/test_runner.py --integration-only")
        print("3. Run with coverage: python user_notifications/test_runner.py --coverage")
    else:
        print("❌ SOME VERIFICATIONS FAILED!")
        print("Please review the errors above and fix any issues.")
    
    print("=" * 50)
    
    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(main())