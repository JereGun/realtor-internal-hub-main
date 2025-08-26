#!/usr/bin/env python
"""
Complete workflow test for email functionality in OwnerReceiptService.
This test verifies the entire email workflow from generation to sending.
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

def test_complete_email_workflow():
    """Test the complete email workflow from receipt generation to sending."""
    try:
        from accounting.services import OwnerReceiptService
        from django.core.exceptions import ValidationError
        
        service = OwnerReceiptService()
        
        print("Testing complete email workflow...")
        
        # Step 1: Create mock objects for the complete workflow
        mock_invoice = create_mock_invoice()
        mock_agent = create_mock_agent()
        
        # Step 2: Test receipt generation
        with patch('accounting.models_invoice.OwnerReceipt') as mock_receipt_class:
            mock_receipt = Mock()
            mock_receipt.pk = 1
            mock_receipt.receipt_number = 'REC-2024-0001'
            mock_receipt.status = 'generated'
            mock_receipt.save = Mock()
            mock_receipt_class.return_value = mock_receipt
            
            # Mock can_generate_receipt
            with patch.object(service, 'can_generate_receipt', return_value=(True, "")):
                with patch.object(service, 'get_receipt_data') as mock_get_data:
                    mock_get_data.return_value = create_mock_receipt_data()
                    
                    receipt = service.generate_receipt(mock_invoice, mock_agent)
                    
                    if receipt:
                        print("✓ Step 1: Receipt generation successful")
                    else:
                        print("✗ Step 1: Receipt generation failed")
                        return False
        
        # Step 3: Test email sending workflow
        mock_receipt = create_mock_receipt()
        
        with patch('accounting.services.render_to_string') as mock_render:
            with patch('accounting.services.EmailMessage') as mock_email_class:
                with patch.object(service, 'generate_pdf') as mock_pdf:
                    
                    # Setup mocks
                    mock_render.return_value = '<html>Email content</html>'
                    mock_pdf.return_value = b'PDF content'
                    mock_email_instance = Mock()
                    mock_email_class.return_value = mock_email_instance
                    
                    # Mock get_receipt_data for email sending
                    with patch.object(service, 'get_receipt_data') as mock_get_data:
                        mock_get_data.return_value = create_mock_receipt_data()
                        
                        result = service.send_receipt_email(mock_receipt)
                        
                        if result:
                            print("✓ Step 2: Email sending successful")
                            
                            # Verify email was created correctly
                            mock_email_class.assert_called_once()
                            call_args = mock_email_class.call_args
                            
                            # Check email parameters
                            if 'subject' in call_args[1] and 'to' in call_args[1]:
                                print("✓ Step 3: Email parameters correct")
                            else:
                                print("✗ Step 3: Email parameters missing")
                                return False
                            
                            # Check PDF attachment
                            mock_email_instance.attach.assert_called_once()
                            print("✓ Step 4: PDF attachment added")
                            
                            # Check email sending
                            mock_email_instance.send.assert_called_once()
                            print("✓ Step 5: Email sent successfully")
                            
                            # Check status update
                            mock_receipt.mark_as_sent.assert_called_once()
                            print("✓ Step 6: Receipt status updated")
                            
                            return True
                        else:
                            print("✗ Step 2: Email sending failed")
                            return False
        
    except Exception as e:
        print(f"✗ Complete workflow test failed: {e}")
        return False

def test_email_error_recovery():
    """Test email error recovery and retry mechanism."""
    try:
        from accounting.services import OwnerReceiptService
        from django.core.exceptions import ValidationError
        
        service = OwnerReceiptService()
        
        print("Testing email error recovery...")
        
        # Create mock receipt in failed state
        mock_receipt = create_mock_receipt()
        mock_receipt.status = 'failed'
        mock_receipt.error_message = 'Previous SMTP error'
        mock_receipt.can_resend.return_value = True
        
        # Test retry mechanism
        with patch.object(service, 'send_receipt_email', return_value=True) as mock_send:
            result = service.resend_receipt_email(mock_receipt)
            
            if result:
                print("✓ Email retry successful")
                
                # Verify status was reset
                mock_receipt.save.assert_called()
                print("✓ Receipt status reset before retry")
                
                # Verify send was called
                mock_send.assert_called_once_with(mock_receipt)
                print("✓ Email resend attempted")
                
                return True
            else:
                print("✗ Email retry failed")
                return False
                
    except Exception as e:
        print(f"✗ Email error recovery test failed: {e}")
        return False

def test_email_validation_scenarios():
    """Test various email validation scenarios."""
    try:
        from accounting.services import OwnerReceiptService
        from django.core.exceptions import ValidationError
        
        service = OwnerReceiptService()
        
        print("Testing email validation scenarios...")
        
        # Test 1: Already sent receipt
        mock_receipt = create_mock_receipt()
        mock_receipt.status = 'sent'
        mock_receipt.can_resend.return_value = False
        
        try:
            service.send_receipt_email(mock_receipt)
            print("✗ Should have prevented sending already sent receipt")
            return False
        except ValidationError as e:
            if "ya fue enviado exitosamente" in str(e):
                print("✓ Correctly prevented resending sent receipt")
            else:
                print(f"✗ Unexpected error message: {e}")
                return False
        
        # Test 2: Cannot resend receipt
        try:
            service.resend_receipt_email(mock_receipt)
            print("✗ Should have prevented resending non-resendable receipt")
            return False
        except ValidationError as e:
            if "no puede ser reenviado" in str(e):
                print("✓ Correctly prevented resending non-resendable receipt")
            else:
                print(f"✗ Unexpected error message: {e}")
                return False
        
        return True
        
    except Exception as e:
        print(f"✗ Email validation test failed: {e}")
        return False

def create_mock_invoice():
    """Create a mock invoice with all required relationships."""
    mock_invoice = Mock()
    mock_invoice.pk = 1
    mock_invoice.number = "INV-2024-001"
    mock_invoice.date = Mock()
    mock_invoice.date.strftime.return_value = "Enero 2024"
    mock_invoice.due_date = Mock()
    mock_invoice.description = "Alquiler Enero 2024"
    mock_invoice.total_amount = Decimal('1000.00')
    mock_invoice.status = 'validated'
    mock_invoice.get_status_display.return_value = "Validada"
    
    # Mock contract
    mock_contract = Mock()
    mock_contract.amount = Decimal('1000.00')
    mock_contract.owner_discount_percentage = Decimal('10.00')
    mock_contract.start_date = Mock()
    mock_contract.end_date = Mock()
    mock_contract.get_status_display.return_value = "Activo"
    
    # Mock property
    mock_property = Mock()
    mock_property.title = "Departamento Centro"
    mock_property.street = "Av. Principal"
    mock_property.number = "123"
    mock_property.neighborhood = "Centro"
    mock_property.property_type.name = "Departamento"
    
    # Mock owner
    mock_owner = Mock()
    mock_owner.get_full_name.return_value = "Maria Garcia"
    mock_owner.first_name = "Maria"
    mock_owner.last_name = "Garcia"
    mock_owner.email = "owner@test.com"
    mock_owner.phone = "123456789"
    
    # Mock agent
    mock_agent = Mock()
    mock_agent.get_full_name.return_value = "Test Agent"
    mock_agent.email = "agent@test.com"
    mock_agent.phone = "987654321"
    mock_agent.license_number = "LIC123"
    
    # Mock customer
    mock_customer = Mock()
    mock_customer.get_full_name.return_value = "John Doe"
    mock_customer.first_name = "John"
    mock_customer.last_name = "Doe"
    mock_customer.email = "tenant@test.com"
    mock_customer.phone = "555123456"
    
    # Wire up relationships
    mock_property.owner = mock_owner
    mock_contract.property = mock_property
    mock_contract.agent = mock_agent
    mock_invoice.contract = mock_contract
    mock_invoice.customer = mock_customer
    
    return mock_invoice

def create_mock_agent():
    """Create a mock agent."""
    mock_agent = Mock()
    mock_agent.get_full_name.return_value = "Test Agent"
    mock_agent.email = "agent@test.com"
    mock_agent.license_number = "LIC123"
    return mock_agent

def create_mock_receipt():
    """Create a mock receipt."""
    mock_receipt = Mock()
    mock_receipt.pk = 1
    mock_receipt.receipt_number = 'REC-2024-0001'
    mock_receipt.email_sent_to = 'owner@test.com'
    mock_receipt.gross_amount = Decimal('1000.00')
    mock_receipt.discount_percentage = Decimal('10.00')
    mock_receipt.discount_amount = Decimal('100.00')
    mock_receipt.net_amount = Decimal('900.00')
    mock_receipt.status = 'generated'
    mock_receipt.generated_at = Mock()
    mock_receipt.generated_by = create_mock_agent()
    mock_receipt.invoice = create_mock_invoice()
    mock_receipt.mark_as_sent = Mock()
    mock_receipt.mark_as_failed = Mock()
    mock_receipt.can_resend.return_value = True
    mock_receipt.save = Mock()
    return mock_receipt

def create_mock_receipt_data():
    """Create mock receipt data."""
    return {
        'invoice': {
            'number': 'INV-2024-001',
            'date': Mock(),
            'due_date': Mock(),
            'description': 'Alquiler Enero 2024',
            'status': 'Validada',
        },
        'contract': {
            'start_date': Mock(),
            'end_date': Mock(),
            'amount': Decimal('1000.00'),
            'status': 'Activo',
        },
        'property': {
            'title': 'Departamento Centro',
            'address': 'Av. Principal 123',
            'property_type': 'Departamento',
            'neighborhood': 'Centro',
        },
        'owner': {
            'name': 'Maria Garcia',
            'email': 'owner@test.com',
            'phone': '123456789',
        },
        'customer': {
            'name': 'John Doe',
            'email': 'tenant@test.com',
            'phone': '555123456',
        },
        'agent': {
            'name': 'Test Agent',
            'email': 'agent@test.com',
            'phone': '987654321',
            'license_number': 'LIC123',
        },
        'financial': {
            'gross_amount': Decimal('1000.00'),
            'discount_percentage': Decimal('10.00'),
            'discount_amount': Decimal('100.00'),
            'net_amount': Decimal('900.00'),
            'net_percentage': Decimal('90.00'),
        },
        'generated_at': Mock(),
    }

def main():
    """Run all complete workflow tests."""
    print("Running Complete Email Workflow Tests")
    print("=" * 50)
    
    tests = [
        test_complete_email_workflow,
        test_email_error_recovery,
        test_email_validation_scenarios,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        print(f"\nRunning {test.__name__}...")
        if test():
            passed += 1
            print(f"✅ {test.__name__} passed")
        else:
            print(f"❌ {test.__name__} failed!")
    
    print("\n" + "=" * 50)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All complete workflow tests passed!")
        return 0
    else:
        print("❌ Some tests failed!")
        return 1

if __name__ == "__main__":
    exit(main())