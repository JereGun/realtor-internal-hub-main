from django.urls import path
from . import views

app_name = 'user_notifications'

urlpatterns = [
    path('', views.notification_list, name='notification_list'),
    path('<int:pk>/', views.notification_detail, name='notification_detail'),
    path('<int:pk>/mark-as-read/', views.mark_notification_read, name='mark_notification_read'),
    path('mark-all-as-read/', views.mark_all_notifications_read, name='mark_all_notifications_read'),
    path('count/', views.notification_count, name='notification_count'),
    path('preferences/', views.notification_preferences, name='notification_preferences'),
]