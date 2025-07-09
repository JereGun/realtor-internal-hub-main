from django.db import models
from core.models import BaseModel

class Currency(BaseModel):
    name = models.CharField(max_length=64, unique=True)
    code = models.CharField(max_length=8, unique=True)
    symbol = models.CharField(max_length=8, blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Moneda'
        verbose_name_plural = 'Monedas'

    def __str__(self):
        return f"{self.name} ({self.code})"

class Company(BaseModel):
    name = models.CharField(max_length=128, unique=True)
    vat = models.CharField(max_length=32, blank=True)
    currency = models.ForeignKey('Currency', on_delete=models.PROTECT, related_name='companies')
    active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Empresa'
        verbose_name_plural = 'Empresas'

    def __str__(self):
        return self.name

class AccountTag(BaseModel):
    name = models.CharField(max_length=64, unique=True)
    code = models.CharField(max_length=16, unique=True)

    class Meta:
        verbose_name = 'Etiqueta de Cuenta'
        verbose_name_plural = 'Etiquetas de Cuenta'

    def __str__(self):
        return self.name

class Account(BaseModel):
    ACCOUNT_TYPES = [
        ('asset', 'Activo'),
        ('liability', 'Pasivo'),
        ('equity', 'Patrimonio'),
        ('income', 'Ingreso'),
        ('expense', 'Gasto'),
        ('other', 'Otro'),
    ]
    name = models.CharField(max_length=128)
    code = models.CharField(max_length=32, unique=True)
    account_type = models.CharField(max_length=16, choices=ACCOUNT_TYPES)
    currency = models.ForeignKey('Currency', on_delete=models.SET_NULL, null=True, blank=True, related_name='accounts')
    reconcile = models.BooleanField(default=False)
    company = models.ForeignKey('Company', on_delete=models.CASCADE, related_name='accounts')
    tags = models.ManyToManyField('AccountTag', blank=True, related_name='accounts')

    class Meta:
        verbose_name = 'Cuenta Contable'
        verbose_name_plural = 'Cuentas Contables'
        unique_together = ('code', 'company')

    def __str__(self):
        return f"{self.code} - {self.name}"

class Journal(BaseModel):
    name = models.CharField(max_length=128)
    code = models.CharField(max_length=16, unique=True)
    type = models.CharField(max_length=32, choices=[
        ('sale', 'Ventas'),
        ('purchase', 'Compras'),
        ('bank', 'Bancos'),
        ('cash', 'Caja'),
        ('general', 'General'),
    ])
    company = models.ForeignKey('Company', on_delete=models.CASCADE, related_name='journals')
    sequence = models.PositiveIntegerField(default=1)

    class Meta:
        verbose_name = 'Diario Contable'
        verbose_name_plural = 'Diarios Contables'

    def __str__(self):
        return f"{self.code} - {self.name}"
