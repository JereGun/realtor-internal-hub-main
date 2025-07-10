from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.db.models import Q
# Removed Invoice, InvoiceItem from models import
from .models import Contract, ContractIncrease
# Removed InvoiceForm, InvoiceItemForm from forms import
from .forms import ContractForm, ContractIncreaseForm, ContractSearchForm


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
        # Point to accounting_invoices from the accounting app's Invoice model
        # Ensure 'accounting_invoices' is the correct related_name in accounting.models_invoice.Invoice
        if hasattr(self.object, 'accounting_invoices'):
            context['invoices'] = self.object.accounting_invoices.prefetch_related('lines').all() 
        else:
            context['invoices'] = [] # Or handle as an error/log message
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
        response = super().form_valid(form)
        # After saving, update status if necessary (e.g., if dates changed)
        self.object.update_status()
        self.object.save(update_fields=['status'])
        return response
    
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
            contract.save() # Saves the new amount
            
            # Potentially update contract status if the increase implies a change relevant to status
            # For now, contract.update_status() is mainly date-based, so less critical here
            # but if it included logic based on activity/amount changes, it would be relevant.
            # contract.update_status()
            # contract.save(update_fields=['status']) 

            messages.success(request, 'Aumento agregado correctamente.')
            return redirect('contracts:contract_detail', pk=pk)
    else:
        form = ContractIncreaseForm(initial={'previous_amount': contract.amount})
    
    return render(request, 'contracts/add_increase.html', {
        'form': form,
        'contract': contract
    })

# Removed InvoiceListView, InvoiceDetailView, InvoiceCreateView, InvoiceUpdateView, InvoiceDeleteView