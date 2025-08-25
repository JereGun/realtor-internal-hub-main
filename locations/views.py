from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from .models import State, City, Country
import json

def get_countries(request):
    """
    Devuelve una lista de todos los países.
    """
    countries = Country.objects.all().order_by('name')
    data = [{'id': country.id, 'name': country.name} for country in countries]
    return JsonResponse(data, safe=False)

def get_states(request):
    """
    Devuelve una lista de provincias/estados para un país dado.
    Espera un parámetro 'country_id' en la query string.
    """
    country_id = request.GET.get('country_id')
    if not country_id:
        return JsonResponse({'error': 'country_id es requerido'}, status=400)
    try:
        states = State.objects.filter(country_id=country_id).order_by('name')
        data = [{'id': state.id, 'name': state.name} for state in states]
        return JsonResponse(data, safe=False)
    except ValueError:
        return JsonResponse({'error': 'country_id inválido'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def get_cities(request):
    """
    Devuelve una lista de ciudades/localidades para una provincia/estado dado.
    Espera un parámetro 'state_id' en la query string.
    """
    state_id = request.GET.get('state_id')
    if not state_id:
        return JsonResponse({'error': 'state_id es requerido'}, status=400)
    try:
        cities = City.objects.filter(state_id=state_id).order_by('name')
        data = [{'id': city.id, 'name': city.name} for city in cities]
        return JsonResponse(data, safe=False)
    except ValueError:
        return JsonResponse({'error': 'state_id inválido'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# VISTAS AJAX PARA AUTOCOMPLETADO Y CREACIÓN
@login_required
def autocomplete_countries(request):
    """Autocompletado de países"""
    term = request.GET.get('term', '')
    countries = Country.objects.filter(name__icontains=term)[:10]
    
    results = [{
        'id': country.id,
        'text': country.name,
        'name': country.name
    } for country in countries]
    
    return JsonResponse({'results': results})


@login_required
def autocomplete_states(request):
    """Autocompletado de provincias/estados"""
    term = request.GET.get('term', '')
    country_id = request.GET.get('country_id')
    
    states = State.objects.filter(name__icontains=term)
    if country_id:
        states = states.filter(country_id=country_id)
    
    results = [{
        'id': state.id,
        'text': f"{state.name}, {state.country.name}",
        'name': state.name,
        'country': state.country.name,
        'country_id': state.country.id
    } for state in states[:10]]
    
    return JsonResponse({'results': results})


@login_required
def autocomplete_cities(request):
    """Autocompletado de ciudades"""
    term = request.GET.get('term', '')
    state_id = request.GET.get('state_id')
    
    cities = City.objects.filter(name__icontains=term)
    if state_id:
        cities = cities.filter(state_id=state_id)
    
    results = [{
        'id': city.id,
        'text': f"{city.name}, {city.state.name}, {city.state.country.name}",
        'name': city.name,
        'state': city.state.name,
        'state_id': city.state.id,
        'country': city.state.country.name,
        'country_id': city.state.country.id
    } for city in cities[:10]]
    
    return JsonResponse({'results': results})


@login_required
def create_country_ajax(request):
    """Crear país vía AJAX"""
    if request.method == 'POST':
        data = json.loads(request.body)
        name = data.get('name', '').strip()
        
        # Validaciones básicas
        if not name:
            return JsonResponse({'success': False, 'error': 'El nombre del país es requerido'})
        
        # Verificar si ya existe
        if Country.objects.filter(name__iexact=name).exists():
            return JsonResponse({'success': False, 'error': 'Ya existe un país con este nombre'})
        
        try:
            # Crear el país
            country = Country.objects.create(name=name.title())
            
            return JsonResponse({
                'success': True,
                'location': {
                    'id': country.id,
                    'name': country.name,
                    'text': country.name
                }
            })
        
        except Exception as e:
            return JsonResponse({'success': False, 'error': f'Error al crear el país: {str(e)}'})
        
    return JsonResponse({'success': False, 'error': 'Método no permitido'})


@login_required
def create_state_ajax(request):
    """Crear provincia/estado vía AJAX"""
    if request.method == 'POST':
        data = json.loads(request.body)
        name = data.get('name', '').strip()
        country_id = data.get('country_id')
        
        # Validaciones básicas
        if not name:
            return JsonResponse({'success': False, 'error': 'El nombre de la provincia es requerido'})
        
        if not country_id:
            return JsonResponse({'success': False, 'error': 'El país es requerido'})
        
        try:
            country = Country.objects.get(id=country_id)
        except Country.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'País no válido'})
        
        # Verificar si ya existe en ese país
        if State.objects.filter(name__iexact=name, country=country).exists():
            return JsonResponse({'success': False, 'error': 'Ya existe una provincia con este nombre en el país seleccionado'})
        
        try:
            # Crear la provincia
            state = State.objects.create(
                name=name.title(),
                country=country
            )
            
            return JsonResponse({
                'success': True,
                'location': {
                    'id': state.id,
                    'name': state.name,
                    'text': f"{state.name}, {state.country.name}",
                    'country_id': country.id,
                    'country': country.name
                }
            })
        
        except Exception as e:
            return JsonResponse({'success': False, 'error': f'Error al crear la provincia: {str(e)}'})
        
    return JsonResponse({'success': False, 'error': 'Método no permitido'})


@login_required
def create_city_ajax(request):
    """Crear ciudad vía AJAX"""
    if request.method == 'POST':
        data = json.loads(request.body)
        name = data.get('name', '').strip()
        state_id = data.get('state_id')
        
        # Validaciones básicas
        if not name:
            return JsonResponse({'success': False, 'error': 'El nombre de la ciudad es requerido'})
        
        if not state_id:
            return JsonResponse({'success': False, 'error': 'La provincia es requerida'})
        
        try:
            state = State.objects.get(id=state_id)
        except State.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Provincia no válida'})
        
        # Verificar si ya existe en esa provincia
        if City.objects.filter(name__iexact=name, state=state).exists():
            return JsonResponse({'success': False, 'error': 'Ya existe una ciudad con este nombre en la provincia seleccionada'})
        
        try:
            # Crear la ciudad
            city = City.objects.create(
                name=name.title(),
                state=state
            )
            
            return JsonResponse({
                'success': True,
                'location': {
                    'id': city.id,
                    'name': city.name,
                    'text': f"{city.name}, {city.state.name}, {city.state.country.name}",
                    'state_id': state.id,
                    'state': state.name,
                    'country_id': state.country.id,
                    'country': state.country.name
                }
            })
        
        except Exception as e:
            return JsonResponse({'success': False, 'error': f'Error al crear la ciudad: {str(e)}'})
        
    return JsonResponse({'success': False, 'error': 'Método no permitido'})
