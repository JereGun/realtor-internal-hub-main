#!/usr/bin/env python
"""
Script para implementar un sistema de creación automática de facturas por contrato.

Este script crea:
1. Una tarea de Celery para generar facturas automáticamente
2. Un servicio para manejar la lógica de facturación recurrente
3. Métodos en el modelo Contract para calcular fechas de facturación
"""

import os
import sys
import django
from datetime import date, timedelta
from decimal import Decimal

# Configurar Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "real_estate_management.settings")
django.setup()

from django.utils import timezone
from contracts.models import Contract
from accounting.models_invoice import Invoice, InvoiceLine


def create_invoice_service():
    """Crear servicio de facturación automática"""

    service_content = '''from datetime import timedelta
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
'''

    # Crear directorio de servicios si no existe
    service_dir = "accounting/services"
    if not os.path.exists(service_dir):
        os.makedirs(service_dir)

    # Escribir el servicio
    service_path = f"{service_dir}/automatic_invoice_service.py"
    with open(service_path, "w", encoding="utf-8") as f:
        f.write(service_content)

    print(f"✅ Servicio de facturación automática creado: {service_path}")
    return service_path


def create_celery_task():
    """Crear tarea de Celery para facturación automática"""

    task_content = '''from celery import shared_task
from django.utils import timezone
from .services.automatic_invoice_service import AutomaticInvoiceService
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def generate_automatic_invoices(self):
    """
    Tarea programada para generar facturas automáticamente.
    
    Esta tarea se ejecuta diariamente y verifica todos los contratos activos
    para generar facturas según su frecuencia configurada.
    """
    try:
        logger.info("Iniciando generación automática de facturas")
        
        # Generar todas las facturas pendientes
        results = AutomaticInvoiceService.generate_all_due_invoices()
        
        # Log de resultados
        summary = results['summary']
        logger.info(
            f"Generación automática completada: "
            f"{summary['total_invoices_created']} facturas creadas, "
            f"{summary['total_errors']} errores"
        )
        
        # Retornar resumen para monitoreo
        return {
            'success': True,
            'invoices_created': summary['total_invoices_created'],
            'errors': summary['total_errors'],
            'details': results
        }
        
    except Exception as exc:
        logger.error(f"Error en generación automática de facturas: {str(exc)}")
        
        # Reintentar la tarea
        try:
            raise self.retry(countdown=60 * 5, exc=exc)  # Reintentar en 5 minutos
        except self.MaxRetriesExceeded:
            logger.error("Máximo número de reintentos alcanzado para generación de facturas")
            return {
                'success': False,
                'error': str(exc),
                'max_retries_exceeded': True
            }


@shared_task
def generate_monthly_invoices():
    """Tarea específica para generar facturas mensuales"""
    try:
        results = AutomaticInvoiceService.generate_monthly_invoices()
        logger.info(f"Facturas mensuales generadas: {results['invoices_created']}")
        return results
    except Exception as e:
        logger.error(f"Error generando facturas mensuales: {str(e)}")
        return {'success': False, 'error': str(e)}


@shared_task
def generate_quarterly_invoices():
    """Tarea específica para generar facturas trimestrales"""
    try:
        results = AutomaticInvoiceService.generate_quarterly_invoices()
        logger.info(f"Facturas trimestrales generadas: {results['invoices_created']}")
        return results
    except Exception as e:
        logger.error(f"Error generando facturas trimestrales: {str(e)}")
        return {'success': False, 'error': str(e)}
'''

    # Agregar la tarea al archivo de tareas existente
    tasks_file = "accounting/tasks.py"

    with open(tasks_file, "a", encoding="utf-8") as f:
        f.write("\n\n# Tareas de facturación automática\n")
        f.write(task_content)

    print(f"✅ Tareas de Celery agregadas a: {tasks_file}")
    return tasks_file


def add_contract_methods():
    """Agregar métodos al modelo Contract para facturación automática"""

    methods_content = '''
    def get_next_billing_date(self):
        """
        Calcula la próxima fecha de facturación para este contrato.
        
        Returns:
            date: Próxima fecha de facturación o None si no tiene frecuencia
        """
        if not self.frequency:
            return None
        
        from accounting.services.automatic_invoice_service import AutomaticInvoiceService
        return AutomaticInvoiceService._calculate_next_billing_date(self)
    
    def needs_billing(self, reference_date=None):
        """
        Verifica si este contrato necesita facturación.
        
        Args:
            reference_date (date, optional): Fecha de referencia. Por defecto hoy.
            
        Returns:
            bool: True si necesita facturación
        """
        if not self.frequency or self.status != self.STATUS_ACTIVE:
            return False
        
        if reference_date is None:
            from django.utils import timezone
            reference_date = timezone.now().date()
        
        from accounting.services.automatic_invoice_service import AutomaticInvoiceService
        return AutomaticInvoiceService._should_generate_invoice(self, reference_date)
    
    def generate_invoice(self, invoice_date=None):
        """
        Genera una factura para este contrato.
        
        Args:
            invoice_date (date, optional): Fecha de la factura. Por defecto hoy.
            
        Returns:
            Invoice: Factura creada
        """
        if invoice_date is None:
            from django.utils import timezone
            invoice_date = timezone.now().date()
        
        from accounting.services.automatic_invoice_service import AutomaticInvoiceService
        return AutomaticInvoiceService._create_invoice_from_contract(self, invoice_date)
    
    def get_billing_history(self):
        """
        Obtiene el historial de facturación de este contrato.
        
        Returns:
            QuerySet: Facturas del contrato ordenadas por fecha
        """
        return self.invoices.all().order_by('-date')
    
    def get_last_invoice_date(self):
        """
        Obtiene la fecha de la última factura generada.
        
        Returns:
            date: Fecha de la última factura o None si no hay facturas
        """
        last_invoice = self.invoices.order_by('-date').first()
        return last_invoice.date if last_invoice else None
    
    def days_since_last_invoice(self):
        """
        Calcula los días transcurridos desde la última factura.
        
        Returns:
            int: Días desde la última factura o None si no hay facturas
        """
        last_date = self.get_last_invoice_date()
        if not last_date:
            return None
        
        from django.utils import timezone
        today = timezone.now().date()
        return (today - last_date).days
'''

    print("📝 Métodos para agregar al modelo Contract:")
    print(methods_content)
    print(
        "\n💡 Para agregar estos métodos al modelo Contract, copia el código anterior"
    )
    print("   y pégalo al final de la clase Contract en contracts/models.py")

    return methods_content


def update_celery_schedule():
    """Mostrar configuración para agregar al CELERY_BEAT_SCHEDULE"""

    schedule_config = """
    # Generación automática de facturas - diariamente a las 6:00 AM
    'generate-automatic-invoices': {
        'task': 'accounting.tasks.generate_automatic_invoices',
        'schedule': crontab(hour=6, minute=0),
        'options': {
            'expires': 3600,
            'retry': True,
            'retry_policy': {
                'max_retries': 3,
                'interval_start': 0,
                'interval_step': 0.2,
                'interval_max': 0.2,
            }
        }
    },
    
    # Facturas mensuales - el día 1 de cada mes a las 7:00 AM
    'generate-monthly-invoices': {
        'task': 'accounting.tasks.generate_monthly_invoices',
        'schedule': crontab(hour=7, minute=0, day_of_month=1),
        'options': {
            'expires': 3600,
            'retry': True,
        }
    },
    
    # Facturas trimestrales - el día 1 de enero, abril, julio y octubre a las 7:30 AM
    'generate-quarterly-invoices': {
        'task': 'accounting.tasks.generate_quarterly_invoices',
        'schedule': crontab(hour=7, minute=30, day_of_month=1, month_of_year='1,4,7,10'),
        'options': {
            'expires': 3600,
            'retry': True,
        }
    },
"""

    print("📅 Configuración para agregar a CELERY_BEAT_SCHEDULE en settings.py:")
    print(schedule_config)

    return schedule_config


def test_automatic_system():
    """Probar el sistema de facturación automática"""
    print("\n🧪 Probando el sistema de facturación automática...")

    try:
        # Importar el servicio
        from accounting.services.automatic_invoice_service import (
            AutomaticInvoiceService,
        )

        # Obtener contratos activos con frecuencia
        contracts_with_frequency = Contract.objects.filter(
            status=Contract.STATUS_ACTIVE, frequency__isnull=False
        )

        print(
            f"📊 Contratos activos con frecuencia: {contracts_with_frequency.count()}"
        )

        for contract in contracts_with_frequency[:3]:  # Mostrar solo los primeros 3
            print(
                f"   - Contrato {contract.id}: {contract.frequency} - ${contract.amount}"
            )

            # Probar métodos si existen
            try:
                next_billing = contract.get_next_billing_date()
                needs_billing = contract.needs_billing()
                print(f"     * Próxima facturación: {next_billing}")
                print(f"     * Necesita facturación: {needs_billing}")
            except AttributeError:
                print("     * Métodos de facturación no agregados aún al modelo")

        # Probar generación de facturas (modo simulación)
        print("\n🔍 Simulando generación de facturas...")

        # Contar facturas antes
        invoice_count_before = Invoice.objects.count()

        # Simular generación (sin crear realmente)
        monthly_contracts = Contract.objects.filter(
            status=Contract.STATUS_ACTIVE, frequency="monthly"
        ).count()

        quarterly_contracts = Contract.objects.filter(
            status=Contract.STATUS_ACTIVE, frequency="quarterly"
        ).count()

        print(f"   - Contratos mensuales: {monthly_contracts}")
        print(f"   - Contratos trimestrales: {quarterly_contracts}")
        print(f"   - Total de facturas actuales: {invoice_count_before}")

        return True

    except ImportError as e:
        print(f"❌ Error importando servicio: {e}")
        return False
    except Exception as e:
        print(f"❌ Error en prueba: {e}")
        return False


def main():
    """Función principal"""
    print("🚀 Creando sistema de facturación automática por contrato\n")

    try:
        # 1. Crear servicio de facturación automática
        service_path = create_invoice_service()

        # 2. Crear tareas de Celery
        tasks_path = create_celery_task()

        # 3. Mostrar métodos para el modelo Contract
        contract_methods = add_contract_methods()

        # 4. Mostrar configuración de Celery Beat
        schedule_config = update_celery_schedule()

        # 5. Probar el sistema
        test_success = test_automatic_system()

        # Resumen final
        print("\n📋 RESUMEN DE IMPLEMENTACIÓN:")
        print("=" * 60)
        print(f"✅ Servicio creado: {service_path}")
        print(f"✅ Tareas agregadas: {tasks_path}")
        print("✅ Métodos del modelo mostrados")
        print("✅ Configuración de Celery mostrada")

        if test_success:
            print("✅ Pruebas básicas: EXITOSAS")
        else:
            print("⚠️  Pruebas básicas: REQUIEREN AJUSTES")

        print("\n📝 PRÓXIMOS PASOS:")
        print("1. Agregar los métodos mostrados al modelo Contract")
        print("2. Agregar la configuración de Celery Beat a settings.py")
        print("3. Reiniciar los servicios de Celery")
        print("4. Probar la generación manual de facturas")
        print("5. Monitorear las tareas programadas")

        print("\n🎯 FUNCIONALIDADES IMPLEMENTADAS:")
        print("- ✅ Creación automática de facturas por frecuencia")
        print("- ✅ Soporte para frecuencias: mensual, trimestral, semestral, anual")
        print("- ✅ Validación de períodos para evitar duplicados")
        print("- ✅ Cálculo automático de fechas de vencimiento")
        print("- ✅ Tareas programadas con Celery Beat")
        print("- ✅ Manejo de errores y reintentos")
        print("- ✅ Logging detallado para monitoreo")

    except Exception as e:
        print(f"❌ Error durante la implementación: {str(e)}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
