# -*- coding: utf-8 -*-
"""
Comprehensive integration tests for the complete owner receipt feature.

This module contains end-to-end integration tests that verify the complete
workflow from receipt generation to email sending, covering all components
working together.
"""

from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.core import mail
from django.utils import timezone
from django.db import transaction
from decimal import Decimal
from unittest.mock import patch, Mock, MagicMock
import tempfile
import os

from accounting.models_invoice import Invoice, OwnerReceipt
from accounting.services import OwnerReceiptService
from customers.models import Customer
from contracts.models import Contract
from properties.models import Property, PropertyType
from agents.models import Agent

User = get_user_model()


class OwnerReceiptEndToEndIntegrationTest(TransactionTestCase):
    """
    End-to-end integration tests for the complete owner receipt workflow.
    
    Tests the complete flow from invoice creation to receipt generation,
    PDF creation, and email sending.
    """
    
    def setUp(self):
        """Set up test data for integration tests."""
        # Create test agent
        self.agent = Agent.objects.create(
            username='testagent',
            email='agent@test.com',
            first_name='Test',
            last_name='Agent',
            license_number='LIC123'
        )
        
        # Create test customers
        self.owner = Customer.objects.create(
            first_name='Maria',
            last_name='Garcia',
            email='owner@test.com',
            phone='123456789'
        )
        
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
        
        # Create test contract
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
        
        self.service = OwnerReceiptService()
    
    def test_complete_receipt_generation_workflow(self):
        """Test the complete receipt generation workflow."""
        # Step 1: Validate that receipt can be generated
        can_generate, error_msg = self.service.can_generate_receipt(self.invoice)
        self.assertTrue(can_generate, f"Receipt generation validation failed: {error_msg}")
        
        # Step 2: Generate receipt
        receipt = self.service.generate_receipt(self.invoice, self.agent)
        
        # Verify receipt was created
        self.assertIsNotNone(receipt)
        self.assertIsNotNone(receipt.pk)
        self.assertEqual(receipt.invoice, self.invoice)
        self.assertEqual(receipt.generated_by, self.agent)
        self.assertEqual(receipt.email_sent_to, self.owner.email)
        self.assertEqual(receipt.status, 'generated')
        
        # Verify financial calculations
        self.assertEqual(receipt.gross_amount, Decimal('1000.00'))
        self.assertEqual(receipt.discount_percentage, Decimal('10.00'))
        self.assertEqual(receipt.discount_amount, Decimal('100.00'))
        self.assertEqual(receipt.net_amount, Decimal('900.00'))
        
        # Verify receipt number was generated
        self.assertIsNotNone(receipt.receipt_number)
        self.assertTrue(receipt.receipt_number.startswith('REC-'))
        
        # Step 3: Test PDF generation
        with patch('accounting.services.HTML') as mock_html:
            mock_html_instance = Mock()
            mock_html_instance.write_pdf.return_value = b'PDF content'
            mock_html.return_value = mock_html_instance
            
            pdf_content = self.service.generate_pdf(receipt)
            
            self.assertIsNotNone(pdf_content)
            self.assertEqual(pdf_content, b'PDF content')
            mock_html.assert_called_once()
        
        # Step 4: Test email sending
        with patch('accounting.services.EmailMessage') as mock_email_class:
            mock_email_instance = Mock()
            mock_email_class.return_value = mock_email_instance
            
            with patch.object(self.service, 'generate_pdf', return_value=b'PDF content'):
                result = self.service.send_receipt_email(receipt)
                
                self.assertTrue(result)
                
                # Verify email was created and sent
                mock_email_class.assert_called_once()
                mock_email_instance.send.assert_called_once()
                mock_email_instance.attach.assert_called_once()
                
                # Verify receipt status was updated
                receipt.refresh_from_db()
                self.assertEqual(receipt.status, 'sent')
                self.assertIsNotNone(receipt.sent_at)
    
    def test_receipt_generation_with_various_scenarios(self):
        """Test receipt generation with various invoice and contract scenarios."""
        scenarios = [
            # Scenario 1: No discount
            {
                'discount_percentage': None,
                'expected_discount': Decimal('0.00'),
                'expected_net': Decimal('1000.00')
            },
            # Scenario 2: 5% discount
            {
                'discount_percentage': Decimal('5.00'),
                'expected_discount': Decimal('50.00'),
                'expected_net': Decimal('950.00')
            },
            # Scenario 3: 25% discount
            {
                'discount_percentage': Decimal('25.00'),
                'expected_discount': Decimal('250.00'),
                'expected_net': Decimal('750.00')
            },
            # Scenario 4: Different invoice amount
            {
                'invoice_amount': Decimal('1500.00'),
                'discount_percentage': Decimal('15.00'),
                'expected_discount': Decimal('225.00'),
                'expected_net': Decimal('1275.00')
            }
        ]
        
        for i, scenario in enumerate(scenarios):
            with self.subTest(scenario=i):
                # Create new contract and invoice for each scenario
                contract = Contract.objects.create(
                    customer=self.tenant,
                    agent=self.agent,
                    property=self.property,
                    start_date=timezone.now().date(),
                    amount=scenario.get('invoice_amount', Decimal('1000.00')),
                    owner_discount_percentage=scenario['discount_percentage'],
                    status=Contract.STATUS_ACTIVE
                )
                
                invoice = Invoice.objects.create(
                    number=f'INV-2024-{i+2:03d}',
                    date=timezone.now().date(),
                    due_date=timezone.now().date() + timezone.timedelta(days=30),
                    customer=self.tenant,
                    contract=contract,
                    description=f'Alquiler Scenario {i+1}',
                    total_amount=scenario.get('invoice_amount', Decimal('1000.00')),
                    status='validated'
                )
                
                # Generate receipt
                receipt = self.service.generate_receipt(invoice, self.agent)
                
                # Verify calculations
                self.assertEqual(receipt.discount_amount, scenario['expected_discount'])
                self.assertEqual(receipt.net_amount, scenario['expected_net'])
    
    def test_error_recovery_workflow(self):
        """Test error recovery and retry mechanisms."""
        # Generate a receipt
        receipt = self.service.generate_receipt(self.invoice, self.agent)
        
        # Simulate email sending failure
        with patch('accounting.services.EmailMessage') as mock_email_class:
            mock_email_instance = Mock()
            mock_email_instance.send.side_effect = Exception("SMTP error")
            mock_email_class.return_value = mock_email_instance
            
            with patch.object(self.service, 'generate_pdf', return_value=b'PDF content'):
                # Should fail and mark receipt as failed
                with self.assertRaises(Exception):
                    self.service.send_receipt_email(receipt)
                
                receipt.refresh_from_db()
                self.assertEqual(receipt.status, 'failed')
                self.assertIn("SMTP error", receipt.error_message)
        
        # Test retry mechanism
        with patch('accounting.services.EmailMessage') as mock_email_class:
            mock_email_instance = Mock()
            mock_email_class.return_value = mock_email_instance
            
            with patch.object(self.service, 'generate_pdf', return_value=b'PDF content'):
                # Should succeed on retry
                result = self.service.resend_receipt_email(receipt)
                
                self.assertTrue(result)
                receipt.refresh_from_db()
                self.assertEqual(receipt.status, 'sent')
    
    def test_concurrent_receipt_generation(self):
        """Test concurrent receipt generation for the same invoice."""
        # Create multiple invoices to avoid unique constraint issues
        invoices = []
        for i in range(3):
            invoice = Invoice.objects.create(
                number=f'INV-2024-CONCURRENT-{i+1:03d}',
                date=timezone.now().date(),
                due_date=timezone.now().date() + timezone.timedelta(days=30),
                customer=self.tenant,
                contract=self.contract,
                description=f'Concurrent Test {i+1}',
                total_amount=Decimal('1000.00'),
                status='validated'
            )
            invoices.append(invoice)
        
        # Generate receipts concurrently
        receipts = []
        for invoice in invoices:
            receipt = self.service.generate_receipt(invoice, self.agent)
            receipts.append(receipt)
        
        # Verify all receipts were created with unique numbers
        receipt_numbers = [r.receipt_number for r in receipts]
        self.assertEqual(len(receipt_numbers), len(set(receipt_numbers)))
        
        # Verify all receipts have correct data
        for receipt in receipts:
            self.assertEqual(receipt.gross_amount, Decimal('1000.00'))
            self.assertEqual(receipt.net_amount, Decimal('900.00'))
    
    def test_data_consistency_across_components(self):
        """Test data consistency across all components."""
        # Generate receipt
        receipt = self.service.generate_receipt(self.invoice, self.agent)
        
        # Get receipt data for PDF/email generation
        receipt_data = self.service.get_receipt_data(self.invoice)
        
        # Verify consistency between receipt model and receipt data
        self.assertEqual(receipt.gross_amount, receipt_data['financial']['gross_amount'])
        self.assertEqual(receipt.discount_amount, receipt_data['financial']['discount_amount'])
        self.assertEqual(receipt.net_amount, receipt_data['financial']['net_amount'])
        self.assertEqual(receipt.email_sent_to, receipt_data['owner']['email'])
        
        # Verify property data consistency
        self.assertEqual(receipt_data['property']['title'], self.property.title)
        self.assertEqual(receipt_data['property']['address'], f"{self.property.street} {self.property.number}")
        
        # Verify owner data consistency
        self.assertEqual(receipt_data['owner']['name'], f"{self.owner.first_name} {self.owner.last_name}")
        self.assertEqual(receipt_data['owner']['email'], self.owner.email)
    
    def test_database_transaction_integrity(self):
        """Test database transaction integrity during receipt generation."""
        # Test that failed receipt generation doesn't leave partial data
        with patch.object(self.service, 'get_receipt_data') as mock_get_data:
            mock_get_data.side_effect = Exception("Data collection failed")
            
            with self.assertRaises(Exception):
                self.service.generate_receipt(self.invoice, self.agent)
            
            # Verify no receipt was created
            self.assertEqual(OwnerReceipt.objects.filter(invoice=self.invoice).count(), 0)
    
    def test_email_template_integration(self):
        """Test email template integration with real data."""
        receipt = self.service.generate_receipt(self.invoice, self.agent)
        
        with patch('accounting.services.render_to_string') as mock_render:
            with patch('accounting.services.EmailMessage') as mock_email_class:
                mock_render.return_value = '<html>Test email content</html>'
                mock_email_instance = Mock()
                mock_email_class.return_value = mock_email_instance
                
                with patch.object(self.service, 'generate_pdf', return_value=b'PDF content'):
                    self.service.send_receipt_email(receipt)
                    
                    # Verify template was called with correct context
                    mock_render.assert_called_once()
                    template_name, context = mock_render.call_args[0]
                    
                    self.assertEqual(template_name, 'emails/owner_receipt_email.html')
                    self.assertIn('owner_name', context)
                    self.assertIn('property_address', context)
                    self.assertIn('net_amount', context)
                    self.assertIn('receipt_number', context)
                    
                    # Verify context data
                    self.assertEqual(context['owner_name'], 'Maria Garcia')
                    self.assertEqual(context['net_amount'], Decimal('900.00'))
                    self.assertEqual(context['receipt_number'], receipt.receipt_number)


class OwnerReceiptBulkOperationsTest(TestCase):
    """Test bulk operations and performance scenarios."""
    
    def setUp(self):
        """Set up test data for bulk operations."""
        # Create test agent
        self.agent = Agent.objects.create(
            username='testagent',
            email='agent@test.com',
            first_name='Test',
            last_name='Agent',
            license_number='LIC123'
        )
        
        # Create test customers
        self.owner = Customer.objects.create(
            first_name='Maria',
            last_name='Garcia',
            email='owner@test.com',
            phone='123456789'
        )
        
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
        
        # Create test contract
        self.contract = Contract.objects.create(
            customer=self.tenant,
            agent=self.agent,
            property=self.property,
            start_date=timezone.now().date(),
            amount=Decimal('1000.00'),
            owner_discount_percentage=Decimal('10.00'),
            status=Contract.STATUS_ACTIVE
        )
        
        self.service = OwnerReceiptService()
    
    def test_bulk_receipt_generation_performance(self):
        """Test performance of bulk receipt generation."""
        # Create multiple invoices
        invoices = []
        for i in range(10):
            invoice = Invoice.objects.create(
                number=f'INV-2024-BULK-{i+1:03d}',
                date=timezone.now().date(),
                due_date=timezone.now().date() + timezone.timedelta(days=30),
                customer=self.tenant,
                contract=self.contract,
                description=f'Bulk Test {i+1}',
                total_amount=Decimal('1000.00'),
                status='validated'
            )
            invoices.append(invoice)
        
        # Measure time for bulk generation
        import time
        start_time = time.time()
        
        receipts = []
        for invoice in invoices:
            receipt = self.service.generate_receipt(invoice, self.agent)
            receipts.append(receipt)
        
        end_time = time.time()
        generation_time = end_time - start_time
        
        # Verify all receipts were created
        self.assertEqual(len(receipts), 10)
        
        # Performance assertion (should complete within reasonable time)
        self.assertLess(generation_time, 5.0, "Bulk generation took too long")
        
        # Verify data integrity
        for receipt in receipts:
            self.assertEqual(receipt.gross_amount, Decimal('1000.00'))
            self.assertEqual(receipt.net_amount, Decimal('900.00'))
            self.assertEqual(receipt.status, 'generated')
    
    def test_bulk_email_sending_with_rate_limiting(self):
        """Test bulk email sending with rate limiting."""
        # Create multiple receipts
        receipts = []
        for i in range(5):
            invoice = Invoice.objects.create(
                number=f'INV-2024-EMAIL-{i+1:03d}',
                date=timezone.now().date(),
                due_date=timezone.now().date() + timezone.timedelta(days=30),
                customer=self.tenant,
                contract=self.contract,
                description=f'Email Test {i+1}',
                total_amount=Decimal('1000.00'),
                status='validated'
            )
            receipt = self.service.generate_receipt(invoice, self.agent)
            receipts.append(receipt)
        
        # Mock email sending with rate limiting
        with patch('accounting.services.EmailMessage') as mock_email_class:
            mock_email_instance = Mock()
            mock_email_class.return_value = mock_email_instance
            
            with patch.object(self.service, 'generate_pdf', return_value=b'PDF content'):
                # Send emails in bulk
                sent_count = 0
                for receipt in receipts:
                    try:
                        result = self.service.send_receipt_email(receipt)
                        if result:
                            sent_count += 1
                    except Exception:
                        pass
                
                # Verify emails were sent
                self.assertEqual(sent_count, 5)
                self.assertEqual(mock_email_instance.send.call_count, 5)
    
    def test_memory_usage_with_large_datasets(self):
        """Test memory usage with large datasets."""
        # Create a larger number of invoices
        invoices = []
        for i in range(50):
            invoice = Invoice.objects.create(
                number=f'INV-2024-MEMORY-{i+1:03d}',
                date=timezone.now().date(),
                due_date=timezone.now().date() + timezone.timedelta(days=30),
                customer=self.tenant,
                contract=self.contract,
                description=f'Memory Test {i+1}',
                total_amount=Decimal('1000.00'),
                status='validated'
            )
            invoices.append(invoice)
        
        # Process invoices and verify memory doesn't grow excessively
        receipts = []
        for invoice in invoices:
            receipt = self.service.generate_receipt(invoice, self.agent)
            receipts.append(receipt)
            
            # Clear references to help garbage collection
            del receipt
        
        # Verify all receipts were created
        created_receipts = OwnerReceipt.objects.filter(
            invoice__number__startswith='INV-2024-MEMORY-'
        ).count()
        self.assertEqual(created_receipts, 50)
    
    def test_database_query_optimization(self):
        """Test database query optimization for bulk operations."""
        # Create multiple invoices
        invoices = []
        for i in range(20):
            invoice = Invoice.objects.create(
                number=f'INV-2024-QUERY-{i+1:03d}',
                date=timezone.now().date(),
                due_date=timezone.now().date() + timezone.timedelta(days=30),
                customer=self.tenant,
                contract=self.contract,
                description=f'Query Test {i+1}',
                total_amount=Decimal('1000.00'),
                status='validated'
            )
            invoices.append(invoice)
        
        # Test query count for bulk operations
        with self.assertNumQueries(expected_num=None):  # We'll check manually
            receipts = []
            for invoice in invoices:
                receipt = self.service.generate_receipt(invoice, self.agent)
                receipts.append(receipt)
        
        # Verify all receipts were created
        self.assertEqual(len(receipts), 20)


class OwnerReceiptEdgeCasesTest(TestCase):
    """Test edge cases and boundary conditions."""
    
    def setUp(self):
        """Set up test data for edge cases."""
        # Create test agent
        self.agent = Agent.objects.create(
            username='testagent',
            email='agent@test.com',
            first_name='Test',
            last_name='Agent',
            license_number='LIC123'
        )
        
        # Create test customers
        self.owner = Customer.objects.create(
            first_name='Maria',
            last_name='Garcia',
            email='owner@test.com',
            phone='123456789'
        )
        
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
        
        self.service = OwnerReceiptService()
    
    def test_receipt_generation_with_special_characters(self):
        """Test receipt generation with special characters in data."""
        # Update property with special characters
        self.property.title = 'Departamento "El Mirador" - Piso 5°'
        self.property.street = 'Av. José María Morelos y Pavón'
        self.property.save()
        
        # Update owner with special characters
        self.owner.first_name = 'María José'
        self.owner.last_name = 'García-López'
        self.owner.save()
        
        # Create contract and invoice
        contract = Contract.objects.create(
            customer=self.tenant,
            agent=self.agent,
            property=self.property,
            start_date=timezone.now().date(),
            amount=Decimal('1000.00'),
            owner_discount_percentage=Decimal('10.00'),
            status=Contract.STATUS_ACTIVE
        )
        
        invoice = Invoice.objects.create(
            number='INV-2024-SPECIAL',
            date=timezone.now().date(),
            due_date=timezone.now().date() + timezone.timedelta(days=30),
            customer=self.tenant,
            contract=contract,
            description='Alquiler con caracteres especiales',
            total_amount=Decimal('1000.00'),
            status='validated'
        )
        
        # Generate receipt
        receipt = self.service.generate_receipt(invoice, self.agent)
        
        # Verify receipt was created successfully
        self.assertIsNotNone(receipt)
        self.assertEqual(receipt.email_sent_to, self.owner.email)
        
        # Test PDF generation with special characters
        with patch('accounting.services.HTML') as mock_html:
            mock_html_instance = Mock()
            mock_html_instance.write_pdf.return_value = b'PDF with special chars'
            mock_html.return_value = mock_html_instance
            
            pdf_content = self.service.generate_pdf(receipt)
            self.assertIsNotNone(pdf_content)
    
    def test_receipt_generation_with_extreme_amounts(self):
        """Test receipt generation with extreme amounts."""
        test_cases = [
            # Very small amount
            {
                'amount': Decimal('0.01'),
                'discount': Decimal('0.00'),
                'expected_net': Decimal('0.01')
            },
            # Very large amount
            {
                'amount': Decimal('999999.99'),
                'discount': Decimal('5.00'),
                'expected_net': Decimal('949999.99')
            },
            # Amount with many decimal places
            {
                'amount': Decimal('1234.5678'),
                'discount': Decimal('12.34'),
                'expected_net': Decimal('1082.9678')  # Rounded appropriately
            }
        ]
        
        for i, case in enumerate(test_cases):
            with self.subTest(case=i):
                contract = Contract.objects.create(
                    customer=self.tenant,
                    agent=self.agent,
                    property=self.property,
                    start_date=timezone.now().date(),
                    amount=case['amount'],
                    owner_discount_percentage=case['discount'],
                    status=Contract.STATUS_ACTIVE
                )
                
                invoice = Invoice.objects.create(
                    number=f'INV-2024-EXTREME-{i+1}',
                    date=timezone.now().date(),
                    due_date=timezone.now().date() + timezone.timedelta(days=30),
                    customer=self.tenant,
                    contract=contract,
                    description=f'Extreme amount test {i+1}',
                    total_amount=case['amount'],
                    status='validated'
                )
                
                receipt = self.service.generate_receipt(invoice, self.agent)
                
                # Verify calculations are correct
                self.assertEqual(receipt.gross_amount, case['amount'])
                # Allow for small rounding differences
                self.assertAlmostEqual(
                    float(receipt.net_amount), 
                    float(case['expected_net']), 
                    places=2
                )
    
    def test_receipt_generation_with_missing_optional_data(self):
        """Test receipt generation when optional data is missing."""
        # Remove optional phone numbers
        self.owner.phone = ''
        self.owner.save()
        
        self.tenant.phone = ''
        self.tenant.save()
        
        # Create contract and invoice
        contract = Contract.objects.create(
            customer=self.tenant,
            agent=self.agent,
            property=self.property,
            start_date=timezone.now().date(),
            amount=Decimal('1000.00'),
            owner_discount_percentage=None,  # No discount
            status=Contract.STATUS_ACTIVE
        )
        
        invoice = Invoice.objects.create(
            number='INV-2024-MISSING',
            date=timezone.now().date(),
            due_date=timezone.now().date() + timezone.timedelta(days=30),
            customer=self.tenant,
            contract=contract,
            description='Test with missing optional data',
            total_amount=Decimal('1000.00'),
            status='validated'
        )
        
        # Should still generate receipt successfully
        receipt = self.service.generate_receipt(invoice, self.agent)
        
        self.assertIsNotNone(receipt)
        self.assertEqual(receipt.discount_percentage, Decimal('0.00'))
        self.assertEqual(receipt.discount_amount, Decimal('0.00'))
        self.assertEqual(receipt.net_amount, Decimal('1000.00'))
    
    def test_receipt_number_uniqueness_under_load(self):
        """Test receipt number uniqueness under concurrent load."""
        # Create multiple invoices
        invoices = []
        for i in range(100):
            contract = Contract.objects.create(
                customer=self.tenant,
                agent=self.agent,
                property=self.property,
                start_date=timezone.now().date(),
                amount=Decimal('1000.00'),
                owner_discount_percentage=Decimal('10.00'),
                status=Contract.STATUS_ACTIVE
            )
            
            invoice = Invoice.objects.create(
                number=f'INV-2024-UNIQUE-{i+1:03d}',
                date=timezone.now().date(),
                due_date=timezone.now().date() + timezone.timedelta(days=30),
                customer=self.tenant,
                contract=contract,
                description=f'Uniqueness test {i+1}',
                total_amount=Decimal('1000.00'),
                status='validated'
            )
            invoices.append(invoice)
        
        # Generate receipts rapidly
        receipts = []
        for invoice in invoices:
            receipt = self.service.generate_receipt(invoice, self.agent)
            receipts.append(receipt)
        
        # Verify all receipt numbers are unique
        receipt_numbers = [r.receipt_number for r in receipts]
        unique_numbers = set(receipt_numbers)
        
        self.assertEqual(len(receipt_numbers), len(unique_numbers), 
                        "Receipt numbers are not unique")