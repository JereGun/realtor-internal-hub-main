
from django.urls import path
from . import views

app_name = 'customers'

urlpatterns = [
    path('', views.CustomerListView.as_view(), name='customer_list'),
    path('<int:pk>/', views.CustomerDetailView.as_view(), name='customer_detail'),
    path('create/', views.CustomerCreateView.as_view(), name='customer_create'),
    path('<int:pk>/edit/', views.CustomerUpdateView.as_view(), name='customer_edit'),
    path('<int:pk>/delete/', views.CustomerDeleteView.as_view(), name='customer_delete'),
]
