"""
Business logic checker classes for notification system.

This module contains checker classes that implement the business logic
for determining when notifications should be created for different types
of events in the real estate management system.
"""

import logging
from datetime import date, timedelta
from django.utils import timezone
from django.db.models import Q
from contracts.models import Contract
from accounting.models_invoice import Invoice
from .services import create_notification_if_not_exists

logger = logging.getLogger(__name__)


class ContractExpirationChecker:
    """
    Checker class for contract expiration notifications.
    
    Handles the business logic for identifying contracts that are expiring
    and creating appropriate notifications based on urgency levels.
    """
    
    def __init__(self):
        self.today = timezone.now().date()
    
    def get_expiring_contracts(self, days_threshold=30):
        """
        Get contracts expiring within the specified threshold.
        
        Args:
            days_threshold (int): Number of days to look ahead for expiring contracts
            
        Returns:
            QuerySet: Contracts expiring within the threshold
        """
        threshold_date = self.today + timedelta(days=days_threshold)
        
        return Contract.objects.filter(
            status=Contract.STATUS_ACTIVE,
            end_date__isnull=False,
            end_date__lte=threshold_date,
            end_date__gte=self.today
        ).select_related('agent', 'property', 'customer')
    
    def get_expired_contracts(self):
        """
        Get contracts that have already expired.
        
        Returns:
            QuerySet: Contracts that have expired
        """
        return Contract.objects.filter(
            status=Contract.STATUS_ACTIVE,
            end_date__isnull=False,
            end_date__lt=self.today
        ).select_related('agent', 'property', 'customer')
    
    def should_notify(self, contract, notification_type):
        """
        Determine if a notification should be created for this contract.
        
        Args:
            contract (Contract): The contract to check
            notification_type (str): Type of notification to check
            
        Returns:
            bool: True if notification should be created
        """
        # Check if agent has notification preferences
        try:
            from .models_preferences import NotificationPreference
            preferences = NotificationPreference.objects.get(agent=contract.agent)
            
            # Check if contract expiration notifications are enabled
            return preferences.receive_contract_expiration
        except NotificationPreference.DoesNotExist:
            # Default to creating notifications if no preferences set
            return True
    
    def create_expiration_notification(self, contract, days_until_expiry):
        """
        Create an expiration notification for a contract.
        
        Args:
            contract (Contract): The contract that is expiring
            days_until_expiry (int): Number of days until expiry (negative if expired)
        """
        if days_until_expiry < 0:
            # Contract has expired
            title = f"Contrato Vencido - {contract.property.title}"
            message = (
                f"El contrato para la propiedad '{contract.property.title}' "
                f"del cliente {contract.customer.full_name} venció el "
                f"{contract.end_date.strftime('%d/%m/%Y')}. "
                f"Se requiere acción inmediata."
            )
            notification_type = 'contract_expired'
        elif days_until_expiry <= 7:
            # Contract expires within 7 days - urgent
            title = f"Contrato Vence Pronto - {contract.property.title}"
            message = (
                f"El contrato para la propiedad '{contract.property.title}' "
                f"del cliente {contract.customer.full_name} vence en "
                f"{days_until_expiry} día{'s' if days_until_expiry != 1 else ''} "
                f"({contract.end_date.strftime('%d/%m/%Y')}). "
                f"Se requiere renovación o finalización."
            )
            notification_type = 'contract_expiring_urgent'
        else:
            # Contract expires within 30 days - advance notice
            title = f"Contrato Próximo a Vencer - {contract.property.title}"
            message = (
                f"El contrato para la propiedad '{contract.property.title}' "
                f"del cliente {contract.customer.full_name} vence en "
                f"{days_until_expiry} días ({contract.end_date.strftime('%d/%m/%Y')}). "
                f"Considere iniciar el proceso de renovación."
            )
            notification_type = 'contract_expiring_soon'
        
        notification, created = create_notification_if_not_exists(
            agent=contract.agent,
            title=title,
            message=message,
            notification_type=notification_type,
            related_object=contract,
            duplicate_threshold_days=1
        )
        return notification
    
    def check_and_notify(self):
        """
        Check for expiring contracts and create notifications.
        
        Returns:
            dict: Summary of notifications created
        """
        results = {
            'expired_notifications': 0,
            'urgent_notifications': 0,
            'advance_notifications': 0,
            'total_notifications': 0
        }
        
        # Check expired contracts
        expired_contracts = self.get_expired_contracts()
        for contract in expired_contracts:
            if self.should_notify(contract, 'contract_expired'):
                days_until_expiry = (contract.end_date - self.today).days
                notification = self.create_expiration_notification(contract, days_until_expiry)
                if notification:  # Only count if notification was actually created (not duplicate)
                    results['expired_notifications'] += 1
        
        # Check contracts expiring within 7 days
        urgent_contracts = self.get_expiring_contracts(7)
        for contract in urgent_contracts:
            if self.should_notify(contract, 'contract_expiring_urgent'):
                days_until_expiry = (contract.end_date - self.today).days
                if days_until_expiry <= 7:  # Double check to avoid duplicates
                    notification = self.create_expiration_notification(contract, days_until_expiry)
                    if notification:  # Only count if notification was actually created (not duplicate)
                        results['urgent_notifications'] += 1
        
        # Check contracts expiring within 30 days (but not within 7 days)
        advance_contracts = self.get_expiring_contracts(30).exclude(
            end_date__lte=self.today + timedelta(days=7)
        )
        for contract in advance_contracts:
            if self.should_notify(contract, 'contract_expiring_soon'):
                days_until_expiry = (contract.end_date - self.today).days
                notification = self.create_expiration_notification(contract, days_until_expiry)
                if notification:  # Only count if notification was actually created (not duplicate)
                    results['advance_notifications'] += 1
        
        results['total_notifications'] = (
            results['expired_notifications'] + 
            results['urgent_notifications'] + 
            results['advance_notifications']
        )
        
        return results


class InvoiceOverdueChecker:
    """
    Checker class for overdue invoice notifications.
    
    Handles the business logic for identifying overdue invoices and creating
    escalating notifications based on how long they have been overdue.
    """
    
    def __init__(self):
        self.today = timezone.now().date()
    
    def get_overdue_invoices(self):
        """
        Get invoices that are overdue with outstanding balances.
        
        Returns:
            QuerySet: Overdue invoices with balances > 0
        """
        return Invoice.objects.filter(
            due_date__lt=self.today,
            status__in=['validated', 'sent']  # Exclude draft, paid, and cancelled
        ).select_related('customer', 'contract__agent')
    
    def calculate_days_overdue(self, invoice):
        """
        Calculate how many days an invoice is overdue.
        
        Args:
            invoice (Invoice): The invoice to check
            
        Returns:
            int: Number of days overdue
        """
        return (self.today - invoice.due_date).days
    
    def should_notify(self, invoice, notification_type):
        """
        Determine if a notification should be created for this invoice.
        
        Args:
            invoice (Invoice): The invoice to check
            notification_type (str): Type of notification to check
            
        Returns:
            bool: True if notification should be created
        """
        # Get the agent from the contract if available
        agent = invoice.contract.agent if invoice.contract else None
        if not agent:
            return False
        
        try:
            from .models_preferences import NotificationPreference
            preferences = NotificationPreference.objects.get(agent=agent)
            return preferences.receive_invoice_overdue and preferences.email_notifications
        except NotificationPreference.DoesNotExist:
            return True
    
    def create_overdue_notification(self, invoice, days_overdue):
        """
        Create an overdue notification for an invoice.
        
        Args:
            invoice (Invoice): The overdue invoice
            days_overdue (int): Number of days the invoice is overdue
        """
        agent = invoice.contract.agent if invoice.contract else None
        if not agent:
            return None
        
        balance = invoice.get_balance()
        
        if days_overdue >= 30:
            # Critical overdue - 30+ days
            title = f"Factura Crítica Vencida - {invoice.number}"
            message = (
                f"La factura N° {invoice.number} del cliente {invoice.customer.full_name} "
                f"está vencida hace {days_overdue} días. "
                f"Saldo pendiente: ${balance:,.2f}. "
                f"Se requiere acción urgente para la cobranza."
            )
            notification_type = 'invoice_overdue_critical'
        elif days_overdue >= 7:
            # Urgent overdue - 7-29 days
            title = f"Factura Urgente Vencida - {invoice.number}"
            message = (
                f"La factura N° {invoice.number} del cliente {invoice.customer.full_name} "
                f"está vencida hace {days_overdue} días. "
                f"Saldo pendiente: ${balance:,.2f}. "
                f"Se recomienda contactar al cliente."
            )
            notification_type = 'invoice_overdue_urgent'
        else:
            # Standard overdue - 1-6 days
            title = f"Factura Vencida - {invoice.number}"
            message = (
                f"La factura N° {invoice.number} del cliente {invoice.customer.full_name} "
                f"está vencida hace {days_overdue} día{'s' if days_overdue != 1 else ''}. "
                f"Saldo pendiente: ${balance:,.2f}."
            )
            notification_type = 'invoice_overdue'
        
        notification, created = create_notification_if_not_exists(
            agent=agent,
            title=title,
            message=message,
            notification_type=notification_type,
            related_object=invoice,
            duplicate_threshold_days=1
        )
        return notification
    
    def check_and_notify(self):
        """
        Check for overdue invoices and create notifications.
        
        Returns:
            dict: Summary of notifications created
        """
        results = {
            'standard_overdue': 0,
            'urgent_overdue': 0,
            'critical_overdue': 0,
            'total_notifications': 0
        }
        
        overdue_invoices = self.get_overdue_invoices()
        
        for invoice in overdue_invoices:
            # Only process invoices with outstanding balances
            if invoice.get_balance() > 0:
                if self.should_notify(invoice, 'invoice_overdue'):
                    days_overdue = self.calculate_days_overdue(invoice)
                    self.create_overdue_notification(invoice, days_overdue)
                    
                    if days_overdue >= 30:
                        results['critical_overdue'] += 1
                    elif days_overdue >= 7:
                        results['urgent_overdue'] += 1
                    else:
                        results['standard_overdue'] += 1
        
        results['total_notifications'] = (
            results['standard_overdue'] + 
            results['urgent_overdue'] + 
            results['critical_overdue']
        )
        
        return results


class RentIncreaseChecker:
    """
    Checker class for rent increase notifications.
    
    Handles the business logic for identifying contracts that have rent increases
    due and creating appropriate notifications. Supports different increase frequencies
    and provides methods for calculating next increase dates.
    """
    
    def __init__(self):
        self.today = timezone.now().date()
    
    def get_contracts_with_increases_due(self, days_threshold=7):
        """
        Get contracts with rent increases due within the threshold.
        
        Args:
            days_threshold (int): Number of days to look ahead
            
        Returns:
            QuerySet: Contracts with increases due
        """
        threshold_date = self.today + timedelta(days=days_threshold)
        
        return Contract.objects.filter(
            status=Contract.STATUS_ACTIVE,
            next_increase_date__isnull=False,
            next_increase_date__lte=threshold_date
        ).select_related('agent', 'property', 'customer')
    
    def get_overdue_increases(self):
        """
        Get contracts with overdue rent increases.
        
        Returns:
            QuerySet: Contracts with overdue increases
        """
        return Contract.objects.filter(
            status=Contract.STATUS_ACTIVE,
            next_increase_date__isnull=False,
            next_increase_date__lt=self.today
        ).select_related('agent', 'property', 'customer')
    
    def should_notify(self, contract, notification_type):
        """
        Determine if a notification should be created for this contract.
        
        Args:
            contract (Contract): The contract to check
            notification_type (str): Type of notification to check
            
        Returns:
            bool: True if notification should be created
        """
        try:
            from .models_preferences import NotificationPreference
            preferences = NotificationPreference.objects.get(agent=contract.agent)
            return preferences.receive_rent_increase and preferences.email_notifications
        except NotificationPreference.DoesNotExist:
            return True
    
    def calculate_days_until_increase(self, contract):
        """
        Calculate how many days until the next rent increase.
        
        Args:
            contract (Contract): The contract to check
            
        Returns:
            int: Number of days until increase (negative if overdue, None if no increase date)
        """
        if not contract.next_increase_date:
            return None
        
        return (contract.next_increase_date - self.today).days
    
    def get_increase_frequency_display(self, contract):
        """
        Get a human-readable display of the increase frequency.
        
        Args:
            contract (Contract): The contract to check
            
        Returns:
            str: Human-readable frequency description
        """
        if not contract.frequency:
            return "Sin frecuencia definida"
        
        frequency_map = {
            'monthly': 'Mensual',
            'quarterly': 'Trimestral', 
            'semi-annually': 'Semestral',
            'annually': 'Anual'
        }
        
        return frequency_map.get(contract.frequency, contract.frequency.title())
    
    def calculate_next_increase_date(self, contract, from_date=None):
        """
        Calculate the next increase date based on the contract's frequency.
        
        Args:
            contract (Contract): The contract to calculate for
            from_date (date, optional): Date to calculate from (defaults to current increase date)
            
        Returns:
            date: The calculated next increase date, or None if frequency not set
        """
        if not contract.frequency:
            return None
        
        base_date = from_date or contract.next_increase_date or contract.start_date
        
        if contract.frequency == 'monthly':
            # Add one month
            if base_date.month == 12:
                return base_date.replace(year=base_date.year + 1, month=1)
            else:
                try:
                    return base_date.replace(month=base_date.month + 1)
                except ValueError:
                    # Handle cases like Jan 31 -> Feb 28/29
                    next_month = base_date.month + 1
                    year = base_date.year
                    if next_month > 12:
                        next_month = 1
                        year += 1
                    
                    # Find the last day of the next month
                    import calendar
                    last_day = calendar.monthrange(year, next_month)[1]
                    day = min(base_date.day, last_day)
                    return base_date.replace(year=year, month=next_month, day=day)
        
        elif contract.frequency == 'quarterly':
            # Add 3 months
            month = base_date.month + 3
            year = base_date.year
            while month > 12:
                month -= 12
                year += 1
            
            try:
                return base_date.replace(year=year, month=month)
            except ValueError:
                # Handle day overflow
                import calendar
                last_day = calendar.monthrange(year, month)[1]
                day = min(base_date.day, last_day)
                return base_date.replace(year=year, month=month, day=day)
        
        elif contract.frequency == 'semi-annually':
            # Add 6 months
            month = base_date.month + 6
            year = base_date.year
            if month > 12:
                month -= 12
                year += 1
            
            try:
                return base_date.replace(year=year, month=month)
            except ValueError:
                # Handle day overflow
                import calendar
                last_day = calendar.monthrange(year, month)[1]
                day = min(base_date.day, last_day)
                return base_date.replace(year=year, month=month, day=day)
        
        elif contract.frequency == 'annually':
            # Add one year
            try:
                return base_date.replace(year=base_date.year + 1)
            except ValueError:
                # Handle leap year edge case (Feb 29)
                return base_date.replace(year=base_date.year + 1, day=28)
        
        return None
    
    def create_rent_increase_notification(self, contract, days_until_increase):
        """
        Create a rent increase notification for a contract.
        
        Args:
            contract (Contract): The contract with rent increase due
            days_until_increase (int): Days until increase (negative if overdue)
        """
        frequency_display = self.get_increase_frequency_display(contract)
        
        if days_until_increase < 0:
            # Rent increase is overdue
            title = f"Aumento de Alquiler Vencido - {contract.property.title}"
            message = (
                f"El aumento de alquiler para la propiedad '{contract.property.title}' "
                f"del cliente {contract.customer.full_name} estaba programado para el "
                f"{contract.next_increase_date.strftime('%d/%m/%Y')} "
                f"(hace {abs(days_until_increase)} día{'s' if abs(days_until_increase) != 1 else ''}). "
                f"Monto actual: ${contract.amount:,.2f}. "
                f"Frecuencia: {frequency_display}. "
                f"Se requiere procesar el aumento urgentemente."
            )
            notification_type = 'rent_increase_overdue'
        else:
            # Rent increase is due soon
            title = f"Aumento de Alquiler Próximo - {contract.property.title}"
            message = (
                f"El aumento de alquiler para la propiedad '{contract.property.title}' "
                f"del cliente {contract.customer.full_name} está programado para el "
                f"{contract.next_increase_date.strftime('%d/%m/%Y')} "
                f"({days_until_increase} día{'s' if days_until_increase != 1 else ''}). "
                f"Monto actual: ${contract.amount:,.2f}. "
                f"Frecuencia: {frequency_display}. "
                f"Prepare el nuevo monto para el aumento."
            )
            notification_type = 'rent_increase_due'
        
        notification, created = create_notification_if_not_exists(
            agent=contract.agent,
            title=title,
            message=message,
            notification_type=notification_type,
            related_object=contract,
            duplicate_threshold_days=1
        )
        return notification, created
    
    def check_and_notify(self):
        """
        Check for rent increases and create notifications.
        
        Returns:
            dict: Summary of notifications created
        """
        results = {
            'overdue_increases': 0,
            'upcoming_increases': 0,
            'total_notifications': 0,
            'contracts_processed': 0
        }
        
        # Check overdue increases
        overdue_contracts = self.get_overdue_increases()
        for contract in overdue_contracts:
            results['contracts_processed'] += 1
            if self.should_notify(contract, 'rent_increase_overdue'):
                days_until_increase = self.calculate_days_until_increase(contract)
                notification, created = self.create_rent_increase_notification(contract, days_until_increase)
                if created:
                    results['overdue_increases'] += 1
        
        # Check upcoming increases (within 7 days, but not overdue)
        upcoming_contracts = self.get_contracts_with_increases_due(7).filter(
            next_increase_date__gte=self.today
        )
        for contract in upcoming_contracts:
            results['contracts_processed'] += 1
            if self.should_notify(contract, 'rent_increase_due'):
                days_until_increase = self.calculate_days_until_increase(contract)
                notification, created = self.create_rent_increase_notification(contract, days_until_increase)
                if created:
                    results['upcoming_increases'] += 1
        
        results['total_notifications'] = (
            results['overdue_increases'] + 
            results['upcoming_increases']
        )
        
        logger.info(f"Rent increase check completed: {results}")
        return results
    
    def process_rent_increase(self, contract, new_amount, processed_date=None):
        """
        Process a rent increase for a contract and update the next increase date.
        
        This method should be called when an agent has manually processed a rent increase
        to update the contract with the new amount and calculate the next increase date.
        
        Args:
            contract (Contract): The contract to process the increase for
            new_amount (Decimal): The new rent amount
            processed_date (date, optional): Date the increase was processed (defaults to today)
            
        Returns:
            dict: Summary of processing results including next increase date
        """
        if processed_date is None:
            processed_date = self.today
            
        # Store the previous amount for record keeping
        previous_amount = contract.amount
        
        # Calculate increase percentage
        if previous_amount > 0:
            increase_percentage = ((new_amount - previous_amount) / previous_amount) * 100
        else:
            increase_percentage = 0
        
        # Update contract amount
        contract.amount = new_amount
        
        # Calculate next increase date
        next_increase_date = self.calculate_next_increase_date(contract, processed_date)
        if next_increase_date:
            contract.next_increase_date = next_increase_date
        
        # Save the contract
        contract.save()
        
        # Create a ContractIncrease record for history
        try:
            from contracts.models import ContractIncrease
            increase_record = ContractIncrease.objects.create(
                contract=contract,
                previous_amount=previous_amount,
                new_amount=new_amount,
                increase_percentage=increase_percentage,
                effective_date=processed_date,
                notes=f"Aumento procesado automáticamente el {processed_date.strftime('%d/%m/%Y')}"
            )
            
            logger.info(f"Rent increase processed for contract {contract.id}: ${previous_amount} -> ${new_amount} ({increase_percentage:.2f}%)")
            
        except Exception as e:
            logger.warning(f"Could not create ContractIncrease record: {e}")
            increase_record = None
        
        # Return summary
        results = {
            'success': True,
            'contract_id': contract.id,
            'previous_amount': float(previous_amount),
            'new_amount': float(new_amount),
            'increase_percentage': float(increase_percentage),
            'processed_date': processed_date.isoformat(),
            'next_increase_date': next_increase_date.isoformat() if next_increase_date else None,
            'increase_record_created': increase_record is not None
        }
        
        return results
    
    def bulk_process_rent_increases(self, increase_data_list):
        """
        Process multiple rent increases in bulk.
        
        Args:
            increase_data_list: List of dictionaries containing:
                - contract_id: ID of the contract
                - new_amount: New rent amount
                - processed_date: Date processed (optional)
                
        Returns:
            dict: Summary of bulk processing results
        """
        results = {
            'successful_increases': 0,
            'failed_increases': 0,
            'total_processed': len(increase_data_list),
            'details': []
        }
        
        for increase_data in increase_data_list:
            try:
                contract_id = increase_data['contract_id']
                new_amount = increase_data['new_amount']
                processed_date = increase_data.get('processed_date')
                
                # Get the contract
                contract = Contract.objects.get(id=contract_id, status=Contract.STATUS_ACTIVE)
                
                # Process the increase
                result = self.process_rent_increase(contract, new_amount, processed_date)
                
                if result['success']:
                    results['successful_increases'] += 1
                    results['details'].append({
                        'contract_id': contract_id,
                        'status': 'success',
                        'result': result
                    })
                else:
                    results['failed_increases'] += 1
                    results['details'].append({
                        'contract_id': contract_id,
                        'status': 'failed',
                        'error': 'Processing failed'
                    })
                    
            except Contract.DoesNotExist:
                results['failed_increases'] += 1
                results['details'].append({
                    'contract_id': increase_data.get('contract_id', 'unknown'),
                    'status': 'failed',
                    'error': 'Contract not found or not active'
                })
                logger.error(f"Contract {increase_data.get('contract_id')} not found or not active for rent increase")
                
            except Exception as e:
                results['failed_increases'] += 1
                results['details'].append({
                    'contract_id': increase_data.get('contract_id', 'unknown'),
                    'status': 'failed',
                    'error': str(e)
                })
                logger.error(f"Error processing rent increase for contract {increase_data.get('contract_id')}: {e}")
        
        logger.info(f"Bulk rent increase processing completed: {results['successful_increases']}/{results['total_processed']} successful")
        return results


class InvoiceDueSoonChecker:
    """
    Checker class for invoice due soon notifications.
    
    Handles the business logic for identifying invoices that are approaching
    their due dates and creating advance notice notifications.
    """
    
    def __init__(self):
        self.today = timezone.now().date()
    
    def get_due_soon_invoices(self, days_threshold=7):
        """
        Get invoices due within the specified threshold.
        
        Args:
            days_threshold (int): Number of days to look ahead
            
        Returns:
            QuerySet: Invoices due within the threshold
        """
        threshold_date = self.today + timedelta(days=days_threshold)
        
        return Invoice.objects.filter(
            due_date__lte=threshold_date,
            due_date__gte=self.today,
            status__in=['validated', 'sent']  # Exclude draft, paid, and cancelled
        ).select_related('customer', 'contract__agent')
    
    def calculate_days_until_due(self, invoice):
        """
        Calculate how many days until an invoice is due.
        
        Args:
            invoice (Invoice): The invoice to check
            
        Returns:
            int: Number of days until due
        """
        return (invoice.due_date - self.today).days
    
    def should_notify(self, invoice, notification_type):
        """
        Determine if a notification should be created for this invoice.
        
        Args:
            invoice (Invoice): The invoice to check
            notification_type (str): Type of notification to check
            
        Returns:
            bool: True if notification should be created
        """
        agent = invoice.contract.agent if invoice.contract else None
        if not agent:
            return False
        
        try:
            from .models_preferences import NotificationPreference
            preferences = NotificationPreference.objects.get(agent=agent)
            return preferences.receive_invoice_due_soon and preferences.email_notifications
        except NotificationPreference.DoesNotExist:
            return True
    
    def create_due_soon_notification(self, invoice, days_until_due):
        """
        Create a due soon notification for an invoice.
        
        Args:
            invoice (Invoice): The invoice that is due soon
            days_until_due (int): Number of days until due
        """
        agent = invoice.contract.agent if invoice.contract else None
        if not agent:
            return None
        
        balance = invoice.get_balance()
        
        if days_until_due <= 3:
            # Urgent - due within 3 days
            title = f"Factura Vence Pronto - {invoice.number}"
            message = (
                f"La factura N° {invoice.number} del cliente {invoice.customer.full_name} "
                f"vence en {days_until_due} día{'s' if days_until_due != 1 else ''} "
                f"({invoice.due_date.strftime('%d/%m/%Y')}). "
                f"Saldo pendiente: ${balance:,.2f}. "
                f"Se recomienda recordar al cliente sobre el vencimiento."
            )
            notification_type = 'invoice_due_urgent'
        else:
            # Standard - due within 7 days
            title = f"Recordatorio de Vencimiento - {invoice.number}"
            message = (
                f"La factura N° {invoice.number} del cliente {invoice.customer.full_name} "
                f"vence en {days_until_due} días ({invoice.due_date.strftime('%d/%m/%Y')}). "
                f"Saldo pendiente: ${balance:,.2f}."
            )
            notification_type = 'invoice_due_soon'
        
        notification, created = create_notification_if_not_exists(
            agent=agent,
            title=title,
            message=message,
            notification_type=notification_type,
            related_object=invoice,
            duplicate_threshold_days=1
        )
        return notification
    
    def create_payment_received_notification(self, invoice, payment):
        """
        Create a payment received notification for an invoice.
        
        Args:
            invoice (Invoice): The invoice that received payment
            payment (Payment): The payment that was received
        """
        agent = invoice.contract.agent if invoice.contract else None
        if not agent:
            return None
        
        remaining_balance = invoice.get_balance()
        
        title = f"Pago Recibido - {invoice.number}"
        message = (
            f"Se recibió un pago de ${payment.amount:,.2f} para la factura N° {invoice.number} "
            f"del cliente {invoice.customer.full_name}. "
            f"Saldo restante: ${remaining_balance:,.2f}."
        )
        
        notification, created = create_notification_if_not_exists(
            agent=agent,
            title=title,
            message=message,
            notification_type='invoice_payment_received',
            related_object=invoice,
            duplicate_threshold_days=1
        )
        return notification
    
    def check_and_notify(self):
        """
        Check for invoices due soon and create notifications.
        
        Returns:
            dict: Summary of notifications created
        """
        results = {
            'urgent_due_soon': 0,
            'standard_due_soon': 0,
            'total_notifications': 0
        }
        
        # Check invoices due within 3 days
        urgent_invoices = self.get_due_soon_invoices(3)
        for invoice in urgent_invoices:
            if invoice.get_balance() > 0:  # Only notify for unpaid invoices
                if self.should_notify(invoice, 'invoice_due_urgent'):
                    days_until_due = self.calculate_days_until_due(invoice)
                    self.create_due_soon_notification(invoice, days_until_due)
                    results['urgent_due_soon'] += 1
        
        # Check invoices due within 7 days (but not within 3 days)
        standard_invoices = self.get_due_soon_invoices(7).exclude(
            due_date__lte=self.today + timedelta(days=3)
        )
        for invoice in standard_invoices:
            if invoice.get_balance() > 0:  # Only notify for unpaid invoices
                if self.should_notify(invoice, 'invoice_due_soon'):
                    days_until_due = self.calculate_days_until_due(invoice)
                    self.create_due_soon_notification(invoice, days_until_due)
                    results['standard_due_soon'] += 1
        
        results['total_notifications'] = (
            results['urgent_due_soon'] + 
            results['standard_due_soon']
        )
        
        return results