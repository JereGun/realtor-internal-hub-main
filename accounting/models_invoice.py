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

    @classmethod
    def get_overdue_invoices(cls):
        """
        Get invoices that are overdue with outstanding balances.
        
        Returns:
            QuerySet: Invoices that are past their due date and not fully paid
        """
        from django.utils import timezone
        today = timezone.now().date()
        
        return cls.objects.filter(
            due_date__lt=today,
            status__in=['validated', 'sent']  # Exclude draft, paid, and cancelled
        ).select_related('customer', 'contract__agent')

    @classmethod
    def get_due_soon_invoices(cls, days_threshold=7):
        """
        Get invoices due within the specified threshold.
        
        Args:
            days_threshold (int): Number of days to look ahead for due invoices
            
        Returns:
            QuerySet: Invoices due within the threshold
        """
        from django.utils import timezone
        today = timezone.now().date()
        threshold_date = today + timezone.timedelta(days=days_threshold)
        
        return cls.objects.filter(
            due_date__lte=threshold_date,
            due_date__gte=today,
            status__in=['validated', 'sent']  # Exclude draft, paid, and cancelled
        ).select_related('customer', 'contract__agent')

    def days_until_due(self):
        """
        Calculate the number of days until this invoice is due.
        
        Returns:
            int: Number of days until due (negative if overdue)
        """
        from django.utils import timezone
        today = timezone.now().date()
        return (self.due_date - today).days

    def days_overdue(self):
        """
        Calculate the number of days this invoice is overdue.
        
        Returns:
            int: Number of days overdue (0 if not overdue)
        """
        from django.utils import timezone
        today = timezone.now().date()
        if self.due_date >= today:
            return 0
        return (today - self.due_date).days

    def is_overdue(self):
        """
        Check if this invoice is overdue.
        
        Returns:
            bool: True if the invoice is past its due date
        """
        from django.utils import timezone
        today = timezone.now().date()
        return self.due_date < today and self.get_balance() > 0

    def is_due_soon(self, days_threshold=7):
        """
        Check if this invoice is due within the specified threshold.
        
        Args:
            days_threshold (int): Number of days to consider as "due soon"
            
        Returns:
            bool: True if the invoice is due within the threshold
        """
        from django.utils import timezone
        today = timezone.now().date()
        threshold_date = today + timezone.timedelta(days=days_threshold)
        
        return (self.due_date <= threshold_date and 
                self.due_date >= today and 
                self.get_balance() > 0)

    def get_notification_urgency_level(self, notification_type):
        """
        Determine the urgency level for notifications related to this invoice.
        
        Args:
            notification_type (str): Type of notification ('overdue' or 'due_soon')
            
        Returns:
            str: Urgency level ('low', 'medium', 'high', 'critical')
        """
        if notification_type == 'overdue':
            days_overdue = self.days_overdue()
            if days_overdue >= 30:
                return 'critical'  # 30+ days overdue
            elif days_overdue >= 7:
                return 'high'      # 7-29 days overdue
            elif days_overdue > 0:
                return 'medium'    # 1-6 days overdue
            else:
                return 'low'       # Not overdue
        
        elif notification_type == 'due_soon':
            days_until_due = self.days_until_due()
            if days_until_due <= 3:
                return 'high'      # Due within 3 days
            elif days_until_due <= 7:
                return 'medium'    # Due within 7 days
            else:
                return 'low'
        
        return 'low'

    def needs_overdue_notification(self):
        """
        Check if this invoice needs an overdue notification.
        
        Returns:
            bool: True if the invoice is overdue with outstanding balance
        """
        return self.is_overdue() and self.status in ['validated', 'sent']

    def needs_due_soon_notification(self, days_threshold=7):
        """
        Check if this invoice needs a due soon notification.
        
        Args:
            days_threshold (int): Number of days to consider as "due soon"
            
        Returns:
            bool: True if the invoice is due soon with outstanding balance
        """
        return self.is_due_soon(days_threshold) and self.status in ['validated', 'sent']


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
