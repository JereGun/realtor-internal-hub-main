# -*- coding: utf-8 -*-
"""
Tests for owner receipt error handling and validation.

This module tests all error scenarios and validation logic for the owner receipt system,
ensuring robust error handling and user-friendly error messages.
"""

from django.test import TestCase, override_settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core import mail
from unittest.mock import patch, Mock, MagicMock
from decimal import Decimal

from accounting.models_invoice import Invoice, OwnerReceipt
from accounting.services import (
    OwnerReceiptService, 
    OwnerReceiptValidationError, 
    OwnerReceiptEmailError, 
    OwnerReceiptPDFError
)
from accounting.validators import OwnerReceiptValidator, validate_owner_receipt_generation
from contracts.models import Contract
from properties.models import Property
from customers.models import Customer
from agents.models import Agent


class OwnerReceiptValidationTests(TestCase):
    """Test validation logic for owner receipts."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.agent = Agent.objects.create(
            user=self.user,
            license_number='12345',
            phone='123-456-7890'
        )
        
        self.customer = Customer.objects.create(
            first_name='John',
            last_name='Doe',
            email='john@example.com',
            phone='123-456-7890'
        )
        
        self.owner = Customer.objects.create(
            first_name='Jane',
            last_name='Smith',
            email='jane@example.com',
            phone='123-456-7891'
        )
        
        self.property = Property.objects.create(
            title='Test Property',
            street='Test Street',
            number='123',
            owner=self.owner
        )
        
        self.contract = Contract.objects.create(
            property=self.property,
            agent=self.agent,
            amount=Decimal('1000.00'),
            owner_discount_percentage=Decimal('10.00'),
            start_date='2024-01-01',
            end_date='2024-12-31'
        )
        
        self.invoice = Invoice.objects.create(
            customer=self.customer,
            contract=self.contract,
            number='INV-001',
            date='2024-01-15',
            total_amount=Decimal('1000.00'),
            status='validated',
            user=self.user
        )
        
        self.validator = OwnerReceiptValidator()
        self.service = OwnerReceiptService()
    
    def test_validate_invoice_success(self):
        """Test successful invoice validation."""
        is_valid = self.validator.validate_invoice(self.invoice)
        self.assertTrue(is_valid)
        self.assertEqual(len(self.validator.errors), 0)
    
    def test_validate_invoice_no_invoice(self):
        """Test validation with no invoice."""
        is_valid = self.validator.validate_invoice(None)
        self.assertFalse(is_valid)
        self.assertIn("La factura no existe", self.validator.errors)
    
    def test_validate_invoice_invalid_status(self):
        """Test validation with invalid invoice status."""
        self.invoice.status = 'draft'
        is_valid = self.validator.validate_invoice(self.invoice)
        self.assertFalse(is_valid)
        self.assertIn("debe estar validada, enviada o pagada", self.validator.errors[0])
    
    def test_validate_invoice_zero_amount(self):
        """Test validation with zero amount."""
        self.invoice.total_amount = Decimal('0.00')
        is_valid = self.validator.validate_invoice(self.invoice)
        self.assertFalse(is_valid)
        self.assertIn("debe ser mayor a cero", self.validator.errors[0])
    
    def test_validate_contract_success(self):
        """Test successful contract validation."""
        is_valid = self.validator.validate_contract(self.contract)
        self.assertTrue(is_valid)
        self.assertEqual(len(self.validator.errors), 0)
    
    def test_validate_contract_no_contract(self):
        """Test validation with no contract."""
        is_valid = self.validator.validate_contract(None)
        self.assertFalse(is_valid)
        self.assertIn("no tiene contrato asociado", self.validator.errors[0])
    
    def test_validate_contract_no_property(self):
        """Test validation with contract without property."""
        self.contract.property = None
        is_valid = self.validator.validate_contract(self.contract)
        self.assertFalse(is_valid)
        self.assertIn("no tiene propiedad asociada", self.validator.errors[0])
    
    def test_validate_contract_invalid_discount(self):
        """Test validation with invalid discount percentage."""
        self.contract.owner_discount_percentage = Decimal('150.00')
        is_valid = self.validator.validate_contract(self.contract)
        self.assertFalse(is_valid)
        self.assertIn("debe estar entre 0% y 100%", self.validator.errors[0])
    
    def test_validate_owner_success(self):
        """Test successful owner validation."""
        is_valid = self.validator.validate_owner(self.owner)
        self.assertTrue(is_valid)
        self.assertEqual(len(self.validator.errors), 0)
    
    def test_validate_owner_no_email(self):
        """Test validation with owner without email."""
        self.owner.email = ''
        is_valid = self.validator.validate_owner(self.owner)
        self.assertFalse(is_valid)
        self.assertIn("no tiene dirección de email", self.validator.errors[0])
    
    def test_validate_owner_invalid_email(self):
        """Test validation with invalid email format."""
        self.owner.email = 'invalid-email'
        is_valid = self.validator.validate_owner(self.owner)
        self.assertFalse(is_valid)
        self.assertIn("no es válida", self.validator.errors[0])
    
    def test_validate_financial_calculations_success(self):
        """Test successful financial calculations validation."""
        is_valid, calculations = self.validator.validate_financial_calculations(self.invoice, self.contract)
        self.assertTrue(is_valid)
        self.assertEqual(calculations['gross_amount'], Decimal('1000.00'))
        self.assertEqual(calculations['discount_amount'], Decimal('100.00'))
        self.assertEqual(calculations['net_amount'], Decimal('900.00'))
    
    def test_validate_financial_calculations_negative_net(self):
        """Test validation with calculations resulting in negative net amount."""
        self.contract.owner_discount_percentage = Decimal('150.00')
        is_valid, calculations = self.validator.validate_financial_calculations(self.invoice, self.contract)
        self.assertFalse(is_valid)
        self.assertIn("no puede ser negativo", self.validator.errors[0])
    
    def test_validate_complete_success(self):
        """Test complete validation success."""
        is_valid, errors, warnings = self.validator.validate_complete(self.invoice)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
    
    def test_validate_complete_multiple_errors(self):
        """Test complete validation with multiple errors."""
        self.invoice.status = 'draft'
        self.owner.email = ''
        self.contract.owner_discount_percentage = Decimal('150.00')
        
        is_valid, errors, warnings = self.validator.validate_complete(self.invoice)
        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 1)


class OwnerReceiptServiceErrorHandlingTests(TestCase):
    """Test error handling in OwnerReceiptService."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.agent = Agent.objects.create(
            user=self.user,
            license_number='12345',
            phone='123-456-7890'
        )
        
        self.customer = Customer.objects.create(
            first_name='John',
            last_name='Doe',
            email='john@example.com',
            phone='123-456-7890'
        )
        
        self.owner = Customer.objects.create(
            first_name='Jane',
            last_name='Smith',
            email='jane@example.com',
            phone='123-456-7891'
        )
        
        self.property = Property.objects.create(
            title='Test Property',
            street='Test Street',
            number='123',
            owner=self.owner
        )
        
        self.contract = Contract.objects.create(
            property=self.property,
            agent=self.agent,
            amount=Decimal('1000.00'),
            owner_discount_percentage=Decimal('10.00'),
            start_date='2024-01-01',
            end_date='2024-12-31'
        )
        
        self.invoice = Invoice.objects.create(
            customer=self.customer,
            contract=self.contract,
            number='INV-001',
            date='2024-01-15',
            total_amount=Decimal('1000.00'),
            status='validated',
            user=self.user
        )
        
        self.service = OwnerReceiptService()
    
    def test_can_generate_receipt_invalid_invoice(self):
        """Test can_generate_receipt with invalid invoice."""
        self.invoice.status = 'draft'
        can_generate, error_msg = self.service.can_generate_receipt(self.invoice)
        self.assertFalse(can_generate)
        self.assertIn("debe estar validada", error_msg)
    
    def test_generate_receipt_validation_error(self):
        """Test generate_receipt with validation error."""
        self.owner.email = ''
        with self.assertRaises(OwnerReceiptValidationError):
            self.service.generate_receipt(self.invoice, self.user)
    
    def test_generate_receipt_no_user(self):
        """Test generate_receipt with no user."""
        with self.assertRaises(OwnerReceiptValidationError) as cm:
            self.service.generate_receipt(self.invoice, None)
        self.assertIn("Usuario requerido", str(cm.exception))
    
    @patch('accounting.services.render_to_string')
    def test_generate_pdf_template_error(self, mock_render):
        """Test PDF generation with template error."""
        mock_render.side_effect = Exception("Template error")
        
        receipt = OwnerReceipt.objects.create(
            invoice=self.invoice,
            generated_by=self.agent,
            email_sent_to=self.owner.email,
            gross_amount=Decimal('1000.00'),
            net_amount=Decimal('900.00'),
            status='generated'
        )
        
        with self.assertRaises(OwnerReceiptPDFError) as cm:
            self.service.generate_pdf(receipt)
        self.assertIn("Error renderizando el template", str(cm.exception))
    
    @patch('accounting.services.HTML')
    def test_generate_pdf_weasyprint_error(self, mock_html):
        """Test PDF generation with WeasyPrint error."""
        mock_html_instance = Mock()
        mock_html_instance.write_pdf.side_effect = Exception("WeasyPrint error")
        mock_html.return_value = mock_html_instance
        
        receipt = OwnerReceipt.objects.create(
            invoice=self.invoice,
            generated_by=self.agent,
            email_sent_to=self.owner.email,
            gross_amount=Decimal('1000.00'),
            net_amount=Decimal('900.00'),
            status='generated'
        )
        
        with self.assertRaises(OwnerReceiptPDFError) as cm:
            self.service.generate_pdf(receipt)
        self.assertIn("Error en la generación del PDF", str(cm.exception))
    
    @override_settings(DEFAULT_FROM_EMAIL='')
    def test_send_email_no_configuration(self):
        """Test email sending with no configuration."""
        receipt = OwnerReceipt.objects.create(
            invoice=self.invoice,
            generated_by=self.agent,
            email_sent_to=self.owner.email,
            gross_amount=Decimal('1000.00'),
            net_amount=Decimal('900.00'),
            status='generated'
        )
        
        with self.assertRaises(OwnerReceiptEmailError) as cm:
            self.service.send_receipt_email(receipt)
        self.assertIn("Configuración de email", str(cm.exception))
    
    def test_send_email_invalid_recipient(self):
        """Test email sending with invalid recipient."""
        receipt = OwnerReceipt.objects.create(
            invoice=self.invoice,
            generated_by=self.agent,
            email_sent_to='invalid-email',
            gross_amount=Decimal('1000.00'),
            net_amount=Decimal('900.00'),
            status='generated'
        )
        
        with self.assertRaises(OwnerReceiptEmailError) as cm:
            self.service.send_receipt_email(receipt)
        self.assertIn("Dirección de email inválida", str(cm.exception))
    
    @patch('accounting.services.EmailMessage')
    def test_send_email_smtp_error_with_retry(self, mock_email):
        """Test email sending with SMTP error and retry mechanism."""
        mock_email_instance = Mock()
        mock_email_instance.send.side_effect = Exception("SMTP connection error")
        mock_email.return_value = mock_email_instance
        
        receipt = OwnerReceipt.objects.create(
            invoice=self.invoice,
            generated_by=self.agent,
            email_sent_to=self.owner.email,
            gross_amount=Decimal('1000.00'),
            net_amount=Decimal('900.00'),
            status='generated'
        )
        
        # Mock PDF generation to avoid that complexity
        with patch.object(self.service, 'generate_pdf', return_value=b'fake-pdf'):
            with self.assertRaises(OwnerReceiptEmailError) as cm:
                self.service.send_receipt_email(receipt)
            
            # Should have tried multiple times
            self.assertEqual(mock_email_instance.send.call_count, self.service.max_retry_attempts)
            self.assertIn("Error de conexión SMTP", str(cm.exception))
    
    def test_resend_receipt_already_sent(self):
        """Test resending a receipt that was already sent successfully."""
        receipt = OwnerReceipt.objects.create(
            invoice=self.invoice,
            generated_by=self.agent,
            email_sent_to=self.owner.email,
            gross_amount=Decimal('1000.00'),
            net_amount=Decimal('900.00'),
            status='sent'
        )
        
        with self.assertRaises(OwnerReceiptEmailError) as cm:
            self.service.resend_receipt_email(receipt)
        self.assertIn("no puede ser reenviado", str(cm.exception))


class OwnerReceiptLoggingTests(TestCase):
    """Test logging functionality for owner receipts."""
    
    def setUp(self):
        """Set up test data."""
        self.service = OwnerReceiptService()
    
    @patch('accounting.services.logging.getLogger')
    def test_structured_logging(self, mock_get_logger):
        """Test structured logging functionality."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        # Create a new service instance to get the mocked logger
        service = OwnerReceiptService()
        
        # Test logging operation
        service._log_receipt_operation(
            'test_operation',
            success=True,
            test_param='test_value'
        )
        
        # Verify logger was called
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        self.assertIn('test_operation', call_args[0][0])
    
    def test_log_receipt_operation_with_receipt(self):
        """Test logging with receipt data."""
        # This test verifies the logging method doesn't crash with real data
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        customer = Customer.objects.create(
            first_name='John',
            last_name='Doe',
            email='john@example.com'
        )
        
        invoice = Invoice.objects.create(
            customer=customer,
            number='INV-001',
            date='2024-01-15',
            total_amount=Decimal('1000.00'),
            status='validated',
            user=user
        )
        
        receipt = OwnerReceipt.objects.create(
            invoice=invoice,
            email_sent_to='test@example.com',
            gross_amount=Decimal('1000.00'),
            net_amount=Decimal('900.00'),
            status='generated'
        )
        
        # This should not raise an exception
        self.service._log_receipt_operation(
            'test_operation',
            receipt=receipt,
            invoice=invoice,
            user=user,
            success=True
        )


class OwnerReceiptIntegrationErrorTests(TestCase):
    """Integration tests for error handling across the entire system."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.agent = Agent.objects.create(
            user=self.user,
            license_number='12345',
            phone='123-456-7890'
        )
        
        self.customer = Customer.objects.create(
            first_name='John',
            last_name='Doe',
            email='john@example.com',
            phone='123-456-7890'
        )
        
        self.service = OwnerReceiptService()
    
    def test_end_to_end_validation_failure(self):
        """Test end-to-end validation failure scenario."""
        # Create invoice without proper setup
        invoice = Invoice.objects.create(
            customer=self.customer,
            number='INV-001',
            date='2024-01-15',
            total_amount=Decimal('1000.00'),
            status='draft',  # Invalid status
            user=self.user
        )
        
        # Should fail validation
        can_generate, error_msg = self.service.can_generate_receipt(invoice)
        self.assertFalse(can_generate)
        self.assertIn("debe estar validada", error_msg)
        
        # Should raise exception when trying to generate
        with self.assertRaises(OwnerReceiptValidationError):
            self.service.generate_receipt(invoice, self.user)
    
    def test_cascade_error_handling(self):
        """Test error handling when multiple components fail."""
        # Create minimal invoice that will fail at multiple levels
        invoice = Invoice.objects.create(
            customer=self.customer,
            number='INV-001',
            date='2024-01-15',
            total_amount=Decimal('0.00'),  # Invalid amount
            status='validated',
            user=self.user
            # No contract - will fail
        )
        
        # Should collect multiple errors
        validator = OwnerReceiptValidator()
        is_valid, errors, warnings = validator.validate_complete(invoice)
        
        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 1)  # Should have multiple errors
        
        # Service should also fail gracefully
        can_generate, error_msg = self.service.can_generate_receipt(invoice)
        self.assertFalse(can_generate)
        self.assertIsInstance(error_msg, str)
        self.assertGreater(len(error_msg), 0)