from celery import Celery
from django.conf import settings
from datetime import timedelta

app = Celery('real_estate_management')
app.config_from_object('django.conf:settings', namespace='CELERY')

app.conf.beat_schedule = {
}
