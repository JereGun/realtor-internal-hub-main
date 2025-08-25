"""
Unit tests for notification business logic.

This module contains comprehensive unit tests for all business logic checkers
and notification creation functionality in the notification system.
"""

import pytest
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType

from contracts.models import Contract
from accounting.models_invoice import Invoice
from properties.models import Property
from customers.models import Customer
from agents.models import Agent

from user_notifications.models import Notification, NotificationLog, NotificationBatch
from user_notifications.models_preferences import NotificationPreference
from user_notifications.checkers import (
    ContractExpirationChecker,
    InvoiceOverdueChecker,
    RentIncreaseChecker,
    InvoiceDueSoonChecker
)
from user_notifications.services import (
    create_notification,
    create_notification_if_not_exists,
    get_notification_preferences,
    batch_create_notifications
)

User = get_user_model()


class ContractExpirationCheckerTest(TestCase):
    """Test cases for ContractExpirationChecker business logic."""
    
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
        
        self.checker = ContractExpirationChecker()
        self.today = self.checker.today
        
        # Create notification preferences
        self.preferences = NotificationPreference.objects.create(
            agent=self.agent,
            receive_contract_expiration=True,
            email_notifications=True
        )
    
    def test_get_expiring_contracts_30_days(self):
        """Test getting contracts expiring within 30 days."""
        # Create contract expiring in 25 days
        expiring_contract = Contract.objects.create(
            property=self.property,
            customer=self.customer,
            agent=self.agent,
            amount=Decimal('1000.00'),
            start_date=self.today - timedelta(days=365),
            end_date=self.today + timedelta(days=25),
            status=Contract.STATUS_ACTIVE
        )
        
        # Create contract expiring in 35 days (should not be included)
        Contract.objects.create(
            property=self.property,
            customer=self.customer,
            agent=self.agent,
            amount=Decimal('1000.00'),
            start_date=self.today - timedelta(days=365),
            end_date=self.today + timedelta(days=35),
            status=Contract.STATUS_ACTIVE
        )
        
        contracts = self.checker.get_expiring_contracts(30)
        self.assertEqual(contracts.count(), 1)
        self.assertEqual(contracts.first(), expiring_contract)
    
    def test_get_expired_contracts(self):
        """Test getting contracts that have already expired."""
        # Create expired contract
        expired_contract = Contract.objects.create(
            property=self.property,
            customer=self.customer,
            agent=self.agent,
            amount=Decimal('1000.00'),
            start_date=self.today - timedelta(days=365),
            end_date=self.today - timedelta(days=5),
            status=Contract.STATUS_ACTIVE
        )
        
        # Create active contract (should not be included)
        Contract.objects.create(
            property=self.property,
            customer=self.customer,
            agent=self.agent,
            amount=Decimal('1000.00'),
            start_date=self.today - timedelta(days=365),
            end_date=self.today + timedelta(days=30),
            status=Contract.STATUS_ACTIVE
        )
        
        contracts = self.checker.get_expired_contracts()
        self.assertEqual(contracts.count(), 1)
        self.assertEqual(contracts.first(), expired_contract)
    
    def test_should_notify_with_preferences_enabled(self):
        """Test notification should be sent when preferences are enabled."""
        contract = Contract.objects.create(
            property=self.property,
            customer=self.customer,
            agent=self.agent,
            amount=Decimal('1000.00'),
            start_date=self.today - timedelta(days=365),
            end_date=self.today + timedelta(days=25),
            status=Contract.STATUS_ACTIVE
        )
        
        should_notify = self.checker.should_notify(contract, 'contract_expiring_soon')
        self.assertTrue(should_notify)
    
    def test_should_notify_with_preferences_disabled(self):
        """Test notification should not be sent when preferences are disabled."""
        self.preferences.receive_contract_expiration = False
        self.preferences.save()
        
        contract = Contract.objects.create(
            property=self.property,
            customer=self.customer,
            agent=self.agent,
            amount=Decimal('1000.00'),
            start_date=self.today - timedelta(days=365),
            end_date=self.today + timedelta(days=25),
            status=Contract.STATUS_ACTIVE
        )
        
        should_notify = self.checker.should_notify(contract, 'contract_expiring_soon')
        self.assertFalse(should_notify)
    
    def test_should_notify_no_preferences(self):
        """Test notification defaults to True when no preferences exist."""
        self.preferences.delete()
        
        contract = Contract.objects.create(
            property=self.property,
            customer=self.customer,
            agent=self.agent,
            amount=Decimal('1000.00'),
            start_date=self.today - timedelta(days=365),
            end_date=self.today + timedelta(days=25),
            status=Contract.STATUS_ACTIVE
        )
        
        should_notify = self.checker.should_notify(contract, 'contract_expiring_soon')
        self.assertTrue(should_notify)
    
    def test_create_expiration_notification_expired(self):
        """Test creating notification for expired contract."""
        contract = Contract.objects.create(
            property=self.property,
            customer=self.customer,
            agent=self.agent,
            amount=Decimal('1000.00'),
            start_date=self.today - timedelta(days=365),
            end_date=self.today - timedelta(days=5),
            status=Contract.STATUS_ACTIVE
        )
        
        with patch('user_notifications.checkers.create_notification_if_not_exists') as mock_create:
            mock_create.return_value = (MagicMock(), True)
            
            notification = self.checker.create_expiration_notification(contract, -5)
            
            mock_create.assert_called_once()
            args, kwargs = mock_create.call_args
            
            self.assertEqual(kwargs['agent'], self.agent)
            self.assertIn('Contrato Vencido', kwargs['title'])
            self.assertIn('venció el', kwargs['message'])
            self.assertEqual(kwargs['notification_type'], 'contract_expired')
            self.assertEqual(kwargs['related_object'], contract)
    
    def test_create_expiration_notification_urgent(self):
        """Test creating notification for contract expiring within 7 days."""
        contract = Contract.objects.create(
            property=self.property,
            customer=self.customer,
            agent=self.agent,
            amount=Decimal('1000.00'),
            start_date=self.today - timedelta(days=365),
            end_date=self.today + timedelta(days=5),
            status=Contract.STATUS_ACTIVE
        )
        
        with patch('user_notifications.checkers.create_notification_if_not_exists') as mock_create:
            mock_create.return_value = (MagicMock(), True)
            
            notification = self.checker.create_expiration_notification(contract, 5)
            
            mock_create.assert_called_once()
            args, kwargs = mock_create.call_args
            
            self.assertEqual(kwargs['agent'], self.agent)
            self.assertIn('Contrato Vence Pronto', kwargs['title'])
            self.assertIn('vence en 5 días', kwargs['message'])
            self.assertEqual(kwargs['notification_type'], 'contract_expiring_urgent')
    
    def test_create_expiration_notification_advance(self):
        """Test creating notification for contract expiring within 30 days."""
        contract = Contract.objects.create(
            property=self.property,
            customer=self.customer,
            agent=self.agent,
            amount=Decimal('1000.00'),
            start_date=self.today - timedelta(days=365),
            end_date=self.today + timedelta(days=20),
            status=Contract.STATUS_ACTIVE
        )
        
        with patch('user_notifications.checkers.create_notification_if_not_exists') as mock_create:
            mock_create.return_value = (MagicMock(), True)
            
            notification = self.checker.create_expiration_notification(contract, 20)
            
            mock_create.assert_called_once()
            args, kwargs = mock_create.call_args
            
            self.assertEqual(kwargs['agent'], self.agent)
            self.assertIn('Contrato Próximo a Vencer', kwargs['title'])
            self.assertIn('vence en 20 días', kwargs['message'])
            self.assertEqual(kwargs['notification_type'], 'contract_expiring_soon')
    
    @patch('user_notifications.checkers.create_notification_if_not_exists')
    def test_check_and_notify_comprehensive(self, mock_create):
        """Test comprehensive check and notify functionality."""
        mock_create.return_value = (MagicMock(), True)
        
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
        
        # Create urgent expiring contract
        Contract.objects.create(
            property=self.property,
            customer=self.customer,
            agent=self.agent,
            amount=Decimal('1000.00'),
            start_date=self.today - timedelta(days=365),
            end_date=self.today + timedelta(days=5),
            status=Contract.STATUS_ACTIVE
        )
        
        # Create advance notice contract
        Contract.objects.create(
            property=self.property,
            customer=self.customer,
            agent=self.agent,
            amount=Decimal('1000.00'),
            start_date=self.today - timedelta(days=365),
            end_date=self.today + timedelta(days=20),
            status=Contract.STATUS_ACTIVE
        )
        
        results = self.checker.check_and_notify()
        
        self.assertEqual(results['expired_notifications'], 1)
        self.assertEqual(results['urgent_notifications'], 1)
        self.assertEqual(results['advance_notifications'], 1)
        self.assertEqual(results['total_notifications'], 3)
        self.assertEqual(mock_create.call_count, 3)


class InvoiceOverdueCheckerTest(TestCase):
    """Test cases for InvoiceOverdueChecker business logic."""
    
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
        
        self.checker = InvoiceOverdueChecker()
        self.today = self.checker.today
        
        # Create notification preferences
        self.preferences = NotificationPreference.objects.create(
            agent=self.agent,
            receive_invoice_overdue=True,
            email_notifications=True
        )
    
    def test_get_overdue_invoices(self):
        """Test getting overdue invoices with outstanding balances."""
        # Create overdue invoice
        overdue_invoice = Invoice.objects.create(
            customer=self.customer,
            contract=self.contract,
            number='INV-001',
            amount=Decimal('1000.00'),
            due_date=self.today - timedelta(days=10),
            status='validated'
        )
        
        # Create current invoice (should not be included)
        Invoice.objects.create(
            customer=self.customer,
            contract=self.contract,
            number='INV-002',
            amount=Decimal('1000.00'),
            due_date=self.today + timedelta(days=10),
            status='validated'
        )
        
        invoices = self.checker.get_overdue_invoices()
        self.assertEqual(invoices.count(), 1)
        self.assertEqual(invoices.first(), overdue_invoice)
    
    def test_calculate_days_overdue(self):
        """Test calculating days overdue for an invoice."""
        invoice = Invoice.objects.create(
            customer=self.customer,
            contract=self.contract,
            number='INV-001',
            amount=Decimal('1000.00'),
            due_date=self.today - timedelta(days=15),
            status='validated'
        )
        
        days_overdue = self.checker.calculate_days_overdue(invoice)
        self.assertEqual(days_overdue, 15)
    
    def test_should_notify_with_preferences_enabled(self):
        """Test notification should be sent when preferences are enabled."""
        invoice = Invoice.objects.create(
            customer=self.customer,
            contract=self.contract,
            number='INV-001',
            amount=Decimal('1000.00'),
            due_date=self.today - timedelta(days=10),
            status='validated'
        )
        
        should_notify = self.checker.should_notify(invoice, 'invoice_overdue')
        self.assertTrue(should_notify)
    
    def test_should_notify_with_preferences_disabled(self):
        """Test notification should not be sent when preferences are disabled."""
        self.preferences.receive_invoice_overdue = False
        self.preferences.save()
        
        invoice = Invoice.objects.create(
            customer=self.customer,
            contract=self.contract,
            number='INV-001',
            amount=Decimal('1000.00'),
            due_date=self.today - timedelta(days=10),
            status='validated'
        )
        
        should_notify = self.checker.should_notify(invoice, 'invoice_overdue')
        self.assertFalse(should_notify)
    
    def test_should_notify_no_contract_agent(self):
        """Test notification should not be sent when invoice has no contract agent."""
        invoice = Invoice.objects.create(
            customer=self.customer,
            number='INV-001',
            amount=Decimal('1000.00'),
            due_date=self.today - timedelta(days=10),
            status='validated'
        )
        
        should_notify = self.checker.should_notify(invoice, 'invoice_overdue')
        self.assertFalse(should_notify)
    
    @patch('accounting.models_invoice.Invoice.get_balance')
    def test_create_overdue_notification_standard(self, mock_get_balance):
        """Test creating notification for standard overdue invoice (1-6 days)."""
        mock_get_balance.return_value = Decimal('1000.00')
        
        invoice = Invoice.objects.create(
            customer=self.customer,
            contract=self.contract,
            number='INV-001',
            amount=Decimal('1000.00'),
            due_date=self.today - timedelta(days=3),
            status='validated'
        )
        
        with patch('user_notifications.checkers.create_notification_if_not_exists') as mock_create:
            mock_create.return_value = (MagicMock(), True)
            
            notification = self.checker.create_overdue_notification(invoice, 3)
            
            mock_create.assert_called_once()
            args, kwargs = mock_create.call_args
            
            self.assertEqual(kwargs['agent'], self.agent)
            self.assertIn('Factura Vencida', kwargs['title'])
            self.assertIn('está vencida hace 3 días', kwargs['message'])
            self.assertEqual(kwargs['notification_type'], 'invoice_overdue')
    
    @patch('accounting.models_invoice.Invoice.get_balance')
    def test_create_overdue_notification_urgent(self, mock_get_balance):
        """Test creating notification for urgent overdue invoice (7-29 days)."""
        mock_get_balance.return_value = Decimal('1000.00')
        
        invoice = Invoice.objects.create(
            customer=self.customer,
            contract=self.contract,
            number='INV-001',
            amount=Decimal('1000.00'),
            due_date=self.today - timedelta(days=15),
            status='validated'
        )
        
        with patch('user_notifications.checkers.create_notification_if_not_exists') as mock_create:
            mock_create.return_value = (MagicMock(), True)
            
            notification = self.checker.create_overdue_notification(invoice, 15)
            
            mock_create.assert_called_once()
            args, kwargs = mock_create.call_args
            
            self.assertEqual(kwargs['agent'], self.agent)
            self.assertIn('Factura Urgente Vencida', kwargs['title'])
            self.assertIn('está vencida hace 15 días', kwargs['message'])
            self.assertEqual(kwargs['notification_type'], 'invoice_overdue_urgent')
    
    @patch('accounting.models_invoice.Invoice.get_balance')
    def test_create_overdue_notification_critical(self, mock_get_balance):
        """Test creating notification for critical overdue invoice (30+ days)."""
        mock_get_balance.return_value = Decimal('1000.00')
        
        invoice = Invoice.objects.create(
            customer=self.customer,
            contract=self.contract,
            number='INV-001',
            amount=Decimal('1000.00'),
            due_date=self.today - timedelta(days=35),
            status='validated'
        )
        
        with patch('user_notifications.checkers.create_notification_if_not_exists') as mock_create:
            mock_create.return_value = (MagicMock(), True)
            
            notification = self.checker.create_overdue_notification(invoice, 35)
            
            mock_create.assert_called_once()
            args, kwargs = mock_create.call_args
            
            self.assertEqual(kwargs['agent'], self.agent)
            self.assertIn('Factura Crítica Vencida', kwargs['title'])
            self.assertIn('está vencida hace 35 días', kwargs['message'])
            self.assertEqual(kwargs['notification_type'], 'invoice_overdue_critical')


class RentIncreaseCheckerTest(TestCase):
    """Test cases for RentIncreaseChecker business logic."""
    
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
        
        self.checker = RentIncreaseChecker()
        self.today = self.checker.today
        
        # Create notification preferences
        self.preferences = NotificationPreference.objects.create(
            agent=self.agent,
            receive_rent_increase=True,
            email_notifications=True
        )
    
    def test_get_contracts_with_increases_due(self):
        """Test getting contracts with rent increases due within threshold."""
        # Create contract with increase due in 5 days
        due_contract = Contract.objects.create(
            property=self.property,
            customer=self.customer,
            agent=self.agent,
            amount=Decimal('1000.00'),
            start_date=self.today - timedelta(days=365),
            end_date=self.today + timedelta(days=365),
            next_increase_date=self.today + timedelta(days=5),
            frequency='monthly',
            status=Contract.STATUS_ACTIVE
        )
        
        # Create contract with increase due in 10 days (should not be included with 7-day threshold)
        Contract.objects.create(
            property=self.property,
            customer=self.customer,
            agent=self.agent,
            amount=Decimal('1000.00'),
            start_date=self.today - timedelta(days=365),
            end_date=self.today + timedelta(days=365),
            next_increase_date=self.today + timedelta(days=10),
            frequency='monthly',
            status=Contract.STATUS_ACTIVE
        )
        
        contracts = self.checker.get_contracts_with_increases_due(7)
        self.assertEqual(contracts.count(), 1)
        self.assertEqual(contracts.first(), due_contract)
    
    def test_get_overdue_increases(self):
        """Test getting contracts with overdue rent increases."""
        # Create contract with overdue increase
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
        
        # Create contract with future increase (should not be included)
        Contract.objects.create(
            property=self.property,
            customer=self.customer,
            agent=self.agent,
            amount=Decimal('1000.00'),
            start_date=self.today - timedelta(days=365),
            end_date=self.today + timedelta(days=365),
            next_increase_date=self.today + timedelta(days=10),
            frequency='monthly',
            status=Contract.STATUS_ACTIVE
        )
        
        contracts = self.checker.get_overdue_increases()
        self.assertEqual(contracts.count(), 1)
        self.assertEqual(contracts.first(), overdue_contract)
    
    def test_calculate_days_until_increase(self):
        """Test calculating days until next rent increase."""
        contract = Contract.objects.create(
            property=self.property,
            customer=self.customer,
            agent=self.agent,
            amount=Decimal('1000.00'),
            start_date=self.today - timedelta(days=365),
            end_date=self.today + timedelta(days=365),
            next_increase_date=self.today + timedelta(days=15),
            frequency='monthly',
            status=Contract.STATUS_ACTIVE
        )
        
        days_until = self.checker.calculate_days_until_increase(contract)
        self.assertEqual(days_until, 15)
    
    def test_calculate_days_until_increase_overdue(self):
        """Test calculating days until increase for overdue increase."""
        contract = Contract.objects.create(
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
        
        days_until = self.checker.calculate_days_until_increase(contract)
        self.assertEqual(days_until, -10)
    
    def test_calculate_days_until_increase_no_date(self):
        """Test calculating days until increase when no increase date is set."""
        contract = Contract.objects.create(
            property=self.property,
            customer=self.customer,
            agent=self.agent,
            amount=Decimal('1000.00'),
            start_date=self.today - timedelta(days=365),
            end_date=self.today + timedelta(days=365),
            frequency='monthly',
            status=Contract.STATUS_ACTIVE
        )
        
        days_until = self.checker.calculate_days_until_increase(contract)
        self.assertIsNone(days_until)
    
    def test_calculate_next_increase_date_monthly(self):
        """Test calculating next increase date for monthly frequency."""
        contract = Contract.objects.create(
            property=self.property,
            customer=self.customer,
            agent=self.agent,
            amount=Decimal('1000.00'),
            start_date=self.today - timedelta(days=365),
            end_date=self.today + timedelta(days=365),
            next_increase_date=date(2024, 1, 15),
            frequency='monthly',
            status=Contract.STATUS_ACTIVE
        )
        
        next_date = self.checker.calculate_next_increase_date(contract)
        expected_date = date(2024, 2, 15)
        self.assertEqual(next_date, expected_date)
    
    def test_calculate_next_increase_date_quarterly(self):
        """Test calculating next increase date for quarterly frequency."""
        contract = Contract.objects.create(
            property=self.property,
            customer=self.customer,
            agent=self.agent,
            amount=Decimal('1000.00'),
            start_date=self.today - timedelta(days=365),
            end_date=self.today + timedelta(days=365),
            next_increase_date=date(2024, 1, 15),
            frequency='quarterly',
            status=Contract.STATUS_ACTIVE
        )
        
        next_date = self.checker.calculate_next_increase_date(contract)
        expected_date = date(2024, 4, 15)
        self.assertEqual(next_date, expected_date)
    
    def test_calculate_next_increase_date_annually(self):
        """Test calculating next increase date for annual frequency."""
        contract = Contract.objects.create(
            property=self.property,
            customer=self.customer,
            agent=self.agent,
            amount=Decimal('1000.00'),
            start_date=self.today - timedelta(days=365),
            end_date=self.today + timedelta(days=365),
            next_increase_date=date(2024, 1, 15),
            frequency='annually',
            status=Contract.STATUS_ACTIVE
        )
        
        next_date = self.checker.calculate_next_increase_date(contract)
        expected_date = date(2025, 1, 15)
        self.assertEqual(next_date, expected_date)
    
    def test_calculate_next_increase_date_no_frequency(self):
        """Test calculating next increase date when no frequency is set."""
        contract = Contract.objects.create(
            property=self.property,
            customer=self.customer,
            agent=self.agent,
            amount=Decimal('1000.00'),
            start_date=self.today - timedelta(days=365),
            end_date=self.today + timedelta(days=365),
            next_increase_date=date(2024, 1, 15),
            status=Contract.STATUS_ACTIVE
        )
        
        next_date = self.checker.calculate_next_increase_date(contract)
        self.assertIsNone(next_date)


class NotificationServicesTest(TestCase):
    """Test cases for notification service functions."""
    
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
    
    def test_create_notification_basic(self):
        """Test basic notification creation."""
        notification = create_notification(
            agent=self.agent,
            title='Test Notification',
            message='This is a test notification',
            notification_type='generic'
        )
        
        self.assertIsInstance(notification, Notification)
        self.assertEqual(notification.agent, self.agent)
        self.assertEqual(notification.title, 'Test Notification')
        self.assertEqual(notification.message, 'This is a test notification')
        self.assertEqual(notification.notification_type, 'generic')
        self.assertFalse(notification.is_read)
    
    def test_create_notification_with_related_object(self):
        """Test notification creation with related object."""
        notification = create_notification(
            agent=self.agent,
            title='Contract Notification',
            message='Contract related notification',
            notification_type='contract_expiration',
            related_object=self.contract
        )
        
        self.assertEqual(notification.related_object, self.contract)
        self.assertEqual(notification.content_type, ContentType.objects.get_for_model(Contract))
        self.assertEqual(notification.object_id, self.contract.pk)
    
    def test_create_notification_if_not_exists_new(self):
        """Test creating notification when no duplicate exists."""
        notification, created = create_notification_if_not_exists(
            agent=self.agent,
            title='Test Notification',
            message='This is a test notification',
            notification_type='generic',
            related_object=self.contract,
            duplicate_threshold_days=1
        )
        
        self.assertTrue(created)
        self.assertIsInstance(notification, Notification)
        
        # Check that notification log was created
        log_exists = NotificationLog.objects.filter(
            agent=self.agent,
            notification_type='generic',
            content_type=ContentType.objects.get_for_model(Contract),
            object_id=self.contract.pk
        ).exists()
        self.assertTrue(log_exists)
    
    def test_create_notification_if_not_exists_duplicate(self):
        """Test preventing duplicate notification creation."""
        # Create first notification
        notification1, created1 = create_notification_if_not_exists(
            agent=self.agent,
            title='Test Notification',
            message='This is a test notification',
            notification_type='generic',
            related_object=self.contract,
            duplicate_threshold_days=1
        )
        
        self.assertTrue(created1)
        
        # Try to create duplicate notification
        notification2, created2 = create_notification_if_not_exists(
            agent=self.agent,
            title='Test Notification',
            message='This is a test notification',
            notification_type='generic',
            related_object=self.contract,
            duplicate_threshold_days=1
        )
        
        self.assertFalse(created2)
        self.assertIsNone(notification2)
    
    def test_get_notification_preferences_existing(self):
        """Test getting existing notification preferences."""
        # Create preferences
        preferences = NotificationPreference.objects.create(
            agent=self.agent,
            receive_invoice_due_soon=True,
            receive_invoice_overdue=False,
            email_notifications=True
        )
        
        retrieved_preferences = get_notification_preferences(self.agent)
        self.assertEqual(retrieved_preferences, preferences)
        self.assertTrue(retrieved_preferences.receive_invoice_due_soon)
        self.assertFalse(retrieved_preferences.receive_invoice_overdue)
    
    def test_get_notification_preferences_create_default(self):
        """Test creating default notification preferences when none exist."""
        # Ensure no preferences exist
        NotificationPreference.objects.filter(agent=self.agent).delete()
        
        preferences = get_notification_preferences(self.agent)
        
        self.assertIsInstance(preferences, NotificationPreference)
        self.assertEqual(preferences.agent, self.agent)
        self.assertTrue(preferences.receive_invoice_due_soon)
        self.assertTrue(preferences.receive_invoice_overdue)
        self.assertEqual(preferences.notification_frequency, 'immediately')
        self.assertFalse(preferences.email_notifications)
    
    def test_batch_create_notifications_immediate(self):
        """Test batch notification creation with immediate delivery."""
        # Create preferences for immediate delivery
        NotificationPreference.objects.create(
            agent=self.agent,
            notification_frequency='immediately',
            email_notifications=False
        )
        
        notification_data = [
            {
                'agent': self.agent,
                'title': 'Test Notification 1',
                'message': 'Message 1',
                'notification_type': 'generic',
                'related_object': self.contract
            },
            {
                'agent': self.agent,
                'title': 'Test Notification 2',
                'message': 'Message 2',
                'notification_type': 'generic'
            }
        ]
        
        results = batch_create_notifications(notification_data)
        
        self.assertEqual(results['immediate_notifications'], 2)
        self.assertEqual(results['batched_notifications'], 0)
        self.assertEqual(results['skipped_notifications'], 0)
        self.assertEqual(results['total_processed'], 2)
        
        # Check that notifications were created
        self.assertEqual(Notification.objects.filter(agent=self.agent).count(), 2)
    
    def test_batch_create_notifications_daily_batching(self):
        """Test batch notification creation with daily batching."""
        # Create preferences for daily batching
        NotificationPreference.objects.create(
            agent=self.agent,
            notification_frequency='daily',
            email_notifications=False
        )
        
        notification_data = [
            {
                'agent': self.agent,
                'title': 'Test Notification 1',
                'message': 'Message 1',
                'notification_type': 'generic',
                'related_object': self.contract
            }
        ]
        
        with patch('user_notifications.services.create_batched_notification') as mock_batch:
            mock_batch.return_value = MagicMock()
            
            results = batch_create_notifications(notification_data)
            
            self.assertEqual(results['immediate_notifications'], 0)
            self.assertEqual(results['batched_notifications'], 1)
            self.assertEqual(results['skipped_notifications'], 0)
            
            mock_batch.assert_called_once()


class NotificationLogTest(TestCase):
    """Test cases for NotificationLog model."""
    
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
    
    def test_log_notification(self):
        """Test logging a notification."""
        log_entry = NotificationLog.log_notification(
            agent=self.agent,
            notification_type='generic',
            related_object=self.contract
        )
        
        self.assertIsInstance(log_entry, NotificationLog)
        self.assertEqual(log_entry.agent, self.agent)
        self.assertEqual(log_entry.notification_type, 'generic')
        self.assertEqual(log_entry.content_type, ContentType.objects.get_for_model(Contract))
        self.assertEqual(log_entry.object_id, self.contract.pk)
        self.assertEqual(log_entry.created_date, timezone.now().date())
    
    def test_has_recent_notification_true(self):
        """Test checking for recent notification when one exists."""
        # Create a log entry
        NotificationLog.log_notification(
            agent=self.agent,
            notification_type='generic',
            related_object=self.contract
        )
        
        has_recent = NotificationLog.has_recent_notification(
            agent=self.agent,
            notification_type='generic',
            related_object=self.contract,
            days_threshold=1
        )
        
        self.assertTrue(has_recent)
    
    def test_has_recent_notification_false(self):
        """Test checking for recent notification when none exists."""
        has_recent = NotificationLog.has_recent_notification(
            agent=self.agent,
            notification_type='generic',
            related_object=self.contract,
            days_threshold=1
        )
        
        self.assertFalse(has_recent)
    
    def test_has_recent_notification_expired(self):
        """Test checking for recent notification when log entry is too old."""
        # Create a log entry with old date
        log_entry = NotificationLog.objects.create(
            agent=self.agent,
            notification_type='generic',
            content_type=ContentType.objects.get_for_model(Contract),
            object_id=self.contract.pk,
            created_date=timezone.now().date() - timedelta(days=5)
        )
        
        has_recent = NotificationLog.has_recent_notification(
            agent=self.agent,
            notification_type='generic',
            related_object=self.contract,
            days_threshold=1
        )
        
        self.assertFalse(has_recent)
    
    def test_has_recent_notification_no_related_object(self):
        """Test checking for recent notification with no related object."""
        has_recent = NotificationLog.has_recent_notification(
            agent=self.agent,
            notification_type='generic',
            related_object=None,
            days_threshold=1
        )
        
        self.assertFalse(has_recent)


class NotificationBatchTest(TestCase):
    """Test cases for NotificationBatch model."""
    
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
    
    def test_create_batch_notification_daily(self):
        """Test creating daily batch notification."""
        # Create preferences for daily batching
        NotificationPreference.objects.create(
            agent=self.agent,
            notification_frequency='daily',
            email_notifications=False
        )
        
        batch = NotificationBatch.create_batch_notification(
            agent=self.agent,
            title='Test Batch Notification',
            message='This is a batch notification',
            notification_type='generic',
            related_object=self.contract
        )
        
        self.assertIsInstance(batch, NotificationBatch)
        self.assertEqual(batch.agent, self.agent)
        self.assertEqual(batch.batch_type, 'daily')
        self.assertEqual(batch.title, 'Test Batch Notification')
        self.assertEqual(batch.related_object, self.contract)
        self.assertFalse(batch.processed)
        
        # Check that scheduled_for is set to next day at 9 AM
        expected_time = timezone.now().replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=1)
        self.assertEqual(batch.scheduled_for.date(), expected_time.date())
        self.assertEqual(batch.scheduled_for.hour, 9)
    
    def test_create_batch_notification_weekly(self):
        """Test creating weekly batch notification."""
        # Create preferences for weekly batching
        NotificationPreference.objects.create(
            agent=self.agent,
            notification_frequency='weekly',
            email_notifications=False
        )
        
        batch = NotificationBatch.create_batch_notification(
            agent=self.agent,
            title='Test Batch Notification',
            message='This is a batch notification',
            notification_type='generic',
            related_object=self.contract
        )
        
        self.assertIsInstance(batch, NotificationBatch)
        self.assertEqual(batch.batch_type, 'weekly')
        self.assertEqual(batch.scheduled_for.hour, 9)
        self.assertEqual(batch.scheduled_for.weekday(), 0)  # Monday
    
    def test_create_batch_notification_immediate(self):
        """Test that immediate delivery returns None for batching."""
        # Create preferences for immediate delivery
        NotificationPreference.objects.create(
            agent=self.agent,
            notification_frequency='immediately',
            email_notifications=False
        )
        
        batch = NotificationBatch.create_batch_notification(
            agent=self.agent,
            title='Test Batch Notification',
            message='This is a batch notification',
            notification_type='generic',
            related_object=self.contract
        )
        
        self.assertIsNone(batch)
    
    def test_get_ready_batches(self):
        """Test getting batches that are ready for processing."""
        # Create a batch scheduled for the past
        past_batch = NotificationBatch.objects.create(
            agent=self.agent,
            batch_type='daily',
            title='Past Batch',
            message='Past batch message',
            notification_type='generic',
            scheduled_for=timezone.now() - timedelta(hours=1),
            processed=False
        )
        
        # Create a batch scheduled for the future
        future_batch = NotificationBatch.objects.create(
            agent=self.agent,
            batch_type='daily',
            title='Future Batch',
            message='Future batch message',
            notification_type='generic',
            scheduled_for=timezone.now() + timedelta(hours=1),
            processed=False
        )
        
        # Create a processed batch
        processed_batch = NotificationBatch.objects.create(
            agent=self.agent,
            batch_type='daily',
            title='Processed Batch',
            message='Processed batch message',
            notification_type='generic',
            scheduled_for=timezone.now() - timedelta(hours=1),
            processed=True
        )
        
        ready_batches = NotificationBatch.get_ready_batches()
        
        self.assertEqual(ready_batches.count(), 1)
        self.assertEqual(ready_batches.first(), past_batch)
    
    def test_mark_as_processed(self):
        """Test marking batch as processed."""
        batch = NotificationBatch.objects.create(
            agent=self.agent,
            batch_type='daily',
            title='Test Batch',
            message='Test batch message',
            notification_type='generic',
            scheduled_for=timezone.now() - timedelta(hours=1),
            processed=False
        )
        
        self.assertFalse(batch.processed)
        self.assertIsNone(batch.processed_at)
        
        batch.mark_as_processed()
        
        self.assertTrue(batch.processed)
        self.assertIsNotNone(batch.processed_at)