
from django.contrib.auth.models import AbstractUser
from django.db import models
from core.models import BaseModel


class Agent(AbstractUser, BaseModel):
    """
    Modelo de Agente que extiende el modelo de Usuario de Django.
    
    Representa a los agentes inmobiliarios del sistema con información
    personal y profesional como número de licencia, biografía e imagen.
    Utiliza el email como campo de autenticación principal.
    """
    first_name = models.CharField(max_length=150, verbose_name="Nombre")
    last_name = models.CharField(max_length=150, verbose_name="Apellido")
    email = models.EmailField(unique=True, verbose_name="Email")
    phone = models.CharField(max_length=20, blank=True, verbose_name="Teléfono")
    license_number = models.CharField(max_length=50, unique=True, verbose_name="Número de Matrícula")
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
        """
        Propiedad que devuelve el nombre completo del agente.
        
        Returns:
            str: Nombre y apellido concatenados del agente.
        """
        return f"{self.first_name} {self.last_name}"
    
    def get_full_name(self):
        """
        Método para obtener el nombre completo del agente - compatible con el modelo User de Django.
        
        Este método sobrescribe el método get_full_name de AbstractUser para proporcionar
        una implementación consistente con el resto del sistema.
        
        Returns:
            str: Nombre completo del agente (nombre y apellido concatenados).
        """
        return f"{self.first_name} {self.last_name}".strip()
