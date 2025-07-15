from django.urls import path
from .views import dashboard, company_settings

app_name = 'core'

urlpatterns = [
    path('dashboard/', dashboard, name='dashboard'),
    path('company-settings/', company_settings, name='company_settings'),
]
