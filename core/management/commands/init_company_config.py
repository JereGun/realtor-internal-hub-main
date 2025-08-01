from django.core.management.base import BaseCommand
from core.models import Company, SystemConfiguration, DocumentTemplate, NotificationSettings


class Command(BaseCommand):
    help = 'Inicializa configuraciones por defecto para la empresa'

    def add_arguments(self, parser):
        parser.add_argument(
            '--company-id',
            type=int,
            default=1,
            help='ID de la empresa para inicializar configuraciones'
        )

    def handle(self, *args, **options):
        company_id = options['company_id']
        
        try:
            company = Company.objects.get(id=company_id)
        except Company.DoesNotExist:
            # Crear empresa por defecto si no existe
            company = Company.objects.create(
                id=company_id,
                name='Mi Empresa Inmobiliaria',
                email='info@miempresa.com'
            )
            self.stdout.write(
                self.style.SUCCESS(f'Empresa creada: {company.name}')
            )

        # Crear configuración del sistema si no existe
        system_config, created = SystemConfiguration.objects.get_or_create(
            company=company,
            defaults={
                'currency': 'EUR',
                'timezone': 'Europe/Madrid',
                'date_format': 'DD/MM/YYYY',
                'language': 'es',
                'decimal_places': 2,
                'tax_rate': 21.0,
                'invoice_prefix': 'INV',
                'contract_prefix': 'CON'
            }
        )
        
        if created:
            self.stdout.write(
                self.style.SUCCESS('Configuración del sistema creada')
            )
        else:
            self.stdout.write(
                self.style.WARNING('Configuración del sistema ya existe')
            )

        # Crear plantillas de documentos por defecto
        default_templates = [
            {
                'template_name': 'Factura Estándar',
                'template_type': 'invoice',
                'header_content': '''
                <div class="header">
                    <h1>{{company.name}}</h1>
                    <p>{{company.address}}</p>
                    <p>Tel: {{company.phone}} | Email: {{company.email}}</p>
                    <p>NIF: {{company.tax_id}}</p>
                </div>
                ''',
                'footer_content': '''
                <div class="footer">
                    <p>Gracias por confiar en nosotros</p>
                    <p>{{company.website}}</p>
                </div>
                '''
            },
            {
                'template_name': 'Contrato Estándar',
                'template_type': 'contract',
                'header_content': '''
                <div class="header">
                    <h1>CONTRATO DE ARRENDAMIENTO</h1>
                    <h2>{{company.name}}</h2>
                    <p>{{company.address}}</p>
                </div>
                ''',
                'footer_content': '''
                <div class="footer">
                    <p>Firmado en {{current_date}}</p>
                </div>
                '''
            }
        ]

        for template_data in default_templates:
            template, created = DocumentTemplate.objects.get_or_create(
                company=company,
                template_name=template_data['template_name'],
                template_type=template_data['template_type'],
                defaults={
                    'header_content': template_data['header_content'],
                    'footer_content': template_data['footer_content'],
                    'is_active': True
                }
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Plantilla creada: {template.template_name}')
                )

        # Crear configuraciones de notificaciones por defecto
        default_notifications = [
            {
                'notification_type': 'payment_reminder',
                'is_enabled': True,
                'email_template': '''
                Estimado/a {{customer.name}},
                
                Le recordamos que tiene un pago pendiente por el importe de {{payment.amount}}€.
                Fecha de vencimiento: {{payment.due_date}}
                
                Saludos cordiales,
                {{company.name}}
                ''',
                'frequency_days': 7
            },
            {
                'notification_type': 'contract_expiry',
                'is_enabled': True,
                'email_template': '''
                Estimado/a {{customer.name}},
                
                Su contrato {{contract.number}} vence el {{contract.end_date}}.
                Por favor, póngase en contacto con nosotros para renovar.
                
                Saludos cordiales,
                {{company.name}}
                ''',
                'frequency_days': 30
            }
        ]

        for notification_data in default_notifications:
            notification, created = NotificationSettings.objects.get_or_create(
                company=company,
                notification_type=notification_data['notification_type'],
                defaults={
                    'is_enabled': notification_data['is_enabled'],
                    'email_template': notification_data['email_template'],
                    'frequency_days': notification_data['frequency_days']
                }
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Configuración de notificación creada: {notification.get_notification_type_display()}')
                )

        self.stdout.write(
            self.style.SUCCESS('Inicialización de configuraciones completada')
        )