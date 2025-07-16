from datetime import timedelta
from django.utils import timezone
from user_notifications.services import create_notification
from ..models_invoice import Invoice

class InvoiceNotificationService:
    @staticmethod
    def check_due_soon_notifications(days=7):
        """
        Checks for invoices due in the next 'days' days and creates notifications for them.
        Returns the number of notifications created.
        """
        from user_notifications.models import Notification
        from django.contrib.contenttypes.models import ContentType
        
        today = timezone.now().date()
        due_soon_date = today + timedelta(days=days)
        
        invoices = Invoice.objects.filter(
            status__in=['sent', 'validated'],  # Incluir facturas validadas también
            due_date__lte=due_soon_date,
            due_date__gt=today
        )
        
        notification_count = 0
        invoice_content_type = ContentType.objects.get_for_model(Invoice)
        
        for invoice in invoices:
            # Verificar si ya existe una notificación similar en las últimas 24 horas
            existing_notification = Notification.objects.filter(
                notification_type='invoice_due_soon',
                content_type=invoice_content_type,
                object_id=invoice.id,
                created_at__gte=timezone.now() - timedelta(days=1)
            ).exists()
            
            if not existing_notification:
                days_until_due = (invoice.due_date - today).days
                create_notification(
                    agent=invoice.customer.agent,
                    title=f"Factura por vencer: {invoice.number}",
                    message=f"La factura {invoice.number} vence en {days_until_due} días.",
                    notification_type='invoice_due_soon',
                    related_object=invoice
                )
                notification_count += 1
        
        return notification_count
    
    @staticmethod
    def check_overdue_notifications():
        """
        Checks for overdue invoices and creates notifications for them.
        Returns the number of notifications created.
        """
        from user_notifications.models import Notification
        from django.contrib.contenttypes.models import ContentType
        
        today = timezone.now().date()
        
        invoices = Invoice.objects.filter(
            status__in=['sent', 'validated'],  # Incluir facturas validadas también
            due_date__lt=today
        )
        
        notification_count = 0
        invoice_content_type = ContentType.objects.get_for_model(Invoice)
        
        for invoice in invoices:
            # Verificar si ya existe una notificación similar en las últimas 24 horas
            existing_notification = Notification.objects.filter(
                notification_type='invoice_overdue',
                content_type=invoice_content_type,
                object_id=invoice.id,
                created_at__gte=timezone.now() - timedelta(days=1)
            ).exists()
            
            if not existing_notification:
                days_overdue = (today - invoice.due_date).days
                create_notification(
                    agent=invoice.customer.agent,
                    title=f"Factura vencida: {invoice.number}",
                    message=f"La factura {invoice.number} está vencida desde hace {days_overdue} días.",
                    notification_type='invoice_overdue',
                    related_object=invoice
                )
                notification_count += 1
        
        return notification_count
    
    @staticmethod
    def create_payment_received_notification(payment):
        """
        Creates a notification when a payment is received.
        """
        create_notification(
            agent=payment.invoice.customer.agent,
            title=f"Pago recibido para la factura: {payment.invoice.number}",
            message=f"Se recibió un pago de ${payment.amount} para la factura {payment.invoice.number}.",
            notification_type='invoice_payment_received',
            related_object=payment.invoice
        )
    
    @staticmethod
    def create_status_change_notification(invoice, old_status):
        """
        Creates a notification when the status of an invoice changes.
        """
        create_notification(
            agent=invoice.customer.agent,
            title=f"Cambio de estado de la factura: {invoice.number}",
            message=f"El estado de la factura {invoice.number} cambió de {old_status} a {invoice.status}.",
            notification_type='invoice_status_change',
            related_object=invoice
        )
