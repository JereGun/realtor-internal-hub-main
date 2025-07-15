from datetime import timedelta
from django.utils import timezone
from user_notifications.services import create_notification
from ..models_invoice import Invoice

class InvoiceNotificationService:
    @staticmethod
    def check_due_soon_notifications(days=7):
        """
        Checks for invoices due in the next 'days' days and creates notifications for them.
        """
        today = timezone.now().date()
        due_soon_date = today + timedelta(days=days)
        
        invoices = Invoice.objects.filter(
            status='sent',
            due_date__lte=due_soon_date,
            due_date__gt=today
        )
        
        for invoice in invoices:
            create_notification(
                agent=invoice.customer.agent,
                title=f"Factura por vencer: {invoice.number}",
                message=f"La factura {invoice.number} vence en {days} días.",
                notification_type='invoice_due_soon',
                related_object=invoice
            )
    
    @staticmethod
    def check_overdue_notifications():
        """
        Checks for overdue invoices and creates notifications for them.
        """
        today = timezone.now().date()
        
        invoices = Invoice.objects.filter(
            status='sent',
            due_date__lt=today
        )
        
        for invoice in invoices:
            create_notification(
                agent=invoice.customer.agent,
                title=f"Factura vencida: {invoice.number}",
                message=f"La factura {invoice.number} está vencida desde {invoice.due_date}.",
                notification_type='invoice_overdue',
                related_object=invoice
            )
    
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
