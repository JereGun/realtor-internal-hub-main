
from django.db import models


class BaseModel(models.Model):
    """
    Modelo base abstracto que proporciona campos comunes para todos los modelos del sistema.
    
    Incluye campos para el seguimiento de la creación y actualización de registros,
    permitiendo una auditoría básica de los datos en el sistema.
    """
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Company(models.Model):
    """
    Modelo para almacenar información de la empresa inmobiliaria.
    
    Contiene datos básicos de la empresa como nombre, dirección, información
    de contacto, logotipo e identificación fiscal, necesarios para la
    generación de documentos y configuración del sistema.
    """
    name = models.CharField(max_length=255, help_text="Nombre de la empresa")
    address = models.CharField(max_length=255, blank=True, null=True, help_text="Dirección de la empresa")
    phone = models.CharField(max_length=20, blank=True, null=True, help_text="Teléfono de contacto")
    email = models.EmailField(blank=True, null=True, help_text="Correo electrónico de la empresa")
    website = models.URLField(blank=True, null=True, help_text="Sitio web de la empresa")
    logo = models.ImageField(upload_to='logos/', blank=True, null=True, help_text="Logotipo de la empresa")
    tax_id = models.CharField(max_length=50, blank=True, null=True, help_text="NIF/CIF de la empresa")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Compañía"
        verbose_name_plural = "Compañías"
