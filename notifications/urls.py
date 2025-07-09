
from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('', views.TaskNotificationListView.as_view(), name='task_list'),
    path('<int:pk>/', views.TaskNotificationDetailView.as_view(), name='task_detail'),
    path('create/', views.TaskNotificationCreateView.as_view(), name='task_create'),
    path('<int:pk>/edit/', views.TaskNotificationUpdateView.as_view(), name='task_edit'),
    path('<int:pk>/delete/', views.TaskNotificationDeleteView.as_view(), name='task_delete'),
]
