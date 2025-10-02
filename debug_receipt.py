#!/usr/bin/env python
import os
import django
import sys
from decimal import Decimal

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'real_estate_management.settings')
sys.path.append('.')
django.setup()

from accounting.models_invoice import Invoice
from accounting.services import OwnerReceiptService

# Obtener la factura 26 y sus cálculos
invoice = Invoice.objects.get(pk=26)
service = OwnerReceiptService()

print("=== Investigación del Error de Comprobante ===")
print(f"Factura: {invoice.number} - ${invoice.total_amount}")

# Verificar contrato
if invoice.contract:
    print(f"Contrato: {invoice.contract}")
    print(f"Descuento propietario: {invoice.contract.owner_discount_percentage}%")
    
    # Calcular manualmente
    gross_amount = invoice.total_amount
    discount_percentage = invoice.contract.owner_discount_percentage or Decimal('0')
    discount_amount = gross_amount * (discount_percentage / Decimal('100'))
    net_amount = gross_amount - discount_amount
    
    print(f"\n=== Cálculos Manuales ===")
    print(f"Gross: {gross_amount} ({type(gross_amount)})")
    print(f"Discount %: {discount_percentage} ({type(discount_percentage)})")
    print(f"Discount Amount: {discount_amount} ({type(discount_amount)})")
    print(f"Net Amount: {net_amount} ({type(net_amount)})")
    
    # Verificar precisión decimal
    print(f"\n=== Precisión Decimal ===")
    print(f"Discount Amount str: '{str(discount_amount)}'")
    print(f"Net Amount str: '{str(net_amount)}'")
    
    # Número de decimales
    discount_decimal_places = len(str(discount_amount).split('.')[-1]) if '.' in str(discount_amount) else 0
    net_decimal_places = len(str(net_amount).split('.')[-1]) if '.' in str(net_amount) else 0
    print(f"Discount Amount decimales: {discount_decimal_places}")
    print(f"Net Amount decimales: {net_decimal_places}")
    
    # Redondear a 2 decimales
    discount_rounded = discount_amount.quantize(Decimal('0.01'))
    net_rounded = net_amount.quantize(Decimal('0.01'))
    print(f"Discount Amount redondeado: {discount_rounded}")
    print(f"Net Amount redondeado: {net_rounded}")

try:
    print(f"\n=== Datos del Servicio ===")
    receipt_data = service.get_receipt_data(invoice)
    financial = receipt_data['financial']
    print(f"Service Gross: {financial['gross_amount']}")
    print(f"Service Discount: {financial['discount_amount']}")
    print(f"Service Net: {financial['net_amount']}")
except Exception as e:
    print(f"Error en servicio: {e}")
    import traceback
    traceback.print_exc()

# Probar generación del número de comprobante
try:
    from accounting.models_invoice import OwnerReceipt
    test_number = OwnerReceipt.generate_receipt_number()
    print(f"\n=== Número de Comprobante ===")
    print(f"Número generado: {test_number}")
except Exception as e:
    print(f"Error generando número: {e}")
    import traceback
    traceback.print_exc()
