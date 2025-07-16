
from django.contrib.auth.models import AbstractUser
from django.db import models
from core.models import BaseModel


class Agent(AbstractUser, BaseModel):
    """Agent model extending Django's User model"""
    first_name = models.CharField(max_length=150, verbose_name="Nombre")
    last_name = models.CharField(max_length=150, verbose_name="Apellido")
    email = models.EmailField(unique=True, verbose_name="Email")
    phone = models.CharField(max_length=20, blank=True, verbose_name="Teléfono")
    license_number = models.CharField(max_length=50, unique=True, verbose_name="Número de Matrícula")
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=3.00, verbose_name="Tasa de Comisión (%)")
    is_active = models.BooleanField(default=True, verbose_name="Activo")
    image_path = models.ImageField(upload_to='agents/', blank=True, null=True, verbose_name="Foto de Perfil")
    bio = models.TextField(blank=True, verbose_name="Biografía")
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']
    
    class Meta:
        verbose_name = "Agente"
        verbose_name_plural = "Agentes"
    
    def __str__(self):
        return f"{self.first_name} {self.last_name}"
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def get_full_name(self):
        """Method to get full name - compatible with Django's User model"""
        return f"{self.first_name} {self.last_name}".strip()
