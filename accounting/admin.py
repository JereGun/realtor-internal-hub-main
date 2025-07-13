from django.contrib import admin
from .models_invoice import Invoice, InvoiceLine, Payment

class PaymentAdmin(admin.ModelAdmin):
    list_display = ("invoice", "date", "amount", "method")
    search_fields = ("invoice__number", "method")
    list_filter = ("date",)

class InvoiceLineInline(admin.TabularInline):
    model = InvoiceLine
    extra = 1

class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("number", "customer", "date", "due_date", "total_amount", "state")
    search_fields = ("number", "customer__full_name", "description")
    list_filter = ("state",)
    inlines = [InvoiceLineInline]
    readonly_fields = ("total_amount",)

class InvoiceLineAdmin(admin.ModelAdmin):
    list_display = ("invoice", "concept", "amount")
    search_fields = ("concept", "invoice__number")
    list_filter = ("invoice",)

admin.site.register(Invoice, InvoiceAdmin)
admin.site.register(InvoiceLine, InvoiceLineAdmin)
admin.site.register(Payment, PaymentAdmin)
