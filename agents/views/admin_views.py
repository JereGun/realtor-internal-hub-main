"""
Vistas de administración de usuarios.

Este módulo contiene las vistas para administradores que permiten
gestionar usuarios, roles, permisos y logs de auditoría.
"""

import logging
from typing import Dict, Any
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse, HttpResponse, Http404
from django.views.decorators.http import require_http_methods
from django.views.generic import ListView, DetailView, UpdateView
from django.core.paginator import Paginator
from django.db.models import Q, Count, Avg
from django.utils import timezone
from datetime import timedelta
import csv

from agents.models import Agent, UserProfile, SecuritySettings, AuditLog, Role, AgentRole
from agents.forms import ProfileUpdateForm, SecuritySettingsForm
from agents.services.user_management_service import UserManagementService
from agents.services.audit_service import AuditService


logger = logging.getLogger(__name__)


def is_admin_user(user):
    """Verifica si el usuario es administrador."""
    if not user.is_authenticated:
        return False
    return user.is_superuser or user.is_staff


class AdminUserListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """
    Vista de lista de usuarios para administradores.
    
    Permite filtrar, buscar y paginar usuarios del sistema.
    """
    model = Agent
    template_name = 'agents/admin/user_list.html'
    context_object_name = 'users'
    paginate_by = 25
    
    def test_func(self):
        """Verificar que el usuario sea administrador."""
        return is_admin_user(self.request.user)
    
    def get_queryset(self):
        """Obtener queryset filtrado y ordenado."""
        queryset = Agent.objects.select_related('profile').prefetch_related('roles')
        
        # Filtros
        search = self.request.GET.get('search', '').strip()
        status = self.request.GET.get('status', '')
        role = self.request.GET.get('role', '')
        
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(email__icontains=search) |
                Q(license_number__icontains=search)
            )
        
        if status == 'active':
            queryset = queryset.filter(is_active=True)
        elif status == 'inactive':
            queryset = queryset.filter(is_active=False)
        
        if role:
            queryset = queryset.filter(roles__name=role)
        
        # Ordenamiento
        order_by = self.request.GET.get('order_by', '-date_joined')
        if order_by in ['first_name', 'last_name', 'email', 'date_joined', '-date_joined', 'last_login', '-last_login']:
            queryset = queryset.order_by(order_by)
        
        return queryset.distinct()
    
    def get_context_data(self, **kwargs):
        """Añadir contexto adicional."""
        context = super().get_context_data(**kwargs)
        
        # Estadísticas generales
        total_users = Agent.objects.count()
        active_users = Agent.objects.filter(is_active=True).count()
        inactive_users = total_users - active_users
        
        # Usuarios recientes (últimos 30 días)
        recent_users = Agent.objects.filter(
            date_joined__gte=timezone.now() - timedelta(days=30)
        ).count()
        
        # Roles disponibles para filtro
        available_roles = Role.objects.all().order_by('name')
        
        context.update({
            'title': 'Gestión de Usuarios',
            'total_users': total_users,
            'active_users': active_users,
            'inactive_users': inactive_users,
            'recent_users': recent_users,
            'available_roles': available_roles,
            'current_filters': {
                'search': self.request.GET.get('search', ''),
                'status': self.request.GET.get('status', ''),
                'role': self.request.GET.get('role', ''),
                'order_by': self.request.GET.get('order_by', '-date_joined')
            }
        })
        
        return context


class AdminUserDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    """
    Vista de detalle de usuario para administradores.
    
    Muestra información completa del usuario, estadísticas y actividad reciente.
    """
    model = Agent
    template_name = 'agents/admin/user_detail.html'
    context_object_name = 'user_detail'
    
    def test_func(self):
        """Verificar que el usuario sea administrador."""
        return is_admin_user(self.request.user)
    
    def get_context_data(self, **kwargs):
        """Añadir contexto adicional."""
        context = super().get_context_data(**kwargs)
        user_detail = self.get_object()
        
        # Servicios
        user_service = UserManagementService()
        audit_service = AuditService()
        
        # Estadísticas del usuario
        user_stats = user_service.get_user_statistics(user_detail)
        
        # Actividad reciente
        recent_activity = AuditLog.objects.filter(
            agent=user_detail
        ).order_by('-created_at')[:20]
        
        # Sesiones activas
        from agents.services.session_service import SessionService
        session_service = SessionService()
        active_sessions = session_service.get_active_sessions(user_detail)
        
        # Configuraciones de seguridad
        try:
            security_settings = user_detail.security_settings
        except SecuritySettings.DoesNotExist:
            security_settings = None
        
        # Roles del usuario
        user_roles = AgentRole.objects.filter(
            agent=user_detail,
            is_active=True
        ).select_related('role', 'assigned_by')
        
        # Completitud del perfil
        profile_completion = user_service.calculate_profile_completion(user_detail)
        
        # Actividad sospechosa
        suspicious_activity = audit_service.detect_suspicious_activity(user_detail, days=7)
        
        context.update({
            'title': f'Usuario: {user_detail.get_full_name()}',
            'user_stats': user_stats,
            'recent_activity': recent_activity,
            'active_sessions': active_sessions,
            'security_settings': security_settings,
            'user_roles': user_roles,
            'profile_completion': profile_completion,
            'suspicious_activity': suspicious_activity,
            'available_roles': Role.objects.all().order_by('name')
        })
        
        return context


@login_required
@user_passes_test(is_admin_user)
def admin_user_toggle_status(request, user_id):
    """
    Vista para activar/desactivar usuario.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    
    try:
        user = get_object_or_404(Agent, id=user_id)
        
        # No permitir desactivar al propio usuario
        if user == request.user:
            return JsonResponse({
                'error': 'No puedes desactivar tu propia cuenta'
            }, status=400)
        
        # Cambiar estado
        user.is_active = not user.is_active
        user.save()
        
        # Registrar acción
        AuditLog.objects.create(
            agent=request.user,
            action='user_status_changed',
            resource_type='agent',
            resource_id=str(user.id),
            ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            details={
                'target_user': user.email,
                'new_status': 'active' if user.is_active else 'inactive',
                'action_type': 'activate' if user.is_active else 'deactivate'
            },
            success=True,
            session_key=request.session.session_key
        )
        
        # Si se desactiva, terminar sesiones
        if not user.is_active:
            from agents.services.session_service import SessionService
            session_service = SessionService()
            terminated_count = session_service.terminate_all_sessions(user)
            
            logger.info(f"User {user.email} deactivated by {request.user.email}, {terminated_count} sessions terminated")
        
        return JsonResponse({
            'success': True,
            'new_status': 'active' if user.is_active else 'inactive',
            'message': f'Usuario {"activado" if user.is_active else "desactivado"} correctamente'
        })
        
    except Exception as e:
        logger.error(f"Error toggling user status: {str(e)}")
        return JsonResponse({'error': 'Error interno del servidor'}, status=500)


@login_required
@user_passes_test(is_admin_user)
def admin_assign_role(request, user_id):
    """
    Vista para asignar rol a usuario.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    
    try:
        user = get_object_or_404(Agent, id=user_id)
        role_id = request.POST.get('role_id')
        
        if not role_id:
            return JsonResponse({'error': 'ID de rol requerido'}, status=400)
        
        role = get_object_or_404(Role, id=role_id)
        
        # Verificar si ya tiene el rol
        existing_role = AgentRole.objects.filter(
            agent=user,
            role=role,
            is_active=True
        ).first()
        
        if existing_role:
            return JsonResponse({
                'error': f'El usuario ya tiene el rol {role.name}'
            }, status=400)
        
        # Asignar rol
        agent_role = AgentRole.objects.create(
            agent=user,
            role=role,
            assigned_by=request.user,
            is_active=True
        )
        
        # Registrar acción
        AuditLog.objects.create(
            agent=request.user,
            action='role_assigned',
            resource_type='agent_role',
            resource_id=str(agent_role.id),
            ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            details={
                'target_user': user.email,
                'role_name': role.name,
                'role_id': role.id
            },
            success=True,
            session_key=request.session.session_key
        )
        
        logger.info(f"Role {role.name} assigned to {user.email} by {request.user.email}")
        
        return JsonResponse({
            'success': True,
            'message': f'Rol {role.name} asignado correctamente',
            'role': {
                'id': role.id,
                'name': role.name,
                'assigned_at': agent_role.assigned_at.isoformat(),
                'assigned_by': request.user.get_full_name()
            }
        })
        
    except Exception as e:
        logger.error(f"Error assigning role: {str(e)}")
        return JsonResponse({'error': 'Error interno del servidor'}, status=500)


@login_required
@user_passes_test(is_admin_user)
def admin_remove_role(request, user_id, role_id):
    """
    Vista para remover rol de usuario.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    
    try:
        user = get_object_or_404(Agent, id=user_id)
        role = get_object_or_404(Role, id=role_id)
        
        # Buscar asignación de rol activa
        agent_role = AgentRole.objects.filter(
            agent=user,
            role=role,
            is_active=True
        ).first()
        
        if not agent_role:
            return JsonResponse({
                'error': f'El usuario no tiene el rol {role.name}'
            }, status=400)
        
        # Desactivar rol
        agent_role.is_active = False
        agent_role.save()
        
        # Registrar acción
        AuditLog.objects.create(
            agent=request.user,
            action='role_removed',
            resource_type='agent_role',
            resource_id=str(agent_role.id),
            ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            details={
                'target_user': user.email,
                'role_name': role.name,
                'role_id': role.id
            },
            success=True,
            session_key=request.session.session_key
        )
        
        logger.info(f"Role {role.name} removed from {user.email} by {request.user.email}")
        
        return JsonResponse({
            'success': True,
            'message': f'Rol {role.name} removido correctamente'
        })
        
    except Exception as e:
        logger.error(f"Error removing role: {str(e)}")
        return JsonResponse({'error': 'Error interno del servidor'}, status=500)


class AdminAuditLogView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """
    Vista de logs de auditoría para administradores.
    
    Permite filtrar, buscar y exportar logs de auditoría.
    """
    model = AuditLog
    template_name = 'agents/admin/audit_logs.html'
    context_object_name = 'audit_logs'
    paginate_by = 50
    
    def test_func(self):
        """Verificar que el usuario sea administrador."""
        return is_admin_user(self.request.user)
    
    def get_queryset(self):
        """Obtener queryset filtrado y ordenado."""
        queryset = AuditLog.objects.select_related('agent').order_by('-created_at')
        
        # Filtros
        user_id = self.request.GET.get('user')
        action = self.request.GET.get('action')
        success = self.request.GET.get('success')
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        ip_address = self.request.GET.get('ip_address')
        
        if user_id:
            queryset = queryset.filter(agent_id=user_id)
        
        if action:
            queryset = queryset.filter(action=action)
        
        if success == 'true':
            queryset = queryset.filter(success=True)
        elif success == 'false':
            queryset = queryset.filter(success=False)
        
        if date_from:
            try:
                from datetime import datetime
                date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
                queryset = queryset.filter(created_at__date__gte=date_from_obj.date())
            except ValueError:
                pass
        
        if date_to:
            try:
                from datetime import datetime
                date_to_obj = datetime.strptime(date_to, '%Y-%m-%d')
                queryset = queryset.filter(created_at__date__lte=date_to_obj.date())
            except ValueError:
                pass
        
        if ip_address:
            queryset = queryset.filter(ip_address__icontains=ip_address)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        """Añadir contexto adicional."""
        context = super().get_context_data(**kwargs)
        
        # Estadísticas de logs
        total_logs = AuditLog.objects.count()
        successful_logs = AuditLog.objects.filter(success=True).count()
        failed_logs = total_logs - successful_logs
        
        # Acciones más frecuentes
        top_actions = AuditLog.objects.values('action').annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        
        # Usuarios más activos
        top_users = AuditLog.objects.exclude(agent=None).values(
            'agent__email', 'agent__first_name', 'agent__last_name'
        ).annotate(count=Count('id')).order_by('-count')[:10]
        
        # Usuarios para filtro
        users_for_filter = Agent.objects.filter(
            id__in=AuditLog.objects.exclude(agent=None).values_list('agent_id', flat=True).distinct()
        ).order_by('first_name', 'last_name')
        
        # Acciones para filtro
        actions_for_filter = AuditLog.objects.values_list('action', flat=True).distinct().order_by('action')
        
        context.update({
            'title': 'Logs de Auditoría',
            'total_logs': total_logs,
            'successful_logs': successful_logs,
            'failed_logs': failed_logs,
            'success_rate': (successful_logs / total_logs * 100) if total_logs > 0 else 0,
            'top_actions': top_actions,
            'top_users': top_users,
            'users_for_filter': users_for_filter,
            'actions_for_filter': actions_for_filter,
            'current_filters': {
                'user': self.request.GET.get('user', ''),
                'action': self.request.GET.get('action', ''),
                'success': self.request.GET.get('success', ''),
                'date_from': self.request.GET.get('date_from', ''),
                'date_to': self.request.GET.get('date_to', ''),
                'ip_address': self.request.GET.get('ip_address', '')
            }
        })
        
        return context


@login_required
@user_passes_test(is_admin_user)
def admin_export_audit_logs(request):
    """
    Vista para exportar logs de auditoría en CSV.
    """
    try:
        # Aplicar los mismos filtros que la vista de lista
        queryset = AuditLog.objects.select_related('agent').order_by('-created_at')
        
        # Aplicar filtros (reutilizar lógica de AdminAuditLogView)
        user_id = request.GET.get('user')
        action = request.GET.get('action')
        success = request.GET.get('success')
        date_from = request.GET.get('date_from')
        date_to = request.GET.get('date_to')
        ip_address = request.GET.get('ip_address')
        
        if user_id:
            queryset = queryset.filter(agent_id=user_id)
        if action:
            queryset = queryset.filter(action=action)
        if success == 'true':
            queryset = queryset.filter(success=True)
        elif success == 'false':
            queryset = queryset.filter(success=False)
        if date_from:
            try:
                from datetime import datetime
                date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
                queryset = queryset.filter(created_at__date__gte=date_from_obj.date())
            except ValueError:
                pass
        if date_to:
            try:
                from datetime import datetime
                date_to_obj = datetime.strptime(date_to, '%Y-%m-%d')
                queryset = queryset.filter(created_at__date__lte=date_to_obj.date())
            except ValueError:
                pass
        if ip_address:
            queryset = queryset.filter(ip_address__icontains=ip_address)
        
        # Crear respuesta CSV
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="audit_logs_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        writer = csv.writer(response)
        
        # Escribir encabezados
        writer.writerow([
            'Fecha/Hora', 'Usuario', 'Acción', 'Recurso', 'IP', 'Éxito', 'Detalles'
        ])
        
        # Escribir datos (limitar a 10000 registros para evitar timeouts)
        for log in queryset[:10000]:
            writer.writerow([
                log.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                log.agent.email if log.agent else 'Sistema',
                log.action,
                f"{log.resource_type}:{log.resource_id}" if log.resource_id else log.resource_type,
                log.ip_address,
                'Sí' if log.success else 'No',
                str(log.details) if log.details else ''
            ])
        
        # Registrar exportación
        AuditLog.objects.create(
            agent=request.user,
            action='audit_logs_exported',
            resource_type='audit_log',
            ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            details={
                'export_count': min(queryset.count(), 10000),
                'filters_applied': {
                    'user': user_id,
                    'action': action,
                    'success': success,
                    'date_from': date_from,
                    'date_to': date_to,
                    'ip_address': ip_address
                }
            },
            success=True,
            session_key=request.session.session_key
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error exporting audit logs: {str(e)}")
        messages.error(request, 'Error exportando logs de auditoría.')
        return redirect('agents:admin_audit_logs')


@login_required
@user_passes_test(is_admin_user)
def admin_dashboard(request):
    """
    Dashboard principal para administradores.
    """
    try:
        # Estadísticas generales
        total_users = Agent.objects.count()
        active_users = Agent.objects.filter(is_active=True).count()
        inactive_users = total_users - active_users
        
        # Usuarios recientes
        recent_users = Agent.objects.filter(
            date_joined__gte=timezone.now() - timedelta(days=7)
        ).count()
        
        # Actividad reciente
        recent_activity = AuditLog.objects.select_related('agent').order_by('-created_at')[:10]
        
        # Estadísticas de auditoría
        total_logs = AuditLog.objects.count()
        failed_actions = AuditLog.objects.filter(success=False).count()
        
        # Actividad sospechosa
        audit_service = AuditService()
        suspicious_activity = audit_service.detect_suspicious_activity(days=7)
        
        # Sesiones activas
        from agents.models import UserSession
        active_sessions = UserSession.objects.filter(
            is_active=True,
            expires_at__gt=timezone.now()
        ).count()
        
        context = {
            'title': 'Panel de Administración',
            'total_users': total_users,
            'active_users': active_users,
            'inactive_users': inactive_users,
            'recent_users': recent_users,
            'recent_activity': recent_activity,
            'total_logs': total_logs,
            'failed_actions': failed_actions,
            'suspicious_activity': suspicious_activity,
            'active_sessions': active_sessions
        }
        
        return render(request, 'agents/admin/dashboard.html', context)
        
    except Exception as e:
        logger.error(f"Error loading admin dashboard: {str(e)}")
        messages.error(request, 'Error cargando el panel de administración.')
        return redirect('agents:dashboard')


@login_required
@user_passes_test(is_admin_user)
def admin_terminate_session(request, session_key):
    """
    Vista para terminar una sesión específica desde administración.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    
    try:
        from agents.models import UserSession
        from agents.services.session_service import SessionService
        
        session = get_object_or_404(UserSession, session_key=session_key)
        session_service = SessionService()
        
        # Terminar sesión
        success = session_service.terminate_session(session_key)
        
        if success:
            # Registrar acción
            AuditLog.objects.create(
                agent=request.user,
                action='session_terminated_by_admin',
                resource_type='user_session',
                resource_id=session_key,
                ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1'),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                details={
                    'target_user': session.agent.email,
                    'session_ip': session.ip_address,
                    'terminated_by_admin': True
                },
                success=True,
                session_key=request.session.session_key
            )
            
            logger.info(f"Session {session_key} terminated by admin {request.user.email}")
            
            return JsonResponse({
                'success': True,
                'message': 'Sesión terminada correctamente'
            })
        else:
            return JsonResponse({
                'error': 'Error terminando la sesión'
            }, status=400)
            
    except Exception as e:
        logger.error(f"Error terminating session from admin: {str(e)}")
        return JsonResponse({'error': 'Error interno del servidor'}, status=500)