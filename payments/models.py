
from django.db import models
from core.models import BaseModel


class PaymentMethod(BaseModel):
    """Payment method model"""
    name = models.CharField(max_length=100, unique=True, verbose_name="Método de Pago")
    description = models.TextField(blank=True, verbose_name="Descripción")
    is_active = models.BooleanField(default=True, verbose_name="Activo")
    
    class Meta:
        verbose_name = "Método de Pago"
        verbose_name_plural = "Métodos de Pago"
    
    def __str__(self):
        return self.name


class ContractPayment(BaseModel):
    """Contract payment model"""
    PAYMENT_STATUS = [
        ('pending', 'Pendiente'),
        ('paid', 'Pagado'),
        ('overdue', 'Vencido'),
        ('partial', 'Parcial'),
    ]
    
    # Basic Information
    contract = models.ForeignKey('contracts.Contract', on_delete=models.CASCADE, related_name='payments', verbose_name="Contrato")
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.CASCADE, verbose_name="Método de Pago")
    
    # Payment Details
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Monto")
    due_date = models.DateField(verbose_name="Fecha de Vencimiento")
    payment_date = models.DateField(blank=True, null=True, verbose_name="Fecha de Pago")
    status = models.CharField(max_length=10, choices=PAYMENT_STATUS, default='pending', verbose_name="Estado")
    
    # Additional Information
    receipt_number = models.CharField(max_length=100, blank=True, verbose_name="Número de Recibo")
    notes = models.TextField(blank=True, verbose_name="Notas")
    
    class Meta:
        verbose_name = "Pago de Contrato"
        verbose_name_plural = "Pagos de Contratos"
        ordering = ['-due_date']
    
    def __str__(self):
        return f"Pago {self.contract} - {self.due_date} - ${self.amount}"
    
    @property
    def is_overdue(self):
        from django.utils import timezone
        return self.status == 'pending' and self.due_date < timezone.now().date()
