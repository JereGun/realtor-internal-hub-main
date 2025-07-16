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
    path('invoices/<int:pk>/send-email/', views_web.send_invoice_by_email, name='send_invoice_email'),
    path('invoices/<int:pk>/delete/', views_web.invoice_delete, name='invoice_delete'),
    path('invoices/<int:pk>/cancel/', views_web.invoice_cancel, name='invoice_cancel'),
    path('invoices/<int:pk>/reactivate/', views_web.invoice_reactivate, name='invoice_reactivate'),
    path('invoices/<int:pk>/validate/', views_web.invoice_validate, name='invoice_validate'),
    path('invoices/<int:pk>/duplicate/', views_web.invoice_duplicate, name='invoice_duplicate'),
    path('invoices/<int:invoice_pk>/invoicelines/create/', views_web.invoiceline_create, name='invoiceline_create'),
    path('invoicelines/<int:pk>/edit/', views_web.invoiceline_update, name='invoiceline_update'),
    path('invoicelines/<int:pk>/delete/', views_web.invoiceline_delete, name='invoiceline_delete'),
    path('payments/', views_web.payment_list, name='payment_list'),
    path('invoices/<int:invoice_pk>/payments/create/', views_web.payment_create, name='payment_create'),
    path('invoices/<int:invoice_pk>/quick-payment/', views_web.quick_payment_create, name='quick_payment_create'),
    path('payments/<int:pk>/', views_web.payment_detail, name='payment_detail'),
    path('payments/<int:pk>/edit/', views_web.payment_update, name='payment_update'),
    path('payments/<int:pk>/delete/', views_web.payment_delete, name='payment_delete'),
    path('notifications/', views_web.invoice_notifications, name='invoice_notifications'),
    path('notifications/<int:pk>/mark-as-read/', views_web.mark_notification_as_read, name='mark_notification_as_read'),
    path('notifications/mark-all-as-read/', views_web.mark_all_notifications_as_read, name='mark_all_notifications_as_read'),
]
