from django.urls import path
from . import views_web

app_name = 'accounting'

urlpatterns = [
    path('dashboard/', views_web.accounting_dashboard, name='accounting_dashboard'),
    path('invoices/', views_web.invoice_list, name='invoice_list'),
    path('invoices/create/', views_web.invoice_create, name='invoice_create'),
    path('invoices/<int:pk>/', views_web.invoice_detail, name='invoice_detail'),
    path('invoices/<int:pk>/edit/', views_web.invoice_update, name='invoice_update'),
    path('invoices/<int:pk>/pdf/', views_web.invoice_pdf, name='invoice_pdf'),
    path('invoices/<int:pk>/delete/', views_web.invoice_delete, name='invoice_delete'),
    path('invoices/<int:invoice_pk>/invoicelines/create/', views_web.invoiceline_create, name='invoiceline_create'),
    path('invoicelines/<int:pk>/edit/', views_web.invoiceline_update, name='invoiceline_update'),
    path('invoicelines/<int:pk>/delete/', views_web.invoiceline_delete, name='invoiceline_delete'),
    path('payments/', views_web.payment_list, name='payment_list'),
    path('invoices/<int:invoice_pk>/payments/create/', views_web.payment_create, name='payment_create'),
    path('payments/<int:pk>/', views_web.payment_detail, name='payment_detail'),
    path('payments/<int:pk>/edit/', views_web.payment_update, name='payment_update'),
    path('payments/<int:pk>/delete/', views_web.payment_delete, name='payment_delete'),
]
