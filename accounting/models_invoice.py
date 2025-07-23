from django.db import models
from core.models import BaseModel
from customers.models import Customer


class Invoice(BaseModel):
    """
    Modelo que representa una factura en el sistema.

    Una factura está asociada a un cliente y opcionalmente a un contrato.
    Contiene información sobre el monto total, fechas de emisión y vencimiento,
    y su estado actual en el ciclo de facturación.
    """

    STATUS_CHOICES = [
        ("draft", "Borrador"),
        ("validated", "Validada"),
        ("sent", "Enviada"),
        ("paid", "Pagada"),
        ("cancelled", "Cancelada"),
    ]
    number = models.CharField(max_length=64, unique=True)
    date = models.DateField()
    due_date = models.DateField()
    customer = models.ForeignKey(
        Customer, on_delete=models.PROTECT, related_name="invoices"
    )
    contract = models.ForeignKey(
        "contracts.Contract",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invoices",
        verbose_name="Contrato",
    )
    description = models.TextField()
    total_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0.0)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="draft")

    class Meta:
        verbose_name = "Factura"
        verbose_name_plural = "Facturas"
        ordering = ["-date"]

    def __str__(self):
        return f"Factura Nº{self.number} - {self.customer}"

    def get_balance(self):
        """
        Calcula el saldo pendiente de la factura.

        Returns:
            Decimal: La diferencia entre el monto total de la factura y la suma de todos los pagos realizados.
        """
        paid_amount = self.payments.aggregate(total=models.Sum("amount"))["total"] or 0
        return self.total_amount - paid_amount

    def update_status(self):
        """
        Actualiza el estado de la factura basándose en el saldo pendiente.

        Si el saldo es cero o negativo, marca la factura como pagada.
        Si la factura estaba marcada como pagada pero tiene saldo pendiente,
        la devuelve al estado 'enviada'.
        """
        balance = self.get_balance()
        if balance <= 0:
            self.status = "paid"
        elif self.status == "paid" and balance > 0:
            self.status = "sent"  # o el estado que corresponda
        self.save()

    def mark_as_sent(self):
        """
        Marca la factura como enviada.

        Actualiza el estado de la factura a 'sent' (enviada) y guarda
        únicamente este campo para optimizar la operación de guardado.
        """
        self.status = "sent"
        self.save(update_fields=["status"])

    def compute_total(self):
        """
        Calcula y actualiza el monto total de la factura.

        Suma los importes de todas las líneas de factura asociadas
        y actualiza el campo total_amount con el resultado.
        """
        self.total_amount = sum(line.amount for line in self.lines.all())
        self.save()


class InvoiceLine(BaseModel):
    """
    Modelo que representa una línea o concepto individual dentro de una factura.

    Cada línea está asociada a una factura específica y contiene información
    sobre el concepto facturado y su importe correspondiente.
    """

    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="lines")
    concept = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=14, decimal_places=2)

    class Meta:
        verbose_name = "Línea de Factura"
        verbose_name_plural = "Líneas de Factura"

    def __str__(self):
        return f"{self.concept} ({self.amount})"


class Payment(BaseModel):
    """
    Modelo que representa un pago realizado para una factura.

    Registra información sobre la fecha del pago, el importe abonado,
    el método de pago utilizado y notas adicionales relacionadas con la transacción.
    """

    invoice = models.ForeignKey(
        Invoice, on_delete=models.CASCADE, related_name="payments"
    )
    date = models.DateField()
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    method = models.CharField(max_length=100)
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = "Pago"
        verbose_name_plural = "Pagos"
        ordering = ["-date"]

    def __str__(self):
        return f"Pago {self.amount} a Factura Nº{self.invoice.number}"
