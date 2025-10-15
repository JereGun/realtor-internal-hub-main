from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.contrib import messages
from django.utils import timezone
from django.http import HttpResponse, JsonResponse
from django.template.loader import render_to_string
from django.db.models import Q, Sum
from django.forms import modelform_factory
from weasyprint import HTML
from .models_invoice import Invoice, InvoiceLine, Payment
from .forms_invoice import InvoiceForm, InvoiceLineFormSet, InvoiceLineForm
from .services import send_invoice_email
from core.models import Company
from user_notifications.models import Notification
import logging

logger = logging.getLogger(__name__)


@login_required
def accounting_dashboard(request):
    # Obtener estadísticas de facturas
    total_invoices = Invoice.objects.count()
    pending_invoices = Invoice.objects.filter(status__in=["validated", "sent"]).count()
    paid_invoices = Invoice.objects.filter(status="paid").count()
    cancelled_invoices = Invoice.objects.filter(status="cancelled").count()

    # Calcular totales por estado
    total_pending = (
        Invoice.objects.filter(status__in=["validated", "sent"]).aggregate(
            total=Sum("total_amount")
        )["total"]
        or 0
    )
    total_paid = (
        Invoice.objects.filter(status="paid").aggregate(total=Sum("total_amount"))[
            "total"
        ]
        or 0
    )

    # Facturas recientes
    recent_invoices = Invoice.objects.select_related("customer").order_by("-date")[:10]

    # Pagos recientes
    recent_payments = Payment.objects.select_related("invoice").order_by("-date")[:10]

    # Facturas vencidas
    overdue_invoices = (
        Invoice.objects.filter(
            status__in=["validated", "sent"], due_date__lt=timezone.now().date()
        )
        .select_related("customer")
        .order_by("due_date")
    )

    context = {
        "total_invoices": total_invoices,
        "pending_invoices": pending_invoices,
        "paid_invoices": paid_invoices,
        "cancelled_invoices": cancelled_invoices,
        "total_pending": total_pending,
        "total_paid": total_paid,
        "recent_invoices": recent_invoices,
        "recent_payments": recent_payments,
        "overdue_invoices": overdue_invoices,
    }

    return render(request, "accounting/accounting_dashboard.html", context)


@login_required
def invoice_list(request):
    invoice_list = Invoice.objects.select_related("customer").order_by("-date")
    today = timezone.now().date()

    # Búsqueda
    query = request.GET.get("q")
    if query:
        invoice_list = invoice_list.filter(
            Q(number__icontains=query)
            | Q(customer__first_name__icontains=query)
            | Q(customer__last_name__icontains=query)
        )

    # Filtro por estado
    status = request.GET.get("status")
    if status:
        invoice_list = invoice_list.filter(status=status)

    # Filtro por cliente
    customer_id = request.GET.get("customer")
    if customer_id:
        invoice_list = invoice_list.filter(customer_id=customer_id)

    # Filtro por fecha de emisión desde
    date_from = request.GET.get("date_from")
    if date_from:
        try:
            date_from = timezone.datetime.strptime(date_from, "%Y-%m-%d").date()
            invoice_list = invoice_list.filter(date__gte=date_from)
        except ValueError:
            messages.warning(
                request,
                "Formato de fecha de emisión 'desde' incorrecto. Use YYYY-MM-DD.",
            )

    # Filtro por fecha de emisión hasta
    date_to = request.GET.get("date_to")
    if date_to:
        try:
            date_to = timezone.datetime.strptime(date_to, "%Y-%m-%d").date()
            invoice_list = invoice_list.filter(date__lte=date_to)
        except ValueError:
            messages.warning(
                request,
                "Formato de fecha de emisión 'hasta' incorrecto. Use YYYY-MM-DD.",
            )

    # Filtro por fecha de vencimiento desde
    due_date_from = request.GET.get("due_date_from")
    if due_date_from:
        try:
            due_date_from = timezone.datetime.strptime(due_date_from, "%Y-%m-%d").date()
            invoice_list = invoice_list.filter(due_date__gte=due_date_from)
        except ValueError:
            messages.warning(
                request,
                "Formato de fecha de vencimiento 'desde' incorrecto. Use YYYY-MM-DD.",
            )

    # Filtro por fecha de vencimiento hasta
    due_date_to = request.GET.get("due_date_to")
    if due_date_to:
        try:
            due_date_to = timezone.datetime.strptime(due_date_to, "%Y-%m-%d").date()
            invoice_list = invoice_list.filter(due_date__lte=due_date_to)
        except ValueError:
            messages.warning(
                request,
                "Formato de fecha de vencimiento 'hasta' incorrecto. Use YYYY-MM-DD.",
            )

    # Filtro por monto mínimo
    min_amount = request.GET.get("min_amount")
    if min_amount:
        try:
            min_amount = float(min_amount)
            invoice_list = invoice_list.filter(total_amount__gte=min_amount)
        except ValueError:
            messages.warning(request, "El monto mínimo debe ser un número.")

    # Filtro por monto máximo
    max_amount = request.GET.get("max_amount")
    if max_amount:
        try:
            max_amount = float(max_amount)
            invoice_list = invoice_list.filter(total_amount__lte=max_amount)
        except ValueError:
            messages.warning(request, "El monto máximo debe ser un número.")

    # Filtro por facturas vencidas
    overdue = request.GET.get("overdue")
    if overdue == "yes":
        invoice_list = invoice_list.filter(
            status__in=["validated", "sent"], due_date__lt=timezone.now().date()
        )

    # Filtro por contrato
    contract = request.GET.get("contract")
    if contract:
        if contract == "with_contract":
            invoice_list = invoice_list.filter(contract__isnull=False)
        elif contract == "without_contract":
            invoice_list = invoice_list.filter(contract__isnull=True)

    paginator = Paginator(invoice_list, 25)  # 25 facturas por página
    page_number = request.GET.get("page")
    invoices = paginator.get_page(page_number)

    # Obtener lista de clientes para el filtro
    from customers.models import Customer

    customers = Customer.objects.all().order_by("last_name", "first_name")

    return render(
        request,
        "accounting/invoice_list.html",
        {
            "invoices": invoices,
            "today": today,
            "query": query,
            "status": status,
            "customer_id": customer_id,
            "date_from": (
                date_from
                if isinstance(date_from, str)
                else (
                    date_from.strftime("%Y-%m-%d")
                    if hasattr(date_from, "strftime")
                    else ""
                )
            ),
            "date_to": (
                date_to
                if isinstance(date_to, str)
                else (
                    date_to.strftime("%Y-%m-%d") if hasattr(date_to, "strftime") else ""
                )
            ),
            "due_date_from": (
                due_date_from
                if isinstance(due_date_from, str)
                else (
                    due_date_from.strftime("%Y-%m-%d")
                    if hasattr(due_date_from, "strftime")
                    else ""
                )
            ),
            "due_date_to": (
                due_date_to
                if isinstance(due_date_to, str)
                else (
                    due_date_to.strftime("%Y-%m-%d")
                    if hasattr(due_date_to, "strftime")
                    else ""
                )
            ),
            "min_amount": min_amount,
            "max_amount": max_amount,
            "overdue": overdue,
            "contract": contract,
            "customers": customers,
        },
    )


@login_required
def invoice_detail(request, pk):
    invoice = get_object_or_404(
        Invoice.objects.prefetch_related("lines", "payments"), pk=pk
    )

    # Calcular el total pagado y el saldo pendiente
    total_paid = invoice.payments.aggregate(total=Sum("amount"))["total"] or 0
    balance = invoice.total_amount - total_paid

    if request.method == "POST":
        form = InvoiceLineForm(request.POST)
        if form.is_valid():
            line = form.save(commit=False)
            line.invoice = invoice
            line.save()
            invoice.compute_total()  # Recalcular el total después de agregar una línea
            messages.success(request, "Línea agregada correctamente")
            return redirect("accounting:invoice_detail", pk=invoice.pk)
        else:
            messages.error(request, "Error en el formulario. Revise los datos.")
    else:
        form = InvoiceLineForm()

    # Crear formulario para pago rápido
    QuickPaymentForm = modelform_factory(Payment, fields=("amount", "method"))
    quick_payment_form = QuickPaymentForm(initial={"amount": balance})

    return render(
        request,
        "accounting/invoice_detail.html",
        {
            "invoice": invoice,
            "form": form,
            "lines": invoice.lines.all(),
            "payments": invoice.payments.all().order_by("-date"),
            "total_paid": total_paid,
            "balance": balance,
            "quick_payment_form": quick_payment_form,
        },
    )


@login_required
def invoice_delete(request, pk):
    try:
        # Primero verificamos si la factura existe
        invoice = get_object_or_404(Invoice, pk=pk)

        if request.method == "POST":
            # Eliminamos la factura
            invoice.delete()

            # Si es una petición AJAX, devolvemos éxito
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse({"success": True})

            # Si es una petición normal, redirigimos
            messages.success(request, "Factura eliminada correctamente")
            return redirect("accounting:invoice_list")

        # Si es GET, mostramos el modal de confirmación
        return render(
            request, "accounting/invoice_confirm_delete.html", {"invoice": invoice}
        )
    except Invoice.DoesNotExist:
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse(
                {"success": False, "error": "Factura no encontrada"}, status=404
            )
        else:
            messages.error(request, "Factura no encontrada")
            return redirect("accounting:invoice_list")
    except Exception as e:
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"success": False, "error": str(e)}, status=500)
        else:
            messages.error(request, f"Error al eliminar la factura: {str(e)}")
            return redirect("accounting:invoice_list")


@login_required
def invoice_create(request):
    if request.method == "POST":
        form = InvoiceForm(request.POST)
        formset = InvoiceLineFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            invoice = form.save(commit=False)
            invoice.user = request.user
            invoice.save()
            formset.instance = invoice
            formset.save()
            invoice.compute_total()
            messages.success(request, "Factura creada correctamente")
            return redirect("accounting:invoice_detail", pk=invoice.pk)
        else:
            messages.error(request, "Corrija los errores en el formulario")
    else:
        form = InvoiceForm(
            initial={
                "date": timezone.now().date(),
                "due_date": timezone.now().date() + timezone.timedelta(days=30),
            }
        )
        formset = InvoiceLineFormSet()

    return render(
        request,
        "accounting/invoice_form.html",
        {"form": form, "formset": formset, "invoice": None},
    )


@login_required
def invoice_update(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)

    # Solo no permitir edición de facturas pagadas
    if invoice.status == "paid":
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse(
                {"error": "No se pueden editar facturas pagadas."}, status=403
            )
        else:
            messages.error(request, "No se pueden editar facturas pagadas.")
            return redirect("accounting:invoice_detail", pk=invoice.pk)

    if request.method == "POST":
        form = InvoiceForm(request.POST, instance=invoice)
        formset = InvoiceLineFormSet(request.POST, instance=invoice)
        if form.is_valid() and formset.is_valid():
            # Ya no volvemos a draft las facturas validadas al modificarlas
            # Permitimos la edición manteniendo el estado actual

            form.save()
            formset.save()
            invoice.compute_total()
            messages.success(request, "Factura actualizada correctamente")

            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse(
                    {
                        "success": True,
                        "redirect_url": reverse(
                            "accounting:invoice_detail", kwargs={"pk": invoice.pk}
                        ),
                    }
                )
            else:
                return redirect("accounting:invoice_detail", pk=invoice.pk)
        else:
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse(
                    {
                        "success": False,
                        "error": "Error al actualizar la factura. Revise los datos.",
                    },
                    status=400,
                )
            else:
                messages.error(
                    request, "Error al actualizar la factura. Revise los datos."
                )
    else:
        form = InvoiceForm(instance=invoice)
        formset = InvoiceLineFormSet(instance=invoice)

    return render(
        request,
        "accounting/invoice_form.html",
        {"form": form, "formset": formset, "invoice": invoice},
    )


@login_required
def payment_list(request):
    payments_list = Payment.objects.select_related("invoice").order_by("-date")
    paginator = Paginator(payments_list, 25)
    page_number = request.GET.get("page")
    payments = paginator.get_page(page_number)
    return render(request, "accounting/payment_list.html", {"payments": payments})


@login_required
def payment_detail(request, pk):
    payment = get_object_or_404(Payment, pk=pk)
    return render(request, "accounting/payment_detail.html", {"payment": payment})


@login_required
def payment_create(request, invoice_pk):
    invoice = get_object_or_404(Invoice, pk=invoice_pk)

    # Calcular el saldo pendiente para sugerir como monto predeterminado
    total_paid = invoice.payments.aggregate(total=Sum("amount"))["total"] or 0
    balance = invoice.total_amount - total_paid

    PaymentForm = modelform_factory(
        Payment, fields=("date", "amount", "method", "notes")
    )
    if request.method == "POST":
        form = PaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.invoice = invoice
            payment.save()
            invoice.update_status()
            messages.success(request, "Pago registrado correctamente.")
            return redirect("accounting:invoice_detail", pk=invoice.pk)
        else:
            messages.error(request, "Error al registrar el pago. Revise los datos.")
    else:
        form = PaymentForm(
            initial={
                "date": timezone.now().date(),
                "amount": balance,  # Sugerir el saldo pendiente como monto predeterminado
            }
        )
    return render(
        request,
        "accounting/payment_form.html",
        {"form": form, "invoice": invoice, "balance": balance},
    )


@login_required
def quick_payment_create(request, invoice_pk):
    """Función para registrar pagos rápidos desde la vista de detalle de factura"""
    invoice = get_object_or_404(Invoice, pk=invoice_pk)

    if request.method == "POST":
        QuickPaymentForm = modelform_factory(Payment, fields=("amount", "method"))
        form = QuickPaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.invoice = invoice
            payment.date = timezone.now().date()  # Fecha actual
            payment.save()
            invoice.update_status()

            # Si es una petición AJAX, devolver JSON
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                # Recalcular totales
                total_paid = (
                    invoice.payments.aggregate(total=Sum("amount"))["total"] or 0
                )
                balance = invoice.total_amount - total_paid

                return JsonResponse(
                    {
                        "success": True,
                        "message": "Pago rápido registrado correctamente.",
                        "payment": {
                            "id": payment.pk,
                            "amount": float(payment.amount),
                            "method": payment.method,
                            "date": payment.date.strftime("%d/%m/%Y"),
                        },
                        "total_paid": float(total_paid),
                        "balance": float(balance),
                        "invoice_status": invoice.get_status_display(),
                    }
                )

            messages.success(request, "Pago rápido registrado correctamente.")
            return redirect("accounting:invoice_detail", pk=invoice.pk)
        else:
            # Si es una petición AJAX, devolver errores en JSON
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse(
                    {"success": False, "errors": form.errors}, status=400
                )

            messages.error(
                request, "Error al registrar el pago rápido. Revise los datos."
            )
            return redirect("accounting:invoice_detail", pk=invoice.pk)

    # Si no es POST, redirigir a la vista de detalle
    return redirect("accounting:invoice_detail", pk=invoice.pk)


@login_required
def invoice_notifications(request):
    # Tipos de notificaciones relacionadas con facturas
    notification_types = [
        "invoice_due_soon",
        "invoice_overdue",
        "invoice_payment_received",
        "invoice_status_change",
    ]

    # Filtros
    notification_type = request.GET.get("type")
    read_status = request.GET.get("read_status")
    date_from = request.GET.get("date_from")
    date_to = request.GET.get("date_to")

    # Filtrar notificaciones relacionadas con facturas
    notifications = Notification.objects.filter(
        agent=request.user, notification_type__in=notification_types
    )

    # Aplicar filtros adicionales si se proporcionan
    if notification_type and notification_type != "all":
        notifications = notifications.filter(notification_type=notification_type)

    if read_status:
        if read_status == "read":
            notifications = notifications.filter(is_read=True)
        elif read_status == "unread":
            notifications = notifications.filter(is_read=False)

    if date_from:
        try:
            date_from = timezone.datetime.strptime(date_from, "%Y-%m-%d").date()
            notifications = notifications.filter(created_at__date__gte=date_from)
        except ValueError:
            messages.warning(
                request, "Formato de fecha 'desde' incorrecto. Use YYYY-MM-DD."
            )

    if date_to:
        try:
            date_to = timezone.datetime.strptime(date_to, "%Y-%m-%d").date()
            notifications = notifications.filter(created_at__date__lte=date_to)
        except ValueError:
            messages.warning(
                request, "Formato de fecha 'hasta' incorrecto. Use YYYY-MM-DD."
            )

    # Ordenar por fecha de creación (más recientes primero)
    notifications = notifications.order_by("-created_at")

    # Obtener el número de notificaciones no leídas (total, no solo las filtradas)
    unread_notifications_count = Notification.objects.filter(
        agent=request.user, notification_type__in=notification_types, is_read=False
    ).count()

    # Obtener conteos por tipo para mostrar en los filtros
    notification_counts = {
        "all": Notification.objects.filter(
            agent=request.user, notification_type__in=notification_types
        ).count(),
        "invoice_due_soon": Notification.objects.filter(
            agent=request.user, notification_type="invoice_due_soon"
        ).count(),
        "invoice_overdue": Notification.objects.filter(
            agent=request.user, notification_type="invoice_overdue"
        ).count(),
        "invoice_payment_received": Notification.objects.filter(
            agent=request.user, notification_type="invoice_payment_received"
        ).count(),
        "invoice_status_change": Notification.objects.filter(
            agent=request.user, notification_type="invoice_status_change"
        ).count(),
        "read": Notification.objects.filter(
            agent=request.user, notification_type__in=notification_types, is_read=True
        ).count(),
        "unread": Notification.objects.filter(
            agent=request.user, notification_type__in=notification_types, is_read=False
        ).count(),
    }

    # Paginación
    paginator = Paginator(notifications, 25)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # Preparar opciones para el filtro de tipo de notificación
    notification_type_choices = [
        ("all", "Todas"),
        ("invoice_due_soon", "Vencimiento Próximo"),
        ("invoice_overdue", "Factura Vencida"),
        ("invoice_payment_received", "Pago Recibido"),
        ("invoice_status_change", "Cambio de Estado"),
    ]

    # Preparar opciones para el filtro de estado de lectura
    read_status_choices = [
        ("all", "Todos"),
        ("read", "Leídas"),
        ("unread", "No leídas"),
    ]

    return render(
        request,
        "accounting/invoice_notifications.html",
        {
            "notifications": page_obj,
            "unread_notifications_count": unread_notifications_count,
            "notification_counts": notification_counts,
            "notification_type_choices": notification_type_choices,
            "read_status_choices": read_status_choices,
            "selected_type": notification_type or "all",
            "selected_read_status": read_status or "all",
            "date_from": (
                date_from.strftime("%Y-%m-%d")
                if hasattr(date_from, "strftime")
                else date_from
            ),
            "date_to": (
                date_to.strftime("%Y-%m-%d")
                if hasattr(date_to, "strftime")
                else date_to
            ),
        },
    )


@login_required
def mark_notification_as_read(request, pk):
    notification = get_object_or_404(Notification, pk=pk, agent=request.user)

    if request.method == "POST":
        notification.is_read = True
        notification.save()
        return JsonResponse({"success": True})

    return JsonResponse({"success": False}, status=400)


@login_required
def mark_all_notifications_as_read(request):
    if request.method == "POST":
        # Actualizar todas las notificaciones de facturas no leídas del usuario
        Notification.objects.filter(
            agent=request.user,
            is_read=False,
            notification_type__in=[
                "invoice_due_soon",
                "invoice_overdue",
                "invoice_payment_received",
                "invoice_status_change",
            ],
        ).update(is_read=True)
        return JsonResponse({"success": True})

    return JsonResponse({"success": False}, status=400)


@login_required
def payment_update(request, pk):
    payment = get_object_or_404(Payment, pk=pk)
    invoice = payment.invoice
    PaymentForm = modelform_factory(
        Payment, fields=("date", "amount", "method", "notes")
    )
    if request.method == "POST":
        form = PaymentForm(request.POST, instance=payment)
        if form.is_valid():
            form.save()
            invoice.update_status()
            messages.success(request, "Pago actualizado correctamente.")
            return redirect("accounting:invoice_detail", pk=invoice.pk)
        else:
            messages.error(request, "Error al actualizar el pago. Revise los datos.")
    else:
        form = PaymentForm(instance=payment)
    return render(
        request, "accounting/payment_form.html", {"form": form, "invoice": invoice}
    )


@login_required
def payment_delete(request, pk):
    payment = get_object_or_404(Payment, pk=pk)
    invoice = payment.invoice
    if request.method == "POST":
        payment.delete()
        invoice.update_status()
        messages.success(request, "Pago eliminado correctamente.")
        return redirect("accounting:invoice_detail", pk=invoice.pk)
    return render(
        request, "accounting/payment_confirm_delete.html", {"payment": payment}
    )


@login_required
def invoiceline_create(request, invoice_pk):
    invoice = get_object_or_404(Invoice, pk=invoice_pk)
    InvoiceLineForm = modelform_factory(InvoiceLine, fields=("concept", "amount"))

    if request.method == "POST":
        form = InvoiceLineForm(request.POST)
        if form.is_valid():
            invoiceline = form.save(commit=False)
            invoiceline.invoice = invoice
            invoiceline.save()
            invoice.compute_total()  # Recalcular el total después de agregar una línea

            # Si es una petición AJAX, devolver JSON
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse(
                    {
                        "success": True,
                        "message": "Línea de factura agregada correctamente.",
                        "item": {
                            "id": invoiceline.pk,
                            "concept": invoiceline.concept,
                            "amount": float(invoiceline.amount),
                        },
                        "new_total": float(invoice.total_amount),
                    }
                )

            messages.success(request, "Línea de factura agregada correctamente.")
            return redirect("accounting:invoice_detail", pk=invoice.pk)
        else:
            # Si es una petición AJAX, devolver errores en JSON
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse(
                    {"success": False, "errors": form.errors}, status=400
                )

            messages.error(
                request, "Error al agregar la línea de factura. Revise los datos."
            )
    else:
        form = InvoiceLineForm()

    return render(
        request, "accounting/invoiceline_form.html", {"form": form, "invoice": invoice}
    )


@login_required
def invoiceline_update(request, pk):
    invoiceline = get_object_or_404(InvoiceLine, pk=pk)
    invoice = invoiceline.invoice
    InvoiceLineForm = modelform_factory(InvoiceLine, fields=("concept", "amount"))
    if request.method == "POST":
        form = InvoiceLineForm(request.POST, instance=invoiceline)
        if form.is_valid():
            form.save()
            invoice.compute_total()  # Recalcular el total después de actualizar una línea
            messages.success(request, "Línea de factura actualizada correctamente.")
            return redirect("accounting:invoice_detail", pk=invoice.pk)
        else:
            messages.error(
                request, "Error al actualizar la línea de factura. Revise los datos."
            )
    else:
        form = InvoiceLineForm(instance=invoiceline)
    return render(
        request,
        "accounting/invoiceline_form.html",
        {"form": form, "invoice": invoice},
    )


@login_required
def invoiceline_delete(request, pk):
    invoiceline = get_object_or_404(InvoiceLine, pk=pk)
    invoice = invoiceline.invoice
    if request.method == "POST":
        invoice_pk = invoice.pk
        invoiceline.delete()
        invoice.compute_total()  # Recalcular el total después de eliminar una línea
        messages.success(request, "Línea de factura eliminada correctamente.")
        return redirect("accounting:invoice_detail", pk=invoice_pk)
    return render(
        request,
        "accounting/invoiceline_confirm_delete.html",
        {"invoiceline": invoiceline},
    )


@login_required
def invoice_pdf(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    company = Company.objects.first()
    html_string = render_to_string(
        "accounting/invoice_pdf.html", {"invoice": invoice, "company": company}
    )

    html = HTML(string=html_string, base_url=request.build_absolute_uri())
    pdf = html.write_pdf()

    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename="factura_{invoice.number}.pdf"'
    )
    return response


@login_required
def send_invoice_by_email(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    if invoice.status not in ["validated", "sent"]:
        messages.error(
            request, "Solo se pueden enviar facturas validadas o ya enviadas."
        )
        return redirect("accounting:invoice_detail", pk=pk)

    try:
        send_invoice_email(invoice)
        invoice.mark_as_sent()
        messages.success(request, "Factura enviada por correo electrónico")
    except Exception as e:
        messages.error(request, f"Error al enviar el correo: {str(e)}")
    return redirect("accounting:invoice_detail", pk=pk)


@login_required
def owner_receipt_detail(request, receipt_pk):
    """
    Vista para mostrar los detalles completos de un comprobante específico.
    """
    from .models_invoice import OwnerReceipt
    from .services import OwnerReceiptService

    # Obtener el comprobante con relaciones necesarias
    receipt = get_object_or_404(
        OwnerReceipt.objects.select_related(
            "invoice",
            "invoice__customer",
            "invoice__contract",
            "invoice__contract__property",
            "invoice__contract__property__owner",
            "invoice__contract__agent",
            "generated_by",
        ),
        pk=receipt_pk,
    )

    # Obtener información adicional del comprobante
    service = OwnerReceiptService()

    # Información de la propiedad
    property_info = receipt.get_property_info()

    # Información del propietario
    owner_info = receipt.get_owner_info()

    # Calcular totales de la factura para mostrar balance
    total_paid = receipt.invoice.payments.aggregate(total=Sum("amount"))["total"] or 0
    balance = receipt.invoice.total_amount - total_paid

    # Determinar acciones disponibles según el estado
    can_resend = receipt.can_resend()
    can_download_pdf = True  # Siempre se puede descargar PDF

    # Obtener historial de envíos (si existe)
    send_history = []
    if receipt.sent_at:
        send_history.append(
            {
                "action": "Enviado",
                "date": receipt.sent_at,
                "email": receipt.email_sent_to,
                "status": "success",
            }
        )

    if receipt.status == "failed" and receipt.error_message:
        send_history.append(
            {
                "action": "Error en envío",
                "date": receipt.generated_at,
                "error": receipt.error_message,
                "status": "error",
            }
        )

    context = {
        "receipt": receipt,
        "property_info": property_info,
        "owner_info": owner_info,
        "total_paid": total_paid,
        "balance": balance,
        "can_resend": can_resend,
        "can_download_pdf": can_download_pdf,
        "send_history": send_history,
    }

    return render(request, "accounting/owner_receipt_detail.html", context)


@login_required
def owner_receipts_list(request):
    """
    Vista para mostrar la lista de comprobantes de propietarios con filtros y paginación.
    """
    from .models_invoice import OwnerReceipt

    # Obtener todos los comprobantes con relaciones necesarias
    receipts_list = OwnerReceipt.objects.select_related(
        "invoice",
        "invoice__customer",
        "invoice__contract",
        "invoice__contract__property",
        "generated_by",
    ).order_by("-generated_at")

    # Búsqueda por número de comprobante, propietario o propiedad
    query = request.GET.get("q")
    if query:
        receipts_list = receipts_list.filter(
            Q(receipt_number__icontains=query)
            | Q(invoice__customer__first_name__icontains=query)
            | Q(invoice__customer__last_name__icontains=query)
            | Q(invoice__contract__property__title__icontains=query)
        )

    # Filtro por estado
    status = request.GET.get("status")
    if status:
        receipts_list = receipts_list.filter(status=status)

    # Filtro por fecha de generación desde
    date_from = request.GET.get("date_from")
    if date_from:
        try:
            date_from = timezone.datetime.strptime(date_from, "%Y-%m-%d").date()
            receipts_list = receipts_list.filter(generated_at__date__gte=date_from)
        except ValueError:
            messages.warning(
                request, "Formato de fecha 'desde' incorrecto. Use YYYY-MM-DD."
            )

    # Filtro por fecha de generación hasta
    date_to = request.GET.get("date_to")
    if date_to:
        try:
            date_to = timezone.datetime.strptime(date_to, "%Y-%m-%d").date()
            receipts_list = receipts_list.filter(generated_at__date__lte=date_to)
        except ValueError:
            messages.warning(
                request, "Formato de fecha 'hasta' incorrecto. Use YYYY-MM-DD."
            )

    # Filtro por propietario
    owner_id = request.GET.get("owner")
    if owner_id:
        receipts_list = receipts_list.filter(invoice__customer_id=owner_id)

    # Paginación
    paginator = Paginator(receipts_list, 25)  # 25 comprobantes por página
    page_number = request.GET.get("page")
    receipts = paginator.get_page(page_number)

    # Obtener lista de propietarios para el filtro
    from customers.models import Customer

    owners = (
        Customer.objects.filter(invoices__owner_receipts__isnull=False)
        .distinct()
        .order_by("last_name", "first_name")
    )

    # Estadísticas rápidas
    total_receipts = OwnerReceipt.objects.count()
    sent_receipts = OwnerReceipt.objects.filter(status="sent").count()
    failed_receipts = OwnerReceipt.objects.filter(status="failed").count()
    generated_receipts = OwnerReceipt.objects.filter(status="generated").count()

    context = {
        "receipts": receipts,
        "query": query,
        "status": status,
        "date_from": (
            date_from.strftime("%Y-%m-%d")
            if hasattr(date_from, "strftime")
            else date_from
        ),
        "date_to": (
            date_to.strftime("%Y-%m-%d") if hasattr(date_to, "strftime") else date_to
        ),
        "owner_id": owner_id,
        "owners": owners,
        "total_receipts": total_receipts,
        "sent_receipts": sent_receipts,
        "failed_receipts": failed_receipts,
        "generated_receipts": generated_receipts,
    }

    return render(request, "accounting/owner_receipts_list.html", context)


@login_required
def invoice_cancel(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)

    # Solo no permitir cancelar facturas pagadas o ya canceladas
    if invoice.status == "paid":
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse(
                {"error": "No se pueden cancelar facturas pagadas."}, status=403
            )
        else:
            messages.error(request, "No se pueden cancelar facturas pagadas.")
            return redirect("accounting:invoice_detail", pk=invoice.pk)

    if invoice.status == "cancelled":
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse(
                {"error": "Esta factura ya está cancelada."}, status=403
            )
        else:
            messages.error(request, "Esta factura ya está cancelada.")
            return redirect("accounting:invoice_detail", pk=invoice.pk)

    if request.method == "POST":
        # Ya no verificamos si tiene pagos asociados, permitimos cancelar incluso con pagos

        # Cancelar la factura
        invoice.status = "cancelled"
        invoice.save(update_fields=["status"])

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse(
                {"success": True, "message": "Factura cancelada correctamente"}
            )
        else:
            messages.success(request, "Factura cancelada correctamente")
            return redirect("accounting:invoice_detail", pk=invoice.pk)

    # Si es GET, mostrar confirmación
    return render(
        request, "accounting/invoice_confirm_cancel.html", {"invoice": invoice}
    )


@login_required
def invoice_reactivate(request, pk):
    """Función para reactivar facturas canceladas"""
    invoice = get_object_or_404(Invoice, pk=pk)

    # Solo permitir reactivar facturas canceladas
    if invoice.status != "cancelled":
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse(
                {"error": "Solo se pueden reactivar facturas canceladas."}, status=403
            )
        else:
            messages.error(request, "Solo se pueden reactivar facturas canceladas.")
            return redirect("accounting:invoice_detail", pk=invoice.pk)

    if request.method == "POST":
        # Determinar el estado al que debe volver la factura
        if invoice.payments.exists():
            # Si tiene pagos parciales, marcar como enviada
            invoice.status = "sent"
        else:
            # Si no tiene pagos, volver a estado validado
            invoice.status = "validated"

        invoice.save(update_fields=["status"])

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse(
                {"success": True, "message": "Factura reactivada correctamente"}
            )
        else:
            messages.success(request, "Factura reactivada correctamente")
            return redirect("accounting:invoice_detail", pk=invoice.pk)

    # Si es GET, mostrar confirmación
    return render(
        request, "accounting/invoice_confirm_reactivate.html", {"invoice": invoice}
    )


@login_required
def invoice_validate(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)

    # Solo se pueden validar facturas en borrador
    if invoice.status != "draft":
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse(
                {"error": 'Solo se pueden validar facturas en estado "Borrador".'},
                status=403,
            )
        else:
            messages.error(
                request, 'Solo se pueden validar facturas en estado "Borrador".'
            )
            return redirect("accounting:invoice_detail", pk=invoice.pk)

    if request.method == "POST":
        # Validar que la factura tenga líneas
        if not invoice.lines.exists():
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse(
                    {"error": "No se puede validar una factura sin líneas."}, status=400
                )
            else:
                messages.error(request, "No se puede validar una factura sin líneas.")
                return redirect("accounting:invoice_detail", pk=invoice.pk)

        # Validar la factura
        invoice.status = "validated"
        invoice.save(update_fields=["status"])

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse(
                {"success": True, "message": "Factura validada correctamente"}
            )
        else:
            messages.success(request, "Factura validada correctamente")
            return redirect("accounting:invoice_detail", pk=invoice.pk)

    return JsonResponse({"error": "Método no permitido"}, status=405)


@login_required
def invoice_duplicate(request, pk):
    """Función para duplicar una factura existente"""
    original_invoice = get_object_or_404(Invoice, pk=pk)

    if request.method == "POST":
        # Crear una nueva factura basada en la original
        new_invoice = Invoice.objects.create(
            customer=original_invoice.customer,
            contract=original_invoice.contract,
            description=original_invoice.description,
            date=timezone.now().date(),
            due_date=timezone.now().date() + timezone.timedelta(days=30),
            status="draft",
            user=request.user,
            # Generar un nuevo número de factura
            number=f"COPIA-{original_invoice.number}",
        )

        # Duplicar las líneas de la factura
        for line in original_invoice.lines.all():
            InvoiceLine.objects.create(
                invoice=new_invoice, concept=line.concept, amount=line.amount
            )

        # Calcular el total
        new_invoice.compute_total()

        messages.success(
            request,
            "Factura duplicada correctamente. Revise los datos antes de validarla.",
        )
        return redirect("accounting:invoice_update", pk=new_invoice.pk)

    # Si es GET, mostrar confirmación
    return render(
        request,
        "accounting/invoice_confirm_duplicate.html",
        {"invoice": original_invoice},
    )


@login_required
def send_bulk_emails(request):
    """
    Vista para enviar correos electrónicos de manera masiva a las facturas seleccionadas.
    """
    if request.method != "POST":
        return redirect("accounting:invoice_list")

    # Obtener los IDs de las facturas seleccionadas
    invoice_ids = request.POST.getlist("invoice_ids")

    if not invoice_ids:
        messages.warning(request, "No se seleccionaron facturas para enviar correos.")
        return redirect("accounting:invoice_list")

    # Obtener las facturas seleccionadas que cumplan con los requisitos:
    # 1. El cliente debe tener correo electrónico
    # 2. La factura debe estar en estado "validated" o "sent"
    invoices = (
        Invoice.objects.filter(id__in=invoice_ids, status__in=["validated", "sent"])
        .select_related("customer")
        .filter(customer__email__isnull=False)
        .exclude(customer__email="")
    )

    # Contar facturas procesadas y errores
    success_count = 0
    error_count = 0
    no_email_count = 0
    invalid_status_count = 0

    # Procesar cada factura
    for invoice in invoices:
        try:
            # Verificar si el cliente tiene correo electrónico
            if not invoice.customer.email:
                no_email_count += 1
                continue

            # Verificar si la factura está en un estado válido
            if invoice.status not in ["validated", "sent"]:
                invalid_status_count += 1
                continue

            # Enviar el correo electrónico
            send_invoice_email(invoice)

            # Marcar la factura como enviada si estaba validada
            if invoice.status == "validated":
                invoice.mark_as_sent()

            success_count += 1

        except Exception as e:
            error_count += 1
            # Registrar el error para depuración
            logger.error(f"Error al enviar correo para factura {invoice.id}: {str(e)}")

    # Mostrar mensajes según los resultados
    if success_count > 0:
        messages.success(
            request, f"Se enviaron correctamente {success_count} correos electrónicos."
        )

    if error_count > 0:
        messages.error(
            request,
            f"Ocurrieron {error_count} errores al enviar correos. Revise el registro para más detalles.",
        )

    if no_email_count > 0:
        messages.warning(
            request,
            f"{no_email_count} facturas fueron omitidas porque los clientes no tienen correo electrónico.",
        )

    if invalid_status_count > 0:
        messages.warning(
            request,
            f"{invalid_status_count} facturas fueron omitidas porque no están en estado 'Validada' o 'Enviada'.",
        )

    return redirect("accounting:invoice_list")


# Owner Receipt Views


@login_required
def generate_owner_receipt(request, invoice_pk):
    """
    Genera y opcionalmente envía un comprobante al propietario.

    Maneja tanto la generación como el envío del comprobante en una sola vista.
    Soporta tanto peticiones AJAX como peticiones normales con manejo robusto de errores.
    """
    try:
        invoice = get_object_or_404(Invoice, pk=invoice_pk)
    except Exception as e:
        logger.error(f"Error obteniendo factura {invoice_pk}: {str(e)}")
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse(
                {"success": False, "error": "Factura no encontrada"}, status=404
            )
        else:
            messages.error(request, "Factura no encontrada")
            return redirect("accounting:invoice_list")

    if request.method == "POST":
        try:
            from .services import (
                OwnerReceiptService,
                OwnerReceiptValidationError,
                OwnerReceiptEmailError,
            )

            service = OwnerReceiptService()

            # Verificar si se puede generar el comprobante
            can_generate, error_message = service.can_generate_receipt(invoice)
            if not can_generate:
                logger.warning(
                    f"No se puede generar comprobante para factura {invoice.pk}: {error_message}"
                )
                if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    return JsonResponse(
                        {
                            "success": False,
                            "error": error_message,
                            "error_type": "validation",
                        },
                        status=400,
                    )
                else:
                    messages.error(request, error_message)
                    return redirect("accounting:invoice_detail", pk=invoice.pk)

            # Generar el comprobante
            try:
                receipt = service.generate_receipt(invoice, request.user)
                logger.info(
                    f"Comprobante {receipt.receipt_number} generado exitosamente por usuario {request.user}"
                )
            except OwnerReceiptValidationError as e:
                logger.warning(
                    f"Error de validación generando comprobante para factura {invoice.pk}: {str(e)}"
                )
                if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    return JsonResponse(
                        {"success": False, "error": str(e), "error_type": "validation"},
                        status=400,
                    )
                else:
                    messages.error(request, str(e))
                    return redirect("accounting:invoice_detail", pk=invoice.pk)

            # Verificar si se debe enviar automáticamente
            send_email = request.POST.get("send_email", "true").lower() == "true"

            if send_email:
                try:
                    service.send_receipt_email(receipt)
                    success_message = f"Comprobante {receipt.receipt_number} generado y enviado correctamente a {receipt.email_sent_to}."
                    logger.info(
                        f"Comprobante {receipt.receipt_number} enviado exitosamente"
                    )
                except OwnerReceiptEmailError as e:
                    # Marcar como fallido pero no fallar completamente
                    logger.warning(
                        f"Error enviando comprobante {receipt.receipt_number}: {str(e)}"
                    )
                    success_message = f"Comprobante {receipt.receipt_number} generado correctamente, pero falló el envío por email: {str(e)}"
                except Exception as e:
                    # Error inesperado en envío
                    logger.error(
                        f"Error inesperado enviando comprobante {receipt.receipt_number}: {str(e)}"
                    )
                    try:
                        receipt.mark_as_failed(f"Error inesperado: {str(e)}")
                    except:
                        pass
                    success_message = f"Comprobante {receipt.receipt_number} generado, pero ocurrió un error inesperado en el envío. Puede reenviar desde el detalle del comprobante."
            else:
                success_message = f"Comprobante {receipt.receipt_number} generado correctamente. No se envió por email."

            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse(
                    {
                        "success": True,
                        "message": success_message,
                        "receipt": {
                            "id": receipt.pk,
                            "receipt_number": receipt.receipt_number,
                            "status": receipt.get_status_display(),
                            "generated_at": receipt.generated_at.strftime(
                                "%d/%m/%Y %H:%M"
                            ),
                            "net_amount": float(receipt.net_amount),
                            "email_sent_to": receipt.email_sent_to,
                        },
                    }
                )
            else:
                messages.success(request, success_message)
                return redirect("accounting:invoice_detail", pk=invoice.pk)

        except OwnerReceiptValidationError as e:
            logger.warning(
                f"Error de validación en generación de comprobante para factura {invoice.pk}: {str(e)}"
            )
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse(
                    {"success": False, "error": str(e), "error_type": "validation"},
                    status=400,
                )
            else:
                messages.error(request, str(e))
                return redirect("accounting:invoice_detail", pk=invoice.pk)

        except Exception as e:
            logger.error(
                f"Error inesperado generando comprobante para factura {invoice.pk}: {str(e)}",
                exc_info=True,
            )
            error_message = "Error interno al generar el comprobante. Por favor, contacte al administrador del sistema."
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse(
                    {
                        "success": False,
                        "error": error_message,
                        "error_type": "internal",
                    },
                    status=500,
                )
            else:
                messages.error(request, error_message)
                return redirect("accounting:invoice_detail", pk=invoice.pk)

    # GET request - mostrar formulario de confirmación
    try:
        from .services import OwnerReceiptService, OwnerReceiptValidationError

        service = OwnerReceiptService()

        # Verificar si se puede generar
        can_generate, error_message = service.can_generate_receipt(invoice)
        if not can_generate:
            messages.error(request, error_message)
            return redirect("accounting:invoice_detail", pk=invoice.pk)

        # Obtener datos para preview
        try:
            receipt_data = service.get_receipt_data(invoice)
        except OwnerReceiptValidationError as e:
            messages.error(request, str(e))
            return redirect("accounting:invoice_detail", pk=invoice.pk)
        except Exception as e:
            logger.error(
                f"Error obteniendo datos de preview para factura {invoice.pk}: {str(e)}"
            )
            messages.error(request, "Error obteniendo datos del comprobante")
            return redirect("accounting:invoice_detail", pk=invoice.pk)

        return render(
            request,
            "accounting/generate_owner_receipt.html",
            {
                "invoice": invoice,
                "receipt_data": receipt_data,
                "can_generate": can_generate,
                "error_message": error_message,
            },
        )

    except Exception as e:
        logger.error(
            f"Error inesperado en GET de generación de comprobante para factura {invoice.pk}: {str(e)}",
            exc_info=True,
        )
        messages.error(
            request, "Error interno. Por favor, contacte al administrador del sistema."
        )
        return redirect("accounting:invoice_detail", pk=invoice.pk)


@login_required
def preview_owner_receipt(request, invoice_pk):
    """
    Previsualiza el comprobante antes de generar.

    Muestra cálculos y información que se incluirá en el comprobante
    usando OwnerReceiptService.get_receipt_data() sin generar el comprobante.
    """
    try:
        invoice = get_object_or_404(Invoice, pk=invoice_pk)
    except Exception as e:
        logger.error(f"Error obteniendo factura {invoice_pk} para preview: {str(e)}")
        messages.error(request, "Factura no encontrada")
        return redirect("accounting:invoice_list")

    try:
        from .services import OwnerReceiptService, OwnerReceiptValidationError

        service = OwnerReceiptService()

        # Verificar si se puede generar
        can_generate, error_message = service.can_generate_receipt(invoice)
        if not can_generate:
            logger.warning(
                f"No se puede previsualizar comprobante para factura {invoice.pk}: {error_message}"
            )
            messages.error(request, error_message)
            return redirect("accounting:invoice_detail", pk=invoice.pk)

        # Obtener datos del comprobante sin generarlo
        try:
            receipt_data = service.get_receipt_data(invoice)
        except OwnerReceiptValidationError as e:
            logger.warning(
                f"Error de validación obteniendo datos para preview de factura {invoice.pk}: {str(e)}"
            )
            messages.error(request, str(e))
            return redirect("accounting:invoice_detail", pk=invoice.pk)

        # Agregar información adicional para la previsualización
        receipt_data["preview_info"] = {
            "number": f"PREVIEW-{invoice.number}",
            "generated_at": timezone.now(),
            "generated_by": (
                request.user.get_full_name()
                if hasattr(request.user, "get_full_name")
                else str(request.user)
            ),
            "status": "Vista Previa",
        }

        # Obtener información de la empresa
        try:
            from core.models import Company

            company = Company.objects.first()
        except Exception as e:
            logger.warning(
                f"Error obteniendo información de la empresa para preview: {str(e)}"
            )
            company = None

        context = {
            "invoice": invoice,
            "receipt_data": receipt_data,
            "company": company,
            "preview": True,
        }

        logger.info(
            f"Preview de comprobante mostrado exitosamente para factura {invoice.pk}"
        )
        return render(request, "accounting/preview_owner_receipt.html", context)

    except OwnerReceiptValidationError as e:
        logger.warning(
            f"Error de validación en preview para factura {invoice.pk}: {str(e)}"
        )
        messages.error(request, str(e))
        return redirect("accounting:invoice_detail", pk=invoice.pk)

    except Exception as e:
        logger.error(
            f"Error inesperado generando preview para factura {invoice.pk}: {str(e)}",
            exc_info=True,
        )
        messages.error(
            request,
            "Error interno generando la previsualización. Por favor, contacte al administrador del sistema.",
        )
        return redirect("accounting:invoice_detail", pk=invoice.pk)


@login_required
def owner_receipt_detail(request, receipt_pk):
    """
    Muestra detalles de un comprobante generado.

    Permite ver la información completa del comprobante y acciones como reenvío.
    """
    from .models_invoice import OwnerReceipt

    receipt = get_object_or_404(
        OwnerReceipt.objects.select_related(
            "invoice",
            "invoice__customer",
            "invoice__contract",
            "invoice__contract__property",
            "generated_by",
        ),
        pk=receipt_pk,
    )

    # Verificar permisos - solo el usuario que generó o admin puede ver
    if not (request.user.is_staff or receipt.generated_by == request.user):
        messages.error(request, "No tiene permisos para ver este comprobante.")
        return redirect("accounting:invoice_list")

    context = {
        "receipt": receipt,
        "invoice": receipt.invoice,
        "can_resend": receipt.can_resend(),
        "property_info": receipt.get_property_info(),
        "owner_info": receipt.get_owner_info(),
    }

    return render(request, "accounting/owner_receipt_detail.html", context)


@login_required
def resend_owner_receipt(request, receipt_pk):
    """
    Reenvía un comprobante existente.

    Permite reenviar comprobantes que fallaron o que necesitan ser enviados nuevamente.
    """
    from .models_invoice import OwnerReceipt

    try:
        receipt = get_object_or_404(
            OwnerReceipt.objects.select_related(
                "invoice",
                "invoice__customer",
                "invoice__contract",
                "invoice__contract__property",
                "generated_by",
            ),
            pk=receipt_pk,
        )
    except Exception as e:
        logger.error(
            f"Error obteniendo comprobante {receipt_pk} para reenvío: {str(e)}"
        )
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse(
                {"success": False, "error": "Comprobante no encontrado"}, status=404
            )
        else:
            messages.error(request, "Comprobante no encontrado")
            return redirect("accounting:owner_receipts_list")

    # Verificar permisos
    if not (request.user.is_staff or receipt.generated_by == request.user):
        logger.warning(
            f"Usuario {request.user} intentó reenviar comprobante {receipt.pk} sin permisos"
        )
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse(
                {
                    "success": False,
                    "error": "No tiene permisos para reenviar este comprobante.",
                    "error_type": "permission",
                },
                status=403,
            )
        else:
            messages.error(request, "No tiene permisos para reenviar este comprobante.")
            return redirect("accounting:owner_receipts_list")

    if request.method == "POST":
        try:
            # Verificar si se puede reenviar
            if not receipt.can_resend():
                current_status = (
                    receipt.get_status_display()
                    if hasattr(receipt, "get_status_display")
                    else receipt.status
                )
                error_message = f"Este comprobante no puede ser reenviado. Estado actual: {current_status}"
                logger.warning(
                    f"Intento de reenvío de comprobante {receipt.pk} en estado no válido: {receipt.status}"
                )

                if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    return JsonResponse(
                        {
                            "success": False,
                            "error": error_message,
                            "error_type": "validation",
                        },
                        status=400,
                    )
                else:
                    messages.error(request, error_message)
                    return redirect("accounting:owner_receipt_detail", pk=receipt.pk)

            # Reenviar el comprobante
            try:
                from .services import OwnerReceiptService, OwnerReceiptEmailError

                service = OwnerReceiptService()
                service.resend_receipt_email(receipt)

                success_message = f"Comprobante {receipt.receipt_number} reenviado correctamente a {receipt.email_sent_to}."
                logger.info(
                    f"Comprobante {receipt.receipt_number} reenviado exitosamente por usuario {request.user}"
                )

                if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    return JsonResponse(
                        {
                            "success": True,
                            "message": success_message,
                            "receipt": {
                                "status": receipt.get_status_display(),
                                "sent_at": (
                                    receipt.sent_at.strftime("%d/%m/%Y %H:%M")
                                    if receipt.sent_at
                                    else None
                                ),
                                "email_sent_to": receipt.email_sent_to,
                            },
                        }
                    )
                else:
                    messages.success(request, success_message)
                    return redirect("accounting:owner_receipt_detail", pk=receipt.pk)

            except OwnerReceiptEmailError as e:
                logger.warning(
                    f"Error de email reenviando comprobante {receipt.pk}: {str(e)}"
                )
                error_message = f"Error al reenviar el comprobante: {str(e)}"

                if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    return JsonResponse(
                        {
                            "success": False,
                            "error": error_message,
                            "error_type": "email",
                        },
                        status=400,
                    )
                else:
                    messages.error(request, error_message)
                    return redirect("accounting:owner_receipt_detail", pk=receipt.pk)

        except Exception as e:
            logger.error(
                f"Error inesperado reenviando comprobante {receipt.pk}: {str(e)}",
                exc_info=True,
            )

            # Marcar como fallido si es posible
            try:
                receipt.mark_as_failed(f"Error inesperado: {str(e)}")
            except Exception as mark_error:
                logger.error(
                    f"Error marcando comprobante {receipt.pk} como fallido: {str(mark_error)}"
                )

            error_message = "Error interno al reenviar el comprobante. Por favor, contacte al administrador del sistema."

            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse(
                    {
                        "success": False,
                        "error": error_message,
                        "error_type": "internal",
                    },
                    status=500,
                )
            else:
                messages.error(request, error_message)
                return redirect("accounting:owner_receipt_detail", pk=receipt.pk)

    # GET request - mostrar confirmación
    try:
        # Verificar que el comprobante sigue siendo válido para reenvío
        can_resend = receipt.can_resend()

        # Obtener información adicional para mostrar en la confirmación
        context = {
            "receipt": receipt,
            "can_resend": can_resend,
            "invoice": receipt.invoice,
            "property_info": (
                receipt.get_property_info()
                if hasattr(receipt, "get_property_info")
                else None
            ),
            "owner_info": (
                receipt.get_owner_info() if hasattr(receipt, "get_owner_info") else None
            ),
        }

        return render(request, "accounting/resend_owner_receipt.html", context)

    except Exception as e:
        logger.error(
            f"Error preparando página de confirmación de reenvío para comprobante {receipt.pk}: {str(e)}"
        )
        messages.error(
            request, "Error interno. Por favor, contacte al administrador del sistema."
        )
        return redirect("accounting:owner_receipt_detail", pk=receipt.pk)


@login_required
def owner_receipts_list(request):
    """
    Lista todos los comprobantes generados con filtros y paginación.

    Permite filtrar por estado, fecha, factura y buscar por número de comprobante.
    """
    from .models_invoice import OwnerReceipt

    # Obtener todos los comprobantes con relaciones
    receipts_list = OwnerReceipt.objects.select_related(
        "invoice",
        "invoice__customer",
        "invoice__contract",
        "invoice__contract__property",
        "generated_by",
    ).order_by("-generated_at")

    # Filtros

    # Búsqueda por número de comprobante o factura
    query = request.GET.get("q")
    if query:
        receipts_list = receipts_list.filter(
            Q(receipt_number__icontains=query)
            | Q(invoice__number__icontains=query)
            | Q(invoice__customer__first_name__icontains=query)
            | Q(invoice__customer__last_name__icontains=query)
        )

    # Filtro por estado
    status = request.GET.get("status")
    if status:
        receipts_list = receipts_list.filter(status=status)

    # Filtro por fecha de generación desde
    date_from = request.GET.get("date_from")
    if date_from:
        try:
            date_from = timezone.datetime.strptime(date_from, "%Y-%m-%d").date()
            receipts_list = receipts_list.filter(generated_at__date__gte=date_from)
        except ValueError:
            messages.warning(
                request, "Formato de fecha 'desde' incorrecto. Use YYYY-MM-DD."
            )

    # Filtro por fecha de generación hasta
    date_to = request.GET.get("date_to")
    if date_to:
        try:
            date_to = timezone.datetime.strptime(date_to, "%Y-%m-%d").date()
            receipts_list = receipts_list.filter(generated_at__date__lte=date_to)
        except ValueError:
            messages.warning(
                request, "Formato de fecha 'hasta' incorrecto. Use YYYY-MM-DD."
            )

    # Filtro por usuario que generó
    generated_by = request.GET.get("generated_by")
    if generated_by:
        receipts_list = receipts_list.filter(generated_by_id=generated_by)

    # Filtro por monto mínimo
    min_amount = request.GET.get("min_amount")
    if min_amount:
        try:
            min_amount = float(min_amount)
            receipts_list = receipts_list.filter(net_amount__gte=min_amount)
        except ValueError:
            messages.warning(request, "El monto mínimo debe ser un número.")

    # Filtro por monto máximo
    max_amount = request.GET.get("max_amount")
    if max_amount:
        try:
            max_amount = float(max_amount)
            receipts_list = receipts_list.filter(net_amount__lte=max_amount)
        except ValueError:
            messages.warning(request, "El monto máximo debe ser un número.")

    # Filtro por facturas con errores
    has_errors = request.GET.get("has_errors")
    if has_errors == "yes":
        receipts_list = receipts_list.filter(status="failed")
    elif has_errors == "no":
        receipts_list = receipts_list.exclude(status="failed")

    # Paginación
    paginator = Paginator(receipts_list, 25)  # 25 comprobantes por página
    page_number = request.GET.get("page")
    receipts = paginator.get_page(page_number)

    # Obtener lista de usuarios para el filtro
    from agents.models import Agent

    agents = Agent.objects.filter(
        id__in=OwnerReceipt.objects.values_list("generated_by", flat=True).distinct()
    ).order_by("first_name", "last_name")

    # Estadísticas para mostrar en la vista
    total_receipts = OwnerReceipt.objects.count()
    sent_receipts = OwnerReceipt.objects.filter(status="sent").count()
    failed_receipts = OwnerReceipt.objects.filter(status="failed").count()
    pending_receipts = OwnerReceipt.objects.filter(status="generated").count()

    context = {
        "receipts": receipts,
        "query": query,
        "status": status,
        "date_from": (
            date_from.strftime("%Y-%m-%d")
            if hasattr(date_from, "strftime")
            else date_from
        ),
        "date_to": (
            date_to.strftime("%Y-%m-%d") if hasattr(date_to, "strftime") else date_to
        ),
        "generated_by": generated_by,
        "min_amount": min_amount,
        "max_amount": max_amount,
        "has_errors": has_errors,
        "agents": agents,
        "total_receipts": total_receipts,
        "sent_receipts": sent_receipts,
        "failed_receipts": failed_receipts,
        "pending_receipts": pending_receipts,
        "status_choices": OwnerReceipt.STATUS_CHOICES,
    }

    return render(request, "accounting/owner_receipts_list.html", context)


@login_required
def owner_receipt_pdf(request, receipt_pk):
    """
    Genera y descarga el PDF de un comprobante existente.

    Permite descargar el PDF de un comprobante ya generado.
    """
    from .models_invoice import OwnerReceipt
    from .services import OwnerReceiptService, OwnerReceiptPDFError

    receipt = get_object_or_404(OwnerReceipt, pk=receipt_pk)

    # Verificar permisos
    if not (request.user.is_staff or receipt.generated_by == request.user):
        messages.error(request, "No tiene permisos para descargar este comprobante.")
        return redirect("accounting:invoice_list")

    try:
        service = OwnerReceiptService()

        # Generar PDF
        pdf_content = service.generate_pdf(receipt)

        response = HttpResponse(pdf_content, content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="comprobante_{receipt.receipt_number}.pdf"'
        )
        return response

    except OwnerReceiptPDFError as e:
        logger.error(f"Error de PDF para comprobante {receipt_pk}: {str(e)}")
        messages.error(request, f"Error al generar el PDF: {str(e)}")
        return redirect("accounting:owner_receipt_detail", pk=receipt.pk)
    except Exception as e:
        logger.error(
            f"Error inesperado generando PDF para comprobante {receipt_pk}: {str(e)}",
            exc_info=True,
        )
        messages.error(
            request,
            "Error interno al generar el PDF. Por favor, contacte al administrador del sistema.",
        )
        return redirect("accounting:owner_receipt_detail", pk=receipt.pk)
