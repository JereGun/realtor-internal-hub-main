from django.db import models
from core.models import BaseModel

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
