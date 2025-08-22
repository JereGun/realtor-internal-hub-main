from django.db import models
from core.models import BaseModel

class NotificationPreference(BaseModel):
    """
    Modelo que almacena las preferencias de notificaciones de los agentes.
    
    Permite a cada agente personalizar qué tipos de notificaciones desea recibir,
    con qué frecuencia y a través de qué canales. Incluye configuraciones específicas
    para notificaciones relacionadas con facturas, vencimientos y cambios de estado.
    """
    
    FREQUENCY_CHOICES = [
        ('immediately', 'Inmediatamente'),
        ('daily', 'Diariamente'),
        ('weekly', 'Semanalmente'),
    ]
    
    agent = models.OneToOneField('agents.Agent', on_delete=models.CASCADE, related_name='notification_preferences')
    
    # Preferencias para facturas
    receive_invoice_due_soon = models.BooleanField(default=True, verbose_name="Recibir notificaciones de facturas por vencer")
    receive_invoice_overdue = models.BooleanField(default=True, verbose_name="Recibir notificaciones de facturas vencidas")
    receive_invoice_payment = models.BooleanField(default=True, verbose_name="Recibir notificaciones de pagos de facturas")
    receive_invoice_status_change = models.BooleanField(default=True, verbose_name="Recibir notificaciones de cambios de estado de facturas")
    
    # Preferencias para contratos
    receive_contract_expiration = models.BooleanField(default=True, verbose_name="Recibir notificaciones de vencimiento de contratos")
    receive_rent_increase = models.BooleanField(default=True, verbose_name="Recibir notificaciones de aumentos de alquiler")
    
    # Configuración de frecuencia
    notification_frequency = models.CharField(
        max_length=20, 
        choices=FREQUENCY_CHOICES, 
        default='immediately',
        verbose_name="Frecuencia de notificaciones"
    )
    
    # Días de anticipación para notificaciones de vencimiento
    days_before_due_date = models.PositiveIntegerField(
        default=7,
        verbose_name="Días de anticipación para notificar vencimientos"
    )
    
    # Preferencia de correo electrónico
    email_notifications = models.BooleanField(default=False, verbose_name="Recibir notificaciones por correo electrónico")
    
    class Meta:
        verbose_name = "Preferencia de notificación"
        verbose_name_plural = "Preferencias de notificaciones"
    
    def __str__(self):
        return f"Preferencias de {self.agent}"