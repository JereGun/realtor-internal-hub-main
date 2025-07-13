from .models import TaskNotification

def unread_notifications_count(request):
    if request.user.is_authenticated:
        # Como AUTH_USER_MODEL es 'agents.Agent', request.user ya es una instancia de Agent.
        # La comprobación de is_authenticated ya excluye a AnonymousUser.
        count = TaskNotification.objects.filter(agent=request.user, status='pending').count()
        return {'unread_notifications_count': count}
    return {'unread_notifications_count': 0}
