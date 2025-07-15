from django.db import models
from django.utils import timezone
from .models_invoice import Invoice
from customers.models import Customer

class InvoiceNotification(models.Model):
    TYPE_CHOICES = [
        ('due_soon', 'Vencimiento Próximo'),
        ('overdue', 'Factura Vencida'),
        ('payment_received', 'Pago Recibido'),
        ('status_change', 'Cambio de Estado'),
    ]
    
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='invoice_notifications')
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='customer_invoice_notifications')
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    message = models.TextField()
    due_date = models.DateField(null=True, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Notificación de Factura'
        verbose_name_plural = 'Notificaciones de Facturas'
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.get_type_display()} - Factura {self.invoice.number}"
