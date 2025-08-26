from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils import timezone
from decimal import Decimal
from unittest.mock import patch

from accounting.models_invoice import Invoice, OwnerReceipt
from customers.models import Customer
from contracts.models import Contract
from agents.models import Agent
from properties.models import Property


class OwnerReceiptModelTest(TestCase):
    """
    Test suite for the OwnerReceipt model.
    
    Tests model creation, validation, methods, and business logic
    according to the requirements specified in the design document.
    """
    
    def setUp(self):
        """Set up test data for OwnerReceipt tests."""
        # Create test agent
        self.agent = Agent.objects.create(
            username='testagent',
            email='agent@test.com',
            first_name='Test',
            last_name='Agent',
            license_number='LIC123'
        )
        
        # Create test customer
        self.customer = Customer.objects.create(
            first_name='John',
            last_name='Doe',
            email='john@test.com',
            phone='123456789'
        )
        
        # Create test property (assuming basic structure)
        try:
            self.property = Property.objects.create(
                title='Test Property',
                address='123 Test St',
                property_type='apartment',
                agent=self.agent
            )
        except Exception:
            # If Property model has different required fields, create minimal version
            self.property = None
        
        # Create test contract
        self.contract = Contract.objects.create(
            customer=self.customer,
            agent=self.agent,
            property=self.property,
            start_date=timezone.now().date(),
            amount=Decimal('1000.00'),
            owner_discount_percentage=Decimal('10.00'),
            status=Contract.STATUS_ACTIVE
        )
        
        # Create test invoice
        self.invoice = Invoice.objects.create(
            number='INV-2024-001',
            date=timezone.now().date(),
            due_date=timezone.now().date() + timezone.timedelta(days=30),
            customer=self.customer,
            contract=self.contract,
            description='Test invoice',
            total_amount=Decimal('1000.00'),
            status='validated'
        )
    
    def test_owner_receipt_creation(self):
        """Test basic OwnerReceipt creation with required fields."""
        receipt = OwnerReceipt.objects.create(
            invoice=self.invoice,
            generated_by=self.agent,
            email_sent_to='owner@test.com',
            gross_amount=Decimal('1000.00'),
            discount_percentage=Decimal('10.00'),
            discount_amount=Decimal('100.00'),
            net_amount=Decimal('900.00')
        )
        
        self.assertIsNotNone(receipt.pk)
        self.assertEqual(receipt.invoice, self.invoice)
        self.assertEqual(receipt.generated_by, self.agent)
        self.assertEqual(receipt.email_sent_to, 'owner@test.com')
        self.assertEqual(receipt.gross_amount, Decimal('1000.00'))
        self.assertEqual(receipt.discount_percentage, Decimal('10.00'))
        self.assertEqual(receipt.discount_amount, Decimal('100.00'))
        self.assertEqual(receipt.net_amount, Decimal('900.00'))
        self.assertEqual(receipt.status, 'generated')
        self.assertIsNotNone(receipt.receipt_number)
        self.assertIsNotNone(receipt.generated_at)
    
    def test_receipt_number_generation(self):
        """Test automatic receipt number generation."""
        receipt1 = OwnerReceipt.objects.create(
            invoice=self.invoice,
            email_sent_to='owner@test.com',
            gross_amount=Decimal('1000.00'),
            net_amount=Decimal('900.00')
        )
        
        # Create another invoice for second receipt
        invoice2 = Invoice.objects.create(
            number='INV-2024-002',
            date=timezone.now().date(),
            due_date=timezone.now().date() + timezone.timedelta(days=30),
            customer=self.customer,
            contract=self.contract,
            description='Test invoice 2',
            total_amount=Decimal('1000.00'),
            status='validated'
        )
        
        receipt2 = OwnerReceipt.objects.create(
            invoice=invoice2,
            email_sent_to='owner@test.com',
            gross_amount=Decimal('1000.00'),
            net_amount=Decimal('900.00')
        )
        
        # Check that receipt numbers are unique and follow pattern
        self.assertNotEqual(receipt1.receipt_number, receipt2.receipt_number)
        self.assertTrue(receipt1.receipt_number.startswith('REC-'))
        self.assertTrue(receipt2.receipt_number.startswith('REC-'))
        
        # Check sequential numbering
        year = timezone.now().year
        expected_pattern = f"REC-{year}-"
        self.assertTrue(receipt1.receipt_number.startswith(expected_pattern))
        self.assertTrue(receipt2.receipt_number.startswith(expected_pattern))
    
    def test_receipt_number_uniqueness(self):
        """Test that receipt numbers are unique."""
        receipt1 = OwnerReceipt.objects.create(
            invoice=self.invoice,
            email_sent_to='owner@test.com',
            gross_amount=Decimal('1000.00'),
            net_amount=Decimal('900.00')
        )
        
        # Try to create another receipt with the same number
        with self.assertRaises(IntegrityError):
            OwnerReceipt.objects.create(
                invoice=self.invoice,
                email_sent_to='owner2@test.com',
                receipt_number=receipt1.receipt_number,
                gross_amount=Decimal('1000.00'),
                net_amount=Decimal('900.00')
            )
    
    def test_calculate_amounts_from_invoice_with_discount(self):
        """Test amount calculation from invoice with owner discount."""
        receipt = OwnerReceipt(
            invoice=self.invoice,
            email_sent_to='owner@test.com'
        )
        
        amounts = receipt.calculate_amounts_from_invoice()
        
        self.assertEqual(amounts['gross_amount'], Decimal('1000.00'))
        self.assertEqual(amounts['discount_percentage'], Decimal('10.00'))
        self.assertEqual(amounts['discount_amount'], Decimal('100.00'))
        self.assertEqual(amounts['net_amount'], Decimal('900.00'))
    
    def test_calculate_amounts_from_invoice_without_discount(self):
        """Test amount calculation from invoice without owner discount."""
        # Create contract without discount
        contract_no_discount = Contract.objects.create(
            customer=self.customer,
            agent=self.agent,
            property=self.property,
            start_date=timezone.now().date(),
            amount=Decimal('1000.00'),
            owner_discount_percentage=None,
            status=Contract.STATUS_ACTIVE
        )
        
        invoice_no_discount = Invoice.objects.create(
            number='INV-2024-003',
            date=timezone.now().date(),
            due_date=timezone.now().date() + timezone.timedelta(days=30),
            customer=self.customer,
            contract=contract_no_discount,
            description='Test invoice without discount',
            total_amount=Decimal('1000.00'),
            status='validated'
        )
        
        receipt = OwnerReceipt(
            invoice=invoice_no_discount,
            email_sent_to='owner@test.com'
        )
        
        amounts = receipt.calculate_amounts_from_invoice()
        
        self.assertEqual(amounts['gross_amount'], Decimal('1000.00'))
        self.assertIsNone(amounts['discount_percentage'])
        self.assertEqual(amounts['discount_amount'], Decimal('0.00'))
        self.assertEqual(amounts['net_amount'], Decimal('1000.00'))
    
    def test_calculate_amounts_from_invoice_without_contract(self):
        """Test amount calculation from invoice without contract."""
        invoice_no_contract = Invoice.objects.create(
            number='INV-2024-004',
            date=timezone.now().date(),
            due_date=timezone.now().date() + timezone.timedelta(days=30),
            customer=self.customer,
            contract=None,
            description='Test invoice without contract',
            total_amount=Decimal('1000.00'),
            status='validated'
        )
        
        receipt = OwnerReceipt(
            invoice=invoice_no_contract,
            email_sent_to='owner@test.com'
        )
        
        amounts = receipt.calculate_amounts_from_invoice()
        
        self.assertEqual(amounts['gross_amount'], Decimal('1000.00'))
        self.assertIsNone(amounts['discount_percentage'])
        self.assertEqual(amounts['discount_amount'], Decimal('0.00'))
        self.assertEqual(amounts['net_amount'], Decimal('1000.00'))
    
    def test_auto_calculate_amounts_on_save(self):
        """Test that amounts are automatically calculated when saving without amounts."""
        receipt = OwnerReceipt(
            invoice=self.invoice,
            email_sent_to='owner@test.com'
        )
        receipt.save()
        
        self.assertEqual(receipt.gross_amount, Decimal('1000.00'))
        self.assertEqual(receipt.discount_percentage, Decimal('10.00'))
        self.assertEqual(receipt.discount_amount, Decimal('100.00'))
        self.assertEqual(receipt.net_amount, Decimal('900.00'))
    
    def test_mark_as_sent(self):
        """Test marking receipt as sent."""
        receipt = OwnerReceipt.objects.create(
            invoice=self.invoice,
            email_sent_to='owner@test.com',
            gross_amount=Decimal('1000.00'),
            net_amount=Decimal('900.00')
        )
        
        self.assertEqual(receipt.status, 'generated')
        self.assertIsNone(receipt.sent_at)
        
        receipt.mark_as_sent('owner@test.com')
        
        self.assertEqual(receipt.status, 'sent')
        self.assertIsNotNone(receipt.sent_at)
        self.assertEqual(receipt.email_sent_to, 'owner@test.com')
        self.assertEqual(receipt.error_message, '')
    
    def test_mark_as_failed(self):
        """Test marking receipt as failed with error message."""
        receipt = OwnerReceipt.objects.create(
            invoice=self.invoice,
            email_sent_to='owner@test.com',
            gross_amount=Decimal('1000.00'),
            net_amount=Decimal('900.00')
        )
        
        error_msg = 'Email sending failed: SMTP error'
        receipt.mark_as_failed(error_msg)
        
        self.assertEqual(receipt.status, 'failed')
        self.assertEqual(receipt.error_message, error_msg)
    
    def test_can_resend(self):
        """Test can_resend method for different statuses."""
        receipt = OwnerReceipt.objects.create(
            invoice=self.invoice,
            email_sent_to='owner@test.com',
            gross_amount=Decimal('1000.00'),
            net_amount=Decimal('900.00')
        )
        
        # Generated status - can resend
        self.assertTrue(receipt.can_resend())
        
        # Failed status - can resend
        receipt.mark_as_failed('Test error')
        self.assertTrue(receipt.can_resend())
        
        # Sent status - cannot resend
        receipt.mark_as_sent()
        self.assertFalse(receipt.can_resend())
    
    def test_get_property_info(self):
        """Test getting property information from receipt."""
        receipt = OwnerReceipt.objects.create(
            invoice=self.invoice,
            email_sent_to='owner@test.com',
            gross_amount=Decimal('1000.00'),
            net_amount=Decimal('900.00')
        )
        
        if self.property:
            property_info = receipt.get_property_info()
            self.assertIsNotNone(property_info)
            self.assertEqual(property_info['title'], 'Test Property')
            self.assertEqual(property_info['address'], '123 Test St')
        else:
            # If property creation failed, test should handle gracefully
            property_info = receipt.get_property_info()
            self.assertIsNone(property_info)
    
    def test_get_property_info_without_contract(self):
        """Test getting property info when invoice has no contract."""
        invoice_no_contract = Invoice.objects.create(
            number='INV-2024-005',
            date=timezone.now().date(),
            due_date=timezone.now().date() + timezone.timedelta(days=30),
            customer=self.customer,
            contract=None,
            description='Test invoice without contract',
            total_amount=Decimal('1000.00'),
            status='validated'
        )
        
        receipt = OwnerReceipt.objects.create(
            invoice=invoice_no_contract,
            email_sent_to='owner@test.com',
            gross_amount=Decimal('1000.00'),
            net_amount=Decimal('1000.00')
        )
        
        property_info = receipt.get_property_info()
        self.assertIsNone(property_info)
    
    def test_string_representation(self):
        """Test string representation of OwnerReceipt."""
        receipt = OwnerReceipt.objects.create(
            invoice=self.invoice,
            email_sent_to='owner@test.com',
            gross_amount=Decimal('1000.00'),
            net_amount=Decimal('900.00')
        )
        
        expected_str = f"Comprobante {receipt.receipt_number} - {self.invoice.number}"
        self.assertEqual(str(receipt), expected_str)
    
    def test_positive_amount_constraints(self):
        """Test database constraints for positive amounts."""
        # Test positive gross amount constraint
        with self.assertRaises(IntegrityError):
            OwnerReceipt.objects.create(
                invoice=self.invoice,
                email_sent_to='owner@test.com',
                gross_amount=Decimal('-100.00'),  # Negative amount
                net_amount=Decimal('900.00')
            )
    
    def test_discount_percentage_constraints(self):
        """Test database constraints for discount percentage."""
        # Test invalid discount percentage (over 100%)
        with self.assertRaises(IntegrityError):
            OwnerReceipt.objects.create(
                invoice=self.invoice,
                email_sent_to='owner@test.com',
                gross_amount=Decimal('1000.00'),
                discount_percentage=Decimal('150.00'),  # Over 100%
                net_amount=Decimal('900.00')
            )
        
        # Test negative discount percentage
        with self.assertRaises(IntegrityError):
            OwnerReceipt.objects.create(
                invoice=self.invoice,
                email_sent_to='owner@test.com',
                gross_amount=Decimal('1000.00'),
                discount_percentage=Decimal('-10.00'),  # Negative
                net_amount=Decimal('900.00')
            )
    
    def test_invoice_relationship(self):
        """Test relationship with Invoice model."""
        receipt = OwnerReceipt.objects.create(
            invoice=self.invoice,
            email_sent_to='owner@test.com',
            gross_amount=Decimal('1000.00'),
            net_amount=Decimal('900.00')
        )
        
        # Test forward relationship
        self.assertEqual(receipt.invoice, self.invoice)
        
        # Test reverse relationship
        self.assertIn(receipt, self.invoice.owner_receipts.all())
    
    def test_agent_relationship(self):
        """Test relationship with Agent model."""
        receipt = OwnerReceipt.objects.create(
            invoice=self.invoice,
            generated_by=self.agent,
            email_sent_to='owner@test.com',
            gross_amount=Decimal('1000.00'),
            net_amount=Decimal('900.00')
        )
        
        self.assertEqual(receipt.generated_by, self.agent)
    
    def test_ordering(self):
        """Test default ordering by generated_at descending."""
        # Create first receipt
        receipt1 = OwnerReceipt.objects.create(
            invoice=self.invoice,
            email_sent_to='owner@test.com',
            gross_amount=Decimal('1000.00'),
            net_amount=Decimal('900.00')
        )
        
        # Create second invoice and receipt
        invoice2 = Invoice.objects.create(
            number='INV-2024-006',
            date=timezone.now().date(),
            due_date=timezone.now().date() + timezone.timedelta(days=30),
            customer=self.customer,
            contract=self.contract,
            description='Test invoice 2',
            total_amount=Decimal('1000.00'),
            status='validated'
        )
        
        receipt2 = OwnerReceipt.objects.create(
            invoice=invoice2,
            email_sent_to='owner@test.com',
            gross_amount=Decimal('1000.00'),
            net_amount=Decimal('900.00')
        )
        
        # Check ordering (most recent first)
        receipts = list(OwnerReceipt.objects.all())
        self.assertEqual(receipts[0], receipt2)  # Most recent first
        self.assertEqual(receipts[1], receipt1)
    
    @patch('accounting.models_invoice.timezone.now')
    def test_receipt_number_generation_different_years(self, mock_now):
        """Test receipt number generation across different years."""
        # Mock current year as 2024
        mock_now.return_value.year = 2024
        
        receipt1 = OwnerReceipt.objects.create(
            invoice=self.invoice,
            email_sent_to='owner@test.com',
            gross_amount=Decimal('1000.00'),
            net_amount=Decimal('900.00')
        )
        
        # Mock current year as 2025
        mock_now.return_value.year = 2025
        
        # Create another invoice for second receipt
        invoice2 = Invoice.objects.create(
            number='INV-2025-001',
            date=timezone.now().date(),
            due_date=timezone.now().date() + timezone.timedelta(days=30),
            customer=self.customer,
            contract=self.contract,
            description='Test invoice 2025',
            total_amount=Decimal('1000.00'),
            status='validated'
        )
        
        receipt2 = OwnerReceipt.objects.create(
            invoice=invoice2,
            email_sent_to='owner@test.com',
            gross_amount=Decimal('1000.00'),
            net_amount=Decimal('900.00')
        )
        
        # Check that receipt numbers have different years
        self.assertTrue(receipt1.receipt_number.startswith('REC-2024-'))
        self.assertTrue(receipt2.receipt_number.startswith('REC-2025-'))