
from django.contrib import admin
from .models import Customer


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'email', 'phone', 'document', 'locality', 'created_at')
    list_filter = ('province', 'locality', 'profession')
    search_fields = ('first_name', 'last_name', 'email', 'document', 'phone')
    
    fieldsets = (
        ('Información Personal', {
            'fields': ('first_name', 'last_name', 'email', 'phone', 'document', 'birth_date', 'profession')
        }),
        ('Dirección', {
            'fields': ('street', 'number', 'neighborhood', 'locality', 'province', 'country')
        }),
        ('Información Adicional', {
            'fields': ('notes',)
        }),
    )
