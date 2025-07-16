from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models_preferences import NotificationPreference
from .forms import NotificationPreferenceForm

@login_required
def notification_preferences(request):
    """Vista para configurar las preferencias de notificaciones"""
    
    # Obtener o crear las preferencias del usuario
    preferences, created = NotificationPreference.objects.get_or_create(
        agent=request.user,
        defaults={
            'receive_invoice_due_soon': True,
            'receive_invoice_overdue': True,
            'receive_invoice_payment': True,
            'receive_invoice_status_change': True,
            'notification_frequency': 'immediately',
            'days_before_due_date': 7,
            'email_notifications': False,
        }
    )
    
    if request.method == 'POST':
        form = NotificationPreferenceForm(request.POST, instance=preferences)
        if form.is_valid():
            form.save()
            messages.success(request, "Preferencias de notificaciones actualizadas correctamente")
            return redirect('user_notifications:notification_preferences')
    else:
        form = NotificationPreferenceForm(instance=preferences)
    
    return render(request, 'user_notifications/notification_preferences.html', {
        'form': form,
        'preferences': preferences,
    })