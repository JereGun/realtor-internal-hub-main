import random
from datetime import timedelta
from django.utils import timezone
from django.core.management.base import BaseCommand
from django.contrib.contenttypes.models import ContentType
from faker import Faker
from locations.models import Country, State, City
from customers.models import Customer
from agents.models import Agent
from properties.models import Property, PropertyType, PropertyStatus, Feature, Tag
from contracts.models import Contract
from accounting.models_invoice import Invoice, InvoiceLine, Payment
from user_notifications.models import Notification

class Command(BaseCommand):
    help = 'Generate test data for the project'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting data generation...'))
        self.fake = Faker('es_ES')
        self.generate_locations()
        self.generate_customers()
        self.generate_agents()
        self.generate_properties()
        self.generate_contracts_and_invoices()
        self.generate_notifications()
        self.stdout.write(self.style.SUCCESS('Data generation finished.'))

    def generate_locations(self):
        self.stdout.write(self.style.SUCCESS('Generating locations...'))
        country, created = Country.objects.get_or_create(name='Argentina')
        if created:
            provinces = ['Buenos Aires', 'Córdoba', 'Santa Fe']
            for province_name in provinces:
                state, created = State.objects.get_or_create(country=country, name=province_name)
                if created:
                    for _ in range(3):
                        City.objects.create(state=state, name=self.fake.city())

    def generate_customers(self):
        self.stdout.write(self.style.SUCCESS('Generating customers...'))
        for _ in range(10):
            Customer.objects.create(
                first_name=self.fake.first_name(),
                last_name=self.fake.last_name(),
                email=self.fake.email(),
                phone=self.fake.phone_number(),
                document=self.fake.unique.random_number(digits=8),
                street=self.fake.street_name(),
                number=self.fake.building_number(),
                country=Country.objects.first(),
                province=State.objects.order_by('?').first(),
                locality=City.objects.order_by('?').first(),
            )

    def generate_agents(self):
        self.stdout.write(self.style.SUCCESS('Generating agents...'))
        for i in range(3):
            Agent.objects.create_user(
                username=self.fake.user_name(),
                first_name=self.fake.first_name(),
                last_name=self.fake.last_name(),
                email=self.fake.email(),
                phone=self.fake.phone_number(),
                license_number=self.fake.unique.random_number(digits=5),
                password=f'password{i}'
            )

    def generate_properties(self):
        self.stdout.write(self.style.SUCCESS('Generating properties...'))
        property_types = ['Casa', 'Departamento', 'Local']
        for prop_type in property_types:
            PropertyType.objects.get_or_create(name=prop_type)

        property_statuses = ['Disponible', 'Vendida', 'Alquilada']
        for status in property_statuses:
            PropertyStatus.objects.get_or_create(name=status)
        
        features = ['Piscina', 'Garage', 'Jardín']
        for feature in features:
            Feature.objects.get_or_create(name=feature)

        tags = ['Nuevo', 'Renovado', 'Cerca de transporte público']
        for tag in tags:
            Tag.objects.get_or_create(name=tag)

        agents = Agent.objects.all()
        customers = Customer.objects.all()

        for _ in range(15):
            property = Property.objects.create(
                title=self.fake.sentence(nb_words=4),
                description=self.fake.text(),
                property_type=PropertyType.objects.order_by('?').first(),
                property_status=PropertyStatus.objects.order_by('?').first(),
                street=self.fake.street_name(),
                number=self.fake.building_number(),
                country=Country.objects.first(),
                province=State.objects.order_by('?').first(),
                locality=City.objects.order_by('?').first(),
                total_surface=random.randint(50, 300),
                covered_surface=random.randint(40, 250),
                bedrooms=random.randint(1, 5),
                bathrooms=random.randint(1, 3),
                garage=random.choice([True, False]),
                furnished=random.choice([True, False]),
                sale_price=random.randint(100000, 500000),
                rental_price=random.randint(500, 2000),
                agent=random.choice(agents),
                owner=random.choice(customers),
            )
            property.features.set(Feature.objects.order_by('?')[:random.randint(1, 3)])
            property.tags.set(Tag.objects.order_by('?')[:random.randint(1, 2)])

    def generate_contracts_and_invoices(self):
        self.stdout.write(self.style.SUCCESS('Generating contracts and invoices...'))
        properties = Property.objects.filter(property_status__name='Alquilada')
        customers = Customer.objects.all()
        agents = Agent.objects.all()

        for property in properties:
            contract = Contract.objects.create(
                property=property,
                customer=random.choice(customers),
                agent=random.choice(agents),
                start_date=timezone.now().date() - timedelta(days=random.randint(30, 365)),
                end_date=timezone.now().date() + timedelta(days=random.randint(30, 365)),
                amount=property.rental_price,
                frequency='monthly',
            )

            for i in range(1, 4):
                invoice = Invoice.objects.create(
                    contract=contract,
                    customer=contract.customer,
                    number=self.fake.unique.random_number(digits=8),
                    date=contract.start_date + timedelta(days=30 * i),
                    due_date=contract.start_date + timedelta(days=30 * i + 15),
                    description=f'Alquiler mes {i}',
                    total_amount=contract.amount,
                    status=random.choice(['draft', 'sent', 'paid'])
                )
                InvoiceLine.objects.create(
                    invoice=invoice,
                    concept=f'Alquiler mes {i}',
                    amount=contract.amount
                )

                if invoice.status == 'paid':
                    Payment.objects.create(
                        invoice=invoice,
                        date=invoice.date + timedelta(days=random.randint(1, 10)),
                        amount=invoice.total_amount,
                        method='transferencia'
                    )
    
    def generate_notifications(self):
        self.stdout.write(self.style.SUCCESS('Generating notifications...'))
        agents = Agent.objects.all()
        invoices = Invoice.objects.all()

        for agent in agents:
            for _ in range(5):
                invoice = random.choice(invoices)
                Notification.objects.create(
                    agent=agent,
                    title=f'Factura {invoice.number} actualizada',
                    message=f'El estado de la factura {invoice.number} ha cambiado a {invoice.get_status_display()}',
                    notification_type='invoice_status_change',
                    content_type=ContentType.objects.get_for_model(invoice),
                    object_id=invoice.id
                )
