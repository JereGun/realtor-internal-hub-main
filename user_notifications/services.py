from django.contrib.contenttypes.models import ContentType
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils import timezone
from datetime import timedelta
from collections import defaultdict
from .models import Notification, NotificationLog
from .models_preferences import NotificationPreference
import logging

logger = logging.getLogger(__name__)

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
            elif notification_type in ['invoice_overdue', 'invoice_overdue_urgent', 'invoice_overdue_critical'] and preferences.receive_invoice_overdue:
                should_send_email = True
            elif notification_type == 'invoice_payment_received' and preferences.receive_invoice_payment:
                should_send_email = True
            elif notification_type == 'invoice_status_change' and preferences.receive_invoice_status_change:
                should_send_email = True
            elif notification_type in ['contract_expired', 'contract_expiring_urgent', 'contract_expiring_soon'] and preferences.receive_contract_expiration:
                should_send_email = True
            elif notification_type in ['rent_increase_due', 'rent_increase_overdue'] and preferences.receive_rent_increase:
                should_send_email = True
            
            if should_send_email and agent.email:
                send_notification_email(notification)
    except NotificationPreference.DoesNotExist:
        # Si no hay preferencias configuradas, no enviar correo electrónico
        pass
    
    return notification

def send_notification_email(notification):
    """
    Sends an email notification to the user with appropriate template based on notification type.
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
    
    # Seleccionar la plantilla apropiada basada en el tipo de notificación
    template_name = 'user_notifications/email/notification_email.html'  # Default template
    
    if notification.notification_type == 'invoice_overdue':
        template_name = 'user_notifications/email/invoice_overdue_standard.html'
    elif notification.notification_type == 'invoice_overdue_urgent':
        template_name = 'user_notifications/email/invoice_overdue_urgent.html'
    elif notification.notification_type == 'invoice_overdue_critical':
        template_name = 'user_notifications/email/invoice_overdue_critical.html'
    elif notification.notification_type == 'rent_increase_due':
        template_name = 'user_notifications/email/rent_increase_due.html'
    elif notification.notification_type == 'rent_increase_overdue':
        template_name = 'user_notifications/email/rent_increase_overdue.html'
    
    # Renderizar el contenido HTML del correo
    try:
        html_message = render_to_string(template_name, context)
    except:
        # Fallback to default template if specific template fails
        logger.warning(f"Failed to render template {template_name}, using default template")
        html_message = render_to_string('user_notifications/email/notification_email.html', context)
    
    plain_message = strip_tags(html_message)
    
    # Enviar el correo electrónico
    try:
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[notification.agent.email],
            html_message=html_message,
            fail_silently=True,
        )
        logger.info(f"Email notification sent to {notification.agent.email} for {notification.notification_type}")
    except Exception as e:
        logger.error(f"Failed to send email notification: {e}")
        # Don't raise exception to avoid breaking the notification creation process


def create_notification_if_not_exists(agent, title, message, notification_type, related_object=None, duplicate_threshold_days=1):
    """
    Creates a notification only if a similar one doesn't exist within the threshold period.
    
    Args:
        agent: The agent to notify
        title: Notification title
        message: Notification message
        notification_type: Type of notification
        related_object: Related object (optional)
        duplicate_threshold_days: Days to check for duplicates (default: 1)
        
    Returns:
        tuple: (notification, created) where created is True if notification was created
    """
    try:
        # Check if a recent notification exists
        if NotificationLog.has_recent_notification(
            agent=agent,
            notification_type=notification_type,
            related_object=related_object,
            days_threshold=duplicate_threshold_days
        ):
            logger.info(f"Duplicate notification prevented for agent {agent.id}, type {notification_type}")
            return None, False
        
        # Create the notification
        notification = create_notification(
            agent=agent,
            title=title,
            message=message,
            notification_type=notification_type,
            related_object=related_object
        )
        
        # Log the notification creation
        NotificationLog.log_notification(
            agent=agent,
            notification_type=notification_type,
            related_object=related_object
        )
        
        logger.info(f"Notification created for agent {agent.id}, type {notification_type}")
        return notification, True
        
    except Exception as e:
        logger.error(f"Error creating notification: {e}")
        return None, False


def get_notification_preferences(agent):
    """
    Get notification preferences for an agent, creating default preferences if none exist.
    
    Args:
        agent: The agent to get preferences for
        
    Returns:
        NotificationPreference: The agent's notification preferences
    """
    try:
        preferences = NotificationPreference.objects.get(agent=agent)
    except NotificationPreference.DoesNotExist:
        # Create default preferences
        preferences = NotificationPreference.objects.create(
            agent=agent,
            receive_invoice_due_soon=True,
            receive_invoice_overdue=True,
            receive_invoice_payment=True,
            receive_invoice_status_change=True,
            receive_contract_expiration=True,
            receive_rent_increase=True,
            notification_frequency='immediately',
            days_before_due_date=7,
            email_notifications=False
        )
        logger.info(f"Created default notification preferences for agent {agent.id}")
    
    return preferences


def batch_create_notifications(notification_data_list):
    """
    Create multiple notifications efficiently in batch, respecting user preferences for batching.
    
    Args:
        notification_data_list: List of dictionaries containing notification data
                               Each dict should have: agent, title, message, notification_type, related_object
                               
    Returns:
        dict: Summary of notifications created, batched, and skipped
    """
    immediate_count = 0
    batched_count = 0
    skipped_count = 0
    
    for data in notification_data_list:
        try:
            agent = data['agent']
            title = data['title']
            message = data['message']
            notification_type = data['notification_type']
            related_object = data.get('related_object')
            duplicate_threshold = data.get('duplicate_threshold_days', 1)
            
            # Check if notification should be batched based on user preferences
            preferences = get_notification_preferences(agent)
            
            if preferences.notification_frequency == 'immediately':
                # Create notification immediately
                notification, created = create_notification_if_not_exists(
                    agent=agent,
                    title=title,
                    message=message,
                    notification_type=notification_type,
                    related_object=related_object,
                    duplicate_threshold_days=duplicate_threshold
                )
                
                if created:
                    immediate_count += 1
                else:
                    skipped_count += 1
            else:
                # Create batched notification
                batch_notification = create_batched_notification(
                    agent=agent,
                    title=title,
                    message=message,
                    notification_type=notification_type,
                    related_object=related_object,
                    duplicate_threshold_days=duplicate_threshold
                )
                
                if batch_notification:
                    batched_count += 1
                else:
                    skipped_count += 1
                
        except Exception as e:
            logger.error(f"Error in batch notification creation: {e}")
            skipped_count += 1
    
    results = {
        'immediate_notifications': immediate_count,
        'batched_notifications': batched_count,
        'skipped_notifications': skipped_count,
        'total_processed': len(notification_data_list)
    }
    
    logger.info(f"Batch notification creation completed: {results}")
    return results


def create_batched_notification(agent, title, message, notification_type, related_object=None, duplicate_threshold_days=1):
    """
    Create a batched notification that will be delivered according to user preferences.
    
    Args:
        agent: The agent to notify
        title: Notification title
        message: Notification message
        notification_type: Type of notification
        related_object: Related object (optional)
        duplicate_threshold_days: Days to check for duplicates
        
    Returns:
        NotificationBatch: The created batch notification or None if duplicate/error
    """
    from .models import NotificationBatch, NotificationLog
    
    try:
        # Check for duplicates in both regular notifications and batched notifications
        if NotificationLog.has_recent_notification(
            agent=agent,
            notification_type=notification_type,
            related_object=related_object,
            days_threshold=duplicate_threshold_days
        ):
            logger.info(f"Duplicate batched notification prevented for agent {agent.id}, type {notification_type}")
            return None
        
        # Check for existing batched notifications of the same type
        if related_object and _has_recent_batch_notification(agent, notification_type, related_object, duplicate_threshold_days):
            logger.info(f"Duplicate batch notification prevented for agent {agent.id}, type {notification_type}")
            return None
        
        # Create the batched notification
        batch_notification = NotificationBatch.create_batch_notification(
            agent=agent,
            title=title,
            message=message,
            notification_type=notification_type,
            related_object=related_object
        )
        
        if batch_notification:
            # Log the notification creation to prevent duplicates
            NotificationLog.log_notification(
                agent=agent,
                notification_type=notification_type,
                related_object=related_object
            )
            
            logger.info(f"Batched notification created for agent {agent.id}, type {notification_type}, scheduled for {batch_notification.scheduled_for}")
        
        return batch_notification
        
    except Exception as e:
        logger.error(f"Error creating batched notification: {e}")
        return None


def _has_recent_batch_notification(agent, notification_type, related_object, days_threshold):
    """
    Check if a similar batched notification exists recently.
    
    Args:
        agent: The agent to check for
        notification_type: Type of notification
        related_object: The related object
        days_threshold: Number of days to look back
        
    Returns:
        bool: True if a recent batch notification exists
    """
    from .models import NotificationBatch
    from django.contrib.contenttypes.models import ContentType
    
    if not related_object:
        return False
        
    content_type = ContentType.objects.get_for_model(related_object)
    threshold_date = timezone.now() - timedelta(days=days_threshold)
    
    return NotificationBatch.objects.filter(
        agent=agent,
        notification_type=notification_type,
        content_type=content_type,
        object_id=related_object.pk,
        created_at__gte=threshold_date,
        processed=False
    ).exists()


def process_ready_notification_batches():
    """
    Process all notification batches that are ready for delivery.
    
    Returns:
        dict: Summary of batch processing results
    """
    from .models import NotificationBatch
    from collections import defaultdict
    
    try:
        # Get all ready batches grouped by agent and batch type
        ready_batches = NotificationBatch.get_ready_batches()
        
        if not ready_batches.exists():
            logger.info("No notification batches ready for processing")
            return {
                'daily_batches_sent': 0,
                'weekly_batches_sent': 0,
                'total_notifications_batched': 0,
                'agents_notified': 0
            }
        
        # Group batches by agent and batch type
        batches_by_agent = defaultdict(lambda: defaultdict(list))
        for batch in ready_batches:
            batches_by_agent[batch.agent][batch.batch_type].append(batch)
        
        daily_batches_sent = 0
        weekly_batches_sent = 0
        total_notifications = 0
        agents_notified = 0
        
        # Process batches for each agent
        for agent, batch_types in batches_by_agent.items():
            agent_notified = False
            
            for batch_type, batches in batch_types.items():
                if batches:
                    # Create summary notification for this batch
                    summary_notification = _create_batch_summary_notification(agent, batch_type, batches)
                    
                    if summary_notification:
                        # Mark all batches as processed
                        for batch in batches:
                            batch.mark_as_processed()
                        
                        total_notifications += len(batches)
                        agent_notified = True
                        
                        if batch_type == 'daily':
                            daily_batches_sent += 1
                        elif batch_type == 'weekly':
                            weekly_batches_sent += 1
                        
                        logger.info(f"Processed {len(batches)} {batch_type} notifications for agent {agent.id}")
            
            if agent_notified:
                agents_notified += 1
        
        results = {
            'daily_batches_sent': daily_batches_sent,
            'weekly_batches_sent': weekly_batches_sent,
            'total_notifications_batched': total_notifications,
            'agents_notified': agents_notified
        }
        
        logger.info(f"Batch processing completed: {results}")
        return results
        
    except Exception as e:
        logger.error(f"Error processing notification batches: {e}")
        return {
            'daily_batches_sent': 0,
            'weekly_batches_sent': 0,
            'total_notifications_batched': 0,
            'agents_notified': 0,
            'error': str(e)
        }


def _create_batch_summary_notification(agent, batch_type, batches):
    """
    Create a summary notification for a batch of notifications.
    
    Args:
        agent: The agent to notify
        batch_type: Type of batch ('daily' or 'weekly')
        batches: List of NotificationBatch objects
        
    Returns:
        Notification: The created summary notification
    """
    try:
        # Group notifications by type for better summary
        notifications_by_type = defaultdict(list)
        for batch in batches:
            notifications_by_type[batch.notification_type].append(batch)
        
        # Create summary title and message
        batch_count = len(batches)
        type_count = len(notifications_by_type)
        
        if batch_type == 'daily':
            title = f"Resumen Diario de Notificaciones ({batch_count} notificaciones)"
        else:
            title = f"Resumen Semanal de Notificaciones ({batch_count} notificaciones)"
        
        # Build detailed message
        message_parts = [f"Tienes {batch_count} notificaciones pendientes:"]
        
        for notification_type, type_batches in notifications_by_type.items():
            type_count = len(type_batches)
            type_name = _get_notification_type_display_name(notification_type)
            message_parts.append(f"• {type_name}: {type_count}")
            
            # Add details for first few notifications of each type
            for i, batch in enumerate(type_batches[:3]):  # Show first 3 of each type
                message_parts.append(f"  - {batch.title}")
            
            if len(type_batches) > 3:
                remaining = len(type_batches) - 3
                message_parts.append(f"  ... y {remaining} más")
        
        message = "\n".join(message_parts)
        
        # Create the summary notification
        summary_notification = create_notification(
            agent=agent,
            title=title,
            message=message,
            notification_type='batch_summary'
        )
        
        return summary_notification
        
    except Exception as e:
        logger.error(f"Error creating batch summary notification: {e}")
        return None


def _get_notification_type_display_name(notification_type):
    """
    Get display name for notification type.
    
    Args:
        notification_type: The notification type code
        
    Returns:
        str: Human-readable display name
    """
    type_names = {
        'invoice_due_soon': 'Facturas por vencer',
        'invoice_overdue': 'Facturas vencidas',
        'invoice_overdue_urgent': 'Facturas vencidas (urgente)',
        'invoice_overdue_critical': 'Facturas vencidas (crítica)',
        'invoice_payment_received': 'Pagos recibidos',
        'invoice_status_change': 'Cambios de estado de facturas',
        'contract_expired': 'Contratos vencidos',
        'contract_expiring_urgent': 'Contratos por vencer (urgente)',
        'contract_expiring_soon': 'Contratos próximos a vencer',
        'rent_increase_due': 'Aumentos de alquiler pendientes',
        'rent_increase_overdue': 'Aumentos de alquiler vencidos',
        'generic': 'Notificaciones generales',
    }
    
    return type_names.get(notification_type, notification_type.replace('_', ' ').title())


def should_send_notification_by_preference(agent, notification_type):
    """
    Check if a notification should be sent based on agent preferences.
    
    Args:
        agent: The agent to check preferences for
        notification_type: Type of notification to check
        
    Returns:
        bool: True if notification should be sent
    """
    try:
        preferences = get_notification_preferences(agent)
        
        # Map notification types to preference fields
        preference_mapping = {
            'invoice_due_soon': preferences.receive_invoice_due_soon,
            'invoice_overdue': preferences.receive_invoice_overdue,
            'invoice_overdue_urgent': preferences.receive_invoice_overdue,
            'invoice_overdue_critical': preferences.receive_invoice_overdue,
            'invoice_payment_received': preferences.receive_invoice_payment,
            'invoice_status_change': preferences.receive_invoice_status_change,
            'contract_expired': preferences.receive_contract_expiration,
            'contract_expiring_urgent': preferences.receive_contract_expiration,
            'contract_expiring_soon': preferences.receive_contract_expiration,
            'rent_increase_due': preferences.receive_rent_increase,
            'rent_increase_overdue': preferences.receive_rent_increase,
            'generic': True,              # Default to True for generic
        }
        
        return preference_mapping.get(notification_type, True)
        
    except Exception as e:
        logger.error(f"Error checking notification preferences: {e}")
        return True  # Default to sending if there's an error