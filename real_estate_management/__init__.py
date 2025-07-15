from .celery import app as celery_app
__all__ = ('celery_app',)

# Importar configuración de Celery Beat
from .celery_beat import app as celery_beat_app
__all__ += ('celery_beat_app',)
