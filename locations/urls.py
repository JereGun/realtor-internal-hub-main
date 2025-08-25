from django.urls import path
from . import views

app_name = 'locations'

urlpatterns = [
    # APIs existentes
    path('api/countries/', views.get_countries, name='api_get_countries'),
    path('api/states/', views.get_states, name='api_get_states'), # Espera country_id como query param
    path('api/cities/', views.get_cities, name='api_get_cities'), # Espera state_id como query param
    
    # AJAX endpoints para autocompletado
    path('ajax/countries/autocomplete/', views.autocomplete_countries, name='autocomplete_countries'),
    path('ajax/states/autocomplete/', views.autocomplete_states, name='autocomplete_states'),
    path('ajax/cities/autocomplete/', views.autocomplete_cities, name='autocomplete_cities'),
    
    # AJAX endpoints para creación
    path('ajax/countries/create/', views.create_country_ajax, name='create_country_ajax'),
    path('ajax/states/create/', views.create_state_ajax, name='create_state_ajax'),
    path('ajax/cities/create/', views.create_city_ajax, name='create_city_ajax'),
]
