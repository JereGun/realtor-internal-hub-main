import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from contracts.models import Contract
from user_notifications.services import create_notification

class Command(BaseCommand):
    help = 'Updates contract prices based on their increase frequency and creates notifications.'

    def handle(self, *args, **options):
        today = timezone.now().date()
        contracts_to_update = Contract.objects.filter(
            is_active=True, 
            next_increase_date__lte=today
        )

        for contract in contracts_to_update:
            # Logic to update the contract price
            new_price = contract.price * (1 + contract.increase_percentage / 100)
            contract.price = new_price

            # Update the next increase date
            if contract.frequency == 'monthly':
                contract.next_increase_date += datetime.timedelta(days=30)
            elif contract.frequency == 'quarterly':
                contract.next_increase_date += datetime.timedelta(days=90)
            elif contract.frequency == 'semi-annually':
                contract.next_increase_date += datetime.timedelta(days=180)
            elif contract.frequency == 'annually':
                contract.next_increase_date += datetime.timedelta(days=365)

            contract.save()

            # Create a notification for the price increase
            create_notification(
                agent=contract.agent,
                title=f"Aumento de precio para el contrato #{contract.id}",
                message=f"El contrato para la propiedad {contract.property.title} ha tenido un aumento de precio. El nuevo monto es de ${new_price}.",
                notification_type='contract_increase',
                related_object=contract
            )

            self.stdout.write(self.style.SUCCESS(f'Successfully updated price and created notification for contract {contract.id}'))
