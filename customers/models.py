
from django.db import models
from core.models import BaseModel

class Customer(BaseModel):
    """
    Modelo de Cliente que almacena información de los clientes del sistema inmobiliario.
    
    Contiene datos personales, información de contacto, dirección y datos adicionales
    relevantes para la gestión de clientes, ya sean propietarios o inquilinos.
    """
    # Informacion Personal
    first_name = models.CharField(max_length=150, verbose_name="Nombre")
    last_name = models.CharField(max_length=150, verbose_name="Apellido")
    email = models.EmailField(unique=True, verbose_name="Email")
    phone = models.CharField(max_length=20, verbose_name="Teléfono")
    document = models.CharField(max_length=20, unique=True, verbose_name="Documento")
    
    # Informacion de Direccion
    street = models.CharField(max_length=200, blank=True, verbose_name="Calle")
    number = models.CharField(max_length=20, blank=True, verbose_name="Número")
    neighborhood = models.CharField(max_length=100, blank=True, verbose_name="Barrio")
    country = models.ForeignKey('locations.Country', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="País")
    province = models.ForeignKey('locations.State', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Provincia")
    locality = models.ForeignKey('locations.City', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Localidad")
    
    # Informacion Adicional
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
        """
        Propiedad que devuelve el nombre completo del cliente.
        
        Returns:
            str: Nombre y apellido concatenados del cliente.
        """
        return f"{self.first_name} {self.last_name}"
    
    @property
    def full_address(self):
        """
        Propiedad que devuelve la dirección completa del cliente.
        
        Returns:
            str: Dirección completa formateada si hay calle y número, o cadena vacía si no hay datos.
        """
        if self.street and self.number:
            return f"{self.street} {self.number}, {self.neighborhood}"
        return ""

    def get_full_name(self):
        """
        Método que devuelve el nombre completo del cliente.
        
        Este método proporciona compatibilidad con interfaces que esperan
        un método get_full_name() en lugar de una propiedad.
        
        Returns:
            str: Nombre completo del cliente (nombre y apellido concatenados).
        """
        return f"{self.first_name} {self.last_name}"
