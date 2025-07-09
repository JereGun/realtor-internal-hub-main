
from django.contrib import admin
from .models import PaymentMethod, ContractPayment


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name',)


@admin.register(ContractPayment)
class ContractPaymentAdmin(admin.ModelAdmin):
    list_display = ('contract', 'amount', 'due_date', 'payment_date', 'status', 'payment_method')
    list_filter = ('status', 'payment_method', 'due_date')
    search_fields = ('contract__property__title', 'contract__customer__first_name', 'receipt_number')
    date_hierarchy = 'due_date'
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('contract', 'payment_method', 'amount')
        }),
        ('Fechas', {
            'fields': ('due_date', 'payment_date')
        }),
        ('Estado y Detalles', {
            'fields': ('status', 'receipt_number', 'notes')
        }),
    )
