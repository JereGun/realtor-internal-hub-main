"""
URL configuration for real_estate_management project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('public.urls')),
    path('app/', include('core.urls')),  # Dashboard como home
    path('agents/', include('agents.urls')),
    path('properties/', include('properties.urls')),
    path('customers/', include('customers.urls')),
    path('contracts/', include('contracts.urls')),
    path('payments/', include('payments.urls')),
    path('notifications/', include('user_notifications.urls')),
    path('contabilidad/', include('accounting.urls_web')),
    path('locations/', include('locations.urls')),
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
