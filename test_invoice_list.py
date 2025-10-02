#!/usr/bin/env python
"""
Test específico para la lista de facturas
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'real_estate_management.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from django.urls import reverse

def test_invoice_list():
    # Crear cliente
    client = Client()
    
    # Obtener usuario
    User = get_user_model()
    user = User.objects.filter(is_active=True, is_staff=True).first()
    if not user:
        print("❌ No hay usuario disponible")
        return
    
    print(f"✅ Usuario: {user.username}")
    
    # Login
    client.force_login(user)
    
    # Probar lista de facturas
    print("\n--- Probando Lista de Facturas ---")
    try:
        url = reverse('accounting:invoice_list')
        print(f"URL: {url}")
        
        response = client.get(url)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ ¡Lista de facturas funciona correctamente!")
        else:
            print("Contenido de la respuesta:")
            content = response.content.decode('utf-8')[:1000]  
            print(content)
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_invoice_list()
