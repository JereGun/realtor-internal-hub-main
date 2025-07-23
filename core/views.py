from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Company
from .forms import CompanyForm
from contracts.models import Contract
from payments.models import ContractPayment
from django.db.models import Sum, Q
from datetime import datetime

def dashboard(request):
    # Necesitamos determinar qué contratos son de venta y cuáles de alquiler
    # Como no existe el campo contract_type, podemos usar otro criterio
    # Por ejemplo, podemos asumir que los contratos con status='finished' son ventas
    # y los contratos con status='active' son alquileres (esto es solo un ejemplo)
    
    # Ventas de propiedades (asumiendo que son contratos finalizados)
    sales = Contract.objects.filter(status='finished')
    sales_total = sales.aggregate(total=Sum('amount'))['total'] or 0
    sales_count = sales.count()

    # Ingresos por alquileres (asumiendo que son contratos activos)
    rent_contracts = Contract.objects.filter(status='active')
    rent_payments = ContractPayment.objects.filter(contract__in=rent_contracts, status='paid')
    rent_income = rent_payments.aggregate(total=Sum('amount'))['total'] or 0
    rent_count = rent_payments.count()

    # Pagos pendientes
    pending_payments_qs = ContractPayment.objects.filter(status='pending')
    pending_payments = pending_payments_qs.aggregate(total=Sum('amount'))['total'] or 0
    pending_count = pending_payments_qs.count()

    # Últimas operaciones (ventas y alquileres)
    last_sales = sales.order_by('-created_at')[:5]
    last_rents = rent_payments.order_by('-due_date')[:5]
    last_operations = []
    for s in last_sales:
        last_operations.append({
            'type': 'Venta',
            'property': str(s.property),
            'customer': str(s.customer),
            'amount': s.amount,
            'date': s.created_at
        })
    for r in last_rents:
        last_operations.append({
            'type': 'Alquiler',
            'property': str(r.contract.property),
            'customer': str(r.contract.customer),
            'amount': r.amount,
            'date': r.due_date
        })
    # Ordenar por fecha descendente
    last_operations = sorted(last_operations, key=lambda x: x['date'], reverse=True)[:10]

    context = {
        'sales_total': sales_total,
        'sales_count': sales_count,
        'rent_income': rent_income,
        'rent_count': rent_count,
        'pending_payments': pending_payments,
        'pending_count': pending_count,
        'last_operations': last_operations,
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
