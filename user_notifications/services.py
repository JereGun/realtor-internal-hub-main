from django.contrib.contenttypes.models import ContentType
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from .models import Notification
from .models_preferences import NotificationPreference

def create_notification(agent, title, message, notification_type, related_object=None):
    """
    Creates a new notification and sends an email if configured.
    """
    content_type = None
    object_id = None
    if related_object:
        content_type = ContentType.objects.get_for_model(related_object)
        object_id = related_object.pk

    # Crear la notificación en el sistema
    notification = Notification.objects.create(
        agent=agent,
        title=title,
        message=message,
        notification_type=notification_type,
        content_type=content_type,
        object_id=object_id,
    )
    
    # Verificar si el usuario desea recibir notificaciones por correo electrónico
    try:
        preferences = NotificationPreference.objects.get(agent=agent)
        if preferences.email_notifications:
            # Verificar el tipo de notificación y las preferencias específicas
            should_send_email = False
            
            if notification_type == 'invoice_due_soon' and preferences.receive_invoice_due_soon:
                should_send_email = True
            elif notification_type == 'invoice_overdue' and preferences.receive_invoice_overdue:
                should_send_email = True
            elif notification_type == 'invoice_payment_received' and preferences.receive_invoice_payment:
                should_send_email = True
            elif notification_type == 'invoice_status_change' and preferences.receive_invoice_status_change:
                should_send_email = True
            
            if should_send_email and agent.email:
                send_notification_email(notification)
    except NotificationPreference.DoesNotExist:
        # Si no hay preferencias configuradas, no enviar correo electrónico
        pass
    
    return notification

def send_notification_email(notification):
    """
    Sends an email notification to the user.
    """
    from django.contrib.sites.shortcuts import get_current_site
    from django.contrib.sites.models import Site
    
    subject = notification.title
    
    # Obtener la URL del sitio
    try:
        site = Site.objects.get_current()
        site_url = f"https://{site.domain}" if site.domain else ""
    except:
        # Si no se puede obtener el sitio, usar una URL vacía
        site_url = ""
    
    # Preparar el contexto para la plantilla
    context = {
        'notification': notification,
        'agent': notification.agent,
        'site_url': site_url,
    }
    
    # Renderizar el contenido HTML del correo
    html_message = render_to_string('user_notifications/email/notification_email.html', context)
    plain_message = strip_tags(html_message)
    
    # Enviar el correo electrónico
    send_mail(
        subject=subject,
        message=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[notification.agent.email],
        html_message=html_message,
        fail_silently=True,
    )