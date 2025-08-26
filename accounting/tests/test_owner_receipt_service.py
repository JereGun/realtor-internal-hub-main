# -*- coding: utf-8 -*-
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal
from unittest.mock import patch, MagicMock, Mock
import io

from accounting.services import OwnerReceiptService
from accounting.models_invoice import Invoice, OwnerReceipt
from customers.models import Customer
from contracts.models import Contract
from agents.models import Agent
from properties.models import Property, PropertyType


class OwnerReceiptServiceTest(TestCase):
    """
    Test suite for the OwnerReceiptService class.
    
    Tests all service methods including business logic validation,
    data collection, PDF generation, and email sending functionality.
    """
    
    def setUp(self):
        """Set up test data for OwnerReceiptService tests."""
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
    
    def test_can_generate_receipt_valid_invoice(self):
        """Test can_generate_receipt with valid invoice."""
        can_generate, error_msg = self.service.can_generate_receipt(self.invoice)
        
        self.assertTrue(can_generate)
        self.assertEqual(error_msg, "")
    
    def test_can_generate_receipt_no_invoice(self):
        """Test can_generate_receipt with None invoice."""
        can_generate, error_msg = self.service.can_generate_receipt(None)
        
        self.assertFalse(can_generate)
        self.assertEqual(error_msg, "La factura no existe.")
    
    def test_can_generate_receipt_invalid_status(self):
        """Test can_generate_receipt with invalid invoice status."""
        self.invoice.status = 'draft'
        self.invoice.save()
        
        can_generate, error_msg = self.service.can_generate_receipt(self.invoice)
        
        self.assertFalse(can_generate)
        self.assertIn("debe estar validada, enviada o pagada", error_msg)
    
    def test_can_generate_receipt_no_contract(self):
        """Test can_generate_receipt with invoice without contract."""
        self.invoice.contract = None
        self.invoice.save()
        
        can_generate, error_msg = self.service.can_generate_receipt(self.invoice)
        
        self.assertFalse(can_generate)
        self.assertEqual(error_msg, "La factura no tiene un contrato asociado.")
    
    def test_can_generate_receipt_no_property(self):
        """Test can_generate_receipt with contract without property."""
        self.contract.property = None
        self.contract.save()
        
        can_generate, error_msg = self.service.can_generate_receipt(self.invoice)
        
        self.assertFalse(can_generate)
        self.assertEqual(error_msg, "El contrato no tiene una propiedad asociada.")
    
    def test_can_generate_receipt_no_owner(self):
        """Test can_generate_receipt with property without owner."""
        self.property.owner = None
        self.property.save()
        
        can_generate, error_msg = self.service.can_generate_receipt(self.invoice)
        
        self.assertFalse(can_generate)
        self.assertEqual(error_msg, "La propiedad no tiene un propietario asignado.")
    
    def test_can_generate_receipt_no_owner_email(self):
        """Test can_generate_receipt with owner without email."""
        self.owner.email = ''
        self.owner.save()
        
        can_generate, error_msg = self.service.can_generate_receipt(self.invoice)
        
        self.assertFalse(can_generate)
        self.assertEqual(error_msg, "El propietario no tiene una dirección de email configurada.")
    
    def test_can_generate_receipt_zero_amount(self):
        """Test can_generate_receipt with zero invoice amount."""
        self.invoice.total_amount = Decimal('0.00')
        self.invoice.save()
        
        can_generate, error_msg = self.service.can_generate_receipt(self.invoice)
        
        self.assertFalse(can_generate)
        self.assertEqual(error_msg, "El monto de la factura debe ser mayor a cero.")
    
    def test_get_receipt_data_complete(self):
        """Test get_receipt_data with complete valid data."""
        receipt_data = self.service.get_receipt_data(self.invoice)
        
        # Verify structure
        self.assertIn('invoice', receipt_data)
        self.assertIn('contract', receipt_data)
        self.assertIn('property', receipt_data)
        self.assertIn('owner', receipt_data)
        self.assertIn('customer', receipt_data)
        self.assertIn('agent', receipt_data)
        self.assertIn('financial', receipt_data)
        self.assertIn('generated_at', receipt_data)
        
        # Verify invoice data
        self.assertEqual(receipt_data['invoice']['number'], 'INV-2024-001')
        self.assertEqual(receipt_data['invoice']['date'], self.invoice.date)
        
        # Verify financial calculations
        self.assertEqual(receipt_data['financial']['gross_amount'], Decimal('1000.00'))
        self.assertEqual(receipt_data['financial']['discount_percentage'], Decimal('10.00'))
        self.assertEqual(receipt_data['financial']['discount_amount'], Decimal('100.00'))
        self.assertEqual(receipt_data['financial']['net_amount'], Decimal('900.00'))
        
        # Verify property data
        self.assertEqual(receipt_data['property']['title'], 'Departamento Centro')
        self.assertEqual(receipt_data['property']['property_type'], 'Departamento')
        
        # Verify owner data
        self.assertEqual(receipt_data['owner']['name'], 'Maria Garcia')
        self.assertEqual(receipt_data['owner']['email'], 'owner@test.com')
        
        # Verify customer data
        self.assertEqual(receipt_data['customer']['name'], 'John Doe')
        self.assertEqual(receipt_data['customer']['email'], 'tenant@test.com')
        
        # Verify agent data
        self.assertEqual(receipt_data['agent']['name'], 'Test Agent')
        self.assertEqual(receipt_data['agent']['license_number'], 'LIC123')
    
    def test_get_receipt_data_no_discount(self):
        """Test get_receipt_data with contract without owner discount."""
        self.contract.owner_discount_percentage = None
        self.contract.save()
        
        receipt_data = self.service.get_receipt_data(self.invoice)
        
        # Verify financial calculations without discount
        self.assertEqual(receipt_data['financial']['gross_amount'], Decimal('1000.00'))
        self.assertEqual(receipt_data['financial']['discount_percentage'], Decimal('0.00'))
        self.assertEqual(receipt_data['financial']['discount_amount'], Decimal('0.00'))
        self.assertEqual(receipt_data['financial']['net_amount'], Decimal('1000.00'))
    
    def test_get_receipt_data_invalid_invoice(self):
        """Test get_receipt_data with invalid invoice."""
        self.invoice.status = 'draft'
        self.invoice.save()
        
        with self.assertRaises(ValidationError) as context:
            self.service.get_receipt_data(self.invoice)
        
        self.assertIn("debe estar validada", str(context.exception))
    
    def test_generate_receipt_success(self):
        """Test successful receipt generation."""
        receipt = self.service.generate_receipt(self.invoice, self.agent)
        
        # Verify receipt was created
        self.assertIsNotNone(receipt.pk)
        self.assertEqual(receipt.invoice, self.invoice)
        self.assertEqual(receipt.generated_by, self.agent)
        self.assertEqual(receipt.email_sent_to, 'owner@test.com')
        self.assertEqual(receipt.status, 'generated')
        
        # Verify financial calculations
        self.assertEqual(receipt.gross_amount, Decimal('1000.00'))
        self.assertEqual(receipt.discount_percentage, Decimal('10.00'))
        self.assertEqual(receipt.discount_amount, Decimal('100.00'))
        self.assertEqual(receipt.net_amount, Decimal('900.00'))
        
        # Verify receipt number was generated
        self.assertIsNotNone(receipt.receipt_number)
        self.assertTrue(receipt.receipt_number.startswith('REC-'))
    
    def test_generate_receipt_invalid_invoice(self):
        """Test receipt generation with invalid invoice."""
        self.invoice.status = 'draft'
        self.invoice.save()
        
        with self.assertRaises(ValidationError) as context:
            self.service.generate_receipt(self.invoice, self.agent)
        
        self.assertIn("debe estar validada", str(context.exception))
    
    def test_generate_receipt_non_agent_user(self):
        """Test receipt generation with non-agent user."""
        # Create a mock user without license_number attribute
        mock_user = Mock()
        mock_user.license_number = None
        
        receipt = self.service.generate_receipt(self.invoice, mock_user)
        
        # Should create receipt but without generated_by
        self.assertIsNotNone(receipt.pk)
        self.assertIsNone(receipt.generated_by)
    
    @patch('accounting.services.render_to_string')
    @patch('accounting.services.HTML')
    def test_generate_pdf_success(self, mock_html_class, mock_render):
        """Test successful PDF generation."""
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
        
        # Mock render_to_string
        mock_render.return_value = '<html>Test HTML</html>'
        
        # Mock HTML and write_pdf
        mock_html_instance = Mock()
        mock_html_instance.write_pdf.return_value = b'PDF content'
        mock_html_class.return_value = mock_html_instance
        
        # Generate PDF
        pdf_content = self.service.generate_pdf(receipt)
        
        # Verify calls
        mock_render.assert_called_once()
        mock_html_class.assert_called_once_with(string='<html>Test HTML</html>')
        mock_html_instance.write_pdf.assert_called_once()
        
        # Verify result
        self.assertEqual(pdf_content, b'PDF content')
    
    @patch('accounting.services.render_to_string')
    def test_generate_pdf_template_error(self, mock_render):
        """Test PDF generation with template error."""
        receipt = OwnerReceipt.objects.create(
            invoice=self.invoice,
            email_sent_to='owner@test.com',
            gross_amount=Decimal('1000.00'),
            net_amount=Decimal('900.00')
        )
        
        # Mock template error
        mock_render.side_effect = Exception("Template error")
        
        with self.assertRaises(ValidationError) as context:
            self.service.generate_pdf(receipt)
        
        self.assertIn("Error al generar el PDF", str(context.exception))
    
    @patch('accounting.services.EmailMessage')
    @patch.object(OwnerReceiptService, 'generate_pdf')
    @patch('accounting.services.render_to_string')
    def test_send_receipt_email_success(self, mock_render, mock_generate_pdf, mock_email_class):
        """Test successful email sending."""
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
        result = self.service.send_receipt_email(receipt)
        
        # Verify result
        self.assertTrue(result)
        
        # Verify email was created and sent
        mock_email_class.assert_called_once()
        mock_email_instance.send.assert_called_once()
        mock_email_instance.attach.assert_called_once()
        
        # Verify receipt status was updated
        receipt.refresh_from_db()
        self.assertEqual(receipt.status, 'sent')
        self.assertIsNotNone(receipt.sent_at)
    
    @patch.object(OwnerReceiptService, 'generate_pdf')
    def test_send_receipt_email_already_sent(self, mock_generate_pdf):
        """Test sending email for already sent receipt."""
        receipt = OwnerReceipt.objects.create(
            invoice=self.invoice,
            email_sent_to='owner@test.com',
            gross_amount=Decimal('1000.00'),
            net_amount=Decimal('900.00'),
            status='sent'
        )
        
        with self.assertRaises(ValidationError) as context:
            self.service.send_receipt_email(receipt)
        
        self.assertIn("ya fue enviado exitosamente", str(context.exception))
    
    @patch('accounting.services.EmailMessage')
    @patch.object(OwnerReceiptService, 'generate_pdf')
    @patch('accounting.services.render_to_string')
    def test_send_receipt_email_failure(self, mock_render, mock_generate_pdf, mock_email_class):
        """Test email sending failure."""
        receipt = OwnerReceipt.objects.create(
            invoice=self.invoice,
            email_sent_to='owner@test.com',
            gross_amount=Decimal('1000.00'),
            net_amount=Decimal('900.00')
        )
        
        # Mock PDF generation
        mock_generate_pdf.return_value = b'PDF content'
        mock_render.return_value = '<html>Email content</html>'
        
        # Mock email sending failure
        mock_email_instance = Mock()
        mock_email_instance.send.side_effect = Exception("SMTP error")
        mock_email_class.return_value = mock_email_instance
        
        with self.assertRaises(ValidationError) as context:
            self.service.send_receipt_email(receipt)
        
        self.assertIn("Error al enviar comprobante por email", str(context.exception))
        
        # Verify receipt was marked as failed
        receipt.refresh_from_db()
        self.assertEqual(receipt.status, 'failed')
        self.assertIn("SMTP error", receipt.error_message)
    
    @patch.object(OwnerReceiptService, 'send_receipt_email')
    def test_resend_receipt_email_success(self, mock_send_email):
        """Test successful receipt resending."""
        receipt = OwnerReceipt.objects.create(
            invoice=self.invoice,
            email_sent_to='owner@test.com',
            gross_amount=Decimal('1000.00'),
            net_amount=Decimal('900.00'),
            status='failed',
            error_message='Previous error'
        )
        
        # Mock successful sending
        mock_send_email.return_value = True
        
        result = self.service.resend_receipt_email(receipt)
        
        self.assertTrue(result)
        mock_send_email.assert_called_once_with(receipt)
        
        # Verify status was reset before resending
        receipt.refresh_from_db()
        self.assertEqual(receipt.status, 'sent')  # Will be set by mock send_receipt_email
    
    def test_resend_receipt_email_cannot_resend(self):
        """Test resending receipt that cannot be resent."""
        receipt = OwnerReceipt.objects.create(
            invoice=self.invoice,
            email_sent_to='owner@test.com',
            gross_amount=Decimal('1000.00'),
            net_amount=Decimal('900.00'),
            status='sent'
        )
        
        with self.assertRaises(ValidationError) as context:
            self.service.resend_receipt_email(receipt)
        
        self.assertIn("no puede ser reenviado", str(context.exception))
    
    @patch.object(OwnerReceiptService, 'send_receipt_email')
    def test_resend_receipt_email_failure(self, mock_send_email):
        """Test receipt resending failure."""
        receipt = OwnerReceipt.objects.create(
            invoice=self.invoice,
            email_sent_to='owner@test.com',
            gross_amount=Decimal('1000.00'),
            net_amount=Decimal('900.00'),
            status='failed'
        )
        
        # Mock sending failure
        mock_send_email.side_effect = ValidationError("Send failed")
        
        with self.assertRaises(ValidationError):
            self.service.resend_receipt_email(receipt)
    
    def test_service_initialization(self):
        """Test service initialization."""
        service = OwnerReceiptService()
        self.assertIsNotNone(service.logger)
    
    def test_get_receipt_data_with_missing_optional_fields(self):
        """Test get_receipt_data when some optional fields are missing."""
        # Remove optional phone numbers
        self.owner.phone = ''
        self.owner.save()
        
        self.tenant.phone = ''
        self.tenant.save()
        
        # Remove optional agent phone
        if hasattr(self.agent, 'phone'):
            self.agent.phone = ''
            self.agent.save()
        
        receipt_data = self.service.get_receipt_data(self.invoice)
        
        # Should still work with empty optional fields
        self.assertEqual(receipt_data['owner']['phone'], '')
        self.assertEqual(receipt_data['customer']['phone'], '')
        self.assertEqual(receipt_data['agent']['phone'], '')
    
    def test_financial_calculations_precision(self):
        """Test financial calculations with decimal precision."""
        # Set up invoice with amount that results in non-round discount
        self.invoice.total_amount = Decimal('1234.56')
        self.invoice.save()
        
        self.contract.amount = Decimal('1234.56')
        self.contract.owner_discount_percentage = Decimal('12.34')
        self.contract.save()
        
        receipt_data = self.service.get_receipt_data(self.invoice)
        
        expected_discount = Decimal('1234.56') * (Decimal('12.34') / Decimal('100'))
        expected_net = Decimal('1234.56') - expected_discount
        
        self.assertEqual(receipt_data['financial']['gross_amount'], Decimal('1234.56'))
        self.assertEqual(receipt_data['financial']['discount_percentage'], Decimal('12.34'))
        self.assertEqual(receipt_data['financial']['discount_amount'], expected_discount)
        self.assertEqual(receipt_data['financial']['net_amount'], expected_net)
    
    def test_error_handling_with_logging(self):
        """Test that errors are properly logged."""
        with patch.object(self.service, 'logger') as mock_logger:
            # Test with invalid invoice
            self.invoice.status = 'draft'
            self.invoice.save()
            
            try:
                self.service.generate_receipt(self.invoice, self.agent)
            except ValidationError:
                pass
            
            # Verify error was logged
            mock_logger.error.assert_called()