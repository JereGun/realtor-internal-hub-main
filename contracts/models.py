from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from core.models import BaseModel
from decimal import Decimal


class Contract(BaseModel):
    """
    Modelo de Contrato que representa acuerdos entre clientes y propietarios.
    
    Almacena información detallada sobre contratos inmobiliarios, incluyendo
    datos de la propiedad, cliente, agente, fechas, montos, términos de aumento
    y estado actual del contrato. Gestiona la lógica de estados y aumentos periódicos.
    """
    
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
    
    # Automatic Price Increase (without percentage - agent will set new amount directly)
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, blank=True, null=True, verbose_name="Frecuencia de Aumento")
    next_increase_date = models.DateField(blank=True, null=True, verbose_name="Fecha del Próximo Aumento")

    # Additional Information
    terms = models.TextField(blank=True, verbose_name="Términos y Condiciones")
    notes = models.TextField(blank=True, verbose_name="Notas")

    STATUS_DRAFT = 'draft'
    STATUS_ACTIVE = 'active'
    STATUS_FINISHED = 'finished'
    STATUS_CANCELLED = 'cancelled'
    
    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Borrador'),
        (STATUS_ACTIVE, 'Activo'),
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
        
        # Constraints de base de datos
        constraints = [
            # Evitar contratos duplicados para la misma propiedad y cliente en fechas superpuestas
            models.UniqueConstraint(
                fields=['property', 'customer', 'start_date'],
                name='unique_property_customer_start_date',
                violation_error_message="Ya existe un contrato para esta propiedad y cliente en la misma fecha de inicio."
            ),
            # Validar que el monto sea positivo
            models.CheckConstraint(
                check=models.Q(amount__gt=0),
                name='positive_amount',
                violation_error_message="El monto del contrato debe ser mayor a cero."
            ),
            # Validar que la fecha de fin sea posterior a la fecha de inicio (cuando existe)
            models.CheckConstraint(
                check=models.Q(end_date__isnull=True) | models.Q(end_date__gt=models.F('start_date')),
                name='end_date_after_start_date',
                violation_error_message="La fecha de fin debe ser posterior a la fecha de inicio."
            ),

        ]
        
        # Índices para mejorar performance
        indexes = [
            models.Index(fields=['property', 'status']),
            models.Index(fields=['customer', 'status']),
            models.Index(fields=['agent', 'status']),
            models.Index(fields=['start_date', 'end_date']),
            models.Index(fields=['next_increase_date']),
            models.Index(fields=['is_active', 'status']),
        ]
    
    def __str__(self):
        return f"Contrato ({self.get_status_display()}) - {self.property.title} - {self.customer.full_name}"
    
    def clean(self):
        """
        Validaciones personalizadas del modelo Contract.
        
        Realiza validaciones que no se pueden hacer con constraints de base de datos,
        como validaciones que requieren lógica compleja o consultas a otros modelos.
        
        Raises:
            ValidationError: Si alguna validación falla.
        """
        errors = {}
        
        # Validar fechas
        if self.start_date and self.end_date:
            if self.start_date >= self.end_date:
                errors['end_date'] = "La fecha de fin debe ser posterior a la fecha de inicio."
            
            # Validar que el contrato no sea demasiado largo (más de 10 años)
            if (self.end_date - self.start_date).days > 3650:  # 10 años
                errors['end_date'] = "La duración del contrato no puede exceder 10 años."
        
        # Validar que la fecha de inicio no sea muy antigua (más de 1 año atrás)
        if self.start_date:
            one_year_ago = timezone.now().date().replace(year=timezone.now().date().year - 1)
            if self.start_date < one_year_ago:
                errors['start_date'] = "La fecha de inicio no puede ser anterior a un año atrás."
        
        # Validar monto
        if self.amount is not None and self.amount <= 0:
            errors['amount'] = "El monto debe ser mayor a cero."
        
        # Validar que no existan contratos activos superpuestos para la misma propiedad
        if self.property_id and self.start_date:
            overlapping_contracts = Contract.objects.filter(
                property=self.property,
                status__in=[self.STATUS_ACTIVE, self.STATUS_DRAFT]
            ).exclude(pk=self.pk)
            
            for contract in overlapping_contracts:
                # Verificar superposición de fechas
                if self._dates_overlap(
                    self.start_date, self.end_date,
                    contract.start_date, contract.end_date
                ):
                    errors['start_date'] = f"Ya existe un contrato activo para esta propiedad que se superpone con las fechas seleccionadas (Contrato #{contract.pk})."
                    break
        
        # Validar fecha de próximo aumento
        if self.next_increase_date:
            if self.start_date and self.next_increase_date < self.start_date:
                errors['next_increase_date'] = "La fecha del próximo aumento no puede ser anterior a la fecha de inicio."
            
            if self.end_date and self.next_increase_date > self.end_date:
                errors['next_increase_date'] = "La fecha del próximo aumento no puede ser posterior a la fecha de fin."
        
        if errors:
            raise ValidationError(errors)
    
    def _dates_overlap(self, start1, end1, start2, end2):
        """
        Verifica si dos rangos de fechas se superponen.
        
        Args:
            start1, end1: Primer rango de fechas
            start2, end2: Segundo rango de fechas
            
        Returns:
            bool: True si los rangos se superponen
        """
        # Si alguna fecha de fin es None, se considera que el contrato no tiene fin
        if end1 is None:
            end1 = timezone.now().date().replace(year=9999)  # Fecha muy lejana
        if end2 is None:
            end2 = timezone.now().date().replace(year=9999)
            
        return start1 <= end2 and start2 <= end1
    
    def duration_in_days(self):
        """
        Calcula la duración del contrato en días.
        
        Returns:
            int: Número de días entre la fecha de inicio y fin del contrato,
                 o None si no hay fecha de fin establecida.
        """
        if self.end_date and self.start_date:
            return (self.end_date - self.start_date).days
        return None

    def is_expiring_soon(self, days_threshold=30):
        """
        Verifica si un contrato está próximo a vencer dentro del umbral especificado.
        
        Args:
            days_threshold (int): Número de días para considerar que un contrato está próximo a vencer.
                                 Por defecto es 30 días.
        
        Returns:
            bool: True si el contrato está activo y vence dentro del umbral especificado,
                  False en caso contrario.
        """
        if self.end_date and self.status == self.STATUS_ACTIVE:
            from django.utils import timezone
            return self.start_date <= timezone.now().date() <= self.end_date and \
                   (self.end_date - timezone.now().date()).days <= days_threshold
        return False

    def update_status(self):
        """
        Actualiza el estado del contrato basándose en las fechas actuales.
        
        Evalúa la fecha actual en relación con las fechas de inicio y fin del contrato
        para determinar su estado (borrador, activo, finalizado). Los contratos se
        finalizan automáticamente cuando pasa la fecha de fin.
        Este método puede ser llamado periódicamente por un trabajo programado
        o al guardar el modelo.
        """
        from django.utils import timezone
        today = timezone.now().date()

        # No cambiar estados ya finalizados a menos que se haga explícitamente
        if self.status == self.STATUS_CANCELLED or self.status == self.STATUS_FINISHED:
            return

        # Finalizar automáticamente si pasó la fecha de fin
        if self.end_date and today > self.end_date:
            self.status = self.STATUS_FINISHED
            self.is_active = False
        # Si aún no empezó, mantener como borrador
        elif self.start_date > today:
            self.status = self.STATUS_DRAFT
        # Si está en el período activo, marcar como activo
        elif self.start_date <= today and (not self.end_date or today <= self.end_date):
            self.status = self.STATUS_ACTIVE
            self.is_active = True

    def commission_amount(self):
        """
        Calcula la comisión del agente basada en su tasa y el monto del contrato.
        
        Utiliza el atributo commission_rate del agente (si existe) para calcular
        el monto de la comisión como un porcentaje del valor del contrato.
        
        Returns:
            Decimal: Monto de la comisión calculada, o 0.00 si no se puede calcular.
        """
        if self.agent and hasattr(self.agent, 'commission_rate') and self.amount:
            # Ensure agent has commission_rate attribute
            commission_rate = getattr(self.agent, 'commission_rate', Decimal('0.00'))
            if commission_rate is None: # handle case where commission_rate might be None
                commission_rate = Decimal('0.00')
            return self.amount * (commission_rate / Decimal('100'))
        return Decimal('0.00')

    def save(self, *args, **kwargs):
        """
        Guarda el contrato y actualiza automáticamente su estado basándose en las fechas.
        """
        # Actualizar estado antes de guardar
        self.update_status()
        super().save(*args, **kwargs)


class ContractIncrease(BaseModel):
    """
    Modelo que registra los aumentos de precio en contratos de alquiler.
    
    Almacena información sobre cada ajuste de precio realizado a un contrato,
    incluyendo el monto anterior, el nuevo monto, el porcentaje de aumento,
    la fecha efectiva y notas adicionales. Incluye validaciones para garantizar
    la integridad de los datos de aumento.
    """
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
        
        # Constraints de base de datos
        constraints = [
            # Evitar aumentos duplicados en la misma fecha para el mismo contrato
            models.UniqueConstraint(
                fields=['contract', 'effective_date'],
                name='unique_contract_increase_date',
                violation_error_message="Ya existe un aumento para este contrato en la misma fecha."
            ),
            # Validar que los montos sean positivos
            models.CheckConstraint(
                check=models.Q(previous_amount__gt=0),
                name='positive_previous_amount',
                violation_error_message="El monto anterior debe ser mayor a cero."
            ),
            models.CheckConstraint(
                check=models.Q(new_amount__gt=0),
                name='positive_new_amount',
                violation_error_message="El nuevo monto debe ser mayor a cero."
            ),
            # Validar que el porcentaje de aumento sea razonable
            models.CheckConstraint(
                check=models.Q(increase_percentage__gte=-100, increase_percentage__lte=1000),
                name='reasonable_increase_percentage_range',
                violation_error_message="El porcentaje de aumento debe estar entre -100% y 1000%."
            ),
        ]
        
        # Índices para mejorar performance
        indexes = [
            models.Index(fields=['contract', 'effective_date']),
            models.Index(fields=['effective_date']),
        ]
    
    def __str__(self):
        return f"Aumento {self.increase_percentage}% - {self.contract}"
    
    def clean(self):
        """
        Valida la instancia de ContractIncrease antes de guardarla.
        
        Realiza las siguientes validaciones:
        - La fecha efectiva es lógica respecto a las fechas del contrato y aumentos previos.
        - El monto anterior es positivo si se proporciona un nuevo monto (para cálculo de porcentaje).
        
        Raises:
            ValidationError: Si alguna de las validaciones falla, con mensajes específicos
                            para cada tipo de error.
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
        """
        Guarda la instancia de ContractIncrease y calcula automáticamente el porcentaje de aumento.
        
        Si el porcentaje de aumento no está establecido o es cero, lo calcula automáticamente
        basándose en el monto anterior y el nuevo monto. Si el monto anterior no es válido
        o no está establecido, establece el porcentaje de aumento como None.
        
        Args:
            *args: Argumentos variables para el método save.
            **kwargs: Argumentos de palabras clave para el método save.
        """
        # Calculate increase percentage if not provided and amounts are valid
        if self.previous_amount and self.new_amount and self.previous_amount > 0:
            if self.increase_percentage is None or self.increase_percentage == 0: # Recalculate if not set or zero
                self.increase_percentage = ((self.new_amount - self.previous_amount) / self.previous_amount) * 100
        else:
            # If previous_amount is zero or not set, percentage cannot be calculated
            self.increase_percentage = None 
            
        super().save(*args, **kwargs)
