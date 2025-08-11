"""
Vistas mejoradas de autenticación y gestión de usuarios.

Este módulo contiene las vistas actualizadas para login, logout,
recuperación de contraseñas y gestión de 2FA.
"""

import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse, HttpResponseRedirect
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect
from django.utils.decorators import method_decorator
from django.views.generic import FormView, TemplateView
from django.core.exceptions import ValidationError
from django.utils import timezone

from agents.models import Agent, UserProfile, SecuritySettings, AuditLog
from agents.forms import (
    EnhancedLoginForm, PasswordResetRequestForm, PasswordResetForm,
    EnhancedPasswordChangeForm
)
from agents.services.authentication_service import AuthenticationService
from agents.services.session_service import SessionService
from agents.services.user_management_service import UserManagementService
from agents.services.email_service import EmailService


logger = logging.getLogger(__name__)


class EnhancedLoginView(FormView):
    """
    Vista mejorada de login con soporte para 2FA y validaciones de seguridad.
    """
    template_name = 'agents/auth/login.html'
    form_class = EnhancedLoginForm
    success_url = reverse_lazy('agents:dashboard')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.auth_service = AuthenticationService()
        self.session_service = SessionService()
    
    def dispatch(self, request, *args, **kwargs):
        """Redirigir usuarios ya autenticados"""
        if request.user.is_authenticated:
            return redirect(self.success_url)
        return super().dispatch(request, *args, **kwargs)
    
    def get_form_kwargs(self):
        """Añadir request al formulario"""
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs
    
    def form_valid(self, form):
        """Procesar login exitoso"""
        try:
            user = form.get_user()
            
            if user:
                # Realizar login
                login(self.request, user)
                
                # Crear sesión en nuestro sistema
                self.session_service.create_session(user, self.request)
                
                # Registrar login exitoso
                AuditLog.objects.create(
                    agent=user,
                    action='login',
                    resource_type='authentication',
                    ip_address=self._get_client_ip(),
                    user_agent=self.request.META.get('HTTP_USER_AGENT', ''),
                    details={
                        'login_method': 'enhanced_form',
                        'remember_me': form.cleaned_data.get('remember_me', False)
                    },
                    success=True,
                    session_key=self.request.session.session_key
                )
                
                # Configurar duración de sesión si "recordarme" está marcado
                if form.cleaned_data.get('remember_me'):
                    self.request.session.set_expiry(60 * 60 * 24 * 30)  # 30 días
                
                messages.success(self.request, f'¡Bienvenido, {user.get_full_name()}!')
                
                # Redirigir a la URL solicitada o al dashboard
                next_url = self.request.GET.get('next', self.success_url)
                return HttpResponseRedirect(next_url)
            
            else:
                messages.error(self.request, 'Error en la autenticación. Intente nuevamente.')
                return self.form_invalid(form)
                
        except Exception as e:
            logger.error(f"Error en login: {str(e)}")
            messages.error(self.request, 'Error interno. Intente nuevamente.')
            return self.form_invalid(form)
    
    def form_invalid(self, form):
        """Procesar login fallido"""
        # Registrar intento fallido si hay email
        email = form.cleaned_data.get('email')
        if email:
            self.auth_service.handle_failed_login(
                email=email,
                ip_address=self._get_client_ip(),
                reason='form_validation_failed'
            )
        
        return super().form_invalid(form)
    
    def get_context_data(self, **kwargs):
        """Añadir contexto adicional"""
        context = super().get_context_data(**kwargs)
        context.update({
            'title': 'Iniciar Sesión',
            'show_2fa_help': True,
            'login_attempts_info': self._get_login_attempts_info()
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
    
    def _get_login_attempts_info(self):
        """Obtener información sobre intentos de login recientes"""
        try:
            recent_failures = AuditLog.objects.filter(
                action='login',
                success=False,
                ip_address=self._get_client_ip(),
                created_at__gte=timezone.now() - timezone.timedelta(hours=1)
            ).count()
            
            return {
                'recent_failures': recent_failures,
                'show_warning': recent_failures >= 3
            }
        except Exception:
            return {'recent_failures': 0, 'show_warning': False}


@login_required
def enhanced_logout_view(request):
    """
    Vista mejorada de logout con limpieza de sesiones.
    """
    try:
        user = request.user
        session_key = request.session.session_key
        
        # Terminar sesión en nuestro sistema
        session_service = SessionService()
        if session_key:
            session_service.terminate_session(session_key, reason='user_logout')
        
        # Registrar logout
        AuditLog.objects.create(
            agent=user,
            action='logout',
            resource_type='authentication',
            ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            details={'logout_method': 'manual'},
            success=True,
            session_key=session_key
        )
        
        # Realizar logout de Django
        logout(request)
        
        messages.info(request, 'Has cerrado sesión correctamente.')
        
    except Exception as e:
        logger.error(f"Error en logout: {str(e)}")
        logout(request)  # Asegurar logout incluso si hay error
        messages.warning(request, 'Sesión cerrada.')
    
    return redirect('agents:login')


class PasswordResetRequestView(FormView):
    """
    Vista para solicitar recuperación de contraseña.
    """
    template_name = 'agents/auth/password_reset_request.html'
    form_class = PasswordResetRequestForm
    success_url = reverse_lazy('agents:password_reset_sent')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.auth_service = AuthenticationService()
    
    def form_valid(self, form):
        """Procesar solicitud de reset"""
        email = form.cleaned_data['email']
        
        try:
            # Buscar usuario
            try:
                agent = Agent.objects.get(email=email, is_active=True)
                
                # Generar token de recuperación
                token = self.auth_service.generate_password_reset_token(agent)
                
                # Enviar email (implementar según necesidades)
                self._send_password_reset_email(agent, token)
                
                logger.info(f"Password reset requested for: {email}")
                
            except Agent.DoesNotExist:
                # Por seguridad, no revelar si el email existe
                logger.warning(f"Password reset requested for non-existent email: {email}")
            
            # Siempre mostrar mensaje de éxito por seguridad
            messages.success(
                self.request,
                'Si el email existe en nuestro sistema, recibirás instrucciones para recuperar tu contraseña.'
            )
            
        except Exception as e:
            logger.error(f"Error in password reset request: {str(e)}")
            messages.error(self.request, 'Error procesando la solicitud. Intente nuevamente.')
            return self.form_invalid(form)
        
        return super().form_valid(form)
    
    def _send_password_reset_email(self, agent, token):
        """
        Enviar email de recuperación de contraseña.
        
        Args:
            agent: Usuario para enviar email
            token: Token de recuperación
        """
        try:
            email_service = EmailService()
            success = email_service.send_password_reset_email(agent, token, self.request)
            
            if success:
                logger.info(f"Password reset email sent successfully to: {agent.email}")
            else:
                logger.warning(f"Failed to send password reset email to: {agent.email}")
            
        except Exception as e:
            logger.error(f"Error sending password reset email: {str(e)}")


class PasswordResetConfirmView(FormView):
    """
    Vista para confirmar reset de contraseña con token.
    """
    template_name = 'agents/auth/password_reset_confirm.html'
    form_class = PasswordResetForm
    success_url = reverse_lazy('agents:login')
    
    def dispatch(self, request, *args, **kwargs):
        """Validar token antes de mostrar formulario"""
        self.token = kwargs.get('token')
        
        try:
            # Buscar usuario con token válido
            profile = UserProfile.objects.get(
                password_reset_token=self.token,
                password_reset_expires__gt=timezone.now()
            )
            self.agent = profile.agent
            
        except UserProfile.DoesNotExist:
            messages.error(request, 'El enlace de recuperación es inválido o ha expirado.')
            return redirect('agents:password_reset_request')
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_form_kwargs(self):
        """Añadir usuario al formulario"""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.agent
        return kwargs
    
    def form_valid(self, form):
        """Procesar cambio de contraseña"""
        try:
            # Cambiar contraseña
            form.save()
            
            # Limpiar token de reset
            profile = self.agent.profile
            profile.password_reset_token = None
            profile.password_reset_expires = None
            profile.save()
            
            # Actualizar configuraciones de seguridad
            security_settings, _ = SecuritySettings.objects.get_or_create(agent=self.agent)
            security_settings.password_changed_at = timezone.now()
            security_settings.require_password_change = False
            security_settings.save()
            
            # Terminar todas las sesiones activas por seguridad
            session_service = SessionService()
            session_service.terminate_all_sessions(self.agent)
            
            # Registrar cambio de contraseña
            AuditLog.objects.create(
                agent=self.agent,
                action='password_change',
                resource_type='authentication',
                ip_address=self.request.META.get('REMOTE_ADDR', '127.0.0.1'),
                user_agent=self.request.META.get('HTTP_USER_AGENT', ''),
                details={'method': 'password_reset'},
                success=True
            )
            
            messages.success(
                self.request,
                'Tu contraseña ha sido cambiada exitosamente. Por favor, inicia sesión con tu nueva contraseña.'
            )
            
            logger.info(f"Password reset completed for: {self.agent.email}")
            
        except Exception as e:
            logger.error(f"Error in password reset confirm: {str(e)}")
            messages.error(self.request, 'Error cambiando la contraseña. Intente nuevamente.')
            return self.form_invalid(form)
        
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        """Añadir contexto adicional"""
        context = super().get_context_data(**kwargs)
        context.update({
            'title': 'Cambiar Contraseña',
            'agent': self.agent
        })
        return context


class PasswordResetSentView(TemplateView):
    """
    Vista de confirmación de envío de email de reset.
    """
    template_name = 'agents/auth/password_reset_sent.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Email Enviado'
        return context


@login_required
def change_password_view(request):
    """
    Vista para cambio de contraseña por parte del usuario autenticado.
    """
    if request.method == 'POST':
        form = EnhancedPasswordChangeForm(user=request.user, data=request.POST)
        
        if form.is_valid():
            try:
                # Cambiar contraseña
                form.save()
                
                # Actualizar configuraciones de seguridad
                security_settings, _ = SecuritySettings.objects.get_or_create(agent=request.user)
                security_settings.password_changed_at = timezone.now()
                security_settings.require_password_change = False
                security_settings.save()
                
                # Registrar cambio
                AuditLog.objects.create(
                    agent=request.user,
                    action='password_change',
                    resource_type='authentication',
                    ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1'),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    details={'method': 'user_initiated'},
                    success=True,
                    session_key=request.session.session_key
                )
                
                # Enviar notificación por email
                try:
                    email_service = EmailService()
                    email_service.send_password_changed_notification(
                        request.user, 
                        request.META.get('REMOTE_ADDR', '127.0.0.1')
                    )
                except Exception as e:
                    logger.warning(f"Failed to send password change notification: {str(e)}")
                
                messages.success(request, 'Tu contraseña ha sido cambiada exitosamente.')
                return redirect('agents:profile')
                
            except Exception as e:
                logger.error(f"Error changing password for {request.user.email}: {str(e)}")
                messages.error(request, 'Error cambiando la contraseña. Intente nuevamente.')
    else:
        form = EnhancedPasswordChangeForm(user=request.user)
    
    return render(request, 'agents/auth/change_password.html', {
        'form': form,
        'title': 'Cambiar Contraseña'
    })


@login_required
@require_http_methods(["POST"])
def terminate_session_view(request, session_key):
    """
    Vista para terminar una sesión específica.
    """
    try:
        session_service = SessionService()
        
        # Verificar que la sesión pertenece al usuario actual
        session_info = session_service.get_session_info(session_key)
        
        if not session_info or session_info['agent']['id'] != request.user.id:
            return JsonResponse({'error': 'Sesión no encontrada'}, status=404)
        
        # Terminar sesión
        success = session_service.terminate_session(session_key, reason='user_terminated')
        
        if success:
            return JsonResponse({'success': True, 'message': 'Sesión terminada'})
        else:
            return JsonResponse({'error': 'Error terminando sesión'}, status=500)
            
    except Exception as e:
        logger.error(f"Error terminating session {session_key}: {str(e)}")
        return JsonResponse({'error': 'Error interno'}, status=500)


@login_required
@require_http_methods(["POST"])
def terminate_all_sessions_view(request):
    """
    Vista para terminar todas las sesiones del usuario.
    """
    try:
        session_service = SessionService()
        current_session = request.session.session_key
        
        # Terminar todas las sesiones excepto la actual
        terminated_count = session_service.terminate_all_sessions(
            request.user, 
            except_current=current_session
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
        logger.error(f"Error terminating all sessions for {request.user.email}: {str(e)}")
        return JsonResponse({'error': 'Error interno'}, status=500)