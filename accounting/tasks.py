from celery import shared_task
from django.core.management import call_command
from django.utils import timezone
from .models_invoice import Invoice
from .services.invoice_notification import InvoiceNotificationService
from user_notifications.services import create_notification
import logging

logger = logging.getLogger(__name__)

@shared_task
def check_invoice_notifications_task():
    """
    Tarea para verificar y crear notificaciones para facturas vencidas y próximas a vencer.
    Esta tarea se ejecuta diariamente a través de Celery Beat.
    """
    try:
        logger.info("Iniciando verificación de notificaciones de facturas")
        
        # Verificar facturas que vencen pronto (7 días)
        due_soon_count = InvoiceNotificationService.check_due_soon_notifications(days=7)
        
        # Verificar facturas vencidas
        overdue_count = InvoiceNotificationService.check_overdue_notifications()
        
        logger.info(f"Verificación completada: {due_soon_count} facturas próximas a vencer, {overdue_count} facturas vencidas")
        return f"Notificaciones creadas: {due_soon_count + overdue_count}"
    except Exception as e:
        logger.error(f"Error al verificar notificaciones de facturas: {str(e)}")
        return f"Error: {str(e)}"