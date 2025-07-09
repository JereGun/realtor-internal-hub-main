
from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.db.models import Q
from django.utils import timezone
from .models import ContractPayment, PaymentMethod
from .forms import ContractPaymentForm, PaymentMethodForm, PaymentSearchForm


class ContractPaymentListView(LoginRequiredMixin, ListView):
    model = ContractPayment
    template_name = 'payments/payment_list.html'
    context_object_name = 'payments'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = ContractPayment.objects.select_related('contract', 'payment_method', 'contract__property', 'contract__customer')
        
        form = PaymentSearchForm(self.request.GET)
        if form.is_valid():
            search = form.cleaned_data.get('search')
            status = form.cleaned_data.get('status')
            payment_method = form.cleaned_data.get('payment_method')
            
            if search:
                queryset = queryset.filter(
                    Q(contract__property__title__icontains=search) |
                    Q(contract__customer__first_name__icontains=search) |
                    Q(contract__customer__last_name__icontains=search) |
                    Q(receipt_number__icontains=search)
                )
            
            if status:
                queryset = queryset.filter(status=status)
            
            if payment_method:
                queryset = queryset.filter(payment_method=payment_method)
        
        return queryset.order_by('-due_date')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_form'] = PaymentSearchForm(self.request.GET)
        
        # Add summary statistics
        today = timezone.now().date()
        context['overdue_count'] = ContractPayment.objects.filter(
            status='pending',
            due_date__lt=today
        ).count()
        context['pending_count'] = ContractPayment.objects.filter(status='pending').count()
        
        return context


class ContractPaymentDetailView(LoginRequiredMixin, DetailView):
    model = ContractPayment
    template_name = 'payments/payment_detail.html'
    context_object_name = 'payment'


class ContractPaymentCreateView(LoginRequiredMixin, CreateView):
    model = ContractPayment
    form_class = ContractPaymentForm
    template_name = 'payments/payment_form.html'
    success_url = reverse_lazy('payments:payment_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Pago creado correctamente.')
        return super().form_valid(form)


class ContractPaymentUpdateView(LoginRequiredMixin, UpdateView):
    model = ContractPayment
    form_class = ContractPaymentForm
    template_name = 'payments/payment_form.html'
    success_url = reverse_lazy('payments:payment_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Pago actualizado correctamente.')
        return super().form_valid(form)


class ContractPaymentDeleteView(LoginRequiredMixin, DeleteView):
    model = ContractPayment
    template_name = 'payments/payment_confirm_delete.html'
    success_url = reverse_lazy('payments:payment_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Pago eliminado correctamente.')
        return super().delete(request, *args, **kwargs)


# Payment Method Views
class PaymentMethodListView(LoginRequiredMixin, ListView):
    model = PaymentMethod
    template_name = 'payments/payment_method_list.html'
    context_object_name = 'payment_methods'
    
    def get_queryset(self):
        return PaymentMethod.objects.filter(is_active=True)


class PaymentMethodCreateView(LoginRequiredMixin, CreateView):
    model = PaymentMethod
    form_class = PaymentMethodForm
    template_name = 'payments/payment_method_form.html'
    success_url = reverse_lazy('payments:payment_method_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Método de pago creado correctamente.')
        return super().form_valid(form)


class PaymentMethodUpdateView(LoginRequiredMixin, UpdateView):
    model = PaymentMethod
    form_class = PaymentMethodForm
    template_name = 'payments/payment_method_form.html'
    success_url = reverse_lazy('payments:payment_method_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Método de pago actualizado correctamente.')
        return super().form_valid(form)
