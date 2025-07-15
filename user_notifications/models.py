from django.db import models
from core.models import BaseModel
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType


class Notification(BaseModel):
    """Notification model"""
    TYPE_CHOICES = [
        ('invoice_due_soon', 'Vencimiento Próximo'),
        ('invoice_overdue', 'Factura Vencida'),
        ('invoice_payment_received', 'Pago Recibido'),
        ('invoice_status_change', 'Cambio de Estado'),
        ('contract_increase', 'Aumento de Contrato'),
        ('generic', 'Notificación General'),
    ]

    agent = models.ForeignKey('agents.Agent', on_delete=models.CASCADE, verbose_name="Agente")
    title = models.CharField(max_length=200, verbose_name="Título")
    message = models.TextField(verbose_name="Mensaje")
    is_read = models.BooleanField(default=False, verbose_name="Leído")
    notification_type = models.CharField(max_length=30, choices=TYPE_CHOICES, default='generic', verbose_name="Tipo de Notificación")

    # Generic relation to other models
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    related_object = GenericForeignKey('content_type', 'object_id')

    class Meta:
        verbose_name = "Notificación"
        verbose_name_plural = "Notificaciones"
        ordering = ['-created_at']

    def __str__(self):
        return self.title
