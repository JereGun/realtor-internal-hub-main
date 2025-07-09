from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from invoicing.models import Invoice, InvoiceItem, Payment
from .forms import InvoiceForm, InvoiceItemForm, PaymentForm

class InvoiceListView(ListView):
    model = Invoice
    template_name = 'invoicing/invoice_list.html'
    context_object_name = 'invoices'
    ordering = ['-issue_date']

class InvoiceDetailView(DetailView):
    model = Invoice
    template_name = 'invoicing/invoice_detail.html'
    context_object_name = 'invoice'

class InvoiceCreateView(CreateView):
    model = Invoice
    form_class = InvoiceForm
    template_name = 'invoicing/invoice_form.html'
    success_url = reverse_lazy('invoicing:invoice_list')

class InvoiceUpdateView(UpdateView):
    model = Invoice
    form_class = InvoiceForm
    template_name = 'invoicing/invoice_form.html'
    success_url = reverse_lazy('invoicing:invoice_list')

class InvoiceDeleteView(DeleteView):
    model = Invoice
    template_name = 'invoicing/invoice_confirm_delete.html'
    success_url = reverse_lazy('invoicing:invoice_list')

class InvoiceItemCreateView(CreateView):
    model = InvoiceItem
    form_class = InvoiceItemForm
    template_name = 'invoicing/invoiceitem_form.html'

    def get_success_url(self):
        return reverse_lazy('invoicing:invoice_detail', kwargs={'pk': self.object.invoice.pk})

    def form_valid(self, form):
        invoice = Invoice.objects.get(pk=self.kwargs['invoice_pk'])
        form.instance.invoice = invoice
        return super().form_valid(form)

class InvoiceItemUpdateView(UpdateView):
    model = InvoiceItem
    form_class = InvoiceItemForm
    template_name = 'invoicing/invoiceitem_form.html'

    def get_success_url(self):
        return reverse_lazy('invoicing:invoice_detail', kwargs={'pk': self.object.invoice.pk})

class InvoiceItemDeleteView(DeleteView):
    model = InvoiceItem
    template_name = 'invoicing/invoiceitem_confirm_delete.html'

    def get_success_url(self):
        return reverse_lazy('invoicing:invoice_detail', kwargs={'pk': self.object.invoice.pk})

class PaymentCreateView(CreateView):
    model = Payment
    form_class = PaymentForm
    template_name = 'invoicing/payment_form.html'

    def get_success_url(self):
        return reverse_lazy('invoicing:invoice_detail', kwargs={'pk': self.object.invoice.pk})

    def form_valid(self, form):
        invoice = Invoice.objects.get(pk=self.kwargs['invoice_pk'])
        form.instance.invoice = invoice
        return super().form_valid(form)

class PaymentDeleteView(DeleteView):
    model = Payment
    template_name = 'invoicing/payment_confirm_delete.html'

    def get_success_url(self):
        return reverse_lazy('invoicing:invoice_detail', kwargs={'pk': self.object.invoice.pk})
