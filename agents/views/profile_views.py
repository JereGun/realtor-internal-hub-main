"""
Vistas de gestión de perfil de usuario.

Este módulo contiene las vistas para gestión completa del perfil de usuario,
incluyendo edición de perfil, configuraciones de seguridad y gestión de sesiones.
"""

import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse, HttpResponseRedirect
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView, FormView, UpdateView
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db import transaction

from agents.models import Agent, UserProfile, SecuritySettings, AuditLog, UserSession
from agents.forms import ProfileUpdateForm, SecuritySettingsForm
from agents.services.user_management_service import UserManagementService
from agents.services.session_service import SessionService


logger = logging.getLogger(__name__)


class ProfileView(LoginRequiredMixin, TemplateView):
    """
    Vista de perfil completo del usuario con información detallada.
    
    Muestra toda la información del perfil, estadísticas de completitud,
    configuraciones de seguridad y actividad reciente.
    """
    template_name = 'agents/profile/profile.html'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_service = UserManagementService()
        self.session_service = SessionService()
    
    def get_context_data(self, **kwargs):
        """Añadir datos del perfil al contexto"""
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        try:
            # Obtener o crear perfil
            profile, created = UserProfile.objects.get_or_create(agent=user)
            if created:
                logger.info(f"Created new profile for user: {user.email}")
            
            # Obtener configuraciones de seguridad
            security_settings, _ = SecuritySettings.objects.get_or_create(agent=user)
            
            # Calcular completitud del perfil
            profile_completion = self.user_service.calculate_profile_completion(user)
            
            # Obtener sesiones activas
            active_sessions = self.session_service.get_active_sessions(user)
            
            # Obtener actividad reciente
            recent_activity = AuditLog.objects.filter(
                agent=user
            ).order_by('-created_at')[:10]
            
            # Estadísticas del perfil
            profile_stats = {
                'total_logins': AuditLog.objects.filter(
                    agent=user, 
                    action='login', 
                    success=True
                ).count(),
                'last_login': user.last_login,
                'account_created': user.date_joined,
                'profile_updates': AuditLog.objects.filter(
                    agent=user, 
                    action='profile_update'
                ).count(),
                'security_events': AuditLog.objects.filter(
                    agent=user,
                    action__in=['password_change', '2fa_enabled', '2fa_disabled', 'suspicious_activity']
                ).count()
            }
            
            context.update({
                'title': 'Mi Perfil',
                'agent': user,
                'profile': profile,
                'security_settings': security_settings,
                'profile_completion': profile_completion,
                'active_sessions': active_sessions,
                'recent_activity': recent_activity,
                'profile_stats': profile_stats,
                'show_completion_warning': profile_completion < 80,
                'has_2fa': profile.two_factor_enabled,
                'session_count': active_sessions.count()
            })
            
        except Exception as e:
            logger.error(f"Error loading profile for {user.email}: {str(e)}")
            messages.error(self.request, 'Error cargando el perfil. Intente nuevamente.')
            context.update({
                'title': 'Mi Perfil',
                'agent': user,
                'error': True
            })
        
        return context


class ProfileEditView(LoginRequiredMixin, FormView):
    """
    Vista para edición del perfil de usuario.
    
    Permite actualizar información personal, avatar, preferencias
    y configuraciones básicas del perfil.
    """
    template_name = 'agents/profile/edit_profile.html'
    form_class = ProfileUpdateForm
    success_url = reverse_lazy('agents:profile')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_service = UserManagementService()
    
    def get_form_kwargs(self):
        """Añadir usuario y perfil al formulario"""
        kwargs = super().get_form_kwargs()
        kwargs['agent'] = self.request.user
        
        # Obtener o crear perfil
        profile, created = UserProfile.objects.get_or_create(agent=self.request.user)
        kwargs['instance'] = profile
        
        return kwargs
    
    def form_valid(self, form):
        """Procesar actualización del perfil"""
        try:
            with transaction.atomic():
                # Guardar el perfil
                profile = form.save()
                
                # Recalcular completitud del perfil
                completion = self.user_service.calculate_profile_completion(self.request.user)
                profile.profile_completion = completion
                profile.save()
                
                # Registrar actualización
                AuditLog.objects.create(
                    agent=self.request.user,
                    action='profile_update',
                    resource_type='user_profile',
                    resource_id=str(profile.id),
                    ip_address=self._get_client_ip(),
                    user_agent=self.request.META.get('HTTP_USER_AGENT', ''),
                    details={
                        'updated_fields': list(form.changed_data),
                        'completion_percentage': completion
                    },
                    success=True,
                    session_key=self.request.session.session_key
                )
                
                messages.success(
                    self.request, 
                    f'Perfil actualizado correctamente. Completitud: {completion}%'
                )
                
                logger.info(f"Profile updated for user: {self.request.user.email}")
                
        except Exception as e:
            logger.error(f"Error updating profile for {self.request.user.email}: {str(e)}")
            messages.error(self.request, 'Error actualizando el perfil. Intente nuevamente.')
            return self.form_invalid(form)
        
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        """Añadir contexto adicional"""
        context = super().get_context_data(**kwargs)
        
        # Obtener perfil actual
        profile, _ = UserProfile.objects.get_or_create(agent=self.request.user)
        
        context.update({
            'title': 'Editar Perfil',
            'agent': self.request.user,
            'profile': profile,
            'current_completion': profile.profile_completion,
            'avatar_url': profile.avatar.url if profile.avatar else None
        })
        
        return context
    
    def _get_client_ip(self):
        """Obtener IP del cliente"""
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = self.request.META.get('REMOTE_ADDR', '127.0.0.1')
        return ip


class SecuritySettingsView(LoginRequiredMixin, FormView):
    """
    Vista para configuraciones de seguridad del usuario.
    
    Permite configurar 2FA, timeouts de sesión, alertas de seguridad
    y otras configuraciones relacionadas con la seguridad de la cuenta.
    """
    template_name = 'agents/profile/security_settings.html'
    form_class = SecuritySettingsForm
    success_url = reverse_lazy('agents:security_settings')
    
    def get_form_kwargs(self):
        """Añadir usuario y configuraciones actuales al formulario"""
        kwargs = super().get_form_kwargs()
        kwargs['agent'] = self.request.user
        
        # Obtener o crear configuraciones de seguridad
        security_settings, created = SecuritySettings.objects.get_or_create(
            agent=self.request.user
        )
        kwargs['instance'] = security_settings
        
        return kwargs
    
    def form_valid(self, form):
        """Procesar actualización de configuraciones de seguridad"""
        try:
            with transaction.atomic():
                # Guardar configuraciones de seguridad
                security_settings = form.save()
                
                # Manejar habilitación/deshabilitación de 2FA
                enable_2fa = form.cleaned_data.get('enable_2fa', False)
                profile, _ = UserProfile.objects.get_or_create(agent=self.request.user)
                
                if enable_2fa and not profile.two_factor_enabled:
                    # Redirigir a configuración de 2FA
                    messages.info(
                        self.request,
                        'Para habilitar 2FA, complete la configuración en la siguiente página.'
                    )
                    return redirect('agents:setup_2fa')
                
                elif not enable_2fa and profile.two_factor_enabled:
                    # Deshabilitar 2FA
                    profile.two_factor_enabled = False
                    profile.two_factor_secret = None
                    profile.backup_codes = []
                    profile.save()
                    
                    # Registrar deshabilitación de 2FA
                    AuditLog.objects.create(
                        agent=self.request.user,
                        action='2fa_disabled',
                        resource_type='security_settings',
                        ip_address=self._get_client_ip(),
                        user_agent=self.request.META.get('HTTP_USER_AGENT', ''),
                        details={'method': 'user_settings'},
                        success=True,
                        session_key=self.request.session.session_key
                    )
                    
                    messages.success(self.request, 'Autenticación de dos factores deshabilitada.')
                
                # Registrar cambio de configuraciones
                AuditLog.objects.create(
                    agent=self.request.user,
                    action='security_settings_change',
                    resource_type='security_settings',
                    resource_id=str(security_settings.id),
                    ip_address=self._get_client_ip(),
                    user_agent=self.request.META.get('HTTP_USER_AGENT', ''),
                    details={
                        'updated_fields': list(form.changed_data),
                        'session_timeout': security_settings.session_timeout_minutes,
                        'alerts_enabled': security_settings.suspicious_activity_alerts
                    },
                    success=True,
                    session_key=self.request.session.session_key
                )
                
                messages.success(self.request, 'Configuraciones de seguridad actualizadas.')
                logger.info(f"Security settings updated for user: {self.request.user.email}")
                
        except Exception as e:
            logger.error(f"Error updating security settings for {self.request.user.email}: {str(e)}")
            messages.error(self.request, 'Error actualizando configuraciones. Intente nuevamente.')
            return self.form_invalid(form)
        
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        """Añadir contexto adicional"""
        context = super().get_context_data(**kwargs)
        
        # Obtener configuraciones actuales
        security_settings, _ = SecuritySettings.objects.get_or_create(
            agent=self.request.user
        )
        profile, _ = UserProfile.objects.get_or_create(agent=self.request.user)
        
        # Estadísticas de seguridad
        security_stats = {
            'last_password_change': security_settings.password_changed_at,
            'failed_login_attempts': security_settings.login_attempts,
            'is_account_locked': security_settings.is_locked(),
            'has_2fa': profile.two_factor_enabled,
            'backup_codes_count': len(profile.backup_codes) if profile.backup_codes else 0,
            'allowed_ips_count': len(security_settings.allowed_ip_addresses) if security_settings.allowed_ip_addresses else 0
        }
        
        context.update({
            'title': 'Configuraciones de Seguridad',
            'security_settings': security_settings,
            'profile': profile,
            'security_stats': security_stats,
            'show_2fa_setup': not profile.two_factor_enabled
        })
        
        return context
    
    def _get_client_ip(self):
        """Obtener IP del cliente"""
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = self.request.META.get('REMOTE_ADDR', '127.0.0.1')
        return ip


class SessionManagementView(LoginRequiredMixin, TemplateView):
    """
    Vista para gestión de sesiones activas del usuario.
    
    Permite ver todas las sesiones activas, información de dispositivos
    y ubicaciones, y terminar sesiones específicas o todas las sesiones.
    """
    template_name = 'agents/profile/session_management.html'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session_service = SessionService()
    
    def get_context_data(self, **kwargs):
        """Añadir datos de sesiones al contexto"""
        context = super().get_context_data(**kwargs)
        
        try:
            # Obtener sesiones activas
            active_sessions = self.session_service.get_active_sessions(self.request.user)
            
            # Obtener información detallada de cada sesión
            sessions_data = []
            current_session_key = self.request.session.session_key
            
            for session in active_sessions:
                session_info = {
                    'session_key': session.session_key,
                    'ip_address': session.ip_address,
                    'user_agent': session.user_agent,
                    'device_info': session.device_info,
                    'location': session.location,
                    'last_activity': session.last_activity,
                    'expires_at': session.expires_at,
                    'is_current': session.session_key == current_session_key,
                    'is_expired': session.is_expired(),
                    'device_name': self._get_device_name(session.user_agent),
                    'browser_name': self._get_browser_name(session.user_agent),
                    'location_display': self._get_location_display(session.location)
                }
                sessions_data.append(session_info)
            
            # Ordenar por última actividad
            sessions_data.sort(key=lambda x: x['last_activity'], reverse=True)
            
            # Estadísticas de sesiones
            session_stats = {
                'total_active': len(sessions_data),
                'current_session': current_session_key,
                'oldest_session': min(sessions_data, key=lambda x: x['last_activity'])['last_activity'] if sessions_data else None,
                'unique_ips': len(set(s['ip_address'] for s in sessions_data)),
                'unique_devices': len(set(s['device_name'] for s in sessions_data))
            }
            
            context.update({
                'title': 'Gestión de Sesiones',
                'sessions_data': sessions_data,
                'session_stats': session_stats,
                'current_session_key': current_session_key
            })
            
        except Exception as e:
            logger.error(f"Error loading sessions for {self.request.user.email}: {str(e)}")
            messages.error(self.request, 'Error cargando las sesiones. Intente nuevamente.')
            context.update({
                'title': 'Gestión de Sesiones',
                'sessions_data': [],
                'session_stats': {},
                'error': True
            })
        
        return context
    
    def _get_device_name(self, user_agent):
        """Extraer nombre del dispositivo del user agent"""
        if not user_agent:
            return 'Dispositivo Desconocido'
        
        user_agent_lower = user_agent.lower()
        
        if 'mobile' in user_agent_lower or 'android' in user_agent_lower:
            return 'Dispositivo Móvil'
        elif 'tablet' in user_agent_lower or 'ipad' in user_agent_lower:
            return 'Tablet'
        elif 'windows' in user_agent_lower:
            return 'PC Windows'
        elif 'mac' in user_agent_lower:
            return 'Mac'
        elif 'linux' in user_agent_lower:
            return 'PC Linux'
        else:
            return 'Dispositivo Desconocido'
    
    def _get_browser_name(self, user_agent):
        """Extraer nombre del navegador del user agent"""
        if not user_agent:
            return 'Navegador Desconocido'
        
        user_agent_lower = user_agent.lower()
        
        if 'chrome' in user_agent_lower:
            return 'Chrome'
        elif 'firefox' in user_agent_lower:
            return 'Firefox'
        elif 'safari' in user_agent_lower:
            return 'Safari'
        elif 'edge' in user_agent_lower:
            return 'Edge'
        elif 'opera' in user_agent_lower:
            return 'Opera'
        else:
            return 'Navegador Desconocido'
    
    def _get_location_display(self, location_data):
        """Formatear información de ubicación para mostrar"""
        if not location_data or not isinstance(location_data, dict):
            return 'Ubicación Desconocida'
        
        parts = []
        if location_data.get('city'):
            parts.append(location_data['city'])
        if location_data.get('country'):
            parts.append(location_data['country'])
        
        return ', '.join(parts) if parts else 'Ubicación Desconocida'


@login_required
@require_http_methods(["POST"])
def terminate_specific_session_view(request, session_key):
    """
    Vista para terminar una sesión específica.
    
    Args:
        session_key: Clave de la sesión a terminar
    """
    try:
        session_service = SessionService()
        
        # Verificar que la sesión pertenece al usuario actual
        session_info = session_service.get_session_info(session_key)
        
        if not session_info or session_info.get('agent_id') != request.user.id:
            return JsonResponse({
                'success': False,
                'error': 'Sesión no encontrada o no autorizada'
            }, status=404)
        
        # No permitir terminar la sesión actual
        if session_key == request.session.session_key:
            return JsonResponse({
                'success': False,
                'error': 'No puede terminar su sesión actual'
            }, status=400)
        
        # Terminar sesión
        success = session_service.terminate_session(
            session_key, 
            reason='user_terminated_specific'
        )
        
        if success:
            # Registrar acción
            AuditLog.objects.create(
                agent=request.user,
                action='session_terminated',
                resource_type='user_session',
                resource_id=session_key,
                ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1'),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                details={
                    'terminated_session': session_key,
                    'method': 'user_action'
                },
                success=True,
                session_key=request.session.session_key
            )
            
            return JsonResponse({
                'success': True,
                'message': 'Sesión terminada correctamente'
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Error terminando la sesión'
            }, status=500)
            
    except Exception as e:
        logger.error(f"Error terminating session {session_key} for {request.user.email}: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Error interno del servidor'
        }, status=500)


@login_required
@require_http_methods(["POST"])
def terminate_other_sessions_view(request):
    """
    Vista para terminar todas las sesiones excepto la actual.
    """
    try:
        session_service = SessionService()
        current_session = request.session.session_key
        
        # Terminar todas las sesiones excepto la actual
        terminated_count = session_service.terminate_all_sessions(
            request.user, 
            except_current=current_session,
            reason='user_terminated_others'
        )
        
        # Registrar acción
        AuditLog.objects.create(
            agent=request.user,
            action='sessions_terminated',
            resource_type='user_session',
            ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            details={
                'terminated_count': terminated_count,
                'kept_session': current_session,
                'method': 'user_action'
            },
            success=True,
            session_key=current_session
        )
        
        messages.success(
            request, 
            f'Se terminaron {terminated_count} sesiones activas.'
        )
        
        return JsonResponse({
            'success': True, 
            'message': f'{terminated_count} sesiones terminadas',
            'terminated_count': terminated_count
        })
        
    except Exception as e:
        logger.error(f"Error terminating other sessions for {request.user.email}: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Error interno del servidor'
        }, status=500)


@login_required
def profile_completion_data(request):
    """
    API para obtener datos de completitud del perfil.
    """
    try:
        user_service = UserManagementService()
        completion_data = user_service.get_profile_completion_details(request.user)
        
        return JsonResponse({
            'success': True,
            'completion_percentage': completion_data['percentage'],
            'completed_fields': completion_data['completed_fields'],
            'missing_fields': completion_data['missing_fields'],
            'recommendations': completion_data['recommendations']
        })
        
    except Exception as e:
        logger.error(f"Error getting profile completion for {request.user.email}: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Error obteniendo datos de completitud'
        }, status=500)