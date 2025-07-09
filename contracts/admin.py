from django.contrib import admin
from .models import Contract, ContractIncrease, Invoice, InvoiceItem


class ContractIncreaseInline(admin.TabularInline):
    model = ContractIncrease
    extra = 0


@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = ('property', 'customer', 'agent', 'contract_type', 'amount', 'start_date', 'is_active')
    list_filter = ('contract_type', 'is_active', 'agent', 'currency')
    search_fields = ('property__title', 'customer__first_name', 'customer__last_name', 'agent__first_name')
    date_hierarchy = 'start_date'
    inlines = [ContractIncreaseInline]
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('property', 'customer', 'agent', 'contract_type')
        }),
        ('Fechas', {
            'fields': ('start_date', 'end_date')
        }),
        ('Información Financiera', {
            'fields': ('amount', 'currency')
        }),
        ('Detalles Adicionales', {
            'fields': ('terms', 'notes', 'is_active')
        }),
    )


@admin.register(ContractIncrease)
class ContractIncreaseAdmin(admin.ModelAdmin):
    list_display = ('contract', 'previous_amount', 'new_amount', 'increase_percentage', 'effective_date')
    list_filter = ('effective_date', 'contract__contract_type')
    search_fields = ('contract__property__title', 'contract__customer__first_name')
    date_hierarchy = 'effective_date'


class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 0


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('id', 'contract', 'issue_date', 'due_date', 'status', 'total')
    list_filter = ('status', 'issue_date', 'due_date')
    search_fields = ('contract__property__title', 'contract__customer__first_name', 'contract__customer__last_name')
    date_hierarchy = 'issue_date'
    inlines = [InvoiceItemInline]
    readonly_fields = ('total',)


@admin.register(InvoiceItem)
class InvoiceItemAdmin(admin.ModelAdmin):
    list_display = ('invoice', 'description', 'amount')
    search_fields = ('description',)
