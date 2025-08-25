"""
Integration tests for notification workflows.

This module contains integration tests that verify complete notification workflows
from trigger to delivery, including Celery task execution and email notifications.
"""

import pytest
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch, MagicMock
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core import mail
from django.test.utils import override_settings

from contracts.models import Contract
from accounting.models_invoice import Invoice
from properties.models import Property
from customers.models import Customer
from agents.models import Agent

from user_notifications.models import Notification, NotificationLog, NotificationBatch
from user_notifications.models_preferences import NotificationPreference
from user_notifications.tasks import (
    check_contract_expirations,
    check_invoice_overdue,
    check_rent_increases,
    check_invoice_due_soon,
    process_notification_batches
)
from user_notifications.services import (
    create_notification,
    send_notification_email,
    process_ready_notification_batches
)

User = get_user_model()


class ContractExpirationWorkflowTest(TransactionTestCase):
    """Integration tests for contract expiration notification workflow."""
    
    def setUp(self):
        """Set up test data."""
        self.agent = Agent.objects.create(
            username='agent1',
            email='agent1@test.com',
            first_name='Test',
            last_name='Agent'
        )
        
        self.customer = Customer.objects.create(
            username='customer1',
            email='customer1@test.com',
            first_name='Test',
            last_name='Customer'
        )
        
        self.property = Property.objects.create(
            title='Test Property',
            address='123 Test St',
            property_type='apartment',
            status='available'
        )
        
        # Create notification preferences
        self.preferences = NotificationPreference.objects.create(
            agent=self.agent,
            receive_contract_expiration=True,
            email_notifications=True,
            notification_frequency='immediately'
        )
        
        self.today = timezone.now().date()
    
    def test_end_to_end_contract_expiration_workflow(self):
        """Test complete workflow from contract expiration detection to notification creation."""
        # Create contracts at different expiration stages
        expired_contract = Contract.objects.create(
            property=self.property,
            customer=self.customer,
            agent=self.agent,
            amount=Decimal('1000.00'),
            start_date=self.today - timedelta(days=365),
            end_date=self.today - timedelta(days=5),
            status=Contract.STATUS_ACTIVE
        )
        
        urgent_contract = Contract.objects.create(
            property=self.property,
            customer=self.customer,
            agent=self.agent,
            amount=Decimal('1200.00'),
            start_date=self.today - timedelta(days=365),
            end_date=self.today + timedelta(days=5),
            status=Contract.STATUS_ACTIVE
        )
        
        advance_contract = Contract.objects.create(
            property=self.property,
            customer=self.customer,
            agent=self.agent,
            amount=Decimal('1500.00'),
            start_date=self.today - timedelta(days=365),
            end_date=self.today + timedelta(days=20),
            status=Contract.STATUS_ACTIVE
        )
        
        # Execute the Celery task
        result = check_contract_expirations.apply()
        
        # Verify task completed successfully
        self.assertTrue(result.successful())
        task_result = result.result
        
        # Verify correct number of notifications were created
        self.assertEqual(task_result['expired_notifications'], 1)
        self.assertEqual(task_result['urgent_notifications'], 1)
        self.assertEqual(task_result['advance_notifications'], 1)
        self.assertEqual(task_result['total_notifications'], 3)
        
        # Verify notifications were created in database
        notifications = Notification.objects.filter(agent=self.agent).order_by('created_at')
        self.assertEqual(notifications.count(), 3)
        
        # Verify notification content
        expired_notification = notifications.filter(notification_type='contract_expired').first()
        self.assertIsNotNone(expired_notification)
        self.assertIn('Contrato Vencido', expired_notification.title)
        self.assertEqual(expired_notification.related_object, expired_contract)
        
        urgent_notification = notifications.filter(notification_type='contract_expiring_urgent').first()
        self.assertIsNotNone(urgent_notification)
        self.assertIn('Contrato Vence Pronto', urgent_notification.title)
        self.assertEqual(urgent_notification.related_object, urgent_contract)
        
        advance_notification = notifications.filter(notification_type='contract_expiring_soon').first()
        self.assertIsNotNone(advance_notification)
        self.assertIn('Contrato Próximo a Vencer', advance_notification.title)
        self.assertEqual(advance_notification.related_object, advance_contract)
        
        # Verify notification logs were created to prevent duplicates
        logs = NotificationLog.objects.filter(agent=self.agent)
        self.assertEqual(logs.count(), 3)
    
    def test_contract_expiration_with_preferences_disabled(self):
        """Test that notifications are not created when preferences are disabled."""
        # Disable contract expiration notifications
        self.preferences.receive_contract_expiration = False
        self.preferences.save()
        
        # Create expired contract
        Contract.objects.create(
            property=self.property,
            customer=self.customer,
            agent=self.agent,
            amount=Decimal('1000.00'),
            start_date=self.today - timedelta(days=365),
            end_date=self.today - timedelta(days=5),
            status=Contract.STATUS_ACTIVE
        )
        
        # Execute the Celery task
        result = check_contract_expirations.apply()
        
        # Verify no notifications were created
        task_result = result.result
        self.assertEqual(task_result['total_notifications'], 0)
        
        notifications = Notification.objects.filter(agent=self.agent)
        self.assertEqual(notifications.count(), 0)
    
    def test_contract_expiration_duplicate_prevention(self):
        """Test that duplicate notifications are prevented."""
        # Create expired contract
        contract = Contract.objects.create(
            property=self.property,
            customer=self.customer,
            agent=self.agent,
            amount=Decimal('1000.00'),
            start_date=self.today - timedelta(days=365),
            end_date=self.today - timedelta(days=5),
            status=Contract.STATUS_ACTIVE
        )
        
        # Execute the task twice
        result1 = check_contract_expirations.apply()
        result2 = check_contract_expirations.apply()
        
        # Verify only one notification was created
        notifications = Notification.objects.filter(agent=self.agent)
        self.assertEqual(notifications.count(), 1)
        
        # Verify second task run found no new notifications to create
        task_result2 = result2.result
        self.assertEqual(task_result2['total_notifications'], 0)


class InvoiceOverdueWorkflowTest(TransactionTestCase):
    """Integration tests for invoice overdue notification workflow."""
    
    def setUp(self):
        """Set up test data."""
        self.agent = Agent.objects.create(
            username='agent1',
            email='agent1@test.com',
            first_name='Test',
            last_name='Agent'
        )
        
        self.customer = Customer.objects.create(
            username='customer1',
            email='customer1@test.com',
            first_name='Test',
            last_name='Customer'
        )
        
        self.property = Property.objects.create(
            title='Test Property',
            address='123 Test St',
            property_type='apartment',
            status='available'
        )
        
        self.contract = Contract.objects.create(
            property=self.property,
            customer=self.customer,
            agent=self.agent,
            amount=Decimal('1000.00'),
            start_date=timezone.now().date() - timedelta(days=365),
            end_date=timezone.now().date() + timedelta(days=365),
            status=Contract.STATUS_ACTIVE
        )
        
        # Create notification preferences
        self.preferences = NotificationPreference.objects.create(
            agent=self.agent,
            receive_invoice_overdue=True,
            email_notifications=True,
            notification_frequency='immediately'
        )
        
        self.today = timezone.now().date()
    
    @patch('accounting.models_invoice.Invoice.get_balance')
    def test_end_to_end_invoice_overdue_workflow(self, mock_get_balance):
        """Test complete workflow from overdue invoice detection to notification creation."""
        mock_get_balance.return_value = Decimal('1000.00')
        
        # Create invoices at different overdue stages
        standard_overdue = Invoice.objects.create(
            customer=self.customer,
            contract=self.contract,
            number='INV-001',
            amount=Decimal('1000.00'),
            due_date=self.today - timedelta(days=3),
            status='validated'
        )
        
        urgent_overdue = Invoice.objects.create(
            customer=self.customer,
            contract=self.contract,
            number='INV-002',
            amount=Decimal('1200.00'),
            due_date=self.today - timedelta(days=15),
            status='validated'
        )
        
        critical_overdue = Invoice.objects.create(
            customer=self.customer,
            contract=self.contract,
            number='INV-003',
            amount=Decimal('1500.00'),
            due_date=self.today - timedelta(days=35),
            status='validated'
        )
        
        # Execute the Celery task
        result = check_invoice_overdue.apply()
        
        # Verify task completed successfully
        self.assertTrue(result.successful())
        task_result = result.result
        
        # Verify correct number of notifications were created
        self.assertEqual(task_result['standard_overdue'], 1)
        self.assertEqual(task_result['urgent_overdue'], 1)
        self.assertEqual(task_result['critical_overdue'], 1)
        self.assertEqual(task_result['total_notifications'], 3)
        
        # Verify notifications were created in database
        notifications = Notification.objects.filter(agent=self.agent).order_by('created_at')
        self.assertEqual(notifications.count(), 3)
        
        # Verify notification content
        standard_notification = notifications.filter(notification_type='invoice_overdue').first()
        self.assertIsNotNone(standard_notification)
        self.assertIn('Factura Vencida', standard_notification.title)
        self.assertEqual(standard_notification.related_object, standard_overdue)
        
        urgent_notification = notifications.filter(notification_type='invoice_overdue_urgent').first()
        self.assertIsNotNone(urgent_notification)
        self.assertIn('Factura Urgente Vencida', urgent_notification.title)
        self.assertEqual(urgent_notification.related_object, urgent_overdue)
        
        critical_notification = notifications.filter(notification_type='invoice_overdue_critical').first()
        self.assertIsNotNone(critical_notification)
        self.assertIn('Factura Crítica Vencida', critical_notification.title)
        self.assertEqual(critical_notification.related_object, critical_overdue)


class RentIncreaseWorkflowTest(TransactionTestCase):
    """Integration tests for rent increase notification workflow."""
    
    def setUp(self):
        """Set up test data."""
        self.agent = Agent.objects.create(
            username='agent1',
            email='agent1@test.com',
            first_name='Test',
            last_name='Agent'
        )
        
        self.customer = Customer.objects.create(
            username='customer1',
            email='customer1@test.com',
            first_name='Test',
            last_name='Customer'
        )
        
        self.property = Property.objects.create(
            title='Test Property',
            address='123 Test St',
            property_type='apartment',
            status='available'
        )
        
        # Create notification preferences
        self.preferences = NotificationPreference.objects.create(
            agent=self.agent,
            receive_rent_increase=True,
            email_notifications=True,
            notification_frequency='immediately'
        )
        
        self.today = timezone.now().date()
    
    def test_end_to_end_rent_increase_workflow(self):
        """Test complete workflow from rent increase detection to notification creation."""
        # Create contracts with different rent increase scenarios
        overdue_contract = Contract.objects.create(
            property=self.property,
            customer=self.customer,
            agent=self.agent,
            amount=Decimal('1000.00'),
            start_date=self.today - timedelta(days=365),
            end_date=self.today + timedelta(days=365),
            next_increase_date=self.today - timedelta(days=10),
            frequency='monthly',
            status=Contract.STATUS_ACTIVE
        )
        
        upcoming_contract = Contract.objects.create(
            property=self.property,
            customer=self.customer,
            agent=self.agent,
            amount=Decimal('1200.00'),
            start_date=self.today - timedelta(days=365),
            end_date=self.today + timedelta(days=365),
            next_increase_date=self.today + timedelta(days=5),
            frequency='quarterly',
            status=Contract.STATUS_ACTIVE
        )
        
        # Execute the Celery task
        result = check_rent_increases.apply()
        
        # Verify task completed successfully
        self.assertTrue(result.successful())
        task_result = result.result
        
        # Verify correct number of notifications were created
        self.assertEqual(task_result['overdue_increases'], 1)
        self.assertEqual(task_result['upcoming_increases'], 1)
        self.assertEqual(task_result['total_notifications'], 2)
        
        # Verify notifications were created in database
        notifications = Notification.objects.filter(agent=self.agent).order_by('created_at')
        self.assertEqual(notifications.count(), 2)
        
        # Verify notification content
        overdue_notification = notifications.filter(notification_type='rent_increase_overdue').first()
        self.assertIsNotNone(overdue_notification)
        self.assertIn('Aumento de Alquiler Vencido', overdue_notification.title)
        self.assertEqual(overdue_notification.related_object, overdue_contract)
        
        upcoming_notification = notifications.filter(notification_type='rent_increase_due').first()
        self.assertIsNotNone(upcoming_notification)
        self.assertIn('Aumento de Alquiler Próximo', upcoming_notification.title)
        self.assertEqual(upcoming_notification.related_object, upcoming_contract)


class InvoiceDueSoonWorkflowTest(TransactionTestCase):
    """Integration tests for invoice due soon notification workflow."""
    
    def setUp(self):
        """Set up test data."""
        self.agent = Agent.objects.create(
            username='agent1',
            email='agent1@test.com',
            first_name='Test',
            last_name='Agent'
        )
        
        self.customer = Customer.objects.create(
            username='customer1',
            email='customer1@test.com',
            first_name='Test',
            last_name='Customer'
        )
        
        self.property = Property.objects.create(
            title='Test Property',
            address='123 Test St',
            property_type='apartment',
            status='available'
        )
        
        self.contract = Contract.objects.create(
            property=self.property,
            customer=self.customer,
            agent=self.agent,
            amount=Decimal('1000.00'),
            start_date=timezone.now().date() - timedelta(days=365),
            end_date=timezone.now().date() + timedelta(days=365),
            status=Contract.STATUS_ACTIVE
        )
        
        # Create notification preferences
        self.preferences = NotificationPreference.objects.create(
            agent=self.agent,
            receive_invoice_due_soon=True,
            email_notifications=True,
            notification_frequency='immediately'
        )
        
        self.today = timezone.now().date()
    
    @patch('accounting.models_invoice.Invoice.get_balance')
    def test_end_to_end_invoice_due_soon_workflow(self, mock_get_balance):
        """Test complete workflow from due soon invoice detection to notification creation."""
        mock_get_balance.return_value = Decimal('1000.00')
        
        # Create invoices at different due soon stages
        advance_due = Invoice.objects.create(
            customer=self.customer,
            contract=self.contract,
            number='INV-001',
            amount=Decimal('1000.00'),
            due_date=self.today + timedelta(days=5),
            status='validated'
        )
        
        urgent_due = Invoice.objects.create(
            customer=self.customer,
            contract=self.contract,
            number='INV-002',
            amount=Decimal('1200.00'),
            due_date=self.today + timedelta(days=2),
            status='validated'
        )
        
        # Execute the Celery task
        result = check_invoice_due_soon.apply()
        
        # Verify task completed successfully
        self.assertTrue(result.successful())
        task_result = result.result
        
        # Verify correct number of notifications were created
        self.assertEqual(task_result['advance_due_notifications'], 1)
        self.assertEqual(task_result['urgent_due_notifications'], 1)
        self.assertEqual(task_result['total_notifications'], 2)
        
        # Verify notifications were created in database
        notifications = Notification.objects.filter(agent=self.agent).order_by('created_at')
        self.assertEqual(notifications.count(), 2)


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class EmailNotificationTest(TestCase):
    """Integration tests for email notification delivery."""
    
    def setUp(self):
        """Set up test data."""
        self.agent = Agent.objects.create(
            username='agent1',
            email='agent1@test.com',
            first_name='Test',
            last_name='Agent'
        )
        
        self.customer = Customer.objects.create(
            username='customer1',
            email='customer1@test.com',
            first_name='Test',
            last_name='Customer'
        )
        
        self.property = Property.objects.create(
            title='Test Property',
            address='123 Test St',
            property_type='apartment',
            status='available'
        )
        
        self.contract = Contract.objects.create(
            property=self.property,
            customer=self.customer,
            agent=self.agent,
            amount=Decimal('1000.00'),
            start_date=timezone.now().date() - timedelta(days=365),
            end_date=timezone.now().date() + timedelta(days=365),
            status=Contract.STATUS_ACTIVE
        )
        
        # Create notification preferences with email enabled
        self.preferences = NotificationPreference.objects.create(
            agent=self.agent,
            receive_contract_expiration=True,
            receive_invoice_overdue=True,
            receive_rent_increase=True,
            receive_invoice_due_soon=True,
            email_notifications=True,
            notification_frequency='immediately'
        )
        
        # Clear the test mailbox
        mail.outbox = []
    
    def test_contract_expiration_email_notification(self):
        """Test email notification for contract expiration."""
        notification = create_notification(
            agent=self.agent,
            title='Contrato Vencido - Test Property',
            message='El contrato para la propiedad Test Property ha vencido.',
            notification_type='contract_expired',
            related_object=self.contract
        )
        
        # Verify email was sent
        self.assertEqual(len(mail.outbox), 1)
        
        email = mail.outbox[0]
        self.assertEqual(email.to, [self.agent.email])
        self.assertIn('Contrato Vencido', email.subject)
        self.assertIn('Test Property', email.body)
    
    @patch('accounting.models_invoice.Invoice.get_balance')
    def test_invoice_overdue_email_notification(self, mock_get_balance):
        """Test email notification for overdue invoice."""
        mock_get_balance.return_value = Decimal('1000.00')
        
        invoice = Invoice.objects.create(
            customer=self.customer,
            contract=self.contract,
            number='INV-001',
            amount=Decimal('1000.00'),
            due_date=timezone.now().date() - timedelta(days=10),
            status='validated'
        )
        
        notification = create_notification(
            agent=self.agent,
            title='Factura Vencida - INV-001',
            message='La factura INV-001 está vencida.',
            notification_type='invoice_overdue',
            related_object=invoice
        )
        
        # Verify email was sent
        self.assertEqual(len(mail.outbox), 1)
        
        email = mail.outbox[0]
        self.assertEqual(email.to, [self.agent.email])
        self.assertIn('Factura Vencida', email.subject)
        self.assertIn('INV-001', email.body)
    
    def test_rent_increase_email_notification(self):
        """Test email notification for rent increase."""
        notification = create_notification(
            agent=self.agent,
            title='Aumento de Alquiler Próximo - Test Property',
            message='El aumento de alquiler para Test Property está próximo.',
            notification_type='rent_increase_due',
            related_object=self.contract
        )
        
        # Verify email was sent
        self.assertEqual(len(mail.outbox), 1)
        
        email = mail.outbox[0]
        self.assertEqual(email.to, [self.agent.email])
        self.assertIn('Aumento de Alquiler', email.subject)
        self.assertIn('Test Property', email.body)
    
    def test_email_not_sent_when_disabled(self):
        """Test that email is not sent when email notifications are disabled."""
        # Disable email notifications
        self.preferences.email_notifications = False
        self.preferences.save()
        
        notification = create_notification(
            agent=self.agent,
            title='Test Notification',
            message='This is a test notification.',
            notification_type='contract_expired',
            related_object=self.contract
        )
        
        # Verify no email was sent
        self.assertEqual(len(mail.outbox), 0)
    
    def test_email_not_sent_for_disabled_notification_type(self):
        """Test that email is not sent for disabled notification types."""
        # Disable contract expiration notifications
        self.preferences.receive_contract_expiration = False
        self.preferences.save()
        
        notification = create_notification(
            agent=self.agent,
            title='Contrato Vencido - Test Property',
            message='El contrato para la propiedad Test Property ha vencido.',
            notification_type='contract_expired',
            related_object=self.contract
        )
        
        # Verify no email was sent
        self.assertEqual(len(mail.outbox), 0)


class BatchNotificationWorkflowTest(TransactionTestCase):
    """Integration tests for batch notification processing workflow."""
    
    def setUp(self):
        """Set up test data."""
        self.agent = Agent.objects.create(
            username='agent1',
            email='agent1@test.com',
            first_name='Test',
            last_name='Agent'
        )
        
        self.customer = Customer.objects.create(
            username='customer1',
            email='customer1@test.com',
            first_name='Test',
            last_name='Customer'
        )
        
        self.property = Property.objects.create(
            title='Test Property',
            address='123 Test St',
            property_type='apartment',
            status='available'
        )
        
        self.contract = Contract.objects.create(
            property=self.property,
            customer=self.customer,
            agent=self.agent,
            amount=Decimal('1000.00'),
            start_date=timezone.now().date() - timedelta(days=365),
            end_date=timezone.now().date() + timedelta(days=365),
            status=Contract.STATUS_ACTIVE
        )
    
    def test_daily_batch_processing_workflow(self):
        """Test complete daily batch processing workflow."""
        # Create preferences for daily batching
        preferences = NotificationPreference.objects.create(
            agent=self.agent,
            receive_contract_expiration=True,
            email_notifications=True,
            notification_frequency='daily'
        )
        
        # Create batch notifications scheduled for processing
        batch1 = NotificationBatch.objects.create(
            agent=self.agent,
            batch_type='daily',
            title='Contract Expiration 1',
            message='Contract expiring soon',
            notification_type='contract_expiring_soon',
            content_type=ContentType.objects.get_for_model(Contract),
            object_id=self.contract.pk,
            scheduled_for=timezone.now() - timedelta(hours=1),
            processed=False
        )
        
        batch2 = NotificationBatch.objects.create(
            agent=self.agent,
            batch_type='daily',
            title='Contract Expiration 2',
            message='Another contract expiring',
            notification_type='contract_expiring_soon',
            content_type=ContentType.objects.get_for_model(Contract),
            object_id=self.contract.pk,
            scheduled_for=timezone.now() - timedelta(hours=1),
            processed=False
        )
        
        # Execute the batch processing task
        result = process_notification_batches.apply()
        
        # Verify task completed successfully
        self.assertTrue(result.successful())
        task_result = result.result
        
        # Verify batch processing results
        self.assertEqual(task_result['daily_batches_sent'], 1)
        self.assertEqual(task_result['total_notifications_batched'], 2)
        self.assertEqual(task_result['agents_notified'], 1)
        
        # Verify batches were marked as processed
        batch1.refresh_from_db()
        batch2.refresh_from_db()
        self.assertTrue(batch1.processed)
        self.assertTrue(batch2.processed)
        self.assertIsNotNone(batch1.processed_at)
        self.assertIsNotNone(batch2.processed_at)
        
        # Verify summary notification was created
        summary_notifications = Notification.objects.filter(
            agent=self.agent,
            notification_type='batch_summary'
        )
        self.assertEqual(summary_notifications.count(), 1)
        
        summary = summary_notifications.first()
        self.assertIn('Resumen Diario', summary.title)
        self.assertIn('2 notificaciones', summary.title)
    
    def test_weekly_batch_processing_workflow(self):
        """Test complete weekly batch processing workflow."""
        # Create preferences for weekly batching
        preferences = NotificationPreference.objects.create(
            agent=self.agent,
            receive_rent_increase=True,
            email_notifications=True,
            notification_frequency='weekly'
        )
        
        # Create batch notifications scheduled for processing
        batch1 = NotificationBatch.objects.create(
            agent=self.agent,
            batch_type='weekly',
            title='Rent Increase 1',
            message='Rent increase due',
            notification_type='rent_increase_due',
            content_type=ContentType.objects.get_for_model(Contract),
            object_id=self.contract.pk,
            scheduled_for=timezone.now() - timedelta(hours=1),
            processed=False
        )
        
        # Execute the batch processing task
        result = process_notification_batches.apply()
        
        # Verify task completed successfully
        self.assertTrue(result.successful())
        task_result = result.result
        
        # Verify batch processing results
        self.assertEqual(task_result['weekly_batches_sent'], 1)
        self.assertEqual(task_result['total_notifications_batched'], 1)
        self.assertEqual(task_result['agents_notified'], 1)
        
        # Verify batch was marked as processed
        batch1.refresh_from_db()
        self.assertTrue(batch1.processed)
        
        # Verify summary notification was created
        summary_notifications = Notification.objects.filter(
            agent=self.agent,
            notification_type='batch_summary'
        )
        self.assertEqual(summary_notifications.count(), 1)
        
        summary = summary_notifications.first()
        self.assertIn('Resumen Semanal', summary.title)
    
    def test_no_batch_processing_when_none_ready(self):
        """Test batch processing when no batches are ready."""
        # Create batch notification scheduled for future
        batch = NotificationBatch.objects.create(
            agent=self.agent,
            batch_type='daily',
            title='Future Batch',
            message='Future batch message',
            notification_type='generic',
            scheduled_for=timezone.now() + timedelta(hours=1),
            processed=False
        )
        
        # Execute the batch processing task
        result = process_notification_batches.apply()
        
        # Verify task completed successfully but processed nothing
        self.assertTrue(result.successful())
        task_result = result.result
        
        self.assertEqual(task_result['daily_batches_sent'], 0)
        self.assertEqual(task_result['weekly_batches_sent'], 0)
        self.assertEqual(task_result['total_notifications_batched'], 0)
        self.assertEqual(task_result['agents_notified'], 0)
        
        # Verify batch was not processed
        batch.refresh_from_db()
        self.assertFalse(batch.processed)


class CeleryTaskErrorHandlingTest(TransactionTestCase):
    """Integration tests for Celery task error handling."""
    
    def setUp(self):
        """Set up test data."""
        self.agent = Agent.objects.create(
            username='agent1',
            email='agent1@test.com',
            first_name='Test',
            last_name='Agent'
        )
    
    @patch('user_notifications.checkers.ContractExpirationChecker.check_and_notify')
    def test_contract_expiration_task_database_error_retry(self, mock_check):
        """Test that database errors in contract expiration task trigger retry."""
        from django.db import DatabaseError
        
        # Mock database error
        mock_check.side_effect = DatabaseError("Database connection failed")
        
        # Execute task and expect it to fail with retry
        result = check_contract_expirations.apply()
        
        # Verify task failed
        self.assertFalse(result.successful())
        self.assertIsInstance(result.result, DatabaseError)
    
    @patch('user_notifications.checkers.InvoiceOverdueChecker.check_and_notify')
    def test_invoice_overdue_task_unexpected_error(self, mock_check):
        """Test that unexpected errors in invoice overdue task are handled."""
        # Mock unexpected error
        mock_check.side_effect = ValueError("Unexpected error")
        
        # Execute task and expect it to fail
        result = check_invoice_overdue.apply()
        
        # Verify task failed
        self.assertFalse(result.successful())
        self.assertIsInstance(result.result, ValueError)
    
    @patch('user_notifications.services.process_ready_notification_batches')
    def test_batch_processing_task_error_handling(self, mock_process):
        """Test error handling in batch processing task."""
        from django.db import DatabaseError
        
        # Mock database error
        mock_process.side_effect = DatabaseError("Database error during batch processing")
        
        # Execute task and expect it to fail with retry
        result = process_notification_batches.apply()
        
        # Verify task failed
        self.assertFalse(result.successful())
        self.assertIsInstance(result.result, DatabaseError)


class NotificationSystemHealthTest(TestCase):
    """Integration tests for notification system health and configuration."""
    
    def setUp(self):
        """Set up test data."""
        self.agent = Agent.objects.create(
            username='agent1',
            email='agent1@test.com',
            first_name='Test',
            last_name='Agent'
        )
    
    def test_notification_preferences_creation(self):
        """Test that notification preferences are created correctly."""
        from user_notifications.services import get_notification_preferences
        
        # Ensure no preferences exist initially
        NotificationPreference.objects.filter(agent=self.agent).delete()
        
        # Get preferences (should create default ones)
        preferences = get_notification_preferences(self.agent)
        
        # Verify preferences were created with correct defaults
        self.assertIsInstance(preferences, NotificationPreference)
        self.assertEqual(preferences.agent, self.agent)
        self.assertTrue(preferences.receive_invoice_due_soon)
        self.assertTrue(preferences.receive_invoice_overdue)
        self.assertTrue(preferences.receive_contract_expiration)
        self.assertTrue(preferences.receive_rent_increase)
        self.assertEqual(preferences.notification_frequency, 'immediately')
        self.assertFalse(preferences.email_notifications)
    
    def test_notification_log_prevents_duplicates(self):
        """Test that notification log correctly prevents duplicate notifications."""
        from user_notifications.services import create_notification_if_not_exists
        
        # Create first notification
        notification1, created1 = create_notification_if_not_exists(
            agent=self.agent,
            title='Test Notification',
            message='Test message',
            notification_type='generic',
            duplicate_threshold_days=1
        )
        
        self.assertTrue(created1)
        self.assertIsInstance(notification1, Notification)
        
        # Try to create duplicate
        notification2, created2 = create_notification_if_not_exists(
            agent=self.agent,
            title='Test Notification',
            message='Test message',
            notification_type='generic',
            duplicate_threshold_days=1
        )
        
        self.assertFalse(created2)
        self.assertIsNone(notification2)
        
        # Verify only one notification exists
        notifications = Notification.objects.filter(agent=self.agent)
        self.assertEqual(notifications.count(), 1)
    
    def test_notification_batch_scheduling(self):
        """Test that notification batches are scheduled correctly."""
        # Create preferences for daily batching
        preferences = NotificationPreference.objects.create(
            agent=self.agent,
            notification_frequency='daily',
            email_notifications=False
        )
        
        # Create batch notification
        batch = NotificationBatch.create_batch_notification(
            agent=self.agent,
            title='Test Batch',
            message='Test batch message',
            notification_type='generic'
        )
        
        self.assertIsInstance(batch, NotificationBatch)
        self.assertEqual(batch.batch_type, 'daily')
        self.assertEqual(batch.scheduled_for.hour, 9)
        self.assertFalse(batch.processed)
        
        # Verify scheduled for next day
        expected_date = timezone.now().date() + timedelta(days=1)
        self.assertEqual(batch.scheduled_for.date(), expected_date)