from django import forms
from .models_preferences import NotificationPreference

class NotificationPreferenceForm(forms.ModelForm):
    """Formulario para configurar las preferencias de notificaciones"""
    
    class Meta:
        model = NotificationPreference
        fields = [
            'receive_invoice_due_soon',
            'receive_invoice_overdue',
            'receive_invoice_payment',
            'receive_invoice_status_change',
            'notification_frequency',
            'days_before_due_date',
            'email_notifications',
        ]
        
        widgets = {
            'days_before_due_date': forms.NumberInput(attrs={'min': 1, 'max': 30}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['days_before_due_date'].help_text = "Número de días antes del vencimiento para enviar notificaciones (entre 1 y 30)"
        self.fields['notification_frequency'].help_text = "Frecuencia con la que deseas recibir notificaciones"
        self.fields['email_notifications'].help_text = "Además de las notificaciones en la plataforma, recibirás notificaciones por correo electrónico"