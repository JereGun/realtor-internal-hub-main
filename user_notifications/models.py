from django.db import models
from core.models import BaseModel
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from datetime import timedelta

# Importar el modelo de preferencias de notificaciones
from .models_preferences import NotificationPreference


class Notification(BaseModel):
    """
    Modelo que representa notificaciones enviadas a los agentes del sistema.
    
    Almacena información sobre diferentes tipos de notificaciones relacionadas
    con facturas, contratos y otros eventos del sistema. Permite relacionar
    la notificación con cualquier otro modelo mediante una relación genérica.
    """
    TYPE_CHOICES = [
        ('invoice_due_soon', 'Vencimiento Próximo'),
        ('invoice_overdue', 'Factura Vencida'),
        ('invoice_payment_received', 'Pago Recibido'),
        ('invoice_status_change', 'Cambio de Estado'),
        ('contract_increase', 'Aumento de Contrato'),
        ('contract_expiration', 'Vencimiento de Contrato'),
        ('batch_summary', 'Resumen de Notificaciones'),
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

    def mark_as_read(self):
        """Mark notification as read"""
        self.is_read = True
        self.save(update_fields=['is_read'])

    def get_related_object_url(self):
        """Get URL for the related object if applicable"""
        if self.related_object:
            # Check if the object has a get_absolute_url method
            if hasattr(self.related_object, 'get_absolute_url'):
                return self.related_object.get_absolute_url()
            
            # Handle specific object types
            model_name = self.content_type.model
            
            if model_name == 'invoice':
                from django.urls import reverse
                return reverse('accounting:invoice_detail', kwargs={'pk': self.related_object.pk})
            elif model_name == 'contract':
                from django.urls import reverse
                return reverse('contracts:contract_detail', kwargs={'pk': self.related_object.pk})
            elif model_name == 'payment':
                from django.urls import reverse
                return reverse('accounting:payment_detail', kwargs={'pk': self.related_object.pk})
        
        return None


class NotificationLog(BaseModel):
    """
    Track notification creation to prevent duplicates within time windows.
    
    This model logs when notifications are created to prevent sending
    duplicate notifications for the same object within a specified time period.
    """
    agent = models.ForeignKey('agents.Agent', on_delete=models.CASCADE, verbose_name="Agente")
    notification_type = models.CharField(max_length=30, verbose_name="Tipo de Notificación")
    object_id = models.PositiveIntegerField(verbose_name="ID del Objeto")
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, verbose_name="Tipo de Contenido")
    created_date = models.DateField(auto_now_add=True, verbose_name="Fecha de Creación")
    
    class Meta:
        verbose_name = "Log de Notificación"
        verbose_name_plural = "Logs de Notificaciones"
        unique_together = ['agent', 'notification_type', 'object_id', 'content_type', 'created_date']
        indexes = [
            models.Index(fields=['agent', 'notification_type', 'created_date']),
            models.Index(fields=['content_type', 'object_id']),
        ]

    def __str__(self):
        return f"{self.agent} - {self.notification_type} - {self.created_date}"

    @classmethod
    def has_recent_notification(cls, agent, notification_type, related_object, days_threshold=1):
        """
        Check if a similar notification was created recently.
        
        Args:
            agent: The agent to check for
            notification_type: Type of notification
            related_object: The related object
            days_threshold: Number of days to look back for duplicates
            
        Returns:
            bool: True if a recent notification exists
        """
        if not related_object:
            return False
            
        content_type = ContentType.objects.get_for_model(related_object)
        threshold_date = timezone.now().date() - timedelta(days=days_threshold)
        
        return cls.objects.filter(
            agent=agent,
            notification_type=notification_type,
            content_type=content_type,
            object_id=related_object.pk,
            created_date__gte=threshold_date
        ).exists()

    @classmethod
    def log_notification(cls, agent, notification_type, related_object):
        """
        Log that a notification was created.
        
        Args:
            agent: The agent the notification was sent to
            notification_type: Type of notification
            related_object: The related object
        """
        if not related_object:
            return None
            
        content_type = ContentType.objects.get_for_model(related_object)
        
        log_entry, created = cls.objects.get_or_create(
            agent=agent,
            notification_type=notification_type,
            content_type=content_type,
            object_id=related_object.pk,
            created_date=timezone.now().date()
        )
        
        return log_entry


class NotificationBatch(BaseModel):
    """
    Model to store batched notifications for users who prefer daily/weekly delivery.
    
    This model temporarily stores notifications that should be delivered in batches
    based on user preferences instead of immediately.
    """
    BATCH_TYPE_CHOICES = [
        ('daily', 'Daily Batch'),
        ('weekly', 'Weekly Batch'),
    ]
    
    agent = models.ForeignKey('agents.Agent', on_delete=models.CASCADE, verbose_name="Agente")
    batch_type = models.CharField(max_length=10, choices=BATCH_TYPE_CHOICES, verbose_name="Tipo de Lote")
    title = models.CharField(max_length=200, verbose_name="Título")
    message = models.TextField(verbose_name="Mensaje")
    notification_type = models.CharField(max_length=30, verbose_name="Tipo de Notificación")
    
    # Generic relation to other models
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    related_object = GenericForeignKey('content_type', 'object_id')
    
    # Batch processing fields
    scheduled_for = models.DateTimeField(verbose_name="Programado para")
    processed = models.BooleanField(default=False, verbose_name="Procesado")
    processed_at = models.DateTimeField(null=True, blank=True, verbose_name="Procesado en")
    
    class Meta:
        verbose_name = "Lote de Notificación"
        verbose_name_plural = "Lotes de Notificaciones"
        ordering = ['scheduled_for', '-created_at']
        indexes = [
            models.Index(fields=['agent', 'batch_type', 'processed']),
            models.Index(fields=['scheduled_for', 'processed']),
        ]

    def __str__(self):
        return f"{self.agent} - {self.batch_type} - {self.title}"

    @classmethod
    def create_batch_notification(cls, agent, title, message, notification_type, related_object=None):
        """
        Create a batched notification based on agent preferences.
        
        Args:
            agent: The agent to notify
            title: Notification title
            message: Notification message
            notification_type: Type of notification
            related_object: Related object (optional)
            
        Returns:
            NotificationBatch: The created batch notification or None if immediate delivery
        """
        from .services import get_notification_preferences
        
        preferences = get_notification_preferences(agent)
        
        # If immediate delivery, return None to indicate no batching
        if preferences.notification_frequency == 'immediately':
            return None
            
        # Calculate scheduled delivery time
        now = timezone.now()
        if preferences.notification_frequency == 'daily':
            # Schedule for next day at 9 AM
            scheduled_for = now.replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=1)
            batch_type = 'daily'
        elif preferences.notification_frequency == 'weekly':
            # Schedule for next Monday at 9 AM
            days_until_monday = (7 - now.weekday()) % 7
            if days_until_monday == 0:  # If today is Monday, schedule for next Monday
                days_until_monday = 7
            scheduled_for = (now + timedelta(days=days_until_monday)).replace(hour=9, minute=0, second=0, microsecond=0)
            batch_type = 'weekly'
        else:
            return None
            
        # Create batch notification
        content_type = None
        object_id = None
        if related_object:
            content_type = ContentType.objects.get_for_model(related_object)
            object_id = related_object.pk
            
        batch_notification = cls.objects.create(
            agent=agent,
            batch_type=batch_type,
            title=title,
            message=message,
            notification_type=notification_type,
            content_type=content_type,
            object_id=object_id,
            scheduled_for=scheduled_for
        )
        
        return batch_notification

    @classmethod
    def get_ready_batches(cls, batch_type=None):
        """
        Get batches that are ready to be processed.
        
        Args:
            batch_type: Optional filter by batch type ('daily' or 'weekly')
            
        Returns:
            QuerySet: Batches ready for processing
        """
        queryset = cls.objects.filter(
            processed=False,
            scheduled_for__lte=timezone.now()
        )
        
        if batch_type:
            queryset = queryset.filter(batch_type=batch_type)
            
        return queryset.order_by('agent', 'scheduled_for')

    def mark_as_processed(self):
        """Mark this batch notification as processed"""
        self.processed = True
        self.processed_at = timezone.now()
        self.save(update_fields=['processed', 'processed_at'])
