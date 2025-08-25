"""
Management command to create sample notifications for testing.

This command creates test notifications of various types to help with
development, testing, and demonstration of the notification system.
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db import transaction
from datetime import timedelta, date
from decimal import Decimal
from user_notifications.services import create_notification
from agents.models import Agent
from contracts.models import Contract
from accounting.models_invoice import Invoice
from customers.models import Customer
from properties.models import Property
import random


class Command(BaseCommand):
    help = 'Create sample notifications for testing and development'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=10,
            help='Number of test notifications to create (default: 10)'
        )
        parser.add_argument(
            '--type',
            type=str,
            choices=['contract', 'invoice_overdue', 'rent_increase', 'invoice_due', 'all'],
            default='all',
            help='Type of test notifications to create'
        )
        parser.add_argument(
            '--agent-id',
            type=int,
            help='Specific agent ID to create notifications for'
        )
        parser.add_argument(
            '--clean',
            action='store_true',
            help='Delete existing test notifications before creating new ones'
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Starting test notification creation...')
        )
        
        # Get agent(s) to create notifications for
        agents = self._get_agents(options.get('agent_id'))
        if not agents:
            raise CommandError('No agents found. Please create at least one agent first.')
        
        # Clean existing test notifications if requested
        if options['clean']:
            self._clean_test_notifications()
        
        count = options['count']
        notification_type = options['type']
        
        created_notifications = {
            'contract_expiration': 0,
            'invoice_overdue': 0,
            'rent_increase': 0,
            'invoice_due_soon': 0,
            'total': 0
        }
        
        try:
            with transaction.atomic():
                if notification_type == 'all':
                    # Distribute notifications across all types
                    types_to_create = ['contract', 'invoice_overdue', 'rent_increase', 'invoice_due']
                    notifications_per_type = count // len(types_to_create)
                    remainder = count % len(types_to_create)
                    
                    for i, ntype in enumerate(types_to_create):
                        type_count = notifications_per_type + (1 if i < remainder else 0)
                        created = self._create_notifications_by_type(ntype, type_count, agents)
                        created_notifications[f'{ntype}_expiration' if ntype == 'contract' else ntype] = created
                        created_notifications['total'] += created
                else:
                    created = self._create_notifications_by_type(notification_type, count, agents)
                    key = f'{notification_type}_expiration' if notification_type == 'contract' else notification_type
                    created_notifications[key] = created
                    created_notifications['total'] = created
                
                # Summary
                self.stdout.write('\n' + '='*40)
                self.stdout.write(self.style.SUCCESS('TEST NOTIFICATIONS CREATED'))
                self.stdout.write('='*40)
                
                for key, value in created_notifications.items():
                    if key != 'total' and value > 0:
                        self.stdout.write(f'{key.replace("_", " ").title()}: {value}')
                
                self.stdout.write(f'\nTotal Notifications Created: {created_notifications["total"]}')
                self.stdout.write(
                    self.style.SUCCESS(f'Test notification creation completed successfully!')
                )
                
        except Exception as e:
            raise CommandError(f'Failed to create test notifications: {e}')

    def _get_agents(self, agent_id=None):
        """Get agents to create notifications for."""
        if agent_id:
            try:
                return [Agent.objects.get(id=agent_id)]
            except Agent.DoesNotExist:
                raise CommandError(f'Agent with ID {agent_id} not found')
        else:
            agents = list(Agent.objects.filter(is_active=True)[:5])  # Limit to 5 agents
            if not agents:
                agents = list(Agent.objects.all()[:5])
            return agents

    def _clean_test_notifications(self):
        """Delete existing test notifications."""
        from user_notifications.models import Notification
        
        # Delete notifications with test-related titles
        test_patterns = [
            'TEST -',
            'PRUEBA -',
            'Contrato de Prueba',
            'Factura de Prueba',
            'Test Contract',
            'Test Invoice'
        ]
        
        deleted_count = 0
        for pattern in test_patterns:
            deleted, _ = Notification.objects.filter(title__icontains=pattern).delete()
            deleted_count += deleted
        
        if deleted_count > 0:
            self.stdout.write(f'Cleaned {deleted_count} existing test notifications')

    def _create_notifications_by_type(self, notification_type, count, agents):
        """Create notifications of a specific type."""
        created = 0
        
        for i in range(count):
            agent = random.choice(agents)
            
            try:
                if notification_type == 'contract':
                    self._create_contract_notification(agent, i)
                elif notification_type == 'invoice_overdue':
                    self._create_invoice_overdue_notification(agent, i)
                elif notification_type == 'rent_increase':
                    self._create_rent_increase_notification(agent, i)
                elif notification_type == 'invoice_due':
                    self._create_invoice_due_notification(agent, i)
                
                created += 1
                
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f'Failed to create {notification_type} notification {i+1}: {e}')
                )
        
        return created

    def _create_contract_notification(self, agent, index):
        """Create a test contract expiration notification."""
        # Create different urgency levels
        urgency_types = [
            ('expired', -5, 'Contrato Vencido'),
            ('urgent', 3, 'Contrato Vence Pronto'),
            ('advance', 15, 'Contrato Próximo a Vencer')
        ]
        
        urgency, days_offset, title_prefix = random.choice(urgency_types)
        
        # Try to get a real contract or create mock data
        try:
            contract = Contract.objects.filter(agent=agent).first()
            if contract:
                property_name = contract.property.title
                customer_name = contract.customer.full_name
                related_object = contract
            else:
                property_name = f"Propiedad de Prueba {index + 1}"
                customer_name = f"Cliente de Prueba {index + 1}"
                related_object = None
        except:
            property_name = f"Propiedad de Prueba {index + 1}"
            customer_name = f"Cliente de Prueba {index + 1}"
            related_object = None
        
        if days_offset < 0:
            title = f"TEST - {title_prefix} - {property_name}"
            message = (
                f"El contrato para la propiedad '{property_name}' "
                f"del cliente {customer_name} venció hace "
                f"{abs(days_offset)} días. Se requiere acción inmediata."
            )
            notification_type = 'contract_expired'
        elif days_offset <= 7:
            title = f"TEST - {title_prefix} - {property_name}"
            message = (
                f"El contrato para la propiedad '{property_name}' "
                f"del cliente {customer_name} vence en "
                f"{days_offset} días. Se requiere renovación o finalización."
            )
            notification_type = 'contract_expiring_urgent'
        else:
            title = f"TEST - {title_prefix} - {property_name}"
            message = (
                f"El contrato para la propiedad '{property_name}' "
                f"del cliente {customer_name} vence en "
                f"{days_offset} días. Considere iniciar el proceso de renovación."
            )
            notification_type = 'contract_expiring_soon'
        
        create_notification(
            agent=agent,
            title=title,
            message=message,
            notification_type=notification_type,
            related_object=related_object
        )

    def _create_invoice_overdue_notification(self, agent, index):
        """Create a test invoice overdue notification."""
        # Create different overdue levels
        overdue_types = [
            ('critical', 35, 'Factura Crítica Vencida'),
            ('urgent', 15, 'Factura Urgente Vencida'),
            ('standard', 3, 'Factura Vencida')
        ]
        
        overdue_level, days_overdue, title_prefix = random.choice(overdue_types)
        
        # Try to get a real invoice or create mock data
        try:
            invoice = Invoice.objects.filter(contract__agent=agent).first()
            if invoice:
                invoice_number = invoice.number
                customer_name = invoice.customer.full_name
                balance = invoice.get_balance()
                related_object = invoice
            else:
                invoice_number = f"TEST-{index + 1:04d}"
                customer_name = f"Cliente de Prueba {index + 1}"
                balance = Decimal(str(random.randint(50000, 500000)))
                related_object = None
        except:
            invoice_number = f"TEST-{index + 1:04d}"
            customer_name = f"Cliente de Prueba {index + 1}"
            balance = Decimal(str(random.randint(50000, 500000)))
            related_object = None
        
        if overdue_level == 'critical':
            title = f"TEST - {title_prefix} - {invoice_number}"
            message = (
                f"La factura N° {invoice_number} del cliente {customer_name} "
                f"está vencida hace {days_overdue} días. "
                f"Saldo pendiente: ${balance:,.2f}. "
                f"Se requiere acción urgente para la cobranza."
            )
            notification_type = 'invoice_overdue_critical'
        elif overdue_level == 'urgent':
            title = f"TEST - {title_prefix} - {invoice_number}"
            message = (
                f"La factura N° {invoice_number} del cliente {customer_name} "
                f"está vencida hace {days_overdue} días. "
                f"Saldo pendiente: ${balance:,.2f}. "
                f"Se recomienda contactar al cliente."
            )
            notification_type = 'invoice_overdue_urgent'
        else:
            title = f"TEST - {title_prefix} - {invoice_number}"
            message = (
                f"La factura N° {invoice_number} del cliente {customer_name} "
                f"está vencida hace {days_overdue} días. "
                f"Saldo pendiente: ${balance:,.2f}."
            )
            notification_type = 'invoice_overdue'
        
        create_notification(
            agent=agent,
            title=title,
            message=message,
            notification_type=notification_type,
            related_object=related_object
        )

    def _create_rent_increase_notification(self, agent, index):
        """Create a test rent increase notification."""
        # Create different timing scenarios
        timing_types = [
            ('overdue', -10, 'Aumento de Alquiler Vencido'),
            ('due_soon', 5, 'Aumento de Alquiler Próximo')
        ]
        
        timing, days_offset, title_prefix = random.choice(timing_types)
        
        # Try to get a real contract or create mock data
        try:
            contract = Contract.objects.filter(agent=agent).first()
            if contract:
                property_name = contract.property.title
                customer_name = contract.customer.full_name
                current_amount = contract.amount
                related_object = contract
            else:
                property_name = f"Propiedad de Prueba {index + 1}"
                customer_name = f"Cliente de Prueba {index + 1}"
                current_amount = Decimal(str(random.randint(100000, 800000)))
                related_object = None
        except:
            property_name = f"Propiedad de Prueba {index + 1}"
            customer_name = f"Cliente de Prueba {index + 1}"
            current_amount = Decimal(str(random.randint(100000, 800000)))
            related_object = None
        
        frequency_display = random.choice(['Mensual', 'Trimestral', 'Semestral', 'Anual'])
        
        if timing == 'overdue':
            title = f"TEST - {title_prefix} - {property_name}"
            message = (
                f"El aumento de alquiler para la propiedad '{property_name}' "
                f"del cliente {customer_name} estaba programado hace "
                f"{abs(days_offset)} días. "
                f"Monto actual: ${current_amount:,.2f}. "
                f"Frecuencia: {frequency_display}. "
                f"Se requiere procesar el aumento urgentemente."
            )
            notification_type = 'rent_increase_overdue'
        else:
            title = f"TEST - {title_prefix} - {property_name}"
            message = (
                f"El aumento de alquiler para la propiedad '{property_name}' "
                f"del cliente {customer_name} está programado en "
                f"{days_offset} días. "
                f"Monto actual: ${current_amount:,.2f}. "
                f"Frecuencia: {frequency_display}. "
                f"Prepare el nuevo monto para el aumento."
            )
            notification_type = 'rent_increase_due'
        
        create_notification(
            agent=agent,
            title=title,
            message=message,
            notification_type=notification_type,
            related_object=related_object
        )

    def _create_invoice_due_notification(self, agent, index):
        """Create a test invoice due soon notification."""
        # Create different urgency levels
        urgency_types = [
            ('urgent', 2, 'Factura Vence Urgente'),
            ('soon', 5, 'Factura Vence Pronto')
        ]
        
        urgency, days_until_due, title_prefix = random.choice(urgency_types)
        
        # Try to get a real invoice or create mock data
        try:
            invoice = Invoice.objects.filter(contract__agent=agent).first()
            if invoice:
                invoice_number = invoice.number
                customer_name = invoice.customer.full_name
                amount = invoice.total_amount
                related_object = invoice
            else:
                invoice_number = f"TEST-{index + 1:04d}"
                customer_name = f"Cliente de Prueba {index + 1}"
                amount = Decimal(str(random.randint(50000, 500000)))
                related_object = None
        except:
            invoice_number = f"TEST-{index + 1:04d}"
            customer_name = f"Cliente de Prueba {index + 1}"
            amount = Decimal(str(random.randint(50000, 500000)))
            related_object = None
        
        if urgency == 'urgent':
            title = f"TEST - {title_prefix} - {invoice_number}"
            message = (
                f"La factura N° {invoice_number} del cliente {customer_name} "
                f"vence en {days_until_due} días. "
                f"Monto: ${amount:,.2f}. "
                f"Se recomienda recordar al cliente sobre el vencimiento."
            )
            notification_type = 'invoice_due_urgent'
        else:
            title = f"TEST - {title_prefix} - {invoice_number}"
            message = (
                f"La factura N° {invoice_number} del cliente {customer_name} "
                f"vence en {days_until_due} días. "
                f"Monto: ${amount:,.2f}."
            )
            notification_type = 'invoice_due_soon'
        
        create_notification(
            agent=agent,
            title=title,
            message=message,
            notification_type=notification_type,
            related_object=related_object
        )