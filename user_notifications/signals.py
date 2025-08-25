"""
Django signals for automatic notification creation.

This module contains signal handlers that automatically create notifications
when certain events occur in the system, such as payment creation.
"""

import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from accounting.models_invoice import Payment
from .checkers import InvoiceDueSoonChecker

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Payment)
def create_payment_received_notification(sender, instance, created, **kwargs):
    """
    Create a payment received notification when a new payment is created.
    
    This signal handler is triggered whenever a Payment instance is saved.
    It only creates notifications for newly created payments (not updates).
    
    Args:
        sender: The Payment model class
        instance: The Payment instance that was saved
        created: Boolean indicating if this is a new instance
        **kwargs: Additional keyword arguments
    """
    if created:  # Only create notifications for new payments
        try:
            checker = InvoiceDueSoonChecker()
            notification = checker.create_payment_received_notification(
                invoice=instance.invoice,
                payment=instance
            )
            
            if notification:
                logger.info(f"Payment received notification created for invoice {instance.invoice.number}")
            else:
                logger.debug(f"No notification created for payment on invoice {instance.invoice.number} (no agent or duplicate)")
                
        except Exception as e:
            logger.error(f"Error creating payment received notification for payment {instance.id}: {e}")