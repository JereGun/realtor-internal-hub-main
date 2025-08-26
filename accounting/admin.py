from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.utils import timezone
from django.db import models
from datetime import timedelta
from .models_invoice import Invoice, InvoiceLine, Payment, OwnerReceipt


class ReceiptDateFilter(admin.SimpleListFilter):
    """Custom filter for receipt generation dates"""

    title = "Fecha de Generación"
    parameter_name = "generated_date"

    def lookups(self, request, model_admin):
        return (
            ("today", "Hoy"),
            ("week", "Esta semana"),
            ("month", "Este mes"),
            ("quarter", "Este trimestre"),
            ("year", "Este año"),
        )

    def queryset(self, request, queryset):
        now = timezone.now()

        if self.value() == "today":
            return queryset.filter(generated_at__date=now.date())
        elif self.value() == "week":
            start_week = now - timedelta(days=now.weekday())
            return queryset.filter(
                generated_at__gte=start_week.replace(hour=0, minute=0, second=0)
            )
        elif self.value() == "month":
            return queryset.filter(
                generated_at__year=now.year, generated_at__month=now.month
            )
        elif self.value() == "quarter":
            quarter_start = ((now.month - 1) // 3) * 3 + 1
            return queryset.filter(
                generated_at__year=now.year,
                generated_at__month__gte=quarter_start,
                generated_at__month__lt=quarter_start + 3,
            )
        elif self.value() == "year":
            return queryset.filter(generated_at__year=now.year)

        return queryset


class ReceiptStatusFilter(admin.SimpleListFilter):
    """Custom filter for receipt status with additional options"""

    title = "Estado del Comprobante"
    parameter_name = "receipt_status"

    def lookups(self, request, model_admin):
        return (
            ("generated", "Generado"),
            ("sent", "Enviado"),
            ("failed", "Error en envío"),
            ("pending", "Pendientes de envío"),
            ("with_errors", "Con errores"),
        )

    def queryset(self, request, queryset):
        if self.value() == "pending":
            return queryset.filter(status="generated")
        elif self.value() == "with_errors":
            return queryset.filter(status="failed").exclude(error_message="")
        elif self.value() in ["generated", "sent", "failed"]:
            return queryset.filter(status=self.value())

        return queryset


class PaymentAdmin(admin.ModelAdmin):
    list_display = ("invoice", "date", "amount", "method")
    search_fields = ("invoice__number", "method")
    list_filter = ("date",)


class InvoiceLineInline(admin.TabularInline):
    model = InvoiceLine
    extra = 1


class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("number", "customer", "date", "due_date", "total_amount", "status")
    search_fields = ("number", "customer__full_name", "description")
    list_filter = ("status",)
    inlines = [InvoiceLineInline]
    readonly_fields = ("total_amount",)


class InvoiceLineAdmin(admin.ModelAdmin):
    list_display = ("invoice", "concept", "amount")
    search_fields = ("concept", "invoice__number")
    list_filter = ("invoice",)


class OwnerReceiptAdmin(admin.ModelAdmin):
    list_display = (
        "receipt_number",
        "invoice_link",
        "status_display",
        "generated_at",
        "sent_at",
        "email_sent_to",
        "gross_amount",
        "discount_amount",
        "net_amount",
        "generated_by",
    )
    search_fields = (
        "receipt_number",
        "invoice__number",
        "email_sent_to",
        "invoice__customer__first_name",
        "invoice__customer__last_name",
        "generated_by__first_name",
        "generated_by__last_name",
    )
    list_filter = (
        ReceiptStatusFilter,
        ReceiptDateFilter,
        ("generated_at", admin.DateFieldListFilter),
        ("sent_at", admin.DateFieldListFilter),
        "generated_by",
    )
    readonly_fields = (
        "receipt_number",
        "generated_at",
        "sent_at",
        "gross_amount",
        "discount_percentage",
        "discount_amount",
        "net_amount",
        "pdf_file_path",
    )
    ordering = ["-generated_at"]
    list_per_page = 25
    date_hierarchy = "generated_at"

    fieldsets = (
        (
            "Información del Comprobante",
            {"fields": ("receipt_number", "invoice", "generated_by", "generated_at")},
        ),
        (
            "Estado y Envío",
            {"fields": ("status", "sent_at", "email_sent_to", "error_message")},
        ),
        (
            "Montos Calculados",
            {
                "fields": (
                    "gross_amount",
                    "discount_percentage",
                    "discount_amount",
                    "net_amount",
                ),
                "classes": ("collapse",),
            },
        ),
        ("Archivo", {"fields": ("pdf_file_path",), "classes": ("collapse",)}),
    )

    actions = [
        "mark_as_sent",
        "mark_as_failed",
        "resend_receipts",
        "export_receipt_data",
    ]

    def invoice_link(self, obj):
        """Display invoice as a clickable link"""
        if obj.invoice:
            url = reverse("admin:accounting_invoice_change", args=[obj.invoice.pk])
            return format_html('<a href="{}">{}</a>', url, obj.invoice.number)
        return "-"

    invoice_link.short_description = "Factura"
    invoice_link.admin_order_field = "invoice__number"

    def status_display(self, obj):
        """Display status with color coding"""
        colors = {
            "generated": "#ffc107",  # Yellow
            "sent": "#28a745",  # Green
            "failed": "#dc3545",  # Red
        }
        color = colors.get(obj.status, "#6c757d")
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display(),
        )

    status_display.short_description = "Estado"
    status_display.admin_order_field = "status"

    def mark_as_sent(self, request, queryset):
        """Bulk action to mark receipts as sent"""
        updated = 0
        for receipt in queryset:
            if receipt.status != "sent":
                receipt.mark_as_sent()
                updated += 1

        if updated:
            self.message_user(
                request,
                f"{updated} comprobante(s) marcado(s) como enviado(s).",
                messages.SUCCESS,
            )
        else:
            self.message_user(
                request,
                "No se actualizaron comprobantes (ya estaban marcados como enviados).",
                messages.WARNING,
            )

    mark_as_sent.short_description = "Marcar como enviados"

    def mark_as_failed(self, request, queryset):
        """Bulk action to mark receipts as failed"""
        updated = 0
        for receipt in queryset:
            if receipt.status != "failed":
                receipt.mark_as_failed("Marcado como fallido desde admin")
                updated += 1

        if updated:
            self.message_user(
                request,
                f"{updated} comprobante(s) marcado(s) como fallido(s).",
                messages.SUCCESS,
            )
        else:
            self.message_user(
                request, "No se actualizaron comprobantes.", messages.WARNING
            )

    mark_as_failed.short_description = "Marcar como fallidos"

    def resend_receipts(self, request, queryset):
        """Bulk action to resend receipts"""
        from accounting.services import OwnerReceiptService

        resendable = queryset.filter(status__in=["generated", "failed"])
        count = resendable.count()

        if count == 0:
            self.message_user(
                request,
                "No hay comprobantes que puedan ser reenviados.",
                messages.WARNING,
            )
            return

        service = OwnerReceiptService()
        success_count = 0
        error_count = 0
        errors = []

        for receipt in resendable:
            try:
                service.send_receipt_email(receipt)
                success_count += 1
            except Exception as e:
                error_count += 1
                errors.append(f"Comprobante {receipt.receipt_number}: {str(e)}")
                # Log the error but continue with other receipts
                self.message_user(
                    request,
                    f"Error reenviando comprobante {receipt.receipt_number}: {str(e)}",
                    messages.ERROR,
                )

        if success_count > 0:
            self.message_user(
                request,
                f"{success_count} comprobante(s) reenviado(s) exitosamente.",
                messages.SUCCESS,
            )

        if error_count > 0:
            self.message_user(
                request,
                f"{error_count} comprobante(s) fallaron al reenviar. Revise los logs para más detalles.",
                messages.ERROR,
            )

    resend_receipts.short_description = "Preparar para reenvío"

    def export_receipt_data(self, request, queryset):
        """Bulk action to export receipt data to CSV"""
        import csv
        from django.http import HttpResponse
        from django.utils import timezone

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = (
            f'attachment; filename="comprobantes_propietarios_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        )

        writer = csv.writer(response)

        # Write header
        writer.writerow(
            [
                "Número Comprobante",
                "Número Factura",
                "Estado",
                "Fecha Generación",
                "Fecha Envío",
                "Email Enviado",
                "Monto Bruto",
                "Porcentaje Descuento",
                "Monto Descuento",
                "Monto Neto",
                "Generado Por",
                "Propiedad",
                "Propietario",
                "Mensaje Error",
            ]
        )

        # Write data
        for receipt in queryset.select_related(
            "invoice", "invoice__customer", "generated_by"
        ):
            # Get property and owner info safely
            property_info = receipt.get_property_info()
            owner_info = receipt.get_owner_info()

            writer.writerow(
                [
                    receipt.receipt_number,
                    receipt.invoice.number,
                    receipt.get_status_display(),
                    (
                        receipt.generated_at.strftime("%d/%m/%Y %H:%M")
                        if receipt.generated_at
                        else ""
                    ),
                    (
                        receipt.sent_at.strftime("%d/%m/%Y %H:%M")
                        if receipt.sent_at
                        else ""
                    ),
                    receipt.email_sent_to,
                    receipt.gross_amount,
                    receipt.discount_percentage or "",
                    receipt.discount_amount,
                    receipt.net_amount,
                    str(receipt.generated_by) if receipt.generated_by else "",
                    property_info.get("address", "") if property_info else "",
                    owner_info.get("name", "") if owner_info else "",
                    receipt.error_message,
                ]
            )

        return response

    export_receipt_data.short_description = "Exportar datos de comprobantes"

    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        return (
            super()
            .get_queryset(request)
            .select_related("invoice", "invoice__customer", "generated_by")
        )

    def has_delete_permission(self, request, obj=None):
        """Restrict delete permissions for sent receipts"""
        if obj and obj.status == "sent":
            return False
        return super().has_delete_permission(request, obj)

    def get_readonly_fields(self, request, obj=None):
        """Make certain fields readonly based on receipt status"""
        readonly = list(self.readonly_fields)

        if obj and obj.status == "sent":
            # Make more fields readonly for sent receipts
            readonly.extend(["invoice", "email_sent_to"])

        return readonly

    def get_form(self, request, obj=None, **kwargs):
        """Customize form based on receipt status"""
        form = super().get_form(request, obj, **kwargs)

        if obj and obj.status == "sent":
            # Disable certain fields for sent receipts
            if "status" in form.base_fields:
                form.base_fields["status"].help_text = (
                    "Este comprobante ya fue enviado exitosamente."
                )

        return form

    def save_model(self, request, obj, form, change):
        """Custom save logic for admin"""
        if not change:  # New object
            # Set the user who is creating the receipt
            if hasattr(request.user, "agent_profile"):
                obj.generated_by = request.user.agent_profile

        super().save_model(request, obj, form, change)

    def get_list_display_links(self, request, list_display):
        """Make receipt number and invoice clickable"""
        return ("receipt_number", "invoice_link")

    def changelist_view(self, request, extra_context=None):
        """Add extra context to changelist view"""
        extra_context = extra_context or {}

        # Add summary statistics
        from django.db.models import Count, Sum

        queryset = self.get_queryset(request)

        stats = queryset.aggregate(
            total_receipts=Count("id"),
            total_sent=Count("id", filter=models.Q(status="sent")),
            total_failed=Count("id", filter=models.Q(status="failed")),
            total_pending=Count("id", filter=models.Q(status="generated")),
            total_gross_amount=Sum("gross_amount"),
            total_net_amount=Sum("net_amount"),
        )

        extra_context["receipt_stats"] = stats

        return super().changelist_view(request, extra_context)


admin.site.register(Invoice, InvoiceAdmin)
admin.site.register(InvoiceLine, InvoiceLineAdmin)
admin.site.register(Payment, PaymentAdmin)
admin.site.register(OwnerReceipt, OwnerReceiptAdmin)
