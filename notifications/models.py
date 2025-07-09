
from django.db import models
from core.models import BaseModel


class TaskNotification(BaseModel):
    """Task notification model"""
    PRIORITY_CHOICES = [
        ('low', 'Baja'),
        ('medium', 'Media'),
        ('high', 'Alta'),
        ('urgent', 'Urgente'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('completed', 'Completada'),
        ('cancelled', 'Cancelada'),
    ]
    
    # Basic Information
    title = models.CharField(max_length=200, verbose_name="Título")
    description = models.TextField(verbose_name="Descripción")
    agent = models.ForeignKey('agents.Agent', on_delete=models.CASCADE, verbose_name="Agente")
    
    # Task Details
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium', verbose_name="Prioridad")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending', verbose_name="Estado")
    due_date = models.DateTimeField(verbose_name="Fecha de Vencimiento")
    
    # Optional Relations
    property = models.ForeignKey('properties.Property', on_delete=models.CASCADE, blank=True, null=True, verbose_name="Propiedad")
    customer = models.ForeignKey('customers.Customer', on_delete=models.CASCADE, blank=True, null=True, verbose_name="Cliente")
    contract = models.ForeignKey('contracts.Contract', on_delete=models.CASCADE, blank=True, null=True, verbose_name="Contrato")
    
    # Additional Information
    notes = models.TextField(blank=True, verbose_name="Notas")
    completed_at = models.DateTimeField(blank=True, null=True, verbose_name="Completada en")
    
    class Meta:
        verbose_name = "Notificación de Tarea"
        verbose_name_plural = "Notificaciones de Tareas"
        ordering = ['due_date', '-priority']
    
    def __str__(self):
        return f"{self.title} - {self.get_priority_display()}"
    
    # @property
    # def is_overdue(self):
    #     from django.utils import timezone
    #     return self.status == 'pending' and self.due_date < timezone.now()
