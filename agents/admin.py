
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Agent


@admin.register(Agent)
class AgentAdmin(UserAdmin):
    list_display = ('email', 'first_name', 'last_name', 'license_number', 'commission_rate', 'is_active')
    list_filter = ('is_active', 'commission_rate')
    search_fields = ('email', 'first_name', 'last_name', 'license_number')
    ordering = ('email',)
    
    fieldsets = (
        (None, {'fields': ('username', 'email', 'password')}),
        ('Información Personal', {'fields': ('first_name', 'last_name', 'phone', 'image_path')}),
        ('Información Profesional', {'fields': ('license_number', 'commission_rate')}),
        ('Permisos', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'first_name', 'last_name', 'license_number', 'password1', 'password2'),
        }),
    )
