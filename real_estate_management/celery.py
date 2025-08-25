from __future__ import absolute_import, unicode_literals
import os
import logging
from celery import Celery
from celery.signals import task_failure, task_success, task_retry
from django.conf import settings

# Set up logging
logger = logging.getLogger(__name__)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'real_estate_management.settings')

app = Celery('real_estate_management')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

# Configure Celery Beat scheduler
app.conf.beat_scheduler = 'django_celery_beat.schedulers:DatabaseScheduler'

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')

# Task monitoring and logging signals
@task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, traceback=None, einfo=None, **kwargs):
    """Handle task failures with proper logging"""
    logger.error(
        f"Task {sender.name} [{task_id}] failed: {exception}",
        extra={
            'task_id': task_id,
            'task_name': sender.name,
            'exception': str(exception),
            'traceback': traceback
        }
    )

@task_success.connect
def task_success_handler(sender=None, result=None, **kwargs):
    """Log successful task completion"""
    logger.info(
        f"Task {sender.name} completed successfully",
        extra={
            'task_name': sender.name,
            'result': result
        }
    )

@task_retry.connect
def task_retry_handler(sender=None, task_id=None, reason=None, einfo=None, **kwargs):
    """Log task retries"""
    logger.warning(
        f"Task {sender.name} [{task_id}] retrying: {reason}",
        extra={
            'task_id': task_id,
            'task_name': sender.name,
            'retry_reason': str(reason)
        }
    )
