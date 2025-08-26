#!/usr/bin/env python
"""
Simple integration test for OwnerReceiptService without database.
This test verifies that the service can be imported and initialized correctly.
"""

import sys
import os
import django
from unittest.mock import Mock, patch

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'real_estate_management.settings')
django.setup()

def test_service_import():
    """Test that OwnerReceiptService can be imported."""
    try:
        from accounting.services import OwnerReceiptService
        print("✓ OwnerReceiptService imported successfully")
        return True
    except ImportError as e:
        print(f"✗ Failed to import OwnerReceiptService: {e}")
        return False

def test_service_initialization():
    """Test that OwnerReceiptService can be initialized."""
    try:
        from accounting.services import OwnerReceiptService
        service = OwnerReceiptService()
        print("✓ OwnerReceiptService initialized successfully")
        print(f"  - Service type: {type(service).__name__}")
        print(f"  - Has logger: {hasattr(service, 'logger')}")
        return True
    except Exception as e:
        print(f"✗ Failed to initialize OwnerReceiptService: {e}")
        return False

def test_service_methods():
    """Test that OwnerReceiptService has all required methods."""
    try:
        from accounting.services import OwnerReceiptService
        service = OwnerReceiptService()
        
        required_methods = [
            'can_generate_receipt',
            'get_receipt_data',
            'generate_receipt',
            'generate_pdf',
            'send_receipt_email',
            'resend_receipt_email'
        ]
        
        missing_methods = []
        for method_name in required_methods:
            if not hasattr(service, method_name):
                missing_methods.append(method_name)
            elif not callable(getattr(service, method_name)):
                missing_methods.append(f"{method_name} (not callable)")
        
        if missing_methods:
            print(f"✗ Missing methods: {', '.join(missing_methods)}")
            return False
        else:
            print("✓ All required methods present")
            for method_name in required_methods:
                print(f"  - {method_name}: ✓")
            return True
            
    except Exception as e:
        print(f"✗ Failed to check service methods: {e}")
        return False

def test_can_generate_receipt_validation():
    """Test can_generate_receipt method with mock data."""
    try:
        from accounting.services import OwnerReceiptService
        service = OwnerReceiptService()
        
        # Test with None invoice
        can_generate, error_msg = service.can_generate_receipt(None)
        if not can_generate and "no existe" in error_msg:
            print("✓ can_generate_receipt correctly validates None invoice")
        else:
            print(f"✗ Unexpected result for None invoice: {can_generate}, {error_msg}")
            return False
        
        # Test with mock invalid invoice
        mock_invoice = Mock()
        mock_invoice.status = 'draft'
        mock_invoice.get_status_display.return_value = 'Borrador'
        
        can_generate, error_msg = service.can_generate_receipt(mock_invoice)
        if not can_generate and "validada" in error_msg:
            print("✓ can_generate_receipt correctly validates invoice status")
        else:
            print(f"✗ Unexpected result for draft invoice: {can_generate}, {error_msg}")
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ Failed to test can_generate_receipt: {e}")
        return False

def main():
    """Run all integration tests."""
    print("Running OwnerReceiptService Integration Tests")
    print("=" * 50)
    
    tests = [
        test_service_import,
        test_service_initialization,
        test_service_methods,
        test_can_generate_receipt_validation,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        print(f"\nRunning {test.__name__}...")
        if test():
            passed += 1
        else:
            print(f"Test {test.__name__} failed!")
    
    print("\n" + "=" * 50)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All integration tests passed!")
        return 0
    else:
        print("❌ Some tests failed!")
        return 1

if __name__ == "__main__":
    exit(main())