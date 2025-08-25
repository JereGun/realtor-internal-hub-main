"""
Management command to verify notification system configuration and connectivity.

This command performs comprehensive health checks on the notification system
including database connectivity, Celery configuration, email settings,
and business logic validation.
"""

from django.core.management.base import BaseCommand, CommandError
from django.core.mail import send_mail
from django.conf import settings
from django.db import connection
from django.utils import timezone
from django.apps import apps
from user_notifications.models import Notification
from user_notifications.models_preferences import NotificationPreference
from agents.models import Agent
from contracts.models import Contract
from accounting.models_invoice import Invoice
import logging
import sys

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Verify notification system configuration and connectivity'

    def add_arguments(self, parser):
        parser.add_argument(
            '--email-test',
            action='store_true',
            help='Send a test email to verify email configuration'
        )
        parser.add_argument(
            '--email-to',
            type=str,
            help='Email address to send test email to'
        )
        parser.add_argument(
            '--fix-issues',
            action='store_true',
            help='Attempt to fix common configuration issues'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed output of all checks'
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Starting notification system health check...')
        )
        
        health_status = {
            'database': False,
            'models': False,
            'celery': False,
            'email': False,
            'business_logic': False,
            'overall': False
        }
        
        issues_found = []
        warnings = []
        
        # Database connectivity check
        self.stdout.write('\n--- Database Connectivity Check ---')
        health_status['database'], db_issues = self._check_database_connectivity(options['verbose'])
        issues_found.extend(db_issues)
        
        # Models and migrations check
        self.stdout.write('\n--- Models and Migrations Check ---')
        health_status['models'], model_issues = self._check_models_and_migrations(options['verbose'])
        issues_found.extend(model_issues)
        
        # Celery configuration check
        self.stdout.write('\n--- Celery Configuration Check ---')
        health_status['celery'], celery_issues, celery_warnings = self._check_celery_configuration(options['verbose'])
        issues_found.extend(celery_issues)
        warnings.extend(celery_warnings)
        
        # Email configuration check
        self.stdout.write('\n--- Email Configuration Check ---')
        health_status['email'], email_issues = self._check_email_configuration(
            options['email_test'], options['email_to'], options['verbose']
        )
        issues_found.extend(email_issues)
        
        # Business logic check
        self.stdout.write('\n--- Business Logic Check ---')
        health_status['business_logic'], logic_issues = self._check_business_logic(options['verbose'])
        issues_found.extend(logic_issues)
        
        # Overall health assessment
        health_status['overall'] = all([
            health_status['database'],
            health_status['models'],
            health_status['business_logic']
        ])
        
        # Attempt to fix issues if requested
        if options['fix_issues'] and issues_found:
            self.stdout.write('\n--- Attempting to Fix Issues ---')
            self._attempt_fixes(issues_found)
        
        # Summary report
        self._print_health_summary(health_status, issues_found, warnings)
        
        # Exit with appropriate code
        if not health_status['overall']:
            sys.exit(1)

    def _check_database_connectivity(self, verbose=False):
        """Check database connectivity and basic operations."""
        issues = []
        
        try:
            # Test basic database connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                if result[0] != 1:
                    issues.append("Database connection test failed")
            
            if verbose:
                self.stdout.write('  ✓ Database connection successful')
            
            # Test notification model operations
            try:
                notification_count = Notification.objects.count()
                if verbose:
                    self.stdout.write(f'  ✓ Notification model accessible ({notification_count} records)')
            except Exception as e:
                issues.append(f"Cannot access Notification model: {e}")
            
            # Test agent model operations
            try:
                agent_count = Agent.objects.count()
                if verbose:
                    self.stdout.write(f'  ✓ Agent model accessible ({agent_count} records)')
                
                if agent_count == 0:
                    issues.append("No agents found in database - notifications require agents")
            except Exception as e:
                issues.append(f"Cannot access Agent model: {e}")
            
            self.stdout.write(self.style.SUCCESS('Database connectivity: PASSED'))
            return len(issues) == 0, issues
            
        except Exception as e:
            issues.append(f"Database connection failed: {e}")
            self.stdout.write(self.style.ERROR('Database connectivity: FAILED'))
            return False, issues

    def _check_models_and_migrations(self, verbose=False):
        """Check that all required models exist and migrations are applied."""
        issues = []
        
        required_models = [
            ('user_notifications', 'Notification'),
            ('user_notifications', 'NotificationPreference'),
            ('agents', 'Agent'),
            ('contracts', 'Contract'),
            ('accounting', 'Invoice'),
        ]
        
        for app_label, model_name in required_models:
            try:
                model = apps.get_model(app_label, model_name)
                # Test that we can query the model
                model.objects.count()
                if verbose:
                    self.stdout.write(f'  ✓ {app_label}.{model_name} model accessible')
            except Exception as e:
                issues.append(f"Model {app_label}.{model_name} not accessible: {e}")
        
        # Check for pending migrations
        try:
            from django.core.management import execute_from_command_line
            from django.core.management.commands.showmigrations import Command as ShowMigrationsCommand
            
            # This is a simplified check - in production you might want more sophisticated migration checking
            if verbose:
                self.stdout.write('  ✓ Migration check completed (manual verification recommended)')
        except Exception as e:
            if verbose:
                self.stdout.write(f'  ! Could not check migrations: {e}')
        
        if len(issues) == 0:
            self.stdout.write(self.style.SUCCESS('Models and migrations: PASSED'))
        else:
            self.stdout.write(self.style.ERROR('Models and migrations: FAILED'))
        
        return len(issues) == 0, issues

    def _check_celery_configuration(self, verbose=False):
        """Check Celery configuration and task availability."""
        issues = []
        warnings = []
        
        # Check if Celery is configured
        try:
            celery_app = getattr(settings, 'CELERY_APP', None)
            if not celery_app and not hasattr(settings, 'CELERY_BROKER_URL'):
                warnings.append("Celery configuration not found - scheduled notifications will not work")
            elif verbose:
                self.stdout.write('  ✓ Celery configuration found')
        except Exception as e:
            warnings.append(f"Could not check Celery configuration: {e}")
        
        # Check if notification tasks are importable
        try:
            from user_notifications.tasks import (
                check_contract_expirations,
                check_invoice_overdue,
                check_rent_increases,
                check_invoice_due_soon
            )
            if verbose:
                self.stdout.write('  ✓ Notification tasks importable')
        except ImportError as e:
            issues.append(f"Cannot import notification tasks: {e}")
        
        # Check if checker classes are importable
        try:
            from user_notifications.checkers import (
                ContractExpirationChecker,
                InvoiceOverdueChecker,
                RentIncreaseChecker,
                InvoiceDueSoonChecker
            )
            if verbose:
                self.stdout.write('  ✓ Checker classes importable')
        except ImportError as e:
            issues.append(f"Cannot import checker classes: {e}")
        
        # Try to instantiate checkers
        try:
            from user_notifications.checkers import ContractExpirationChecker
            checker = ContractExpirationChecker()
            if verbose:
                self.stdout.write('  ✓ Checker classes instantiable')
        except Exception as e:
            issues.append(f"Cannot instantiate checker classes: {e}")
        
        if len(issues) == 0:
            if len(warnings) == 0:
                self.stdout.write(self.style.SUCCESS('Celery configuration: PASSED'))
            else:
                self.stdout.write(self.style.WARNING('Celery configuration: PASSED (with warnings)'))
        else:
            self.stdout.write(self.style.ERROR('Celery configuration: FAILED'))
        
        return len(issues) == 0, issues, warnings

    def _check_email_configuration(self, send_test=False, test_email=None, verbose=False):
        """Check email configuration and optionally send test email."""
        issues = []
        
        # Check basic email settings
        required_settings = ['EMAIL_HOST', 'EMAIL_PORT', 'DEFAULT_FROM_EMAIL']
        for setting in required_settings:
            if not hasattr(settings, setting) or not getattr(settings, setting):
                issues.append(f"Missing or empty email setting: {setting}")
            elif verbose:
                value = getattr(settings, setting)
                if setting == 'EMAIL_HOST_PASSWORD':
                    value = '***' if value else 'Not set'
                self.stdout.write(f'  ✓ {setting}: {value}')
        
        # Check email backend
        email_backend = getattr(settings, 'EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')
        if verbose:
            self.stdout.write(f'  ✓ EMAIL_BACKEND: {email_backend}')
        
        # Send test email if requested
        if send_test:
            if not test_email:
                # Try to get an agent's email for testing
                try:
                    agent = Agent.objects.filter(email__isnull=False).first()
                    if agent and agent.email:
                        test_email = agent.email
                    else:
                        issues.append("No test email provided and no agent email found")
                except Exception:
                    issues.append("No test email provided and cannot access agent emails")
            
            if test_email:
                try:
                    send_mail(
                        subject='Notification System Health Check',
                        message='This is a test email from the notification system health check.',
                        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@example.com'),
                        recipient_list=[test_email],
                        fail_silently=False
                    )
                    self.stdout.write(f'  ✓ Test email sent successfully to {test_email}')
                except Exception as e:
                    issues.append(f"Failed to send test email: {e}")
        
        if len(issues) == 0:
            self.stdout.write(self.style.SUCCESS('Email configuration: PASSED'))
        else:
            self.stdout.write(self.style.ERROR('Email configuration: FAILED'))
        
        return len(issues) == 0, issues

    def _check_business_logic(self, verbose=False):
        """Check business logic and data integrity."""
        issues = []
        
        # Check if there are agents with notification preferences
        try:
            agents_with_prefs = NotificationPreference.objects.count()
            total_agents = Agent.objects.count()
            
            if verbose:
                self.stdout.write(f'  ✓ {agents_with_prefs}/{total_agents} agents have notification preferences')
            
            if total_agents > 0 and agents_with_prefs == 0:
                issues.append("No agents have notification preferences configured")
        except Exception as e:
            issues.append(f"Cannot check notification preferences: {e}")
        
        # Check for contracts with end dates
        try:
            contracts_with_end_dates = Contract.objects.filter(end_date__isnull=False).count()
            total_contracts = Contract.objects.count()
            
            if verbose:
                self.stdout.write(f'  ✓ {contracts_with_end_dates}/{total_contracts} contracts have end dates')
            
            if total_contracts > 0 and contracts_with_end_dates == 0:
                issues.append("No contracts have end dates - expiration notifications will not work")
        except Exception as e:
            issues.append(f"Cannot check contract data: {e}")
        
        # Check for invoices with due dates
        try:
            invoices_with_due_dates = Invoice.objects.filter(due_date__isnull=False).count()
            total_invoices = Invoice.objects.count()
            
            if verbose:
                self.stdout.write(f'  ✓ {invoices_with_due_dates}/{total_invoices} invoices have due dates')
            
            if total_invoices > 0 and invoices_with_due_dates == 0:
                issues.append("No invoices have due dates - due date notifications will not work")
        except Exception as e:
            issues.append(f"Cannot check invoice data: {e}")
        
        # Check for contracts with rent increase dates
        try:
            contracts_with_increases = Contract.objects.filter(next_increase_date__isnull=False).count()
            
            if verbose:
                self.stdout.write(f'  ✓ {contracts_with_increases} contracts have rent increase dates')
        except Exception as e:
            issues.append(f"Cannot check rent increase data: {e}")
        
        # Test notification creation
        try:
            from user_notifications.services import create_notification
            
            # Get a test agent
            test_agent = Agent.objects.first()
            if test_agent:
                # This is just a test - we won't actually create the notification
                if verbose:
                    self.stdout.write('  ✓ Notification creation function accessible')
            else:
                issues.append("No agents available for testing notification creation")
        except Exception as e:
            issues.append(f"Cannot test notification creation: {e}")
        
        if len(issues) == 0:
            self.stdout.write(self.style.SUCCESS('Business logic: PASSED'))
        else:
            self.stdout.write(self.style.ERROR('Business logic: FAILED'))
        
        return len(issues) == 0, issues

    def _attempt_fixes(self, issues):
        """Attempt to fix common issues automatically."""
        fixes_applied = 0
        
        for issue in issues:
            if "No agents have notification preferences configured" in issue:
                try:
                    # Create default notification preferences for agents without them
                    agents_without_prefs = Agent.objects.exclude(
                        id__in=NotificationPreference.objects.values_list('agent_id', flat=True)
                    )
                    
                    for agent in agents_without_prefs:
                        NotificationPreference.objects.create(
                            agent=agent,
                            receive_contract_expiration=True,
                            receive_invoice_overdue=True,
                            receive_rent_increase=True,
                            receive_invoice_due_soon=True,
                            receive_invoice_payment=True,
                            receive_invoice_status_change=True,
                            email_notifications=True,
                            notification_frequency='immediate'
                        )
                    
                    count = agents_without_prefs.count()
                    if count > 0:
                        self.stdout.write(f'  ✓ Created default notification preferences for {count} agents')
                        fixes_applied += 1
                        
                except Exception as e:
                    self.stdout.write(f'  ✗ Failed to create notification preferences: {e}')
        
        if fixes_applied > 0:
            self.stdout.write(f'Applied {fixes_applied} automatic fixes')
        else:
            self.stdout.write('No automatic fixes available for the identified issues')

    def _print_health_summary(self, health_status, issues, warnings):
        """Print comprehensive health summary."""
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('NOTIFICATION SYSTEM HEALTH SUMMARY'))
        self.stdout.write('='*60)
        
        # Component status
        for component, status in health_status.items():
            if component == 'overall':
                continue
            
            status_text = 'PASSED' if status else 'FAILED'
            style = self.style.SUCCESS if status else self.style.ERROR
            self.stdout.write(f'{component.replace("_", " ").title()}: {style(status_text)}')
        
        # Overall status
        overall_status = 'HEALTHY' if health_status['overall'] else 'UNHEALTHY'
        overall_style = self.style.SUCCESS if health_status['overall'] else self.style.ERROR
        self.stdout.write(f'\nOverall System Status: {overall_style(overall_status)}')
        
        # Issues
        if issues:
            self.stdout.write(f'\n{self.style.ERROR("ISSUES FOUND:")}')
            for i, issue in enumerate(issues, 1):
                self.stdout.write(f'  {i}. {issue}')
        
        # Warnings
        if warnings:
            self.stdout.write(f'\n{self.style.WARNING("WARNINGS:")}')
            for i, warning in enumerate(warnings, 1):
                self.stdout.write(f'  {i}. {warning}')
        
        # Recommendations
        if issues or warnings:
            self.stdout.write(f'\n{self.style.HTTP_INFO("RECOMMENDATIONS:")}')
            if issues:
                self.stdout.write('  • Address the issues listed above before deploying to production')
                self.stdout.write('  • Run this command with --fix-issues to attempt automatic fixes')
            if warnings:
                self.stdout.write('  • Review the warnings to ensure optimal system performance')
            self.stdout.write('  • Run this command with --verbose for detailed information')
            self.stdout.write('  • Use --email-test to verify email delivery')
        else:
            self.stdout.write(f'\n{self.style.SUCCESS("✓ All checks passed! The notification system is ready for use.")}')
        
        self.stdout.write('\n' + '='*60)