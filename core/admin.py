from django.contrib import admin
from .models import Company, CompanyConfiguration, SystemConfiguration, DocumentTemplate, NotificationSettings


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'phone', 'tax_id']
    search_fields = ['name', 'email', 'tax_id']


@admin.register(CompanyConfiguration)
class CompanyConfigurationAdmin(admin.ModelAdmin):
    list_display = ['company', 'config_key', 'config_type', 'created_at']
    list_filter = ['config_type', 'company', 'created_at']
    search_fields = ['config_key', 'company__name']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(SystemConfiguration)
class SystemConfigurationAdmin(admin.ModelAdmin):
    list_display = ['company', 'currency', 'timezone', 'language', 'created_at']
    list_filter = ['currency', 'language', 'created_at']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(DocumentTemplate)
class DocumentTemplateAdmin(admin.ModelAdmin):
    list_display = ['template_name', 'template_type', 'company', 'is_active', 'created_at']
    list_filter = ['template_type', 'is_active', 'company', 'created_at']
    search_fields = ['template_name', 'company__name']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(NotificationSettings)
class NotificationSettingsAdmin(admin.ModelAdmin):
    list_display = ['notification_type', 'company', 'is_enabled', 'frequency_days', 'created_at']
    list_filter = ['notification_type', 'is_enabled', 'company', 'created_at']
    search_fields = ['company__name']
    readonly_fields = ['created_at', 'updated_at']