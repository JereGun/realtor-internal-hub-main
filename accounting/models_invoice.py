from django.db import models
from core.models import BaseModel
from customers.models import Customer
from properties.models import Property

class Invoice(BaseModel):
    STATE_CHOICES = [
        ('draft', 'Borrador'),
        ('sent', 'Enviada'),
        ('paid', 'Pagada'),
        ('cancelled', 'Cancelada'),
    ]
    number = models.CharField(max_length=64, unique=True)
    date = models.DateField()
    due_date = models.DateField()
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='invoices')
    description = models.TextField()
    total_amount = models.DecimalField(max_digits=14, decimal_places=2)
    state = models.CharField(max_length=16, choices=STATE_CHOICES, default='draft')
    contract = models.ForeignKey('contracts.Contract', on_delete=models.SET_NULL, null=True, blank=True, related_name='accounting_invoices')
    property = models.ForeignKey(Property, on_delete=models.SET_NULL, null=True, blank=True, related_name='invoices')

    class Meta:
        verbose_name = 'Factura'
        verbose_name_plural = 'Facturas'
        ordering = ['-date']

    def __str__(self):
        return f"Factura Nº{self.number} - {self.customer}"

    def mark_as_paid(self):
        total_paid = sum(p.amount for p in self.payments.all())
        if total_paid >= self.total_amount:
            self.state = 'paid'
            self.save(update_fields=['state'])

    def mark_as_sent(self):
        self.state = 'sent'
        self.save(update_fields=['state'])

    def compute_taxes(self):
        # Lógica de cálculo de impuestos (placeholder)
        self.total_amount = sum(line.amount for line in self.lines.all())
        self.save(update_fields=['total_amount'])

class InvoiceLine(BaseModel):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='lines')
    concept = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=14, decimal_places=2)

    class Meta:
        verbose_name = 'Línea de Factura'
        verbose_name_plural = 'Líneas de Factura'

    def __str__(self):
        return f"{self.concept} ({self.amount})"

class Payment(BaseModel):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='payments')
    date = models.DateField()
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    method = models.CharField(max_length=100)
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Pago'
        verbose_name_plural = 'Pagos'
        ordering = ['-date']

    def __str__(self):
        return f"Pago {self.amount} a Factura Nº{self.invoice.number}"
