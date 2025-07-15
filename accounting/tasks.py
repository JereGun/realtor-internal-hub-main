from celery import shared_task
from .services.invoice_notification import InvoiceNotificationService

@shared_task
def check_invoice_notifications():
    """
    Tarea periódica que verifica y crea notificaciones para facturas
    """
    # Verificar facturas que vencen pronto
    InvoiceNotificationService.check_due_soon_notifications(days=7)
    
    # Verificar facturas vencidas
    InvoiceNotificationService.check_overdue_notifications()
    
    return {"status": "success", "message": "Notificaciones de facturas verificadas"}
