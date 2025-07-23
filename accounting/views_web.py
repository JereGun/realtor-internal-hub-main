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


@login_required
def accounting_dashboard(request):
    # Obtener estadísticas de facturas
    total_invoices = Invoice.objects.count()
    pending_invoices = Invoice.objects.filter(status__in=['validated', 'sent']).count()
    paid_invoices = Invoice.objects.filter(status='paid').count()
    cancelled_invoices = Invoice.objects.filter(status='cancelled').count()
    
    # Calcular totales por estado
    total_pending = Invoice.objects.filter(status__in=['validated', 'sent']).aggregate(
        total=Sum('total_amount'))['total'] or 0
    total_paid = Invoice.objects.filter(status='paid').aggregate(
        total=Sum('total_amount'))['total'] or 0
    
    # Facturas recientes
    recent_invoices = Invoice.objects.select_related('customer').order_by('-date')[:10]
    
    # Pagos recientes
    recent_payments = Payment.objects.select_related('invoice').order_by('-date')[:10]
    
    # Facturas vencidas
    overdue_invoices = Invoice.objects.filter(
        status__in=["validated", "sent"], due_date__lt=timezone.now().date()
    ).select_related("customer").order_by("due_date")
    
    context = {
        'total_invoices': total_invoices,
        'pending_invoices': pending_invoices,
        'paid_invoices': paid_invoices,
        'cancelled_invoices': cancelled_invoices,
        'total_pending': total_pending,
        'total_paid': total_paid,
        'recent_invoices': recent_invoices,
        'recent_payments': recent_payments,
        'overdue_invoices': overdue_invoices,
    }
    
    return render(request, "accounting/accounting_dashboard.html", context)


@login_required
def invoice_list(request):
    invoice_list = Invoice.objects.select_related("customer").order_by("-date")

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
            messages.warning(request, "Formato de fecha de emisión 'desde' incorrecto. Use YYYY-MM-DD.")
    
    # Filtro por fecha de emisión hasta
    date_to = request.GET.get("date_to")
    if date_to:
        try:
            date_to = timezone.datetime.strptime(date_to, "%Y-%m-%d").date()
            invoice_list = invoice_list.filter(date__lte=date_to)
        except ValueError:
            messages.warning(request, "Formato de fecha de emisión 'hasta' incorrecto. Use YYYY-MM-DD.")
    
    # Filtro por fecha de vencimiento desde
    due_date_from = request.GET.get("due_date_from")
    if due_date_from:
        try:
            due_date_from = timezone.datetime.strptime(due_date_from, "%Y-%m-%d").date()
            invoice_list = invoice_list.filter(due_date__gte=due_date_from)
        except ValueError:
            messages.warning(request, "Formato de fecha de vencimiento 'desde' incorrecto. Use YYYY-MM-DD.")
    
    # Filtro por fecha de vencimiento hasta
    due_date_to = request.GET.get("due_date_to")
    if due_date_to:
        try:
            due_date_to = timezone.datetime.strptime(due_date_to, "%Y-%m-%d").date()
            invoice_list = invoice_list.filter(due_date__lte=due_date_to)
        except ValueError:
            messages.warning(request, "Formato de fecha de vencimiento 'hasta' incorrecto. Use YYYY-MM-DD.")
    
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
    customers = Customer.objects.all().order_by('last_name', 'first_name')

    return render(
        request,
        "accounting/invoice_list.html",
        {
            "invoices": invoices,
            "query": query,
            "status": status,
            "customer_id": customer_id,
            "date_from": (
                date_from
                if isinstance(date_from, str)
                else date_from.strftime("%Y-%m-%d") if hasattr(date_from, 'strftime') else ""
            ),
            "date_to": (
                date_to
                if isinstance(date_to, str)
                else date_to.strftime("%Y-%m-%d") if hasattr(date_to, 'strftime') else ""
            ),
            "due_date_from": (
                due_date_from
                if isinstance(due_date_from, str)
                else due_date_from.strftime("%Y-%m-%d") if hasattr(due_date_from, 'strftime') else ""
            ),
            "due_date_to": (
                due_date_to
                if isinstance(due_date_to, str)
                else due_date_to.strftime("%Y-%m-%d") if hasattr(due_date_to, 'strftime') else ""
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
            messages.success(request, "Pago rápido registrado correctamente.")
            return redirect("accounting:invoice_detail", pk=invoice.pk)
        else:
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
                if hasattr(date_from, 'strftime')
                else date_from
            ),
            "date_to": (
                date_to.strftime("%Y-%m-%d")
                if hasattr(date_to, 'strftime')
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
            messages.success(request, "Línea de factura agregada correctamente.")
            return redirect("accounting:invoice_detail", pk=invoice.pk)
        else:
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
            number=f"COPIA-{original_invoice.number}"
        )
        
        # Duplicar las líneas de la factura
        for line in original_invoice.lines.all():
            InvoiceLine.objects.create(
                invoice=new_invoice,
                concept=line.concept,
                amount=line.amount
            )
        
        # Calcular el total
        new_invoice.compute_total()
        
        messages.success(request, "Factura duplicada correctamente. Revise los datos antes de validarla.")
        return redirect("accounting:invoice_update", pk=new_invoice.pk)
    
    # Si es GET, mostrar confirmación
    return render(
        request, "accounting/invoice_confirm_duplicate.html", {"invoice": original_invoice}
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
    invoices = Invoice.objects.filter(
        id__in=invoice_ids,
        status__in=["validated", "sent"]
    ).select_related("customer").filter(
        customer__email__isnull=False
    ).exclude(
        customer__email=""
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
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error al enviar correo para factura {invoice.id}: {str(e)}")
    
    # Mostrar mensajes según los resultados
    if success_count > 0:
        messages.success(request, f"Se enviaron correctamente {success_count} correos electrónicos.")
    
    if error_count > 0:
        messages.error(request, f"Ocurrieron {error_count} errores al enviar correos. Revise el registro para más detalles.")
    
    if no_email_count > 0:
        messages.warning(request, f"{no_email_count} facturas fueron omitidas porque los clientes no tienen correo electrónico.")
    
    if invalid_status_count > 0:
        messages.warning(request, f"{invalid_status_count} facturas fueron omitidas porque no están en estado 'Validada' o 'Enviada'.")
    
    return redirect("accounting:invoice_list")