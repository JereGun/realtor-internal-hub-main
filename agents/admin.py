from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Agent


@admin.register(Agent)
class AgentAdmin(UserAdmin):
    """
    Configuración del panel de administración para el modelo Agent.
    
    Extiende UserAdmin para proporcionar una interfaz de administración
    personalizada para los agentes inmobiliarios, con campos específicos
    y opciones de visualización adaptadas a las necesidades del negocio.
    """
    list_display = ("email", "first_name", "last_name", "license_number", "is_active")
    list_filter = ("is_active",)
    search_fields = ("email", "first_name", "last_name", "license_number")
    ordering = ("email",)

    fieldsets = (
        (None, {"fields": ("username", "email", "password")}),
        (
            "Información Personal",
            {"fields": ("first_name", "last_name", "phone", "image_path")},
        ),
        ("Información Profesional", {"fields": ("license_number",)}),
        (
            "Permisos",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "username",
                    "email",
                    "first_name",
                    "last_name",
                    "license_number",
                    "password1",
                    "password2",
                ),
            },
        ),
    )
