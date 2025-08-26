# -*- coding: utf-8 -*-
"""
Validators for owner receipt functionality.

This module provides comprehensive validation utilities for owner receipts,
including business rule validation, data integrity checks, and error handling.
"""

from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from decimal import Decimal, InvalidOperation
import logging

logger = logging.getLogger('accounting.validators')


class OwnerReceiptValidator:
    """
    Comprehensive validator for owner receipt operations.
    
    Provides validation methods for all aspects of owner receipt generation,
    including invoice validation, contract validation, owner validation,
    and financial calculations.
    """
    
    def __init__(self):
        self.errors = []
        self.warnings = []
    
    def reset(self):
        """Reset error and warning lists."""
        self.errors = []
        self.warnings = []
    
    def validate_invoice(self, invoice):
        """
        Validate invoice for owner receipt generation.
        
        Args:
            invoice: Invoice instance to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        self.reset()
        
        try:
            # Basic existence check
            if not invoice:
                self.errors.append("La factura no existe")
                return False
            
            # Status validation
            valid_statuses = ['validated', 'sent', 'paid']
            if not hasattr(invoice, 'status') or invoice.status not in valid_statuses:
                current_status = getattr(invoice, 'status', 'unknown')
                status_display = invoice.get_status_display() if hasattr(invoice, 'get_status_display') else current_status
                self.errors.append(f"La factura debe estar validada, enviada o pagada. Estado actual: {status_display}")
            
            # Amount validation
            if not hasattr(invoice, 'total_amount') or invoice.total_amount is None:
                self.errors.append("La factura no tiene monto total definido")
            elif invoice.total_amount <= 0:
                self.errors.append(f"El monto de la factura debe ser mayor a cero. Monto actual: ${invoice.total_amount}")
            
            # Number validation
            if not hasattr(invoice, 'number') or not invoice.number:
                self.errors.append("La factura no tiene número asignado")
            
            # Date validation
            if not hasattr(invoice, 'date') or not invoice.date:
                self.errors.append("La factura no tiene fecha asignada")
            
            # Customer validation
            if not hasattr(invoice, 'customer') or not invoice.customer:
                self.errors.append("La factura no tiene cliente asignado")
            
            return len(self.errors) == 0
            
        except Exception as e:
            logger.error(f"Error validating invoice {getattr(invoice, 'pk', 'unknown')}: {str(e)}")
            self.errors.append("Error interno validando la factura")
            return False
    
    def validate_contract(self, contract):
        """
        Validate contract for owner receipt generation.
        
        Args:
            contract: Contract instance to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        if not contract:
            self.errors.append("La factura no tiene contrato asociado")
            return False
        
        try:
            # Property validation
            if not hasattr(contract, 'property') or not contract.property:
                self.errors.append("El contrato no tiene propiedad asociada")
                return False
            
            # Discount percentage validation
            if hasattr(contract, 'owner_discount_percentage') and contract.owner_discount_percentage is not None:
                try:
                    discount = Decimal(str(contract.owner_discount_percentage))
                    if discount < 0 or discount > 100:
                        self.errors.append(f"El porcentaje de descuento debe estar entre 0% y 100%. Valor actual: {discount}%")
                except (ValueError, InvalidOperation):
                    self.errors.append("El porcentaje de descuento tiene un formato inválido")
            
            # Contract amount validation
            if hasattr(contract, 'amount') and contract.amount is not None:
                try:
                    amount = Decimal(str(contract.amount))
                    if amount <= 0:
                        self.warnings.append(f"El monto del contrato es cero o negativo: ${amount}")
                except (ValueError, InvalidOperation):
                    self.warnings.append("El monto del contrato tiene un formato inválido")
            
            return len(self.errors) == 0
            
        except Exception as e:
            logger.error(f"Error validating contract {getattr(contract, 'pk', 'unknown')}: {str(e)}")
            self.errors.append("Error interno validando el contrato")
            return False
    
    def validate_property(self, property_obj):
        """
        Validate property for owner receipt generation.
        
        Args:
            property_obj: Property instance to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        if not property_obj:
            self.errors.append("El contrato no tiene propiedad asociada")
            return False
        
        try:
            # Owner validation
            if not hasattr(property_obj, 'owner') or not property_obj.owner:
                self.errors.append("La propiedad no tiene propietario asignado")
                return False
            
            # Basic property info validation
            if not hasattr(property_obj, 'title') or not property_obj.title:
                self.warnings.append("La propiedad no tiene título definido")
            
            # Address validation
            address = self._get_property_address(property_obj)
            if not address or address == 'Dirección no disponible':
                self.warnings.append("La propiedad no tiene dirección completa")
            
            return len(self.errors) == 0
            
        except Exception as e:
            logger.error(f"Error validating property {getattr(property_obj, 'pk', 'unknown')}: {str(e)}")
            self.errors.append("Error interno validando la propiedad")
            return False
    
    def validate_owner(self, owner):
        """
        Validate property owner for owner receipt generation.
        
        Args:
            owner: Owner instance to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        if not owner:
            self.errors.append("La propiedad no tiene propietario asignado")
            return False
        
        try:
            # Email validation
            if not hasattr(owner, 'email') or not owner.email:
                self.errors.append("El propietario no tiene dirección de email configurada")
                return False
            
            # Email format validation
            try:
                validate_email(owner.email)
            except ValidationError:
                self.errors.append(f"La dirección de email del propietario no es válida: {owner.email}")
                return False
            
            # Name validation
            name = self._get_person_name(owner)
            if not name or name == 'N/A':
                self.warnings.append("El propietario no tiene nombre completo configurado")
            
            return len(self.errors) == 0
            
        except Exception as e:
            logger.error(f"Error validating owner {getattr(owner, 'pk', 'unknown')}: {str(e)}")
            self.errors.append("Error interno validando el propietario")
            return False
    
    def validate_financial_calculations(self, invoice, contract):
        """
        Validate financial calculations for owner receipt.
        
        Args:
            invoice: Invoice instance
            contract: Contract instance
            
        Returns:
            tuple: (bool, dict) - (is_valid, calculations)
        """
        try:
            # Get amounts
            gross_amount = Decimal(str(invoice.total_amount))
            discount_percentage = Decimal(str(contract.owner_discount_percentage or 0))
            
            # Calculate amounts
            discount_amount = gross_amount * (discount_percentage / Decimal('100')) if discount_percentage else Decimal('0.00')
            net_amount = gross_amount - discount_amount
            
            # Validate calculations
            if gross_amount <= 0:
                self.errors.append("El monto bruto debe ser mayor a cero")
            
            if discount_percentage < 0 or discount_percentage > 100:
                self.errors.append(f"El porcentaje de descuento debe estar entre 0% y 100%. Valor: {discount_percentage}%")
            
            if discount_amount < 0:
                self.errors.append("El monto de descuento no puede ser negativo")
            
            if net_amount < 0:
                self.errors.append("El monto neto no puede ser negativo")
            
            if discount_amount > gross_amount:
                self.errors.append("El descuento no puede ser mayor al monto bruto")
            
            calculations = {
                'gross_amount': gross_amount,
                'discount_percentage': discount_percentage,
                'discount_amount': discount_amount,
                'net_amount': net_amount,
                'net_percentage': Decimal('100.00') - discount_percentage,
            }
            
            return len(self.errors) == 0, calculations
            
        except (ValueError, InvalidOperation, TypeError) as e:
            logger.error(f"Error in financial calculations: {str(e)}")
            self.errors.append("Error en los cálculos financieros")
            return False, {}
        except Exception as e:
            logger.error(f"Unexpected error in financial calculations: {str(e)}")
            self.errors.append("Error interno en los cálculos financieros")
            return False, {}
    
    def validate_existing_receipts(self, invoice):
        """
        Validate existing receipts for the invoice.
        
        Args:
            invoice: Invoice instance
            
        Returns:
            bool: True if no conflicts, False otherwise
        """
        try:
            from accounting.models_invoice import OwnerReceipt
            
            # Check for existing successful receipts
            existing_receipt = OwnerReceipt.objects.filter(
                invoice=invoice,
                status='sent'
            ).first()
            
            if existing_receipt:
                self.warnings.append(f"Ya existe un comprobante enviado exitosamente para esta factura: {existing_receipt.receipt_number}")
                return False
            
            # Check for pending receipts
            pending_receipts = OwnerReceipt.objects.filter(
                invoice=invoice,
                status='generated'
            ).count()
            
            if pending_receipts > 0:
                self.warnings.append(f"Existen {pending_receipts} comprobante(s) pendiente(s) de envío para esta factura")
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating existing receipts for invoice {getattr(invoice, 'pk', 'unknown')}: {str(e)}")
            self.warnings.append("Error verificando comprobantes existentes")
            return True  # Don't block generation for this error
    
    def validate_complete(self, invoice):
        """
        Perform complete validation for owner receipt generation.
        
        Args:
            invoice: Invoice instance to validate
            
        Returns:
            tuple: (bool, list, list) - (is_valid, errors, warnings)
        """
        self.reset()
        
        try:
            # Validate invoice
            if not self.validate_invoice(invoice):
                return False, self.errors, self.warnings
            
            # Validate contract
            if not self.validate_contract(invoice.contract):
                return False, self.errors, self.warnings
            
            # Validate property
            if not self.validate_property(invoice.contract.property):
                return False, self.errors, self.warnings
            
            # Validate owner
            if not self.validate_owner(invoice.contract.property.owner):
                return False, self.errors, self.warnings
            
            # Validate financial calculations
            is_valid, calculations = self.validate_financial_calculations(invoice, invoice.contract)
            if not is_valid:
                return False, self.errors, self.warnings
            
            # Validate existing receipts
            self.validate_existing_receipts(invoice)
            
            return len(self.errors) == 0, self.errors, self.warnings
            
        except Exception as e:
            logger.error(f"Error in complete validation for invoice {getattr(invoice, 'pk', 'unknown')}: {str(e)}")
            self.errors.append("Error interno en la validación completa")
            return False, self.errors, self.warnings
    
    def _get_property_address(self, property_obj):
        """Get property address safely."""
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
    
    def _get_person_name(self, person):
        """Get person name safely."""
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


def validate_owner_receipt_generation(invoice):
    """
    Convenience function to validate owner receipt generation.
    
    Args:
        invoice: Invoice instance to validate
        
    Returns:
        tuple: (bool, str, list) - (is_valid, error_message, warnings)
    """
    validator = OwnerReceiptValidator()
    is_valid, errors, warnings = validator.validate_complete(invoice)
    
    if not is_valid:
        error_message = "; ".join(errors)
        return False, error_message, warnings
    
    return True, "", warnings


def validate_receipt_resend(receipt):
    """
    Validate if a receipt can be resent.
    
    Args:
        receipt: OwnerReceipt instance
        
    Returns:
        tuple: (bool, str) - (can_resend, error_message)
    """
    try:
        if not receipt:
            return False, "Comprobante no encontrado"
        
        if not receipt.can_resend():
            current_status = receipt.get_status_display() if hasattr(receipt, 'get_status_display') else receipt.status
            return False, f"El comprobante no puede ser reenviado en su estado actual: {current_status}"
        
        # Validate associated invoice is still valid
        if hasattr(receipt, 'invoice') and receipt.invoice:
            is_valid, error_message, warnings = validate_owner_receipt_generation(receipt.invoice)
            if not is_valid:
                return False, f"La factura asociada ya no es válida: {error_message}"
        
        return True, ""
        
    except Exception as e:
        logger.error(f"Error validating receipt resend for receipt {getattr(receipt, 'pk', 'unknown')}: {str(e)}")
        return False, "Error interno validando el reenvío"