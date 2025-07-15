from django.core.management.base import BaseCommand
from contracts.models import Contract, ContractIncrease
from django.utils import timezone

class Command(BaseCommand):
    help = 'Verifica los aumentos aplicados'

    def handle(self, *args, **options):
        # Obtener todos los contratos con aumentos
        contracts = Contract.objects.filter(is_active=True)
        
        for contract in contracts:
            # Verificar aumentos aplicados
            increases = ContractIncrease.objects.filter(contract=contract).order_by('-effective_date')
            if increases.exists():
                last_increase = increases.first()
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Contrato {contract.id}: '
                        f'Monto actual: {contract.amount}, '
                        f'Último aumento: {last_increase.effective_date}, '
                        f'Nuevo monto: {last_increase.new_amount}'
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f'Contrato {contract.id}: Sin aumentos aplicados'
                    )
                )
