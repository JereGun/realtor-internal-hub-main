"""
Celery Beat configuration for the real estate management system.

This module is kept for backward compatibility but the actual beat schedule
configuration has been moved to settings.py for better organization and
to avoid duplication with the main Celery configuration.

All periodic task schedules are now defined in CELERY_BEAT_SCHEDULE in settings.py.
"""

from celery import Celery
from django.conf import settings

app = Celery('real_estate_management')
app.config_from_object('django.conf:settings', namespace='CELERY')

# Note: Beat schedule is now configured in settings.py
# This ensures all Celery configuration is centralized and avoids conflicts
