# -*- coding: utf-8 -*-
"""
Performance tests for the owner receipt system.

This module contains performance tests for bulk operations, memory usage,
and scalability scenarios for the owner receipt feature.
"""

import time
import gc
import psutil
import os
from django.test import TestCase, TransactionTestCase
from django.test.utils import override_settings
from django.db import connection
from django.utils import timezone
from decimal import Decimal
from unittest.mock import patch, Mock
from concurrent.futures import ThreadPoolExecutor, as_completed

from accounting.models_invoice import Invoice, OwnerReceipt
from accounting.services import OwnerReceiptService
from customers.models import Customer
from contracts.models import Contract
from properties.models import Property, PropertyType
from agents.models import Agent


class OwnerReceiptPerformanceTest(TestCase):
    """Performance tests for owner receipt operations."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test data for performance tests."""
        super().setUpClass()
        
        # Create test agent
        cls.agent = Agent.objects.create(
            username='perfagent',
            email='perf@test.com',
            first_name='Performance',
            last_name='Agent',
            license_number='PERF123'
        )
        
        # Create test customers
        cls.owner = Customer.objects.create(
            first_name='Performance',
            last_name='Owner',
            email='perfowner@test.com',
            phone='123456789'
        )
        
        cls.tenant = Customer.objects.create(
            first_name='Performance',
            last_name='Tenant',
            email='perftenant@test.com',
            phone='987654321'
        )
        
        # Create property type
        cls.property_type = PropertyType.objects.create(
            name='Performance Test',
            description='Property type for performance testing'
        )
        
        # Create test property
        cls.property = Property.objects.create(
            title='Performance Test Property',
            description='Property for performance testing',
            property_type=cls.property_type,
            street='Performance St',
            number='123',
            neighborhood='Test Area',
            total_surface=Decimal('100.00'),
            bedrooms=2,
            bathrooms=1,
            agent=cls.agent,
            owner=cls.owner
        )
        
        # Create test contract
        cls.contract = Contract.objects.create(
            customer=cls.tenant,
            agent=cls.agent,
            property=cls.property,
            start_date=timezone.now().date(),
            amount=Decimal('1000.00'),
            owner_discount_percentage=Decimal('10.00'),
            status=Contract.STATUS_ACTIVE
        )
        
        cls.service = OwnerReceiptService()
    
    def setUp(self):
        """Set up for each test."""
        # Clear any existing receipts
        OwnerReceipt.objects.all().delete()
        
        # Reset database query count
        connection.queries_log.clear()
    
    def test_bulk_receipt_generation_performance(self):
        """Test performance of generating multiple receipts."""
        # Create test invoices
        invoice_count = 100
        invoices = []
        
        start_time = time.time()
        
        # Create invoices
        for i in range(invoice_count):
            invoice = Invoice.objects.create(
                number=f'PERF-INV-{i+1:04d}',
                date=timezone.now().date(),
                due_date=timezone.now().date() + timezone.timedelta(days=30),
                customer=self.tenant,
                contract=self.contract,
                description=f'Performance test invoice {i+1}',
                total_amount=Decimal('1000.00'),
                status='validated'
            )
            invoices.append(invoice)
        
        invoice_creation_time = time.time() - start_time
        
        # Generate receipts
        receipt_start_time = time.time()
        receipts = []
        
        for invoice in invoices:
            receipt = self.service.generate_receipt(invoice, self.agent)
            receipts.append(receipt)
        
        receipt_generation_time = time.time() - receipt_start_time
        total_time = time.time() - start_time
        
        # Performance assertions
        self.assertEqual(len(receipts), invoice_count)
        self.assertLess(receipt_generation_time, 10.0, 
                       f"Receipt generation took {receipt_generation_time:.2f}s for {invoice_count} receipts")
        
        # Calculate performance metrics
        receipts_per_second = invoice_count / receipt_generation_time
        self.assertGreater(receipts_per_second, 10, 
                          f"Receipt generation rate too slow: {receipts_per_second:.2f} receipts/second")
        
        print(f"Performance metrics for {invoice_count} receipts:")
        print(f"  Invoice creation: {invoice_creation_time:.2f}s")
        print(f"  Receipt generation: {receipt_generation_time:.2f}s")
        print(f"  Total time: {total_time:.2f}s")
        print(f"  Receipts per second: {receipts_per_second:.2f}")
    
    def test_memory_usage_during_bulk_operations(self):
        """Test memory usage during bulk receipt generation."""
        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create and process a large number of invoices
        invoice_count = 500
        invoices = []
        
        # Create invoices in batches to monitor memory
        batch_size = 50
        memory_readings = []
        
        for batch in range(0, invoice_count, batch_size):
            # Create batch of invoices
            batch_invoices = []
            for i in range(batch, min(batch + batch_size, invoice_count)):
                invoice = Invoice.objects.create(
                    number=f'MEM-INV-{i+1:04d}',
                    date=timezone.now().date(),
                    due_date=timezone.now().date() + timezone.timedelta(days=30),
                    customer=self.tenant,
                    contract=self.contract,
                    description=f'Memory test invoice {i+1}',
                    total_amount=Decimal('1000.00'),
                    status='validated'
                )
                batch_invoices.append(invoice)
            
            # Generate receipts for batch
            for invoice in batch_invoices:
                receipt = self.service.generate_receipt(invoice, self.agent)
                # Immediately clear reference to help GC
                del receipt
            
            # Force garbage collection
            gc.collect()
            
            # Record memory usage
            current_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_readings.append(current_memory)
            
            invoices.extend(batch_invoices)
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory usage assertions
        self.assertLess(memory_increase, 100, 
                       f"Memory usage increased by {memory_increase:.2f}MB, which is too high")
        
        print(f"Memory usage for {invoice_count} receipts:")
        print(f"  Initial memory: {initial_memory:.2f}MB")
        print(f"  Final memory: {final_memory:.2f}MB")
        print(f"  Memory increase: {memory_increase:.2f}MB")
        print(f"  Memory per receipt: {memory_increase/invoice_count:.4f}MB")
    
    def test_database_query_efficiency(self):
        """Test database query efficiency for receipt operations."""
        # Create test invoices
        invoice_count = 50
        invoices = []
        
        for i in range(invoice_count):
            invoice = Invoice.objects.create(
                number=f'QUERY-INV-{i+1:04d}',
                date=timezone.now().date(),
                due_date=timezone.now().date() + timezone.timedelta(days=30),
                customer=self.tenant,
                contract=self.contract,
                description=f'Query test invoice {i+1}',
                total_amount=Decimal('1000.00'),
                status='validated'
            )
            invoices.append(invoice)
        
        # Reset query count
        connection.queries_log.clear()
        
        # Generate receipts and count queries
        receipts = []
        for invoice in invoices:
            receipt = self.service.generate_receipt(invoice, self.agent)
            receipts.append(receipt)
        
        query_count = len(connection.queries)
        
        # Query efficiency assertions
        max_expected_queries = invoice_count * 10  # Allow reasonable number of queries per receipt
        self.assertLess(query_count, max_expected_queries,
                       f"Too many database queries: {query_count} for {invoice_count} receipts")
        
        queries_per_receipt = query_count / invoice_count
        self.assertLess(queries_per_receipt, 8,
                       f"Too many queries per receipt: {queries_per_receipt:.2f}")
        
        print(f"Database query efficiency for {invoice_count} receipts:")
        print(f"  Total queries: {query_count}")
        print(f"  Queries per receipt: {queries_per_receipt:.2f}")
    
    @patch('accounting.services.EmailMessage')
    @patch.object(OwnerReceiptService, 'generate_pdf')
    def test_bulk_email_sending_performance(self, mock_generate_pdf, mock_email_class):
        """Test performance of bulk email sending."""
        # Mock PDF generation and email sending
        mock_generate_pdf.return_value = b'Mock PDF content'
        mock_email_instance = Mock()
        mock_email_class.return_value = mock_email_instance
        
        # Create receipts
        receipt_count = 100
        receipts = []
        
        for i in range(receipt_count):
            invoice = Invoice.objects.create(
                number=f'EMAIL-INV-{i+1:04d}',
                date=timezone.now().date(),
                due_date=timezone.now().date() + timezone.timedelta(days=30),
                customer=self.tenant,
                contract=self.contract,
                description=f'Email test invoice {i+1}',
                total_amount=Decimal('1000.00'),
                status='validated'
            )
            receipt = self.service.generate_receipt(invoice, self.agent)
            receipts.append(receipt)
        
        # Test bulk email sending performance
        start_time = time.time()
        sent_count = 0
        
        for receipt in receipts:
            try:
                result = self.service.send_receipt_email(receipt)
                if result:
                    sent_count += 1
            except Exception as e:
                print(f"Email sending failed: {e}")
        
        email_sending_time = time.time() - start_time
        
        # Performance assertions
        self.assertEqual(sent_count, receipt_count)
        self.assertLess(email_sending_time, 15.0,
                       f"Email sending took {email_sending_time:.2f}s for {receipt_count} emails")
        
        emails_per_second = receipt_count / email_sending_time
        self.assertGreater(emails_per_second, 5,
                          f"Email sending rate too slow: {emails_per_second:.2f} emails/second")
        
        print(f"Email sending performance for {receipt_count} emails:")
        print(f"  Total time: {email_sending_time:.2f}s")
        print(f"  Emails per second: {emails_per_second:.2f}")
    
    def test_concurrent_receipt_generation(self):
        """Test concurrent receipt generation performance."""
        # Create test invoices
        invoice_count = 50
        invoices = []
        
        for i in range(invoice_count):
            invoice = Invoice.objects.create(
                number=f'CONCURRENT-INV-{i+1:04d}',
                date=timezone.now().date(),
                due_date=timezone.now().date() + timezone.timedelta(days=30),
                customer=self.tenant,
                contract=self.contract,
                description=f'Concurrent test invoice {i+1}',
                total_amount=Decimal('1000.00'),
                status='validated'
            )
            invoices.append(invoice)
        
        def generate_receipt(invoice):
            """Generate receipt for a single invoice."""
            return self.service.generate_receipt(invoice, self.agent)
        
        # Test concurrent generation
        start_time = time.time()
        receipts = []
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_invoice = {
                executor.submit(generate_receipt, invoice): invoice 
                for invoice in invoices
            }
            
            for future in as_completed(future_to_invoice):
                try:
                    receipt = future.result()
                    receipts.append(receipt)
                except Exception as e:
                    print(f"Concurrent generation failed: {e}")
        
        concurrent_time = time.time() - start_time
        
        # Test sequential generation for comparison
        sequential_invoices = []
        for i in range(10):  # Smaller sample for comparison
            invoice = Invoice.objects.create(
                number=f'SEQUENTIAL-INV-{i+1:04d}',
                date=timezone.now().date(),
                due_date=timezone.now().date() + timezone.timedelta(days=30),
                customer=self.tenant,
                contract=self.contract,
                description=f'Sequential test invoice {i+1}',
                total_amount=Decimal('1000.00'),
                status='validated'
            )
            sequential_invoices.append(invoice)
        
        sequential_start = time.time()
        sequential_receipts = []
        for invoice in sequential_invoices:
            receipt = self.service.generate_receipt(invoice, self.agent)
            sequential_receipts.append(receipt)
        sequential_time = time.time() - sequential_start
        
        # Performance assertions
        self.assertEqual(len(receipts), invoice_count)
        self.assertEqual(len(sequential_receipts), 10)
        
        # Calculate rates
        concurrent_rate = invoice_count / concurrent_time
        sequential_rate = 10 / sequential_time
        
        print(f"Concurrent vs Sequential performance:")
        print(f"  Concurrent: {invoice_count} receipts in {concurrent_time:.2f}s ({concurrent_rate:.2f}/s)")
        print(f"  Sequential: 10 receipts in {sequential_time:.2f}s ({sequential_rate:.2f}/s)")
        
        # Concurrent should be at least as fast as sequential
        self.assertGreaterEqual(concurrent_rate, sequential_rate * 0.8,
                               "Concurrent generation should not be significantly slower")
    
    def test_pdf_generation_performance(self):
        """Test PDF generation performance."""
        # Create test receipts
        receipt_count = 50
        receipts = []
        
        for i in range(receipt_count):
            invoice = Invoice.objects.create(
                number=f'PDF-INV-{i+1:04d}',
                date=timezone.now().date(),
                due_date=timezone.now().date() + timezone.timedelta(days=30),
                customer=self.tenant,
                contract=self.contract,
                description=f'PDF test invoice {i+1}',
                total_amount=Decimal('1000.00'),
                status='validated'
            )
            receipt = self.service.generate_receipt(invoice, self.agent)
            receipts.append(receipt)
        
        # Test PDF generation performance
        with patch('accounting.services.HTML') as mock_html:
            mock_html_instance = Mock()
            mock_html_instance.write_pdf.return_value = b'Mock PDF content'
            mock_html.return_value = mock_html_instance
            
            start_time = time.time()
            pdf_count = 0
            
            for receipt in receipts:
                try:
                    pdf_content = self.service.generate_pdf(receipt)
                    if pdf_content:
                        pdf_count += 1
                except Exception as e:
                    print(f"PDF generation failed: {e}")
            
            pdf_generation_time = time.time() - start_time
        
        # Performance assertions
        self.assertEqual(pdf_count, receipt_count)
        self.assertLess(pdf_generation_time, 10.0,
                       f"PDF generation took {pdf_generation_time:.2f}s for {receipt_count} PDFs")
        
        pdfs_per_second = receipt_count / pdf_generation_time
        self.assertGreater(pdfs_per_second, 5,
                          f"PDF generation rate too slow: {pdfs_per_second:.2f} PDFs/second")
        
        print(f"PDF generation performance for {receipt_count} PDFs:")
        print(f"  Total time: {pdf_generation_time:.2f}s")
        print(f"  PDFs per second: {pdfs_per_second:.2f}")
    
    def test_large_dataset_scalability(self):
        """Test scalability with large datasets."""
        # Test with progressively larger datasets
        dataset_sizes = [10, 50, 100, 200]
        performance_data = []
        
        for size in dataset_sizes:
            # Create invoices
            invoices = []
            for i in range(size):
                invoice = Invoice.objects.create(
                    number=f'SCALE-{size}-INV-{i+1:04d}',
                    date=timezone.now().date(),
                    due_date=timezone.now().date() + timezone.timedelta(days=30),
                    customer=self.tenant,
                    contract=self.contract,
                    description=f'Scale test {size} invoice {i+1}',
                    total_amount=Decimal('1000.00'),
                    status='validated'
                )
                invoices.append(invoice)
            
            # Measure generation time
            start_time = time.time()
            receipts = []
            
            for invoice in invoices:
                receipt = self.service.generate_receipt(invoice, self.agent)
                receipts.append(receipt)
            
            generation_time = time.time() - start_time
            rate = size / generation_time
            
            performance_data.append({
                'size': size,
                'time': generation_time,
                'rate': rate
            })
            
            print(f"Dataset size {size}: {generation_time:.2f}s ({rate:.2f} receipts/s)")
        
        # Verify scalability - rate should not degrade significantly
        base_rate = performance_data[0]['rate']
        for data in performance_data[1:]:
            rate_ratio = data['rate'] / base_rate
            self.assertGreater(rate_ratio, 0.5,
                             f"Performance degraded too much for size {data['size']}: "
                             f"{rate_ratio:.2f} of base rate")
    
    def test_error_handling_performance_impact(self):
        """Test performance impact of error handling."""
        # Create invoices with various error conditions
        error_invoice_count = 20
        valid_invoice_count = 20
        
        # Create invalid invoices (will cause errors)
        invalid_invoices = []
        for i in range(error_invoice_count):
            invoice = Invoice.objects.create(
                number=f'ERROR-INV-{i+1:04d}',
                date=timezone.now().date(),
                due_date=timezone.now().date() + timezone.timedelta(days=30),
                customer=self.tenant,
                contract=self.contract,
                description=f'Error test invoice {i+1}',
                total_amount=Decimal('1000.00'),
                status='draft'  # Invalid status
            )
            invalid_invoices.append(invoice)
        
        # Create valid invoices
        valid_invoices = []
        for i in range(valid_invoice_count):
            invoice = Invoice.objects.create(
                number=f'VALID-INV-{i+1:04d}',
                date=timezone.now().date(),
                due_date=timezone.now().date() + timezone.timedelta(days=30),
                customer=self.tenant,
                contract=self.contract,
                description=f'Valid test invoice {i+1}',
                total_amount=Decimal('1000.00'),
                status='validated'
            )
            valid_invoices.append(invoice)
        
        # Test error handling performance
        start_time = time.time()
        error_count = 0
        
        for invoice in invalid_invoices:
            try:
                self.service.generate_receipt(invoice, self.agent)
            except Exception:
                error_count += 1
        
        error_handling_time = time.time() - start_time
        
        # Test valid processing performance
        start_time = time.time()
        success_count = 0
        
        for invoice in valid_invoices:
            try:
                receipt = self.service.generate_receipt(invoice, self.agent)
                if receipt:
                    success_count += 1
            except Exception:
                pass
        
        valid_processing_time = time.time() - start_time
        
        # Performance assertions
        self.assertEqual(error_count, error_invoice_count)
        self.assertEqual(success_count, valid_invoice_count)
        
        # Error handling should not be significantly slower
        error_rate = error_invoice_count / error_handling_time
        valid_rate = valid_invoice_count / valid_processing_time
        
        print(f"Error handling performance:")
        print(f"  Error processing: {error_invoice_count} in {error_handling_time:.2f}s ({error_rate:.2f}/s)")
        print(f"  Valid processing: {valid_invoice_count} in {valid_processing_time:.2f}s ({valid_rate:.2f}/s)")
        
        # Error handling should be reasonably fast
        self.assertGreater(error_rate, 10, "Error handling is too slow")


class OwnerReceiptStressTest(TransactionTestCase):
    """Stress tests for owner receipt system under heavy load."""
    
    def setUp(self):
        """Set up for stress tests."""
        # Create minimal test data
        self.agent = Agent.objects.create(
            username='stressagent',
            email='stress@test.com',
            first_name='Stress',
            last_name='Agent',
            license_number='STRESS123'
        )
        
        self.owner = Customer.objects.create(
            first_name='Stress',
            last_name='Owner',
            email='stressowner@test.com'
        )
        
        self.tenant = Customer.objects.create(
            first_name='Stress',
            last_name='Tenant',
            email='stresstenant@test.com'
        )
        
        self.property_type = PropertyType.objects.create(
            name='Stress Test',
            description='Stress test property type'
        )
        
        self.property = Property.objects.create(
            title='Stress Test Property',
            property_type=self.property_type,
            street='Stress St',
            number='1',
            agent=self.agent,
            owner=self.owner
        )
        
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
    
    def test_high_volume_receipt_generation(self):
        """Test system behavior under high volume receipt generation."""
        # Create a large number of invoices
        invoice_count = 1000
        print(f"Creating {invoice_count} invoices for stress test...")
        
        invoices = []
        batch_size = 100
        
        for batch in range(0, invoice_count, batch_size):
            batch_invoices = []
            for i in range(batch, min(batch + batch_size, invoice_count)):
                invoice = Invoice.objects.create(
                    number=f'STRESS-INV-{i+1:05d}',
                    date=timezone.now().date(),
                    due_date=timezone.now().date() + timezone.timedelta(days=30),
                    customer=self.tenant,
                    contract=self.contract,
                    description=f'Stress test invoice {i+1}',
                    total_amount=Decimal('1000.00'),
                    status='validated'
                )
                batch_invoices.append(invoice)
            
            invoices.extend(batch_invoices)
            print(f"Created {len(invoices)} invoices...")
        
        print(f"Starting receipt generation for {invoice_count} invoices...")
        start_time = time.time()
        
        receipts = []
        error_count = 0
        
        for i, invoice in enumerate(invoices):
            try:
                receipt = self.service.generate_receipt(invoice, self.agent)
                receipts.append(receipt)
                
                # Progress indicator
                if (i + 1) % 100 == 0:
                    elapsed = time.time() - start_time
                    rate = (i + 1) / elapsed
                    print(f"Generated {i + 1} receipts in {elapsed:.2f}s ({rate:.2f}/s)")
                    
            except Exception as e:
                error_count += 1
                if error_count <= 10:  # Only print first 10 errors
                    print(f"Error generating receipt {i+1}: {e}")
        
        total_time = time.time() - start_time
        success_count = len(receipts)
        success_rate = success_count / total_time
        
        print(f"Stress test results:")
        print(f"  Total invoices: {invoice_count}")
        print(f"  Successful receipts: {success_count}")
        print(f"  Errors: {error_count}")
        print(f"  Total time: {total_time:.2f}s")
        print(f"  Success rate: {success_rate:.2f} receipts/second")
        
        # Stress test assertions
        self.assertGreater(success_count, invoice_count * 0.95,
                          f"Success rate too low: {success_count}/{invoice_count}")
        self.assertGreater(success_rate, 5,
                          f"Processing rate too slow: {success_rate:.2f} receipts/second")
    
    @override_settings(DEBUG=False)  # Disable debug to reduce memory usage
    def test_memory_stability_under_load(self):
        """Test memory stability under sustained load."""
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Run multiple batches to test memory stability
        batch_count = 10
        batch_size = 50
        memory_readings = []
        
        for batch_num in range(batch_count):
            print(f"Processing batch {batch_num + 1}/{batch_count}...")
            
            # Create batch of invoices
            invoices = []
            for i in range(batch_size):
                invoice = Invoice.objects.create(
                    number=f'MEM-STRESS-B{batch_num+1}-{i+1:03d}',
                    date=timezone.now().date(),
                    due_date=timezone.now().date() + timezone.timedelta(days=30),
                    customer=self.tenant,
                    contract=self.contract,
                    description=f'Memory stress batch {batch_num+1} invoice {i+1}',
                    total_amount=Decimal('1000.00'),
                    status='validated'
                )
                invoices.append(invoice)
            
            # Process batch
            for invoice in invoices:
                receipt = self.service.generate_receipt(invoice, self.agent)
                # Clear reference immediately
                del receipt
            
            # Force garbage collection
            gc.collect()
            
            # Record memory usage
            current_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_readings.append(current_memory)
            
            print(f"  Memory after batch {batch_num + 1}: {current_memory:.2f}MB")
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        max_memory = max(memory_readings)
        memory_growth = final_memory - initial_memory
        
        print(f"Memory stability test results:")
        print(f"  Initial memory: {initial_memory:.2f}MB")
        print(f"  Final memory: {final_memory:.2f}MB")
        print(f"  Max memory: {max_memory:.2f}MB")
        print(f"  Memory growth: {memory_growth:.2f}MB")
        
        # Memory stability assertions
        self.assertLess(memory_growth, 50,
                       f"Memory growth too high: {memory_growth:.2f}MB")
        self.assertLess(max_memory - initial_memory, 100,
                       f"Peak memory usage too high: {max_memory - initial_memory:.2f}MB")