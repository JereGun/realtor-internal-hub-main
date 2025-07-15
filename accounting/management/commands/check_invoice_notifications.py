from django.core.management.base import BaseCommand
from accounting.services.invoice_notification import InvoiceNotificationService

class Command(BaseCommand):
    help = 'Verifica y crea notificaciones para facturas vencidas y próximas a vencer'

    def handle(self, *args, **options):
        # Verificar facturas que vencen pronto
        InvoiceNotificationService.check_due_soon_notifications(days=7)
        
        # Verificar facturas vencidas
        InvoiceNotificationService.check_overdue_notifications()
        
        self.stdout.write(self.style.SUCCESS('Notificaciones de facturas verificadas exitosamente'))
