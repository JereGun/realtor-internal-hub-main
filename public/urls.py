from django.urls import path
from . import views
from . import debug_views

app_name = 'public'

urlpatterns = [
    path('', views.home, name='home'),
    path('nosotros/', views.about, name='about'),
    path('propiedades/', views.properties, name='properties'),
    path('propiedad/<int:property_id>/', views.property_detail, name='property_detail'),
    path('agentes/', views.agents, name='agents'),
    path('api/locations/', views.location_autocomplete, name='location_autocomplete'),
    # SEO URLs
    path('sitemap.xml', views.sitemap_xml, name='sitemap'),
    path('robots.txt', views.robots_txt, name='robots'),
    # Debug URLs
    path('debug/properties/', debug_views.debug_properties, name='debug_properties'),
]
