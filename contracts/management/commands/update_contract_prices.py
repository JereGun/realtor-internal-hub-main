from django.core.management.base import BaseCommand
from django.utils import timezone
from contracts.models import Contract, ContractIncrease
from dateutil.relativedelta import relativedelta

class Command(BaseCommand):
    help = 'Updates contract prices based on their frequency and increase percentage.'

    def handle(self, *args, **options):
        today = timezone.now().date()
        contracts_to_update = Contract.objects.filter(is_active=True, next_increase_date__lte=today)

        for contract in contracts_to_update:
            previous_amount = contract.amount
            increase_percentage = contract.increase_percentage
            new_amount = previous_amount * (1 + increase_percentage / 100)

            # Create a record of the increase
            ContractIncrease.objects.create(
                contract=contract,
                previous_amount=previous_amount,
                new_amount=new_amount,
                increase_percentage=increase_percentage,
                effective_date=today,
                notes=f"Aumento automático del {increase_percentage}%"
            )

            # Update the contract
            contract.amount = new_amount
            
            # Calculate the next increase date
            if contract.frequency == 'monthly':
                contract.next_increase_date += relativedelta(months=1)
            elif contract.frequency == 'quarterly':
                contract.next_increase_date += relativedelta(months=3)
            elif contract.frequency == 'semi-annually':
                contract.next_increase_date += relativedelta(months=6)
            elif contract.frequency == 'annually':
                contract.next_increase_date += relativedelta(years=1)
            
            contract.save()

            self.stdout.write(self.style.SUCCESS(f'Successfully updated contract {contract.id}'))
