from django.contrib.contenttypes.models import ContentType
from .models import Notification

def create_notification(agent, title, message, notification_type, related_object=None):
    """
    Creates a new notification.
    """
    content_type = None
    object_id = None
    if related_object:
        content_type = ContentType.objects.get_for_model(related_object)
        object_id = related_object.pk

    Notification.objects.create(
        agent=agent,
        title=title,
        message=message,
        notification_type=notification_type,
        content_type=content_type,
        object_id=object_id,
    )
