from django.urls import path
from . import views

app_name = 'locations'

urlpatterns = [
    path('api/countries/', views.get_countries, name='api_get_countries'),
    path('api/states/', views.get_states, name='api_get_states'), # Espera country_id como query param
    path('api/cities/', views.get_cities, name='api_get_cities'), # Espera state_id como query param
]
