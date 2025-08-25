"""
Management command to manually trigger all notification checks.

This command allows administrators to manually run all notification checking
tasks without waiting for the scheduled Celery tasks. Useful for testing,
debugging, and immediate notification processing.
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db import transaction
from user_notifications.checkers import (
    ContractExpirationChecker,
    InvoiceOverdueChecker,
    RentIncreaseChecker,
    InvoiceDueSoonChecker
)
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Manually trigger all notification checks'

    def add_arguments(self, parser):
        parser.add_argument(
            '--type',
            type=str,
            choices=['contract', 'invoice_overdue', 'rent_increase', 'invoice_due'],
            help='Run only specific notification type check'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what notifications would be created without actually creating them'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed output of the checking process'
        )

    def handle(self, *args, **options):
        start_time = timezone.now()
        
        self.stdout.write(
            self.style.SUCCESS(f'Starting notification checks at {start_time.strftime("%Y-%m-%d %H:%M:%S")}')
        )
        
        total_results = {
            'contract_expiration': {},
            'invoice_overdue': {},
            'rent_increase': {},
            'invoice_due_soon': {},
            'total_notifications': 0
        }
        
        try:
            # Contract expiration notifications
            if not options['type'] or options['type'] == 'contract':
                self.stdout.write('\n--- Checking Contract Expirations ---')
                total_results['contract_expiration'] = self._check_contract_expirations(
                    options['dry_run'], options['verbose']
                )
            
            # Invoice overdue notifications
            if not options['type'] or options['type'] == 'invoice_overdue':
                self.stdout.write('\n--- Checking Overdue Invoices ---')
                total_results['invoice_overdue'] = self._check_invoice_overdue(
                    options['dry_run'], options['verbose']
                )
            
            # Rent increase notifications
            if not options['type'] or options['type'] == 'rent_increase':
                self.stdout.write('\n--- Checking Rent Increases ---')
                total_results['rent_increase'] = self._check_rent_increases(
                    options['dry_run'], options['verbose']
                )
            
            # Invoice due soon notifications
            if not options['type'] or options['type'] == 'invoice_due':
                self.stdout.write('\n--- Checking Invoices Due Soon ---')
                total_results['invoice_due_soon'] = self._check_invoice_due_soon(
                    options['dry_run'], options['verbose']
                )
            
            # Calculate total notifications
            for check_type, results in total_results.items():
                if isinstance(results, dict) and 'total_notifications' in results:
                    total_results['total_notifications'] += results['total_notifications']
            
            # Summary
            end_time = timezone.now()
            duration = end_time - start_time
            
            self.stdout.write('\n' + '='*50)
            self.stdout.write(self.style.SUCCESS('NOTIFICATION CHECK SUMMARY'))
            self.stdout.write('='*50)
            
            for check_type, results in total_results.items():
                if check_type != 'total_notifications' and results:
                    self.stdout.write(f'\n{check_type.replace("_", " ").title()}:')
                    if isinstance(results, dict):
                        for key, value in results.items():
                            if key != 'total_notifications':
                                self.stdout.write(f'  {key.replace("_", " ").title()}: {value}')
            
            self.stdout.write(f'\nTotal Notifications Created: {total_results["total_notifications"]}')
            self.stdout.write(f'Execution Time: {duration.total_seconds():.2f} seconds')
            
            if options['dry_run']:
                self.stdout.write(
                    self.style.WARNING('\nDRY RUN MODE - No notifications were actually created')
                )
            
            self.stdout.write(
                self.style.SUCCESS(f'\nNotification checks completed successfully at {end_time.strftime("%Y-%m-%d %H:%M:%S")}')
            )
            
        except Exception as e:
            logger.error(f"Error during notification checks: {e}")
            raise CommandError(f'Notification check failed: {e}')

    def _check_contract_expirations(self, dry_run=False, verbose=False):
        """Check for contract expiration notifications."""
        try:
            checker = ContractExpirationChecker()
            
            if dry_run:
                # In dry run mode, just count what would be processed
                expired_contracts = checker.get_expired_contracts()
                urgent_contracts = checker.get_expiring_contracts(7)
                advance_contracts = checker.get_expiring_contracts(30).exclude(
                    end_date__lte=timezone.now().date() + timezone.timedelta(days=7)
                )
                
                results = {
                    'expired_notifications': expired_contracts.count(),
                    'urgent_notifications': urgent_contracts.count(),
                    'advance_notifications': advance_contracts.count(),
                    'total_notifications': expired_contracts.count() + urgent_contracts.count() + advance_contracts.count()
                }
                
                if verbose:
                    self.stdout.write(f'  Would create {results["expired_notifications"]} expired contract notifications')
                    self.stdout.write(f'  Would create {results["urgent_notifications"]} urgent contract notifications')
                    self.stdout.write(f'  Would create {results["advance_notifications"]} advance contract notifications')
            else:
                with transaction.atomic():
                    results = checker.check_and_notify()
                
                if verbose:
                    self.stdout.write(f'  Created {results["expired_notifications"]} expired contract notifications')
                    self.stdout.write(f'  Created {results["urgent_notifications"]} urgent contract notifications')
                    self.stdout.write(f'  Created {results["advance_notifications"]} advance contract notifications')
            
            self.stdout.write(f'Contract expiration check: {results["total_notifications"]} notifications')
            return results
            
        except Exception as e:
            logger.error(f"Error in contract expiration check: {e}")
            self.stdout.write(
                self.style.ERROR(f'Contract expiration check failed: {e}')
            )
            return {'total_notifications': 0}

    def _check_invoice_overdue(self, dry_run=False, verbose=False):
        """Check for overdue invoice notifications."""
        try:
            checker = InvoiceOverdueChecker()
            
            if dry_run:
                # In dry run mode, just count what would be processed
                overdue_invoices = checker.get_overdue_invoices()
                count = 0
                for invoice in overdue_invoices:
                    if invoice.get_balance() > 0:
                        count += 1
                
                results = {
                    'total_notifications': count,
                    'overdue_invoices_found': count
                }
                
                if verbose:
                    self.stdout.write(f'  Would create {count} overdue invoice notifications')
            else:
                with transaction.atomic():
                    results = checker.check_and_notify()
                
                if verbose:
                    self.stdout.write(f'  Created {results["standard_overdue"]} standard overdue notifications')
                    self.stdout.write(f'  Created {results["urgent_overdue"]} urgent overdue notifications')
                    self.stdout.write(f'  Created {results["critical_overdue"]} critical overdue notifications')
            
            self.stdout.write(f'Invoice overdue check: {results["total_notifications"]} notifications')
            return results
            
        except Exception as e:
            logger.error(f"Error in invoice overdue check: {e}")
            self.stdout.write(
                self.style.ERROR(f'Invoice overdue check failed: {e}')
            )
            return {'total_notifications': 0}

    def _check_rent_increases(self, dry_run=False, verbose=False):
        """Check for rent increase notifications."""
        try:
            checker = RentIncreaseChecker()
            
            if dry_run:
                # In dry run mode, just count what would be processed
                overdue_contracts = checker.get_overdue_increases()
                upcoming_contracts = checker.get_contracts_with_increases_due(7).filter(
                    next_increase_date__gte=timezone.now().date()
                )
                
                results = {
                    'overdue_increases': overdue_contracts.count(),
                    'upcoming_increases': upcoming_contracts.count(),
                    'total_notifications': overdue_contracts.count() + upcoming_contracts.count()
                }
                
                if verbose:
                    self.stdout.write(f'  Would create {results["overdue_increases"]} overdue increase notifications')
                    self.stdout.write(f'  Would create {results["upcoming_increases"]} upcoming increase notifications')
            else:
                with transaction.atomic():
                    results = checker.check_and_notify()
                
                if verbose:
                    self.stdout.write(f'  Created {results["overdue_increases"]} overdue increase notifications')
                    self.stdout.write(f'  Created {results["upcoming_increases"]} upcoming increase notifications')
                    self.stdout.write(f'  Processed {results["contracts_processed"]} contracts')
            
            self.stdout.write(f'Rent increase check: {results["total_notifications"]} notifications')
            return results
            
        except Exception as e:
            logger.error(f"Error in rent increase check: {e}")
            self.stdout.write(
                self.style.ERROR(f'Rent increase check failed: {e}')
            )
            return {'total_notifications': 0}

    def _check_invoice_due_soon(self, dry_run=False, verbose=False):
        """Check for invoice due soon notifications."""
        try:
            checker = InvoiceDueSoonChecker()
            
            if dry_run:
                # In dry run mode, just count what would be processed
                due_soon_7 = checker.get_due_soon_invoices(7)
                due_soon_3 = checker.get_due_soon_invoices(3)
                
                results = {
                    'due_soon_7_days': due_soon_7.count(),
                    'due_soon_3_days': due_soon_3.count(),
                    'total_notifications': due_soon_7.count() + due_soon_3.count()
                }
                
                if verbose:
                    self.stdout.write(f'  Would create {results["due_soon_7_days"]} 7-day due soon notifications')
                    self.stdout.write(f'  Would create {results["due_soon_3_days"]} 3-day due soon notifications')
            else:
                with transaction.atomic():
                    results = checker.check_and_notify()
                
                if verbose:
                    self.stdout.write(f'  Created {results.get("due_soon_notifications", 0)} due soon notifications')
                    self.stdout.write(f'  Created {results.get("urgent_due_notifications", 0)} urgent due notifications')
            
            self.stdout.write(f'Invoice due soon check: {results["total_notifications"]} notifications')
            return results
            
        except Exception as e:
            logger.error(f"Error in invoice due soon check: {e}")
            self.stdout.write(
                self.style.ERROR(f'Invoice due soon check failed: {e}')
            )
            return {'total_notifications': 0}