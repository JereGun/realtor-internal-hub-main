from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Q, Count
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Company
from .forms import CompanyForm
from contracts.models import Contract
from payments.models import ContractPayment
from properties.models import Property, PropertyType, PropertyStatus
from customers.models import Customer

@login_required
def dashboard(request):
    """
    Vista principal del dashboard con métricas y estadísticas del negocio inmobiliario.
    """
    # Obtener fecha actual y rangos de tiempo
    today = timezone.now().date()
    current_month_start = today.replace(day=1)
    last_month = current_month_start - timedelta(days=1)
    last_month_start = last_month.replace(day=1)
    
    # === MÉTRICAS PRINCIPALES ===
    
    # Ventas de propiedades (contratos finalizados con propiedades de venta)
    sales_contracts = Contract.objects.filter(
        status='finished',
        property__listing_type__in=['sale', 'both']
    )
    sales_total = sales_contracts.aggregate(total=Sum('amount'))['total'] or 0
    sales_count = sales_contracts.count()

    # Ingresos por alquileres (pagos de contratos activos de alquiler)
    rent_contracts = Contract.objects.filter(
        status='active',
        property__listing_type__in=['rent', 'both']
    )
    rent_payments = ContractPayment.objects.filter(
        contract__in=rent_contracts, 
        status='paid'
    )
    rent_income = rent_payments.aggregate(total=Sum('amount'))['total'] or 0
    rent_count = rent_payments.count()

    # Pagos pendientes
    pending_payments_qs = ContractPayment.objects.filter(status='pending')
    pending_payments = pending_payments_qs.aggregate(total=Sum('amount'))['total'] or 0
    pending_count = pending_payments_qs.count()

    # Propiedades totales y disponibles
    total_properties = Property.objects.count()
    available_properties = Property.objects.filter(
        property_status__name__icontains='disponible'
    ).count()

    # === ESTADÍSTICAS ADICIONALES ===
    
    # Contratos activos
    active_contracts = Contract.objects.filter(status='active').count()
    
    # Nuevos clientes este mes
    new_customers = Customer.objects.filter(
        created_at__gte=current_month_start
    ).count()
    
    # Contratos próximos a vencer (próximos 30 días)
    expiring_date = today + timedelta(days=30)
    expiring_contracts = Contract.objects.filter(
        status='active',
        end_date__lte=expiring_date,
        end_date__gte=today
    ).count()
    
    # Pagos del mes actual
    monthly_payments = ContractPayment.objects.filter(
        payment_date__gte=current_month_start,
        status='paid'
    ).aggregate(total=Sum('amount'))['total'] or 0

    # === ÚLTIMAS OPERACIONES ===
    
    # Últimas ventas
    last_sales = sales_contracts.order_by('-created_at')[:5]
    # Últimos pagos de alquiler
    last_rents = rent_payments.order_by('-payment_date')[:5]
    
    last_operations = []
    
    # Agregar ventas
    for sale in last_sales:
        last_operations.append({
            'type': 'Venta',
            'property': str(sale.property),
            'customer': str(sale.customer),
            'amount': sale.amount,
            'date': sale.created_at
        })
    
    # Agregar alquileres
    for rent in last_rents:
        last_operations.append({
            'type': 'Alquiler',
            'property': str(rent.contract.property),
            'customer': str(rent.contract.customer),
            'amount': rent.amount,
            'date': rent.payment_date or rent.due_date
        })
    
    # Ordenar por fecha descendente
    last_operations = sorted(last_operations, key=lambda x: x['date'], reverse=True)[:10]

    # === ESTADÍSTICAS POR TIPO Y ESTADO ===
    
    # Propiedades por tipo
    property_types_stats = PropertyType.objects.annotate(
        count=Count('property')
    ).filter(count__gt=0).order_by('-count')[:6]
    
    # Propiedades por estado
    property_status_stats = PropertyStatus.objects.annotate(
        count=Count('property')
    ).filter(count__gt=0).order_by('-count')[:6]

    # === CONTEXTO PARA EL TEMPLATE ===
    context = {
        # Métricas principales
        'sales_total': sales_total,
        'sales_count': sales_count,
        'rent_income': rent_income,
        'rent_count': rent_count,
        'pending_payments': pending_payments,
        'pending_count': pending_count,
        'total_properties': total_properties,
        'available_properties': available_properties,
        
        # Estadísticas adicionales
        'active_contracts': active_contracts,
        'new_customers': new_customers,
        'expiring_contracts': expiring_contracts,
        'monthly_payments': monthly_payments,
        
        # Actividad reciente
        'last_operations': last_operations,
        
        # Estadísticas por categorías
        'property_types_stats': property_types_stats,
        'property_status_stats': property_status_stats,
    }
    
    return render(request, 'dashboard.html', context)


def company_settings(request):
    # Intentamos obtener la primera compañía, si no existe, la creamos
    company, created = Company.objects.get_or_create(
        id=1,
        defaults={'name': 'Mi Empresa'}
    )

    if request.method == 'POST':
        form = CompanyForm(request.POST, request.FILES, instance=company)
        if form.is_valid():
            form.save()
            messages.success(request, 'Los datos de la empresa se han actualizado correctamente.')
            return redirect('core:company_settings')
    else:
        form = CompanyForm(instance=company)

    return render(request, 'core/company_settings.html', {'form': form})
