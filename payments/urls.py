
from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    # Contract Payments
    path('', views.ContractPaymentListView.as_view(), name='payment_list'),
    path('<int:pk>/', views.ContractPaymentDetailView.as_view(), name='payment_detail'),
    path('create/', views.ContractPaymentCreateView.as_view(), name='payment_create'),
    path('<int:pk>/edit/', views.ContractPaymentUpdateView.as_view(), name='payment_edit'),
    path('<int:pk>/delete/', views.ContractPaymentDeleteView.as_view(), name='payment_delete'),
    
    # Payment Methods
    path('methods/', views.PaymentMethodListView.as_view(), name='payment_method_list'),
    path('methods/create/', views.PaymentMethodCreateView.as_view(), name='payment_method_create'),
    path('methods/<int:pk>/edit/', views.PaymentMethodUpdateView.as_view(), name='payment_method_edit'),
]
