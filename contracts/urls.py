from django.urls import path
from . import views
# from .urls_invoice import urlpatterns as invoice_urlpatterns # Removed

app_name = 'contracts'

urlpatterns = [
    path('', views.ContractListView.as_view(), name='contract_list'),
    path('<int:pk>/', views.ContractDetailView.as_view(), name='contract_detail'),
    path('create/', views.ContractCreateView.as_view(), name='contract_create'),
    path('<int:pk>/edit/', views.ContractUpdateView.as_view(), name='contract_edit'),
    path('<int:pk>/delete/', views.ContractDeleteView.as_view(), name='contract_delete'),
    path('<int:pk>/add-increase/', views.add_contract_increase, name='add_increase'),
    
    # AJAX
    path('ajax/get_property_rental_price/', views.get_property_rental_price, name='get_property_rental_price'),
]