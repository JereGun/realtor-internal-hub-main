
from django.db import models
from core.models import BaseModel


class Customer(BaseModel):
    """Customer model"""
    # Personal Information
    first_name = models.CharField(max_length=150, verbose_name="Nombre")
    last_name = models.CharField(max_length=150, verbose_name="Apellido")
    email = models.EmailField(unique=True, verbose_name="Email")
    phone = models.CharField(max_length=20, verbose_name="Teléfono")
    document = models.CharField(max_length=20, unique=True, verbose_name="Documento")
    
    # Address Information
    street = models.CharField(max_length=200, blank=True, verbose_name="Calle")
    number = models.CharField(max_length=20, blank=True, verbose_name="Número")
    neighborhood = models.CharField(max_length=100, blank=True, verbose_name="Barrio")
    locality = models.CharField(max_length=100, blank=True, verbose_name="Localidad")
    province = models.CharField(max_length=100, blank=True, verbose_name="Provincia")
    country = models.CharField(max_length=100, default="Argentina", verbose_name="País")
    
    # Additional Information
    birth_date = models.DateField(blank=True, null=True, verbose_name="Fecha de Nacimiento")
    profession = models.CharField(max_length=100, blank=True, verbose_name="Profesión")
    notes = models.TextField(blank=True, verbose_name="Notas")
    
    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        ordering = ['first_name', 'last_name']
    
    def __str__(self):
        return f"{self.first_name} {self.last_name}"
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    @property
    def full_address(self):
        if self.street and self.number:
            return f"{self.street} {self.number}, {self.neighborhood}, {self.locality}, {self.province}"
        return ""
