"""
Servicio para autenticación y seguridad de usuarios.

Este servicio maneja todas las operaciones relacionadas con la autenticación,
incluyendo login, recuperación de contraseñas, 2FA y detección de actividad sospechosa.
"""

import logging
import secrets
import hashlib
import pyotp
import qrcode
from io import BytesIO
import base64
from typing import Tuple, Dict, Any, Optional
from datetime import timedelta

from django.contrib.auth import authenticate
from django.core.mail import send_mail
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.conf import settings
from django.template.loader import render_to_string

from agents.models import Agent, UserProfile, SecuritySettings, AuditLog


logger = logging.getLogger(__name__)


class AuthenticationService:
    """
    Servicio para autenticación y seguridad.
    
    Maneja autenticación de usuarios, recuperación de contraseñas,
    autenticación de dos factores y detección de actividad sospechosa.
    """
    
    def __init__(self):
        """Inicializa el servicio de autenticación."""
        self.logger = logging.getLogger(f"{__name__}.AuthenticationService")
    
    def authenticate_user(self, email: str, password: str, request, two_factor_code: str = None) -> Tuple[Agent, Dict[str, Any]]:
        """
        Autentica usuario con validaciones de seguridad completas.
        
        Args:
            email: Email del usuario
            password: Contraseña del usuario
            request: Request HTTP para obtener IP y user agent
            two_factor_code: Código de 2FA si está habilitado
            
        Returns:
            Tuple[Agent, Dict]: Usuario autenticado y información adicional
            
        Raises:
            ValidationError: Si la autenticación falla
        """
        try:
            # Obtener información del request
            ip_address = self._get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')
            
            # Buscar usuario por email
            try:
                agent = Agent.objects.get(email=email)
            except Agent.DoesNotExist:
                self._log_failed_login(email, ip_address, user_agent, 'user_not_found')
                raise ValidationError("Credenciales inválidas")
            
            # Verificar si la cuenta está activa
            if not agent.is_active:
                self._log_failed_login(email, ip_address, user_agent, 'account_inactive')
                raise ValidationError("Cuenta inactiva")
            
            # Obtener configuraciones de seguridad
            security_settings, _ = SecuritySettings.objects.get_or_create(agent=agent)
            
            # Verificar si la cuenta está bloqueada
            if security_settings.is_locked():
                self._log_failed_login(email, ip_address, user_agent, 'account_locked')
                raise ValidationError("Cuenta bloqueada temporalmente")
            
            # Verificar contraseña
            user = authenticate(request, email=email, password=password)
            if user is None:
                security_settings.increment_login_attempts()
                self._log_failed_login(email, ip_address, user_agent, 'invalid_password')
                raise ValidationError("Credenciales inválidas")
            
            # Verificar 2FA si está habilitado
            profile, _ = UserProfile.objects.get_or_create(agent=agent)
            if profile.two_factor_enabled:
                if not two_factor_code:
                    return agent, {
                        'requires_2fa': True,
                        'message': 'Código de autenticación de dos factores requerido'
                    }
                
                if not self.verify_two_factor_code(agent, two_factor_code):
                    security_settings.increment_login_attempts()
                    self._log_failed_login(email, ip_address, user_agent, 'invalid_2fa')
                    raise ValidationError("Código de autenticación inválido")
            
            # Detectar actividad sospechosa
            if self.detect_suspicious_activity(agent, request):
                self._log_suspicious_activity(agent, ip_address, user_agent, 'unusual_login_pattern')
                if security_settings.suspicious_activity_alerts:
                    self._send_security_alert(agent, 'suspicious_login', {
                        'ip_address': ip_address,
                        'user_agent': user_agent,
                        'timestamp': timezone.now()
                    })
            
            # Login exitoso - resetear intentos fallidos
            security_settings.reset_login_attempts()
            
            # Actualizar último login
            agent.last_login = timezone.now()
            agent.save()
            
            # Registrar login exitoso
            self._log_successful_login(agent, ip_address, user_agent)
            
            self.logger.info(f"Login exitoso para usuario: {email}")
            
            return agent, {
                'success': True,
                'message': 'Autenticación exitosa'
            }
            
        except ValidationError:
            raise
        except Exception as e:
            self.logger.error(f"Error en autenticación para {email}: {str(e)}")
            raise ValidationError("Error interno del servidor")
    
    def handle_failed_login(self, email: str, ip_address: str, reason: str = 'unknown') -> bool:
        """
        Maneja intentos fallidos de login.
        
        Args:
            email: Email del usuario
            ip_address: Dirección IP del intento
            reason: Razón del fallo
            
        Returns:
            bool: True si se manejó correctamente
        """
        try:
            # Buscar usuario
            try:
                agent = Agent.objects.get(email=email)
                security_settings, _ = SecuritySettings.objects.get_or_create(agent=agent)
                security_settings.increment_login_attempts()
            except Agent.DoesNotExist:
                # Usuario no existe, pero registrar intento
                pass
            
            # Registrar en auditoría
            AuditLog.objects.create(
                agent=agent if 'agent' in locals() else None,
                action='login',
                resource_type='authentication',
                ip_address=ip_address,
                user_agent='Unknown',
                details={'reason': reason, 'email': email},
                success=False
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error manejando login fallido para {email}: {str(e)}")
            return False
    
    def generate_password_reset_token(self, agent: Agent) -> str:
        """
        Genera token para recuperación de contraseña.
        
        Args:
            agent: Usuario para generar token
            
        Returns:
            str: Token de recuperación
        """
        try:
            # Generar token seguro
            token = secrets.token_urlsafe(32)
            
            # Guardar token en el perfil con expiración
            profile, _ = UserProfile.objects.get_or_create(agent=agent)
            profile.password_reset_token = token
            profile.password_reset_expires = timezone.now() + timedelta(hours=1)
            profile.save()
            
            # Actualizar configuraciones de seguridad
            security_settings, _ = SecuritySettings.objects.get_or_create(agent=agent)
            security_settings.last_password_reset = timezone.now()
            security_settings.save()
            
            # Registrar en auditoría
            AuditLog.objects.create(
                agent=agent,
                action='password_reset_requested',
                resource_type='authentication',
                ip_address='127.0.0.1',  # Sistema interno
                user_agent='System',
                details={'token_generated': True},
                success=True
            )
            
            self.logger.info(f"Token de recuperación generado para: {agent.email}")
            return token
            
        except Exception as e:
            self.logger.error(f"Error generando token de recuperación para {agent.email}: {str(e)}")
            raise
    
    def setup_two_factor_auth(self, agent: Agent) -> Dict[str, Any]:
        """
        Configura autenticación de dos factores para el usuario.
        
        Args:
            agent: Usuario para configurar 2FA
            
        Returns:
            dict: Información de configuración de 2FA
        """
        try:
            profile, _ = UserProfile.objects.get_or_create(agent=agent)
            
            # Generar secreto para 2FA
            secret = pyotp.random_base32()
            profile.two_factor_secret = secret
            profile.save()
            
            # Generar códigos de respaldo
            backup_codes = profile.generate_backup_codes()
            
            # Crear URL para código QR
            totp = pyotp.TOTP(secret)
            provisioning_uri = totp.provisioning_uri(
                name=agent.email,
                issuer_name=getattr(settings, 'SITE_NAME', 'Real Estate Management')
            )
            
            # Generar código QR
            qr_code_data = self._generate_qr_code(provisioning_uri)
            
            # Registrar en auditoría
            AuditLog.objects.create(
                agent=agent,
                action='2fa_setup_initiated',
                resource_type='security',
                ip_address='127.0.0.1',
                user_agent='System',
                details={'secret_generated': True},
                success=True
            )
            
            self.logger.info(f"2FA configurado para usuario: {agent.email}")
            
            return {
                'secret': secret,
                'qr_code': qr_code_data,
                'backup_codes': backup_codes,
                'provisioning_uri': provisioning_uri
            }
            
        except Exception as e:
            self.logger.error(f"Error configurando 2FA para {agent.email}: {str(e)}")
            raise
    
    def verify_two_factor_code(self, agent: Agent, code: str) -> bool:
        """
        Verifica código de autenticación de dos factores.
        
        Args:
            agent: Usuario para verificar código
            code: Código a verificar
            
        Returns:
            bool: True si el código es válido
        """
        try:
            profile = agent.profile
            
            if not profile.two_factor_enabled or not profile.two_factor_secret:
                return False
            
            # Verificar código TOTP
            totp = pyotp.TOTP(profile.two_factor_secret)
            if totp.verify(code, valid_window=1):  # Ventana de 30 segundos
                return True
            
            # Verificar código de respaldo
            if profile.use_backup_code(code):
                # Registrar uso de código de respaldo
                AuditLog.objects.create(
                    agent=agent,
                    action='backup_code_used',
                    resource_type='security',
                    ip_address='127.0.0.1',
                    user_agent='System',
                    details={'backup_code_used': True},
                    success=True
                )
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error verificando código 2FA para {agent.email}: {str(e)}")
            return False
    
    def detect_suspicious_activity(self, agent: Agent, request) -> bool:
        """
        Detecta actividad sospechosa basada en patrones de uso.
        
        Args:
            agent: Usuario a verificar
            request: Request HTTP
            
        Returns:
            bool: True si se detecta actividad sospechosa
        """
        try:
            ip_address = self._get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')
            
            # Obtener sesiones recientes
            from agents.models import UserSession
            recent_sessions = UserSession.objects.filter(
                agent=agent,
                created_at__gte=timezone.now() - timedelta(days=7)
            ).order_by('-created_at')[:10]
            
            suspicious_indicators = []
            
            # Verificar IP inusual
            recent_ips = set(session.ip_address for session in recent_sessions)
            if ip_address not in recent_ips and len(recent_ips) > 0:
                suspicious_indicators.append('unusual_ip')
            
            # Verificar user agent inusual
            recent_user_agents = set(session.user_agent for session in recent_sessions)
            if user_agent not in recent_user_agents and len(recent_user_agents) > 0:
                suspicious_indicators.append('unusual_user_agent')
            
            # Verificar múltiples intentos de login recientes
            recent_failed_logins = AuditLog.objects.filter(
                agent=agent,
                action='login',
                success=False,
                created_at__gte=timezone.now() - timedelta(hours=1)
            ).count()
            
            if recent_failed_logins >= 3:
                suspicious_indicators.append('multiple_failed_attempts')
            
            # Verificar login fuera de horario habitual
            current_hour = timezone.now().hour
            usual_hours = set()
            for session in recent_sessions:
                usual_hours.add(session.created_at.hour)
            
            if usual_hours and current_hour not in usual_hours:
                # Solo considerar sospechoso si es muy fuera del rango habitual
                min_hour = min(usual_hours)
                max_hour = max(usual_hours)
                if current_hour < min_hour - 3 or current_hour > max_hour + 3:
                    suspicious_indicators.append('unusual_time')
            
            # Considerar sospechoso si hay 2 o más indicadores
            is_suspicious = len(suspicious_indicators) >= 2
            
            if is_suspicious:
                self.logger.warning(f"Actividad sospechosa detectada para {agent.email}: {suspicious_indicators}")
            
            return is_suspicious
            
        except Exception as e:
            self.logger.error(f"Error detectando actividad sospechosa para {agent.email}: {str(e)}")
            return False
    
    def _get_client_ip(self, request) -> str:
        """Extrae la IP del cliente del request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '127.0.0.1')
        return ip
    
    def _generate_qr_code(self, data: str) -> str:
        """
        Genera código QR en formato base64.
        
        Args:
            data: Datos para el código QR
            
        Returns:
            str: Código QR en base64
        """
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        qr_code_data = base64.b64encode(buffer.getvalue()).decode()
        return f"data:image/png;base64,{qr_code_data}"
    
    def _log_successful_login(self, agent: Agent, ip_address: str, user_agent: str):
        """Registra login exitoso en auditoría."""
        AuditLog.objects.create(
            agent=agent,
            action='login',
            resource_type='authentication',
            ip_address=ip_address,
            user_agent=user_agent,
            details={'login_method': 'email'},
            success=True
        )
    
    def _log_failed_login(self, email: str, ip_address: str, user_agent: str, reason: str):
        """Registra login fallido en auditoría."""
        try:
            agent = Agent.objects.get(email=email)
        except Agent.DoesNotExist:
            agent = None
        
        AuditLog.objects.create(
            agent=agent,
            action='login',
            resource_type='authentication',
            ip_address=ip_address,
            user_agent=user_agent,
            details={'reason': reason, 'email': email},
            success=False
        )
    
    def _log_suspicious_activity(self, agent: Agent, ip_address: str, user_agent: str, reason: str):
        """Registra actividad sospechosa en auditoría."""
        AuditLog.objects.create(
            agent=agent,
            action='suspicious_activity',
            resource_type='security',
            ip_address=ip_address,
            user_agent=user_agent,
            details={'reason': reason},
            success=True
        )
    
    def _send_security_alert(self, agent: Agent, alert_type: str, context: Dict[str, Any]):
        """
        Envía alerta de seguridad por email.
        
        Args:
            agent: Usuario para enviar alerta
            alert_type: Tipo de alerta
            context: Contexto adicional para la alerta
        """
        try:
            subject = f"Alerta de Seguridad - {alert_type}"
            
            # Renderizar template de email
            html_message = render_to_string('emails/security_alert.html', {
                'agent': agent,
                'alert_type': alert_type,
                'context': context
            })
            
            send_mail(
                subject=subject,
                message=f"Alerta de seguridad para su cuenta: {alert_type}",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[agent.email],
                html_message=html_message,
                fail_silently=False
            )
            
            self.logger.info(f"Alerta de seguridad enviada a {agent.email}: {alert_type}")
            
        except Exception as e:
            self.logger.error(f"Error enviando alerta de seguridad a {agent.email}: {str(e)}")
    
    def enable_two_factor_auth(self, agent: Agent, verification_code: str) -> bool:
        """
        Habilita 2FA después de verificar el código de configuración.
        
        Args:
            agent: Usuario para habilitar 2FA
            verification_code: Código de verificación
            
        Returns:
            bool: True si se habilitó correctamente
        """
        try:
            profile = agent.profile
            
            if not profile.two_factor_secret:
                raise ValidationError("2FA no está configurado")
            
            # Verificar código
            totp = pyotp.TOTP(profile.two_factor_secret)
            if not totp.verify(verification_code, valid_window=1):
                return False
            
            # Habilitar 2FA
            profile.two_factor_enabled = True
            profile.save()
            
            # Registrar en auditoría
            AuditLog.objects.create(
                agent=agent,
                action='2fa_enabled',
                resource_type='security',
                ip_address='127.0.0.1',
                user_agent='System',
                details={'enabled': True},
                success=True
            )
            
            self.logger.info(f"2FA habilitado para usuario: {agent.email}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error habilitando 2FA para {agent.email}: {str(e)}")
            return False
    
    def disable_two_factor_auth(self, agent: Agent, password: str) -> bool:
        """
        Deshabilita 2FA después de verificar la contraseña.
        
        Args:
            agent: Usuario para deshabilitar 2FA
            password: Contraseña del usuario
            
        Returns:
            bool: True si se deshabilitó correctamente
        """
        try:
            # Verificar contraseña
            if not agent.check_password(password):
                return False
            
            profile = agent.profile
            profile.two_factor_enabled = False
            profile.two_factor_secret = None
            profile.backup_codes = []
            profile.save()
            
            # Registrar en auditoría
            AuditLog.objects.create(
                agent=agent,
                action='2fa_disabled',
                resource_type='security',
                ip_address='127.0.0.1',
                user_agent='System',
                details={'disabled': True},
                success=True
            )
            
            self.logger.info(f"2FA deshabilitado para usuario: {agent.email}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error deshabilitando 2FA para {agent.email}: {str(e)}")
            return False