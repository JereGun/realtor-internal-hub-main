from django.shortcuts import render
from contracts.models import Contract
from payments.models import ContractPayment
from django.db.models import Sum, Q
from datetime import datetime

def dashboard(request):
    # Ventas de propiedades (contratos de tipo 'venta')
    sales = Contract.objects.filter(contract_type='sale')
    sales_total = sales.aggregate(total=Sum('amount'))['total'] or 0
    sales_count = sales.count()

    # Ingresos por alquileres (pagos de contratos de tipo 'rent' y pagos completados)
    rent_contracts = Contract.objects.filter(contract_type='rent')
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
