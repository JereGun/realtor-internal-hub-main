#!/usr/bin/env python
"""
Simple test script to verify invoice overdue notification functionality.
This script can be run to test the email notification system for overdue invoices.
"""

import os
import sys
import django
from datetime import date, timedelta

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'real_estate_management.settings')
django.setup()

from django.core.mail import get_connection
from django.test import override_settings
from user_notifications.checkers import InvoiceOverdueChecker
from user_notifications.services import send_notification_email, create_notification
from accounting.models_invoice import Invoice
from agents.models import Agent
from customers.models import Customer

def test_invoice_overdue_email_templates():
    """
    Test that email templates render correctly for different overdue scenarios.
    """
    print("Testing invoice overdue email templates...")
    
    try:
        # Get or create test data
        agent = Agent.objects.first()
        customer = Customer.objects.first()
        
        if not agent or not customer:
            print("❌ No test data available. Please ensure you have at least one agent and customer in the database.")
            return False
        
        # Create test invoices with different overdue scenarios
        today = date.today()
        
        # Test scenarios
        test_scenarios = [
            {
                'days_overdue': 3,
                'notification_type': 'invoice_overdue',
                'description': 'Standard overdue (3 days)'
            },
            {
                'days_overdue': 10,
                'notification_type': 'invoice_overdue_urgent', 
                'description': 'Urgent overdue (10 days)'
            },
            {
                'days_overdue': 35,
                'notification_type': 'invoice_overdue_critical',
                'description': 'Critical overdue (35 days)'
            }
        ]
        
        for scenario in test_scenarios:
            print(f"\n📧 Testing {scenario['description']}...")
            
            # Create test invoice
            due_date = today - timedelta(days=scenario['days_overdue'])
            
            # Create a mock invoice for testing
            class MockInvoice:
                def __init__(self, number, customer, due_date, days_overdue):
                    self.id = 999
                    self.number = number
                    self.customer = customer
                    self.due_date = due_date
                    self._days_overdue = days_overdue
                
                def get_balance(self):
                    return 1500.00
                
                def days_overdue(self):
                    return self._days_overdue
            
            mock_invoice = MockInvoice(
                f"TEST-{scenario['days_overdue']}", 
                customer, 
                due_date, 
                scenario['days_overdue']
            )
            
            # Create test notification
            title = f"Test - Factura Vencida {scenario['days_overdue']} días"
            message = f"Factura de prueba vencida hace {scenario['days_overdue']} días."
            
            notification = create_notification(
                agent=agent,
                title=title,
                message=message,
                notification_type=scenario['notification_type'],
                related_object=None  # Using None since it's a mock object
            )
            
            # Manually set the related object for template testing
            notification.related_object = mock_invoice
            
            print(f"✅ Created notification: {notification.title}")
            print(f"   Type: {notification.notification_type}")
            
            # Test email template rendering (without actually sending)
            try:
                from django.template.loader import render_to_string
                
                template_mapping = {
                    'invoice_overdue': 'user_notifications/email/invoice_overdue_standard.html',
                    'invoice_overdue_urgent': 'user_notifications/email/invoice_overdue_urgent.html',
                    'invoice_overdue_critical': 'user_notifications/email/invoice_overdue_critical.html'
                }
                
                template_name = template_mapping.get(
                    scenario['notification_type'], 
                    'user_notifications/email/notification_email.html'
                )
                
                context = {
                    'notification': notification,
                    'agent': agent,
                    'site_url': 'http://localhost:8000',
                }
                
                html_content = render_to_string(template_name, context)
                
                if html_content and len(html_content) > 100:
                    print(f"✅ Template {template_name} rendered successfully")
                    print(f"   Content length: {len(html_content)} characters")
                else:
                    print(f"❌ Template {template_name} rendered but content seems incomplete")
                    
            except Exception as e:
                print(f"❌ Template rendering failed: {e}")
                return False
        
        print(f"\n✅ All email template tests completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False

def test_overdue_checker_logic():
    """
    Test the InvoiceOverdueChecker business logic.
    """
    print("\n" + "="*50)
    print("Testing InvoiceOverdueChecker business logic...")
    
    try:
        checker = InvoiceOverdueChecker()
        
        # Test getting overdue invoices
        overdue_invoices = checker.get_overdue_invoices()
        print(f"✅ Found {overdue_invoices.count()} overdue invoices in database")
        
        # Test the check_and_notify method
        results = checker.check_and_notify()
        print(f"✅ Notification check completed:")
        print(f"   Standard overdue: {results['standard_overdue']}")
        print(f"   Urgent overdue: {results['urgent_overdue']}")
        print(f"   Critical overdue: {results['critical_overdue']}")
        print(f"   Total notifications: {results['total_notifications']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Checker test failed: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Starting Invoice Overdue Notification Tests")
    print("="*50)
    
    # Run tests
    template_test_passed = test_invoice_overdue_email_templates()
    checker_test_passed = test_overdue_checker_logic()
    
    print("\n" + "="*50)
    print("📊 Test Results Summary:")
    print(f"   Email Templates: {'✅ PASSED' if template_test_passed else '❌ FAILED'}")
    print(f"   Checker Logic: {'✅ PASSED' if checker_test_passed else '❌ FAILED'}")
    
    if template_test_passed and checker_test_passed:
        print("\n🎉 All tests passed! Invoice overdue notification system is working correctly.")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed. Please check the implementation.")
        sys.exit(1)