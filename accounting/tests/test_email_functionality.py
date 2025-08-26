# -*- coding: utf-8 -*-
"""
Additional tests for email functionality in OwnerReceiptService.

This test file focuses specifically on email sending scenarios,
retry mechanisms, and error handling for the owner receipt system.
"""
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.core.mail import EmailMessage
from django.utils import timezone
from decimal import Decimal
from unittest.mock import patch, MagicMock, Mock
import smtplib

from accounting.services import OwnerReceiptService
from accounting.models_invoice import Invoice, OwnerReceipt
from customers.models import Customer
from contracts.models import Contract
from agents.models import Agent
from properties.models import Property, PropertyType


class EmailFunctionalityTest(TestCase):
    """
    Test suite focused on email functionality for owner receipts.
    
    Tests email sending, retry mechanisms, error handling,
    and various email-related scenarios.
    """
    
    def setUp(self):
        """Set up test data for email functionality tests."""
        # Create test agent
        self.agent = Agent.objects.create(
            username='testagent',
            email='agent@test.com',
            first_name='Test',
            last_name='Agent',
            license_number='LIC123'
        )
        
        # Create test customer (owner)
        self.owner = Customer.objects.create(
            first_name='Maria',
            last_name='Garcia',
            email='owner@test.com',
            phone='123456789'
        )
        
        # Create test customer (tenant)
        self.tenant = Customer.objects.create(
            first_name='John',
            last_name='Doe',
            email='tenant@test.com',
            phone='987654321'
        )
        
        # Create property type
        self.property_type = PropertyType.objects.create(
            name='Departamento',
            description='Departamento de alquiler'
        )
        
        # Create test property
        self.property = Property.objects.create(
            title='Departamento Centro',
            description='Departamento en el centro de la ciudad',
            property_type=self.property_type,
            street='Av. Principal',
            number='123',
            neighborhood='Centro',
            total_surface=Decimal('80.00'),
            bedrooms=2,
            bathrooms=1,
            agent=self.agent,
            owner=self.owner
        )
        
        # Create test contract with owner discount
        self.contract = Contract.objects.create(
            customer=self.tenant,
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
            customer=self.tenant,
            contract=self.contract,
            description='Alquiler Enero 2024',
            total_amount=Decimal('1000.00'),
            status='validated'
        )
        
        # Initialize service
        self.service = OwnerReceiptService()
    
    @patch('accounting.services.EmailMessage')
    @patch.object(OwnerReceiptService, 'generate_pdf')
    @patch('accounting.services.render_to_string')
    def test_email_content_and_structure(self, mock_render, mock_generate_pdf, mock_email_class):
        """Test that email is created with correct content and structure."""
        # Create a receipt
        receipt = OwnerReceipt.objects.create(
            invoice=self.invoice,
            generated_by=self.agent,
            email_sent_to='owner@test.com',
            gross_amount=Decimal('1000.00'),
            discount_percentage=Decimal('10.00'),
            discount_amount=Decimal('100.00'),
            net_amount=Decimal('900.00')
        )
        
        # Mock PDF generation
        mock_generate_pdf.return_value = b'PDF content'
        
        # Mock email template rendering
        mock_render.return_value = '<html>Email content</html>'
        
        # Mock email
        mock_email_instance = Mock()
        mock_email_class.return_value = mock_email_instance
        
        # Send email
        self.service.send_receipt_email(receipt)
        
        # Verify email was created with correct parameters
        mock_email_class.assert_called_once()
        call_args = mock_email_class.call_args
        
        # Check subject contains property and period
        subject = call_args[1]['subject']
        self.assertIn('Comprobante de Alquiler', subject)
        self.assertIn('Av. Principal 123', subject)
        
        # Check email addresses
        self.assertEqual(call_args[1]['to'], ['owner@test.com'])
        
        # Verify email content type is set to HTML
        self.assertEqual(mock_email_instance.content_subtype, 'html')
        
        # Verify PDF attachment
        mock_email_instance.attach.assert_called_once_with(
            f'comprobante_{receipt.receipt_number}.pdf',
            b'PDF content',
            'application/pdf'
        )
        
        # Verify email template was rendered with correct context
        mock_render.assert_called_once()
        template_context = mock_render.call_args[0][1]
        
        self.assertEqual(template_context['owner_name'], 'Maria Garcia')
        self.assertEqual(template_context['property_address'], 'Av. Principal 123')
        self.assertEqual(template_context['net_amount'], Decimal('900.00'))
        self.assertEqual(template_context['receipt_number'], receipt.receipt_number)
    
    @patch('accounting.services.EmailMessage')
    @patch.object(OwnerReceiptService, 'generate_pdf')
    @patch('accounting.services.render_to_string')
    def test_smtp_connection_error(self, mock_render, mock_generate_pdf, mock_email_class):
        """Test handling of SMTP connection errors."""
        receipt = OwnerReceipt.objects.create(
            invoice=self.invoice,
            email_sent_to='owner@test.com',
            gross_amount=Decimal('1000.00'),
            net_amount=Decimal('900.00')
        )
        
        # Mock PDF generation
        mock_generate_pdf.return_value = b'PDF content'
        mock_render.return_value = '<html>Email content</html>'
        
        # Mock SMTP connection error
        mock_email_instance = Mock()
        mock_email_instance.send.side_effect = smtplib.SMTPConnectError(421, "Service not available")
        mock_email_class.return_value = mock_email_instance
        
        with self.assertRaises(ValidationError) as context:
            self.service.send_receipt_email(receipt)
        
        self.assertIn("Error al enviar comprobante por email", str(context.exception))
        
        # Verify receipt was marked as failed
        receipt.refresh_from_db()
        self.assertEqual(receipt.status, 'failed')
        self.assertIn("Service not available", receipt.error_message)
    
    @patch('accounting.services.EmailMessage')
    @patch.object(OwnerReceiptService, 'generate_pdf')
    @patch('accounting.services.render_to_string')
    def test_smtp_authentication_error(self, mock_render, mock_generate_pdf, mock_email_class):
        """Test handling of SMTP authentication errors."""
        receipt = OwnerReceipt.objects.create(
            invoice=self.invoice,
            email_sent_to='owner@test.com',
            gross_amount=Decimal('1000.00'),
            net_amount=Decimal('900.00')
        )
        
        # Mock PDF generation
        mock_generate_pdf.return_value = b'PDF content'
        mock_render.return_value = '<html>Email content</html>'
        
        # Mock SMTP authentication error
        mock_email_instance = Mock()
        mock_email_instance.send.side_effect = smtplib.SMTPAuthenticationError(535, "Authentication failed")
        mock_email_class.return_value = mock_email_instance
        
        with self.assertRaises(ValidationError) as context:
            self.service.send_receipt_email(receipt)
        
        self.assertIn("Error al enviar comprobante por email", str(context.exception))
        
        # Verify receipt was marked as failed
        receipt.refresh_from_db()
        self.assertEqual(receipt.status, 'failed')
        self.assertIn("Authentication failed", receipt.error_message)
    
    @patch('accounting.services.EmailMessage')
    @patch.object(OwnerReceiptService, 'generate_pdf')
    @patch('accounting.services.render_to_string')
    def test_invalid_email_address_error(self, mock_render, mock_generate_pdf, mock_email_class):
        """Test handling of invalid email address errors."""
        receipt = OwnerReceipt.objects.create(
            invoice=self.invoice,
            email_sent_to='invalid-email',  # Invalid email format
            gross_amount=Decimal('1000.00'),
            net_amount=Decimal('900.00')
        )
        
        # Mock PDF generation
        mock_generate_pdf.return_value = b'PDF content'
        mock_render.return_value = '<html>Email content</html>'
        
        # Mock invalid email error
        mock_email_instance = Mock()
        mock_email_instance.send.side_effect = smtplib.SMTPRecipientsRefused({'invalid-email': (550, 'Invalid email address')})
        mock_email_class.return_value = mock_email_instance
        
        with self.assertRaises(ValidationError) as context:
            self.service.send_receipt_email(receipt)
        
        self.assertIn("Error al enviar comprobante por email", str(context.exception))
        
        # Verify receipt was marked as failed
        receipt.refresh_from_db()
        self.assertEqual(receipt.status, 'failed')
        self.assertIn("Invalid email address", receipt.error_message)
    
    @patch.object(OwnerReceiptService, 'send_receipt_email')
    def test_retry_mechanism_success(self, mock_send_email):
        """Test successful retry of failed email sending."""
        # Create a failed receipt
        receipt = OwnerReceipt.objects.create(
            invoice=self.invoice,
            email_sent_to='owner@test.com',
            gross_amount=Decimal('1000.00'),
            net_amount=Decimal('900.00'),
            status='failed',
            error_message='Previous SMTP error'
        )
        
        # Mock successful retry
        mock_send_email.return_value = True
        
        # Attempt resend
        result = self.service.resend_receipt_email(receipt)
        
        self.assertTrue(result)
        
        # Verify status was reset before retry
        receipt.refresh_from_db()
        self.assertEqual(receipt.status, 'sent')  # Will be set by mock
        
        # Verify send_receipt_email was called
        mock_send_email.assert_called_once_with(receipt)
    
    @patch.object(OwnerReceiptService, 'send_receipt_email')
    def test_retry_mechanism_failure(self, mock_send_email):
        """Test retry mechanism when resend also fails."""
        # Create a failed receipt
        receipt = OwnerReceipt.objects.create(
            invoice=self.invoice,
            email_sent_to='owner@test.com',
            gross_amount=Decimal('1000.00'),
            net_amount=Decimal('900.00'),
            status='failed',
            error_message='Previous SMTP error'
        )
        
        # Mock failed retry
        mock_send_email.side_effect = ValidationError("Still failing")
        
        with self.assertRaises(ValidationError) as context:
            self.service.resend_receipt_email(receipt)
        
        self.assertIn("Still failing", str(context.exception))
    
    def test_cannot_resend_sent_receipt(self):
        """Test that successfully sent receipts cannot be resent."""
        receipt = OwnerReceipt.objects.create(
            invoice=self.invoice,
            email_sent_to='owner@test.com',
            gross_amount=Decimal('1000.00'),
            net_amount=Decimal('900.00'),
            status='sent',
            sent_at=timezone.now()
        )
        
        with self.assertRaises(ValidationError) as context:
            self.service.resend_receipt_email(receipt)
        
        self.assertIn("no puede ser reenviado", str(context.exception))
    
    @patch('accounting.services.EmailMessage')
    @patch.object(OwnerReceiptService, 'generate_pdf')
    @patch('accounting.services.render_to_string')
    def test_email_with_special_characters(self, mock_render, mock_generate_pdf, mock_email_class):
        """Test email sending with special characters in property address and names."""
        # Update property with special characters
        self.property.title = 'Departamento "El Mirador" - Piso 5°'
        self.property.street = 'Av. José María Morelos y Pavón'
        self.property.save()
        
        # Update owner with special characters
        self.owner.first_name = 'María José'
        self.owner.last_name = 'García-López'
        self.owner.save()
        
        receipt = OwnerReceipt.objects.create(
            invoice=self.invoice,
            email_sent_to='owner@test.com',
            gross_amount=Decimal('1000.00'),
            net_amount=Decimal('900.00')
        )
        
        # Mock PDF generation and email
        mock_generate_pdf.return_value = b'PDF content'
        mock_render.return_value = '<html>Email content</html>'
        mock_email_instance = Mock()
        mock_email_class.return_value = mock_email_instance
        
        # Send email
        result = self.service.send_receipt_email(receipt)
        
        self.assertTrue(result)
        
        # Verify template context handles special characters
        mock_render.assert_called_once()
        template_context = mock_render.call_args[0][1]
        
        self.assertEqual(template_context['owner_name'], 'María José García-López')
        self.assertIn('José María Morelos y Pavón', template_context['property_address'])
    
    @patch('accounting.services.EmailMessage')
    @patch.object(OwnerReceiptService, 'generate_pdf')
    @patch('accounting.services.render_to_string')
    def test_email_with_large_pdf_attachment(self, mock_render, mock_generate_pdf, mock_email_class):
        """Test email sending with large PDF attachment."""
        receipt = OwnerReceipt.objects.create(
            invoice=self.invoice,
            email_sent_to='owner@test.com',
            gross_amount=Decimal('1000.00'),
            net_amount=Decimal('900.00')
        )
        
        # Mock large PDF (5MB)
        large_pdf_content = b'PDF content' * 100000  # Simulate large PDF
        mock_generate_pdf.return_value = large_pdf_content
        mock_render.return_value = '<html>Email content</html>'
        
        mock_email_instance = Mock()
        mock_email_class.return_value = mock_email_instance
        
        # Send email
        result = self.service.send_receipt_email(receipt)
        
        self.assertTrue(result)
        
        # Verify large attachment was handled
        mock_email_instance.attach.assert_called_once_with(
            f'comprobante_{receipt.receipt_number}.pdf',
            large_pdf_content,
            'application/pdf'
        )
    
    @patch.object(OwnerReceiptService, 'generate_pdf')
    def test_pdf_generation_error_during_email(self, mock_generate_pdf):
        """Test handling of PDF generation errors during email sending."""
        receipt = OwnerReceipt.objects.create(
            invoice=self.invoice,
            email_sent_to='owner@test.com',
            gross_amount=Decimal('1000.00'),
            net_amount=Decimal('900.00')
        )
        
        # Mock PDF generation error
        mock_generate_pdf.side_effect = ValidationError("PDF generation failed")
        
        with self.assertRaises(ValidationError) as context:
            self.service.send_receipt_email(receipt)
        
        self.assertIn("PDF generation failed", str(context.exception))
        
        # Verify receipt was marked as failed
        receipt.refresh_from_db()
        self.assertEqual(receipt.status, 'failed')
    
    @patch('accounting.services.EmailMessage')
    @patch.object(OwnerReceiptService, 'generate_pdf')
    @patch('accounting.services.render_to_string')
    def test_email_template_rendering_error(self, mock_render, mock_generate_pdf, mock_email_class):
        """Test handling of email template rendering errors."""
        receipt = OwnerReceipt.objects.create(
            invoice=self.invoice,
            email_sent_to='owner@test.com',
            gross_amount=Decimal('1000.00'),
            net_amount=Decimal('900.00')
        )
        
        # Mock PDF generation success
        mock_generate_pdf.return_value = b'PDF content'
        
        # Mock template rendering error
        mock_render.side_effect = Exception("Template rendering failed")
        
        with self.assertRaises(ValidationError) as context:
            self.service.send_receipt_email(receipt)
        
        self.assertIn("Error al enviar comprobante por email", str(context.exception))
        
        # Verify receipt was marked as failed
        receipt.refresh_from_db()
        self.assertEqual(receipt.status, 'failed')
        self.assertIn("Template rendering failed", receipt.error_message)
    
    def test_can_resend_status_validation(self):
        """Test can_resend method with different receipt statuses."""
        # Test generated status - can resend
        receipt_generated = OwnerReceipt.objects.create(
            invoice=self.invoice,
            email_sent_to='owner@test.com',
            gross_amount=Decimal('1000.00'),
            net_amount=Decimal('900.00'),
            status='generated'
        )
        self.assertTrue(receipt_generated.can_resend())
        
        # Test failed status - can resend
        receipt_failed = OwnerReceipt.objects.create(
            invoice=self.invoice,
            email_sent_to='owner2@test.com',
            gross_amount=Decimal('1000.00'),
            net_amount=Decimal('900.00'),
            status='failed'
        )
        self.assertTrue(receipt_failed.can_resend())
        
        # Test sent status - cannot resend
        receipt_sent = OwnerReceipt.objects.create(
            invoice=self.invoice,
            email_sent_to='owner3@test.com',
            gross_amount=Decimal('1000.00'),
            net_amount=Decimal('900.00'),
            status='sent'
        )
        self.assertFalse(receipt_sent.can_resend())
    
    @patch('accounting.services.EmailMessage')
    @patch.object(OwnerReceiptService, 'generate_pdf')
    @patch('accounting.services.render_to_string')
    def test_email_status_tracking(self, mock_render, mock_generate_pdf, mock_email_class):
        """Test that email status is properly tracked throughout the process."""
        receipt = OwnerReceipt.objects.create(
            invoice=self.invoice,
            email_sent_to='owner@test.com',
            gross_amount=Decimal('1000.00'),
            net_amount=Decimal('900.00'),
            status='generated'
        )
        
        # Mock successful email sending
        mock_generate_pdf.return_value = b'PDF content'
        mock_render.return_value = '<html>Email content</html>'
        mock_email_instance = Mock()
        mock_email_class.return_value = mock_email_instance
        
        # Verify initial status
        self.assertEqual(receipt.status, 'generated')
        self.assertIsNone(receipt.sent_at)
        
        # Send email
        result = self.service.send_receipt_email(receipt)
        
        self.assertTrue(result)
        
        # Verify status was updated
        receipt.refresh_from_db()
        self.assertEqual(receipt.status, 'sent')
        self.assertIsNotNone(receipt.sent_at)
        self.assertEqual(receipt.error_message, '')