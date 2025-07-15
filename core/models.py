
from django.db import models


class BaseModel(models.Model):
    """Base model with common fields"""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Company(models.Model):
    """Model to store company information"""
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
