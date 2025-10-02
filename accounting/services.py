# -*- coding: utf-8 -*-
from django.conf import settings
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.utils import timezone
from django.core.exceptions import ValidationError
from weasyprint import HTML
import logging
from decimal import Decimal
import decimal
import time

logger = logging.getLogger(__name__)

def send_invoice_email(invoice):
    """
    Genera y envía una factura por correo electrónico.
    """
    if not invoice.customer.email:
        raise ValueError("El cliente no tiene una dirección de correo electrónico.")

    # Generar el PDF en memoria
    html_string = render_to_string('accounting/invoice_pdf.html', {'invoice': invoice})
    html = HTML(string=html_string)
    pdf_file = html.write_pdf()

    # Crear el correo electrónico
    subject = f"Factura Nº {invoice.number}"
    body = "Adjuntamos la factura correspondiente."
    email = EmailMessage(
        subject,
        body,
        settings.DEFAULT_FROM_EMAIL,
        [invoice.customer.email]
    )

    # Adjuntar el PDF
    email.attach(f'factura_{invoice.number}.pdf', pdf_file, 'application/pdf')

    # Enviar el correo
    email.send()


class OwnerReceiptValidationError(ValidationError):
    """Excepción específica para errores de validación de comprobantes."""
    pass


class OwnerReceiptEmailError(Exception):
    """Excepción específica para errores de envío de email."""
    pass


class OwnerReceiptPDFError(Exception):
    """Excepción específica para errores de generación de PDF."""
    pass


class OwnerReceiptService:
    """
    Servicio para gestionar la generación y envío de comprobantes al propietario.
    
    Proporciona funcionalidad para generar comprobantes PDF, enviarlos por email
    y gestionar el estado de los comprobantes según los requerimientos del sistema.
    """
    
    def __init__(self):
        """Inicializa el servicio de comprobantes de propietario."""
        self.logger = logging.getLogger('accounting.owner_receipts')
        self.max_retry_attempts = 3
        self.retry_delay = 5  # seconds
        
        # Configure specific logger for owner receipts if not already configured
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - [%(funcName)s:%(lineno)d] - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def can_generate_receipt(self, invoice):
        """
        Verifica si se puede generar un comprobante para la factura.
        
        Args:
            invoice: Instancia de Invoice para verificar
            
        Returns:
            tuple: (bool, str) - (puede_generar, mensaje_error)
        """
        try:
            from .validators import validate_owner_receipt_generation
            
            is_valid, error_message, warnings = validate_owner_receipt_generation(invoice)
            
            # Log warnings if any
            if warnings:
                for warning in warnings:
                    self.logger.warning(f"Validation warning for invoice {getattr(invoice, 'pk', 'unknown')}: {warning}")
            
            if is_valid:
                self._log_receipt_operation('validation', invoice=invoice, success=True, warnings=warnings)
                return True, ""
            else:
                self._log_receipt_operation('validation', invoice=invoice, success=False, error=error_message, warnings=warnings)
                return False, error_message
            
        except Exception as e:
            self.logger.error(f"Error inesperado verificando si se puede generar comprobante para factura {getattr(invoice, 'pk', 'unknown')}: {str(e)}", exc_info=True)
            self._log_receipt_operation('validation', invoice=invoice, success=False, error=str(e))
            return False, "Error interno al verificar la factura. Por favor, contacte al administrador del sistema."
    
    def get_receipt_data(self, invoice):
        """
        Obtiene todos los datos necesarios para el comprobante.
        
        Args:
            invoice: Instancia de Invoice
            
        Returns:
            dict: Diccionario con todos los datos del comprobante
            
        Raises:
            OwnerReceiptValidationError: Si faltan datos requeridos
        """
        try:
            # Verificar que se puede generar el comprobante
            can_generate, error_msg = self.can_generate_receipt(invoice)
            if not can_generate:
                raise OwnerReceiptValidationError(error_msg)
            
            contract = invoice.contract
            property_obj = contract.property
            owner = property_obj.owner
            
            # Validar y calcular montos con manejo de errores
            try:
                gross_amount = Decimal(str(invoice.total_amount))
                if gross_amount <= 0:
                    raise OwnerReceiptValidationError("El monto bruto debe ser mayor a cero")
                
                discount_percentage = Decimal(str(contract.owner_discount_percentage or 0))
                if discount_percentage < 0 or discount_percentage > 100:
                    raise OwnerReceiptValidationError(f"El porcentaje de descuento debe estar entre 0% y 100%. Valor actual: {discount_percentage}%")
                
                # Calcular y redondear a 2 decimales para evitar problemas de validación
                discount_amount = gross_amount * (discount_percentage / Decimal('100')) if discount_percentage else Decimal('0.00')
                discount_amount = discount_amount.quantize(Decimal('0.01'))
                net_amount = gross_amount - discount_amount
                net_amount = net_amount.quantize(Decimal('0.01'))
                
                if net_amount < 0:
                    raise OwnerReceiptValidationError("El monto neto no puede ser negativo. Verifique el porcentaje de descuento.")
                    
            except (ValueError, TypeError, decimal.InvalidOperation) as e:
                self.logger.error(f"Error calculando montos para factura {invoice.pk}: {str(e)}")
                raise OwnerReceiptValidationError("Error en los cálculos financieros. Verifique los montos de la factura y contrato.")
            
            # Obtener información del agente con validación
            try:
                agent_info = {
                    'name': 'N/A',
                    'email': '',
                    'phone': '',
                    'license_number': '',
                }
                
                if hasattr(contract, 'agent') and contract.agent:
                    agent = contract.agent
                    agent_info.update({
                        'name': agent.get_full_name() if hasattr(agent, 'get_full_name') else str(agent),
                        'email': getattr(agent, 'email', ''),
                        'phone': getattr(agent, 'phone', ''),
                        'license_number': getattr(agent, 'license_number', ''),
                    })
            except Exception as e:
                self.logger.warning(f"Error obteniendo información del agente para factura {invoice.pk}: {str(e)}")
                agent_info = {'name': 'N/A', 'email': '', 'phone': '', 'license_number': ''}
            
            # Obtener información de la propiedad con validación
            try:
                property_info = {
                    'title': getattr(property_obj, 'title', 'Sin título'),
                    'address': self._get_property_address(property_obj),
                    'property_type': self._get_property_type(property_obj),
                    'neighborhood': getattr(property_obj, 'neighborhood', ''),
                }
            except Exception as e:
                self.logger.error(f"Error obteniendo información de la propiedad para factura {invoice.pk}: {str(e)}")
                raise OwnerReceiptValidationError("Error obteniendo información de la propiedad")
            
            # Obtener información del propietario con validación
            try:
                owner_info = {
                    'name': self._get_person_name(owner),
                    'email': getattr(owner, 'email', ''),
                    'phone': getattr(owner, 'phone', ''),
                }
                
                if not owner_info['email']:
                    raise OwnerReceiptValidationError("El propietario no tiene email configurado")
                    
            except OwnerReceiptValidationError:
                raise
            except Exception as e:
                self.logger.error(f"Error obteniendo información del propietario para factura {invoice.pk}: {str(e)}")
                raise OwnerReceiptValidationError("Error obteniendo información del propietario")
            
            # Obtener información del inquilino (customer) con validación
            try:
                customer_info = {
                    'name': self._get_person_name(invoice.customer),
                    'email': getattr(invoice.customer, 'email', ''),
                    'phone': getattr(invoice.customer, 'phone', ''),
                }
            except Exception as e:
                self.logger.warning(f"Error obteniendo información del cliente para factura {invoice.pk}: {str(e)}")
                customer_info = {'name': 'N/A', 'email': '', 'phone': ''}
            
            # Información del contrato con validación
            try:
                contract_info = {
                    'start_date': getattr(contract, 'start_date', None),
                    'end_date': getattr(contract, 'end_date', None),
                    'amount': getattr(contract, 'amount', gross_amount),
                    'status': contract.get_status_display() if hasattr(contract, 'get_status_display') else 'N/A',
                }
            except Exception as e:
                self.logger.warning(f"Error obteniendo información del contrato para factura {invoice.pk}: {str(e)}")
                contract_info = {'start_date': None, 'end_date': None, 'amount': gross_amount, 'status': 'N/A'}
            
            # Información de la factura con validación
            try:
                invoice_info = {
                    'number': getattr(invoice, 'number', 'N/A'),
                    'date': getattr(invoice, 'date', timezone.now().date()),
                    'due_date': getattr(invoice, 'due_date', None),
                    'description': getattr(invoice, 'description', ''),
                    'status': invoice.get_status_display() if hasattr(invoice, 'get_status_display') else 'N/A',
                }
            except Exception as e:
                self.logger.warning(f"Error obteniendo información de la factura {invoice.pk}: {str(e)}")
                invoice_info = {'number': 'N/A', 'date': timezone.now().date(), 'due_date': None, 'description': '', 'status': 'N/A'}
            
            # Información financiera
            net_percentage = Decimal('100.00') - discount_percentage if discount_percentage else Decimal('100.00')
            financial_info = {
                'gross_amount': gross_amount,
                'discount_percentage': discount_percentage,
                'discount_amount': discount_amount,
                'net_amount': net_amount,
                'net_percentage': net_percentage,
            }
            
            receipt_data = {
                'invoice': invoice_info,
                'contract': contract_info,
                'property': property_info,
                'owner': owner_info,
                'customer': customer_info,
                'agent': agent_info,
                'financial': financial_info,
                'generated_at': timezone.now(),
            }
            
            self.logger.info(f"Datos del comprobante obtenidos exitosamente para factura {invoice.pk}")
            return receipt_data
            
        except OwnerReceiptValidationError:
            raise
        except Exception as e:
            self.logger.error(f"Error inesperado obteniendo datos del comprobante para factura {getattr(invoice, 'pk', 'unknown')}: {str(e)}", exc_info=True)
            raise OwnerReceiptValidationError("Error interno al obtener datos del comprobante. Por favor, contacte al administrador del sistema.")
    
    def _get_property_address(self, property_obj):
        """Obtiene la dirección de la propiedad de forma segura."""
        try:
            if hasattr(property_obj, 'full_address'):
                return property_obj.full_address
            elif hasattr(property_obj, 'street') and hasattr(property_obj, 'number'):
                street = getattr(property_obj, 'street', '')
                number = getattr(property_obj, 'number', '')
                return f"{street} {number}".strip()
            else:
                return getattr(property_obj, 'address', 'Dirección no disponible')
        except Exception:
            return 'Dirección no disponible'
    
    def _get_property_type(self, property_obj):
        """Obtiene el tipo de propiedad de forma segura."""
        try:
            if hasattr(property_obj, 'property_type') and property_obj.property_type:
                if hasattr(property_obj.property_type, 'name'):
                    return property_obj.property_type.name
                else:
                    return str(property_obj.property_type)
            return 'N/A'
        except Exception:
            return 'N/A'
    
    def _get_person_name(self, person):
        """Obtiene el nombre de una persona de forma segura."""
        try:
            if hasattr(person, 'get_full_name'):
                return person.get_full_name()
            elif hasattr(person, 'first_name') and hasattr(person, 'last_name'):
                first_name = getattr(person, 'first_name', '')
                last_name = getattr(person, 'last_name', '')
                return f"{first_name} {last_name}".strip()
            else:
                return str(person)
        except Exception:
            return 'N/A'
    
    def generate_receipt(self, invoice, user):
        """
        Genera un comprobante para una factura específica.
        
        Args:
            invoice: Instancia de Invoice
            user: Usuario que genera el comprobante (Agent)
            
        Returns:
            OwnerReceipt: Instancia del comprobante generado
            
        Raises:
            OwnerReceiptValidationError: Si no se puede generar el comprobante
        """
        from accounting.models_invoice import OwnerReceipt
        from django.db import transaction, IntegrityError
        
        try:
            # Verificar que se puede generar el comprobante
            can_generate, error_msg = self.can_generate_receipt(invoice)
            if not can_generate:
                raise OwnerReceiptValidationError(error_msg)
            
            # Validar usuario
            if not user:
                raise OwnerReceiptValidationError("Usuario requerido para generar el comprobante")
            
            # Obtener datos del comprobante
            receipt_data = self.get_receipt_data(invoice)
            
            # Usar transacción para asegurar consistencia
            with transaction.atomic():
                try:
                    # Crear el comprobante
                    receipt = OwnerReceipt(
                        invoice=invoice,
                        generated_by=user if hasattr(user, 'license_number') else None,
                        email_sent_to=receipt_data['owner']['email'],
                        gross_amount=receipt_data['financial']['gross_amount'],
                        discount_percentage=receipt_data['financial']['discount_percentage'],
                        discount_amount=receipt_data['financial']['discount_amount'],
                        net_amount=receipt_data['financial']['net_amount'],
                        status='generated'
                    )
                    
                    # Validar el modelo antes de guardar
                    receipt.full_clean()
                    
                    # Guardar el comprobante (esto generará automáticamente el número)
                    receipt.save()
                    
                    self._log_receipt_operation('generate', receipt=receipt, invoice=invoice, user=user, success=True)
                    
                    return receipt
                    
                except IntegrityError as e:
                    self.logger.error(f"Error de integridad al generar comprobante para factura {invoice.pk}: {str(e)}")
                    if 'receipt_number' in str(e):
                        raise OwnerReceiptValidationError("Error generando número único de comprobante. Por favor, intente nuevamente.")
                    else:
                        raise OwnerReceiptValidationError("Error de integridad en la base de datos. Por favor, contacte al administrador.")
                
                except ValidationError as e:
                    self.logger.error(f"Error de validación del modelo al generar comprobante para factura {invoice.pk}: {str(e)}")
                    raise OwnerReceiptValidationError(f"Error de validación: {str(e)}")
            
        except OwnerReceiptValidationError:
            raise
        except Exception as e:
            self.logger.error(f"Error inesperado generando comprobante para factura {getattr(invoice, 'pk', 'unknown')}: {str(e)}", exc_info=True)
            raise OwnerReceiptValidationError("Error interno al generar el comprobante. Por favor, contacte al administrador del sistema.")
    
    def generate_pdf(self, receipt):
        """
        Genera el PDF del comprobante.
        
        Args:
            receipt: Instancia de OwnerReceipt
            
        Returns:
            bytes: Contenido del PDF generado
            
        Raises:
            OwnerReceiptPDFError: Si no se puede generar el PDF
        """
        try:
            # Validar entrada
            if not receipt:
                raise OwnerReceiptPDFError("Comprobante requerido para generar PDF")
            
            if not hasattr(receipt, 'invoice') or not receipt.invoice:
                raise OwnerReceiptPDFError("El comprobante no tiene una factura asociada")
            
            # Obtener datos completos del comprobante
            try:
                receipt_data = self.get_receipt_data(receipt.invoice)
            except Exception as e:
                self.logger.error(f"Error obteniendo datos para PDF del comprobante {receipt.pk}: {str(e)}")
                raise OwnerReceiptPDFError("Error obteniendo datos del comprobante para el PDF")
            
            # Agregar información específica del comprobante
            receipt_data['receipt'] = {
                'number': getattr(receipt, 'receipt_number', 'N/A'),
                'generated_at': getattr(receipt, 'generated_at', timezone.now()),
                'generated_by': self._get_person_name(receipt.generated_by) if receipt.generated_by else 'Sistema',
                'status': receipt.get_status_display() if hasattr(receipt, 'get_status_display') else 'N/A',
            }
            
            # Obtener información de la empresa
            try:
                from core.models import Company
                company = Company.objects.first()
                receipt_data['company'] = company
            except Exception as e:
                self.logger.warning(f"Error obteniendo información de la empresa para PDF: {str(e)}")
                receipt_data['company'] = None
            
            # Renderizar el template HTML
            try:
                html_string = render_to_string('accounting/owner_receipt_pdf.html', receipt_data)
                if not html_string or len(html_string.strip()) == 0:
                    raise OwnerReceiptPDFError("El template HTML está vacío")
            except Exception as e:
                self.logger.error(f"Error renderizando template HTML para comprobante {receipt.pk}: {str(e)}")
                raise OwnerReceiptPDFError("Error renderizando el template del comprobante")
            
            # Generar PDF con WeasyPrint
            try:
                html = HTML(string=html_string)
                pdf_content = html.write_pdf()
                
                if not pdf_content or len(pdf_content) == 0:
                    raise OwnerReceiptPDFError("El PDF generado está vacío")
                
                # Validar que el PDF es válido (al menos tiene el header PDF)
                if not pdf_content.startswith(b'%PDF-'):
                    raise OwnerReceiptPDFError("El contenido generado no es un PDF válido")
                
            except Exception as e:
                self.logger.error(f"Error con WeasyPrint generando PDF para comprobante {receipt.pk}: {str(e)}")
                if "WeasyPrint" in str(e) or "CSS" in str(e) or "HTML" in str(e):
                    raise OwnerReceiptPDFError("Error en la generación del PDF. Verifique el template y los estilos CSS.")
                else:
                    raise OwnerReceiptPDFError(f"Error técnico generando PDF: {str(e)}")
            
            self._log_receipt_operation('pdf_generate', receipt=receipt, success=True, pdf_size=len(pdf_content))
            
            return pdf_content
            
        except OwnerReceiptPDFError:
            raise
        except Exception as e:
            self.logger.error(f"Error inesperado generando PDF para comprobante {getattr(receipt, 'pk', 'unknown')}: {str(e)}", exc_info=True)
            raise OwnerReceiptPDFError("Error interno al generar el PDF. Por favor, contacte al administrador del sistema.")
    
    def send_receipt_email(self, receipt, retry_count=0):
        """
        Envía el comprobante por email al propietario con mecanismo de reintentos.
        
        Args:
            receipt: Instancia de OwnerReceipt
            retry_count: Número de intento actual (para reintentos internos)
            
        Returns:
            bool: True si se envió correctamente
            
        Raises:
            OwnerReceiptEmailError: Si no se puede enviar el email después de todos los reintentos
        """
        try:
            # Validar entrada
            if not receipt:
                raise OwnerReceiptEmailError("Comprobante requerido para enviar email")
            
            # Verificar que el comprobante puede ser enviado
            if not receipt.can_resend() and receipt.status == 'sent':
                raise OwnerReceiptEmailError("El comprobante ya fue enviado exitosamente.")
            
            # Validar configuración de email del sistema
            config_valid, config_error = self._validate_email_configuration()
            if not config_valid:
                raise OwnerReceiptEmailError(f"Configuración de email del sistema inválida: {config_error}")
            
            # Validar email de destino
            if not receipt.email_sent_to:
                raise OwnerReceiptEmailError("Dirección de email de destino no configurada")
            
            from django.core.validators import validate_email
            try:
                validate_email(receipt.email_sent_to)
            except ValidationError:
                raise OwnerReceiptEmailError(f"Dirección de email inválida: {receipt.email_sent_to}")
            
            # Obtener datos del comprobante
            try:
                receipt_data = self.get_receipt_data(receipt.invoice)
            except Exception as e:
                self.logger.error(f"Error obteniendo datos para email del comprobante {receipt.pk}: {str(e)}")
                raise OwnerReceiptEmailError("Error obteniendo datos del comprobante para el email")
            
            # Generar PDF
            try:
                pdf_content = self.generate_pdf(receipt)
            except OwnerReceiptPDFError as e:
                self.logger.error(f"Error generando PDF para email del comprobante {receipt.pk}: {str(e)}")
                raise OwnerReceiptEmailError(f"Error generando PDF para adjuntar al email: {str(e)}")
            
            # Preparar datos para el template de email
            try:
                email_context = {
                    'owner_name': receipt_data['owner']['name'],
                    'property_address': receipt_data['property']['address'],
                    'period': self._format_period(receipt.invoice.date),
                    'net_amount': receipt.net_amount,
                    'receipt_number': receipt.receipt_number,
                    'company_name': getattr(settings, 'COMPANY_NAME', 'Inmobiliaria'),
                    'invoice_number': receipt.invoice.number,
                    'gross_amount': receipt.gross_amount,
                    'discount_amount': receipt.discount_amount,
                    'discount_percentage': receipt.discount_percentage,
                }
            except Exception as e:
                self.logger.error(f"Error preparando contexto de email para comprobante {receipt.pk}: {str(e)}")
                raise OwnerReceiptEmailError("Error preparando datos del email")
            
            # Renderizar el template de email
            try:
                email_body = render_to_string('emails/owner_receipt_email.html', email_context)
                if not email_body or len(email_body.strip()) == 0:
                    raise OwnerReceiptEmailError("El template de email está vacío")
            except Exception as e:
                self.logger.error(f"Error renderizando template de email para comprobante {receipt.pk}: {str(e)}")
                raise OwnerReceiptEmailError("Error renderizando el template del email")
            
            # Crear el email
            try:
                subject = f"Comprobante de Alquiler - {email_context['property_address']} - {email_context['period']}"
                
                email = EmailMessage(
                    subject=subject,
                    body=email_body,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[receipt.email_sent_to],
                )
                
                # Configurar email como HTML
                email.content_subtype = 'html'
                
                # Adjuntar PDF
                email.attach(
                    f'comprobante_{receipt.receipt_number}.pdf',
                    pdf_content,
                    'application/pdf'
                )
                
            except Exception as e:
                self.logger.error(f"Error creando mensaje de email para comprobante {receipt.pk}: {str(e)}")
                raise OwnerReceiptEmailError("Error creando el mensaje de email")
            
            # Enviar email con manejo de errores específicos
            try:
                email.send()
                
            except Exception as e:
                error_msg = str(e).lower()
                
                # Errores específicos de SMTP
                if 'smtp' in error_msg or 'connection' in error_msg:
                    if retry_count < self.max_retry_attempts:
                        self.logger.warning(f"Error SMTP enviando comprobante {receipt.pk}, reintentando en {self.retry_delay}s (intento {retry_count + 1}/{self.max_retry_attempts})")
                        time.sleep(self.retry_delay)
                        return self.send_receipt_email(receipt, retry_count + 1)
                    else:
                        raise OwnerReceiptEmailError("Error de conexión SMTP. Verifique la configuración del servidor de correo.")
                
                elif 'authentication' in error_msg or 'auth' in error_msg:
                    raise OwnerReceiptEmailError("Error de autenticación del servidor de correo. Verifique las credenciales.")
                
                elif 'recipient' in error_msg or 'address' in error_msg:
                    raise OwnerReceiptEmailError(f"Error con la dirección de destino: {receipt.email_sent_to}")
                
                elif 'size' in error_msg or 'large' in error_msg:
                    raise OwnerReceiptEmailError("El email es demasiado grande. El PDF podría ser muy pesado.")
                
                else:
                    if retry_count < self.max_retry_attempts:
                        self.logger.warning(f"Error genérico enviando comprobante {receipt.pk}, reintentando en {self.retry_delay}s (intento {retry_count + 1}/{self.max_retry_attempts}): {str(e)}")
                        time.sleep(self.retry_delay)
                        return self.send_receipt_email(receipt, retry_count + 1)
                    else:
                        raise OwnerReceiptEmailError(f"Error enviando email después de {self.max_retry_attempts} intentos: {str(e)}")
            
            # Marcar como enviado
            try:
                receipt.mark_as_sent(receipt.email_sent_to)
            except Exception as e:
                self.logger.error(f"Error marcando comprobante {receipt.pk} como enviado: {str(e)}")
                # No fallar aquí ya que el email se envió correctamente
            
            self._log_receipt_operation('email_send', receipt=receipt, success=True, 
                                      email_to=receipt.email_sent_to, retry_count=retry_count)
            
            return True
            
        except OwnerReceiptEmailError as e:
            # Marcar como fallido y registrar error
            self._log_receipt_operation('email_send', receipt=receipt, success=False, error=str(e), retry_count=retry_count)
            try:
                receipt.mark_as_failed(str(e))
            except Exception as mark_error:
                self.logger.error(f"Error marcando comprobante {receipt.pk} como fallido: {str(mark_error)}")
            raise
            
        except Exception as e:
            error_msg = f"Error inesperado enviando comprobante por email: {str(e)}"
            self.logger.error(f"Error inesperado enviando comprobante {getattr(receipt, 'pk', 'unknown')}: {error_msg}", exc_info=True)
            
            # Marcar como fallido
            try:
                receipt.mark_as_failed(error_msg)
            except Exception as mark_error:
                self.logger.error(f"Error marcando comprobante {receipt.pk} como fallido: {str(mark_error)}")
            
            raise OwnerReceiptEmailError("Error interno enviando email. Por favor, contacte al administrador del sistema.")
    
    def _format_period(self, date):
        """Formatea el período de la factura de forma segura."""
        try:
            if hasattr(date, 'strftime'):
                return date.strftime('%B %Y')
            else:
                return str(date)
        except Exception:
            return 'Período no disponible'
    
    def _log_receipt_operation(self, operation, receipt=None, invoice=None, user=None, success=True, error=None, **kwargs):
        """
        Registra operaciones de comprobantes con información estructurada.
        
        Args:
            operation (str): Tipo de operación (generate, send, resend, etc.)
            receipt: Instancia de OwnerReceipt (opcional)
            invoice: Instancia de Invoice (opcional)
            user: Usuario que realiza la operación (opcional)
            success (bool): Si la operación fue exitosa
            error (str): Mensaje de error si la operación falló
            **kwargs: Información adicional para el log
        """
        try:
            log_data = {
                'operation': operation,
                'success': success,
                'timestamp': timezone.now().isoformat(),
            }
            
            # Información del comprobante
            if receipt:
                log_data.update({
                    'receipt_id': getattr(receipt, 'pk', None),
                    'receipt_number': getattr(receipt, 'receipt_number', None),
                    'receipt_status': getattr(receipt, 'status', None),
                    'email_sent_to': getattr(receipt, 'email_sent_to', None),
                    'net_amount': float(getattr(receipt, 'net_amount', 0)),
                })
            
            # Información de la factura
            if invoice:
                log_data.update({
                    'invoice_id': getattr(invoice, 'pk', None),
                    'invoice_number': getattr(invoice, 'number', None),
                    'invoice_status': getattr(invoice, 'status', None),
                    'invoice_amount': float(getattr(invoice, 'total_amount', 0)),
                })
                
                # Información del contrato y propiedad si están disponibles
                if hasattr(invoice, 'contract') and invoice.contract:
                    contract = invoice.contract
                    log_data.update({
                        'contract_id': getattr(contract, 'pk', None),
                        'property_id': getattr(contract.property, 'pk', None) if hasattr(contract, 'property') and contract.property else None,
                        'property_title': getattr(contract.property, 'title', None) if hasattr(contract, 'property') and contract.property else None,
                    })
            
            # Información del usuario
            if user:
                log_data.update({
                    'user_id': getattr(user, 'pk', None),
                    'username': getattr(user, 'username', None),
                    'user_email': getattr(user, 'email', None),
                })
            
            # Información de error
            if error:
                log_data['error_message'] = str(error)
            
            # Información adicional
            log_data.update(kwargs)
            
            # Registrar en el log
            if success:
                self.logger.info(f"Owner receipt {operation} successful", extra=log_data)
            else:
                self.logger.error(f"Owner receipt {operation} failed", extra=log_data)
                
        except Exception as e:
            # Fallback logging si falla el logging estructurado
            self.logger.error(f"Error logging receipt operation {operation}: {str(e)}")
    
    def _validate_email_configuration(self):
        """
        Valida la configuración de email del sistema.
        
        Returns:
            tuple: (bool, str) - (es_válida, mensaje_error)
        """
        try:
            # Verificar configuración básica
            if not hasattr(settings, 'DEFAULT_FROM_EMAIL') or not settings.DEFAULT_FROM_EMAIL:
                return False, "DEFAULT_FROM_EMAIL no está configurado"
            
            if not hasattr(settings, 'EMAIL_HOST') or not settings.EMAIL_HOST:
                return False, "EMAIL_HOST no está configurado"
            
            # Verificar configuración de autenticación si es necesaria
            if hasattr(settings, 'EMAIL_HOST_USER') and settings.EMAIL_HOST_USER:
                if not hasattr(settings, 'EMAIL_HOST_PASSWORD') or not settings.EMAIL_HOST_PASSWORD:
                    return False, "EMAIL_HOST_PASSWORD requerido cuando EMAIL_HOST_USER está configurado"
            
            return True, ""
            
        except Exception as e:
            return False, f"Error verificando configuración de email: {str(e)}"
    
    def resend_receipt_email(self, receipt):
        """
        Reenvía un comprobante existente por email.
        
        Args:
            receipt: Instancia de OwnerReceipt
            
        Returns:
            bool: True si se reenvió correctamente
            
        Raises:
            OwnerReceiptEmailError: Si no se puede reenviar
        """
        try:
            # Validar entrada
            if not receipt:
                raise OwnerReceiptEmailError("Comprobante requerido para reenviar")
            
            # Verificar que se puede reenviar usando el validator
            from .validators import validate_receipt_resend
            can_resend, error_msg = validate_receipt_resend(receipt)
            if not can_resend:
                raise OwnerReceiptEmailError(error_msg)
            
            # Resetear estado para reenvío
            try:
                receipt.status = 'generated'
                receipt.error_message = ''
                receipt.sent_at = None
                receipt.save(update_fields=['status', 'error_message', 'sent_at'])
                
                self.logger.info(f"Estado del comprobante {receipt.receipt_number} reseteado para reenvío")
                
            except Exception as e:
                self.logger.error(f"Error reseteando estado del comprobante {receipt.pk} para reenvío: {str(e)}")
                raise OwnerReceiptEmailError("Error preparando el comprobante para reenvío")
            
            # Enviar email
            try:
                return self.send_receipt_email(receipt)
            except OwnerReceiptEmailError:
                raise
            except Exception as e:
                error_msg = f"Error en el reenvío del email: {str(e)}"
                self.logger.error(f"Error en reenvío de comprobante {receipt.pk}: {error_msg}")
                receipt.mark_as_failed(error_msg)
                raise OwnerReceiptEmailError(error_msg)
            
        except OwnerReceiptEmailError:
            raise
        except Exception as e:
            error_msg = f"Error inesperado al reenviar comprobante: {str(e)}"
            self.logger.error(f"Error inesperado reenviando comprobante {getattr(receipt, 'pk', 'unknown')}: {error_msg}", exc_info=True)
            
            try:
                receipt.mark_as_failed(error_msg)
            except Exception as mark_error:
                self.logger.error(f"Error marcando comprobante como fallido durante reenvío: {str(mark_error)}")
            
            raise OwnerReceiptEmailError("Error interno al reenviar el comprobante. Por favor, contacte al administrador del sistema.")
