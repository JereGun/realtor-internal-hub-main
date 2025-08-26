# -*- coding: utf-8 -*-
"""
UI and AJAX functionality tests for the owner receipt system.

This module contains tests for user interface interactions, AJAX requests,
JavaScript functionality, and frontend-backend integration.
"""

import json
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.http import JsonResponse
from decimal import Decimal
from unittest.mock import patch, Mock

from accounting.models_invoice import Invoice, OwnerReceipt
from accounting.services import OwnerReceiptService
from customers.models import Customer
from contracts.models import Contract
from properties.models import Property, PropertyType
from agents.models import Agent

User = get_user_model()


class OwnerReceiptAjaxViewsTest(TestCase):
    """Test AJAX functionality for owner receipt views."""
    
    def setUp(self):
        """Set up test data for AJAX tests."""
        self.client = Client()
        
        # Create test user/agent
        self.user = Agent.objects.create_user(
            username='ajaxuser',
            email='ajax@test.com',
            password='testpass123',
            first_name='Ajax',
            last_name='User',
            license_number='AJAX123'
        )
        self.client.login(username='ajaxuser', password='testpass123')
        
        # Create test customers
        self.owner = Customer.objects.create(
            first_name='Ajax',
            last_name='Owner',
            email='ajaxowner@test.com',
            phone='123456789'
        )
        
        self.tenant = Customer.objects.create(
            first_name='Ajax',
            last_name='Tenant',
            email='ajaxtenant@test.com',
            phone='987654321'
        )
        
        # Create property type
        self.property_type = PropertyType.objects.create(
            name='Ajax Test',
            description='Property type for AJAX testing'
        )
        
        # Create test property
        self.property = Property.objects.create(
            title='Ajax Test Property',
            description='Property for AJAX testing',
            property_type=self.property_type,
            street='Ajax St',
            number='123',
            neighborhood='Test Area',
            total_surface=Decimal('100.00'),
            bedrooms=2,
            bathrooms=1,
            agent=self.user,
            owner=self.owner
        )
        
        # Create test contract
        self.contract = Contract.objects.create(
            customer=self.tenant,
            agent=self.user,
            property=self.property,
            start_date=timezone.now().date(),
            amount=Decimal('1000.00'),
            owner_discount_percentage=Decimal('10.00'),
            status=Contract.STATUS_ACTIVE
        )
        
        # Create test invoice
        self.invoice = Invoice.objects.create(
            number='AJAX-INV-001',
            date=timezone.now().date(),
            due_date=timezone.now().date() + timezone.timedelta(days=30),
            customer=self.tenant,
            contract=self.contract,
            description='AJAX test invoice',
            total_amount=Decimal('1000.00'),
            status='validated'
        )
    
    def test_ajax_generate_receipt_success(self):
        """Test successful AJAX receipt generation."""
        url = reverse('accounting:generate_owner_receipt', kwargs={'invoice_pk': self.invoice.pk})
        
        with patch.object(OwnerReceiptService, 'generate_receipt') as mock_generate:
            mock_receipt = Mock()
            mock_receipt.pk = 1
            mock_receipt.receipt_number = 'REC-AJAX-001'
            mock_receipt.status = 'generated'
            mock_generate.return_value = mock_receipt
            
            response = self.client.post(
                url,
                {'send_email': 'true'},
                HTTP_X_REQUESTED_WITH='XMLHttpRequest',
                content_type='application/x-www-form-urlencoded'
            )
            
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response['Content-Type'], 'application/json')
            
            data = json.loads(response.content)
            self.assertTrue(data['success'])
            self.assertEqual(data['receipt_number'], 'REC-AJAX-001')
            self.assertIn('message', data)
            self.assertIn('receipt_id', data)
    
    def test_ajax_generate_receipt_validation_error(self):
        """Test AJAX receipt generation with validation error."""
        # Make invoice invalid
        self.invoice.status = 'draft'
        self.invoice.save()
        
        url = reverse('accounting:generate_owner_receipt', kwargs={'invoice_pk': self.invoice.pk})
        
        response = self.client.post(
            url,
            {'send_email': 'false'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertFalse(data['success'])
        self.assertIn('error', data)
        self.assertIn('debe estar validada', data['error'])
    
    def test_ajax_generate_receipt_service_error(self):
        """Test AJAX receipt generation with service error."""
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
    
    def test_ajax_preview_receipt_success(self):
        """Test successful AJAX receipt preview."""
        url = reverse('accounting:preview_owner_receipt', kwargs={'invoice_pk': self.invoice.pk})
        
        with patch.object(OwnerReceiptService, 'get_receipt_data') as mock_get_data:
            mock_get_data.return_value = {
                'invoice': {
                    'number': 'AJAX-INV-001',
                    'date': self.invoice.date,
                    'total_amount': Decimal('1000.00')
                },
                'financial': {
                    'gross_amount': Decimal('1000.00'),
                    'discount_amount': Decimal('100.00'),
                    'net_amount': Decimal('900.00')
                },
                'owner': {
                    'name': 'Ajax Owner',
                    'email': 'ajaxowner@test.com'
                },
                'property': {
                    'title': 'Ajax Test Property',
                    'address': 'Ajax St 123'
                }
            }
            
            response = self.client.get(
                url,
                HTTP_X_REQUESTED_WITH='XMLHttpRequest'
            )
            
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.content)
            self.assertTrue(data['success'])
            self.assertIn('preview_html', data)
            self.assertIn('receipt_data', data)
    
    def test_ajax_resend_receipt_success(self):
        """Test successful AJAX receipt resend."""
        # Create a failed receipt
        receipt = OwnerReceipt.objects.create(
            invoice=self.invoice,
            receipt_number='REC-AJAX-RESEND-001',
            generated_by=self.user,
            email_sent_to=self.owner.email,
            gross_amount=Decimal('1000.00'),
            discount_amount=Decimal('100.00'),
            net_amount=Decimal('900.00'),
            status='failed',
            error_message='Previous error'
        )
        
        url = reverse('accounting:resend_owner_receipt', kwargs={'receipt_pk': receipt.pk})
        
        with patch.object(OwnerReceiptService, 'resend_receipt_email') as mock_resend:
            mock_resend.return_value = True
            
            response = self.client.post(
                url,
                HTTP_X_REQUESTED_WITH='XMLHttpRequest'
            )
            
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.content)
            self.assertTrue(data['success'])
            self.assertIn('message', data)
    
    def test_ajax_resend_receipt_error(self):
        """Test AJAX receipt resend with error."""
        # Create a sent receipt (cannot be resent)
        receipt = OwnerReceipt.objects.create(
            invoice=self.invoice,
            receipt_number='REC-AJAX-RESEND-ERROR-001',
            generated_by=self.user,
            email_sent_to=self.owner.email,
            gross_amount=Decimal('1000.00'),
            discount_amount=Decimal('100.00'),
            net_amount=Decimal('900.00'),
            status='sent'
        )
        
        url = reverse('accounting:resend_owner_receipt', kwargs={'receipt_pk': receipt.pk})
        
        response = self.client.post(
            url,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertFalse(data['success'])
        self.assertIn('error', data)
    
    def test_ajax_receipt_status_check(self):
        """Test AJAX receipt status checking."""
        receipt = OwnerReceipt.objects.create(
            invoice=self.invoice,
            receipt_number='REC-AJAX-STATUS-001',
            generated_by=self.user,
            email_sent_to=self.owner.email,
            gross_amount=Decimal('1000.00'),
            discount_amount=Decimal('100.00'),
            net_amount=Decimal('900.00'),
            status='sent'
        )
        
        url = reverse('accounting:owner_receipt_status', kwargs={'receipt_pk': receipt.pk})
        
        response = self.client.get(
            url,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(data['status'], 'sent')
        self.assertIn('status_display', data)
        self.assertIn('can_resend', data)
    
    def test_ajax_bulk_receipt_generation(self):
        """Test AJAX bulk receipt generation."""
        # Create multiple invoices
        invoices = []
        for i in range(3):
            invoice = Invoice.objects.create(
                number=f'AJAX-BULK-INV-{i+1:03d}',
                date=timezone.now().date(),
                due_date=timezone.now().date() + timezone.timedelta(days=30),
                customer=self.tenant,
                contract=self.contract,
                description=f'AJAX bulk test invoice {i+1}',
                total_amount=Decimal('1000.00'),
                status='validated'
            )
            invoices.append(invoice)
        
        url = reverse('accounting:bulk_generate_owner_receipts')
        invoice_ids = [str(inv.pk) for inv in invoices]
        
        with patch.object(OwnerReceiptService, 'generate_receipt') as mock_generate:
            mock_receipts = []
            for i, invoice in enumerate(invoices):
                mock_receipt = Mock()
                mock_receipt.pk = i + 1
                mock_receipt.receipt_number = f'REC-AJAX-BULK-{i+1:03d}'
                mock_receipt.status = 'generated'
                mock_receipts.append(mock_receipt)
            
            mock_generate.side_effect = mock_receipts
            
            response = self.client.post(
                url,
                {
                    'invoice_ids': invoice_ids,
                    'send_email': 'true'
                },
                HTTP_X_REQUESTED_WITH='XMLHttpRequest'
            )
            
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.content)
            self.assertTrue(data['success'])
            self.assertEqual(data['generated_count'], 3)
            self.assertEqual(len(data['receipts']), 3)
    
    def test_ajax_receipt_list_filtering(self):
        """Test AJAX receipt list filtering."""
        # Create receipts with different statuses
        statuses = ['generated', 'sent', 'failed']
        receipts = []
        
        for i, status in enumerate(statuses):
            receipt = OwnerReceipt.objects.create(
                invoice=self.invoice,
                receipt_number=f'REC-AJAX-FILTER-{i+1:03d}',
                generated_by=self.user,
                email_sent_to=self.owner.email,
                gross_amount=Decimal('1000.00'),
                discount_amount=Decimal('100.00'),
                net_amount=Decimal('900.00'),
                status=status
            )
            receipts.append(receipt)
        
        url = reverse('accounting:owner_receipts_list')
        
        # Test filtering by status
        response = self.client.get(
            url,
            {'status': 'sent', 'ajax': '1'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(len(data['receipts']), 1)
        self.assertEqual(data['receipts'][0]['status'], 'sent')
    
    def test_ajax_error_handling_with_invalid_data(self):
        """Test AJAX error handling with invalid data."""
        url = reverse('accounting:generate_owner_receipt', kwargs={'invoice_pk': 99999})
        
        response = self.client.post(
            url,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.content)
        self.assertFalse(data['success'])
        self.assertIn('error', data)
    
    def test_ajax_response_format_consistency(self):
        """Test that all AJAX responses follow consistent format."""
        # Test successful response format
        url = reverse('accounting:preview_owner_receipt', kwargs={'invoice_pk': self.invoice.pk})
        
        with patch.object(OwnerReceiptService, 'get_receipt_data') as mock_get_data:
            mock_get_data.return_value = {'test': 'data'}
            
            response = self.client.get(
                url,
                HTTP_X_REQUESTED_WITH='XMLHttpRequest'
            )
            
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.content)
            
            # Check required fields in successful response
            self.assertIn('success', data)
            self.assertTrue(data['success'])
            
        # Test error response format
        self.invoice.status = 'draft'
        self.invoice.save()
        
        response = self.client.get(
            url,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        data = json.loads(response.content)
        
        # Check required fields in error response
        self.assertIn('success', data)
        self.assertFalse(data['success'])
        self.assertIn('error', data)


class OwnerReceiptUIIntegrationTest(TestCase):
    """Test UI integration and user interface functionality."""
    
    def setUp(self):
        """Set up test data for UI integration tests."""
        self.client = Client()
        
        # Create test user/agent
        self.user = Agent.objects.create_user(
            username='uiuser',
            email='ui@test.com',
            password='testpass123',
            first_name='UI',
            last_name='User',
            license_number='UI123'
        )
        self.client.login(username='uiuser', password='testpass123')
        
        # Create test customers
        self.owner = Customer.objects.create(
            first_name='UI',
            last_name='Owner',
            email='uiowner@test.com',
            phone='123456789'
        )
        
        self.tenant = Customer.objects.create(
            first_name='UI',
            last_name='Tenant',
            email='uitenant@test.com',
            phone='987654321'
        )
        
        # Create property type
        self.property_type = PropertyType.objects.create(
            name='UI Test',
            description='Property type for UI testing'
        )
        
        # Create test property
        self.property = Property.objects.create(
            title='UI Test Property',
            description='Property for UI testing',
            property_type=self.property_type,
            street='UI St',
            number='123',
            neighborhood='Test Area',
            total_surface=Decimal('100.00'),
            bedrooms=2,
            bathrooms=1,
            agent=self.user,
            owner=self.owner
        )
        
        # Create test contract
        self.contract = Contract.objects.create(
            customer=self.tenant,
            agent=self.user,
            property=self.property,
            start_date=timezone.now().date(),
            amount=Decimal('1000.00'),
            owner_discount_percentage=Decimal('10.00'),
            status=Contract.STATUS_ACTIVE
        )
        
        # Create test invoice
        self.invoice = Invoice.objects.create(
            number='UI-INV-001',
            date=timezone.now().date(),
            due_date=timezone.now().date() + timezone.timedelta(days=30),
            customer=self.tenant,
            contract=self.contract,
            description='UI test invoice',
            total_amount=Decimal('1000.00'),
            status='validated'
        )
    
    def test_invoice_list_receipt_buttons(self):
        """Test receipt generation buttons in invoice list."""
        url = reverse('accounting:invoice_list')
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Generar Comprobante Propietario')
        self.assertContains(response, f'data-invoice-id="{self.invoice.pk}"')
        
        # Check that JavaScript is included
        self.assertContains(response, 'owner-receipt.js')
    
    def test_invoice_detail_receipt_section(self):
        """Test receipt section in invoice detail page."""
        url = reverse('accounting:invoice_detail', kwargs={'pk': self.invoice.pk})
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Comprobantes del Propietario')
        self.assertContains(response, 'Generar Nuevo Comprobante')
    
    def test_receipt_generation_modal(self):
        """Test receipt generation modal functionality."""
        url = reverse('accounting:generate_owner_receipt', kwargs={'invoice_pk': self.invoice.pk})
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Generar Comprobante para Propietario')
        self.assertContains(response, 'Vista Previa')
        self.assertContains(response, 'Enviar por Email')
        
        # Check form elements
        self.assertContains(response, 'name="send_email"')
        self.assertContains(response, 'type="checkbox"')
    
    def test_receipt_preview_modal(self):
        """Test receipt preview modal functionality."""
        url = reverse('accounting:preview_owner_receipt', kwargs={'invoice_pk': self.invoice.pk})
        
        with patch.object(OwnerReceiptService, 'get_receipt_data') as mock_get_data:
            mock_get_data.return_value = {
                'invoice': {
                    'number': 'UI-INV-001',
                    'date': self.invoice.date,
                    'total_amount': Decimal('1000.00')
                },
                'financial': {
                    'gross_amount': Decimal('1000.00'),
                    'discount_amount': Decimal('100.00'),
                    'net_amount': Decimal('900.00')
                },
                'owner': {
                    'name': 'UI Owner',
                    'email': 'uiowner@test.com'
                },
                'property': {
                    'title': 'UI Test Property',
                    'address': 'UI St 123'
                }
            }
            
            response = self.client.get(url)
            
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'Vista Previa del Comprobante')
            self.assertContains(response, 'UI-INV-001')
            self.assertContains(response, 'UI Owner')
            self.assertContains(response, '$1,000.00')
            self.assertContains(response, '$900.00')
    
    def test_receipt_list_interface(self):
        """Test receipt list interface."""
        # Create test receipts
        receipts = []
        for i in range(3):
            receipt = OwnerReceipt.objects.create(
                invoice=self.invoice,
                receipt_number=f'REC-UI-{i+1:03d}',
                generated_by=self.user,
                email_sent_to=self.owner.email,
                gross_amount=Decimal('1000.00'),
                discount_amount=Decimal('100.00'),
                net_amount=Decimal('900.00'),
                status=['generated', 'sent', 'failed'][i]
            )
            receipts.append(receipt)
        
        url = reverse('accounting:owner_receipts_list')
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Lista de Comprobantes')
        
        # Check that all receipts are displayed
        for receipt in receipts:
            self.assertContains(response, receipt.receipt_number)
        
        # Check filter controls
        self.assertContains(response, 'Filtrar por Estado')
        self.assertContains(response, 'Buscar')
        
        # Check action buttons
        self.assertContains(response, 'Reenviar')
        self.assertContains(response, 'Ver Detalle')
    
    def test_receipt_detail_interface(self):
        """Test receipt detail interface."""
        receipt = OwnerReceipt.objects.create(
            invoice=self.invoice,
            receipt_number='REC-UI-DETAIL-001',
            generated_by=self.user,
            email_sent_to=self.owner.email,
            gross_amount=Decimal('1000.00'),
            discount_amount=Decimal('100.00'),
            net_amount=Decimal('900.00'),
            status='sent'
        )
        
        url = reverse('accounting:owner_receipt_detail', kwargs={'receipt_pk': receipt.pk})
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Detalle del Comprobante')
        self.assertContains(response, 'REC-UI-DETAIL-001')
        self.assertContains(response, 'uiowner@test.com')
        self.assertContains(response, '$1,000.00')
        self.assertContains(response, '$900.00')
        
        # Check action buttons
        self.assertContains(response, 'Descargar PDF')
        self.assertContains(response, 'Ver Factura')
    
    def test_error_message_display(self):
        """Test error message display in UI."""
        # Create invalid invoice
        self.invoice.status = 'draft'
        self.invoice.save()
        
        url = reverse('accounting:generate_owner_receipt', kwargs={'invoice_pk': self.invoice.pk})
        
        response = self.client.post(url, {'send_email': 'false'})
        
        # Should redirect with error message
        self.assertEqual(response.status_code, 302)
        
        # Follow redirect to see error message
        response = self.client.get(response.url)
        self.assertContains(response, 'debe estar validada')
    
    def test_success_message_display(self):
        """Test success message display in UI."""
        url = reverse('accounting:generate_owner_receipt', kwargs={'invoice_pk': self.invoice.pk})
        
        with patch.object(OwnerReceiptService, 'generate_receipt') as mock_generate:
            mock_receipt = Mock()
            mock_receipt.pk = 1
            mock_receipt.receipt_number = 'REC-UI-SUCCESS-001'
            mock_generate.return_value = mock_receipt
            
            response = self.client.post(url, {'send_email': 'false'})
            
            # Should redirect with success message
            self.assertEqual(response.status_code, 302)
            
            # Follow redirect to see success message
            response = self.client.get(response.url)
            self.assertContains(response, 'generado exitosamente')
    
    def test_responsive_design_elements(self):
        """Test responsive design elements in templates."""
        url = reverse('accounting:owner_receipts_list')
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        
        # Check for responsive CSS classes
        self.assertContains(response, 'table-responsive')
        self.assertContains(response, 'btn-group')
        self.assertContains(response, 'form-control')
        
        # Check for mobile-friendly elements
        self.assertContains(response, 'viewport')
    
    def test_accessibility_features(self):
        """Test accessibility features in UI."""
        url = reverse('accounting:generate_owner_receipt', kwargs={'invoice_pk': self.invoice.pk})
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        
        # Check for accessibility attributes
        self.assertContains(response, 'aria-label')
        self.assertContains(response, 'role=')
        
        # Check for proper form labels
        self.assertContains(response, '<label')
        self.assertContains(response, 'for=')
    
    def test_javascript_integration(self):
        """Test JavaScript integration in templates."""
        url = reverse('accounting:invoice_list')
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        
        # Check for JavaScript files
        self.assertContains(response, 'owner-receipt.js')
        
        # Check for JavaScript configuration
        self.assertContains(response, 'data-ajax-url')
        self.assertContains(response, 'data-csrf-token')
    
    def test_css_styling_integration(self):
        """Test CSS styling integration."""
        url = reverse('accounting:owner_receipts_list')
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        
        # Check for CSS classes
        self.assertContains(response, 'owner-receipt-list')
        self.assertContains(response, 'receipt-status')
        self.assertContains(response, 'receipt-actions')
        
        # Check for status-specific styling
        self.assertContains(response, 'status-sent')
        self.assertContains(response, 'status-failed')
        self.assertContains(response, 'status-generated')


class OwnerReceiptJavaScriptFunctionalityTest(TestCase):
    """Test JavaScript functionality through Django test client."""
    
    def setUp(self):
        """Set up test data for JavaScript functionality tests."""
        self.client = Client()
        
        # Create test user/agent
        self.user = Agent.objects.create_user(
            username='jsuser',
            email='js@test.com',
            password='testpass123',
            first_name='JS',
            last_name='User',
            license_number='JS123'
        )
        self.client.login(username='jsuser', password='testpass123')
        
        # Create minimal test data
        self.owner = Customer.objects.create(
            first_name='JS',
            last_name='Owner',
            email='jsowner@test.com'
        )
        
        self.tenant = Customer.objects.create(
            first_name='JS',
            last_name='Tenant',
            email='jstenant@test.com'
        )
        
        self.property_type = PropertyType.objects.create(
            name='JS Test',
            description='Property type for JS testing'
        )
        
        self.property = Property.objects.create(
            title='JS Test Property',
            property_type=self.property_type,
            street='JS St',
            number='123',
            agent=self.user,
            owner=self.owner
        )
        
        self.contract = Contract.objects.create(
            customer=self.tenant,
            agent=self.user,
            property=self.property,
            start_date=timezone.now().date(),
            amount=Decimal('1000.00'),
            owner_discount_percentage=Decimal('10.00'),
            status=Contract.STATUS_ACTIVE
        )
        
        self.invoice = Invoice.objects.create(
            number='JS-INV-001',
            date=timezone.now().date(),
            due_date=timezone.now().date() + timezone.timedelta(days=30),
            customer=self.tenant,
            contract=self.contract,
            description='JS test invoice',
            total_amount=Decimal('1000.00'),
            status='validated'
        )
    
    def test_ajax_form_submission_handling(self):
        """Test AJAX form submission handling."""
        url = reverse('accounting:generate_owner_receipt', kwargs={'invoice_pk': self.invoice.pk})
        
        # Simulate AJAX form submission
        with patch.object(OwnerReceiptService, 'generate_receipt') as mock_generate:
            mock_receipt = Mock()
            mock_receipt.pk = 1
            mock_receipt.receipt_number = 'REC-JS-001'
            mock_generate.return_value = mock_receipt
            
            response = self.client.post(
                url,
                {
                    'send_email': 'true',
                    'ajax': '1'
                },
                HTTP_X_REQUESTED_WITH='XMLHttpRequest'
            )
            
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.content)
            self.assertTrue(data['success'])
    
    def test_dynamic_content_loading(self):
        """Test dynamic content loading via AJAX."""
        # Create receipts for dynamic loading
        receipts = []
        for i in range(5):
            receipt = OwnerReceipt.objects.create(
                invoice=self.invoice,
                receipt_number=f'REC-JS-DYNAMIC-{i+1:03d}',
                generated_by=self.user,
                email_sent_to=self.owner.email,
                gross_amount=Decimal('1000.00'),
                discount_amount=Decimal('100.00'),
                net_amount=Decimal('900.00'),
                status=['generated', 'sent'][i % 2]
            )
            receipts.append(receipt)
        
        url = reverse('accounting:owner_receipts_list')
        
        # Test pagination via AJAX
        response = self.client.get(
            url,
            {'page': '1', 'ajax': '1'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertIn('receipts', data)
    
    def test_real_time_status_updates(self):
        """Test real-time status updates via AJAX polling."""
        receipt = OwnerReceipt.objects.create(
            invoice=self.invoice,
            receipt_number='REC-JS-STATUS-001',
            generated_by=self.user,
            email_sent_to=self.owner.email,
            gross_amount=Decimal('1000.00'),
            discount_amount=Decimal('100.00'),
            net_amount=Decimal('900.00'),
            status='generated'
        )
        
        url = reverse('accounting:owner_receipt_status', kwargs={'receipt_pk': receipt.pk})
        
        # Initial status check
        response = self.client.get(
            url,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'generated')
        
        # Update status and check again
        receipt.status = 'sent'
        receipt.save()
        
        response = self.client.get(
            url,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'sent')
    
    def test_client_side_validation_simulation(self):
        """Test client-side validation through server responses."""
        url = reverse('accounting:generate_owner_receipt', kwargs={'invoice_pk': self.invoice.pk})
        
        # Test missing required data
        response = self.client.post(
            url,
            {},  # Empty data
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        # Should handle gracefully
        self.assertIn(response.status_code, [200, 400])
        
        if response.status_code == 400:
            data = json.loads(response.content)
            self.assertFalse(data['success'])
            self.assertIn('error', data)
    
    def test_progress_indication_endpoints(self):
        """Test endpoints that support progress indication."""
        # Create multiple invoices for bulk operation
        invoices = []
        for i in range(3):
            invoice = Invoice.objects.create(
                number=f'JS-PROGRESS-INV-{i+1:03d}',
                date=timezone.now().date(),
                due_date=timezone.now().date() + timezone.timedelta(days=30),
                customer=self.tenant,
                contract=self.contract,
                description=f'JS progress test invoice {i+1}',
                total_amount=Decimal('1000.00'),
                status='validated'
            )
            invoices.append(invoice)
        
        url = reverse('accounting:bulk_generate_owner_receipts')
        invoice_ids = [str(inv.pk) for inv in invoices]
        
        with patch.object(OwnerReceiptService, 'generate_receipt') as mock_generate:
            mock_receipts = []
            for i, invoice in enumerate(invoices):
                mock_receipt = Mock()
                mock_receipt.pk = i + 1
                mock_receipt.receipt_number = f'REC-JS-PROGRESS-{i+1:03d}'
                mock_receipts.append(mock_receipt)
            
            mock_generate.side_effect = mock_receipts
            
            response = self.client.post(
                url,
                {
                    'invoice_ids': invoice_ids,
                    'progress': '1'
                },
                HTTP_X_REQUESTED_WITH='XMLHttpRequest'
            )
            
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.content)
            self.assertTrue(data['success'])
            self.assertIn('progress', data)
            self.assertIn('total', data)
            self.assertIn('completed', data)