from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from core.models import Company, CompanyConfiguration, SystemConfiguration, DocumentTemplate, NotificationSettings
import json


class CompanyConfigurationModelTest(TestCase):
    """Pruebas para el modelo CompanyConfiguration"""
    
    def setUp(self):
        self.company = Company.objects.create(
            name="Test Company",
            email="test@company.com"
        )
    
    def test_create_string_configuration(self):
        """Prueba creación de configuración tipo string"""
        config = CompanyConfiguration.objects.create(
            company=self.company,
            config_key="test_string",
            config_value="test value",
            config_type="string"
        )
        self.assertEqual(config.get_value(), "test value")
        self.assertEqual(str(config), "Test Company - test_string")
    
    def test_create_boolean_configuration(self):
        """Prueba creación de configuración tipo boolean"""
        config = CompanyConfiguration.objects.create(
            company=self.company,
            config_key="test_bool",
            config_value="true",
            config_type="boolean"
        )
        self.assertTrue(config.get_value())
        
        # Probar diferentes valores booleanos
        config.config_value = "false"
        self.assertFalse(config.get_value())
        
        config.config_value = "1"
        self.assertTrue(config.get_value())
        
        config.config_value = "0"
        self.assertFalse(config.get_value())
    
    def test_create_integer_configuration(self):
        """Prueba creación de configuración tipo integer"""
        config = CompanyConfiguration.objects.create(
            company=self.company,
            config_key="test_int",
            config_value="42",
            config_type="integer"
        )
        self.assertEqual(config.get_value(), 42)
        self.assertIsInstance(config.get_value(), int)
    
    def test_create_decimal_configuration(self):
        """Prueba creación de configuración tipo decimal"""
        config = CompanyConfiguration.objects.create(
            company=self.company,
            config_key="test_decimal",
            config_value="3.14",
            config_type="decimal"
        )
        self.assertEqual(config.get_value(), 3.14)
        self.assertIsInstance(config.get_value(), float)
    
    def test_create_json_configuration(self):
        """Prueba creación de configuración tipo JSON"""
        test_data = {"key": "value", "number": 123}
        config = CompanyConfiguration.objects.create(
            company=self.company,
            config_key="test_json",
            config_value=json.dumps(test_data),
            config_type="json"
        )
        self.assertEqual(config.get_value(), test_data)
    
    def test_set_value_method(self):
        """Prueba el método set_value"""
        config = CompanyConfiguration.objects.create(
            company=self.company,
            config_key="test_set",
            config_type="boolean"
        )
        
        config.set_value(True)
        self.assertEqual(config.config_value, "true")
        
        config.config_type = "json"
        test_data = {"test": "data"}
        config.set_value(test_data)
        self.assertEqual(config.config_value, json.dumps(test_data))
    
    def test_unique_constraint(self):
        """Prueba que no se puedan crear configuraciones duplicadas para la misma empresa"""
        CompanyConfiguration.objects.create(
            company=self.company,
            config_key="unique_key",
            config_value="value1"
        )
        
        with self.assertRaises(IntegrityError):
            CompanyConfiguration.objects.create(
                company=self.company,
                config_key="unique_key",
                config_value="value2"
            )
    
    def test_invalid_value_handling(self):
        """Prueba manejo de valores inválidos"""
        config = CompanyConfiguration.objects.create(
            company=self.company,
            config_key="test_invalid",
            config_value="invalid_number",
            config_type="integer"
        )
        # Debe retornar el valor original si no se puede convertir
        self.assertEqual(config.get_value(), "invalid_number")


class SystemConfigurationModelTest(TestCase):
    """Pruebas para el modelo SystemConfiguration"""
    
    def setUp(self):
        self.company = Company.objects.create(
            name="Test Company",
            email="test@company.com"
        )
    
    def test_create_system_configuration(self):
        """Prueba creación de configuración del sistema"""
        config = SystemConfiguration.objects.create(
            company=self.company,
            currency="USD",
            timezone="America/New_York",
            date_format="MM/DD/YYYY",
            language="en"
        )
        
        self.assertEqual(config.currency, "USD")
        self.assertEqual(config.timezone, "America/New_York")
        self.assertEqual(config.date_format, "MM/DD/YYYY")
        self.assertEqual(config.language, "en")
        self.assertEqual(str(config), "Configuración del Sistema - Test Company")
    
    def test_default_values(self):
        """Prueba valores por defecto"""
        config = SystemConfiguration.objects.create(company=self.company)
        
        self.assertEqual(config.currency, "EUR")
        self.assertEqual(config.timezone, "Europe/Madrid")
        self.assertEqual(config.date_format, "DD/MM/YYYY")
        self.assertEqual(config.language, "es")
        self.assertEqual(config.decimal_places, 2)
        self.assertEqual(config.tax_rate, 21.0)
        self.assertEqual(config.invoice_prefix, "INV")
        self.assertEqual(config.contract_prefix, "CON")
    
    def test_one_to_one_relationship(self):
        """Prueba que solo puede haber una configuración por empresa"""
        SystemConfiguration.objects.create(company=self.company)
        
        with self.assertRaises(IntegrityError):
            SystemConfiguration.objects.create(company=self.company)


class DocumentTemplateModelTest(TestCase):
    """Pruebas para el modelo DocumentTemplate"""
    
    def setUp(self):
        self.company = Company.objects.create(
            name="Test Company",
            email="test@company.com"
        )
    
    def test_create_document_template(self):
        """Prueba creación de plantilla de documento"""
        template = DocumentTemplate.objects.create(
            company=self.company,
            template_name="Test Invoice Template",
            template_type="invoice",
            header_content="<h1>{{company.name}}</h1>",
            footer_content="<p>Thank you for your business</p>"
        )
        
        self.assertEqual(template.template_name, "Test Invoice Template")
        self.assertEqual(template.template_type, "invoice")
        self.assertTrue(template.is_active)
        self.assertEqual(str(template), "Test Invoice Template (Factura)")
    
    def test_get_available_variables(self):
        """Prueba obtención de variables disponibles"""
        template = DocumentTemplate.objects.create(
            company=self.company,
            template_name="Invoice Template",
            template_type="invoice"
        )
        
        variables = template.get_available_variables()
        
        # Verificar variables base
        self.assertIn('{{company.name}}', variables)
        self.assertIn('{{current_date}}', variables)
        
        # Verificar variables específicas de factura
        self.assertIn('{{invoice.number}}', variables)
        self.assertIn('{{customer.name}}', variables)
    
    def test_unique_constraint(self):
        """Prueba restricción de unicidad"""
        DocumentTemplate.objects.create(
            company=self.company,
            template_name="Test Template",
            template_type="invoice"
        )
        
        with self.assertRaises(IntegrityError):
            DocumentTemplate.objects.create(
                company=self.company,
                template_name="Test Template",
                template_type="invoice"
            )


class NotificationSettingsModelTest(TestCase):
    """Pruebas para el modelo NotificationSettings"""
    
    def setUp(self):
        self.company = Company.objects.create(
            name="Test Company",
            email="test@company.com"
        )
    
    def test_create_notification_settings(self):
        """Prueba creación de configuración de notificación"""
        notification = NotificationSettings.objects.create(
            company=self.company,
            notification_type="payment_reminder",
            is_enabled=True,
            email_template="Payment reminder for {{customer.name}}",
            frequency_days=7
        )
        
        self.assertEqual(notification.notification_type, "payment_reminder")
        self.assertTrue(notification.is_enabled)
        self.assertEqual(notification.frequency_days, 7)
        self.assertEqual(str(notification), "Recordatorio de Pago - Test Company")
    
    def test_default_values(self):
        """Prueba valores por defecto"""
        notification = NotificationSettings.objects.create(
            company=self.company,
            notification_type="payment_reminder"
        )
        
        self.assertTrue(notification.is_enabled)
        self.assertEqual(notification.frequency_days, 1)
    
    def test_clean_validation(self):
        """Prueba validación personalizada"""
        # Frecuencia inválida
        notification = NotificationSettings(
            company=self.company,
            notification_type="payment_reminder",
            frequency_days=0
        )
        
        with self.assertRaises(ValidationError):
            notification.clean()
        
        # Notificación habilitada sin plantilla
        notification = NotificationSettings(
            company=self.company,
            notification_type="payment_reminder",
            is_enabled=True,
            email_template=None
        )
        
        with self.assertRaises(ValidationError):
            notification.clean()
    
    def test_unique_constraint(self):
        """Prueba restricción de unicidad"""
        NotificationSettings.objects.create(
            company=self.company,
            notification_type="payment_reminder"
        )
        
        with self.assertRaises(IntegrityError):
            NotificationSettings.objects.create(
                company=self.company,
                notification_type="payment_reminder"
            )