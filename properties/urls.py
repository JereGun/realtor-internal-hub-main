
from django.urls import path
from . import views

app_name = 'properties'

urlpatterns = [
    # URL pública para propiedades
    path('public/propiedades/', views.PublicPropertyListView.as_view(), name='public_property_list'),
    
    # URLs internas
    path('', views.PropertyListView.as_view(), name='property_list'),
    path('<int:pk>/', views.PropertyDetailView.as_view(), name='property_detail'),
    path('create/', views.PropertyCreateView.as_view(), name='property_create'),
    path('<int:pk>/edit/', views.PropertyUpdateView.as_view(), name='property_edit'),
    path('<int:pk>/delete/', views.PropertyDeleteView.as_view(), name='property_delete'),
    path('<int:pk>/add-image/', views.add_property_image, name='add_image'),
    path('add-image/', views.add_property_image, name='add_image_no_property'),
    path('<int:pk>/delete-image/<int:image_pk>/', views.delete_property_image, name='delete_image'),
    
    # AJAX endpoints para Features y Tags
    path('ajax/features/autocomplete/', views.autocomplete_features, name='autocomplete_features'),
    path('ajax/tags/autocomplete/', views.autocomplete_tags, name='autocomplete_tags'),
    path('ajax/features/create/', views.create_feature_ajax, name='create_feature_ajax'),
    path('ajax/tags/create/', views.create_tag_ajax, name='create_tag_ajax'),
    path('ajax/property-types/create/', views.create_property_type_ajax, name='create_property_type_ajax'),
    path('ajax/property-statuses/create/', views.create_property_status_ajax, name='create_property_status_ajax'),
    path('ajax/property-types/', views.get_property_types_ajax, name='get_property_types_ajax'),
    path('ajax/property-statuses/', views.get_property_statuses_ajax, name='get_property_statuses_ajax'),
    
    # AJAX endpoints para autocompletado de Owner, Country, Province, Locality
    path('ajax/owners/autocomplete/', views.autocomplete_owners, name='autocomplete_owners'),
    path('ajax/countries/autocomplete/', views.autocomplete_countries, name='autocomplete_countries'),
    path('ajax/provinces/autocomplete/', views.autocomplete_provinces, name='autocomplete_provinces'),
    path('ajax/localities/autocomplete/', views.autocomplete_localities, name='autocomplete_localities'),
    
    # AJAX endpoints para autocompletado y creación de propiedades
    path('ajax/autocomplete/', views.autocomplete_properties, name='autocomplete_properties'),
    path('ajax/create/', views.create_property_ajax, name='create_property_ajax'),
    
    # Demo page
    path('demo/image-upload/', views.image_upload_demo, name='image_upload_demo'),
]
