# -*- coding: utf-8 -*-
"""
Management command to assign numbers to invoices that don't have one assigned.

This command identifies invoices without a number and assigns them a sequential
number following the format INV-YEAR-XXX.
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from accounting.models_invoice import Invoice
from django.utils import timezone


class Command(BaseCommand):
    help = 'Assign numbers to invoices that don\'t have one assigned'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes',
        )
        parser.add_argument(
            '--year',
            type=int,
            default=timezone.now().year,
            help='Year to use for invoice numbering (default: current year)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        year = options['year']
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Starting invoice number assignment for year {year}'
            )
        )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No changes will be made')
            )
        
        # Find invoices without numbers
        invoices_without_number = Invoice.objects.filter(
            number__isnull=True
        ) | Invoice.objects.filter(number='')
        
        count = invoices_without_number.count()
        
        if count == 0:
            self.stdout.write(
                self.style.SUCCESS('No invoices found without numbers')
            )
            return
        
        self.stdout.write(f'Found {count} invoices without numbers')
        
        # Find the highest existing number for the year
        year_prefix = f'INV-{year}-'
        existing_invoices = Invoice.objects.filter(
            number__startswith=year_prefix
        ).order_by('number')
        
        if existing_invoices.exists():
            # Extract the highest number
            highest_number = 0
            for invoice in existing_invoices:
                try:
                    number_part = invoice.number.split('-')[-1]
                    number = int(number_part)
                    if number > highest_number:
                        highest_number = number
                except (ValueError, IndexError):
                    continue
        else:
            highest_number = 0
        
        self.stdout.write(f'Starting from number: {highest_number + 1}')
        
        if not dry_run:
            with transaction.atomic():
                for i, invoice in enumerate(invoices_without_number):
                    new_number = highest_number + i + 1
                    formatted_number = f'INV-{year}-{new_number:03d}'
                    
                    # Check if this number already exists
                    while Invoice.objects.filter(number=formatted_number).exists():
                        new_number += 1
                        formatted_number = f'INV-{year}-{new_number:03d}'
                    
                    invoice.number = formatted_number
                    invoice.save(update_fields=['number'])
                    
                    self.stdout.write(
                        f'  Invoice ID {invoice.pk} -> {formatted_number}'
                    )
        else:
            # Dry run - just show what would be done
            for i, invoice in enumerate(invoices_without_number):
                new_number = highest_number + i + 1
                formatted_number = f'INV-{year}-{new_number:03d}'
                
                self.stdout.write(
                    f'  Invoice ID {invoice.pk} -> {formatted_number} (DRY RUN)'
                )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'DRY RUN completed. {count} invoices would be updated.'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully assigned numbers to {count} invoices'
                )
            )
