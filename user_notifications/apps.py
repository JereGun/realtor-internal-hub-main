
from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'user_notifications'
    
    def ready(self):
        """
        Import signal handlers when the app is ready.
        
        This ensures that signal handlers are connected when Django starts.
        """
        import user_notifications.signals
