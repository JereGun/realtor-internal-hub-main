from django.db import models
from django.utils import timezone
from notifications.models import TaskNotification
from .models_invoice import Invoice
from customers.models import Customer

class InvoiceNotification(BaseModel):
    TYPE_CHOICES = [
        ('due_soon', 'Vencimiento Próximo'),
        ('overdue', 'Factura Vencida'),
        ('payment_received', 'Pago Recibido'),
        ('status_change', 'Cambio de Estado'),
    ]
    
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='notifications')
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='invoice_notifications')
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    message = models.TextField()
    due_date = models.DateField(null=True, blank=True)
    is_read = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = 'Notificación de Factura'
        verbose_name_plural = 'Notificaciones de Facturas'
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.get_type_display()} - Factura {self.invoice.number}"
    
    def create_task_notification(self):
        """Crear una TaskNotification asociada"""
        TaskNotification.objects.create(
            agent=self.invoice.customer.agent,
            title=self.get_type_display(),
            description=self.message,
            due_date=self.due_date,
            status='pending' if self.type in ['due_soon', 'overdue'] else 'completed',
            priority='high' if self.type == 'overdue' else 'medium',
            related_object=self.invoice,
            related_model='Invoice'
        )
