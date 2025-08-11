"""
Middleware de seguridad para validaciones y monitoreo.

Este middleware maneja validaciones de seguridad en tiempo real,
incluyendo validación de IP, detección de actividad sospechosa
y actualización de sesiones.
"""

import logging
import time
from typing import Optional
from django.utils.deprecation import MiddlewareMixin
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.contrib.auth import logout
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from agents.models import Agent, SecuritySettings, UserSession, AuditLog
from agents.services.authentication_service import AuthenticationService


logger = logging.getLogger(__name__)


class SecurityMiddleware(MiddlewareMixin):
    """
    Middleware para validaciones de seguridad.
    
    Realiza validaciones de seguridad en cada request, incluyendo:
    - Validación de IP permitidas
    - Detección de actividad sospechosa
    - Actualización de sesiones
    - Bloqueo de cuentas comprometidas
    """
    
    def __init__(self, get_response=None):
        """Inicializa el middleware de seguridad."""
        super().__init__(get_response)
        self.logger = logging.getLogger(f"{__name__}.SecurityMiddleware")
        self.auth_service = AuthenticationService()
        
        # URLs que no requieren validación de seguridad
        self.exempt_urls = [
            '/agents/login/',
            '/agents/logout/',
            '/public/',
            '/static/',
            '/media/',
            '/admin/login/',
        ]
        
        # URLs críticas que requieren validación extra
        self.critical_urls = [
            '/admin/',
            '/agents/create/',
            '/agents/delete/',
            '/settings/',
        ]
    
    def process_request(self, request):
        """
        Procesa el request entrante y aplica validaciones de seguridad.
        
        Args:
            request: HttpRequest object
            
        Returns:
            HttpResponse o None
        """
        try:
            # Obtener información del request
            ip_address = self._get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')
            path = request.path
            
            # Registrar información del request para logging
            request.security_info = {
                'ip_address': ip_address,
                'user_agent': user_agent,
                'start_time': time.time(),
                'path': path
            }
            
            # Verificar si la URL está exenta de validaciones
            if self._is_exempt_url(path):
                return None
            
            # Solo aplicar validaciones a usuarios autenticados
            if not request.user.is_authenticated:
                return None
            
            # Obtener configuraciones de seguridad del usuario
            try:
                security_settings = request.user.security_settings
            except SecuritySettings.DoesNotExist:
                # Crear configuraciones por defecto si no existen
                security_settings = SecuritySettings.objects.create(agent=request.user)
            
            # Verificar si la cuenta está bloqueada
            if security_settings.is_locked():
                return self._handle_locked_account(request)
            
            # Validar IP permitidas si están configuradas
            if security_settings.allowed_ip_addresses:
                if not self._validate_ip_address(ip_address, security_settings.allowed_ip_addresses):
                    return self._handle_unauthorized_ip(request, ip_address)
            
            # Detectar actividad sospechosa
            if self._is_critical_url(path):
                if self.auth_service.detect_suspicious_activity(request.user, request):
                    return self._handle_suspicious_activity(request)
            
            # Actualizar sesión si existe
            self._update_user_session(request)
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error en SecurityMiddleware: {str(e)}")
            # En caso de error, permitir que el request continúe
            return None
    
    def process_response(self, request, response):
        """
        Procesa la respuesta y registra información de seguridad.
        
        Args:
            request: HttpRequest object
            response: HttpResponse object
            
        Returns:
            HttpResponse: Response object
        """
        try:
            # Calcular duración del request
            if hasattr(request, 'security_info'):
                duration = time.time() - request.security_info['start_time']
                
                # Registrar requests lentos como posible indicador de ataque
                if duration > 10.0:  # 10 segundos
                    self._log_slow_request(request, duration, response.status_code)
                
                # Registrar acceso a URLs críticas
                if (request.user.is_authenticated and 
                    self._is_critical_url(request.security_info['path'])):
                    self._log_critical_access(request, response.status_code)
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error en process_response de SecurityMiddleware: {str(e)}")
            return response
    
    def process_exception(self, request, exception):
        """
        Procesa excepciones y registra posibles ataques.
        
        Args:
            request: HttpRequest object
            exception: Exception que ocurrió
        """
        try:
            if hasattr(request, 'security_info') and request.user.is_authenticated:
                # Registrar excepción como posible intento de ataque
                AuditLog.objects.create(
                    agent=request.user,
                    action='security_exception',
                    resource_type='security',
                    ip_address=request.security_info['ip_address'],
                    user_agent=request.security_info['user_agent'],
                    details={
                        'exception_type': type(exception).__name__,
                        'exception_message': str(exception),
                        'path': request.security_info['path']
                    },
                    success=False
                )
                
                self.logger.warning(
                    f"Security exception for user {request.user.email}: {type(exception).__name__}"
                )
            
        except Exception as e:
            self.logger.error(f"Error en process_exception de SecurityMiddleware: {str(e)}")
        
        return None  # Permitir que Django maneje la excepción normalmente
    
    def _get_client_ip(self, request) -> str:
        """
        Extrae la IP del cliente del request.
        
        Args:
            request: HttpRequest object
            
        Returns:
            str: Dirección IP del cliente
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '127.0.0.1')
        return ip
    
    def _is_exempt_url(self, path: str) -> bool:
        """
        Verifica si una URL está exenta de validaciones de seguridad.
        
        Args:
            path: Path de la URL
            
        Returns:
            bool: True si está exenta
        """
        return any(path.startswith(exempt_url) for exempt_url in self.exempt_urls)
    
    def _is_critical_url(self, path: str) -> bool:
        """
        Verifica si una URL es crítica y requiere validación extra.
        
        Args:
            path: Path de la URL
            
        Returns:
            bool: True si es crítica
        """
        return any(path.startswith(critical_url) for critical_url in self.critical_urls)
    
    def _validate_ip_address(self, ip_address: str, allowed_ips: list) -> bool:
        """
        Valida si una IP está en la lista de IPs permitidas.
        
        Args:
            ip_address: IP a validar
            allowed_ips: Lista de IPs permitidas
            
        Returns:
            bool: True si está permitida
        """
        try:
            # Verificar IP exacta
            if ip_address in allowed_ips:
                return True
            
            # Verificar rangos de IP (implementación básica)
            for allowed_ip in allowed_ips:
                if '*' in allowed_ip:
                    # Soporte básico para wildcards (ej: 192.168.1.*)
                    pattern = allowed_ip.replace('*', '')
                    if ip_address.startswith(pattern):
                        return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error validando IP {ip_address}: {str(e)}")
            return True  # En caso de error, permitir acceso
    
    def _handle_locked_account(self, request) -> HttpResponse:
        """
        Maneja el acceso de una cuenta bloqueada.
        
        Args:
            request: HttpRequest object
            
        Returns:
            HttpResponse: Respuesta de cuenta bloqueada
        """
        try:
            # Cerrar sesión del usuario
            logout(request)
            
            # Registrar intento de acceso con cuenta bloqueada
            AuditLog.objects.create(
                agent=request.user if request.user.is_authenticated else None,
                action='locked_account_access',
                resource_type='security',
                ip_address=request.security_info['ip_address'],
                user_agent=request.security_info['user_agent'],
                details={'path': request.security_info['path']},
                success=False
            )
            
            # Respuesta según el tipo de request
            if request.headers.get('Accept', '').startswith('application/json'):
                return JsonResponse({
                    'error': 'account_locked',
                    'message': 'Su cuenta está temporalmente bloqueada por seguridad.'
                }, status=403)
            else:
                messages.error(request, 'Su cuenta está temporalmente bloqueada por seguridad.')
                return redirect('agents:login')
                
        except Exception as e:
            self.logger.error(f"Error manejando cuenta bloqueada: {str(e)}")
            return redirect('agents:login')
    
    def _handle_unauthorized_ip(self, request, ip_address: str) -> HttpResponse:
        """
        Maneja el acceso desde una IP no autorizada.
        
        Args:
            request: HttpRequest object
            ip_address: IP no autorizada
            
        Returns:
            HttpResponse: Respuesta de IP no autorizada
        """
        try:
            # Registrar intento de acceso desde IP no autorizada
            AuditLog.objects.create(
                agent=request.user,
                action='unauthorized_ip_access',
                resource_type='security',
                ip_address=ip_address,
                user_agent=request.security_info['user_agent'],
                details={
                    'path': request.security_info['path'],
                    'unauthorized_ip': ip_address
                },
                success=False
            )
            
            # Enviar alerta de seguridad si está habilitada
            try:
                security_settings = request.user.security_settings
                if security_settings.suspicious_activity_alerts:
                    self.auth_service._send_security_alert(
                        request.user,
                        'unauthorized_ip',
                        {
                            'ip_address': ip_address,
                            'timestamp': timezone.now(),
                            'path': request.security_info['path']
                        }
                    )
            except Exception:
                pass  # No fallar si no se puede enviar la alerta
            
            # Cerrar sesión por seguridad
            logout(request)
            
            # Respuesta según el tipo de request
            if request.headers.get('Accept', '').startswith('application/json'):
                return JsonResponse({
                    'error': 'unauthorized_ip',
                    'message': 'Acceso denegado desde esta ubicación.'
                }, status=403)
            else:
                messages.error(request, 'Acceso denegado desde esta ubicación por seguridad.')
                return redirect('agents:login')
                
        except Exception as e:
            self.logger.error(f"Error manejando IP no autorizada: {str(e)}")
            return redirect('agents:login')
    
    def _handle_suspicious_activity(self, request) -> Optional[HttpResponse]:
        """
        Maneja la detección de actividad sospechosa.
        
        Args:
            request: HttpRequest object
            
        Returns:
            HttpResponse o None
        """
        try:
            # Registrar actividad sospechosa
            AuditLog.objects.create(
                agent=request.user,
                action='suspicious_activity_detected',
                resource_type='security',
                ip_address=request.security_info['ip_address'],
                user_agent=request.security_info['user_agent'],
                details={
                    'path': request.security_info['path'],
                    'detection_reason': 'middleware_detection'
                },
                success=True
            )
            
            # Enviar alerta si está habilitada
            try:
                security_settings = request.user.security_settings
                if security_settings.suspicious_activity_alerts:
                    self.auth_service._send_security_alert(
                        request.user,
                        'suspicious_activity',
                        {
                            'ip_address': request.security_info['ip_address'],
                            'timestamp': timezone.now(),
                            'path': request.security_info['path']
                        }
                    )
            except Exception:
                pass
            
            # Para URLs críticas, requerir reautenticación
            if self._is_critical_url(request.security_info['path']):
                if request.headers.get('Accept', '').startswith('application/json'):
                    return JsonResponse({
                        'error': 'reauthentication_required',
                        'message': 'Se requiere reautenticación por seguridad.'
                    }, status=401)
                else:
                    messages.warning(request, 'Se detectó actividad inusual. Por favor, inicie sesión nuevamente.')
                    logout(request)
                    return redirect('agents:login')
            
            # Para otras URLs, solo registrar y continuar
            return None
            
        except Exception as e:
            self.logger.error(f"Error manejando actividad sospechosa: {str(e)}")
            return None
    
    def _update_user_session(self, request):
        """
        Actualiza la información de la sesión del usuario.
        
        Args:
            request: HttpRequest object
        """
        try:
            if not hasattr(request, 'session') or not request.session.session_key:
                return
            
            # Buscar sesión en la base de datos
            try:
                user_session = UserSession.objects.get(
                    agent=request.user,
                    session_key=request.session.session_key,
                    is_active=True
                )
                
                # Actualizar última actividad (se hace automáticamente por auto_now)
                # Verificar si la sesión está cerca de expirar y extenderla si es necesario
                time_until_expiry = user_session.expires_at - timezone.now()
                
                # Si queda menos de 30 minutos, extender la sesión
                if time_until_expiry < timedelta(minutes=30):
                    security_settings = request.user.security_settings
                    user_session.extend_session(security_settings.session_timeout_minutes)
                    
                    self.logger.debug(f"Sesión extendida para usuario {request.user.email}")
                
            except UserSession.DoesNotExist:
                # La sesión no existe en nuestra base de datos, podría ser una sesión de Django
                # Crear una nueva entrada si es necesario
                pass
                
        except Exception as e:
            self.logger.error(f"Error actualizando sesión de usuario: {str(e)}")
    
    def _log_slow_request(self, request, duration: float, status_code: int):
        """
        Registra requests lentos como posible indicador de ataque.
        
        Args:
            request: HttpRequest object
            duration: Duración del request en segundos
            status_code: Código de estado de la respuesta
        """
        try:
            AuditLog.objects.create(
                agent=request.user if request.user.is_authenticated else None,
                action='slow_request',
                resource_type='performance',
                ip_address=request.security_info['ip_address'],
                user_agent=request.security_info['user_agent'],
                details={
                    'path': request.security_info['path'],
                    'duration': duration,
                    'status_code': status_code,
                    'method': request.method
                },
                success=True
            )
            
            self.logger.warning(f"Slow request detected: {duration:.2f}s for {request.security_info['path']}")
            
        except Exception as e:
            self.logger.error(f"Error registrando request lento: {str(e)}")
    
    def _log_critical_access(self, request, status_code: int):
        """
        Registra acceso a URLs críticas.
        
        Args:
            request: HttpRequest object
            status_code: Código de estado de la respuesta
        """
        try:
            AuditLog.objects.create(
                agent=request.user,
                action='critical_access',
                resource_type='security',
                ip_address=request.security_info['ip_address'],
                user_agent=request.security_info['user_agent'],
                details={
                    'path': request.security_info['path'],
                    'method': request.method,
                    'status_code': status_code
                },
                success=status_code < 400
            )
            
        except Exception as e:
            self.logger.error(f"Error registrando acceso crítico: {str(e)}")