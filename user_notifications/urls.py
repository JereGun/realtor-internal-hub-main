from django.urls import path
from . import views

app_name = 'user_notifications'

urlpatterns = [
    path('', views.NotificationListView.as_view(), name='notification_list'),
    path('<int:pk>/mark-as-read/', views.MarkAsReadView.as_view(), name='mark_as_read'),
    path('mark-all-as-read/', views.MarkAllAsReadView.as_view(), name='mark_all_as_read'),
]
