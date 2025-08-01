"""
Pruebas para el servicio DocumentTemplateService.

Estas pruebas verifican la funcionalidad del servicio de gestión de plantillas
de documentos, incluyendo renderizado, validación y previsualización.
"""

from django.test import TestCase
from django.template import TemplateSyntaxError
from django.core.exceptions import ValidationError
from unittest.mock import patch

from core.models import Company, DocumentTemplate
from core.services.document_template_service import DocumentTemplateService


class DocumentTemplateServiceTest(TestCase):
    """Pruebas para el servicio DocumentTemplateService"""
    
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
        self.service = DocumentTemplateService(self.company)
        
        # Crear plantilla de prueba
        self.test_template = DocumentTemplate.objects.create(
            company=self.company,
            template_name="test_invoice",
            template_type="invoice",
            header_content="<h1>{{company.name}}</h1><p>{{company.address}}</p>",
            footer_content="<p>Gracias por su confianza</p>",
            custom_css="h1 { color: blue; }",
            is_active=True
        )
    
    def test_render_template_success(self):
        """Prueba renderizado exitoso de plantilla"""
        context = {
            'body_content': '<p>Contenido del documento</p>',
            'invoice': {
                'number': 'INV-001',
                'total': '1000.00 €'
            }
        }
        
        result = self.service.render_template('test_invoice', context, 'invoice')
        
        self.assertIn('Empresa Test S.L.', result)
        self.assertIn('Calle Test 123, Madrid', result)
        self.assertIn('Contenido del documento', result)
        self.assertIn('Gracias por su confianza', result)
        self.assertIn('color: blue', result)
    
    def test_render_template_not_found(self):
        """Prueba error cuando plantilla no existe"""
        context = {'body_content': 'Test'}
        
        with self.assertRaises(DocumentTemplate.DoesNotExist):
            self.service.render_template('nonexistent', context)
    
    def test_validate_template_syntax_valid(self):
        """Prueba validación de sintaxis correcta"""
        valid_template = "<h1>{{company.name}}</h1><p>{{current_date}}</p>"
        
        is_valid, error_msg = self.service.validate_template_syntax(valid_template)
        
        self.assertTrue(is_valid)
        self.assertIsNone(error_msg)
    
    def test_validate_template_syntax_invalid(self):
        """Prueba validación de sintaxis incorrecta"""
        invalid_template = "<h1>{{company.name}</h1><p>{{unclosed_tag</p>"
        
        is_valid, error_msg = self.service.validate_template_syntax(invalid_template)
        
        self.assertFalse(is_valid)
        self.assertIsNotNone(error_msg)
        self.assertIn("Syntax error", error_msg)
    
    def test_validate_template_syntax_empty(self):
        """Prueba validación de plantilla vacía"""
        is_valid, error_msg = self.service.validate_template_syntax("")
        
        self.assertTrue(is_valid)
        self.assertIsNone(error_msg)
    
    def test_get_available_variables_base(self):
        """Prueba obtención de variables base"""
        variables = self.service.get_available_variables('unknown_type')
        
        self.assertIn('{{company.name}}', variables)
        self.assertIn('{{company.address}}', variables)
        self.assertIn('{{current_date}}', variables)
        self.assertEqual(len(variables), len(self.service.BASE_VARIABLES))
    
    def test_get_available_variables_invoice(self):
        """Prueba obtención de variables para facturas"""
        variables = self.service.get_available_variables('invoice')
        
        self.assertIn('{{company.name}}', variables)
        self.assertIn('{{invoice.number}}', variables)
        self.assertIn('{{customer.name}}', variables)
        self.assertIn('{{items}}', variables)
        
        expected_count = len(self.service.BASE_VARIABLES) + len(self.service.TEMPLATE_VARIABLES['invoice'])
        self.assertEqual(len(variables), expected_count)
    
    def test_preview_template_success(self):
        """Prueba generación exitosa de preview"""
        template_content = "<h1>{{company.name}}</h1><p>Factura: {{invoice.number}}</p>"
        
        result = self.service.preview_template(template_content, 'invoice')
        
        self.assertIn('Empresa Test S.L.', result)
        self.assertIn('INV-2024-001', result)
    
    def test_preview_template_with_custom_context(self):
        """Prueba preview con contexto personalizado"""
        template_content = "<h1>{{company.name}}</h1><p>{{custom_field}}</p>"
        custom_context = {'custom_field': 'Valor personalizado'}
        
        result = self.service.preview_template(template_content, 'invoice', custom_context)
        
        self.assertIn('Empresa Test S.L.', result)
        self.assertIn('Valor personalizado', result)
    
    def test_preview_template_syntax_error(self):
        """Prueba preview con error de sintaxis"""
        invalid_template = "<h1>{{company.name}</h1><p>{{unclosed"
        
        with self.assertRaises(TemplateSyntaxError):
            self.service.preview_template(invalid_template, 'invoice')
    
    def test_create_template_success(self):
        """Prueba creación exitosa de plantilla"""
        template = self.service.create_template(
            template_name="new_template",
            template_type="contract",
            header_content="<h1>{{company.name}}</h1>",
            footer_content="<p>Fin del documento</p>",
            custom_css="body { font-size: 12px; }"
        )
        
        self.assertEqual(template.template_name, "new_template")
        self.assertEqual(template.template_type, "contract")
        self.assertEqual(template.company, self.company)
        self.assertTrue(template.is_active)
    
    def test_create_template_invalid_syntax(self):
        """Prueba creación con sintaxis inválida"""
        with self.assertRaises(ValidationError):
            self.service.create_template(
                template_name="invalid_template",
                template_type="contract",
                header_content="<h1>{{company.name}</h1><p>{{unclosed"
            )
    
    def test_update_template_success(self):
        """Prueba actualización exitosa de plantilla"""
        updated_template = self.service.update_template(
            self.test_template.id,
            template_name="updated_invoice",
            header_content="<h1>NUEVA EMPRESA</h1>"
        )
        
        self.assertEqual(updated_template.template_name, "updated_invoice")
        self.assertIn("NUEVA EMPRESA", updated_template.header_content)
    
    def test_update_template_not_found(self):
        """Prueba actualización de plantilla inexistente"""
        with self.assertRaises(DocumentTemplate.DoesNotExist):
            self.service.update_template(99999, template_name="test")
    
    def test_update_template_invalid_syntax(self):
        """Prueba actualización con sintaxis inválida"""
        with self.assertRaises(ValidationError):
            self.service.update_template(
                self.test_template.id,
                header_content="<h1>{{invalid syntax"
            )
    
    def test_delete_template_success(self):
        """Prueba eliminación exitosa de plantilla"""
        result = self.service.delete_template(self.test_template.id)
        
        self.assertTrue(result)
        
        # Verificar que se marcó como inactiva
        self.test_template.refresh_from_db()
        self.assertFalse(self.test_template.is_active)
    
    def test_delete_template_not_found(self):
        """Prueba eliminación de plantilla inexistente"""
        result = self.service.delete_template(99999)
        
        self.assertFalse(result)
    
    def test_get_template_variables_usage(self):
        """Prueba extracción de variables utilizadas"""
        template_content = """
        <h1>{{company.name}}</h1>
        <p>{{invoice.number}} - {{invoice.date}}</p>
        <p>{{customer.name | upper}}</p>
        """
        
        variables = self.service.get_template_variables_usage(template_content)
        
        expected_variables = [
            '{{company.name}}',
            '{{customer.name}}',
            '{{invoice.date}}',
            '{{invoice.number}}'
        ]
        
        self.assertEqual(sorted(variables), sorted(expected_variables))
    
    def test_get_template_variables_usage_empty(self):
        """Prueba extracción de variables en plantilla vacía"""
        variables = self.service.get_template_variables_usage("")
        
        self.assertEqual(variables, [])
    
    def test_prepare_context(self):
        """Prueba preparación de contexto completo"""
        context = {'custom_field': 'test_value'}
        
        full_context = self.service._prepare_context(context, 'invoice')
        
        self.assertEqual(full_context['custom_field'], 'test_value')
        self.assertEqual(full_context['company']['name'], 'Empresa Test S.L.')
        self.assertEqual(full_context['company']['address'], 'Calle Test 123, Madrid')
        self.assertIn('current_date', full_context)
        self.assertIn('current_time', full_context)
        self.assertIn('current_datetime', full_context)
    
    def test_get_sample_context_invoice(self):
        """Prueba generación de contexto de ejemplo para facturas"""
        context = self.service._get_sample_context('invoice')
        
        self.assertIn('invoice', context)
        self.assertIn('customer', context)
        self.assertIn('items', context)
        self.assertEqual(context['invoice']['number'], 'INV-2024-001')
        self.assertEqual(context['customer']['name'], 'Cliente Ejemplo S.L.')
    
    def test_get_sample_context_contract(self):
        """Prueba generación de contexto de ejemplo para contratos"""
        context = self.service._get_sample_context('contract')
        
        self.assertIn('contract', context)
        self.assertIn('property', context)
        self.assertIn('customer', context)
        self.assertIn('agent', context)
        self.assertEqual(context['contract']['number'], 'CON-2024-001')
    
    def test_get_sample_context_receipt(self):
        """Prueba generación de contexto de ejemplo para recibos"""
        context = self.service._get_sample_context('receipt')
        
        self.assertIn('receipt', context)
        self.assertIn('customer', context)
        self.assertEqual(context['receipt']['number'], 'REC-2024-001')
    
    def test_combine_template_parts(self):
        """Prueba combinación de partes de plantilla"""
        header = "<h1>Encabezado</h1>"
        body = "<p>Contenido principal</p>"
        footer = "<p>Pie de página</p>"
        css = "h1 { color: red; }"
        
        result = self.service._combine_template_parts(header, body, footer, css)
        
        self.assertIn('<!DOCTYPE html>', result)
        self.assertIn('Encabezado', result)
        self.assertIn('Contenido principal', result)
        self.assertIn('Pie de página', result)
        self.assertIn('color: red', result)
        self.assertIn('class="header"', result)
        self.assertIn('class="content"', result)
        self.assertIn('class="footer"', result)
    
    def test_combine_template_parts_no_css(self):
        """Prueba combinación sin CSS personalizado"""
        header = "<h1>Test</h1>"
        body = "<p>Body</p>"
        footer = "<p>Footer</p>"
        
        result = self.service._combine_template_parts(header, body, footer)
        
        self.assertIn('<!DOCTYPE html>', result)
        self.assertIn('Test', result)
        self.assertIn('Body', result)
        self.assertIn('Footer', result)
        # No debe contener CSS personalizado
        self.assertNotIn('<style>', result.split('</style>')[1] if '</style>' in result else result)