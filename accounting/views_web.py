from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.contrib import messages
from django.utils import timezone
from django.http import HttpResponse, JsonResponse
from django.template.loader import render_to_string
from django.db.models import Q
from .models_invoice import Invoice, InvoiceLine, Payment
from .forms_invoice import InvoiceForm, InvoiceLineFormSet, InvoiceLineForm
from .services import send_invoice_email

@login_required
def accounting_dashboard(request):
    # Logica de gastos
    return render(request, 'accounting/accounting_dashboard.html')

@login_required
def invoice_list(request):
    invoice_list = Invoice.objects.select_related('customer').order_by('-date')
    
    # Búsqueda
    query = request.GET.get('q')
    if query:
        invoice_list = invoice_list.filter(
            Q(number__icontains=query) |
            Q(customer__first_name__icontains=query) |
            Q(customer__last_name__icontains=query)
        )

    # Filtro por estado
    status = request.GET.get('status')
    if status:
        invoice_list = invoice_list.filter(status=status)

    paginator = Paginator(invoice_list, 25)  # 25 facturas por página
    page_number = request.GET.get('page')
    invoices = paginator.get_page(page_number)
    
    return render(request, 'accounting/invoice_list.html', {
        'invoices': invoices,
        'query': query,
        'status': status
    })

@login_required
def invoice_detail(request, pk):
    invoice = get_object_or_404(Invoice.objects.prefetch_related('lines'), pk=pk)
    
    if request.method == 'POST':
        form = InvoiceLineForm(request.POST)
        if form.is_valid():
            line = form.save(commit=False)
            line.invoice = invoice
            line.save()
            messages.success(request, 'Línea agregada correctamente')
            return redirect('accounting:invoice_detail', pk=invoice.pk)
        else:
            messages.error(request, 'Error en el formulario. Revise los datos.')
    else:
        form = InvoiceLineForm()
    
    return render(request, 'accounting/invoice_detail.html', {
        'invoice': invoice, 
        'form': form,
        'lines': invoice.lines.all()
    })

@login_required
def invoice_delete(request, pk):
    try:
        # Primero verificamos si la factura existe
        invoice = get_object_or_404(Invoice, pk=pk)
        
        if request.method == 'POST':
            # Eliminamos la factura
            invoice.delete()
            
            # Si es una petición AJAX, devolvemos éxito
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True})
            
            # Si es una petición normal, redirigimos
            messages.success(request, 'Factura eliminada correctamente')
            return redirect('accounting:invoice_list')
        
        # Si es GET, mostramos el modal de confirmación
        return render(request, 'accounting/invoice_confirm_delete.html', {'invoice': invoice})
    except Invoice.DoesNotExist:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'Factura no encontrada'}, status=404)
        else:
            messages.error(request, 'Factura no encontrada')
            return redirect('accounting:invoice_list')
    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
        else:
            messages.error(request, f'Error al eliminar la factura: {str(e)}')
            return redirect('accounting:invoice_list')

@login_required
def invoice_create(request):
    if request.method == 'POST':
        form = InvoiceForm(request.POST)
        formset = InvoiceLineFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            invoice = form.save(commit=False)
            invoice.user = request.user
            invoice.save()
            formset.instance = invoice
            formset.save()
            invoice.compute_total()
            messages.success(request, 'Factura creada correctamente')
            return redirect('accounting:invoice_detail', pk=invoice.pk)
        else:
            messages.error(request, 'Corrija los errores en el formulario')
    else:
        form = InvoiceForm(initial={
            'date': timezone.now().date(),
            'due_date': timezone.now().date() + timezone.timedelta(days=30)
        })
        formset = InvoiceLineFormSet()
    
    return render(request, 'accounting/invoice_form.html', {
        'form': form,
        'formset': formset,
        'invoice': None
    })

@login_required
def invoice_update(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)

    if invoice.status != 'draft':
        return JsonResponse({'error': 'Solo se pueden editar facturas en estado "Borrador".'}, status=403)
    
    if request.method == 'POST':
        form = InvoiceForm(request.POST, instance=invoice)
        formset = InvoiceLineFormSet(request.POST, instance=invoice)
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            invoice.compute_total()
            messages.success(request, 'Factura actualizada correctamente')
            return JsonResponse({'success': True, 'redirect_url': reverse('accounting:invoice_detail', kwargs={'pk': invoice.pk})})
        else:
            messages.error(request, 'Error al actualizar la factura. Revise los datos.')
    else:
        form = InvoiceForm(instance=invoice)
        formset = InvoiceLineFormSet(instance=invoice)
    
    return render(request, 'accounting/invoice_form.html', {
        'form': form,
        'formset': formset,
        'invoice': invoice
    })

@login_required
def payment_list(request):
    payments_list = Payment.objects.select_related('invoice').order_by('-date')
    paginator = Paginator(payments_list, 25)
    page_number = request.GET.get('page')
    payments = paginator.get_page(page_number)
    return render(request, 'accounting/payment_list.html', {'payments': payments})

@login_required
def payment_detail(request, pk):
    payment = get_object_or_404(Payment, pk=pk)
    return render(request, 'accounting/payment_detail.html', {'payment': payment})

@login_required
def payment_create(request, invoice_pk):
    invoice = get_object_or_404(Invoice, pk=invoice_pk)
    PaymentForm = modelform_factory(Payment, fields=('date', 'amount', 'method', 'notes'))
    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.invoice = invoice
            payment.save()
            invoice.update_status()
            messages.success(request, 'Pago registrado correctamente.')
            return redirect('accounting:invoice_detail', pk=invoice.pk)
        else:
            messages.error(request, 'Error al registrar el pago. Revise los datos.')
    else:
        form = PaymentForm(initial={'date': timezone.now().date()})
    return render(request, 'accounting/payment_form.html', {'form': form, 'invoice': invoice})


@login_required
@login_required
def invoice_notifications(request):
    notifications = InvoiceNotification.objects.filter(
        customer__agent=request.user
    ).order_by('-created_at')
    
    # Obtener el número de notificaciones no leídas
    unread_notifications_count = notifications.filter(is_read=False).count()
    
    paginator = Paginator(notifications, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'accounting/invoice_notifications.html', {
        'notifications': page_obj,
        'unread_notifications_count': unread_notifications_count
    })

@login_required
def mark_notification_as_read(request, pk):
    notification = get_object_or_404(InvoiceNotification, pk=pk)
    
    if request.method == 'POST':
        notification.is_read = True
        notification.save()
        return JsonResponse({'success': True})
    
    return JsonResponse({'success': False}, status=400)

@login_required
def mark_all_notifications_as_read(request):
    if request.method == 'POST':
        notifications = InvoiceNotification.objects.filter(
            customer__agent=request.user,
            is_read=False
        )
        notifications.update(is_read=True)
        return JsonResponse({'success': True})
    
    return JsonResponse({'success': False}, status=400)

@login_required
def payment_update(request, pk):
    payment = get_object_or_404(Payment, pk=pk)
    invoice = payment.invoice
    PaymentForm = modelform_factory(Payment, fields=('date', 'amount', 'method', 'notes'))
    if request.method == 'POST':
        form = PaymentForm(request.POST, instance=payment)
        if form.is_valid():
            form.save()
            invoice.update_status()
            messages.success(request, 'Pago actualizado correctamente.')
            return redirect('accounting:invoice_detail', pk=invoice.pk)
        else:
            messages.error(request, 'Error al actualizar el pago. Revise los datos.')
    else:
        form = PaymentForm(instance=payment)
    return render(request, 'accounting/payment_form.html', {'form': form, 'invoice': invoice})


@login_required
def payment_delete(request, pk):
    payment = get_object_or_404(Payment, pk=pk)
    invoice = payment.invoice
    if request.method == 'POST':
        payment.delete()
        invoice.update_status()
        messages.success(request, 'Pago eliminado correctamente.')
        return redirect('accounting:invoice_detail', pk=invoice.pk)
    return render(request, 'accounting/payment_confirm_delete.html', {'payment': payment})

@login_required
def invoiceline_create(request, invoice_pk):
    invoice = get_object_or_404(Invoice, pk=invoice_pk)
    InvoiceLineForm = modelform_factory(InvoiceLine, fields=('concept', 'amount'))
    if request.method == 'POST':
        form = InvoiceLineForm(request.POST)
        if form.is_valid():
            invoiceline = form.save(commit=False)
            invoiceline.invoice = invoice
            invoiceline.save()
            messages.success(request, 'Línea de factura agregada correctamente.')
            return redirect('accounting:invoice_detail', pk=invoice.pk)
        else:
            messages.error(request, 'Error al agregar la línea de factura. Revise los datos.')
    else:
        form = InvoiceLineForm()
    return render(request, 'accounting/invoiceline_form.html', {'form': form, 'invoice': invoice})

@login_required
def invoiceline_update(request, pk):
    invoiceline = get_object_or_404(InvoiceLine, pk=pk)
    InvoiceLineForm = modelform_factory(InvoiceLine, fields=('concept', 'amount'))
    if request.method == 'POST':
        form = InvoiceLineForm(request.POST, instance=invoiceline)
        if form.is_valid():
            form.save()
            messages.success(request, 'Línea de factura actualizada correctamente.')
            return redirect('accounting:invoice_detail', pk=invoiceline.invoice.pk)
        else:
            messages.error(request, 'Error al actualizar la línea de factura. Revise los datos.')
    else:
        form = InvoiceLineForm(instance=invoiceline)
    return render(request, 'accounting/invoiceline_form.html', {'form': form, 'invoice': invoiceline.invoice})

@login_required
def invoiceline_delete(request, pk):
    invoiceline = get_object_or_404(InvoiceLine, pk=pk)
    if request.method == 'POST':
        invoice_pk = invoiceline.invoice.pk
        invoiceline.delete()
        messages.success(request, 'Línea de factura eliminada correctamente.')
        return redirect('accounting:invoice_detail', pk=invoice_pk)
    return render(request, 'accounting/invoiceline_confirm_delete.html', {'invoiceline': invoiceline})

from core.models import Company

@login_required
def invoice_pdf(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    company = Company.objects.first()
    html_string = render_to_string('accounting/invoice_pdf.html', {'invoice': invoice, 'company': company})

    html = HTML(string=html_string, base_url=request.build_absolute_uri())
    pdf = html.write_pdf()

    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="factura_{invoice.number}.pdf"'
    return response

@login_required
def send_invoice_by_email(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    if invoice.status not in ['validated', 'sent']:
        messages.error(request, "Solo se pueden enviar facturas validadas o ya enviadas.")
        return redirect('accounting:invoice_detail', pk=pk)
    
    try:
        send_invoice_email(invoice)
        invoice.mark_as_sent()
        messages.success(request, 'Factura enviada por correo electrónico')
    except Exception as e:
        messages.error(request, f'Error al enviar el correo: {str(e)}')
    return redirect('accounting:invoice_detail', pk=pk)