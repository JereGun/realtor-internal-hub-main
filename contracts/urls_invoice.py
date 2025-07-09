from django.urls import path
from . import views

urlpatterns = [
    path('invoices/', views.InvoiceListView.as_view(), name='invoice_list'),
    path('invoices/<int:pk>/', views.InvoiceDetailView.as_view(), name='invoice_detail'),
    path('invoices/create/', views.InvoiceCreateView.as_view(), name='invoice_create'),
    path('invoices/<int:pk>/edit/', views.InvoiceUpdateView.as_view(), name='invoice_edit'),
    path('invoices/<int:pk>/delete/', views.InvoiceDeleteView.as_view(), name='invoice_delete'),
    path('invoices/<int:invoice_pk>/items/add/', views.InvoiceItemCreateView.as_view(), name='invoiceitem_create'),
    path('invoices/items/<int:pk>/edit/', views.InvoiceItemUpdateView.as_view(), name='invoiceitem_edit'),
    path('invoices/items/<int:pk>/delete/', views.InvoiceItemDeleteView.as_view(), name='invoiceitem_delete'),
]
