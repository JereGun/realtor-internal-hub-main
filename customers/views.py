
from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.db.models import Q
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from .models import Customer
from .forms import CustomerForm, CustomerSearchForm
import json


class CustomerListView(LoginRequiredMixin, ListView):
    model = Customer
    template_name = 'customers/customer_list.html'
    context_object_name = 'customers'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Customer.objects.all()
        
        form = CustomerSearchForm(self.request.GET)
        if form.is_valid():
            search = form.cleaned_data.get('search')
            locality = form.cleaned_data.get('locality')
            
            if search:
                queryset = queryset.filter(
                    Q(first_name__icontains=search) |
                    Q(last_name__icontains=search) |
                    Q(email__icontains=search) |
                    Q(document__icontains=search) |
                    Q(phone__icontains=search)
                )
            
            if locality:
                queryset = queryset.filter(locality__icontains=locality)
        
        return queryset.order_by('first_name', 'last_name')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_form'] = CustomerSearchForm(self.request.GET)
        
        # Add statistics for the template
        context['total_customers'] = Customer.objects.count()
        context['active_customers'] = Customer.objects.count()  # All customers are considered active
        
        # New customers this month
        from django.utils import timezone
        current_month = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        context['new_customers_month'] = Customer.objects.filter(created_at__gte=current_month).count()
        
        # Customers with contracts - using the correct related name
        try:
            context['customers_with_contracts'] = Customer.objects.filter(contract_set__isnull=False).distinct().count()
        except:
            context['customers_with_contracts'] = 0
        
        # Add localities for the filter dropdown
        try:
            from locations.models import City
            context['localities'] = City.objects.filter(customer__isnull=False).distinct().order_by('name')
        except:
            context['localities'] = []
        
        # Check if search was performed
        context['search_performed'] = bool(self.request.GET.get('search') or self.request.GET.get('locality'))
        
        return context


class CustomerDetailView(LoginRequiredMixin, DetailView):
    model = Customer
    template_name = 'customers/customer_detail.html'
    context_object_name = 'customer'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_contracts'] = self.object.contract_set.filter(is_active=True)
        return context


class CustomerCreateView(LoginRequiredMixin, CreateView):
    model = Customer
    form_class = CustomerForm
    template_name = 'customers/customer_form.html'
    success_url = reverse_lazy('customers:customer_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Cliente creado correctamente.')
        return super().form_valid(form)


class CustomerUpdateView(LoginRequiredMixin, UpdateView):
    model = Customer
    form_class = CustomerForm
    template_name = 'customers/customer_form.html'
    success_url = reverse_lazy('customers:customer_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Cliente actualizado correctamente.')
        return super().form_valid(form)


class CustomerDeleteView(LoginRequiredMixin, DeleteView):
    model = Customer
    template_name = 'customers/customer_confirm_delete.html'
    success_url = reverse_lazy('customers:customer_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Cliente eliminado correctamente.')
        return super().delete(request, *args, **kwargs)


@login_required
def search_customers_ajax(request):
    """Buscar clientes via AJAX para autocompletado"""
    try:
        if request.method == 'GET':
            query = request.GET.get('q', '').strip()
            
            if len(query) < 2:
                return JsonResponse({'results': []})
            
            # Buscar clientes que coincidan con el query
            customers = Customer.objects.filter(
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query) |
                Q(email__icontains=query) |
                Q(document__icontains=query)
            ).order_by('first_name', 'last_name')[:10]  # Limitar a 10 resultados
            
            results = []
            for customer in customers:
                results.append({
                    'id': customer.id,
                    'text': f"{customer.get_full_name()} ({customer.email})",
                    'full_name': customer.get_full_name(),
                    'email': customer.email,
                    'phone': customer.phone,
                    'document': customer.document
                })
            
            return JsonResponse({'results': results})
        
        return JsonResponse({'results': []})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def create_customer_ajax(request):
    """Crear cliente via AJAX"""
    if request.method == 'POST':
        data = json.loads(request.body)
        first_name = data.get('first_name', '').strip()
        last_name = data.get('last_name', '').strip()
        email = data.get('email', '').strip()
        phone = data.get('phone', '').strip()
        document = data.get('document', '').strip()
        
        # Validaciones básicas
        if not first_name or not last_name:
            return JsonResponse({'success': False, 'error': 'Nombre y apellido son requeridos'})
        
        if not email:
            return JsonResponse({'success': False, 'error': 'Email es requerido'})
        
        # Verificar si ya existe un cliente con el mismo email
        if Customer.objects.filter(email=email).exists():
            return JsonResponse({'success': False, 'error': 'Ya existe un cliente con este email'})
        
        # Verificar si ya existe un cliente con el mismo documento (si se proporcionó)
        if document and Customer.objects.filter(document=document).exists():
            return JsonResponse({'success': False, 'error': 'Ya existe un cliente con este documento'})
        
        try:
            # Crear el cliente
            customer = Customer.objects.create(
                first_name=first_name.title(),
                last_name=last_name.title(),
                email=email.lower(),
                phone=phone,
                document=document
            )
            
            return JsonResponse({
                'success': True,
                'customer': {
                    'id': customer.id,
                    'full_name': customer.get_full_name(),
                    'email': customer.email,
                    'text': f"{customer.get_full_name()} ({customer.email})"
                }
            })
        
        except Exception as e:
            return JsonResponse({'success': False, 'error': f'Error al crear el cliente: {str(e)}'})
        
    return JsonResponse({'success': False, 'error': 'Método no permitido'})
