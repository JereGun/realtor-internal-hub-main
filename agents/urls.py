
from django.urls import path
from . import views
from .views.auth_views import (
    EnhancedLoginView, enhanced_logout_view, PasswordResetRequestView,
    PasswordResetConfirmView, PasswordResetSentView, change_password_view,
    terminate_session_view, terminate_all_sessions_view
)
from .views.profile_views import (
    ProfileView, ProfileEditView, SecuritySettingsView, SessionManagementView,
    terminate_specific_session_view, terminate_other_sessions_view,
    profile_completion_data
)
from .views.admin_views import (
    AdminUserListView, AdminUserDetailView, AdminAuditLogView,
    admin_user_toggle_status, admin_assign_role, admin_remove_role,
    admin_export_audit_logs, admin_dashboard, admin_terminate_session
)

app_name = 'agents'

urlpatterns = [
    # Autenticación mejorada
    path('login/', EnhancedLoginView.as_view(), name='login'),
    path('logout/', enhanced_logout_view, name='logout'),
    
    # Recuperación de contraseña
    path('password-reset/', PasswordResetRequestView.as_view(), name='password_reset_request'),
    path('password-reset/sent/', PasswordResetSentView.as_view(), name='password_reset_sent'),
    path('password-reset/confirm/<str:token>/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('change-password/', change_password_view, name='change_password'),
    
    # Gestión de sesiones
    path('sessions/terminate/<str:session_key>/', terminate_session_view, name='terminate_session'),
    path('sessions/terminate-all/', terminate_all_sessions_view, name='terminate_all_sessions'),
    
    # Gestión de perfil
    path('profile/view/', ProfileView.as_view(), name='profile_view'),
    path('profile/edit/', ProfileEditView.as_view(), name='profile_edit'),
    path('profile/security/', SecuritySettingsView.as_view(), name='security_settings'),
    path('profile/sessions/', SessionManagementView.as_view(), name='session_management'),
    path('profile/sessions/terminate/<str:session_key>/', terminate_specific_session_view, name='terminate_specific_session'),
    path('profile/sessions/terminate-others/', terminate_other_sessions_view, name='terminate_other_sessions'),
    path('profile/completion-data/', profile_completion_data, name='profile_completion_data'),
    
    # Vistas existentes
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/data/', views.dashboard_data, name='dashboard_data'),
    path('quick-search/', views.quick_search, name='quick_search'),
    path('profile/', views.profile_view, name='profile'),
    path('', views.AgentListView.as_view(), name='agent_list'),
    path('<int:pk>/', views.AgentDetailView.as_view(), name='agent_detail'),
    path('create/', views.AgentCreateView.as_view(), name='agent_create'),
    path('<int:pk>/edit/', views.AgentUpdateView.as_view(), name='agent_edit'),
    
    # URLs legacy para compatibilidad
    path('login-legacy/', views.agent_login, name='login_legacy'),
    path('logout-legacy/', views.agent_logout, name='logout_legacy'),
    
    # Vistas de administración
    path('admin/dashboard/', admin_dashboard, name='admin_dashboard'),
    path('admin/users/', AdminUserListView.as_view(), name='admin_user_list'),
    path('admin/users/<int:pk>/', AdminUserDetailView.as_view(), name='admin_user_detail'),
    path('admin/users/<int:user_id>/toggle-status/', admin_user_toggle_status, name='admin_user_toggle_status'),
    path('admin/users/<int:user_id>/assign-role/', admin_assign_role, name='admin_assign_role'),
    path('admin/users/<int:user_id>/remove-role/<int:role_id>/', admin_remove_role, name='admin_remove_role'),
    path('admin/audit-logs/', AdminAuditLogView.as_view(), name='admin_audit_logs'),
    path('admin/audit-logs/export/', admin_export_audit_logs, name='admin_export_audit_logs'),
    path('admin/sessions/<str:session_key>/terminate/', admin_terminate_session, name='admin_terminate_session'),
]
