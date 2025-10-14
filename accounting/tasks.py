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

# Tareas de facturación automática
from celery import shared_task
from django.utils import timezone
from .services.automatic_invoice_service import AutomaticInvoiceService
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def generate_automatic_invoices(self):
    """
    Tarea programada para generar facturas automáticamente.
    
    Esta tarea se ejecuta diariamente y verifica todos los contratos activos
    para generar facturas según su frecuencia configurada.
    """
    try:
        logger.info("Iniciando generación automática de facturas")
        
        # Generar todas las facturas pendientes
        results = AutomaticInvoiceService.generate_all_due_invoices()
        
        # Log de resultados
        summary = results['summary']
        logger.info(
            f"Generación automática completada: "
            f"{summary['total_invoices_created']} facturas creadas, "
            f"{summary['total_errors']} errores"
        )
        
        # Retornar resumen para monitoreo
        return {
            'success': True,
            'invoices_created': summary['total_invoices_created'],
            'errors': summary['total_errors'],
            'details': results
        }
        
    except Exception as exc:
        logger.error(f"Error en generación automática de facturas: {str(exc)}")
        
        # Reintentar la tarea
        try:
            raise self.retry(countdown=60 * 5, exc=exc)  # Reintentar en 5 minutos
        except self.MaxRetriesExceeded:
            logger.error("Máximo número de reintentos alcanzado para generación de facturas")
            return {
                'success': False,
                'error': str(exc),
                'max_retries_exceeded': True
            }


@shared_task
def generate_monthly_invoices():
    """Tarea específica para generar facturas mensuales"""
    try:
        results = AutomaticInvoiceService.generate_monthly_invoices()
        logger.info(f"Facturas mensuales generadas: {results['invoices_created']}")
        return results
    except Exception as e:
        logger.error(f"Error generando facturas mensuales: {str(e)}")
        return {'success': False, 'error': str(e)}


@shared_task
def generate_quarterly_invoices():
    """Tarea específica para generar facturas trimestrales"""
    try:
        results = AutomaticInvoiceService.generate_quarterly_invoices()
        logger.info(f"Facturas trimestrales generadas: {results['invoices_created']}")
        return results
    except Exception as e:
        logger.error(f"Error generando facturas trimestrales: {str(e)}")
        return {'success': False, 'error': str(e)}
