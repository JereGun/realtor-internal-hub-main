"""
Celery tasks for automated notification checking and creation.

This module contains scheduled tasks that check for various business events
that require notifications to be sent to agents, including contract expirations,
overdue invoices, rent increases, and upcoming invoice due dates.
"""

import logging
from celery import shared_task
from django.utils import timezone
from django.db import transaction, DatabaseError
from .checkers import (
    ContractExpirationChecker,
    InvoiceOverdueChecker, 
    RentIncreaseChecker,
    InvoiceDueSoonChecker
)

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def check_contract_expirations(self):
    """
    Check for contracts that are expiring and create appropriate notifications.
    
    This task identifies contracts that are expiring within 30 days, 7 days,
    or have already expired, and creates notifications for the assigned agents.
    
    Returns:
        dict: Summary of notifications created
    """
    try:
        logger.info("Starting contract expiration check")
        checker = ContractExpirationChecker()
        
        with transaction.atomic():
            results = checker.check_and_notify()
            
        logger.info(f"Contract expiration check completed: {results}")
        return results
        
    except DatabaseError as e:
        logger.error(f"Database error in contract expiration check: {e}")
        raise self.retry(countdown=60 * (2 ** self.request.retries))
    except Exception as e:
        logger.error(f"Unexpected error in contract expiration check: {e}")
        raise


@shared_task(bind=True, max_retries=3)
def check_invoice_overdue(self):
    """
    Check for overdue invoices and create appropriate notifications.
    
    This task identifies invoices that are overdue and creates escalating
    notifications based on how long they have been overdue.
    
    Returns:
        dict: Summary of notifications created
    """
    try:
        logger.info("Starting invoice overdue check")
        checker = InvoiceOverdueChecker()
        
        with transaction.atomic():
            results = checker.check_and_notify()
            
        logger.info(f"Invoice overdue check completed: {results}")
        return results
        
    except DatabaseError as e:
        logger.error(f"Database error in invoice overdue check: {e}")
        raise self.retry(countdown=60 * (2 ** self.request.retries))
    except Exception as e:
        logger.error(f"Unexpected error in invoice overdue check: {e}")
        raise


@shared_task(bind=True, max_retries=3)
def check_rent_increases(self):
    """
    Check for rent increases that are due and create appropriate notifications.
    
    This task identifies contracts that have rent increases due within 7 days
    or are overdue, and creates notifications for the assigned agents.
    
    Returns:
        dict: Summary of notifications created
    """
    try:
        logger.info("Starting rent increase check")
        checker = RentIncreaseChecker()
        
        with transaction.atomic():
            results = checker.check_and_notify()
            
        logger.info(f"Rent increase check completed: {results}")
        return results
        
    except DatabaseError as e:
        logger.error(f"Database error in rent increase check: {e}")
        raise self.retry(countdown=60 * (2 ** self.request.retries))
    except Exception as e:
        logger.error(f"Unexpected error in rent increase check: {e}")
        raise


@shared_task(bind=True, max_retries=3)
def check_invoice_due_soon(self):
    """
    Check for invoices that are due soon and create appropriate notifications.
    
    This task identifies invoices that are due within 7 days or 3 days
    and creates advance notice notifications for the assigned agents.
    
    Returns:
        dict: Summary of notifications created
    """
    try:
        logger.info("Starting invoice due soon check")
        checker = InvoiceDueSoonChecker()
        
        with transaction.atomic():
            results = checker.check_and_notify()
            
        logger.info(f"Invoice due soon check completed: {results}")
        return results
        
    except DatabaseError as e:
        logger.error(f"Database error in invoice due soon check: {e}")
        raise self.retry(countdown=60 * (2 ** self.request.retries))
    except Exception as e:
        logger.error(f"Unexpected error in invoice due soon check: {e}")
        raise


@shared_task(bind=True, max_retries=3)
def process_notification_batches(self):
    """
    Process batched notifications for users who prefer daily/weekly delivery.
    
    This task handles the delivery of batched notifications based on user
    preferences for notification frequency.
    
    Returns:
        dict: Summary of batched notifications processed
    """
    try:
        logger.info("Starting notification batch processing")
        
        from .services import process_ready_notification_batches
        
        with transaction.atomic():
            results = process_ready_notification_batches()
            
        logger.info(f"Notification batch processing completed: {results}")
        return results
        
    except DatabaseError as e:
        logger.error(f"Database error in notification batch processing: {e}")
        raise self.retry(countdown=60 * (2 ** self.request.retries))
    except Exception as e:
        logger.error(f"Unexpected error in notification batch processing: {e}")
        raise