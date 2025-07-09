
from django.urls import path
from . import views

app_name = 'agents'

urlpatterns = [
    path('login/', views.agent_login, name='login'),
    path('logout/', views.agent_logout, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('', views.AgentListView.as_view(), name='agent_list'),
    path('<int:pk>/', views.AgentDetailView.as_view(), name='agent_detail'),
    path('create/', views.AgentCreateView.as_view(), name='agent_create'),
    path('<int:pk>/edit/', views.AgentUpdateView.as_view(), name='agent_edit'),
]
