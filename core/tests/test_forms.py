"""
Pruebas para los formularios de configuración de empresa.

Estas pruebas verifican la funcionalidad de los formularios especializados
para cada sección de configuración.
"""

import tempfile
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError
from PIL import Image
from io import BytesIO

from core.models import (
    Company, 
    CompanyConfiguration, 
    DocumentTemplate, 
    NotificationSettings, 
    SystemConfiguration
)
from core.forms import (
    CompanyBasicForm,
    ContactInfoForm,
    SystemConfigForm,
    DocumentTemplateForm,
    NotificationForm
)


class CompanyBasicFormTest(TestCase):
    """Pruebas para CompanyBasicForm"""
    
    def setUp(self):
        """Configuración inicial para las pruebas"""
        self.company = Company.objects.create(
            name="Empresa Test S.L.",
            address="Calle Test 123, Madrid",
            phone="+34 912 345 678",
            email="test@empresa.com",
            website="https://www.empresa-test.com",
            tax_id="B12345678"
        )
    
    def test_form_valid_data(self):
        """Prueba formulario con datos válidos"""
        form_data = {
            'name': 'Nueva Empresa S.L.',
            'address': 'Nueva Dirección 456, Barcelona',
            'phone': '+34 612 345 678',
            'email': 'nuevo@empresa.com',
            'website': 'https://www.nueva-empresa.com',
            'tax_id': 'A12345674'
        }
        
        form = CompanyBasicForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_form_required_name(self):
        """Prueba que el nombre es obligatorio"""
        form_data = {
            'address': 'Dirección Test',
            'phone': '+34 612 345 678',
            'email': 'test@empresa.com'
        }
        
        form = CompanyBasicForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)
    
    def test_clean_name_validation(self):
        """Prueba validación del nombre de empresa"""
        # Nombre muy corto
        form = CompanyBasicForm(data={'name': 'AB'})
        self.assertFalse(form.is_valid())
        self.assertIn('al menos 3 caracteres', str(form.errors['name']))
        
        # Nombre con caracteres inválidos
        form = CompanyBasicForm(data={'name': 'Empresa@#$%'})
        self.assertFalse(form.is_valid())
        self.assertIn('caracteres no válidos', str(form.errors['name']))
        
        # Nombre válido
        form = CompanyBasicForm(data={'name': 'Empresa Válida S.L.'})
        self.assertTrue(form.is_valid())
    
    def test_clean_email_validation(self):
        """Prueba validación del email"""
        # Email inválido
        form_data = {'name': 'Test', 'email': 'email-invalido'}
        form = CompanyBasicForm(data=form_data)
        self.assertFalse(form.is_valid())
        
        # Email temporal (no permitido)
        form_data = {'name': 'Test', 'email': 'test@10minutemail.com'}
        form = CompanyBasicForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('temporales', str(form.errors['email']))
        
        # Email válido
        form_data = {'name': 'Test', 'email': 'valido@empresa.com'}
        form = CompanyBasicForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_clean_phone_validation(self):
        """Prueba validación del teléfono"""
        # Teléfono sin prefijo (se debe agregar automáticamente)
        form_data = {'name': 'Test', 'phone': '612345678'}
        form = CompanyBasicForm(data=form_data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['phone'], '+34612345678')
        
        # Teléfono con formato inválido
        form_data = {'name': 'Test', 'phone': '123456'}
        form = CompanyBasicForm(data=form_data)
        self.assertFalse(form.is_valid())
    
    def test_clean_website_validation(self):
        """Prueba validación del sitio web"""
        # URL sin protocolo (se debe agregar automáticamente)
        form_data = {'name': 'Test', 'website': 'www.empresa.com'}
        form = CompanyBasicForm(data=form_data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['website'], 'https://www.empresa.com')
        
        # URL inválida
        form_data = {'name': 'Test', 'website': 'no-es-url'}
        form = CompanyBasicForm(data=form_data)
        self.assertFalse(form.is_valid())
    
    def test_clean_tax_id_validation(self):
        """Prueba validación del NIF/CIF"""
        # NIF válido
        form_data = {'name': 'Test', 'tax_id': '12345678Z'}
        form = CompanyBasicForm(data=form_data)
        self.assertTrue(form.is_valid())
        
        # CIF válido
        form_data = {'name': 'Test', 'tax_id': 'A12345674'}
        form = CompanyBasicForm(data=form_data)
        self.assertTrue(form.is_valid())
        
        # Formato inválido
        form_data = {'name': 'Test', 'tax_id': '123ABC'}
        form = CompanyBasicForm(data=form_data)
        self.assertFalse(form.is_valid())
    
    def _create_test_image(self, format='PNG', size=(100, 100)):
        """Crea una imagen de prueba"""
        image = Image.new('RGB', size, color='red')
        temp_file = BytesIO()
        image.save(temp_file, format=format)
        temp_file.seek(0)
        return temp_file
    
    def test_clean_logo_validation(self):
        """Prueba validación del logotipo"""
        # Imagen válida
        image_file = self._create_test_image()
        uploaded_file = SimpleUploadedFile(
            "test.png", 
            image_file.getvalue(), 
            content_type="image/png"
        )
        
        form_data = {'name': 'Test'}
        form = CompanyBasicForm(data=form_data, files={'logo': uploaded_file})
        self.assertTrue(form.is_valid())


class ContactInfoFormTest(TestCase):
    """Pruebas para ContactInfoForm"""
    
    def setUp(self):
        """Configuración inicial para las pruebas"""
        self.company = Company.objects.create(
            name="Empresa Test S.L.",
            email="test@empresa.com",
            phone="+34 912 345 678"
        )
    
    def test_form_valid_data(self):
        """Prueba formulario con datos válidos"""
        form_data = {
            'street_address': 'Calle Nueva 123',
            'city': 'Madrid',
            'state_province': 'Madrid',
            'postal_code': '28001',
            'country': 'España',
            'primary_email': 'contacto@empresa.com',
            'primary_phone': '+34 912 345 678'
        }
        
        form = ContactInfoForm(data=form_data, company=self.company)
        self.assertTrue(form.is_valid())
    
    def test_form_requires_contact_method(self):
        """Prueba que se requiere al menos un método de contacto"""
        form_data = {
            'street_address': 'Calle Test 123',
            'city': 'Madrid'
        }
        
        form = ContactInfoForm(data=form_data, company=self.company)
        self.assertFalse(form.is_valid())
        self.assertIn('al menos un método de contacto', str(form.errors['__all__']))
    
    def test_phone_validation(self):
        """Prueba validación de números de teléfono"""
        form_data = {
            'primary_email': 'test@empresa.com',
            'primary_phone': '612345678'  # Sin prefijo
        }
        
        form = ContactInfoForm(data=form_data, company=self.company)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['primary_phone'], '+34612345678')
    
    def test_mobile_phone_validation(self):
        """Prueba validación específica para móviles"""
        form_data = {
            'primary_email': 'test@empresa.com',
            'mobile_phone': '912345678'  # No es móvil (empieza por 9 fijo)
        }
        
        form = ContactInfoForm(data=form_data, company=self.company)
        self.assertFalse(form.is_valid())
        self.assertIn('debe empezar por 6, 7, 8 o 9', str(form.errors['mobile_phone']))
    
    def test_postal_code_validation(self):
        """Prueba validación del código postal"""
        form_data = {
            'primary_email': 'test@empresa.com',
            'postal_code': '123',  # Muy corto
            'country': 'España'
        }
        
        form = ContactInfoForm(data=form_data, company=self.company)
        self.assertFalse(form.is_valid())
        self.assertIn('5 dígitos', str(form.errors['postal_code']))
    
    def test_save_method(self):
        """Prueba el método save del formulario"""
        form_data = {
            'street_address': 'Nueva Dirección 456',
            'city': 'Barcelona',
            'postal_code': '08001',
            'primary_email': 'nuevo@empresa.com',
            'secondary_phone': '+34 612 345 678'
        }
        
        form = ContactInfoForm(data=form_data, company=self.company)
        self.assertTrue(form.is_valid())
        
        updated_company = form.save(self.company)
        
        # Verificar que se actualizaron los datos básicos
        self.assertEqual(updated_company.email, 'nuevo@empresa.com')
        self.assertIn('Nueva Dirección 456', updated_company.address)
        
        # Verificar que se guardaron las configuraciones adicionales
        config = CompanyConfiguration.objects.get(
            company=self.company,
            config_key='secondary_phone'
        )
        self.assertEqual(config.config_value, '+34612345678')


class SystemConfigFormTest(TestCase):
    """Pruebas para SystemConfigForm"""
    
    def setUp(self):
        """Configuración inicial para las pruebas"""
        self.company = Company.objects.create(name="Empresa Test S.L.")
        self.sys_config = SystemConfiguration.objects.create(
            company=self.company,
            currency='EUR',
            timezone='Europe/Madrid',
            date_format='DD/MM/YYYY',
            language='es'
        )
    
    def test_form_valid_data(self):
        """Prueba formulario con datos válidos"""
        form_data = {
            'currency': 'USD',
            'timezone': 'America/New_York',
            'date_format': 'MM/DD/YYYY',
            'language': 'en',
            'decimal_places': 2,
            'tax_rate': 21.00,
            'invoice_prefix': 'INV',
            'contract_prefix': 'CON',
            'receipt_prefix': 'REC'
        }
        
        form = SystemConfigForm(data=form_data, instance=self.sys_config, company=self.company)
        self.assertTrue(form.is_valid())
    
    def test_tax_rate_validation(self):
        """Prueba validación del tipo de IVA"""
        # Tipo de IVA negativo
        form_data = {
            'currency': 'EUR',
            'timezone': 'Europe/Madrid',
            'date_format': 'DD/MM/YYYY',
            'language': 'es',
            'tax_rate': -5.0
        }
        
        form = SystemConfigForm(data=form_data, instance=self.sys_config, company=self.company)
        self.assertFalse(form.is_valid())
        self.assertIn('entre 0% y 100%', str(form.errors['tax_rate']))
    
    def test_prefix_validation(self):
        """Prueba validación de prefijos"""
        # Prefijo con caracteres inválidos
        form_data = {
            'currency': 'EUR',
            'timezone': 'Europe/Madrid',
            'date_format': 'DD/MM/YYYY',
            'language': 'es',
            'invoice_prefix': 'INV@#'
        }
        
        form = SystemConfigForm(data=form_data, instance=self.sys_config, company=self.company)
        self.assertFalse(form.is_valid())
        self.assertIn('solo puede contener letras y números', str(form.errors['invoice_prefix']))
    
    def test_unique_prefixes_validation(self):
        """Prueba que los prefijos sean únicos"""
        form_data = {
            'currency': 'EUR',
            'timezone': 'Europe/Madrid',
            'date_format': 'DD/MM/YYYY',
            'language': 'es',
            'invoice_prefix': 'DOC',
            'contract_prefix': 'DOC',  # Duplicado
            'receipt_prefix': 'REC'
        }
        
        form = SystemConfigForm(data=form_data, instance=self.sys_config, company=self.company)
        self.assertFalse(form.is_valid())
        self.assertIn('únicos', str(form.errors['__all__']))


class DocumentTemplateFormTest(TestCase):
    """Pruebas para DocumentTemplateForm"""
    
    def setUp(self):
        """Configuración inicial para las pruebas"""
        self.company = Company.objects.create(name="Empresa Test S.L.")
    
    def test_form_valid_data(self):
        """Prueba formulario con datos válidos"""
        form_data = {
            'template_name': 'Plantilla de Factura',
            'template_type': 'invoice',
            'header_content': '<h1>{{company.name}}</h1>',
            'footer_content': '<p>Gracias por su confianza</p>',
            'custom_css': 'h1 { color: blue; }',
            'is_active': True
        }
        
        form = DocumentTemplateForm(data=form_data, company=self.company)
        self.assertTrue(form.is_valid())
    
    def test_template_name_validation(self):
        """Prueba validación del nombre de plantilla"""
        # Nombre muy corto
        form_data = {
            'template_name': 'AB',
            'template_type': 'invoice'
        }
        
        form = DocumentTemplateForm(data=form_data, company=self.company)
        self.assertFalse(form.is_valid())
        self.assertIn('al menos 3 caracteres', str(form.errors['template_name']))
    
    def test_template_content_validation(self):
        """Prueba validación del contenido de plantillas"""
        # Sintaxis inválida en header
        form_data = {
            'template_name': 'Test Template',
            'template_type': 'invoice',
            'header_content': '<h1>{{company.name}</h1><p>{{unclosed_tag'
        }
        
        form = DocumentTemplateForm(data=form_data, company=self.company)
        self.assertFalse(form.is_valid())
        self.assertIn('Error de sintaxis', str(form.errors['header_content']))
    
    def test_css_validation(self):
        """Prueba validación del CSS personalizado"""
        # CSS con contenido peligroso
        form_data = {
            'template_name': 'Test Template',
            'template_type': 'invoice',
            'header_content': '<h1>Test</h1>',
            'custom_css': 'body { background: url(javascript:alert("xss")); }'
        }
        
        form = DocumentTemplateForm(data=form_data, company=self.company)
        self.assertFalse(form.is_valid())
        self.assertIn('potencialmente peligroso', str(form.errors['custom_css']))
    
    def test_unique_template_name_validation(self):
        """Prueba validación de unicidad del nombre de plantilla"""
        # Crear plantilla existente
        DocumentTemplate.objects.create(
            company=self.company,
            template_name='Plantilla Existente',
            template_type='invoice',
            is_active=True
        )
        
        # Intentar crear otra con el mismo nombre y tipo
        form_data = {
            'template_name': 'Plantilla Existente',
            'template_type': 'invoice',
            'header_content': '<h1>Test</h1>'
        }
        
        form = DocumentTemplateForm(data=form_data, company=self.company)
        self.assertFalse(form.is_valid())
        self.assertIn('Ya existe una plantilla', str(form.errors['template_name']))
    
    def test_requires_content_validation(self):
        """Prueba que se requiere al menos header o footer"""
        form_data = {
            'template_name': 'Test Template',
            'template_type': 'invoice',
            'header_content': '',
            'footer_content': ''
        }
        
        form = DocumentTemplateForm(data=form_data, company=self.company)
        self.assertFalse(form.is_valid())
        self.assertIn('al menos contenido', str(form.errors['__all__']))


class NotificationFormTest(TestCase):
    """Pruebas para NotificationForm"""
    
    def setUp(self):
        """Configuración inicial para las pruebas"""
        self.company = Company.objects.create(name="Empresa Test S.L.")
    
    def test_form_valid_data(self):
        """Prueba formulario con datos válidos"""
        form_data = {
            'notification_type': 'payment_reminder',
            'is_enabled': True,
            'email_template': '<p>Recordatorio: {{customer.name}}</p>',
            'frequency_days': 7,
            'send_to_tenant': True,
            'send_to_admin': True,
            'email_subject': 'Recordatorio de pago'
        }
        
        form = NotificationForm(data=form_data, company=self.company)
        self.assertTrue(form.is_valid())
    
    def test_unique_notification_type_validation(self):
        """Prueba validación de unicidad del tipo de notificación"""
        # Crear notificación existente
        NotificationSettings.objects.create(
            company=self.company,
            notification_type='payment_reminder',
            is_enabled=True
        )
        
        # Intentar crear otra del mismo tipo
        form_data = {
            'notification_type': 'payment_reminder',
            'is_enabled': True,
            'email_template': '<p>Test</p>',
            'frequency_days': 7
        }
        
        form = NotificationForm(data=form_data, company=self.company)
        self.assertFalse(form.is_valid())
        self.assertIn('Ya existe una configuración', str(form.errors['notification_type']))
    
    def test_email_template_validation(self):
        """Prueba validación de la plantilla de email"""
        form_data = {
            'notification_type': 'payment_reminder',
            'is_enabled': True,
            'email_template': '<p>{{unclosed_tag</p>',
            'frequency_days': 7
        }
        
        form = NotificationForm(data=form_data, company=self.company)
        self.assertFalse(form.is_valid())
        self.assertIn('Error de sintaxis', str(form.errors['email_template']))
    
    def test_sms_validation(self):
        """Prueba validación de SMS"""
        # SMS habilitado sin plantilla
        form_data = {
            'notification_type': 'payment_reminder',
            'is_enabled': True,
            'email_template': '<p>Test</p>',
            'frequency_days': 7,
            'sms_enabled': True,
            'sms_template': ''
        }
        
        form = NotificationForm(data=form_data, company=self.company)
        self.assertFalse(form.is_valid())
        self.assertIn('plantilla SMS', str(form.errors['__all__']))
        
        # SMS demasiado largo
        form_data['sms_template'] = 'A' * 161  # Más de 160 caracteres
        form = NotificationForm(data=form_data, company=self.company)
        self.assertFalse(form.is_valid())
        self.assertIn('160 caracteres', str(form.errors['sms_template']))
    
    def test_requires_recipient_validation(self):
        """Prueba que se requiere al menos un destinatario"""
        form_data = {
            'notification_type': 'payment_reminder',
            'is_enabled': True,
            'email_template': '<p>Test</p>',
            'frequency_days': 7,
            'send_to_tenant': False,
            'send_to_owner': False,
            'send_to_admin': False
        }
        
        form = NotificationForm(data=form_data, company=self.company)
        self.assertFalse(form.is_valid())
        self.assertIn('al menos un destinatario', str(form.errors['__all__']))