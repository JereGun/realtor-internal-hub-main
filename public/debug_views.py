from django.shortcuts import render
from properties.models import Property

def debug_properties(request):
    """Vista de depuración para verificar los datos de las propiedades"""
    # Obtener todas las propiedades
    properties = Property.objects.all()
    
    # Contar propiedades por tipo de listado
    sale_count = properties.filter(listing_type='sale').count()
    rent_count = properties.filter(listing_type='rent').count()
    both_count = properties.filter(listing_type='both').count()
    
    context = {
        'properties': properties,
        'sale_count': sale_count,
        'rent_count': rent_count,
        'both_count': both_count,
    }
    
    return render(request, 'public/debug_properties.html', context)