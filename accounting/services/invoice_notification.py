from datetime import timedelta
from django.utils import timezone
from django.db.models import Q
from .models_notification import InvoiceNotification
from ..models_invoice import Invoice

class InvoiceNotificationService:
    @staticmethod
    def check_due_soon_notifications(days=7):
        """
        Verifica facturas que vencen en los próximos 'days' días
        y crea notificaciones para ellas
        """
        today = timezone.now().date()
        due_soon_date = today + timedelta(days=days)
        
        # Facturas que vencen en los próximos 'days' días
        invoices = Invoice.objects.filter(
            status='sent',
            due_date__lte=due_soon_date,
            due_date__gt=today
        )
        
        for invoice in invoices:
            # Verificar si ya existe una notificación para esta factura
            if not InvoiceNotification.objects.filter(
                invoice=invoice,
                type='due_soon',
                due_date=invoice.due_date
            ).exists():
                InvoiceNotification.objects.create(
                    invoice=invoice,
                    customer=invoice.customer,
                    type='due_soon',
                    message=f"La factura {invoice.number} vence en {days} días",
                    due_date=invoice.due_date
                )
    
    @staticmethod
    def check_overdue_notifications():
        """
        Verifica facturas vencidas y crea notificaciones para ellas
        """
        today = timezone.now().date()
        
        # Facturas vencidas
        invoices = Invoice.objects.filter(
            status='sent',
            due_date__lt=today
        )
        
        for invoice in invoices:
            # Verificar si ya existe una notificación para esta factura
            if not InvoiceNotification.objects.filter(
                invoice=invoice,
                type='overdue',
                due_date=invoice.due_date
            ).exists():
                InvoiceNotification.objects.create(
                    invoice=invoice,
                    customer=invoice.customer,
                    type='overdue',
                    message=f"La factura {invoice.number} está vencida desde {invoice.due_date}",
                    due_date=invoice.due_date
                )
    
    @staticmethod
    def create_payment_received_notification(payment):
        """
        Crea una notificación cuando se recibe un pago
        """
        InvoiceNotification.objects.create(
            invoice=payment.invoice,
            customer=payment.invoice.customer,
            type='payment_received',
            message=f"Se recibió un pago de ${payment.amount} para la factura {payment.invoice.number}",
            due_date=payment.date
        )
    
    @staticmethod
    def create_status_change_notification(invoice, old_status):
        """
        Crea una notificación cuando cambia el estado de una factura
        """
        InvoiceNotification.objects.create(
            invoice=invoice,
            customer=invoice.customer,
            type='status_change',
            message=f"El estado de la factura {invoice.number} cambió de {old_status} a {invoice.status}",
            due_date=invoice.due_date if invoice.status == 'sent' else None
        )
