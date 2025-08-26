#!/usr/bin/env python
"""
Integration test for email retry functionality in OwnerReceiptService.
This test verifies the retry mechanism without requiring a full database setup.
"""

import sys
import os
import django
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'real_estate_management.settings')
django.setup()

def test_email_retry_mechanism():
    """Test the email retry mechanism with mock objects."""
    try:
        from accounting.services import OwnerReceiptService
        from django.core.exceptions import ValidationError
        
        service = OwnerReceiptService()
        
        # Create mock receipt that can be resent
        mock_receipt = Mock()
        mock_receipt.can_resend.return_value = True
        mock_receipt.status = 'failed'
        mock_receipt.error_message = 'Previous error'
        mock_receipt.save = Mock()
        
        # Mock successful send_receipt_email
        with patch.object(service, 'send_receipt_email', return_value=True) as mock_send:
            result = service.resend_receipt_email(mock_receipt)
            
            # Verify result
            if result:
                print("✓ Email retry mechanism works correctly")
                
                # Verify that status was reset before retry
                mock_receipt.save.assert_called()
                
                # Verify send_receipt_email was called
                mock_send.assert_called_once_with(mock_receipt)
                
                return True
            else:
                print("✗ Email retry returned False")
                return False
                
    except Exception as e:
        print(f"✗ Failed to test email retry mechanism: {e}")
        return False

def test_email_retry_cannot_resend():
    """Test retry mechanism when receipt cannot be resent."""
    try:
        from accounting.services import OwnerReceiptService
        from django.core.exceptions import ValidationError
        
        service = OwnerReceiptService()
        
        # Create mock receipt that cannot be resent
        mock_receipt = Mock()
        mock_receipt.can_resend.return_value = False
        mock_receipt.status = 'sent'
        
        try:
            service.resend_receipt_email(mock_receipt)
            print("✗ Should have raised ValidationError for non-resendable receipt")
            return False
        except ValidationError as e:
            if "no puede ser reenviado" in str(e):
                print("✓ Correctly prevents resending of non-resendable receipts")
                return True
            else:
                print(f"✗ Unexpected error message: {e}")
                return False
                
    except Exception as e:
        print(f"✗ Failed to test cannot resend scenario: {e}")
        return False

def test_email_error_handling():
    """Test email error handling and status tracking."""
    try:
        from accounting.services import OwnerReceiptService
        from django.core.exceptions import ValidationError
        
        service = OwnerReceiptService()
        
        # Create mock receipt
        mock_receipt = Mock()
        mock_receipt.can_resend.return_value = False
        mock_receipt.status = 'sent'
        mock_receipt.mark_as_sent = Mock()
        mock_receipt.mark_as_failed = Mock()
        
        # Test that already sent receipts cannot be resent
        try:
            service.send_receipt_email(mock_receipt)
            print("✗ Should have raised ValidationError for already sent receipt")
            return False
        except ValidationError as e:
            if "ya fue enviado exitosamente" in str(e):
                print("✓ Correctly prevents resending already sent receipts")
                return True
            else:
                print(f"✗ Unexpected error message: {e}")
                return False
                
    except Exception as e:
        print(f"✗ Failed to test email error handling: {e}")
        return False

def test_email_template_context():
    """Test that email template context is properly prepared."""
    try:
        from accounting.services import OwnerReceiptService
        
        service = OwnerReceiptService()
        
        # Create mock invoice with all required relationships
        mock_invoice = Mock()
        mock_invoice.date.strftime.return_value = "Enero 2024"
        mock_invoice.number = "INV-2024-001"
        
        # Mock contract and property
        mock_contract = Mock()
        mock_property = Mock()
        mock_property.title = "Departamento Centro"
        mock_property.street = "Av. Principal"
        mock_property.number = "123"
        mock_property.neighborhood = "Centro"
        mock_property.property_type.name = "Departamento"
        
        mock_owner = Mock()
        mock_owner.get_full_name.return_value = "Maria Garcia"
        mock_owner.first_name = "Maria"
        mock_owner.last_name = "Garcia"
        mock_owner.email = "owner@test.com"
        mock_owner.phone = "123456789"
        
        mock_property.owner = mock_owner
        mock_contract.property = mock_property
        mock_contract.agent = Mock()
        mock_contract.agent.get_full_name.return_value = "Test Agent"
        mock_contract.start_date = Mock()
        mock_contract.end_date = Mock()
        mock_contract.amount = Decimal('1000.00')
        mock_contract.get_status_display.return_value = "Activo"
        mock_contract.owner_discount_percentage = Decimal('10.00')
        
        mock_invoice.contract = mock_contract
        mock_invoice.customer = Mock()
        mock_invoice.customer.get_full_name.return_value = "John Doe"
        mock_invoice.customer.first_name = "John"
        mock_invoice.customer.last_name = "Doe"
        mock_invoice.customer.email = "tenant@test.com"
        mock_invoice.total_amount = Decimal('1000.00')
        mock_invoice.due_date = Mock()
        mock_invoice.description = "Alquiler Enero 2024"
        mock_invoice.get_status_display.return_value = "Validada"
        
        # Mock can_generate_receipt to return True
        with patch.object(service, 'can_generate_receipt', return_value=(True, "")):
            receipt_data = service.get_receipt_data(mock_invoice)
            
            # Verify that all required data is present
            required_keys = ['invoice', 'contract', 'property', 'owner', 'customer', 'agent', 'financial']
            missing_keys = [key for key in required_keys if key not in receipt_data]
            
            if not missing_keys:
                print("✓ Email template context contains all required data")
                
                # Verify financial calculations
                financial = receipt_data['financial']
                if (financial['gross_amount'] == Decimal('1000.00') and
                    financial['discount_percentage'] == Decimal('10.00') and
                    financial['discount_amount'] == Decimal('100.00') and
                    financial['net_amount'] == Decimal('900.00')):
                    print("✓ Financial calculations are correct")
                    return True
                else:
                    print(f"✗ Incorrect financial calculations: {financial}")
                    return False
            else:
                print(f"✗ Missing required keys in receipt data: {missing_keys}")
                return False
                
    except Exception as e:
        print(f"✗ Failed to test email template context: {e}")
        return False

def main():
    """Run all email retry integration tests."""
    print("Running Email Retry Integration Tests")
    print("=" * 50)
    
    tests = [
        test_email_retry_mechanism,
        test_email_retry_cannot_resend,
        test_email_error_handling,
        test_email_template_context,
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
        print("🎉 All email retry integration tests passed!")
        return 0
    else:
        print("❌ Some tests failed!")
        return 1

if __name__ == "__main__":
    exit(main())