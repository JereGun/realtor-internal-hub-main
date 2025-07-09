from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.db.models import Q
from .models import Contract, ContractIncrease, Invoice, InvoiceItem
from .forms import ContractForm, ContractIncreaseForm, ContractSearchForm, InvoiceForm, InvoiceItemForm


class ContractListView(LoginRequiredMixin, ListView):
    model = Contract
    template_name = 'contracts/contract_list.html'
    context_object_name = 'contracts'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Contract.objects.select_related('property', 'customer', 'agent')
        
        form = ContractSearchForm(self.request.GET)
        if form.is_valid():
            search = form.cleaned_data.get('search')
            contract_type = form.cleaned_data.get('contract_type')
            is_active = form.cleaned_data.get('is_active')
            
            if search:
                queryset = queryset.filter(
                    Q(property__title__icontains=search) |
                    Q(customer__first_name__icontains=search) |
                    Q(customer__last_name__icontains=search) |
                    Q(agent__first_name__icontains=search) |
                    Q(agent__last_name__icontains=search)
                )
            
            if contract_type:
                queryset = queryset.filter(contract_type=contract_type)
            
            if is_active:
                queryset = queryset.filter(is_active=(is_active == 'true'))
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_form'] = ContractSearchForm(self.request.GET)
        return context


class ContractDetailView(LoginRequiredMixin, DetailView):
    model = Contract
    template_name = 'contracts/contract_detail.html'
    context_object_name = 'contract'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['increases'] = self.object.increases.all()
        context['invoices'] = self.object.invoices.prefetch_related('items').all()
        return context


class ContractCreateView(LoginRequiredMixin, CreateView):
    model = Contract
    form_class = ContractForm
    template_name = 'contracts/contract_form.html'
    
    def form_valid(self, form):
        form.instance.agent = self.request.user
        messages.success(self.request, 'Contrato creado correctamente.')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('contracts:contract_detail', kwargs={'pk': self.object.pk})


class ContractUpdateView(LoginRequiredMixin, UpdateView):
    model = Contract
    form_class = ContractForm
    template_name = 'contracts/contract_form.html'
    
    def form_valid(self, form):
        messages.success(self.request, 'Contrato actualizado correctamente.')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('contracts:contract_detail', kwargs={'pk': self.object.pk})


class ContractDeleteView(LoginRequiredMixin, DeleteView):
    model = Contract
    template_name = 'contracts/contract_confirm_delete.html'
    success_url = reverse_lazy('contracts:contract_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Contrato eliminado correctamente.')
        return super().delete(request, *args, **kwargs)


@login_required
def add_contract_increase(request, pk):
    contract = get_object_or_404(Contract, pk=pk)
    
    if request.method == 'POST':
        form = ContractIncreaseForm(request.POST)
        if form.is_valid():
            increase = form.save(commit=False)
            increase.contract = contract
            increase.save()
            
            # Update contract amount
            contract.amount = increase.new_amount
            contract.save()
            
            messages.success(request, 'Aumento agregado correctamente.')
            return redirect('contracts:contract_detail', pk=pk)
    else:
        form = ContractIncreaseForm(initial={'previous_amount': contract.amount})
    
    return render(request, 'contracts/add_increase.html', {
        'form': form,
        'contract': contract
    })


class InvoiceListView(LoginRequiredMixin, ListView):
    model = Invoice
    template_name = 'contracts/invoice_list.html'
    context_object_name = 'invoices'
    paginate_by = 20


class InvoiceDetailView(LoginRequiredMixin, DetailView):
    model = Invoice
    template_name = 'contracts/invoice_detail.html'
    context_object_name = 'invoice'


class InvoiceCreateView(LoginRequiredMixin, CreateView):
    model = Invoice
    form_class = InvoiceForm
    template_name = 'contracts/invoice_form.html'
    
    def get_initial(self):
        initial = super().get_initial()
        contract_id = self.request.GET.get('contract')
        if contract_id:
            initial['contract'] = contract_id
        return initial
    
    def get_success_url(self):
        return reverse_lazy('contracts:invoice_detail', kwargs={'pk': self.object.pk})


class InvoiceUpdateView(LoginRequiredMixin, UpdateView):
    model = Invoice
    form_class = InvoiceForm
    template_name = 'contracts/invoice_form.html'
    
    def get_success_url(self):
        return reverse_lazy('contracts:invoice_detail', kwargs={'pk': self.object.pk})


class InvoiceDeleteView(LoginRequiredMixin, DeleteView):
    model = Invoice
    template_name = 'contracts/invoice_confirm_delete.html'
    
    def get_success_url(self):
        return reverse_lazy('contracts:invoice_list')


class InvoiceItemCreateView(LoginRequiredMixin, CreateView):
    model = InvoiceItem
    form_class = InvoiceItemForm
    template_name = 'contracts/invoiceitem_form.html'
    
    def form_valid(self, form):
        invoice_id = self.kwargs.get('invoice_pk')
        form.instance.invoice_id = invoice_id
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('contracts:invoice_detail', kwargs={'pk': self.object.invoice.pk})


class InvoiceItemUpdateView(LoginRequiredMixin, UpdateView):
    model = InvoiceItem
    form_class = InvoiceItemForm
    template_name = 'contracts/invoiceitem_form.html'
    
    def get_success_url(self):
        return reverse_lazy('contracts:invoice_detail', kwargs={'pk': self.object.invoice.pk})


class InvoiceItemDeleteView(LoginRequiredMixin, DeleteView):
    model = InvoiceItem
    template_name = 'contracts/invoiceitem_confirm_delete.html'
    
    def get_success_url(self):
        return reverse_lazy('contracts:invoice_detail', kwargs={'pk': self.object.invoice.pk})
