from django.urls import path
from .views import (
    dashboard, 
    company_settings,
    # Vistas de configuración avanzada
    CompanyConfigurationView,
    CompanyBasicInfoView,
    ContactInfoView,
    SystemConfigurationView,
    DocumentTemplateView,
    DocumentTemplateCreateView,
    DocumentTemplateEditView,
    NotificationSettingsView,
    NotificationCreateView,
    NotificationEditView,
    BackupRestoreView,
    # APIs
    template_preview_api,
    template_variables_api,
    create_backup_api,
    restore_backup_api,
    delete_template_api,
    delete_notification_api,
)

app_name = 'core'

urlpatterns = [
    # URLs existentes
    path('dashboard/', dashboard, name='dashboard'),
    path('company-settings/', company_settings, name='company_settings'),
    
    # URLs de configuración avanzada
    path('configuracion/', CompanyConfigurationView.as_view(), name='company_configuration'),
    
    # Secciones de configuración
    path('configuracion/empresa/', CompanyBasicInfoView.as_view(), name='company_basic_info'),
    path('configuracion/contacto/', ContactInfoView.as_view(), name='contact_info'),
    path('configuracion/sistema/', SystemConfigurationView.as_view(), name='system_configuration'),
    
    # Plantillas de documentos
    path('configuracion/plantillas/', DocumentTemplateView.as_view(), name='document_templates'),
    path('configuracion/plantillas/crear/', DocumentTemplateCreateView.as_view(), name='document_template_create'),
    path('configuracion/plantillas/<int:template_id>/editar/', DocumentTemplateEditView.as_view(), name='document_template_edit'),
    
    # Configuración de notificaciones
    path('configuracion/notificaciones/', NotificationSettingsView.as_view(), name='notification_settings'),
    path('configuracion/notificaciones/crear/', NotificationCreateView.as_view(), name='notification_create'),
    path('configuracion/notificaciones/<int:notification_id>/editar/', NotificationEditView.as_view(), name='notification_edit'),
    
    # Respaldo y restauración
    path('configuracion/respaldo/', BackupRestoreView.as_view(), name='backup_restore'),
    
    # APIs para funcionalidades AJAX
    path('api/plantillas/preview/', template_preview_api, name='template_preview_api'),
    path('api/plantillas/variables/', template_variables_api, name='template_variables_api'),
    path('api/plantillas/<int:template_id>/eliminar/', delete_template_api, name='delete_template_api'),
    path('api/notificaciones/<int:notification_id>/eliminar/', delete_notification_api, name='delete_notification_api'),
    path('api/respaldo/crear/', create_backup_api, name='create_backup_api'),
    path('api/respaldo/restaurar/', restore_backup_api, name='restore_backup_api'),
]
