from django.shortcuts import render, get_object_or_404, redirect
from .models_invoice import Invoice, InvoiceLine, Payment
from .forms_invoice import InvoiceForm, InvoiceLineFormSet
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.contrib import messages
from django.utils import timezone
from django.forms import modelform_factory
from django.http import HttpResponse
from django.template.loader import render_to_string
from weasyprint import HTML

@login_required
def accounting_dashboard(request):
    # Logica de gastos
    return render(request, 'accounting/accounting_dashboard.html')

@login_required
def invoice_list(request):
    invoice_list = Invoice.objects.select_related('customer').order_by('-date')
    paginator = Paginator(invoice_list, 25)  # 25 facturas por página
    page_number = request.GET.get('page')
    invoices = paginator.get_page(page_number)
    return render(request, 'accounting/invoice_list.html', {'invoices': invoices})

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
    
    if request.method == 'POST':
        form = InvoiceForm(request.POST, instance=invoice)
        formset = InvoiceLineFormSet(request.POST, instance=invoice)
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            invoice.compute_total()
            messages.success(request, 'Factura actualizada correctamente')
            return redirect('accounting:invoice_detail', pk=invoice.pk)
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
def payment_create(request):
    PaymentForm = modelform_factory(Payment, fields=('invoice', 'date', 'amount', 'method', 'notes'))
    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            payment = form.save()
            messages.success(request, 'Pago registrado correctamente.')
            return redirect('accounting:payment_detail', pk=payment.pk)
        else:
            messages.error(request, 'Error al registrar el pago. Revise los datos.')
    else:
        form = PaymentForm(initial={'date': timezone.now().date()})
    return render(request, 'accounting/payment_form.html', {'form': form})

@login_required
def payment_update(request, pk):
    payment = get_object_or_404(Payment, pk=pk)
    PaymentForm = modelform_factory(Payment, fields=('invoice', 'date', 'amount', 'method', 'notes'))
    if request.method == 'POST':
        form = PaymentForm(request.POST, instance=payment)
        if form.is_valid():
            form.save()
            messages.success(request, 'Pago actualizado correctamente.')
            return redirect('accounting:payment_detail', pk=payment.pk)
        else:
            messages.error(request, 'Error al actualizar el pago. Revise los datos.')
    else:
        form = PaymentForm(instance=payment)
    return render(request, 'accounting/payment_form.html', {'form': form})

@login_required
def payment_delete(request, pk):
    payment = get_object_or_404(Payment, pk=pk)
    if request.method == 'POST':
        payment.delete()
        messages.success(request, 'Pago eliminado correctamente.')
        return redirect('accounting:payment_list')
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

@login_required
def invoice_pdf(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    html_string = render_to_string('accounting/invoice_pdf.html', {'invoice': invoice})

    html = HTML(string=html_string)
    pdf = html.write_pdf()

    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="factura_{invoice.number}.pdf"'
    return response