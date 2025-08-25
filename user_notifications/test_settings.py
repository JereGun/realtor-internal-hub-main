"""
Test settings for notification system tests.

This module provides test-specific settings and configurations
for running notification system tests effectively.
"""

from django.test import override_settings
from django.conf import settings

# Test database configuration
TEST_DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
        'TEST': {
            'NAME': ':memory:',
        },
    }
}

# Test email backend configuration
TEST_EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# Test Celery configuration
TEST_CELERY_SETTINGS = {
    'CELERY_TASK_ALWAYS_EAGER': True,
    'CELERY_TASK_EAGER_PROPAGATES': True,
    'CELERY_BROKER_URL': 'memory://',
    'CELERY_RESULT_BACKEND': 'cache+memory://',
}

# Test logging configuration
TEST_LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'user_notifications': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}

def get_test_settings():
    """
    Get test-specific Django settings.
    
    Returns:
        dict: Dictionary of test settings
    """
    return {
        'DATABASES': TEST_DATABASES,
        'EMAIL_BACKEND': TEST_EMAIL_BACKEND,
        'LOGGING': TEST_LOGGING,
        **TEST_CELERY_SETTINGS
    }


class NotificationTestMixin:
    """
    Mixin class for notification system tests.
    
    Provides common setup and utility methods for notification tests.
    """
    
    @classmethod
    def setUpClass(cls):
        """Set up test class with proper settings."""
        super().setUpClass()
        
        # Apply test settings
        test_settings = get_test_settings()
        for key, value in test_settings.items():
            setattr(settings, key, value)
    
    def setUp(self):
        """Set up individual test."""
        super().setUp()
        
        # Clear any existing notifications and logs
        from user_notifications.models import Notification, NotificationLog, NotificationBatch
        Notification.objects.all().delete()
        NotificationLog.objects.all().delete()
        NotificationBatch.objects.all().delete()
        
        # Clear email outbox if using locmem backend
        from django.core import mail
        mail.outbox = []
    
    def create_test_agent(self, username='test_agent', email='test@example.com'):
        """
        Create a test agent for use in tests.
        
        Args:
            username (str): Agent username
            email (str): Agent email
            
        Returns:
            Agent: Created agent instance
        """
        from agents.models import Agent
        
        return Agent.objects.create(
            username=username,
            email=email,
            first_name='Test',
            last_name='Agent'
        )
    
    def create_test_customer(self, username='test_customer', email='customer@example.com'):
        """
        Create a test customer for use in tests.
        
        Args:
            username (str): Customer username
            email (str): Customer email
            
        Returns:
            Customer: Created customer instance
        """
        from customers.models import Customer
        
        return Customer.objects.create(
            username=username,
            email=email,
            first_name='Test',
            last_name='Customer'
        )
    
    def create_test_property(self, title='Test Property', address='123 Test St'):
        """
        Create a test property for use in tests.
        
        Args:
            title (str): Property title
            address (str): Property address
            
        Returns:
            Property: Created property instance
        """
        from properties.models import Property
        
        return Property.objects.create(
            title=title,
            address=address,
            property_type='apartment',
            status='available'
        )
    
    def create_test_contract(self, property_obj, customer, agent, **kwargs):
        """
        Create a test contract for use in tests.
        
        Args:
            property_obj (Property): Property for the contract
            customer (Customer): Customer for the contract
            agent (Agent): Agent for the contract
            **kwargs: Additional contract fields
            
        Returns:
            Contract: Created contract instance
        """
        from contracts.models import Contract
        from decimal import Decimal
        from django.utils import timezone
        from datetime import timedelta
        
        defaults = {
            'amount': Decimal('1000.00'),
            'start_date': timezone.now().date() - timedelta(days=365),
            'end_date': timezone.now().date() + timedelta(days=365),
            'status': Contract.STATUS_ACTIVE
        }
        defaults.update(kwargs)
        
        return Contract.objects.create(
            property=property_obj,
            customer=customer,
            agent=agent,
            **defaults
        )
    
    def create_test_invoice(self, customer, contract=None, **kwargs):
        """
        Create a test invoice for use in tests.
        
        Args:
            customer (Customer): Customer for the invoice
            contract (Contract, optional): Contract for the invoice
            **kwargs: Additional invoice fields
            
        Returns:
            Invoice: Created invoice instance
        """
        from accounting.models_invoice import Invoice
        from decimal import Decimal
        from django.utils import timezone
        
        defaults = {
            'number': f'INV-{timezone.now().strftime("%Y%m%d%H%M%S")}',
            'amount': Decimal('1000.00'),
            'due_date': timezone.now().date(),
            'status': 'validated'
        }
        defaults.update(kwargs)
        
        return Invoice.objects.create(
            customer=customer,
            contract=contract,
            **defaults
        )
    
    def create_test_preferences(self, agent, **kwargs):
        """
        Create test notification preferences for an agent.
        
        Args:
            agent (Agent): Agent for the preferences
            **kwargs: Preference field overrides
            
        Returns:
            NotificationPreference: Created preferences instance
        """
        from user_notifications.models_preferences import NotificationPreference
        
        defaults = {
            'receive_invoice_due_soon': True,
            'receive_invoice_overdue': True,
            'receive_invoice_payment': True,
            'receive_invoice_status_change': True,
            'receive_contract_expiration': True,
            'receive_rent_increase': True,
            'notification_frequency': 'immediately',
            'email_notifications': False
        }
        defaults.update(kwargs)
        
        return NotificationPreference.objects.create(
            agent=agent,
            **defaults
        )
    
    def assert_notification_created(self, agent, notification_type, count=1):
        """
        Assert that notifications of a specific type were created for an agent.
        
        Args:
            agent (Agent): Agent to check notifications for
            notification_type (str): Type of notification to check
            count (int): Expected number of notifications
        """
        from user_notifications.models import Notification
        
        notifications = Notification.objects.filter(
            agent=agent,
            notification_type=notification_type
        )
        
        self.assertEqual(
            notifications.count(),
            count,
            f"Expected {count} {notification_type} notifications for {agent}, found {notifications.count()}"
        )
        
        return notifications
    
    def assert_email_sent(self, recipient_email, subject_contains=None, count=1):
        """
        Assert that emails were sent to a specific recipient.
        
        Args:
            recipient_email (str): Email address to check
            subject_contains (str, optional): Text that should be in the subject
            count (int): Expected number of emails
        """
        from django.core import mail
        
        matching_emails = [
            email for email in mail.outbox
            if recipient_email in email.to
        ]
        
        self.assertEqual(
            len(matching_emails),
            count,
            f"Expected {count} emails to {recipient_email}, found {len(matching_emails)}"
        )
        
        if subject_contains and matching_emails:
            for email in matching_emails:
                self.assertIn(
                    subject_contains,
                    email.subject,
                    f"Expected '{subject_contains}' in email subject '{email.subject}'"
                )
        
        return matching_emails
    
    def assert_notification_log_created(self, agent, notification_type, related_object=None):
        """
        Assert that a notification log entry was created.
        
        Args:
            agent (Agent): Agent to check log for
            notification_type (str): Type of notification
            related_object (Model, optional): Related object
        """
        from user_notifications.models import NotificationLog
        from django.contrib.contenttypes.models import ContentType
        
        filters = {
            'agent': agent,
            'notification_type': notification_type
        }
        
        if related_object:
            filters.update({
                'content_type': ContentType.objects.get_for_model(related_object),
                'object_id': related_object.pk
            })
        
        log_exists = NotificationLog.objects.filter(**filters).exists()
        self.assertTrue(
            log_exists,
            f"Expected notification log for {agent} - {notification_type}"
        )
    
    def assert_batch_notification_created(self, agent, batch_type, notification_type):
        """
        Assert that a batch notification was created.
        
        Args:
            agent (Agent): Agent to check batch for
            batch_type (str): Type of batch ('daily' or 'weekly')
            notification_type (str): Type of notification
        """
        from user_notifications.models import NotificationBatch
        
        batch_exists = NotificationBatch.objects.filter(
            agent=agent,
            batch_type=batch_type,
            notification_type=notification_type,
            processed=False
        ).exists()
        
        self.assertTrue(
            batch_exists,
            f"Expected {batch_type} batch notification for {agent} - {notification_type}"
        )


# Test decorators for common test configurations
def with_test_settings(test_func):
    """
    Decorator to apply test settings to a test function.
    
    Args:
        test_func: Test function to decorate
        
    Returns:
        Decorated test function
    """
    test_settings = get_test_settings()
    
    for key, value in test_settings.items():
        test_func = override_settings(**{key: value})(test_func)
    
    return test_func


def with_email_backend(test_func):
    """
    Decorator to apply test email backend to a test function.
    
    Args:
        test_func: Test function to decorate
        
    Returns:
        Decorated test function
    """
    return override_settings(EMAIL_BACKEND=TEST_EMAIL_BACKEND)(test_func)


def with_celery_eager(test_func):
    """
    Decorator to apply eager Celery execution to a test function.
    
    Args:
        test_func: Test function to decorate
        
    Returns:
        Decorated test function
    """
    return override_settings(**TEST_CELERY_SETTINGS)(test_func)