"""
Management command to check Celery Beat status and scheduled tasks.

This command provides information about the current Celery Beat configuration,
scheduled tasks, and their execution status.
"""

from django.core.management.base import BaseCommand
from django.conf import settings
from celery import current_app
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Check Celery Beat status and scheduled notification tasks'

    def add_arguments(self, parser):
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed task configuration',
        )

    def handle(self, *args, **options):
        """Check and display Celery Beat configuration status"""
        
        self.stdout.write(
            self.style.SUCCESS('=== Celery Beat Configuration Status ===')
        )
        
        # Check if Celery Beat schedule is configured
        beat_schedule = getattr(settings, 'CELERY_BEAT_SCHEDULE', {})
        
        if not beat_schedule:
            self.stdout.write(
                self.style.ERROR('No Celery Beat schedule found in settings!')
            )
            return
        
        self.stdout.write(
            self.style.SUCCESS(f'Found {len(beat_schedule)} scheduled tasks:')
        )
        
        # Display each scheduled task
        for task_name, task_config in beat_schedule.items():
            self.stdout.write(f'\n📅 Task: {task_name}')
            self.stdout.write(f'   Task Function: {task_config["task"]}')
            
            # Display schedule information
            schedule = task_config.get('schedule')
            if hasattr(schedule, 'hour') and hasattr(schedule, 'minute'):
                # Handle crontab schedule
                hour = getattr(schedule, 'hour', set())
                minute = getattr(schedule, 'minute', set())
                if isinstance(hour, set) and len(hour) == 1:
                    hour = list(hour)[0]
                if isinstance(minute, set) and len(minute) == 1:
                    minute = list(minute)[0]
                self.stdout.write(f'   Schedule: Daily at {hour:02d}:{minute:02d}')
            else:
                self.stdout.write(f'   Schedule: {schedule}')
            
            # Display options if verbose
            if options['verbose']:
                task_options = task_config.get('options', {})
                if task_options:
                    self.stdout.write(f'   Options: {task_options}')
        
        # Check Celery app configuration
        self.stdout.write('\n=== Celery App Configuration ===')
        
        try:
            app = current_app
            self.stdout.write(f'Broker URL: {app.conf.broker_url}')
            self.stdout.write(f'Result Backend: {app.conf.result_backend}')
            self.stdout.write(f'Timezone: {app.conf.timezone}')
            
            # Check if beat scheduler is configured
            beat_scheduler = getattr(app.conf, 'beat_scheduler', 'celery.beat:PersistentScheduler')
            self.stdout.write(f'Beat Scheduler: {beat_scheduler}')
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error accessing Celery app configuration: {e}')
            )
        
        # Check notification task modules
        self.stdout.write('\n=== Notification Task Modules ===')
        
        try:
            from user_notifications.tasks import (
                check_contract_expirations,
                check_invoice_overdue,
                check_rent_increases,
                check_invoice_due_soon,
                process_notification_batches
            )
            
            tasks = [
                check_contract_expirations,
                check_invoice_overdue,
                check_rent_increases,
                check_invoice_due_soon,
                process_notification_batches
            ]
            
            self.stdout.write(f'✅ All {len(tasks)} notification tasks are importable')
            
            if options['verbose']:
                for task in tasks:
                    self.stdout.write(f'   - {task.name}')
                    
        except ImportError as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error importing notification tasks: {e}')
            )
        
        # Provide next steps
        self.stdout.write('\n=== Next Steps ===')
        self.stdout.write('To start Celery Beat scheduler, run:')
        self.stdout.write('  celery -A real_estate_management beat --loglevel=info')
        self.stdout.write('\nTo start Celery worker, run:')
        self.stdout.write('  celery -A real_estate_management worker --loglevel=info')
        self.stdout.write('\nTo monitor tasks, run:')
        self.stdout.write('  celery -A real_estate_management flower')
        
        logger.info("Celery Beat status check completed")