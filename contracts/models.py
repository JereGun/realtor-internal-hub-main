from django.db import models
from core.models import BaseModel
from decimal import Decimal


class Contract(BaseModel):
    """Contract model"""
    
    FREQUENCY_CHOICES = [
        ('monthly', 'Mensual'),
        ('quarterly', 'Trimestral'),
        ('semi-annually', 'Semestral'),
        ('annually', 'Anual'),
    ]

    # Basic Information
    property = models.ForeignKey('properties.Property', on_delete=models.CASCADE, verbose_name="Propiedad")
    customer = models.ForeignKey('customers.Customer', on_delete=models.CASCADE, verbose_name="Cliente")
    agent = models.ForeignKey('agents.Agent', on_delete=models.CASCADE, verbose_name="Agente")
    
    # Contract Details
    is_active = models.BooleanField(default=True, verbose_name='Activo', help_text='Indica si el contrato está activo')
    start_date = models.DateField(verbose_name="Fecha de Inicio")
    end_date = models.DateField(blank=True, null=True, verbose_name="Fecha de Fin")
    
    # Financial Information
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Monto")
    currency = models.CharField(max_length=10, default='ARS', verbose_name="Moneda")
    
    # Automatic Price Increase
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, blank=True, null=True, verbose_name="Frecuencia de Aumento")
    increase_percentage = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, verbose_name="Porcentaje de Aumento")
    next_increase_date = models.DateField(blank=True, null=True, verbose_name="Fecha del Próximo Aumento")

    # Additional Information
    terms = models.TextField(blank=True, verbose_name="Términos y Condiciones")
    notes = models.TextField(blank=True, verbose_name="Notas")

    STATUS_DRAFT = 'draft'
    STATUS_ACTIVE = 'active'
    STATUS_EXPIRING_SOON = 'expiring_soon' # Podría ser manejado por una propiedad también
    STATUS_FINISHED = 'finished'
    STATUS_CANCELLED = 'cancelled'
    
    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Borrador'),
        (STATUS_ACTIVE, 'Activo'),
        (STATUS_EXPIRING_SOON, 'Próximo a Vencer'),
        (STATUS_FINISHED, 'Finalizado'),
        (STATUS_CANCELLED, 'Cancelado'),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT,
        verbose_name="Estado del Contrato"
    )
    
    class Meta:
        verbose_name = "Contrato"
        verbose_name_plural = "Contratos"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Contrato ({self.get_status_display()}) - {self.property.title} - {self.customer.full_name}"
    
    def duration_in_days(self):
        """Calculates the duration of the contract in days if end_date is set."""
        if self.end_date and self.start_date:
            return (self.end_date - self.start_date).days
        return None

    def is_expiring_soon(self, days_threshold=30):
        """Checks if a contract is expiring within the given threshold (default 30 days)."""
        if self.end_date and self.status == self.STATUS_ACTIVE:
            from django.utils import timezone
            return self.start_date <= timezone.now().date() <= self.end_date and \
                   (self.end_date - timezone.now().date()).days <= days_threshold
        return False

    def update_status(self):
        """Updates the contract status based on dates. 
           This could be called periodically by a cron job or upon model save.
        """
        from django.utils import timezone
        today = timezone.now().date()

        if self.status == self.STATUS_CANCELLED or self.status == self.STATUS_FINISHED:
            return # Do not change already finalized states unless explicitly done

        if self.end_date and today > self.end_date:
            self.status = self.STATUS_FINISHED
        elif self.start_date > today:
            self.status = self.STATUS_DRAFT # Or perhaps a 'Pending Start' status
        elif self.is_expiring_soon: # Check before active if it's expiring soon
            self.status = self.STATUS_EXPIRING_SOON
        elif self.start_date <= today and (not self.end_date or today <= self.end_date):
            self.status = self.STATUS_ACTIVE
        
        # Consider saving the instance if status changed, or let the caller handle it.
        # self.save(update_fields=['status'])

    def commission_amount(self):
        """Calculate commission based on agent's rate and contract amount."""
        if self.agent and hasattr(self.agent, 'commission_rate') and self.amount:
            # Ensure agent has commission_rate attribute
            commission_rate = getattr(self.agent, 'commission_rate', Decimal('0.00'))
            if commission_rate is None: # handle case where commission_rate might be None
                commission_rate = Decimal('0.00')
            return self.amount * (commission_rate / Decimal('100'))
        return Decimal('0.00')


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
    
    def clean(self):
        """
        Validates the ContractIncrease instance before saving, ensuring:
        - Effective date is logical with respect to contract dates and previous increases.
        - Previous amount is positive if new amount is also provided (for percentage calculation).
        """
        from django.core.exceptions import ValidationError
        # Validate effective_date
        if self.contract and self.effective_date:
            if self.effective_date < self.contract.start_date:
                raise ValidationError({'effective_date': "La fecha efectiva no puede ser anterior a la fecha de inicio del contrato."})
            if self.contract.end_date and self.effective_date > self.contract.end_date:
                raise ValidationError({'effective_date': "La fecha efectiva no puede ser posterior a la fecha de fin del contrato."})

            # Check against last increase
            last_increase = ContractIncrease.objects.filter(contract=self.contract).order_by('-effective_date').first()
            if last_increase and self.pk != last_increase.pk and self.effective_date < last_increase.effective_date:
                 raise ValidationError({'effective_date': "La fecha efectiva no puede ser anterior al último aumento registrado."})

        # Validate amounts for percentage calculation
        if self.previous_amount is not None and self.new_amount is not None:
            if self.previous_amount <= 0:
                raise ValidationError({'previous_amount': "El monto anterior debe ser positivo para calcular el porcentaje."})
            if self.new_amount < self.previous_amount:
                # This is a business rule, could be a decrease, but for "increase" model, we might enforce it.
                # For now, allow it, as percentage will be negative.
                pass 
        super().clean()

    def save(self, *args, **kwargs):
        # Calculate increase percentage if not provided and amounts are valid
        if self.previous_amount and self.new_amount and self.previous_amount > 0:
            if self.increase_percentage is None or self.increase_percentage == 0: # Recalculate if not set or zero
                self.increase_percentage = ((self.new_amount - self.previous_amount) / self.previous_amount) * 100
        else:
            # If previous_amount is zero or not set, percentage cannot be calculated
            self.increase_percentage = None 
            
        super().save(*args, **kwargs)

# End of ContractIncrease model
# Invoice and InvoiceItem models are now managed by the 'accounting' app.