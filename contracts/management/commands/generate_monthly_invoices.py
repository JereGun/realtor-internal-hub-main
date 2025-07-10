from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from django.db import transaction

from contracts.models import Contract
# Import from accounting app
from accounting.models_invoice import Invoice as AccountingInvoice, InvoiceLine as AccountingInvoiceLine
# Ensure Customer model is imported if needed for type hinting or direct use, though it's accessed via contract.customer
# from customers.models import Customer 

class Command(BaseCommand):
    help = 'Genera facturas de alquiler (en app accounting) en estado borrador para todos los contratos activos de alquiler al inicio de cada mes.'

    def _generate_next_invoice_number(self):
        """
        Generates a simple next invoice number.
        NOTE: This is a simplified version. In a real scenario, 
        this should use a more robust sequencing mechanism, potentially from the accounting app's Journal.
        """
        # A possible prefix, can be customized or made more dynamic
        prefix = "FACT-" 
        last_invoice = AccountingInvoice.objects.filter(number__startswith=prefix).order_by('number').last()
        
        if not last_invoice or not last_invoice.number:
            numeric_part = 1
        else:
            try:
                # Attempt to extract numeric part after the prefix
                numeric_part = int(last_invoice.number[len(prefix):]) + 1
            except (ValueError, TypeError, IndexError):
                # Fallback: count existing invoices with the prefix if number parsing fails
                numeric_part = AccountingInvoice.objects.filter(number__startswith=prefix).count() + 1 
        return f"{prefix}{numeric_part:05d}"


    @transaction.atomic
    def handle(self, *args, **kwargs):
        today = timezone.now().date()
        first_day_of_month = today.replace(day=1)
        
        # Ensure contract_type 'rental' value is correct as per Contract model
        # Assuming Contract.CONTRACT_TYPES = [('sale', 'Venta'), ('rental', 'Alquiler')]
        # So, 'rental' is the correct key.
        active_contracts = Contract.objects.filter(
            contract_type='rental', 
            status__in=[Contract.STATUS_ACTIVE, Contract.STATUS_EXPIRING_SOON]
        ).select_related('customer', 'property', 'agent')

        created_count = 0
        for contract in active_contracts:
            # Avoid duplicates for the current month and contract
            exists = AccountingInvoice.objects.filter(
                contract=contract, 
                date__year=first_day_of_month.year,
                date__month=first_day_of_month.month
            ).exists()

            if not exists:
                invoice_description = f'Factura generada automáticamente para contrato de alquiler: {contract.property.title if contract.property else "N/A"}. Cliente: {contract.customer.full_name}.'
                
                # Determine due date (e.g., 10 days from issue date, or from customer profile)
                # Placeholder for customer-specific payment terms if they exist:
                # due_date_delta_days = getattr(contract.customer, 'payment_term_days', 10)
                due_date_delta_days = 10 
                invoice_due_date = first_day_of_month + timedelta(days=due_date_delta_days)

                # Create Accounting Invoice
                new_accounting_invoice = AccountingInvoice(
                    number=self._generate_next_invoice_number(),
                    date=first_day_of_month,
                    due_date=invoice_due_date,
                    customer=contract.customer,
                    description=invoice_description,
                    # total_amount will be calculated by compute_taxes after lines are added
                    state=AccountingInvoice.STATE_CHOICES[0][0], # Default to first choice ('draft')
                    contract=contract, 
                    property=contract.property 
                    # Currency: accounting.Invoice does not have a direct currency field.
                    # It's often derived from the company or general ledger account in accounting systems.
                    # contract.currency could be stored in a custom field on AccountingInvoice if necessary,
                    # or in the description, or handled by accounting procedures.
                )
                # total_amount is calculated after lines, so we save first, then add lines, then compute.
                new_accounting_invoice.save() 
                
                # Create Accounting Invoice Line
                AccountingInvoiceLine.objects.create(
                    invoice=new_accounting_invoice,
                    concept=f'Alquiler mensual - {contract.property.title if contract.property else "Propiedad"} ({first_day_of_month.strftime("%B %Y")})',
                    amount=contract.amount # This is the total amount for the line
                )
                
                # Recalculate total_amount in AccountingInvoice and save
                new_accounting_invoice.compute_taxes() # This method should sum lines and save.

                created_count += 1
        
        self.stdout.write(self.style.SUCCESS(f'Se generaron {created_count} facturas de alquiler (en app accounting) en borrador.'))