
from django.contrib import admin
from .models import TaskNotification


@admin.register(TaskNotification)
class TaskNotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'agent', 'priority', 'status', 'due_date', 'created_at')
    list_filter = ('priority', 'status', 'agent', 'due_date')
    search_fields = ('title', 'description', 'agent__first_name', 'agent__last_name')
    date_hierarchy = 'due_date'
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('title', 'description', 'agent')
        }),
        ('Detalles de la Tarea', {
            'fields': ('priority', 'status', 'due_date')
        }),
        ('Relaciones Opcionales', {
            'fields': ('property', 'customer', 'contract')
        }),
        ('Información Adicional', {
            'fields': ('notes', 'completed_at')
        }),
    )
