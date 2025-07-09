from rest_framework import routers
from .views import (
    PaymentViewSet, InvoiceViewSet, InvoiceLineViewSet
)

router = routers.DefaultRouter()
router.register(r'payments', PaymentViewSet)
router.register(r'invoices', InvoiceViewSet)
router.register(r'invoice-lines', InvoiceLineViewSet)

urlpatterns = router.urls
