#!/usr/bin/env python
"""
Script detallado para diagnosticar errores específicos en accounting
"""
import os
import sys
import django
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'real_estate_management.settings')
django.setup()

from django.urls import reverse
from django.test import Client, RequestFactory
from django.contrib.auth import get_user_model
from django.http import Http404
from accounting.views_web import accounting_dashboard, invoice_list

def test_views_directly():
    """Prueba las vistas directamente para ver errores específicos"""
    print("=== Diagnóstico Detallado de Accounting ===")
    
    # Crear usuario de prueba
    User = get_user_model()
    user = User.objects.filter(is_active=True, is_staff=True).first()
    if not user:
        print("❌ No hay usuarios staff disponibles")
        return
    
    print(f"✅ Usuario encontrado: {user.username}")
    
    # Crear factory de requests
    factory = RequestFactory()
    
    print("\n--- Prueba de Vista accounting_dashboard ---")
    try:
        request = factory.get('/contabilidad/dashboard/')
        request.user = user
        
        # Agregar session y messages
        from django.contrib.sessions.middleware import SessionMiddleware
        from django.contrib.messages.middleware import MessageMiddleware
        from django.contrib.messages import get_messages
        
        middleware = SessionMiddleware()
        middleware.process_request(request)
        request.session.save()
        
        middleware = MessageMiddleware()
        middleware.process_request(request)
        
        response = accounting_dashboard(request)
        print(f"✅ Vista accounting_dashboard funcionó correctamente: {response.status_code}")
        
    except Exception as e:
        print(f"❌ Error en accounting_dashboard: {e}")
        import traceback
        print(traceback.format_exc())
    
    print("\n--- Prueba de Vista invoice_list ---")
    try:
        request = factory.get('/contabilidad/invoices/')
        request.user = user
        
        # Agregar session y messages
        middleware = SessionMiddleware()
        middleware.process_request(request)
        request.session.save()
        
        middleware = MessageMiddleware()
        middleware.process_request(request)
        
        response = invoice_list(request)
        print(f"✅ Vista invoice_list funcionó correctamente: {response.status_code}")
        
    except Exception as e:
        print(f"❌ Error en invoice_list: {e}")
        import traceback
        print(traceback.format_exc())
    
    print("\n--- Verificación de Modelos ---")
    try:
        from accounting.models_invoice import Invoice, InvoiceLine, Payment
        invoice_count = Invoice.objects.count()
        payment_count = Payment.objects.count()
        print(f"✅ Modelos funcionando:")
        print(f"   - Facturas: {invoice_count}")
        print(f"   - Pagos: {payment_count}")
    except Exception as e:
        print(f"❌ Error con modelos: {e}")
        import traceback
        print(traceback.format_exc())
    
    print("\n--- Verificación de Formularios ---")
    try:
        from accounting.forms_invoice import InvoiceForm, InvoiceLineForm
        form = InvoiceForm()
        print(f"✅ Formularios importados correctamente")
    except Exception as e:
        print(f"❌ Error con formularios: {e}")
        import traceback
        print(traceback.format_exc())
    
    print("\n--- Verificación de Templates Base ---")
    try:
        from django.template.loader import get_template
        base_template = get_template('base.html')
        accounting_template = get_template('accounting/accounting_dashboard.html')
        print(f"✅ Templates base encontrados correctamente")
    except Exception as e:
        print(f"❌ Error con templates: {e}")
        import traceback
        print(traceback.format_exc())

if __name__ == '__main__':
    test_views_directly()
