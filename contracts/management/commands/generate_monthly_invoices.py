from django.core.management.base import BaseCommand
from contracts.models import Contract
from invoicing.models import Invoice, InvoiceItem
from django.utils import timezone
from datetime import date, timedelta

class Command(BaseCommand):
    help = 'Genera facturas de alquiler en estado borrador para todos los contratos activos de alquiler al inicio de cada mes.'

    def handle(self, *args, **kwargs):
        today = timezone.now().date()
        first_day = today.replace(day=1)
        contracts = Contract.objects.filter(contract_type='rental', is_active=True)
        created_count = 0
        for contract in contracts:
            # Evitar duplicados: no crear si ya existe una factura para este contrato y mes
            exists = Invoice.objects.filter(contract=contract, issue_date=first_day).exists()
            if not exists:
                invoice = Invoice.objects.create(
                    customer=contract.customer,
                    contract=contract,
                    issue_date=first_day,
                    due_date=first_day + timedelta(days=10),  # vencimiento a 10 días
                    status=Invoice.DRAFT,
                    notes='Factura generada automáticamente.'
                )
                InvoiceItem.objects.create(
                    invoice=invoice,
                    description='Alquiler mensual',
                    quantity=1,
                    unit_price=contract.amount,
                    total=contract.amount
                )
                created_count += 1
        self.stdout.write(self.style.SUCCESS(f'Se generaron {created_count} facturas de alquiler en borrador.'))
