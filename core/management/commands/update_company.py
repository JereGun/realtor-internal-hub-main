"""
Management command to update company information.

Usage:
    python manage.py update_company --name "Nueva Empresa" --email "info@nueva.com"
"""

from django.core.management.base import BaseCommand, CommandError
from django.core.files import File
from core.models import Company, CompanyConfiguration
import os


class Command(BaseCommand):
    help = 'Update company information'

    def add_arguments(self, parser):
        parser.add_argument(
            '--name',
            type=str,
            help='Company name',
        )
        parser.add_argument(
            '--address',
            type=str,
            help='Company address',
        )
        parser.add_argument(
            '--phone',
            type=str,
            help='Company phone number',
        )
        parser.add_argument(
            '--email',
            type=str,
            help='Company email address',
        )
        parser.add_argument(
            '--website',
            type=str,
            help='Company website URL',
        )
        parser.add_argument(
            '--tax-id',
            type=str,
            help='Company tax ID (NIF/CIF)',
        )
        parser.add_argument(
            '--logo',
            type=str,
            help='Path to company logo file',
        )
        parser.add_argument(
            '--city',
            type=str,
            help='Company city',
        )
        parser.add_argument(
            '--state',
            type=str,
            help='Company state/province',
        )
        parser.add_argument(
            '--country',
            type=str,
            help='Company country',
        )
        parser.add_argument(
            '--postal-code',
            type=str,
            help='Company postal code',
        )

    def handle(self, *args, **options):
        try:
            # Get or create company
            company, created = Company.objects.get_or_create(
                id=1,
                defaults={'name': 'Mi Empresa'}
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS('Created new company record')
                )
            
            # Update basic company fields
            updated_fields = []
            
            if options['name']:
                company.name = options['name']
                updated_fields.append('name')
            
            if options['address']:
                company.address = options['address']
                updated_fields.append('address')
            
            if options['phone']:
                company.phone = options['phone']
                updated_fields.append('phone')
            
            if options['email']:
                company.email = options['email']
                updated_fields.append('email')
            
            if options['website']:
                website = options['website']
                if not website.startswith(('http://', 'https://')):
                    website = 'https://' + website
                company.website = website
                updated_fields.append('website')
            
            if options['tax_id']:
                company.tax_id = options['tax_id'].upper()
                updated_fields.append('tax_id')
            
            if options['logo']:
                logo_path = options['logo']
                if os.path.exists(logo_path):
                    with open(logo_path, 'rb') as f:
                        company.logo.save(
                            os.path.basename(logo_path),
                            File(f),
                            save=False
                        )
                    updated_fields.append('logo')
                else:
                    self.stdout.write(
                        self.style.ERROR(f'Logo file not found: {logo_path}')
                    )
            
            # Save company changes
            if updated_fields:
                company.save()
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Updated company fields: {", ".join(updated_fields)}'
                    )
                )
            
            # Update additional configurations
            config_updates = []
            
            if options['city']:
                CompanyConfiguration.objects.update_or_create(
                    company=company,
                    config_key='city',
                    defaults={'config_value': options['city'], 'config_type': 'string'}
                )
                config_updates.append('city')
            
            if options['state']:
                CompanyConfiguration.objects.update_or_create(
                    company=company,
                    config_key='state_province',
                    defaults={'config_value': options['state'], 'config_type': 'string'}
                )
                config_updates.append('state_province')
            
            if options['country']:
                CompanyConfiguration.objects.update_or_create(
                    company=company,
                    config_key='country',
                    defaults={'config_value': options['country'], 'config_type': 'string'}
                )
                config_updates.append('country')
            
            if options['postal_code']:
                CompanyConfiguration.objects.update_or_create(
                    company=company,
                    config_key='postal_code',
                    defaults={'config_value': options['postal_code'], 'config_type': 'string'}
                )
                config_updates.append('postal_code')
            
            if config_updates:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Updated configurations: {", ".join(config_updates)}'
                    )
                )
            
            # Display current company information
            self.stdout.write('\n' + self.style.SUCCESS('Current company information:'))
            self.stdout.write(f'Name: {company.name}')
            self.stdout.write(f'Address: {company.address or "Not set"}')
            self.stdout.write(f'Phone: {company.phone or "Not set"}')
            self.stdout.write(f'Email: {company.email or "Not set"}')
            self.stdout.write(f'Website: {company.website or "Not set"}')
            self.stdout.write(f'Tax ID: {company.tax_id or "Not set"}')
            self.stdout.write(f'Logo: {"Set" if company.logo else "Not set"}')
            
            # Display configurations
            configs = CompanyConfiguration.objects.filter(company=company)
            if configs.exists():
                self.stdout.write('\nAdditional configurations:')
                for config in configs:
                    self.stdout.write(f'{config.config_key}: {config.get_value()}')
            
        except Exception as e:
            raise CommandError(f'Error updating company: {str(e)}')