"""
Tests for Owner Receipt Views

This module contains comprehensive tests for all owner receipt related views,
covering both successful scenarios and error cases.
"""

import json
from decimal import Decimal
from unittest.mock import patch, MagicMock

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.http import HttpResponse

from agents.models import Agent
from customers.models import Customer
from contracts.models import Contract
from properties.models import Property
from .models_invoice import Invoice, OwnerReceipt
from .services import OwnerReceiptService

User = get_user_model()


class OwnerReceiptViewsTestCase(TestCase):
    """Base test case with common setup for owner receipt views."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        # Create test user/agent
        self.user = Agent.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        self.client.login(username='testuser', password='testpass123')
        
        # Create test customer
        self.customer = Customer.objects.create(
            first_name='John',
            last_name='Doe',
            email='john@example.com',
            phone='123456789'
        )
        
        # Create test property
        self.property = Property.objects.create(
            title='Test Property',
            address='123 Test St',
            property_type='apartment',
            bedrooms=2,
            bathrooms=1,
            area=100
        )
        
        # Create test contract
        self.contract = Contract.objects.create(
            property=self.property,
            customer=self.customer,
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timezone.timedelta(days=365),
            monthly_rent=Decimal('1000.00'),
            owner_discount_percentage=Decimal('10.00')
        )
        
        # Create test invoice
        self.invoice = Invoice.objects.create(
            customer=self.customer,
            contract=self.contract,
            date=timezone.now().date(),
            due_date=timezone.now().date() + timezone.timedelta(days=30),
            total_amount=Decimal('1000.00'),
            status='validated'
        )


class GenerateOwnerReceiptViewTest(OwnerReceiptViewsTestCase):
    """Tests for generate_owner_receipt view."""
    
    def test_generate_receipt_success(self):
        """Test successful receipt generation."""
        url = reverse('accounting:generate_owner_receipt', kwargs={'invoice_pk': self.invoice.pk})
        
        with patch.object(OwnerReceiptService, 'generate_receipt') as mock_generate:
            mock_receipt = MagicMock()
            mock_receipt.pk = 1
            mock_receipt.receipt_number = 'REC-2024-001'
            mock_generate.return_value = mock_receipt
            
            response = self.client.post(url, {'send_email': 'true'})
            
            self.assertEqual(response.status_code, 302)
            mock_generate.assert_called_once_with(self.invoice, self.user, send_email=True)
    
    def test_generate_receipt_ajax_success(self):
        """Test successful AJAX receipt generation."""
        url = reverse('accounting:generate_owner_receipt', kwargs={'invoice_pk': self.invoice.pk})
        
        with patch.object(OwnerReceiptService, 'generate_receipt') as mock_generate:
            mock_receipt = MagicMock()
            mock_receipt.pk = 1
            mock_receipt.receipt_number = 'REC-2024-001'
            mock_generate.return_value = mock_receipt
            
            response = self.client.post(
                url, 
                {'send_email': 'true'},
                HTTP_X_REQUESTED_WITH='XMLHttpRequest'
            )
            
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.content)
            self.assertTrue(data['success'])
            self.assertEqual(data['receipt_number'], 'REC-2024-001')
    
    def test_generate_receipt_invalid_invoice(self):
        """Test receipt generation with invalid invoice."""
        url = reverse('accounting:generate_owner_receipt', kwargs={'invoice_pk': 99999})
        
        response = self.client.post(url)
        self.assertEqual(response.status_code, 404)
    
    def test_generate_receipt_service_error(self):
        """Test receipt generation with service error."""
        url = reverse('accounting:generate_owner_receipt', kwargs={'invoice_pk': self.invoice.pk})
        
        with patch.object(OwnerReceiptService, 'generate_receipt') as mock_generate:
            mock_generate.side_effect = Exception("Service error")
            
            response = self.client.post(
                url,
                HTTP_X_REQUESTED_WITH='XMLHttpRequest'
            )
            
            self.assertEqual(response.status_code, 500)
            data = json.loads(response.content)
            self.assertFalse(data['success'])
            self.assertIn('error', data)
    
    def test_generate_receipt_get_request(self):
        """Test GET request to generate receipt view."""
        url = reverse('accounting:generate_owner_receipt', kwargs={'invoice_pk': self.invoice.pk})
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Generar Comprobante')


class PreviewOwnerReceiptViewTest(OwnerReceiptViewsTestCase):
    """Tests for preview_owner_receipt view."""
    
    def test_preview_receipt_success(self):
        """Test successful receipt preview."""
        url = reverse('accounting:preview_owner_receipt', kwargs={'invoice_pk': self.invoice.pk})
        
        with patch.object(OwnerReceiptService, 'get_receipt_data') as mock_get_data:
            mock_get_data.return_value = {
                'invoice': self.invoice,
                'contract': self.contract,
                'calculations': {
                    'gross_amount': Decimal('1000.00'),
                    'discount_amount': Decimal('100.00'),
                    'net_amount': Decimal('900.00')
                }
            }
            
            response = self.client.get(url)
            
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'Vista Previa')
    
    def test_preview_receipt_invalid_invoice(self):
        """Test preview with invalid invoice."""
        url = reverse('accounting:preview_owner_receipt', kwargs={'invoice_pk': 99999})
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
    
    def test_preview_receipt_service_error(self):
        """Test preview with service error."""
        url = reverse('accounting:preview_owner_receipt', kwargs={'invoice_pk': self.invoice.pk})
        
        with patch.object(OwnerReceiptService, 'get_receipt_data') as mock_get_data:
            mock_get_data.side_effect = Exception("Service error")
            
            response = self.client.get(url)
            self.assertEqual(response.status_code, 500)


class OwnerReceiptDetailViewTest(OwnerReceiptViewsTestCase):
    """Tests for owner_receipt_detail view."""
    
    def setUp(self):
        super().setUp()
        self.receipt = OwnerReceipt.objects.create(
            invoice=self.invoice,
            receipt_number='REC-2024-001',
            generated_by=self.user,
            email_sent_to='owner@example.com',
            gross_amount=Decimal('1000.00'),
            discount_amount=Decimal('100.00'),
            net_amount=Decimal('900.00'),
            status='sent'
        )
    
    def test_receipt_detail_success(self):
        """Test successful receipt detail view."""
        url = reverse('accounting:owner_receipt_detail', kwargs={'receipt_pk': self.receipt.pk})
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'REC-2024-001')
        self.assertContains(response, 'owner@example.com')
    
    def test_receipt_detail_invalid_receipt(self):
        """Test detail view with invalid receipt."""
        url = reverse('accounting:owner_receipt_detail', kwargs={'receipt_pk': 99999})
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)


class ResendOwnerReceiptViewTest(OwnerReceiptViewsTestCase):
    """Tests for resend_owner_receipt view."""
    
    def setUp(self):
        super().setUp()
        self.receipt = OwnerReceipt.objects.create(
            invoice=self.invoice,
            receipt_number='REC-2024-001',
            generated_by=self.user,
            email_sent_to='owner@example.com',
            gross_amount=Decimal('1000.00'),
            discount_amount=Decimal('100.00'),
            net_amount=Decimal('900.00'),
            status='failed'
        )
    
    def test_resend_receipt_success(self):
        """Test successful receipt resend."""
        url = reverse('accounting:resend_owner_receipt', kwargs={'receipt_pk': self.receipt.pk})
        
        with patch.object(OwnerReceiptService, 'send_receipt_email') as mock_send:
            mock_send.return_value = True
            
            response = self.client.post(url)
            
            self.assertEqual(response.status_code, 302)
            mock_send.assert_called_once_with(self.receipt)
    
    def test_resend_receipt_ajax_success(self):
        """Test successful AJAX receipt resend."""
        url = reverse('accounting:resend_owner_receipt', kwargs={'receipt_pk': self.receipt.pk})
        
        with patch.object(OwnerReceiptService, 'send_receipt_email') as mock_send:
            mock_send.return_value = True
            
            response = self.client.post(
                url,
                HTTP_X_REQUESTED_WITH='XMLHttpRequest'
            )
            
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.content)
            self.assertTrue(data['success'])
    
    def test_resend_receipt_service_error(self):
        """Test resend with service error."""
        url = reverse('accounting:resend_owner_receipt', kwargs={'receipt_pk': self.receipt.pk})
        
        with patch.object(OwnerReceiptService, 'send_receipt_email') as mock_send:
            mock_send.side_effect = Exception("Email error")
            
            response = self.client.post(
                url,
                HTTP_X_REQUESTED_WITH='XMLHttpRequest'
            )
            
            self.assertEqual(response.status_code, 500)
            data = json.loads(response.content)
            self.assertFalse(data['success'])
    
    def test_resend_receipt_get_request(self):
        """Test GET request to resend view."""
        url = reverse('accounting:resend_owner_receipt', kwargs={'receipt_pk': self.receipt.pk})
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Reenviar Comprobante')


class OwnerReceiptsListViewTest(OwnerReceiptViewsTestCase):
    """Tests for owner_receipts_list view."""
    
    def setUp(self):
        super().setUp()
        # Create multiple receipts for testing
        for i in range(5):
            OwnerReceipt.objects.create(
                invoice=self.invoice,
                receipt_number=f'REC-2024-{i+1:03d}',
                generated_by=self.user,
                email_sent_to='owner@example.com',
                gross_amount=Decimal('1000.00'),
                discount_amount=Decimal('100.00'),
                net_amount=Decimal('900.00'),
                status='sent' if i % 2 == 0 else 'failed'
            )
    
    def test_receipts_list_success(self):
        """Test successful receipts list view."""
        url = reverse('accounting:owner_receipts_list')
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Lista de Comprobantes')
        self.assertEqual(len(response.context['receipts']), 5)
    
    def test_receipts_list_with_filters(self):
        """Test receipts list with status filter."""
        url = reverse('accounting:owner_receipts_list')
        
        response = self.client.get(url, {'status': 'sent'})
        
        self.assertEqual(response.status_code, 200)
        # Should show only sent receipts (3 out of 5)
        self.assertEqual(len(response.context['receipts']), 3)
    
    def test_receipts_list_with_search(self):
        """Test receipts list with search query."""
        url = reverse('accounting:owner_receipts_list')
        
        response = self.client.get(url, {'q': 'REC-2024-001'})
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['receipts']), 1)
    
    def test_receipts_list_pagination(self):
        """Test receipts list pagination."""
        # Create more receipts to test pagination
        for i in range(20):
            OwnerReceipt.objects.create(
                invoice=self.invoice,
                receipt_number=f'REC-2024-{i+100:03d}',
                generated_by=self.user,
                email_sent_to='owner@example.com',
                gross_amount=Decimal('1000.00'),
                discount_amount=Decimal('100.00'),
                net_amount=Decimal('900.00'),
                status='sent'
            )
        
        url = reverse('accounting:owner_receipts_list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['receipts'].has_next())


class OwnerReceiptPDFViewTest(OwnerReceiptViewsTestCase):
    """Tests for owner_receipt_pdf view."""
    
    def setUp(self):
        super().setUp()
        self.receipt = OwnerReceipt.objects.create(
            invoice=self.invoice,
            receipt_number='REC-2024-001',
            generated_by=self.user,
            email_sent_to='owner@example.com',
            gross_amount=Decimal('1000.00'),
            discount_amount=Decimal('100.00'),
            net_amount=Decimal('900.00'),
            status='sent'
        )
    
    @patch('accounting.views_web.HTML')
    def test_receipt_pdf_generation(self, mock_html):
        """Test PDF generation for receipt."""
        mock_pdf = MagicMock()
        mock_html.return_value.write_pdf.return_value = b'fake pdf content'
        
        url = reverse('accounting:owner_receipt_pdf', kwargs={'receipt_pk': self.receipt.pk})
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertIn('attachment', response['Content-Disposition'])
    
    def test_receipt_pdf_invalid_receipt(self):
        """Test PDF generation with invalid receipt."""
        url = reverse('accounting:owner_receipt_pdf', kwargs={'receipt_pk': 99999})
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)


class OwnerReceiptViewsPermissionTest(TestCase):
    """Tests for view permissions."""
    
    def setUp(self):
        self.client = Client()
        
        # Create test data without logging in
        self.user = Agent.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.customer = Customer.objects.create(
            first_name='John',
            last_name='Doe',
            email='john@example.com'
        )
        
        self.invoice = Invoice.objects.create(
            customer=self.customer,
            date=timezone.now().date(),
            due_date=timezone.now().date() + timezone.timedelta(days=30),
            total_amount=Decimal('1000.00')
        )
    
    def test_views_require_login(self):
        """Test that all views require login."""
        views_to_test = [
            ('accounting:generate_owner_receipt', {'invoice_pk': self.invoice.pk}),
            ('accounting:preview_owner_receipt', {'invoice_pk': self.invoice.pk}),
            ('accounting:owner_receipts_list', {}),
        ]
        
        for view_name, kwargs in views_to_test:
            url = reverse(view_name, kwargs=kwargs)
            response = self.client.get(url)
            
            # Should redirect to login
            self.assertEqual(response.status_code, 302)
            self.assertIn('/login/', response.url)
         