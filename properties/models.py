from django.db import models
from core.models import BaseModel


class PropertyType(BaseModel):
    """
    Modelo que representa los diferentes tipos de propiedades inmobiliarias.

    Almacena categorías como Casa, Departamento, Local, Oficina, etc.,
    que se utilizan para clasificar las propiedades en el sistema.
    """

    name = models.CharField(max_length=100, unique=True, verbose_name="Tipo")
    description = models.TextField(blank=True, verbose_name="Descripción")

    class Meta:
        verbose_name = "Tipo de Propiedad"
        verbose_name_plural = "Tipos de Propiedades"

    def __str__(self):
        return self.name


class PropertyStatus(BaseModel):
    """
    Modelo que representa los diferentes estados de una propiedad inmobiliaria.

    Almacena estados como Disponible, Vendida, Alquilada, En Construcción, etc.,
    que indican la situación actual de comercialización de la propiedad.
    """

    name = models.CharField(max_length=100, unique=True, verbose_name="Estado")
    description = models.TextField(blank=True, verbose_name="Descripción")

    class Meta:
        verbose_name = "Estado de Propiedad"
        verbose_name_plural = "Estados de Propiedades"

    def __str__(self):
        return self.name


class Feature(BaseModel):
    """
    Modelo que representa las características o amenidades de una propiedad.

    Almacena características como Piscina, Garage, Jardín, Seguridad 24hs, etc.,
    que pueden asociarse a las propiedades para describir sus comodidades.
    """

    name = models.CharField(max_length=100, unique=True, verbose_name="Característica")
    description = models.TextField(blank=True, verbose_name="Descripción")

    class Meta:
        verbose_name = "Característica"
        verbose_name_plural = "Características"

    def __str__(self):
        return self.name


class Tag(BaseModel):
    """
    Modelo que representa etiquetas para categorizar propiedades.

    Las etiquetas permiten clasificar y filtrar propiedades según características
    especiales como 'Oportunidad', 'Destacada', 'Recién Reducida', etc.
    Cada etiqueta tiene un color asociado para su visualización en la interfaz.
    """

    name = models.CharField(max_length=50, unique=True, verbose_name="Etiqueta")
    color = models.CharField(max_length=7, default="#007bff", verbose_name="Color")

    class Meta:
        verbose_name = "Etiqueta"
        verbose_name_plural = "Etiquetas"

    def __str__(self):
        return self.name


class Property(BaseModel):
    """
    Modelo principal de Propiedad inmobiliaria.

    Almacena toda la información relacionada con una propiedad, incluyendo datos básicos,
    ubicación, características físicas, información financiera y relaciones con otros
    modelos como agentes, propietarios, características y etiquetas.
    """

    # Listing type choices
    LISTING_TYPE_CHOICES = [
        ("rent", "Alquiler"),
        ("sale", "Venta"),
        ("both", "Alquiler y Venta"),
    ]

    # Basic Information
    title = models.CharField(max_length=200, verbose_name="Título")
    description = models.TextField(verbose_name="Descripción")
    property_type = models.ForeignKey(
        PropertyType, on_delete=models.CASCADE, verbose_name="Tipo"
    )
    property_status = models.ForeignKey(
        PropertyStatus, on_delete=models.CASCADE, verbose_name="Estado"
    )
    listing_type = models.CharField(
        max_length=10,
        choices=LISTING_TYPE_CHOICES,
        default="sale",
        verbose_name="Tipo de Listado",
    )

    # Address fields (no separate address table)
    street = models.CharField(max_length=200, verbose_name="Calle")
    number = models.CharField(max_length=20, verbose_name="Número")
    neighborhood = models.CharField(max_length=100, verbose_name="Barrio")
    country = models.ForeignKey(
        "locations.Country",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="País",
    )
    province = models.ForeignKey(
        "locations.State",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Provincia",
    )
    locality = models.ForeignKey(
        "locations.City",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Localidad",
    )

    # Property Details
    total_surface = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="Superficie Total (m²)"
    )
    covered_surface = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name="Superficie Cubierta (m²)",
    )
    bedrooms = models.PositiveIntegerField(default=0, verbose_name="Dormitorios")
    bathrooms = models.PositiveIntegerField(default=0, verbose_name="Baños")
    garage = models.BooleanField(default=False, verbose_name="Garage")
    furnished = models.BooleanField(default=False, verbose_name="Amueblado")

    # Financial Information
    sale_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name="Precio de Venta",
    )
    rental_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name="Precio de Alquiler",
    )
    expenses = models.DecimalField(
        max_digits=8, decimal_places=2, blank=True, null=True, verbose_name="Expensas"
    )

    # Additional Information
    year_built = models.PositiveIntegerField(
        blank=True, null=True, verbose_name="Año de Construcción"
    )
    orientation = models.CharField(
        max_length=50, blank=True, verbose_name="Orientación"
    )
    floors = models.PositiveIntegerField(blank=True, null=True, verbose_name="Plantas")

    # Relationships
    agent = models.ForeignKey(
        "agents.Agent", on_delete=models.CASCADE, verbose_name="Agente"
    )
    owner = models.ForeignKey(
        "customers.Customer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Dueño",
    )
    features = models.ManyToManyField(
        Feature, blank=True, verbose_name="Características"
    )
    tags = models.ManyToManyField(Tag, blank=True, verbose_name="Etiquetas")

    class Meta:
        verbose_name = "Propiedad"
        verbose_name_plural = "Propiedades"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} - {self.street} {self.number}"

    @property
    def full_address(self):
        """
        Devuelve la dirección completa de la propiedad formateada.

        Returns:
            str: Dirección completa incluyendo calle, número, barrio, localidad y provincia.
        """
        return f"{self.street} {self.number}, {self.neighborhood}, {self.locality}, {self.province}"

    @property
    def cover_image(self):
        """
        Devuelve la imagen principal o de portada de la propiedad.

        Returns:
            PropertyImage: La primera imagen marcada como portada (is_cover=True),
            o None si no existe ninguna imagen de portada.
        """
        return self.images.filter(is_cover=True).first()

    @property
    def display_price(self):
        """
        Devuelve el precio apropiado para mostrar según el tipo de listado.

        Para propiedades en alquiler, devuelve el precio de alquiler.
        Para propiedades en venta, devuelve el precio de venta.
        Para propiedades en ambas categorías, devuelve un diccionario con ambos precios.

        Returns:
            dict: Diccionario con el tipo de listado, precio(s) y etiqueta(s) correspondiente(s).
        """
        if self.listing_type == "rent":
            return {"type": "rent", "price": self.rental_price, "label": "Alquiler"}
        elif self.listing_type == "sale":
            return {"type": "sale", "price": self.sale_price, "label": "Venta"}
        else:  # both
            return {
                "type": "both",
                "rent_price": self.rental_price,
                "sale_price": self.sale_price,
                "rent_label": "Alquiler",
                "sale_label": "Venta",
            }


class PropertyImage(BaseModel):
    """
    Modelo que representa las imágenes asociadas a una propiedad.

    Permite almacenar múltiples imágenes para cada propiedad, con la posibilidad
    de marcar una de ellas como imagen principal o de portada. Incluye un mecanismo
    para garantizar que solo una imagen sea marcada como portada por propiedad.
    """

    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name="images",
        verbose_name="Propiedad",
    )
    image = models.ImageField(upload_to="properties/", verbose_name="Imagen")
    is_cover = models.BooleanField(default=False, verbose_name="Imagen de Portada")
    description = models.CharField(
        max_length=200, blank=True, verbose_name="Descripción"
    )

    class Meta:
        verbose_name = "Imagen de Propiedad"
        verbose_name_plural = "Imágenes de Propiedades"

    def __str__(self):
        return f"Imagen de {self.property.title}"

    def save(self, *args, **kwargs):
        if self.is_cover:
            # Ensure only one cover image per property
            PropertyImage.objects.filter(property=self.property, is_cover=True).update(
                is_cover=False
            )
        super().save(*args, **kwargs)
