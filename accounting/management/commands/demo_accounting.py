from django.core.management.base import BaseCommand
from accounting.models import Company, Currency, Account, AccountTag, Journal
from accounting.models_invoice import (
    FiscalPosition, Tax, AnalyticAccount, Product, PaymentTerm, Payment,
    Invoice, InvoiceLine
)
from customers.models import Customer
from properties.models import Property, PropertyType, PropertyStatus
from contracts.models import Contract
from django.utils import timezone

class Command(BaseCommand):
    help = 'Crea datos de prueba para contabilidad y facturación'

    def handle(self, *args, **options):
        # Moneda y empresa
        currency, _ = Currency.objects.get_or_create(name='Peso Argentino', code='ARS', symbol='$', active=True)
        company, _ = Company.objects.get_or_create(name='Inmobiliaria Demo', currency=currency, active=True)
        # Cuentas contables
        act_tag, _ = AccountTag.objects.get_or_create(name='Ingresos', code='ING')
        acc_income, _ = Account.objects.get_or_create(name='Ingresos por Alquileres', code='400000', account_type='income', company=company)
        acc_income.tags.add(act_tag)
        acc_expense, _ = Account.objects.get_or_create(name='Gastos de Mantenimiento', code='500000', account_type='expense', company=company)
        # Diario
        journal, _ = Journal.objects.get_or_create(name='Ventas', code='VENTA', type='sale', company=company)
        # Fiscal Position
        fp, _ = FiscalPosition.objects.get_or_create(name='Responsable Inscripto', company=company, active=True)
        # Impuesto
        iva, _ = Tax.objects.get_or_create(name='IVA 21%', rate=21, company=company, active=True, fiscal_position=fp)
        # Producto
        prod, _ = Product.objects.get_or_create(name='Alquiler Mensual', company=company, active=True)
        # Término de pago
        pt, _ = PaymentTerm.objects.get_or_create(name='Neto 30', days=30, company=company)
        # Cliente y propiedad
        customer, _ = Customer.objects.get_or_create(first_name='Juan', last_name='Pérez', email='juan@example.com')
        # Crear objetos relacionados para Property
        ptype, _ = PropertyType.objects.get_or_create(name='Departamento', defaults={'description': 'Depto.'})
        pstatus, _ = PropertyStatus.objects.get_or_create(name='Disponible', defaults={'description': 'Disponible'})
        from agents.models import Agent
        agent, _ = Agent.objects.get_or_create(email='agente@example.com', defaults={
            'first_name': 'Agente', 'last_name': 'Demo', 'username': 'agente.demo', 'license_number': 'LIC123', 'commission_rate': 3.0
        })
        prop, _ = Property.objects.get_or_create(
            title='Depto. Demo',
            description='Departamento de prueba para demo contable',
            property_type=ptype,
            property_status=pstatus,
            street='Calle Falsa',
            number='123',
            neighborhood='Centro',
            locality='Springfield',
            province='Buenos Aires',
            country='Argentina',
            total_surface=80,
            covered_surface=70,
            bedrooms=2,
            bathrooms=1,
            garage=True,
            furnished=False,
            sale_price=100000,
            rental_price=50000,
            expenses=5000,
            year_built=2010,
            orientation='Norte',
            floors=1,
            agent=agent
        )
        # Contrato
        contract, _ = Contract.objects.get_or_create(
            property=prop,
            customer=customer,
            agent=agent,
            contract_type='rental',
            start_date=timezone.now().date(),
            end_date=None,
            amount=50000,
            currency='ARS',
            terms='Contrato de alquiler de prueba',
            notes='Demo',
            is_active=True
        )
        # Factura (solo campos válidos en el constructor)
        invoice = Invoice.objects.create(
            name='FAC-0001',
            date=timezone.now().date(),
            journal=journal,
            partner=customer,
            move_type='out_invoice',
            state='draft',
            amount_total=12100,
            amount_untaxed=10000,
            payment_state='not_paid',
            invoice_date=timezone.now().date(),
            invoice_date_due=timezone.now().date(),
            ref='Contrato de alquiler',
            company=company,
            currency=currency,
            property=prop,
            contract=contract
        )
        # Asignar campos extra si existen
        if hasattr(invoice, 'payment_term'):
            invoice.payment_term = pt
        if hasattr(invoice, 'fiscal_position'):
            invoice.fiscal_position = fp
        if hasattr(invoice, 'notes'):
            invoice.notes = 'Factura de prueba'
        invoice.save()
        line = InvoiceLine.objects.create(
            move=invoice,
            account=acc_income,
            name='Alquiler Mensual',
            debit=0,
            credit=10000,
            product=prod,
            quantity=1,
            price_unit=10000,
            price_subtotal=10000,
        )
        line.taxes.add(iva)
        invoice.compute_taxes()
        Payment.objects.create(invoice=invoice, payment_date=timezone.now().date(), amount=12100, method='Transferencia', notes='Pago completo')
        self.stdout.write(self.style.SUCCESS('Datos de prueba creados exitosamente.'))
