"""
Servicio para gestión de plantillas de documentos.

Este servicio proporciona funcionalidades para renderizar plantillas
con variables dinámicas, validar sintaxis y generar previsualizaciones
de documentos personalizados.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple
from django.template import Template, Context, TemplateSyntaxError
from django.template.loader import get_template
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db import transaction

from core.models import Company, DocumentTemplate


logger = logging.getLogger(__name__)


class DocumentTemplateService:
    """
    Servicio para gestión de plantillas de documentos.
    
    Proporciona métodos para renderizar plantillas con variables dinámicas,
    validar sintaxis y generar previsualizaciones.
    """
    
    # Variables base disponibles en todas las plantillas
    BASE_VARIABLES = [
        '{{company.name}}', '{{company.address}}', '{{company.phone}}',
        '{{company.email}}', '{{company.website}}', '{{company.tax_id}}',
        '{{current_date}}', '{{current_time}}', '{{current_datetime}}'
    ]
    
    # Variables específicas por tipo de plantilla
    TEMPLATE_VARIABLES = {
        'invoice': [
            '{{invoice.number}}', '{{invoice.date}}', '{{invoice.due_date}}',
            '{{invoice.total}}', '{{invoice.subtotal}}', '{{invoice.tax_amount}}',
            '{{customer.name}}', '{{customer.address}}', '{{customer.email}}',
            '{{customer.phone}}', '{{customer.tax_id}}', '{{items}}'
        ],
        'contract': [
            '{{contract.number}}', '{{contract.start_date}}', '{{contract.end_date}}',
            '{{contract.monthly_rent}}', '{{contract.deposit}}', '{{contract.terms}}',
            '{{property.address}}', '{{property.type}}', '{{property.size}}',
            '{{customer.name}}', '{{customer.email}}', '{{agent.name}}'
        ],
        'receipt': [
            '{{receipt.number}}', '{{receipt.date}}', '{{receipt.amount}}',
            '{{receipt.concept}}', '{{receipt.payment_method}}',
            '{{customer.name}}', '{{customer.address}}'
        ],
        'report': [
            '{{report.title}}', '{{report.date}}', '{{report.period}}',
            '{{report.data}}', '{{report.summary}}', '{{report.author}}'
        ],
        'email': [
            '{{recipient.name}}', '{{recipient.email}}', '{{subject}}',
            '{{message.body}}', '{{sender.name}}', '{{sender.email}}'
        ],
        'letter': [
            '{{recipient.name}}', '{{recipient.address}}', '{{date}}',
            '{{subject}}', '{{body}}', '{{sender.name}}', '{{sender.title}}'
        ]
    }
    
    def __init__(self, company: Company):
        """
        Inicializa el servicio con una instancia de empresa.
        
        Args:
            company: Instancia del modelo Company
        """
        self.company = company
        self.logger = logging.getLogger(f"{__name__}.{company.id}")
    
    def render_template(self, template_name: str, context: Dict[str, Any], template_type: Optional[str] = None) -> str:
        """
        Renderiza una plantilla con el contexto proporcionado.
        
        Args:
            template_name: Nombre de la plantilla
            context: Diccionario con variables para el contexto
            template_type: Tipo de plantilla (opcional, para filtrar)
            
        Returns:
            Contenido renderizado de la plantilla
            
        Raises:
            DocumentTemplate.DoesNotExist: Si la plantilla no existe
            TemplateSyntaxError: Si hay errores de sintaxis en la plantilla
        """
        try:
            # Obtener la plantilla
            query = self.company.document_templates.filter(
                template_name=template_name,
                is_active=True
            )
            
            if template_type:
                query = query.filter(template_type=template_type)
            
            template_obj = query.first()
            
            if not template_obj:
                raise DocumentTemplate.DoesNotExist(
                    f"Template '{template_name}' not found for company {self.company.name}"
                )
            
            # Preparar contexto completo
            full_context = self._prepare_context(context, template_obj.template_type)
            
            # Renderizar header
            header_content = ""
            if template_obj.header_content:
                header_template = Template(template_obj.header_content)
                header_content = header_template.render(Context(full_context))
            
            # Renderizar footer
            footer_content = ""
            if template_obj.footer_content:
                footer_template = Template(template_obj.footer_content)
                footer_content = footer_template.render(Context(full_context))
            
            # Combinar contenido
            rendered_content = self._combine_template_parts(
                header_content, 
                context.get('body_content', ''), 
                footer_content,
                template_obj.custom_css
            )
            
            self.logger.info(f"Template '{template_name}' rendered successfully")
            return rendered_content
            
        except TemplateSyntaxError as e:
            self.logger.error(f"Template syntax error in '{template_name}': {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Error rendering template '{template_name}': {str(e)}")
            raise
    
    def validate_template_syntax(self, template_content: str) -> Tuple[bool, Optional[str]]:
        """
        Valida la sintaxis de una plantilla.
        
        Args:
            template_content: Contenido de la plantilla a validar
            
        Returns:
            Tupla (es_válida, mensaje_error)
        """
        if not template_content:
            return True, None
        
        try:
            # Intentar crear y renderizar la plantilla con contexto vacío
            template = Template(template_content)
            
            # Crear contexto de prueba con variables comunes
            test_context = self._get_test_context()
            template.render(Context(test_context))
            
            self.logger.debug("Template syntax validation passed")
            return True, None
            
        except TemplateSyntaxError as e:
            error_msg = f"Syntax error: {str(e)}"
            self.logger.warning(f"Template syntax validation failed: {error_msg}")
            return False, error_msg
        except Exception as e:
            error_msg = f"Validation error: {str(e)}"
            self.logger.warning(f"Template validation failed: {error_msg}")
            return False, error_msg
    
    def get_available_variables(self, template_type: str) -> List[str]:
        """
        Obtiene las variables disponibles para un tipo de plantilla.
        
        Args:
            template_type: Tipo de plantilla
            
        Returns:
            Lista de variables disponibles
        """
        variables = self.BASE_VARIABLES.copy()
        
        if template_type in self.TEMPLATE_VARIABLES:
            variables.extend(self.TEMPLATE_VARIABLES[template_type])
        
        self.logger.debug(f"Retrieved {len(variables)} variables for template type '{template_type}'")
        return sorted(variables)
    
    def preview_template(self, template_content: str, template_type: str, custom_context: Optional[Dict[str, Any]] = None) -> str:
        """
        Genera una previsualización de la plantilla con datos de ejemplo.
        
        Args:
            template_content: Contenido de la plantilla
            template_type: Tipo de plantilla
            custom_context: Contexto personalizado (opcional)
            
        Returns:
            Contenido renderizado con datos de ejemplo
            
        Raises:
            TemplateSyntaxError: Si hay errores de sintaxis
        """
        try:
            # Validar sintaxis primero
            is_valid, error_msg = self.validate_template_syntax(template_content)
            if not is_valid:
                raise TemplateSyntaxError(error_msg)
            
            # Preparar contexto de ejemplo
            sample_context = self._get_sample_context(template_type)
            
            # Agregar contexto personalizado si se proporciona
            if custom_context:
                sample_context.update(custom_context)
            
            # Renderizar plantilla
            template = Template(template_content)
            rendered_content = template.render(Context(sample_context))
            
            self.logger.info(f"Template preview generated for type '{template_type}'")
            return rendered_content
            
        except Exception as e:
            self.logger.error(f"Error generating template preview: {str(e)}")
            raise
    
    def create_template(self, template_name: str, template_type: str, 
                       header_content: Optional[str] = None, 
                       footer_content: Optional[str] = None,
                       custom_css: Optional[str] = None) -> DocumentTemplate:
        """
        Crea una nueva plantilla de documento.
        
        Args:
            template_name: Nombre de la plantilla
            template_type: Tipo de plantilla
            header_content: Contenido del encabezado
            footer_content: Contenido del pie de página
            custom_css: CSS personalizado
            
        Returns:
            Instancia de DocumentTemplate creada
            
        Raises:
            ValidationError: Si hay errores de validación
        """
        try:
            with transaction.atomic():
                # Validar sintaxis de header si se proporciona
                if header_content:
                    is_valid, error_msg = self.validate_template_syntax(header_content)
                    if not is_valid:
                        raise ValidationError(f"Header syntax error: {error_msg}")
                
                # Validar sintaxis de footer si se proporciona
                if footer_content:
                    is_valid, error_msg = self.validate_template_syntax(footer_content)
                    if not is_valid:
                        raise ValidationError(f"Footer syntax error: {error_msg}")
                
                # Crear plantilla
                template = DocumentTemplate.objects.create(
                    company=self.company,
                    template_name=template_name,
                    template_type=template_type,
                    header_content=header_content,
                    footer_content=footer_content,
                    custom_css=custom_css
                )
                
                self.logger.info(f"Template '{template_name}' created successfully")
                return template
                
        except Exception as e:
            self.logger.error(f"Error creating template '{template_name}': {str(e)}")
            raise
    
    def update_template(self, template_id: int, **kwargs) -> DocumentTemplate:
        """
        Actualiza una plantilla existente.
        
        Args:
            template_id: ID de la plantilla
            **kwargs: Campos a actualizar
            
        Returns:
            Instancia actualizada de DocumentTemplate
            
        Raises:
            DocumentTemplate.DoesNotExist: Si la plantilla no existe
            ValidationError: Si hay errores de validación
        """
        try:
            with transaction.atomic():
                template = self.company.document_templates.get(id=template_id)
                
                # Validar sintaxis si se actualizan contenidos
                if 'header_content' in kwargs and kwargs['header_content']:
                    is_valid, error_msg = self.validate_template_syntax(kwargs['header_content'])
                    if not is_valid:
                        raise ValidationError(f"Header syntax error: {error_msg}")
                
                if 'footer_content' in kwargs and kwargs['footer_content']:
                    is_valid, error_msg = self.validate_template_syntax(kwargs['footer_content'])
                    if not is_valid:
                        raise ValidationError(f"Footer syntax error: {error_msg}")
                
                # Actualizar campos
                for field, value in kwargs.items():
                    if hasattr(template, field):
                        setattr(template, field, value)
                
                template.save()
                
                self.logger.info(f"Template '{template.template_name}' updated successfully")
                return template
                
        except DocumentTemplate.DoesNotExist:
            self.logger.error(f"Template with ID {template_id} not found")
            raise
        except Exception as e:
            self.logger.error(f"Error updating template {template_id}: {str(e)}")
            raise
    
    def delete_template(self, template_id: int) -> bool:
        """
        Elimina una plantilla (marcándola como inactiva).
        
        Args:
            template_id: ID de la plantilla
            
        Returns:
            True si se eliminó correctamente
        """
        try:
            template = self.company.document_templates.get(id=template_id)
            template.is_active = False
            template.save()
            
            self.logger.info(f"Template '{template.template_name}' deactivated")
            return True
            
        except DocumentTemplate.DoesNotExist:
            self.logger.warning(f"Attempted to delete non-existent template {template_id}")
            return False
        except Exception as e:
            self.logger.error(f"Error deleting template {template_id}: {str(e)}")
            return False
    
    def get_template_variables_usage(self, template_content: str) -> List[str]:
        """
        Extrae las variables utilizadas en una plantilla.
        
        Args:
            template_content: Contenido de la plantilla
            
        Returns:
            Lista de variables encontradas en la plantilla
        """
        if not template_content:
            return []
        
        # Patrón para encontrar variables Django template
        pattern = r'\{\{\s*([^}]+)\s*\}\}'
        matches = re.findall(pattern, template_content)
        
        # Limpiar y formatear variables
        variables = []
        for match in matches:
            # Remover filtros y espacios
            var_name = match.split('|')[0].strip()
            formatted_var = f"{{{{{var_name}}}}}"
            if formatted_var not in variables:
                variables.append(formatted_var)
        
        self.logger.debug(f"Found {len(variables)} variables in template")
        return sorted(variables)
    
    def _prepare_context(self, context: Dict[str, Any], template_type: str) -> Dict[str, Any]:
        """
        Prepara el contexto completo para renderizar la plantilla.
        
        Args:
            context: Contexto proporcionado por el usuario
            template_type: Tipo de plantilla
            
        Returns:
            Contexto completo con variables base y específicas
        """
        full_context = context.copy()
        
        # Agregar información de la empresa
        full_context['company'] = {
            'name': self.company.name,
            'address': self.company.address or '',
            'phone': self.company.phone or '',
            'email': self.company.email or '',
            'website': self.company.website or '',
            'tax_id': self.company.tax_id or ''
        }
        
        # Agregar fechas actuales
        now = timezone.now()
        full_context['current_date'] = now.strftime('%d/%m/%Y')
        full_context['current_time'] = now.strftime('%H:%M:%S')
        full_context['current_datetime'] = now.strftime('%d/%m/%Y %H:%M:%S')
        
        return full_context
    
    def _get_test_context(self) -> Dict[str, Any]:
        """
        Genera un contexto de prueba para validación de sintaxis.
        
        Returns:
            Contexto con valores de prueba
        """
        return {
            'company': {
                'name': 'Test Company',
                'address': 'Test Address',
                'phone': '+34 123 456 789',
                'email': 'test@company.com',
                'website': 'https://test.com',
                'tax_id': 'B12345678'
            },
            'current_date': '01/01/2024',
            'current_time': '12:00:00',
            'current_datetime': '01/01/2024 12:00:00'
        }
    
    def _get_sample_context(self, template_type: str) -> Dict[str, Any]:
        """
        Genera un contexto de ejemplo para previsualización.
        
        Args:
            template_type: Tipo de plantilla
            
        Returns:
            Contexto con datos de ejemplo
        """
        base_context = self._prepare_context({}, template_type)
        
        # Agregar datos específicos según el tipo
        if template_type == 'invoice':
            base_context.update({
                'invoice': {
                    'number': 'INV-2024-001',
                    'date': '15/01/2024',
                    'due_date': '15/02/2024',
                    'total': '1,250.00 €',
                    'subtotal': '1,033.06 €',
                    'tax_amount': '216.94 €'
                },
                'customer': {
                    'name': 'Cliente Ejemplo S.L.',
                    'address': 'Calle Ejemplo 123, Madrid',
                    'email': 'cliente@ejemplo.com',
                    'phone': '+34 987 654 321',
                    'tax_id': 'B87654321'
                },
                'items': [
                    {'description': 'Servicio de consultoría', 'quantity': 10, 'price': '100.00 €'},
                    {'description': 'Mantenimiento mensual', 'quantity': 1, 'price': '33.06 €'}
                ]
            })
        
        elif template_type == 'contract':
            base_context.update({
                'contract': {
                    'number': 'CON-2024-001',
                    'start_date': '01/02/2024',
                    'end_date': '31/01/2025',
                    'monthly_rent': '800.00 €',
                    'deposit': '1,600.00 €',
                    'terms': 'Contrato de arrendamiento estándar'
                },
                'property': {
                    'address': 'Avenida Principal 456, Barcelona',
                    'type': 'Apartamento',
                    'size': '85 m²'
                },
                'customer': {
                    'name': 'Juan Pérez García',
                    'email': 'juan.perez@email.com'
                },
                'agent': {
                    'name': 'María López'
                }
            })
        
        elif template_type == 'receipt':
            base_context.update({
                'receipt': {
                    'number': 'REC-2024-001',
                    'date': '20/01/2024',
                    'amount': '800.00 €',
                    'concept': 'Pago de alquiler - Enero 2024',
                    'payment_method': 'Transferencia bancaria'
                },
                'customer': {
                    'name': 'Ana Martín Ruiz',
                    'address': 'Plaza Central 789, Valencia'
                }
            })
        
        return base_context
    
    def _combine_template_parts(self, header: str, body: str, footer: str, custom_css: Optional[str] = None) -> str:
        """
        Combina las partes de la plantilla en un documento HTML completo.
        
        Args:
            header: Contenido del encabezado
            body: Contenido del cuerpo
            footer: Contenido del pie de página
            custom_css: CSS personalizado
            
        Returns:
            Documento HTML completo
        """
        css_content = ""
        if custom_css:
            css_content = f"<style>{custom_css}</style>"
        
        html_template = f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Documento</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            line-height: 1.6;
        }}
        .header {{
            border-bottom: 2px solid #333;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        .content {{
            margin: 20px 0;
        }}
        .footer {{
            border-top: 1px solid #ccc;
            padding-top: 20px;
            margin-top: 30px;
            font-size: 0.9em;
            color: #666;
        }}
    </style>
    {css_content}
</head>
<body>
    <div class="header">
        {header}
    </div>
    <div class="content">
        {body}
    </div>
    <div class="footer">
        {footer}
    </div>
</body>
</html>
        """.strip()
        
        return html_template