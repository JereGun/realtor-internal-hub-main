from datetime import timedelta
from django.utils import timezone
from decimal import Decimal
from contracts.models import Contract
from accounting.models_invoice import Invoice, InvoiceLine
import logging

logger = logging.getLogger(__name__)


class AutomaticInvoiceService:
    """
    Servicio para la creación automática de facturas basadas en contratos.
    
    Maneja la lógica de generación de facturas recurrentes según la frecuencia
    configurada en cada contrato activo.
    """
    
    @classmethod
    def generate_monthly_invoices(cls):
        """
        Genera facturas mensuales para contratos con frecuencia mensual.
        
        Returns:
            dict: Resumen de facturas creadas y errores
        """
        return cls._generate_invoices_by_frequency('monthly')
    
    @classmethod
    def generate_quarterly_invoices(cls):
        """
        Genera facturas trimestrales para contratos con frecuencia trimestral.
        
        Returns:
            dict: Resumen de facturas creadas y errores
        """
        return cls._generate_invoices_by_frequency('quarterly')
    
    @classmethod
    def generate_semi_annual_invoices(cls):
        """
        Genera facturas semestrales para contratos con frecuencia semestral.
        
        Returns:
            dict: Resumen de facturas creadas y errores
        """
        return cls._generate_invoices_by_frequency('semi-annually')
    
    @classmethod
    def generate_annual_invoices(cls):
        """
        Genera facturas anuales para contratos con frecuencia anual.
        
        Returns:
            dict: Resumen de facturas creadas y errores
        """
        return cls._generate_invoices_by_frequency('annually')
    
    @classmethod
    def _generate_invoices_by_frequency(cls, frequency):
        """
        Genera facturas para contratos con una frecuencia específica.
        
        Args:
            frequency (str): Frecuencia de facturación
            
        Returns:
            dict: Resumen de la operación
        """
        today = timezone.now().date()
        
        # Obtener contratos activos con la frecuencia especificada
        contracts = Contract.objects.filter(
            status=Contract.STATUS_ACTIVE,
            frequency=frequency
        ).select_related('customer', 'property', 'agent')
        
        created_invoices = []
        errors = []
        
        for contract in contracts:
            try:
                # Verificar si necesita facturación
                if cls._should_generate_invoice(contract, today):
                    invoice = cls._create_invoice_from_contract(contract, today)
                    created_invoices.append(invoice)
                    logger.info(f"Factura {invoice.number} creada para contrato {contract.id}")
                    
            except Exception as e:
                error_msg = f"Error al crear factura para contrato {contract.id}: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)
        
        return {
            'frequency': frequency,
            'contracts_processed': len(contracts),
            'invoices_created': len(created_invoices),
            'errors': len(errors),
            'created_invoices': created_invoices,
            'error_messages': errors
        }
    
    @classmethod
    def _should_generate_invoice(cls, contract, reference_date):
        """
        Determina si se debe generar una factura para un contrato en una fecha dada.
        
        Args:
            contract (Contract): Contrato a evaluar
            reference_date (date): Fecha de referencia
            
        Returns:
            bool: True si se debe generar factura
        """
        # Verificar si ya existe una factura para este período
        last_invoice = Invoice.objects.filter(
            contract=contract,
            date__gte=cls._get_period_start_date(contract, reference_date)
        ).order_by('-date').first()
        
        if last_invoice:
            return False  # Ya existe factura para este período
        
        # Verificar si es tiempo de facturar según la frecuencia
        return cls._is_billing_due(contract, reference_date)
    
    @classmethod
    def _is_billing_due(cls, contract, reference_date):
        """
        Verifica si es tiempo de facturar según la frecuencia del contrato.
        
        Args:
            contract (Contract): Contrato a evaluar
            reference_date (date): Fecha de referencia
            
        Returns:
            bool: True si es tiempo de facturar
        """
        if not contract.frequency:
            return False
        
        # Calcular la próxima fecha de facturación
        next_billing_date = cls._calculate_next_billing_date(contract)
        
        # Es tiempo de facturar si la fecha de referencia es igual o posterior
        return reference_date >= next_billing_date
    
    @classmethod
    def _calculate_next_billing_date(cls, contract):
        """
        Calcula la próxima fecha de facturación para un contrato.
        
        Args:
            contract (Contract): Contrato
            
        Returns:
            date: Próxima fecha de facturación
        """
        # Obtener la última factura del contrato
        last_invoice = Invoice.objects.filter(contract=contract).order_by('-date').first()
        
        if last_invoice:
            base_date = last_invoice.date
        else:
            base_date = contract.start_date
        
        # Calcular siguiente fecha según frecuencia
        if contract.frequency == 'monthly':
            # Próximo mes
            if base_date.month == 12:
                return base_date.replace(year=base_date.year + 1, month=1)
            else:
                return base_date.replace(month=base_date.month + 1)
                
        elif contract.frequency == 'quarterly':
            # Próximo trimestre (3 meses)
            return cls._add_months(base_date, 3)
            
        elif contract.frequency == 'semi-annually':
            # Próximo semestre (6 meses)
            return cls._add_months(base_date, 6)
            
        elif contract.frequency == 'annually':
            # Próximo año
            return base_date.replace(year=base_date.year + 1)
        
        return base_date
    
    @classmethod
    def _add_months(cls, date_obj, months):
        """
        Agrega meses a una fecha.
        
        Args:
            date_obj (date): Fecha base
            months (int): Número de meses a agregar
            
        Returns:
            date: Nueva fecha
        """
        month = date_obj.month - 1 + months
        year = date_obj.year + month // 12
        month = month % 12 + 1
        
        # Manejar casos donde el día no existe en el mes destino
        try:
            return date_obj.replace(year=year, month=month)
        except ValueError:
            # Si el día no existe (ej: 31 de febrero), usar el último día del mes
            import calendar
            last_day = calendar.monthrange(year, month)[1]
            return date_obj.replace(year=year, month=month, day=last_day)
    
    @classmethod
    def _get_period_start_date(cls, contract, reference_date):
        """
        Obtiene la fecha de inicio del período de facturación actual.
        
        Args:
            contract (Contract): Contrato
            reference_date (date): Fecha de referencia
            
        Returns:
            date: Fecha de inicio del período
        """
        if contract.frequency == 'monthly':
            return reference_date.replace(day=1)
        elif contract.frequency == 'quarterly':
            # Inicio del trimestre
            quarter_month = ((reference_date.month - 1) // 3) * 3 + 1
            return reference_date.replace(month=quarter_month, day=1)
        elif contract.frequency == 'semi-annually':
            # Inicio del semestre
            semester_month = 1 if reference_date.month <= 6 else 7
            return reference_date.replace(month=semester_month, day=1)
        elif contract.frequency == 'annually':
            return reference_date.replace(month=1, day=1)
        
        return reference_date
    
    @classmethod
    def _create_invoice_from_contract(cls, contract, invoice_date):
        """
        Crea una factura a partir de un contrato.
        
        Args:
            contract (Contract): Contrato base
            invoice_date (date): Fecha de la factura
            
        Returns:
            Invoice: Factura creada
        """
        # Calcular fecha de vencimiento (30 días por defecto)
        due_date = invoice_date + timedelta(days=30)
        
        # Crear descripción según frecuencia
        period_desc = cls._get_period_description(contract.frequency, invoice_date)
        
        # Crear factura
        invoice = Invoice.objects.create(
            customer=contract.customer,
            contract=contract,
            date=invoice_date,
            due_date=due_date,
            description=f'Factura automática - {period_desc} - {contract.property.title}',
            total_amount=contract.amount,
            status='validated'  # Marcar como validada automáticamente
        )
        
        # Crear línea de factura
        InvoiceLine.objects.create(
            invoice=invoice,
            concept=f'Alquiler {period_desc} - {contract.property.title}',
            amount=contract.amount
        )
        
        return invoice
    
    @classmethod
    def _get_period_description(cls, frequency, date_obj):
        """
        Obtiene la descripción del período según la frecuencia.
        
        Args:
            frequency (str): Frecuencia de facturación
            date_obj (date): Fecha de referencia
            
        Returns:
            str: Descripción del período
        """
        if frequency == 'monthly':
            return f"mes {date_obj.strftime('%B %Y')}"
        elif frequency == 'quarterly':
            quarter = (date_obj.month - 1) // 3 + 1
            return f"trimestre {quarter} {date_obj.year}"
        elif frequency == 'semi-annually':
            semester = 1 if date_obj.month <= 6 else 2
            return f"semestre {semester} {date_obj.year}"
        elif frequency == 'annually':
            return f"año {date_obj.year}"
        
        return f"período {date_obj.strftime('%B %Y')}"
    
    @classmethod
    def generate_all_due_invoices(cls):
        """
        Genera todas las facturas que están pendientes según sus frecuencias.
        
        Returns:
            dict: Resumen completo de la operación
        """
        results = {
            'monthly': cls.generate_monthly_invoices(),
            'quarterly': cls.generate_quarterly_invoices(),
            'semi_annual': cls.generate_semi_annual_invoices(),
            'annual': cls.generate_annual_invoices()
        }
        
        # Calcular totales
        total_invoices = sum(r['invoices_created'] for r in results.values())
        total_errors = sum(r['errors'] for r in results.values())
        
        results['summary'] = {
            'total_invoices_created': total_invoices,
            'total_errors': total_errors,
            'execution_date': timezone.now().date()
        }
        
        return results
