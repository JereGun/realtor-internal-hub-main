from django.core.management.base import BaseCommand
from django.utils import timezone
from contracts.models import Contract
from user_notifications.models import Notification
from django.db import transaction
from django.contrib.contenttypes.models import ContentType

class Command(BaseCommand):
    help = 'Crea notificaciones para aumentos de alquiler pendientes'

    def handle(self, *args, **options):
        today = timezone.now().date()
        
        # Obtener todos los contratos activos con fecha de aumento pendiente
        contracts = Contract.objects.filter(
            is_active=True,
            next_increase_date__isnull=False,
            next_increase_date__lte=today
        )
        
        for contract in contracts:
            try:
                with transaction.atomic():
                    # Crear notificación usando el sistema existente
                    contract_content_type = ContentType.objects.get_for_model(Contract)
                    
                    # Crear notificación para el agente
                    Notification.objects.create(
                        agent=contract.agent,
                        title=f"Recordatorio de Aumento - {contract.property.title}",
                        message=f"Se acerca la fecha de aumento para el contrato {contract.property.title} - {contract.customer.full_name}.\n"
                               f"Fecha de aumento: {today}\n"
                               f"Monto actual: {contract.amount} {contract.currency}",
                        notification_type='contract_increase',
                        content_type=contract_content_type,
                        object_id=contract.id
                    )
                    
                    # Actualizar la fecha de próximo aumento
                    contract.next_increase_date = self.calculate_next_increase_date(contract.frequency, today)
                    contract.save()
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Se creó notificación de aumento para el contrato {contract.id}'
                        )
                    )
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f'Error al crear notificación para el contrato {contract.id}: {str(e)}'
                    )
                )

    def calculate_next_increase_date(self, frequency, current_date):
        from datetime import timedelta
        
        if frequency == 'monthly':
            return current_date + timedelta(days=30)
        elif frequency == 'quarterly':
            return current_date + timedelta(days=90)
        elif frequency == 'semi-annually':
            return current_date + timedelta(days=180)
        elif frequency == 'annually':
            return current_date + timedelta(days=365)
        return None
