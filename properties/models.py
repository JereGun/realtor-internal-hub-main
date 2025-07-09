
from django.db import models
from core.models import BaseModel


class PropertyType(BaseModel):
    """Property type model (Casa, Departamento, Local, etc.)"""
    name = models.CharField(max_length=100, unique=True, verbose_name="Tipo")
    description = models.TextField(blank=True, verbose_name="Descripción")
    
    class Meta:
        verbose_name = "Tipo de Propiedad"
        verbose_name_plural = "Tipos de Propiedades"
    
    def __str__(self):
        return self.name


class PropertyStatus(BaseModel):
    """Property status model (Disponible, Vendida, Alquilada, etc.)"""
    name = models.CharField(max_length=100, unique=True, verbose_name="Estado")
    description = models.TextField(blank=True, verbose_name="Descripción")
    
    class Meta:
        verbose_name = "Estado de Propiedad"
        verbose_name_plural = "Estados de Propiedades"
    
    def __str__(self):
        return self.name


class Feature(BaseModel):
    """Property features model (Piscina, Garage, etc.)"""
    name = models.CharField(max_length=100, unique=True, verbose_name="Característica")
    description = models.TextField(blank=True, verbose_name="Descripción")
    
    class Meta:
        verbose_name = "Característica"
        verbose_name_plural = "Características"
    
    def __str__(self):
        return self.name


class Tag(BaseModel):
    """Property tags model"""
    name = models.CharField(max_length=50, unique=True, verbose_name="Etiqueta")
    color = models.CharField(max_length=7, default="#007bff", verbose_name="Color")
    
    class Meta:
        verbose_name = "Etiqueta"
        verbose_name_plural = "Etiquetas"
    
    def __str__(self):
        return self.name


class Property(BaseModel):
    """Main Property model"""
    # Basic Information
    title = models.CharField(max_length=200, verbose_name="Título")
    description = models.TextField(verbose_name="Descripción")
    property_type = models.ForeignKey(PropertyType, on_delete=models.CASCADE, verbose_name="Tipo")
    property_status = models.ForeignKey(PropertyStatus, on_delete=models.CASCADE, verbose_name="Estado")
    
    # Address fields (no separate address table)
    street = models.CharField(max_length=200, verbose_name="Calle")
    number = models.CharField(max_length=20, verbose_name="Número")
    neighborhood = models.CharField(max_length=100, verbose_name="Barrio")
    locality = models.CharField(max_length=100, verbose_name="Localidad")
    province = models.CharField(max_length=100, verbose_name="Provincia")
    country = models.CharField(max_length=100, default="Argentina", verbose_name="País")
    
    # Property Details
    total_surface = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Superficie Total (m²)")
    covered_surface = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, verbose_name="Superficie Cubierta (m²)")
    bedrooms = models.PositiveIntegerField(default=0, verbose_name="Dormitorios")
    bathrooms = models.PositiveIntegerField(default=0, verbose_name="Baños")
    garage = models.BooleanField(default=False, verbose_name="Garage")
    furnished = models.BooleanField(default=False, verbose_name="Amueblado")
    
    # Financial Information
    sale_price = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True, verbose_name="Precio de Venta")
    rental_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, verbose_name="Precio de Alquiler")
    expenses = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True, verbose_name="Expensas")
    
    # Additional Information
    year_built = models.PositiveIntegerField(blank=True, null=True, verbose_name="Año de Construcción")
    orientation = models.CharField(max_length=50, blank=True, verbose_name="Orientación")
    floors = models.PositiveIntegerField(blank=True, null=True, verbose_name="Plantas")
    
    # Relationships
    agent = models.ForeignKey('agents.Agent', on_delete=models.CASCADE, verbose_name="Agente")
    features = models.ManyToManyField(Feature, blank=True, verbose_name="Características")
    tags = models.ManyToManyField(Tag, blank=True, verbose_name="Etiquetas")
    
    class Meta:
        verbose_name = "Propiedad"
        verbose_name_plural = "Propiedades"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.street} {self.number}"
    
    @property
    def full_address(self):
        return f"{self.street} {self.number}, {self.neighborhood}, {self.locality}, {self.province}"
    
    @property
    def cover_image(self):
        return self.images.filter(is_cover=True).first()


class PropertyImage(BaseModel):
    """Property images model"""
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='images', verbose_name="Propiedad")
    image = models.ImageField(upload_to='properties/', verbose_name="Imagen")
    is_cover = models.BooleanField(default=False, verbose_name="Imagen de Portada")
    description = models.CharField(max_length=200, blank=True, verbose_name="Descripción")
    
    class Meta:
        verbose_name = "Imagen de Propiedad"
        verbose_name_plural = "Imágenes de Propiedades"
    
    def __str__(self):
        return f"Imagen de {self.property.title}"
    
    def save(self, *args, **kwargs):
        if self.is_cover:
            # Ensure only one cover image per property
            PropertyImage.objects.filter(property=self.property, is_cover=True).update(is_cover=False)
        super().save(*args, **kwargs)
