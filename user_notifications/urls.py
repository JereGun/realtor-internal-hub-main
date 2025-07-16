from django.urls import path
from django.views.generic import RedirectView
from . import views

app_name = 'user_notifications'

urlpatterns = [
    # Redirigir la URL principal a la vista de notificaciones de facturas
    path('', RedirectView.as_view(pattern_name='accounting:invoice_notifications'), name='notification_list'),
    path('preferences/', views.notification_preferences, name='notification_preferences'),
]