from django.http import JsonResponse
from .models import State, City, Country

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
