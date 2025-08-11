"""
Servicio de notificaciones por email para el sistema de usuarios.

Este servicio maneja el envío de emails relacionados con autenticación,
recuperación de contraseñas y notificaciones de seguridad.
"""

import logging
from typing import Dict, Any, Optional
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.urls import reverse
from django.utils import timezone

from agents.models import Agent, AuditLog


logger = logging.getLogger(__name__)


class EmailService:
    """
    Servicio para envío de emails del sistema de usuarios.
    
    Proporciona métodos para enviar diferentes tipos de notificaciones
    por email con templates HTML y texto plano.
    """
    
    def __init__(self):
        """Inicializa el servicio de email."""
        self.logger = logging.getLogger(f"{__name__}.EmailService")
        self.from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@sistema.com')
    
    def send_password_reset_email(self, agent: Agent, token: str, request) -> bool:
        """
        Envía email de recuperación de contraseña.
        
        Args:
            agent: Usuario que solicita el reset
            token: Token de recuperación
            request: Request HTTP para construir URLs absolutas
            
        Returns:
            bool: True si se envió correctamente
        """
        try:
            # Construir URL de reset
            reset_url = request.build_absolute_uri(
                reverse('agents:password_reset_confirm', kwargs={'token': token})
            )
            
            # Contexto para el template
            context = {
                'agent': agent,
                'reset_url': reset_url,
                'token': token,
                'site_name': getattr(settings, 'SITE_NAME', 'Sistema Inmobiliario'),
                'expires_hours': 24,
                'current_year': timezone.now().year
            }
            
            # Renderizar templates
            html_content = render_to_string('emails/password_reset.html', context)
            text_content = render_to_string('emails/password_reset.txt', context)
            
            # Crear email
            subject = f'Recuperación de contraseña - {context["site_name"]}'
            
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=self.from_email,
                to=[agent.email]
            )
            email.attach_alternative(html_content, "text/html")
            
            # Enviar email
            email.send()
            
            # Registrar envío
            self._log_email_sent(
                agent=agent,
                email_type='password_reset',
                recipient=agent.email,
                subject=subject,
                success=True
            )
            
            self.logger.info(f"Password reset email sent to: {agent.email}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error sending password reset email to {agent.email}: {str(e)}")
            
            # Registrar error
            self._log_email_sent(
                agent=agent,
                email_type='password_reset',
                recipient=agent.email,
                subject=subject if 'subject' in locals() else 'Password Reset',
                success=False,
                error=str(e)
            )
            
            return False
    
    def send_password_changed_notification(self, agent: Agent, ip_address: str = '127.0.0.1') -> bool:
        """
        Envía notificación de cambio de contraseña exitoso.
        
        Args:
            agent: Usuario que cambió la contraseña
            ip_address: IP desde donde se realizó el cambio
            
        Returns:
            bool: True si se envió correctamente
        """
        try:
            # Contexto para el template
            context = {
                'agent': agent,
                'ip_address': ip_address,
                'change_time': timezone.now(),
                'site_name': getattr(settings, 'SITE_NAME', 'Sistema Inmobiliario'),
                'current_year': timezone.now().year
            }
            
            # Renderizar templates
            html_content = render_to_string('emails/password_changed.html', context)
            text_content = render_to_string('emails/password_changed.txt', context)
            
            # Crear email
            subject = f'Contraseña cambiada - {context["site_name"]}'
            
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=self.from_email,
                to=[agent.email]
            )
            email.attach_alternative(html_content, "text/html")
            
            # Enviar email
            email.send()
            
            # Registrar envío
            self._log_email_sent(
                agent=agent,
                email_type='password_changed',
                recipient=agent.email,
                subject=subject,
                success=True
            )
            
            self.logger.info(f"Password changed notification sent to: {agent.email}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error sending password changed notification to {agent.email}: {str(e)}")
            
            # Registrar error
            self._log_email_sent(
                agent=agent,
                email_type='password_changed',
                recipient=agent.email,
                subject=subject if 'subject' in locals() else 'Password Changed',
                success=False,
                error=str(e)
            )
            
            return False
    
    def send_login_alert(self, agent: Agent, ip_address: str, user_agent: str, 
                        location: Optional[Dict[str, Any]] = None) -> bool:
        """
        Envía alerta de nuevo inicio de sesión.
        
        Args:
            agent: Usuario que inició sesión
            ip_address: IP del login
            user_agent: User agent del navegador
            location: Información de ubicación (opcional)
            
        Returns:
            bool: True si se envió correctamente
        """
        try:
            # Contexto para el template
            context = {
                'agent': agent,
                'ip_address': ip_address,
                'user_agent': user_agent,
                'location': location or {},
                'login_time': timezone.now(),
                'site_name': getattr(settings, 'SITE_NAME', 'Sistema Inmobiliario'),
                'current_year': timezone.now().year
            }
            
            # Renderizar templates
            html_content = render_to_string('emails/login_alert.html', context)
            text_content = render_to_string('emails/login_alert.txt', context)
            
            # Crear email
            subject = f'Nuevo inicio de sesión - {context["site_name"]}'
            
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=self.from_email,
                to=[agent.email]
            )
            email.attach_alternative(html_content, "text/html")
            
            # Enviar email
            email.send()
            
            # Registrar envío
            self._log_email_sent(
                agent=agent,
                email_type='login_alert',
                recipient=agent.email,
                subject=subject,
                success=True
            )
            
            self.logger.info(f"Login alert sent to: {agent.email}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error sending login alert to {agent.email}: {str(e)}")
            
            # Registrar error
            self._log_email_sent(
                agent=agent,
                email_type='login_alert',
                recipient=agent.email,
                subject=subject if 'subject' in locals() else 'Login Alert',
                success=False,
                error=str(e)
            )
            
            return False
    
    def send_suspicious_activity_alert(self, agent: Agent, activity_type: str, 
                                     details: Dict[str, Any]) -> bool:
        """
        Envía alerta de actividad sospechosa.
        
        Args:
            agent: Usuario relacionado con la actividad
            activity_type: Tipo de actividad sospechosa
            details: Detalles de la actividad
            
        Returns:
            bool: True si se envió correctamente
        """
        try:
            # Contexto para el template
            context = {
                'agent': agent,
                'activity_type': activity_type,
                'details': details,
                'alert_time': timezone.now(),
                'site_name': getattr(settings, 'SITE_NAME', 'Sistema Inmobiliario'),
                'current_year': timezone.now().year
            }
            
            # Renderizar templates
            html_content = render_to_string('emails/suspicious_activity.html', context)
            text_content = render_to_string('emails/suspicious_activity.txt', context)
            
            # Crear email
            subject = f'Alerta de seguridad - {context["site_name"]}'
            
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=self.from_email,
                to=[agent.email]
            )
            email.attach_alternative(html_content, "text/html")
            
            # Enviar email
            email.send()
            
            # Registrar envío
            self._log_email_sent(
                agent=agent,
                email_type='suspicious_activity',
                recipient=agent.email,
                subject=subject,
                success=True
            )
            
            self.logger.info(f"Suspicious activity alert sent to: {agent.email}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error sending suspicious activity alert to {agent.email}: {str(e)}")
            
            # Registrar error
            self._log_email_sent(
                agent=agent,
                email_type='suspicious_activity',
                recipient=agent.email,
                subject=subject if 'subject' in locals() else 'Security Alert',
                success=False,
                error=str(e)
            )
            
            return False
    
    def send_account_locked_notification(self, agent: Agent, reason: str, 
                                       unlock_time: Optional[timezone.datetime] = None) -> bool:
        """
        Envía notificación de cuenta bloqueada.
        
        Args:
            agent: Usuario cuya cuenta fue bloqueada
            reason: Razón del bloqueo
            unlock_time: Tiempo de desbloqueo automático (opcional)
            
        Returns:
            bool: True si se envió correctamente
        """
        try:
            # Contexto para el template
            context = {
                'agent': agent,
                'reason': reason,
                'unlock_time': unlock_time,
                'lock_time': timezone.now(),
                'site_name': getattr(settings, 'SITE_NAME', 'Sistema Inmobiliario'),
                'current_year': timezone.now().year
            }
            
            # Renderizar templates
            html_content = render_to_string('emails/account_locked.html', context)
            text_content = render_to_string('emails/account_locked.txt', context)
            
            # Crear email
            subject = f'Cuenta bloqueada - {context["site_name"]}'
            
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=self.from_email,
                to=[agent.email]
            )
            email.attach_alternative(html_content, "text/html")
            
            # Enviar email
            email.send()
            
            # Registrar envío
            self._log_email_sent(
                agent=agent,
                email_type='account_locked',
                recipient=agent.email,
                subject=subject,
                success=True
            )
            
            self.logger.info(f"Account locked notification sent to: {agent.email}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error sending account locked notification to {agent.email}: {str(e)}")
            
            # Registrar error
            self._log_email_sent(
                agent=agent,
                email_type='account_locked',
                recipient=agent.email,
                subject=subject if 'subject' in locals() else 'Account Locked',
                success=False,
                error=str(e)
            )
            
            return False
    
    def _log_email_sent(self, agent: Optional[Agent], email_type: str, recipient: str,
                       subject: str, success: bool, error: Optional[str] = None) -> None:
        """
        Registra el envío de email en el log de auditoría.
        
        Args:
            agent: Usuario relacionado
            email_type: Tipo de email enviado
            recipient: Destinatario del email
            subject: Asunto del email
            success: Si el envío fue exitoso
            error: Error si el envío falló
        """
        try:
            details = {
                'email_type': email_type,
                'recipient': recipient,
                'subject': subject,
                'timestamp': timezone.now().isoformat()
            }
            
            if error:
                details['error'] = error
            
            AuditLog.objects.create(
                agent=agent,
                action='email_sent',
                resource_type='notification',
                ip_address='127.0.0.1',  # Sistema interno
                user_agent='EmailService',
                details=details,
                success=success
            )
            
        except Exception as e:
            self.logger.error(f"Error logging email send: {str(e)}")
    
    def test_email_configuration(self) -> Dict[str, Any]:
        """
        Prueba la configuración de email del sistema.
        
        Returns:
            dict: Resultado de la prueba
        """
        try:
            # Intentar enviar un email de prueba
            test_subject = 'Prueba de configuración de email'
            test_message = 'Este es un email de prueba para verificar la configuración.'
            
            send_mail(
                subject=test_subject,
                message=test_message,
                from_email=self.from_email,
                recipient_list=[self.from_email],  # Enviar a sí mismo
                fail_silently=False
            )
            
            return {
                'success': True,
                'message': 'Configuración de email funcionando correctamente',
                'from_email': self.from_email
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Error en configuración de email: {str(e)}',
                'from_email': self.from_email
            }