from django.db import models
from core.models import BaseModel
from decimal import Decimal


class Contract(BaseModel):
    """Contract model"""
    CONTRACT_TYPES = [
        ('sale', 'Venta'),
        ('rental', 'Alquiler'),
    ]
    
    # Basic Information
    property = models.ForeignKey('properties.Property', on_delete=models.CASCADE, verbose_name="Propiedad")
    customer = models.ForeignKey('customers.Customer', on_delete=models.CASCADE, verbose_name="Cliente")
    agent = models.ForeignKey('agents.Agent', on_delete=models.CASCADE, verbose_name="Agente")
    
    # Contract Details
    contract_type = models.CharField(max_length=10, choices=CONTRACT_TYPES, verbose_name="Tipo de Contrato")
    start_date = models.DateField(verbose_name="Fecha de Inicio")
    end_date = models.DateField(blank=True, null=True, verbose_name="Fecha de Fin")
    
    # Financial Information
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Monto")
    currency = models.CharField(max_length=10, default='ARS', verbose_name="Moneda")
    
    # Additional Information
    terms = models.TextField(blank=True, verbose_name="Términos y Condiciones")
    notes = models.TextField(blank=True, verbose_name="Notas")
    is_active = models.BooleanField(default=True, verbose_name="Activo")
    
    class Meta:
        verbose_name = "Contrato"
        verbose_name_plural = "Contratos"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Contrato {self.get_contract_type_display()} - {self.property.title} - {self.customer.full_name}"
    
    # @property
    # def commission_amount(self):
    #     """Calculate commission based on agent's rate"""
    #     return self.amount * (self.agent.commission_rate / Decimal('100'))


class ContractIncrease(BaseModel):
    """Contract increase model for rental adjustments"""
    contract = models.ForeignKey(Contract, on_delete=models.CASCADE, related_name='increases', verbose_name="Contrato")
    previous_amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Monto Anterior")
    new_amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Nuevo Monto")
    increase_percentage = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Porcentaje de Aumento")
    effective_date = models.DateField(verbose_name="Fecha Efectiva")
    notes = models.TextField(blank=True, verbose_name="Notas")
    
    class Meta:
        verbose_name = "Aumento de Contrato"
        verbose_name_plural = "Aumentos de Contratos"
        ordering = ['-effective_date']
    
    def __str__(self):
        return f"Aumento {self.increase_percentage}% - {self.contract}"
    
    def save(self, *args, **kwargs):
        # Calculate increase percentage if not provided
        if not self.increase_percentage and self.previous_amount and self.new_amount:
            self.increase_percentage = ((self.new_amount - self.previous_amount) / self.previous_amount) * 100
        super().save(*args, **kwargs)


class Invoice(BaseModel):
    """Factura asociada a un contrato"""
    DRAFT = 'draft'
    SENT = 'sent'
    PAID = 'paid'
    OVERDUE = 'overdue'
    CANCELLED = 'cancelled'
    STATUS_CHOICES = [
        (DRAFT, 'Borrador'),
        (SENT, 'Enviada'),
        (PAID, 'Pagada'),
        (OVERDUE, 'Vencida'),
        (CANCELLED, 'Cancelada'),
    ]
    contract = models.ForeignKey('contracts.Contract', on_delete=models.CASCADE, related_name='invoices', verbose_name="Contrato")
    issue_date = models.DateField(auto_now_add=True, verbose_name="Fecha de emisión")
    due_date = models.DateField(verbose_name="Fecha de vencimiento")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=DRAFT, verbose_name="Estado")
    notes = models.TextField(blank=True, verbose_name="Notas")

    class Meta:
        verbose_name = "Factura"
        verbose_name_plural = "Facturas"
        ordering = ['-issue_date']

    def __str__(self):
        return f"Factura #{self.id} - {self.get_status_display()}"

    @property
    def total(self):
        return sum(item.amount for item in self.items.all())

class InvoiceItem(BaseModel):
    """Ítem de una factura"""
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items', verbose_name="Factura")
    description = models.CharField(max_length=255, verbose_name="Descripción")
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Monto")

    class Meta:
        verbose_name = "Ítem de Factura"
        verbose_name_plural = "Ítems de Factura"

    def __str__(self):
        return f"{self.description} (${self.amount})"
