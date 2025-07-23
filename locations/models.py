from django.db import models

class Country(models.Model):
    """
    Modelo que representa países.
    
    Almacena información básica de los países utilizados en el sistema
    para la gestión de direcciones de propiedades y clientes.
    """
    name = models.CharField(max_length=100, unique=True, verbose_name="Nombre del País")

    class Meta:
        verbose_name = "País"
        verbose_name_plural = "Países"
        ordering = ['name']

    def __str__(self):
        return self.name

class State(models.Model):
    """
    Modelo que representa provincias o estados dentro de un país.
    
    Establece una relación jerárquica con el modelo Country y sirve como
    nivel intermedio en la estructura de ubicaciones geográficas del sistema.
    """
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name='states', verbose_name="País")
    name = models.CharField(max_length=100, verbose_name="Nombre de Provincia/Estado")

    class Meta:
        verbose_name = "Provincia/Estado"
        verbose_name_plural = "Provincias/Estados"
        unique_together = ('country', 'name')
        ordering = ['country__name', 'name']

    def __str__(self):
        return f"{self.name}, {self.country.name}"

class City(models.Model):
    """
    Modelo que representa ciudades o localidades dentro de una provincia o estado.
    
    Representa el nivel más específico en la jerarquía de ubicaciones geográficas,
    permitiendo una localización precisa de propiedades y direcciones de clientes.
    """
    state = models.ForeignKey(State, on_delete=models.CASCADE, related_name='cities', verbose_name="Provincia/Estado")
    name = models.CharField(max_length=100, verbose_name="Nombre de Ciudad/Localidad")

    class Meta:
        verbose_name = "Ciudad/Localidad"
        verbose_name_plural = "Ciudades/Localidades"
        unique_together = ('state', 'name')
        ordering = ['state__country__name', 'state__name', 'name']

    def __str__(self):
        return f"{self.name}, {self.state.name}, {self.state.country.name}"
