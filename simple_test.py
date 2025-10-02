#!/usr/bin/env python
"""
Test simple para ver el error real de las vistas de accounting
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'real_estate_management.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from django.urls import reverse

def test_simple():
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
    
    # Probar dashboard
    print("\n--- Probando Dashboard ---")
    try:
        url = reverse('accounting:accounting_dashboard')
        print(f"URL: {url}")
        
        response = client.get(url)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code != 200:
            print("Contenido de la respuesta:")
            content = response.content.decode('utf-8')[:1000]  # Primeros 1000 caracteres
            print(content)
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_simple()
