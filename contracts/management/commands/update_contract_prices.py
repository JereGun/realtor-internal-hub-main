import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from contracts.models import Contract
from notifications.models import TaskNotification

class Command(BaseCommand):
    help = 'Creates notifications for upcoming contract price increases.'

    def handle(self, *args, **options):
        today = timezone.now().date()
        notification_date = today + datetime.timedelta(days=7)
        contracts_to_notify = Contract.objects.filter(
            is_active=True, 
            next_increase_date=notification_date
        )

        for contract in contracts_to_notify:
            TaskNotification.objects.create(
                title=f"Aumento de precio para el contrato #{contract.id}",
                description=f"El contrato para la propiedad {contract.property.title} tiene un aumento de precio programado para el {contract.next_increase_date}. Por favor, actualice el monto.",
                agent=contract.agent,
                priority='medium',
                due_date=contract.next_increase_date,
                contract=contract
            )

            self.stdout.write(self.style.SUCCESS(f'Successfully created notification for contract {contract.id}'))
