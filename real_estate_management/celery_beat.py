from celery import Celery
from django.conf import settings
from datetime import timedelta

app = Celery('real_estate_management')
app.config_from_object('django.conf:settings', namespace='CELERY')

app.conf.beat_schedule = {
    'check-invoice-notifications-daily': {
        'task': 'accounting.tasks.check_invoice_notifications_task',
        'schedule': timedelta(days=1),
        'options': {'expires': 3600}  # Expira después de 1 hora
    },
}
