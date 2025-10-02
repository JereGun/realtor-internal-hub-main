#!/usr/bin/env python
"""
Script para probar las URLs de accounting y detectar problemas
"""
import os
import sys
import django
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'real_estate_management.settings')
django.setup()

from django.urls import reverse, NoReverseMatch
from django.test import Client
from django.contrib.auth import get_user_model

# URLs de accounting para probar
ACCOUNTING_URLS = [
    'accounting:accounting_dashboard',
    'accounting:invoice_list',
    'accounting:invoice_create',
    'accounting:payment_list',
    'accounting:owner_receipts_list',
]

def test_accounting_urls():
    """Prueba las URLs de accounting"""
    print("=== Prueba de URLs de Accounting ===")
    
    # Crear cliente de prueba
    client = Client()
    
    # Crear usuario de prueba
    User = get_user_model()
    user = User.objects.filter(is_active=True, is_staff=True).first()
    if not user:
        print("❌ No hay usuarios staff disponibles para hacer las pruebas")
        return
    
    # Hacer login
    client.force_login(user)
    print(f"✅ Logueado como: {user.username}")
    
    print("\n--- Verificación de URLs ---")
    
    for url_name in ACCOUNTING_URLS:
        try:
            # Intentar generar la URL
            url = reverse(url_name)
            print(f"✅ {url_name}: {url}")
            
            # Hacer petición GET
            response = client.get(url)
            status_code = response.status_code
            
            if status_code == 200:
                print(f"   ➡️  Respuesta: {status_code} ✅")
            elif status_code == 302:
                print(f"   ➡️  Respuesta: {status_code} (redirección) ⚠️")
            else:
                print(f"   ➡️  Respuesta: {status_code} ❌")
                
        except NoReverseMatch as e:
            print(f"❌ {url_name}: Error de URL - {e}")
        except Exception as e:
            print(f"❌ {url_name}: Error - {e}")
    
    print("\n--- Verificación de Templates ---")
    
    # Verificar si los templates existen
    import os
    template_dir = 'templates/accounting/'
    if os.path.exists(template_dir):
        templates = [f for f in os.listdir(template_dir) if f.endswith('.html')]
        print(f"✅ Encontrados {len(templates)} templates de accounting:")
        for template in templates[:10]:  # Mostrar solo los primeros 10
            print(f"   - {template}")
        if len(templates) > 10:
            print(f"   ... y {len(templates) - 10} más")
    else:
        print(f"❌ Directorio de templates no encontrado: {template_dir}")

if __name__ == '__main__':
    test_accounting_urls()
