# -*- coding: utf-8 -*-
"""
Complete integration tests for the owner receipt feature.

This module provides comprehensive integration tests that cover all aspects
of the owner receipt system working together, including edge cases and
real-world scenarios.
"""

import time
import json
from decimal import Decimal
from django.test import TestCase, TransactionTestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from django.core import mail
from django.db import transaction
from unittest.mock import patch, Mock, MagicMock

from accounting.models_invoice import Invoice, OwnerReceipt
from accounting.services import OwnerReceiptService
from customers.models import Customer
from contracts.models import Contract
from properties.models import Property, PropertyType
from agents.models import Agent

User = get_user_model()


class OwnerReceiptCompleteWorkflowTest(TransactionTestCase):
    """
    Complete workflow tests covering the entire owner receipt process
    from invoice creation to email delivery and status tracking.
    """
    
    def setUp(self):
        """Set up comprehensive test data."""
        # Create test agent
        self.agent = Agent.objects.create(
            username='workflowagent',
            email='workflow@test.com',
            first_name='Workflow',
            last_name='Agent',
            license_number='WF123'
        )
        
        # Create test customers
        self.owner = Customer.objects.create(
            first_name='Complete',
            last_name='Owner',
            email='completeowner@test.com',
            phone='123456789'
        )
        
        self.tenant = Customer.objects.create(
            first_name='Complete',
            last_name='Tenant',
            email='completetenant@test.com',
            phone='987654321'
        )
        
        # Create property type
        self.property_type = PropertyType.objects.create(
            name='Complete Test',
            description='Property type for complete testing'
        )
        
        # Create test property
        self.property = Property.objects.create(
            title='Complete Test Property',
            description='Property for complete workflow testing',
            property_type=self.property_type,
            street='Complete St',
            number='123',
            neighborhood='Test Area',
            total_surface=Decimal('100.00'),
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
            number='COMPLETE-INV-001',
            date=timezone.now().date(),
            due_date=timezone.now().date() + timezone.timedelta(days=30),
            customer=self.tenant,
            contract=self.contract,
            description='Complete workflow test invoice',
            total_amount=Decimal('1000.00'),
            status='validated'
        )
        
        self.service = OwnerReceiptService()
        self.client = Client()
        self.client.force_login(self.agent)
    
    def test_complete_receipt_workflow_with_email(self):
        """Test complete receipt workflow including email sending."""
        # Step 1: Validate receipt can be generated
        can_generate, error_msg = self.service.can_generate_receipt(self.invoice)
        self.assertTrue(can_generate, f"Receipt validation failed: {error_msg}")
        
        # Step 2: Generate receipt through service
        with patch('accounting.services.EmailMessage') as mock_email_class:
            with patch.object(self.service, 'generate_pdf', return_value=b'Mock PDF'):
                mock_email_instance = Mock()
                mock_email_class.return_value = mock_email_instance
                
                receipt = self.service.generate_receipt(self.invoice, self.agent)
                
                # Verify receipt creation
                self.assertIsNotNone(receipt)
                self.assertEqual(receipt.invoice, self.invoice)
                self.assertEqual(receipt.generated_by, self.agent)
                self.assertEqual(receipt.status, 'generated')
                
                # Step 3: Send email
                result = self.service.send_receipt_email(receipt)
                self.assertTrue(result)
                
                # Verify email was sent
                mock_email_instance.send.assert_called_once()
                
                # Verify receipt status updated
                receipt.refresh_from_db()
                self.assertEqual(receipt.status, 'sent')
                self.assertIsNotNone(receipt.sent_at)
    
    def test_complete_ui_workflow_through_views(self):
        """Test complete workflow through UI views."""
        # Step 1: Access invoice list and verify receipt button
        invoice_list_url = reverse('accounting:invoice_list')
        response = self.client.get(invoice_list_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Generar Comprobante Propietario')
        
        # Step 2: Preview receipt
        preview_url = reverse('accounting:preview_owner_receipt', 
                            kwargs={'invoice_pk': self.invoice.pk})
        
        with patch.object(self.service, 'get_receipt_data') as mock_get_data:
            mock_get_data.return_value = {
                'invoice': {'number': 'COMPLETE-INV-001'},
                'financial': {
                    'gross_amount': Decimal('1000.00'),
                    'discount_amount': Decimal('100.00'),
                    'net_amount': Decimal('900.00')
                },
                'owner': {'name': 'Complete Owner'},
                'property': {'title': 'Complete Test Property'}
            }
            
            response = self.client.get(preview_url)
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'COMPLETE-INV-001')
            self.assertContains(response, 'Complete Owner')
        
        # Step 3: Generate receipt through view
        generate_url = reverse('accounting:generate_owner_receipt', 
                             kwargs={'invoice_pk': self.invoice.pk})
        
        with patch.object(self.service, 'generate_receipt') as mock_generate:
            mock_receipt = Mock()
            mock_receipt.pk = 1
            mock_receipt.receipt_number = 'REC-COMPLETE-001'
            mock_generate.return_value = mock_receipt
            
            response = self.client.post(generate_url, {'send_email': 'true'})
            self.assertEqual(response.status_code, 302)  # Redirect after success
            
            mock_generate.assert_called_once_with(self.invoice, self.agent, send_email=True)
        
        # Step 4: View receipt list
        receipts_list_url = reverse('accounting:owner_receipts_list')
        response = self.client.get(receipts_list_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Lista de Comprobantes')
    
    def test_ajax_workflow_integration(self):
        """Test complete AJAX workflow integration."""
        # Step 1: AJAX receipt generation
        generate_url = reverse('accounting:generate_owner_receipt', 
                             kwargs={'invoice_pk': self.invoice.pk})
        
        with patch.object(self.service, 'generate_receipt') as mock_generate:
            mock_receipt = Mock()
            mock_receipt.pk = 1
            mock_receipt.receipt_number = 'REC-AJAX-COMPLETE-001'
            mock_receipt.status = 'generated'
            mock_generate.return_value = mock_receipt
            
            response = self.client.post(
                generate_url,
                {'send_email': 'false'},
                HTTP_X_REQUESTED_WITH='XMLHttpRequest'
            )
            
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.content)
            self.assertTrue(data['success'])
            self.assertEqual(data['receipt_number'], 'REC-AJAX-COMPLETE-001')
        
        # Step 2: AJAX receipt status check
        receipt = OwnerReceipt.objects.create(
            invoice=self.invoice,
            receipt_number='REC-AJAX-STATUS-001',
            generated_by=self.agent,
            email_sent_to=self.owner.email,
            gross_amount=Decimal('1000.00'),
            net_amount=Decimal('900.00'),
            status='sent'
        )
        
        status_url = reverse('accounting:owner_receipt_status', 
                           kwargs={'receipt_pk': receipt.pk})
        
        response = self.client.get(
            status_url,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(data['status'], 'sent')
    
    def test_error_recovery_workflow(self):
        """Test complete error recovery workflow."""
        # Step 1: Generate receipt
        receipt = self.service.generate_receipt(self.invoice, self.agent)
        
        # Step 2: Simulate email failure
        with patch('accounting.services.EmailMessage') as mock_email_class:
            mock_email_instance = Mock()
            mock_email_instance.send.side_effect = Exception("SMTP error")
            mock_email_class.return_value = mock_email_instance
            
            with patch.object(self.service, 'generate_pdf', return_value=b'PDF'):
                with self.assertRaises(Exception):
                    self.service.send_receipt_email(receipt)
                
                # Verify receipt marked as failed
                receipt.refresh_from_db()
                self.assertEqual(receipt.status, 'failed')
        
        # Step 3: Retry through UI
        resend_url = reverse('accounting:resend_owner_receipt', 
                           kwargs={'receipt_pk': receipt.pk})
        
        with patch.object(self.service, 'resend_receipt_email') as mock_resend:
            mock_resend.return_value = True
            
            response = self.client.post(resend_url)
            self.assertEqual(response.status_code, 302)  # Redirect after success
            
            mock_resend.assert_called_once_with(receipt)
    
    def test_bulk_operations_workflow(self):
        """Test bulk operations workflow."""
        # Create multiple invoices
        invoices = []
        for i in range(5):
            invoice = Invoice.objects.create(
                number=f'BULK-COMPLETE-INV-{i+1:03d}',
                date=timezone.now().date(),
                due_date=timezone.now().date() + timezone.timedelta(days=30),
                customer=self.tenant,
                contract=self.contract,
                description=f'Bulk complete test invoice {i+1}',
                total_amount=Decimal('1000.00'),
                status='validated'
            )
            invoices.append(invoice)
        
        # Test bulk generation through service
        receipts = []
        for invoice in invoices:
            receipt = self.service.generate_receipt(invoice, self.agent)
            receipts.append(receipt)
        
        # Verify all receipts created
        self.assertEqual(len(receipts), 5)
        for receipt in receipts:
            self.assertEqual(receipt.gross_amount, Decimal('1000.00'))
            self.assertEqual(receipt.net_amount, Decimal('900.00'))
        
        # Test bulk email sending
        with patch('accounting.services.EmailMessage') as mock_email_class:
            mock_email_instance = Mock()
            mock_email_class.return_value = mock_email_instance
            
            with patch.object(self.service, 'generate_pdf', return_value=b'PDF'):
                sent_count = 0
                for receipt in receipts:
                    try:
                        result = self.service.send_receipt_email(receipt)
                        if result:
                            sent_count += 1
                    except Exception:
                        pass
                
                self.assertEqual(sent_count, 5)
    
    def test_data_consistency_throughout_workflow(self):
        """Test data consistency throughout the complete workflow."""
        # Generate receipt
        receipt = self.service.generate_receipt(self.invoice, self.agent)
        
        # Verify data consistency at each step
        receipt_data = self.service.get_receipt_data(self.invoice)
        
        # Check financial calculations consistency
        self.assertEqual(receipt.gross_amount, receipt_data['financial']['gross_amount'])
        self.assertEqual(receipt.discount_amount, receipt_data['financial']['discount_amount'])
        self.assertEqual(receipt.net_amount, receipt_data['financial']['net_amount'])
        
        # Check owner data consistency
        self.assertEqual(receipt.email_sent_to, receipt_data['owner']['email'])
        
        # Check property data consistency
        expected_address = f"{self.property.street} {self.property.number}"
        self.assertEqual(receipt_data['property']['address'], expected_address)
        
        # Verify database consistency
        receipt.refresh_from_db()
        self.assertEqual(receipt.invoice, self.invoice)
        self.assertEqual(receipt.generated_by, self.agent)
    
    def test_concurrent_workflow_operations(self):
        """Test concurrent workflow operations."""
        from concurrent.futures import ThreadPoolExecutor
        import threading
        
        # Create multiple invoices for concurrent processing
        invoices = []
        for i in range(10):
            invoice = Invoice.objects.create(
                number=f'CONCURRENT-COMPLETE-INV-{i+1:03d}',
                date=timezone.now().date(),
                due_date=timezone.now().date() + timezone.timedelta(days=30),
                customer=self.tenant,
                contract=self.contract,
                description=f'Concurrent complete test invoice {i+1}',
                total_amount=Decimal('1000.00'),
                status='validated'
            )
            invoices.append(invoice)
        
        def generate_receipt_thread(invoice):
            """Generate receipt in separate thread."""
            return self.service.generate_receipt(invoice, self.agent)
        
        # Execute concurrent receipt generation
        receipts = []
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(generate_receipt_thread, inv) for inv in invoices]
            for future in futures:
                try:
                    receipt = future.result()
                    receipts.append(receipt)
                except Exception as e:
                    print(f"Concurrent generation error: {e}")
        
        # Verify all receipts created successfully
        self.assertEqual(len(receipts), 10)
        
        # Verify unique receipt numbers
        receipt_numbers = [r.receipt_number for r in receipts]
        self.assertEqual(len(receipt_numbers), len(set(receipt_numbers)))
    
    def test_performance_under_load(self):
        """Test workflow performance under load."""
        # Create larger dataset
        invoice_count = 100
        invoices = []
        
        # Batch create invoices
        batch_size = 20
        for batch in range(0, invoice_count, batch_size):
            batch_invoices = []
            for i in range(batch, min(batch + batch_size, invoice_count)):
                invoice = Invoice.objects.create(
                    number=f'PERF-COMPLETE-INV-{i+1:04d}',
                    date=timezone.now().date(),
                    due_date=timezone.now().date() + timezone.timedelta(days=30),
                    customer=self.tenant,
                    contract=self.contract,
                    description=f'Performance complete test invoice {i+1}',
                    total_amount=Decimal('1000.00'),
                    status='validated'
                )
                batch_invoices.append(invoice)
            invoices.extend(batch_invoices)
        
        # Measure workflow performance
        start_time = time.time()
        receipts = []
        
        for invoice in invoices:
            receipt = self.service.generate_receipt(invoice, self.agent)
            receipts.append(receipt)
        
        generation_time = time.time() - start_time
        
        # Performance assertions
        self.assertEqual(len(receipts), invoice_count)
        self.assertLess(generation_time, 30.0, 
                       f"Workflow took {generation_time:.2f}s for {invoice_count} receipts")
        
        receipts_per_second = invoice_count / generation_time
        self.assertGreater(receipts_per_second, 3,
                          f"Workflow rate too slow: {receipts_per_second:.2f} receipts/second")
    
    def test_workflow_with_various_scenarios(self):
        """Test workflow with various invoice and contract scenarios."""
        scenarios = [
            # No discount scenario
            {
                'discount_percentage': None,
                'expected_net': Decimal('1000.00'),
                'description': 'No discount scenario'
            },
            # High discount scenario
            {
                'discount_percentage': Decimal('25.00'),
                'expected_net': Decimal('750.00'),
                'description': 'High discount scenario'
            },
            # Different amount scenario
            {
                'invoice_amount': Decimal('1500.00'),
                'discount_percentage': Decimal('15.00'),
                'expected_net': Decimal('1275.00'),
                'description': 'Different amount scenario'
            },
            # Minimal amount scenario
            {
                'invoice_amount': Decimal('100.00'),
                'discount_percentage': Decimal('5.00'),
                'expected_net': Decimal('95.00'),
                'description': 'Minimal amount scenario'
            }
        ]
        
        for i, scenario in enumerate(scenarios):
            with self.subTest(scenario=scenario['description']):
                # Create scenario-specific contract and invoice
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
                    number=f'SCENARIO-COMPLETE-INV-{i+1:03d}',
                    date=timezone.now().date(),
                    due_date=timezone.now().date() + timezone.timedelta(days=30),
                    customer=self.tenant,
                    contract=contract,
                    description=f'Scenario complete test: {scenario["description"]}',
                    total_amount=scenario.get('invoice_amount', Decimal('1000.00')),
                    status='validated'
                )
                
                # Execute complete workflow
                receipt = self.service.generate_receipt(invoice, self.agent)
                
                # Verify scenario-specific calculations
                self.assertEqual(receipt.net_amount, scenario['expected_net'])
                
                # Test email sending for this scenario
                with patch('accounting.services.EmailMessage') as mock_email_class:
                    mock_email_instance = Mock()
                    mock_email_class.return_value = mock_email_instance
                    
                    with patch.object(self.service, 'generate_pdf', return_value=b'PDF'):
                        result = self.service.send_receipt_email(receipt)
                        self.assertTrue(result)
                        
                        receipt.refresh_from_db()
                        self.assertEqual(receipt.status, 'sent')


class OwnerReceiptRealWorldScenariosTest(TestCase):
    """Test real-world scenarios and edge cases."""
    
    def setUp(self):
        """Set up real-world test scenarios."""
        # Create test agent
        self.agent = Agent.objects.create(
            username='realworldagent',
            email='realworld@test.com',
            first_name='Real',
            last_name='Agent',
            license_number='RW123'
        )
        
        # Create customers with realistic data
        self.owner = Customer.objects.create(
            first_name='María José',
            last_name='García-López',
            email='maria.garcia@email.com',
            phone='+54 11 1234-5678'
        )
        
        self.tenant = Customer.objects.create(
            first_name='Juan Carlos',
            last_name='Rodríguez',
            email='juan.rodriguez@email.com',
            phone='+54 11 9876-5432'
        )
        
        # Create property type
        self.property_type = PropertyType.objects.create(
            name='Departamento',
            description='Departamento de 2 ambientes'
        )
        
        # Create realistic property
        self.property = Property.objects.create(
            title='Departamento 2 amb. - Palermo',
            description='Departamento de 2 ambientes en Palermo con balcón',
            property_type=self.property_type,
            street='Av. Santa Fe',
            number='3456',
            neighborhood='Palermo',
            total_surface=Decimal('65.50'),
            bedrooms=1,
            bathrooms=1,
            agent=self.agent,
            owner=self.owner
        )
        
        self.service = OwnerReceiptService()
    
    def test_real_world_rental_scenario(self):
        """Test realistic rental scenario with typical amounts and discounts."""
        # Create realistic contract
        contract = Contract.objects.create(
            customer=self.tenant,
            agent=self.agent,
            property=self.property,
            start_date=timezone.now().date(),
            amount=Decimal('85000.00'),  # Realistic Buenos Aires rent
            owner_discount_percentage=Decimal('8.50'),  # Realistic commission
            status=Contract.STATUS_ACTIVE
        )
        
        # Create realistic invoice
        invoice = Invoice.objects.create(
            number='FAC-2024-001234',
            date=timezone.now().date(),
            due_date=timezone.now().date() + timezone.timedelta(days=10),
            customer=self.tenant,
            contract=contract,
            description='Alquiler Marzo 2024 - Av. Santa Fe 3456',
            total_amount=Decimal('85000.00'),
            status='validated'
        )
        
        # Test complete workflow
        receipt = self.service.generate_receipt(invoice, self.agent)
        
        # Verify realistic calculations
        expected_discount = Decimal('85000.00') * (Decimal('8.50') / Decimal('100'))
        expected_net = Decimal('85000.00') - expected_discount
        
        self.assertEqual(receipt.gross_amount, Decimal('85000.00'))
        self.assertEqual(receipt.discount_amount, expected_discount)
        self.assertEqual(receipt.net_amount, expected_net)
        
        # Test email with realistic data
        with patch('accounting.services.EmailMessage') as mock_email_class:
            mock_email_instance = Mock()
            mock_email_class.return_value = mock_email_instance
            
            with patch.object(self.service, 'generate_pdf', return_value=b'PDF'):
                result = self.service.send_receipt_email(receipt)
                self.assertTrue(result)
                
                # Verify email subject contains realistic property info
                call_args = mock_email_class.call_args
                subject = call_args[1]['subject']
                self.assertIn('Av. Santa Fe 3456', subject)
                self.assertIn('Marzo 2024', subject)
    
    def test_special_characters_handling(self):
        """Test handling of special characters in real-world data."""
        # Update with special characters
        self.property.title = 'Depto. "Los Álamos" - 3° Piso'
        self.property.street = 'Av. Pres. José Evaristo Uriburu'
        self.property.save()
        
        contract = Contract.objects.create(
            customer=self.tenant,
            agent=self.agent,
            property=self.property,
            start_date=timezone.now().date(),
            amount=Decimal('75000.00'),
            owner_discount_percentage=Decimal('10.00'),
            status=Contract.STATUS_ACTIVE
        )
        
        invoice = Invoice.objects.create(
            number='FAC-2024-SPECIAL',
            date=timezone.now().date(),
            due_date=timezone.now().date() + timezone.timedelta(days=10),
            customer=self.tenant,
            contract=contract,
            description='Alquiler con caracteres especiales',
            total_amount=Decimal('75000.00'),
            status='validated'
        )
        
        # Test workflow with special characters
        receipt = self.service.generate_receipt(invoice, self.agent)
        self.assertIsNotNone(receipt)
        
        # Test email template with special characters
        with patch('accounting.services.render_to_string') as mock_render:
            with patch('accounting.services.EmailMessage') as mock_email_class:
                mock_render.return_value = '<html>Email with special chars</html>'
                mock_email_instance = Mock()
                mock_email_class.return_value = mock_email_instance
                
                with patch.object(self.service, 'generate_pdf', return_value=b'PDF'):
                    result = self.service.send_receipt_email(receipt)
                    self.assertTrue(result)
                    
                    # Verify template context handles special characters
                    template_context = mock_render.call_args[0][1]
                    self.assertEqual(template_context['owner_name'], 'María José García-López')
                    self.assertIn('José Evaristo Uriburu', template_context['property_address'])
    
    def test_multiple_properties_same_owner(self):
        """Test scenario with multiple properties for the same owner."""
        # Create additional properties for same owner
        properties = []
        for i in range(3):
            property_obj = Property.objects.create(
                title=f'Propiedad {i+1} - Owner Test',
                description=f'Propiedad número {i+1} del mismo propietario',
                property_type=self.property_type,
                street=f'Calle Test {i+1}',
                number=f'{100+i}',
                neighborhood='Test Neighborhood',
                total_surface=Decimal(f'{60+i*10}.00'),
                bedrooms=1+i,
                bathrooms=1,
                agent=self.agent,
                owner=self.owner  # Same owner
            )
            properties.append(property_obj)
        
        # Create contracts and invoices for each property
        receipts = []
        for i, property_obj in enumerate(properties):
            contract = Contract.objects.create(
                customer=self.tenant,
                agent=self.agent,
                property=property_obj,
                start_date=timezone.now().date(),
                amount=Decimal(f'{70000+i*5000}.00'),
                owner_discount_percentage=Decimal('10.00'),
                status=Contract.STATUS_ACTIVE
            )
            
            invoice = Invoice.objects.create(
                number=f'FAC-MULTI-PROP-{i+1:03d}',
                date=timezone.now().date(),
                due_date=timezone.now().date() + timezone.timedelta(days=10),
                customer=self.tenant,
                contract=contract,
                description=f'Alquiler propiedad {i+1}',
                total_amount=Decimal(f'{70000+i*5000}.00'),
                status='validated'
            )
            
            receipt = self.service.generate_receipt(invoice, self.agent)
            receipts.append(receipt)
        
        # Verify all receipts created for same owner
        self.assertEqual(len(receipts), 3)
        for receipt in receipts:
            self.assertEqual(receipt.email_sent_to, self.owner.email)
        
        # Verify unique receipt numbers
        receipt_numbers = [r.receipt_number for r in receipts]
        self.assertEqual(len(receipt_numbers), len(set(receipt_numbers)))
    
    def test_end_of_month_batch_processing(self):
        """Test end-of-month batch processing scenario."""
        # Create multiple invoices for end-of-month processing
        invoices = []
        contracts = []
        
        # Create different contracts with varying discounts
        discount_rates = [Decimal('8.00'), Decimal('10.00'), Decimal('12.00'), Decimal('15.00')]
        
        for i, discount_rate in enumerate(discount_rates):
            contract = Contract.objects.create(
                customer=self.tenant,
                agent=self.agent,
                property=self.property,
                start_date=timezone.now().date(),
                amount=Decimal(f'{80000+i*10000}.00'),
                owner_discount_percentage=discount_rate,
                status=Contract.STATUS_ACTIVE
            )
            contracts.append(contract)
            
            invoice = Invoice.objects.create(
                number=f'FAC-EOM-{i+1:03d}',
                date=timezone.now().date(),
                due_date=timezone.now().date() + timezone.timedelta(days=10),
                customer=self.tenant,
                contract=contract,
                description=f'Alquiler fin de mes - Contrato {i+1}',
                total_amount=Decimal(f'{80000+i*10000}.00'),
                status='validated'
            )
            invoices.append(invoice)
        
        # Process batch
        start_time = time.time()
        receipts = []
        
        for invoice in invoices:
            receipt = self.service.generate_receipt(invoice, self.agent)
            receipts.append(receipt)
        
        processing_time = time.time() - start_time
        
        # Verify batch processing results
        self.assertEqual(len(receipts), 4)
        self.assertLess(processing_time, 5.0, "Batch processing took too long")
        
        # Verify different discount calculations
        expected_nets = [
            Decimal('80000.00') * (Decimal('100') - Decimal('8.00')) / Decimal('100'),
            Decimal('90000.00') * (Decimal('100') - Decimal('10.00')) / Decimal('100'),
            Decimal('100000.00') * (Decimal('100') - Decimal('12.00')) / Decimal('100'),
            Decimal('110000.00') * (Decimal('100') - Decimal('15.00')) / Decimal('100'),
        ]
        
        for i, receipt in enumerate(receipts):
            self.assertEqual(receipt.net_amount, expected_nets[i])
    
    def test_system_recovery_after_failure(self):
        """Test system recovery after various failure scenarios."""
        # Create test invoice
        contract = Contract.objects.create(
            customer=self.tenant,
            agent=self.agent,
            property=self.property,
            start_date=timezone.now().date(),
            amount=Decimal('75000.00'),
            owner_discount_percentage=Decimal('10.00'),
            status=Contract.STATUS_ACTIVE
        )
        
        invoice = Invoice.objects.create(
            number='FAC-RECOVERY-001',
            date=timezone.now().date(),
            due_date=timezone.now().date() + timezone.timedelta(days=10),
            customer=self.tenant,
            contract=contract,
            description='Recovery test invoice',
            total_amount=Decimal('75000.00'),
            status='validated'
        )
        
        # Scenario 1: Database transaction failure during receipt creation
        with patch('accounting.models_invoice.OwnerReceipt.save') as mock_save:
            mock_save.side_effect = Exception("Database error")
            
            with self.assertRaises(Exception):
                self.service.generate_receipt(invoice, self.agent)
            
            # Verify no partial receipt was created
            self.assertEqual(OwnerReceipt.objects.filter(invoice=invoice).count(), 0)
        
        # Scenario 2: Successful receipt creation after recovery
        receipt = self.service.generate_receipt(invoice, self.agent)
        self.assertIsNotNone(receipt)
        
        # Scenario 3: Email failure and recovery
        with patch('accounting.services.EmailMessage') as mock_email_class:
            mock_email_instance = Mock()
            mock_email_instance.send.side_effect = Exception("Email server down")
            mock_email_class.return_value = mock_email_instance
            
            with patch.object(self.service, 'generate_pdf', return_value=b'PDF'):
                with self.assertRaises(Exception):
                    self.service.send_receipt_email(receipt)
                
                # Verify receipt marked as failed
                receipt.refresh_from_db()
                self.assertEqual(receipt.status, 'failed')
        
        # Scenario 4: Successful email after recovery
        with patch('accounting.services.EmailMessage') as mock_email_class:
            mock_email_instance = Mock()
            mock_email_class.return_value = mock_email_instance
            
            with patch.object(self.service, 'generate_pdf', return_value=b'PDF'):
                result = self.service.resend_receipt_email(receipt)
                self.assertTrue(result)
                
                receipt.refresh_from_db()
                self.assertEqual(receipt.status, 'sent')