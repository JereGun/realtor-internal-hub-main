from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.db.models import Q
from django.utils import timezone
from .models import Contract, ContractIncrease
from .forms import ContractForm, ContractIncreaseForm, ContractSearchForm
from accounting.models_invoice import Invoice, InvoiceLine

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
            status = form.cleaned_data.get('status')
            
            if search:
                queryset = queryset.filter(
                    Q(property__title__icontains=search) |
                    Q(customer__first_name__icontains=search) |
                    Q(customer__last_name__icontains=search) |
                    Q(agent__first_name__icontains=search) |
                    Q(agent__last_name__icontains=search)
                )
            
            if status:
                queryset = queryset.filter(status=status)
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_form'] = ContractSearchForm(self.request.GET)
        
        # Calcular estadísticas para las tarjetas
        all_contracts = Contract.objects.all()
        today = timezone.now().date()
        next_month = today + timezone.timedelta(days=30)
        
        context['active_contracts_count'] = all_contracts.filter(status='active').count()
        context['expiring_contracts_count'] = all_contracts.filter(
            status='active',
            end_date__isnull=False,
            end_date__lte=next_month
        ).count()
        context['increase_due_contracts_count'] = all_contracts.filter(
            status='active',
            next_increase_date__isnull=False,
            next_increase_date__lte=next_month,
            next_increase_date__gte=today
        ).count()
        
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
        context['invoices'] = self.object.invoices.prefetch_related('lines').all()
        return context

from dateutil.relativedelta import relativedelta

class ContractCreateView(LoginRequiredMixin, CreateView):
    model = Contract
    form_class = ContractForm
    template_name = 'contracts/contract_form.html'
    
    def get_initial(self):
        """Pre-selects the logged-in agent but allows it to be changed."""
        initial = super().get_initial()
        initial['agent'] = self.request.user
        return initial
    
    def form_valid(self, form):
        # Creamos el objeto en memoria sin guardarlo aún en la BD.
        # El agente seleccionado en el formulario ya está en `form.instance`.
        contract = form.save(commit=False)

        # Calculamos la fecha del próximo aumento
        if contract.start_date and contract.frequency:
            if contract.frequency == 'monthly':
                contract.next_increase_date = contract.start_date + relativedelta(months=1)
            elif contract.frequency == 'quarterly':
                contract.next_increase_date = contract.start_date + relativedelta(months=3)
            elif contract.frequency == 'semi-annually':
                contract.next_increase_date = contract.start_date + relativedelta(months=6)
            elif contract.frequency == 'annually':
                contract.next_increase_date = contract.start_date + relativedelta(years=1)
        
        # Guardamos el objeto una sola vez con todos los datos.
        contract.save()
        self.object = contract # Asignamos el objeto a la vista
        
        messages.success(self.request, 'Contrato creado correctamente.')
        return redirect(self.get_success_url())
    
    def get_success_url(self):
        return reverse_lazy('contracts:contract_detail', kwargs={'pk': self.object.pk})

    def form_invalid(self, form):
        print(form.errors)
        return super().form_invalid(form)


class ContractUpdateView(LoginRequiredMixin, UpdateView):
    model = Contract
    form_class = ContractForm
    template_name = 'contracts/contract_form.html'
    
    def form_valid(self, form):
        # Obtenemos la instancia del contrato con los datos del formulario, sin guardar en BD.
        contract = form.save(commit=False)

        # Recalculamos la fecha del próximo aumento
        if contract.start_date and contract.frequency:
            if contract.frequency == 'monthly':
                contract.next_increase_date = contract.start_date + relativedelta(months=1)
            elif contract.frequency == 'quarterly':
                contract.next_increase_date = contract.start_date + relativedelta(months=3)
            elif contract.frequency == 'semi-annually':
                contract.next_increase_date = contract.start_date + relativedelta(months=6)
            elif contract.frequency == 'annually':
                contract.next_increase_date = contract.start_date + relativedelta(years=1)
        else:
            contract.next_increase_date = None

        # Actualizamos el estado del contrato basado en las fechas
        contract.update_status()
        
        # Guardamos el objeto una sola vez con todos los cambios.
        contract.save()
        self.object = contract

        messages.success(self.request, 'Contrato actualizado correctamente.')
        return redirect(self.get_success_url())
    
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

            # Update next_increase_date using RentIncreaseChecker logic
            from user_notifications.checkers import RentIncreaseChecker
            checker = RentIncreaseChecker()
            next_date = checker.calculate_next_increase_date(contract, from_date=increase.effective_date)
            contract.next_increase_date = next_date
            contract.save() # Saves the new amount and next increase date


            messages.success(request, 'Aumento agregado correctamente.')
            return redirect('contracts:contract_detail', pk=pk)
    else:
        form = ContractIncreaseForm(initial={'previous_amount': contract.amount})
    
    return render(request, 'contracts/add_increase.html', {
        'form': form,
        'contract': contract
    })

from django.http import JsonResponse
from properties.models import Property

def get_property_rental_price(request):
    property_id = request.GET.get('property_id')
    try:
        property = Property.objects.get(id=property_id)
        return JsonResponse({'rental_price': property.rental_price})
    except Property.DoesNotExist:
        return JsonResponse({'error': 'Property not found'}, status=404)

from accounting.models_invoice import Invoice, InvoiceLine
from django.utils import timezone

@login_required
def create_invoice_from_contract(request, contract_id):
    """
    Creates a new invoice from a contract, pre-filling customer and amount.
    """
    contract = get_object_or_404(Contract, pk=contract_id)

    try:
        # Create a new invoice with initial values
        invoice = Invoice.objects.create(
            customer=contract.customer,
            contract=contract,
            date=timezone.now().date(),
            due_date=contract.end_date if contract.end_date else timezone.now().date() + timezone.timedelta(days=30),
            description=f'Factura por contrato {contract}',
            total_amount=contract.amount
        )
        
        # Create a single invoice line with the contract amount
        InvoiceLine.objects.create(
            invoice=invoice,
            concept=f'Alquiler de {contract.property.title}',
            amount=contract.amount
        )
        
        messages.success(request, f'Factura {invoice.number} creada correctamente.')
        return redirect('accounting:invoice_detail', pk=invoice.pk)
        
    except Exception as e:
        messages.error(request, f'Error al crear la factura: {str(e)}')
        return redirect('contracts:contract_detail', pk=contract_id)
    # Create an invoice line for the rent
    InvoiceLine.objects.create(
        invoice=invoice,
        concept=f"Alquiler mes {timezone.now().strftime('%B %Y')}",
        amount=contract.amount
    )

    messages.success(request, f"Factura creada para el contrato {contract.id}.")
    return redirect('accounting:invoice_edit', pk=invoice.pk)