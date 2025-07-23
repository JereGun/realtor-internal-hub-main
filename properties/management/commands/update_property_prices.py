from django.core.management.base import BaseCommand
from properties.models import Property
from decimal import Decimal
import random

class Command(BaseCommand):
    help = 'Actualiza los precios de las propiedades según su tipo de listado'

    def handle(self, *args, **options):
        # Actualizar propiedades en venta
        sale_properties = Property.objects.filter(listing_type='sale')
        for prop in sale_properties:
            if not prop.sale_price:
                prop.sale_price = Decimal(str(random.randint(5000000, 20000000)))
                prop.rental_price = None
                prop.save()
                self.stdout.write(self.style.SUCCESS(f'Actualizada propiedad en venta ID: {prop.id}, Título: {prop.title}'))
        
        # Actualizar propiedades en alquiler
        rent_properties = Property.objects.filter(listing_type='rent')
        for prop in rent_properties:
            if not prop.rental_price:
                prop.rental_price = Decimal(str(random.randint(30000, 100000)))
                prop.sale_price = None
                prop.save()
                self.stdout.write(self.style.SUCCESS(f'Actualizada propiedad en alquiler ID: {prop.id}, Título: {prop.title}'))
        
        # Actualizar propiedades en venta y alquiler
        both_properties = Property.objects.filter(listing_type='both')
        for prop in both_properties:
            if not prop.sale_price:
                prop.sale_price = Decimal(str(random.randint(5000000, 20000000)))
            if not prop.rental_price:
                prop.rental_price = Decimal(str(random.randint(30000, 100000)))
            prop.save()
            self.stdout.write(self.style.SUCCESS(f'Actualizada propiedad en venta y alquiler ID: {prop.id}, Título: {prop.title}'))
        
        # Convertir algunas propiedades en venta a alquiler
        if rent_properties.count() < 5:
            sale_to_rent = sale_properties.order_by('?')[:3]
            for prop in sale_to_rent:
                prop.listing_type = 'rent'
                prop.rental_price = Decimal(str(random.randint(30000, 100000)))
                prop.sale_price = None
                prop.save()
                self.stdout.write(self.style.SUCCESS(f'Convertida propiedad de venta a alquiler ID: {prop.id}, Título: {prop.title}'))
        
        # Convertir algunas propiedades a venta y alquiler
        if both_properties.count() < 3:
            sale_to_both = sale_properties.exclude(id__in=sale_to_rent.values_list('id', flat=True)).order_by('?')[:2]
            for prop in sale_to_both:
                prop.listing_type = 'both'
                prop.rental_price = Decimal(str(random.randint(30000, 100000)))
                prop.save()
                self.stdout.write(self.style.SUCCESS(f'Convertida propiedad a venta y alquiler ID: {prop.id}, Título: {prop.title}'))
        
        self.stdout.write(self.style.SUCCESS('Actualización de precios completada'))
        
        # Mostrar resumen
        self.stdout.write(self.style.SUCCESS(f'Propiedades en venta: {Property.objects.filter(listing_type="sale").count()}'))
        self.stdout.write(self.style.SUCCESS(f'Propiedades en alquiler: {Property.objects.filter(listing_type="rent").count()}'))
        self.stdout.write(self.style.SUCCESS(f'Propiedades en venta y alquiler: {Property.objects.filter(listing_type="both").count()}'))