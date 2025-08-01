from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import TemplateView, FormView
from django.db.models import Sum, Q, Count
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from django.core.exceptions import ValidationError
from datetime import datetime, timedelta
import json

from .models import (
    Company, 
    CompanyConfiguration, 
    DocumentTemplate, 
    NotificationSettings, 
    SystemConfiguration
)
from .forms import (
    CompanyForm, 
    CompanyBasicForm,
    ContactInfoForm,
    SystemConfigForm,
    DocumentTemplateForm,
    NotificationForm
)
from .services.company_configuration_service import CompanyConfigurationService
from .services.document_template_service import DocumentTemplateService
from .services.backup_service import BackupService

from contracts.models import Contract
from payments.models import ContractPayment
from properties.models import Property, PropertyType, PropertyStatus
from customers.models import Customer

@login_required
def dashboard(request):
    """
    Vista principal del dashboard con métricas y estadísticas del negocio inmobiliario.
    """
    # Obtener fecha actual y rangos de tiempo
    today = timezone.now().date()
    current_month_start = today.replace(day=1)
    last_month = current_month_start - timedelta(days=1)
    last_month_start = last_month.replace(day=1)
    
    # === MÉTRICAS PRINCIPALES ===
    
    # Ventas de propiedades (contratos finalizados con propiedades de venta)
    sales_contracts = Contract.objects.filter(
        status='finished',
        property__listing_type__in=['sale', 'both']
    )
    sales_total = sales_contracts.aggregate(total=Sum('amount'))['total'] or 0
    sales_count = sales_contracts.count()

    # Ingresos por alquileres (pagos de contratos activos de alquiler)
    rent_contracts = Contract.objects.filter(
        status='active',
        property__listing_type__in=['rent', 'both']
    )
    rent_payments = ContractPayment.objects.filter(
        contract__in=rent_contracts, 
        status='paid'
    )
    rent_income = rent_payments.aggregate(total=Sum('amount'))['total'] or 0
    rent_count = rent_payments.count()

    # Pagos pendientes
    pending_payments_qs = ContractPayment.objects.filter(status='pending')
    pending_payments = pending_payments_qs.aggregate(total=Sum('amount'))['total'] or 0
    pending_count = pending_payments_qs.count()

    # Propiedades totales y disponibles
    total_properties = Property.objects.count()
    available_properties = Property.objects.filter(
        property_status__name__icontains='disponible'
    ).count()

    # === ESTADÍSTICAS ADICIONALES ===
    
    # Contratos activos
    active_contracts = Contract.objects.filter(status='active').count()
    
    # Nuevos clientes este mes
    new_customers = Customer.objects.filter(
        created_at__gte=current_month_start
    ).count()
    
    # Contratos próximos a vencer (próximos 30 días)
    expiring_date = today + timedelta(days=30)
    expiring_contracts = Contract.objects.filter(
        status='active',
        end_date__lte=expiring_date,
        end_date__gte=today
    ).count()
    
    # Pagos del mes actual
    monthly_payments = ContractPayment.objects.filter(
        payment_date__gte=current_month_start,
        status='paid'
    ).aggregate(total=Sum('amount'))['total'] or 0

    # === ÚLTIMAS OPERACIONES ===
    
    # Últimas ventas
    last_sales = sales_contracts.order_by('-created_at')[:5]
    # Últimos pagos de alquiler
    last_rents = rent_payments.order_by('-payment_date')[:5]
    
    last_operations = []
    
    # Agregar ventas
    for sale in last_sales:
        last_operations.append({
            'type': 'Venta',
            'property': str(sale.property),
            'customer': str(sale.customer),
            'amount': sale.amount,
            'date': sale.created_at
        })
    
    # Agregar alquileres
    for rent in last_rents:
        last_operations.append({
            'type': 'Alquiler',
            'property': str(rent.contract.property),
            'customer': str(rent.contract.customer),
            'amount': rent.amount,
            'date': rent.payment_date or rent.due_date
        })
    
    # Ordenar por fecha descendente
    last_operations = sorted(last_operations, key=lambda x: x['date'], reverse=True)[:10]

    # === ESTADÍSTICAS POR TIPO Y ESTADO ===
    
    # Propiedades por tipo
    property_types_stats = PropertyType.objects.annotate(
        count=Count('property')
    ).filter(count__gt=0).order_by('-count')[:6]
    
    # Propiedades por estado
    property_status_stats = PropertyStatus.objects.annotate(
        count=Count('property')
    ).filter(count__gt=0).order_by('-count')[:6]

    # === CONTEXTO PARA EL TEMPLATE ===
    context = {
        # Métricas principales
        'sales_total': sales_total,
        'sales_count': sales_count,
        'rent_income': rent_income,
        'rent_count': rent_count,
        'pending_payments': pending_payments,
        'pending_count': pending_count,
        'total_properties': total_properties,
        'available_properties': available_properties,
        
        # Estadísticas adicionales
        'active_contracts': active_contracts,
        'new_customers': new_customers,
        'expiring_contracts': expiring_contracts,
        'monthly_payments': monthly_payments,
        
        # Actividad reciente
        'last_operations': last_operations,
        
        # Estadísticas por categorías
        'property_types_stats': property_types_stats,
        'property_status_stats': property_status_stats,
    }
    
    return render(request, 'dashboard.html', context)


def company_settings(request):
    # Intentamos obtener la primera compañía, si no existe, la creamos
    company, created = Company.objects.get_or_create(
        id=1,
        defaults={'name': 'Mi Empresa'}
    )

    if request.method == 'POST':
        form = CompanyForm(request.POST, request.FILES, instance=company)
        if form.is_valid():
            form.save()
            messages.success(request, 'Los datos de la empresa se han actualizado correctamente.')
            return redirect('core:company_settings')
    else:
        form = CompanyForm(instance=company)

    return render(request, 'core/company_settings.html', {'form': form})

# ============================================================================
# VISTAS DE CONFIGURACIÓN AVANZADA
# ============================================================================

def is_admin_user(user):
    """Verifica si el usuario es administrador"""
    return user.is_authenticated and (user.is_superuser or user.is_staff)


class CompanyConfigurationView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """
    Vista principal de configuración de empresa con navegación por pestañas.
    
    Proporciona acceso a todas las secciones de configuración:
    - Datos básicos de empresa
    - Información de contacto
    - Configuraciones del sistema
    - Plantillas de documentos
    - Configuración de notificaciones
    - Respaldo y restauración
    """
    template_name = 'core/configuration/main.html'
    
    def test_func(self):
        """Solo administradores pueden acceder"""
        return is_admin_user(self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener o crear la empresa
        company, created = Company.objects.get_or_create(
            id=1,
            defaults={'name': 'Mi Empresa'}
        )
        
        context.update({
            'company': company,
            'active_tab': self.request.GET.get('tab', 'basic'),
            'page_title': 'Configuración de Empresa',
            'breadcrumbs': [
                {'name': 'Inicio', 'url': '/'},
                {'name': 'Configuración', 'url': None}
            ]
        })
        
        return context


class CompanyBasicInfoView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    """Vista para gestión de datos básicos de la empresa"""
    template_name = 'core/configuration/basic_info.html'
    form_class = CompanyBasicForm
    
    def test_func(self):
        return is_admin_user(self.request.user)
    
    def get_object(self):
        """Obtiene o crea la instancia de empresa"""
        company, created = Company.objects.get_or_create(
            id=1,
            defaults={'name': 'Mi Empresa'}
        )
        return company
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['instance'] = self.get_object()
        return kwargs
    
    def form_valid(self, form):
        form.save()
        messages.success(
            self.request, 
            'Los datos básicos de la empresa se han actualizado correctamente.'
        )
        return redirect('core:company_configuration')
    
    def form_invalid(self, form):
        messages.error(
            self.request,
            'Por favor, corrija los errores en el formulario.'
        )
        return super().form_invalid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'company': self.get_object(),
            'active_tab': 'basic',
            'section_title': 'Datos Básicos de la Empresa'
        })
        return context


class ContactInfoView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    """Vista para gestión de información de contacto"""
    template_name = 'core/configuration/contact_info.html'
    form_class = ContactInfoForm
    
    def test_func(self):
        return is_admin_user(self.request.user)
    
    def get_object(self):
        company, created = Company.objects.get_or_create(
            id=1,
            defaults={'name': 'Mi Empresa'}
        )
        return company
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['company'] = self.get_object()
        return kwargs
    
    def form_valid(self, form):
        company = self.get_object()
        form.save(company)
        messages.success(
            self.request,
            'La información de contacto se ha actualizado correctamente.'
        )
        return redirect('core:company_configuration')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'company': self.get_object(),
            'active_tab': 'contact',
            'section_title': 'Información de Contacto'
        })
        return context


class SystemConfigurationView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    """Vista para configuraciones operacionales del sistema"""
    template_name = 'core/configuration/system_config.html'
    form_class = SystemConfigForm
    
    def test_func(self):
        return is_admin_user(self.request.user)
    
    def get_object(self):
        company, created = Company.objects.get_or_create(
            id=1,
            defaults={'name': 'Mi Empresa'}
        )
        
        # Obtener o crear configuración del sistema
        sys_config, created = SystemConfiguration.objects.get_or_create(
            company=company,
            defaults={
                'currency': 'EUR',
                'timezone': 'Europe/Madrid',
                'date_format': 'DD/MM/YYYY',
                'language': 'es'
            }
        )
        return sys_config
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['instance'] = self.get_object()
        kwargs['company'] = self.get_object().company
        return kwargs
    
    def form_valid(self, form):
        form.save()
        
        # Aplicar configuraciones del sistema
        try:
            service = CompanyConfigurationService(self.get_object().company)
            service.apply_system_configurations()
        except Exception as e:
            messages.warning(
                self.request,
                f'Configuración guardada, pero hubo un problema aplicando algunos cambios: {str(e)}'
            )
        
        messages.success(
            self.request,
            'Las configuraciones del sistema se han actualizado correctamente.'
        )
        return redirect('core:company_configuration')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'company': self.get_object().company,
            'active_tab': 'system',
            'section_title': 'Configuraciones del Sistema'
        })
        return context


class DocumentTemplateView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """Vista para gestión de plantillas de documentos"""
    template_name = 'core/configuration/document_templates.html'
    
    def test_func(self):
        return is_admin_user(self.request.user)
    
    def get_company(self):
        company, created = Company.objects.get_or_create(
            id=1,
            defaults={'name': 'Mi Empresa'}
        )
        return company
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        company = self.get_company()
        
        # Obtener plantillas existentes
        templates = DocumentTemplate.objects.filter(
            company=company,
            is_active=True
        ).order_by('template_type', 'template_name')
        
        context.update({
            'company': company,
            'templates': templates,
            'active_tab': 'templates',
            'section_title': 'Plantillas de Documentos'
        })
        return context


class DocumentTemplateCreateView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    """Vista para crear nuevas plantillas de documentos"""
    template_name = 'core/configuration/template_form.html'
    form_class = DocumentTemplateForm
    
    def test_func(self):
        return is_admin_user(self.request.user)
    
    def get_company(self):
        company, created = Company.objects.get_or_create(
            id=1,
            defaults={'name': 'Mi Empresa'}
        )
        return company
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['company'] = self.get_company()
        return kwargs
    
    def form_valid(self, form):
        template = form.save()
        messages.success(
            self.request,
            f'La plantilla "{template.template_name}" se ha creado correctamente.'
        )
        return redirect('core:document_templates')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'company': self.get_company(),
            'active_tab': 'templates',
            'section_title': 'Crear Plantilla de Documento',
            'form_action': 'Crear'
        })
        return context


class DocumentTemplateEditView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    """Vista para editar plantillas de documentos existentes"""
    template_name = 'core/configuration/template_form.html'
    form_class = DocumentTemplateForm
    
    def test_func(self):
        return is_admin_user(self.request.user)
    
    def get_company(self):
        company, created = Company.objects.get_or_create(
            id=1,
            defaults={'name': 'Mi Empresa'}
        )
        return company
    
    def get_object(self):
        return get_object_or_404(
            DocumentTemplate,
            id=self.kwargs['template_id'],
            company=self.get_company()
        )
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['instance'] = self.get_object()
        kwargs['company'] = self.get_company()
        return kwargs
    
    def form_valid(self, form):
        template = form.save()
        messages.success(
            self.request,
            f'La plantilla "{template.template_name}" se ha actualizado correctamente.'
        )
        return redirect('core:document_templates')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        template = self.get_object()
        context.update({
            'company': self.get_company(),
            'template': template,
            'active_tab': 'templates',
            'section_title': f'Editar Plantilla: {template.template_name}',
            'form_action': 'Actualizar'
        })
        return context


class NotificationSettingsView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """Vista para configuración de notificaciones"""
    template_name = 'core/configuration/notifications.html'
    
    def test_func(self):
        return is_admin_user(self.request.user)
    
    def get_company(self):
        company, created = Company.objects.get_or_create(
            id=1,
            defaults={'name': 'Mi Empresa'}
        )
        return company
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        company = self.get_company()
        
        # Obtener configuraciones de notificaciones existentes
        notifications = NotificationSettings.objects.filter(
            company=company
        ).order_by('notification_type')
        
        context.update({
            'company': company,
            'notifications': notifications,
            'active_tab': 'notifications',
            'section_title': 'Configuración de Notificaciones'
        })
        return context


class NotificationCreateView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    """Vista para crear nuevas configuraciones de notificación"""
    template_name = 'core/configuration/notification_form.html'
    form_class = NotificationForm
    
    def test_func(self):
        return is_admin_user(self.request.user)
    
    def get_company(self):
        company, created = Company.objects.get_or_create(
            id=1,
            defaults={'name': 'Mi Empresa'}
        )
        return company
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['company'] = self.get_company()
        return kwargs
    
    def form_valid(self, form):
        notification = form.save()
        messages.success(
            self.request,
            f'La configuración de notificación "{notification.get_notification_type_display()}" se ha creado correctamente.'
        )
        return redirect('core:notification_settings')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'company': self.get_company(),
            'active_tab': 'notifications',
            'section_title': 'Crear Configuración de Notificación',
            'form_action': 'Crear'
        })
        return context


class NotificationEditView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    """Vista para editar configuraciones de notificación existentes"""
    template_name = 'core/configuration/notification_form.html'
    form_class = NotificationForm
    
    def test_func(self):
        return is_admin_user(self.request.user)
    
    def get_company(self):
        company, created = Company.objects.get_or_create(
            id=1,
            defaults={'name': 'Mi Empresa'}
        )
        return company
    
    def get_object(self):
        return get_object_or_404(
            NotificationSettings,
            id=self.kwargs['notification_id'],
            company=self.get_company()
        )
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['instance'] = self.get_object()
        kwargs['company'] = self.get_company()
        return kwargs
    
    def form_valid(self, form):
        notification = form.save()
        messages.success(
            self.request,
            f'La configuración de notificación "{notification.get_notification_type_display()}" se ha actualizado correctamente.'
        )
        return redirect('core:notification_settings')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        notification = self.get_object()
        context.update({
            'company': self.get_company(),
            'notification': notification,
            'active_tab': 'notifications',
            'section_title': f'Editar Notificación: {notification.get_notification_type_display()}',
            'form_action': 'Actualizar'
        })
        return context


class BackupRestoreView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """Vista para funcionalidades de respaldo y restauración"""
    template_name = 'core/configuration/backup_restore.html'
    
    def test_func(self):
        return is_admin_user(self.request.user)
    
    def get_company(self):
        company, created = Company.objects.get_or_create(
            id=1,
            defaults={'name': 'Mi Empresa'}
        )
        return company
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'company': self.get_company(),
            'active_tab': 'backup',
            'section_title': 'Respaldo y Restauración'
        })
        return context


# ============================================================================
# VISTAS API PARA FUNCIONALIDADES AJAX
# ============================================================================

@login_required
@user_passes_test(is_admin_user)
def template_preview_api(request):
    """API para generar preview de plantillas en tiempo real"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    
    try:
        data = json.loads(request.body)
        template_content = data.get('template_content', '')
        template_type = data.get('template_type', 'invoice')
        
        company, created = Company.objects.get_or_create(
            id=1,
            defaults={'name': 'Mi Empresa'}
        )
        
        service = DocumentTemplateService(company)
        preview_html = service.preview_template(template_content, template_type)
        
        return JsonResponse({
            'success': True,
            'preview_html': preview_html
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@login_required
@user_passes_test(is_admin_user)
def template_variables_api(request):
    """API para obtener variables disponibles por tipo de plantilla"""
    template_type = request.GET.get('type', 'invoice')
    
    try:
        company, created = Company.objects.get_or_create(
            id=1,
            defaults={'name': 'Mi Empresa'}
        )
        
        service = DocumentTemplateService(company)
        variables = service.get_available_variables(template_type)
        
        return JsonResponse({
            'success': True,
            'variables': variables
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@login_required
@user_passes_test(is_admin_user)
def create_backup_api(request):
    """API para crear respaldo de configuraciones"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    
    try:
        company, created = Company.objects.get_or_create(
            id=1,
            defaults={'name': 'Mi Empresa'}
        )
        
        service = BackupService(company)
        backup_data = service.export_configurations()
        
        # Crear respuesta con archivo JSON
        response = HttpResponse(
            json.dumps(backup_data, indent=2, ensure_ascii=False),
            content_type='application/json'
        )
        
        # Generar nombre de archivo
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"backup_configuracion_{timestamp}.json"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@login_required
@user_passes_test(is_admin_user)
def restore_backup_api(request):
    """API para restaurar configuraciones desde respaldo"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    
    try:
        if 'backup_file' not in request.FILES:
            return JsonResponse({
                'success': False,
                'error': 'No se proporcionó archivo de respaldo'
            }, status=400)
        
        backup_file = request.FILES['backup_file']
        overwrite = request.POST.get('overwrite', 'false').lower() == 'true'
        
        # Leer y validar archivo JSON
        try:
            backup_data = json.loads(backup_file.read().decode('utf-8'))
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Archivo de respaldo inválido (no es JSON válido)'
            }, status=400)
        
        company, created = Company.objects.get_or_create(
            id=1,
            defaults={'name': 'Mi Empresa'}
        )
        
        service = BackupService(company)
        
        # Validar respaldo
        is_valid, error_msg = service.validate_backup_data(backup_data)
        if not is_valid:
            return JsonResponse({
                'success': False,
                'error': f'Archivo de respaldo inválido: {error_msg}'
            }, status=400)
        
        # Restaurar configuraciones
        changes_summary = service.import_configurations(backup_data, overwrite)
        
        return JsonResponse({
            'success': True,
            'message': 'Configuraciones restauradas correctamente',
            'changes_summary': changes_summary
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@login_required
@user_passes_test(is_admin_user)
def delete_template_api(request, template_id):
    """API para eliminar plantillas de documentos"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    
    try:
        company, created = Company.objects.get_or_create(
            id=1,
            defaults={'name': 'Mi Empresa'}
        )
        
        template = get_object_or_404(
            DocumentTemplate,
            id=template_id,
            company=company
        )
        
        template_name = template.template_name
        template.is_active = False
        template.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Plantilla "{template_name}" eliminada correctamente'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@login_required
@user_passes_test(is_admin_user)
def delete_notification_api(request, notification_id):
    """API para eliminar configuraciones de notificación"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    
    try:
        company, created = Company.objects.get_or_create(
            id=1,
            defaults={'name': 'Mi Empresa'}
        )
        
        notification = get_object_or_404(
            NotificationSettings,
            id=notification_id,
            company=company
        )
        
        notification_type = notification.get_notification_type_display()
        notification.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'Configuración de notificación "{notification_type}" eliminada correctamente'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)