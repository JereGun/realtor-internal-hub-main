from django.contrib import admin
from .models import Invoice, InvoiceItem, Payment

class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 1

class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'partner', 'invoice_date', 'invoice_date_due', 'state', 'amount_total')
    list_filter = ('state', 'invoice_date', 'invoice_date_due', 'partner')
    search_fields = ('name', 'partner__full_name')
    inlines = [InvoiceItemInline, PaymentInline]

@admin.register(InvoiceItem)
class InvoiceItemAdmin(admin.ModelAdmin):
    list_display = ('move', 'name', 'quantity', 'price_unit', 'price_subtotal')
    search_fields = ('name',)

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('invoice', 'payment_date', 'amount', 'method')
    list_filter = ('method', 'payment_date')
    search_fields = ('invoice__name', 'method')
