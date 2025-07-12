from django.contrib import admin
from .models import Contract, ContractIncrease

class ContractIncreaseInline(admin.TabularInline):
    model = ContractIncrease
    extra = 0


@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = ('property', 'customer', 'agent', 'amount', 'start_date', 'is_active', 'frequency', 'increase_percentage', 'next_increase_date')
    list_filter = ('is_active', 'agent', 'currency', 'frequency')
    search_fields = ('property__title', 'customer__first_name', 'customer__last_name', 'agent__first_name')
    date_hierarchy = 'start_date'
    inlines = [ContractIncreaseInline]
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('property', 'customer', 'agent')
        }),
        ('Fechas', {
            'fields': ('start_date', 'end_date')
        }),
        ('Información Financiera', {
            'fields': ('amount', 'currency')
        }),
        ('Aumento Automático de Precios', {
            'fields': ('frequency', 'increase_percentage', 'next_increase_date')
        }),
        ('Detalles Adicionales', {
            'fields': ('terms', 'notes', 'is_active')
        }),
    )


@admin.register(ContractIncrease)
class ContractIncreaseAdmin(admin.ModelAdmin):
    list_display = ('contract', 'previous_amount', 'new_amount', 'increase_percentage', 'effective_date')
    list_filter = ('effective_date',)
    search_fields = ('contract__property__title', 'contract__customer__first_name')
    date_hierarchy = 'effective_date'