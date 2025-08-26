"""
Tests for OwnerReceipt admin interface functionality.
"""
from django.test import TestCase, RequestFactory
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.contrib.messages.storage.fallback import FallbackStorage
from django.utils import timezone
from decimal import Decimal

from accounting.admin import OwnerReceiptAdmin
from accounting.models_invoice import OwnerReceipt, Invoice
from customers.models import Customer
from agents.models import Agent


User = get_user_model()


class MockRequest:
    """Mock request object for testing admin actions"""
    def __init__(self, user=None):
        self.user = user or User()
        self.META = {}
        self._messages = FallbackStorage(self)


class OwnerReceiptAdminTest(TestCase):
    """Test cases for OwnerReceipt admin interface"""
    
    def setUp(self):
        """Set up test data"""
        self.site = AdminSite()
        self.admin = OwnerReceiptAdmin(OwnerReceipt, self.site)
        self.factory = RequestFactory()
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create test customer
        self.customer = Customer.objects.create(
            first_name='Test',
            last_name='Customer',
            email='customer@example.com'
        )
        
        # Create test agent
        self.agent = Agent.objects.create(
            first_name='Test',
            last_name='Agent',
            email='agent@example.com',
            license_number='12345'
        )
        
        # Create test invoice
        self.invoice = Invoice.objects.create(
            number='INV-2024-001',
            date=timezone.now().date(),
            due_date=timezone.now().date(),
            customer=self.customer,
            description='Test invoice',
            total_amount=Decimal('1000.00'),
            status='validated'
        )
        
        # Create test receipt
        self.receipt = OwnerReceipt.objects.create(
            invoice=self.invoice,
            generated_by=self.agent,
            email_sent_to='owner@example.com',
            gross_amount=Decimal('1000.00'),
            discount_percentage=Decimal('10.00'),
            discount_amount=Decimal('100.00'),
            net_amount=Decimal('900.00'),
            status='generated'
        )
    
    def test_list_display_fields(self):
        """Test that list display fields are correctly configured"""
        expected_fields = [
            'receipt_number',
            'invoice_link',
            'status_display',
            'generated_at',
            'sent_at',
            'email_sent_to',
            'gross_amount',
            'discount_amount',
            'net_amount',
            'generated_by'
        ]
        
        self.assertEqual(list(self.admin.list_display), expected_fields)
    
    def test_search_fields(self):
        """Test that search fields are correctly configured"""
        expected_fields = [
            'receipt_number',
            'invoice__number',
            'email_sent_to',
            'invoice__customer__first_name',
            'invoice__customer__last_name',
            'generated_by__first_name',
            'generated_by__last_name'
        ]
        
        self.assertEqual(list(self.admin.search_fields), expected_fields)
    
    def test_readonly_fields(self):
        """Test that readonly fields are correctly configured"""
        expected_fields = [
            'receipt_number',
            'generated_at',
            'sent_at',
            'gross_amount',
            'discount_percentage',
            'discount_amount',
            'net_amount',
            'pdf_file_path'
        ]
        
        self.assertEqual(list(self.admin.readonly_fields), expected_fields)
    
    def test_invoice_link_display(self):
        """Test the invoice_link display method"""
        link_html = self.admin.invoice_link(self.receipt)
        
        self.assertIn(self.invoice.number, link_html)
        self.assertIn('href=', link_html)
        self.assertIn('<a', link_html)
    
    def test_status_display_method(self):
        """Test the status_display method with color coding"""
        # Test generated status
        self.receipt.status = 'generated'
        status_html = self.admin.status_display(self.receipt)
        self.assertIn('#ffc107', status_html)  # Yellow color
        self.assertIn('Generado', status_html)
        
        # Test sent status
        self.receipt.status = 'sent'
        status_html = self.admin.status_display(self.receipt)
        self.assertIn('#28a745', status_html)  # Green color
        self.assertIn('Enviado', status_html)
        
        # Test failed status
        self.receipt.status = 'failed'
        status_html = self.admin.status_display(self.receipt)
        self.assertIn('#dc3545', status_html)  # Red color
        self.assertIn('Error en envío', status_html)
    
    def test_mark_as_sent_action(self):
        """Test the mark_as_sent bulk action"""
        request = MockRequest(self.user)
        queryset = OwnerReceipt.objects.filter(pk=self.receipt.pk)
        
        # Execute the action
        self.admin.mark_as_sent(request, queryset)
        
        # Refresh from database
        self.receipt.refresh_from_db()
        
        # Check that status was updated
        self.assertEqual(self.receipt.status, 'sent')
        self.assertIsNotNone(self.receipt.sent_at)
    
    def test_mark_as_failed_action(self):
        """Test the mark_as_failed bulk action"""
        request = MockRequest(self.user)
        queryset = OwnerReceipt.objects.filter(pk=self.receipt.pk)
        
        # Execute the action
        self.admin.mark_as_failed(request, queryset)
        
        # Refresh from database
        self.receipt.refresh_from_db()
        
        # Check that status was updated
        self.assertEqual(self.receipt.status, 'failed')
        self.assertIn('Marcado como fallido desde admin', self.receipt.error_message)
    
    def test_export_receipt_data_action(self):
        """Test the export_receipt_data bulk action"""
        request = MockRequest(self.user)
        queryset = OwnerReceipt.objects.filter(pk=self.receipt.pk)
        
        # Execute the action
        response = self.admin.export_receipt_data(request, queryset)
        
        # Check response
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertIn('attachment', response['Content-Disposition'])
        self.assertIn('comprobantes_propietarios_', response['Content-Disposition'])
        
        # Check CSV content
        content = response.content.decode('utf-8')
        self.assertIn('Número Comprobante', content)  # Header
        self.assertIn(self.receipt.receipt_number, content)  # Data
    
    def test_delete_permission_for_sent_receipts(self):
        """Test that sent receipts cannot be deleted"""
        # Test with generated receipt (should allow delete)
        self.receipt.status = 'generated'
        self.receipt.save()
        self.assertTrue(self.admin.has_delete_permission(MockRequest(self.user), self.receipt))
        
        # Test with sent receipt (should not allow delete)
        self.receipt.status = 'sent'
        self.receipt.save()
        self.assertFalse(self.admin.has_delete_permission(MockRequest(self.user), self.receipt))
    
    def test_get_queryset_optimization(self):
        """Test that queryset is optimized with select_related"""
        request = MockRequest(self.user)
        queryset = self.admin.get_queryset(request)
        
        # Check that select_related is applied
        self.assertIn('invoice', queryset.query.select_related)
        self.assertIn('invoice__customer', queryset.query.select_related)
        self.assertIn('generated_by', queryset.query.select_related)
    
    def test_admin_actions_list(self):
        """Test that all expected admin actions are configured"""
        expected_actions = [
            'mark_as_sent',
            'mark_as_failed',
            'resend_receipts',
            'export_receipt_data'
        ]
        
        for action in expected_actions:
            self.assertIn(action, self.admin.actions)
    
    def test_fieldsets_configuration(self):
        """Test that fieldsets are properly configured"""
        fieldsets = self.admin.fieldsets
        
        # Check that we have the expected number of fieldsets
        self.assertEqual(len(fieldsets), 4)
        
        # Check fieldset names
        fieldset_names = [fieldset[0] for fieldset in fieldsets]
        expected_names = [
            "Información del Comprobante",
            "Estado y Envío",
            "Montos Calculados",
            "Archivo"
        ]
        
        self.assertEqual(fieldset_names, expected_names)
    
    def test_list_filters_configuration(self):
        """Test that list filters are properly configured"""
        from accounting.admin import ReceiptStatusFilter, ReceiptDateFilter
        
        # Check that custom filters are included
        self.assertIn(ReceiptStatusFilter, self.admin.list_filter)
        self.assertIn(ReceiptDateFilter, self.admin.list_filter)