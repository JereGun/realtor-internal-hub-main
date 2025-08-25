"""
Management command to set up periodic tasks in the database.

This command creates the periodic tasks in the django-celery-beat database
tables, which allows for dynamic management of scheduled tasks through
the Django admin interface.
"""

from django.core.management.base import BaseCommand
from django.conf import settings
from django_celery_beat.models import PeriodicTask, CrontabSchedule
import json
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Set up periodic notification tasks in the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force update existing tasks',
        )

    def handle(self, *args, **options):
        """Set up periodic tasks in the database"""
        
        self.stdout.write(
            self.style.SUCCESS('=== Setting up Periodic Notification Tasks ===')
        )
        
        # Get the beat schedule from settings
        beat_schedule = getattr(settings, 'CELERY_BEAT_SCHEDULE', {})
        
        if not beat_schedule:
            self.stdout.write(
                self.style.ERROR('No CELERY_BEAT_SCHEDULE found in settings!')
            )
            return
        
        created_count = 0
        updated_count = 0
        
        for task_name, task_config in beat_schedule.items():
            try:
                # Extract schedule information
                schedule = task_config['schedule']
                task_function = task_config['task']
                task_options = task_config.get('options', {})
                
                # Create or get crontab schedule
                if hasattr(schedule, 'hour') and hasattr(schedule, 'minute'):
                    # Handle crontab schedule
                    hour = getattr(schedule, 'hour', set())
                    minute = getattr(schedule, 'minute', set())
                    day_of_week = getattr(schedule, 'day_of_week', '*')
                    day_of_month = getattr(schedule, 'day_of_month', '*')
                    month_of_year = getattr(schedule, 'month_of_year', '*')
                    
                    # Convert sets to strings for database storage
                    if isinstance(hour, set):
                        hour = ','.join(map(str, sorted(hour))) if hour else '*'
                    if isinstance(minute, set):
                        minute = ','.join(map(str, sorted(minute))) if minute else '*'
                    if isinstance(day_of_week, set):
                        day_of_week = ','.join(map(str, sorted(day_of_week))) if day_of_week else '*'
                    if isinstance(day_of_month, set):
                        day_of_month = ','.join(map(str, sorted(day_of_month))) if day_of_month else '*'
                    if isinstance(month_of_year, set):
                        month_of_year = ','.join(map(str, sorted(month_of_year))) if month_of_year else '*'
                    
                    crontab_schedule, created = CrontabSchedule.objects.get_or_create(
                        minute=str(minute),
                        hour=str(hour),
                        day_of_week=str(day_of_week),
                        day_of_month=str(day_of_month),
                        month_of_year=str(month_of_year),
                        timezone=getattr(settings, 'CELERY_TIMEZONE', 'UTC')
                    )
                    
                    if created:
                        self.stdout.write(f'Created crontab schedule: {crontab_schedule}')
                    
                    # Create or update periodic task
                    task_defaults = {
                        'task': task_function,
                        'crontab': crontab_schedule,
                        'enabled': True,
                        'kwargs': json.dumps({}),
                        'args': json.dumps([]),
                    }
                    
                    # Only add expires if it's provided and not None
                    expires = task_options.get('expires')
                    if expires is not None:
                        task_defaults['expire_seconds'] = expires
                    
                    periodic_task, task_created = PeriodicTask.objects.get_or_create(
                        name=task_name,
                        defaults=task_defaults
                    )
                    
                    if task_created:
                        created_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(f'✅ Created periodic task: {task_name}')
                        )
                    else:
                        if options['force']:
                            # Update existing task
                            periodic_task.task = task_function
                            periodic_task.crontab = crontab_schedule
                            periodic_task.enabled = True
                            expires = task_options.get('expires')
                            if expires is not None:
                                periodic_task.expire_seconds = expires
                            periodic_task.save()
                            updated_count += 1
                            self.stdout.write(
                                self.style.WARNING(f'🔄 Updated periodic task: {task_name}')
                            )
                        else:
                            self.stdout.write(
                                self.style.WARNING(f'⚠️  Task already exists: {task_name} (use --force to update)')
                            )
                
                else:
                    self.stdout.write(
                        self.style.ERROR(f'❌ Unsupported schedule type for task: {task_name}')
                    )
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'❌ Error setting up task {task_name}: {e}')
                )
                logger.error(f"Error setting up periodic task {task_name}: {e}")
        
        # Summary
        self.stdout.write('\n=== Summary ===')
        self.stdout.write(f'Tasks created: {created_count}')
        self.stdout.write(f'Tasks updated: {updated_count}')
        
        if created_count > 0 or updated_count > 0:
            self.stdout.write('\n=== Next Steps ===')
            self.stdout.write('1. Start Celery worker:')
            self.stdout.write('   celery -A real_estate_management worker --loglevel=info')
            self.stdout.write('2. Start Celery beat scheduler:')
            self.stdout.write('   celery -A real_estate_management beat --loglevel=info --scheduler=django_celery_beat.schedulers:DatabaseScheduler')
            self.stdout.write('3. View tasks in Django admin: /admin/django_celery_beat/periodictask/')
        
        logger.info(f"Periodic task setup completed: {created_count} created, {updated_count} updated")