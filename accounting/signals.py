"""
Django signals for invoice and payment notifications.

This module handles automatic notification creation when payments are recorded
or invoice statuses change, integrating with the user notification system.
"""

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from user_notifications.checkers import InvoiceDueSoonChecker
from user_notifications.services import create_notification_if_not_exists
from .models_invoice import Payment, Invoice
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Payment)
def payment_received_notification(sender, instance, created, **kwargs):
    """
    Create a notification when a payment is received for an invoice.
    
    Args:
        sender: The Payment model class
        instance: The Payment instance that was saved
        created: Boolean indicating if this is a new payment
        **kwargs: Additional keyword arguments
    """
    if created:  # Only trigger for new payments
        try:
            invoice = instance.invoice
            agent = invoice.customer.agent if hasattr(invoice.customer, 'agent') else None
            
            # Try to get agent from contract if not found on customer
            if not agent and invoice.contract:
                agent = invoice.contract.agent
            
            if not agent:
                logger.warning(f"No agent found for payment {instance.id} on invoice {invoice.number}")
                return
            
            # Calculate remaining balance after this payment
            remaining_balance = invoice.get_balance()
            
            # Create appropriate notification based on payment status
            if remaining_balance <= 0:
                # Invoice is fully paid
                title = f"Factura Totalmente Pagada - {invoice.number}"
                message = (
                    f"La factura N° {invoice.number} del cliente {invoice.customer.get_full_name()} "
                    f"ha sido completamente pagada con un pago de ${instance.amount:,.2f}. "
                    f"El estado de la factura ha sido actualizado automáticamente."
                )
                notification_type = 'invoice_fully_paid'
            else:
                # Partial payment
                title = f"Pago Parcial Recibido - {invoice.number}"
                message = (
                    f"Se recibió un pago de ${instance.amount:,.2f} para la factura N° {invoice.number} "
                    f"del cliente {invoice.customer.get_full_name()}. "
                    f"Saldo restante: ${remaining_balance:,.2f}."
                )
                notification_type = 'invoice_payment_received'
            
            # Create the notification
            notification, created_notification = create_notification_if_not_exists(
                agent=agent,
                title=title,
                message=message,
                notification_type=notification_type,
                related_object=invoice,
                duplicate_threshold_days=1
            )
            
            if created_notification:
                logger.info(f"Payment notification created for payment {instance.id}")
            else:
                logger.debug(f"Duplicate payment notification prevented for payment {instance.id}")
                
        except Exception as e:
            logger.error(f"Error creating payment notification for payment {instance.id}: {e}")


@receiver(pre_save, sender=Invoice)
def track_invoice_status_changes(sender, instance, **kwargs):
    """
    Track invoice status changes to create appropriate notifications.
    
    Args:
        sender: The Invoice model class
        instance: The Invoice instance about to be saved
        **kwargs: Additional keyword arguments
    """
    if instance.pk:  # Only for existing invoices
        try:
            old_invoice = Invoice.objects.get(pk=instance.pk)
            old_status = old_invoice.status
            new_status = instance.status
            
            # Store old status for post_save signal
            instance._old_status = old_status
            
        except Invoice.DoesNotExist:
            # This shouldn't happen, but handle gracefully
            instance._old_status = None


@receiver(post_save, sender=Invoice)
def invoice_status_change_notification(sender, instance, created, **kwargs):
    """
    Create a notification when an invoice status changes.
    
    Args:
        sender: The Invoice model class
        instance: The Invoice instance that was saved
        created: Boolean indicating if this is a new invoice
        **kwargs: Additional keyword arguments
    """
    if not created and hasattr(instance, '_old_status') and instance._old_status:
        try:
            old_status = instance._old_status
            new_status = instance.status
            
            # Only notify for significant status changes
            significant_changes = [
                ('draft', 'validated'),
                ('validated', 'sent'), 
                ('sent', 'paid'),
                ('paid', 'sent'),  # If payment was reversed
                ('validated', 'cancelled'),
                ('sent', 'cancelled'),
                ('cancelled', 'validated'),
                ('cancelled', 'sent'),
            ]
            
            if (old_status, new_status) not in significant_changes:
                return
            
            agent = instance.customer.agent if hasattr(instance.customer, 'agent') else None
            
            # Try to get agent from contract if not found on customer
            if not agent and instance.contract:
                agent = instance.contract.agent
            
            if not agent:
                logger.warning(f"No agent found for invoice status change {instance.number}")
                return
            
            # Create appropriate notification based on status change
            status_messages = {
                'validated': 'validada',
                'sent': 'enviada',
                'paid': 'pagada',
                'cancelled': 'cancelada',
            }
            
            old_status_text = status_messages.get(old_status, old_status)
            new_status_text = status_messages.get(new_status, new_status)
            
            title = f"Cambio de Estado - Factura {instance.number}"
            message = (
                f"La factura N° {instance.number} del cliente {instance.customer.get_full_name()} "
                f"cambió de estado de '{old_status_text}' a '{new_status_text}'."
            )
            
            # Add specific context for certain status changes
            if new_status == 'paid':
                message += f" Saldo final: ${instance.get_balance():,.2f}."
            elif new_status == 'cancelled':
                message += " Esta factura ya no está activa en el sistema."
            
            notification, created_notification = create_notification_if_not_exists(
                agent=agent,
                title=title,
                message=message,
                notification_type='invoice_status_change',
                related_object=instance,
                duplicate_threshold_days=1
            )
            
            if created_notification:
                logger.info(f"Status change notification created for invoice {instance.number}")
                
        except Exception as e:
            logger.error(f"Error creating status change notification for invoice {instance.number}: {e}")


@receiver(post_save, sender=Payment)
def update_invoice_status_after_payment(sender, instance, created, **kwargs):
    """
    Update invoice status after payment is recorded.
    
    Args:
        sender: The Payment model class
        instance: The Payment instance that was saved
        created: Boolean indicating if this is a new payment
        **kwargs: Additional keyword arguments
    """
    if created:  # Only for new payments
        try:
            # Update the invoice status based on balance
            instance.invoice.update_status()
            logger.info(f"Updated invoice status for invoice {instance.invoice.number} after payment")
            
        except Exception as e:
            logger.error(f"Error updating invoice status after payment {instance.id}: {e}")
