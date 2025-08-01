
from django.db import models
from django.core.exceptions import ValidationError
import json


class BaseModel(models.Model):
    """
    Modelo base abstracto que proporciona campos comunes para todos los modelos del sistema.
    
    Incluye campos para el seguimiento de la creación y actualización de registros,
    permitiendo una auditoría básica de los datos en el sistema.
    """
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Company(models.Model):
    """
    Modelo para almacenar información de la empresa inmobiliaria.
    
    Contiene datos básicos de la empresa como nombre, dirección, información
    de contacto, logotipo e identificación fiscal, necesarios para la
    generación de documentos y configuración del sistema.
    """
    name = models.CharField(max_length=255, help_text="Nombre de la empresa")
    address = models.CharField(max_length=255, blank=True, null=True, help_text="Dirección de la empresa")
    phone = models.CharField(max_length=20, blank=True, null=True, help_text="Teléfono de contacto")
    email = models.EmailField(blank=True, null=True, help_text="Correo electrónico de la empresa")
    website = models.URLField(blank=True, null=True, help_text="Sitio web de la empresa")
    logo = models.ImageField(upload_to='logos/', blank=True, null=True, help_text="Logotipo de la empresa")
    tax_id = models.CharField(max_length=50, blank=True, null=True, help_text="NIF/CIF de la empresa")

    def __str__(self):
        return self.name

    def get_configuration(self, key, default=None):
        """Obtiene una configuración específica de la empresa"""
        try:
            config = self.configurations.get(config_key=key)
            return config.get_value()
        except CompanyConfiguration.DoesNotExist:
            return default

    def set_configuration(self, key, value, config_type='string'):
        """Establece una configuración específica de la empresa"""
        config, created = self.configurations.get_or_create(
            config_key=key,
            defaults={'config_type': config_type}
        )
        config.set_value(value)
        config.save()
        return config

    def get_system_config(self):
        """Obtiene la configuración del sistema para esta empresa"""
        try:
            return self.system_config
        except SystemConfiguration.DoesNotExist:
            return SystemConfiguration.objects.create(company=self)

    def get_active_templates(self, template_type=None):
        """Obtiene plantillas activas, opcionalmente filtradas por tipo"""
        templates = self.document_templates.filter(is_active=True)
        if template_type:
            templates = templates.filter(template_type=template_type)
        return templates

    def get_notification_settings(self, notification_type=None):
        """Obtiene configuraciones de notificación, opcionalmente filtradas por tipo"""
        settings = self.notification_settings.all()
        if notification_type:
            settings = settings.filter(notification_type=notification_type)
        return settings

    class Meta:
        verbose_name = "Compañía"
        verbose_name_plural = "Compañías"


class CompanyConfiguration(BaseModel):
    """
    Modelo para almacenar configuraciones flexibles de la empresa.
    
    Permite almacenar configuraciones clave-valor con diferentes tipos de datos,
    proporcionando flexibilidad para configuraciones futuras sin cambios de esquema.
    """
    CONFIG_TYPES = [
        ('string', 'Texto'),
        ('boolean', 'Verdadero/Falso'),
        ('integer', 'Número Entero'),
        ('decimal', 'Número Decimal'),
        ('json', 'Objeto JSON'),
        ('file', 'Archivo'),
    ]
    
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='configurations')
    config_key = models.CharField(max_length=100, help_text="Clave de configuración")
    config_value = models.TextField(blank=True, null=True, help_text="Valor de configuración")
    config_type = models.CharField(max_length=20, choices=CONFIG_TYPES, default='string', help_text="Tipo de dato")
    
    class Meta:
        unique_together = ['company', 'config_key']
        verbose_name = "Configuración de Empresa"
        verbose_name_plural = "Configuraciones de Empresa"
    
    def __str__(self):
        return f"{self.company.name} - {self.config_key}"
    
    def get_value(self):
        """Retorna el valor convertido al tipo apropiado"""
        if not self.config_value:
            return None
            
        try:
            if self.config_type == 'boolean':
                return self.config_value.lower() in ['true', '1', 'yes', 'on']
            elif self.config_type == 'integer':
                return int(self.config_value)
            elif self.config_type == 'decimal':
                return float(self.config_value)
            elif self.config_type == 'json':
                return json.loads(self.config_value)
            else:
                return self.config_value
        except (ValueError, json.JSONDecodeError):
            return self.config_value
    
    def set_value(self, value):
        """Establece el valor convirtiendo al tipo string para almacenamiento"""
        if value is None:
            self.config_value = None
        elif self.config_type == 'json':
            self.config_value = json.dumps(value)
        elif self.config_type == 'boolean':
            self.config_value = str(bool(value)).lower()
        else:
            self.config_value = str(value)


class SystemConfiguration(BaseModel):
    """
    Modelo para configuraciones específicas del sistema.
    
    Almacena configuraciones operacionales como moneda, zona horaria,
    formatos de fecha y otros parámetros que afectan el comportamiento global del sistema.
    """
    company = models.OneToOneField(Company, on_delete=models.CASCADE, related_name='system_config')
    currency = models.CharField(max_length=3, default='EUR', help_text="Código de moneda (ISO 4217)")
    timezone = models.CharField(max_length=50, default='Europe/Madrid', help_text="Zona horaria del sistema")
    date_format = models.CharField(max_length=20, default='DD/MM/YYYY', help_text="Formato de fecha")
    language = models.CharField(max_length=5, default='es', help_text="Idioma del sistema")
    decimal_places = models.IntegerField(default=2, help_text="Decimales para moneda")
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=21.0, help_text="Tasa de impuesto por defecto (%)")
    invoice_prefix = models.CharField(max_length=10, default='INV', help_text="Prefijo para facturas")
    contract_prefix = models.CharField(max_length=10, default='CON', help_text="Prefijo para contratos")
    
    class Meta:
        verbose_name = "Configuración del Sistema"
        verbose_name_plural = "Configuraciones del Sistema"
    
    def __str__(self):
        return f"Configuración del Sistema - {self.company.name}"


class DocumentTemplate(BaseModel):
    """
    Modelo para plantillas de documentos personalizables.
    
    Permite crear plantillas para diferentes tipos de documentos (facturas, contratos, etc.)
    con contenido personalizable y variables dinámicas.
    """
    TEMPLATE_TYPES = [
        ('invoice', 'Factura'),
        ('contract', 'Contrato'),
        ('receipt', 'Recibo'),
        ('report', 'Reporte'),
        ('email', 'Email'),
        ('letter', 'Carta'),
    ]
    
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='document_templates')
    template_name = models.CharField(max_length=100, help_text="Nombre de la plantilla")
    template_type = models.CharField(max_length=50, choices=TEMPLATE_TYPES, help_text="Tipo de documento")
    header_content = models.TextField(blank=True, null=True, help_text="Contenido del encabezado")
    footer_content = models.TextField(blank=True, null=True, help_text="Contenido del pie de página")
    custom_css = models.TextField(blank=True, null=True, help_text="CSS personalizado")
    is_active = models.BooleanField(default=True, help_text="Plantilla activa")
    
    class Meta:
        unique_together = ['company', 'template_name', 'template_type']
        verbose_name = "Plantilla de Documento"
        verbose_name_plural = "Plantillas de Documentos"
    
    def __str__(self):
        return f"{self.template_name} ({self.get_template_type_display()})"
    
    def get_available_variables(self):
        """Retorna las variables disponibles según el tipo de plantilla"""
        base_variables = [
            '{{company.name}}', '{{company.address}}', '{{company.phone}}',
            '{{company.email}}', '{{company.website}}', '{{company.tax_id}}',
            '{{current_date}}', '{{current_time}}'
        ]
        
        type_variables = {
            'invoice': [
                '{{invoice.number}}', '{{invoice.date}}', '{{invoice.total}}',
                '{{customer.name}}', '{{customer.address}}', '{{customer.email}}'
            ],
            'contract': [
                '{{contract.number}}', '{{contract.start_date}}', '{{contract.end_date}}',
                '{{property.address}}', '{{customer.name}}', '{{agent.name}}'
            ],
            'receipt': [
                '{{receipt.number}}', '{{receipt.date}}', '{{receipt.amount}}',
                '{{customer.name}}', '{{payment.method}}'
            ]
        }
        
        return base_variables + type_variables.get(self.template_type, [])


class NotificationSettings(BaseModel):
    """
    Modelo para configuraciones de notificaciones del sistema.
    
    Permite configurar diferentes tipos de notificaciones, sus plantillas
    de email y frecuencias de envío.
    """
    NOTIFICATION_TYPES = [
        ('payment_reminder', 'Recordatorio de Pago'),
        ('contract_expiry', 'Vencimiento de Contrato'),
        ('maintenance_due', 'Mantenimiento Pendiente'),
        ('new_inquiry', 'Nueva Consulta'),
        ('document_ready', 'Documento Listo'),
        ('system_alert', 'Alerta del Sistema'),
    ]
    
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='notification_settings')
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES, help_text="Tipo de notificación")
    is_enabled = models.BooleanField(default=True, help_text="Notificación habilitada")
    email_template = models.TextField(blank=True, null=True, help_text="Plantilla de email")
    frequency_days = models.IntegerField(default=1, help_text="Frecuencia en días")
    
    class Meta:
        unique_together = ['company', 'notification_type']
        verbose_name = "Configuración de Notificación"
        verbose_name_plural = "Configuraciones de Notificaciones"
    
    def __str__(self):
        return f"{self.get_notification_type_display()} - {self.company.name}"
    
    def clean(self):
        """Validación personalizada"""
        if self.frequency_days < 1:
            raise ValidationError('La frecuencia debe ser al menos 1 día')
        
        if self.is_enabled and not self.email_template:
            raise ValidationError('Las notificaciones habilitadas requieren una plantilla de email')