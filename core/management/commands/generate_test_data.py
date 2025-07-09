from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from properties.models import Property
from customers.models import Customer
from contracts.models import Contract
from payments.models import ContractPayment, PaymentMethod
from django.utils import timezone
import random
from faker import Faker
from datetime import timedelta

class Command(BaseCommand):
    help = 'Genera datos de prueba para el sistema inmobiliario'

    def handle(self, *args, **kwargs):
        fake = Faker('es_ES')
        User = get_user_model()

        # Crear métodos de pago
        methods = []
        for name in ['Efectivo', 'Transferencia', 'Tarjeta']:
            method, _ = PaymentMethod.objects.get_or_create(name=name, is_active=True)
            methods.append(method)

        # Crear clientes
        customers = []
        for _ in range(20):
            customer, _ = Customer.objects.get_or_create(
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                email=fake.unique.email(),
                document=fake.unique.random_number(digits=8),
                phone=fake.phone_number(),
                locality=fake.city()
            )
            customers.append(customer)

        # Crear propiedades
        properties = []
        for _ in range(15):
            prop, _ = Property.objects.get_or_create(
                title=fake.street_name(),
                description=fake.text(max_nb_chars=200),
                property_type_id=1,  # Ajustar si es necesario
                property_status_id=1,  # Ajustar si es necesario
                street=fake.street_name(),
                number=str(fake.building_number()),
                neighborhood=fake.city_suffix(),
                locality=fake.city(),
                province=fake.state(),
                country="Argentina",
                total_surface=random.randint(50, 300),
                covered_surface=random.randint(30, 200),
                bedrooms=random.randint(1, 5),
                bathrooms=random.randint(1, 3),
                garage=random.choice([True, False]),
                furnished=random.choice([True, False]),
                sale_price=random.randint(60000, 300000),
                rental_price=random.randint(10000, 50000),
                expenses=random.randint(1000, 10000),
                year_built=random.randint(1980, 2023),
                orientation=random.choice(['Norte', 'Sur', 'Este', 'Oeste']),
                floors=random.randint(1, 3),
                agent_id=1  # Ajustar si es necesario
            )
            properties.append(prop)

        # Crear contratos (ventas y alquileres)
        for _ in range(10):
            start_date = fake.date_between(start_date='-2y', end_date='today')
            end_date = start_date + timedelta(days=365)
            Contract.objects.get_or_create(
                property=random.choice(properties),
                customer=random.choice(customers),
                agent_id=1,  # Ajustar si es necesario
                contract_type='sale',
                start_date=start_date,
                end_date=end_date,
                amount=random.randint(60000, 250000),
                is_active=True,
                created_at=fake.date_time_this_year()
            )
        for _ in range(10):
            start_date = fake.date_between(start_date='-2y', end_date='today')
            end_date = start_date + timedelta(days=365)
            c = Contract.objects.create(
                property=random.choice(properties),
                customer=random.choice(customers),
                agent_id=1,  # Ajustar si es necesario
                contract_type='rental',
                start_date=start_date,
                end_date=end_date,
                amount=random.randint(10000, 50000),
                is_active=True,
                created_at=fake.date_time_this_year()
            )
            # Crear pagos de alquiler
            for i in range(1, 7):
                due = timezone.now().date().replace(day=1) + timezone.timedelta(days=30*i)
                ContractPayment.objects.create(
                    contract=c,
                    payment_method=random.choice(methods),
                    amount=c.amount // 12,
                    status=random.choice(['paid', 'pending']),
                    due_date=due,
                    receipt_number=fake.unique.random_number(digits=6),
                    notes=fake.sentence()
                )
        self.stdout.write(self.style.SUCCESS('¡Datos de prueba generados!'))
