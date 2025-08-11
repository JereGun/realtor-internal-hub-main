"""
Middleware de auditoría para logging automático de acciones de usuario.

Este middleware registra automáticamente las acciones importantes de los usuarios
en el sistema, creando un log de auditoría completo para seguridad y compliance.
"""

import logging
import json
import time
from typing import Dict, Any, Optional
from django.http import HttpRequest, HttpResponse
from django.utils import timezone
from django.contrib.auth.models import AnonymousUser
from django.urls import resolve, Resolver404
from django.conf import settings

from agents.models import Agent, AuditLog


logger = logging.getLogger(__name__)


class AuditMiddleware:
    """
    Middleware para auditoría automática de acciones de usuario.
    
    Registra automáticamente las acciones importantes realizadas por los usuarios,
    incluyendo información de contexto como IP, user agent, y detalles de la acción.
    """
    
    # Acciones que deben ser auditadas automáticamente
    AUDITABLE_ACTIONS = {
        # Autenticación
        'agents:login': 'login_attempt',
        'agents:logout': 'logout',
        'agents:password_reset_request': 'password_reset_request',
        'agents:password_reset_confirm': 'password_reset',
        'agents:change_password': 'password_change',
        
        # Gestión de perfil
        'agents:profile_edit': 'profile_update',
        'agents:security_settings': 'security_settings_change',
        
        # Gestión de sesiones
        'agents:terminate_session': 'session_terminated',
        'agents:terminate_all_sessions': 'sessions_terminated',
        'agents:terminate_specific_session': 'session_terminated',
        'agents:terminate_other_sessions': 'sessions_terminated',
        
        # Gestión de usuarios (admin)
        'agents:agent_create': 'user_created',
        'agents:agent_edit': 'user_updated',
        
        # Acciones críticas en otros módulos
        'properties:property_create': 'property_created',
        'properties:property_update': 'property_updated',
        'properties:property_delete': 'property_deleted',
        'contracts:contract_create': 'contract_created',
        'contracts:contract_update': 'contract_updated',
        'contracts:contract_delete': 'contract_deleted',
        'customers:customer_create': 'customer_created',
        'customers:customer_update': 'customer_updated',
        'customers:customer_delete': 'customer_deleted',
    }
    
    # Métodos HTTP que deben ser auditados
    AUDITABLE_METHODS = ['POST', 'PUT', 'PATCH', 'DELETE']
    
    # Rutas que deben ser excluidas del logging
    EXCLUDED_PATHS = [
        '/static/',
        '/media/',
        '/favicon.ico',
        '/admin/jsi18n/',
        '/agents/dashboard/data/',  # AJAX endpoints que se llaman frecuentemente
        '/agents/quick-search/',
    ]
    
    def __init__(self, get_response):
        """
        Inicializa el middleware.
        
        Args:
            get_response: Función para obtener la respuesta
        """
        self.get_response = get_response
        self.logger = logging.getLogger(f"{__name__}.AuditMiddleware")
    
    def __call__(self, request: HttpRequest) -> HttpResponse:
        """
        Procesa la request y response para auditoría.
        
        Args:
            request: Request HTTP
            
        Returns:
            HttpResponse: Respuesta HTTP
        """
        # Marcar tiempo de inicio
        start_time = time.time()
        
        # Procesar request
        self.process_request(request)
        
        # Obtener respuesta
        response = self.get_response(request)
        
        # Calcular tiempo de procesamiento
        processing_time = time.time() - start_time
        
        # Procesar response
        self.process_response(request, response, processing_time)
        
        return response
    
    def process_request(self, request: HttpRequest) -> None:
        """
        Procesa la request entrante para preparar auditoría.
        
        Args:
            request: Request HTTP
        """
        try:
            # Almacenar información de la request para usar en process_response
            request._audit_data = {
                'start_time': timezone.now(),
                'ip_address': self._get_client_ip(request),
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                'method': request.method,
                'path': request.path,
                'query_params': dict(request.GET),
                'session_key': request.session.session_key if hasattr(request, 'session') else None
            }
            
            # Intentar resolver la URL para obtener información de la vista
            try:
                resolved = resolve(request.path)
                request._audit_data.update({
                    'view_name': resolved.view_name,
                    'url_kwargs': resolved.kwargs
                })
            except Resolver404:
                request._audit_data.update({
                    'view_name': 'unknown',
                    'url_kwargs': {}
                })
                
        except Exception as e:
            self.logger.warning(f"Error en process_request de AuditMiddleware: {str(e)}")
    
    def process_response(self, request: HttpRequest, response: HttpResponse, processing_time: float) -> None:
        """
        Procesa la response para crear logs de auditoría.
        
        Args:
            request: Request HTTP
            response: Response HTTP
            processing_time: Tiempo de procesamiento en segundos
        """
        try:
            # Verificar si debe ser auditado
            if not self._should_audit(request, response):
                return
            
            # Obtener datos de auditoría de la request
            audit_data = getattr(request, '_audit_data', {})
            
            # Determinar el usuario
            user = None
            if hasattr(request, 'user') and not isinstance(request.user, AnonymousUser):
                user = request.user
            
            # Determinar la acción
            action = self._determine_action(request, response)
            if not action:
                return
            
            # Obtener detalles adicionales
            details = self._extract_details(request, response, processing_time)
            
            # Determinar si la acción fue exitosa
            success = self._is_successful_response(response)
            
            # Crear log de auditoría
            self._create_audit_log(
                agent=user,
                action=action,
                request_data=audit_data,
                details=details,
                success=success
            )
            
        except Exception as e:
            self.logger.error(f"Error en process_response de AuditMiddleware: {str(e)}")
    
    def _should_audit(self, request: HttpRequest, response: HttpResponse) -> bool:
        """
        Determina si la request debe ser auditada.
        
        Args:
            request: Request HTTP
            response: Response HTTP
            
        Returns:
            bool: True si debe ser auditada
        """
        try:
            # Excluir rutas específicas
            for excluded_path in self.EXCLUDED_PATHS:
                if request.path.startswith(excluded_path):
                    return False
            
            # Solo auditar métodos específicos
            if request.method not in self.AUDITABLE_METHODS:
                return False
            
            # Excluir requests AJAX de datos frecuentes
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                # Solo auditar AJAX de acciones importantes
                audit_data = getattr(request, '_audit_data', {})
                view_name = audit_data.get('view_name', '')
                if view_name not in self.AUDITABLE_ACTIONS:
                    return False
            
            # Excluir responses de error del servidor (500+)
            if response.status_code >= 500:
                return False
            
            return True
            
        except Exception as e:
            self.logger.warning(f"Error determinando si auditar: {str(e)}")
            return False
    
    def _determine_action(self, request: HttpRequest, response: HttpResponse) -> Optional[str]:
        """
        Determina la acción a registrar basada en la request.
        
        Args:
            request: Request HTTP
            response: Response HTTP
            
        Returns:
            str: Acción a registrar o None si no debe auditarse
        """
        try:
            audit_data = getattr(request, '_audit_data', {})
            view_name = audit_data.get('view_name', '')
            
            # Buscar acción específica por nombre de vista
            if view_name in self.AUDITABLE_ACTIONS:
                return self.AUDITABLE_ACTIONS[view_name]
            
            # Determinar acción por método HTTP y path
            method = request.method
            path = request.path
            
            # Patrones genéricos para acciones CRUD
            if method == 'POST':
                if '/create/' in path or path.endswith('/'):
                    return 'create_action'
            elif method in ['PUT', 'PATCH']:
                return 'update_action'
            elif method == 'DELETE':
                return 'delete_action'
            
            # Acciones específicas por path
            if 'login' in path:
                return 'login_attempt'
            elif 'logout' in path:
                return 'logout'
            elif 'password' in path:
                return 'password_action'
            elif 'profile' in path:
                return 'profile_action'
            elif 'security' in path:
                return 'security_action'
            
            return None
            
        except Exception as e:
            self.logger.warning(f"Error determinando acción: {str(e)}")
            return None
    
    def _extract_details(self, request: HttpRequest, response: HttpResponse, processing_time: float) -> Dict[str, Any]:
        """
        Extrae detalles adicionales de la request y response.
        
        Args:
            request: Request HTTP
            response: Response HTTP
            processing_time: Tiempo de procesamiento
            
        Returns:
            dict: Detalles de la acción
        """
        details = {}
        
        try:
            audit_data = getattr(request, '_audit_data', {})
            
            # Información básica
            details.update({
                'method': request.method,
                'path': request.path,
                'status_code': response.status_code,
                'processing_time_ms': round(processing_time * 1000, 2),
                'view_name': audit_data.get('view_name', 'unknown')
            })
            
            # Parámetros de query (sin información sensible)
            query_params = audit_data.get('query_params', {})
            safe_params = self._sanitize_params(query_params)
            if safe_params:
                details['query_params'] = safe_params
            
            # Información de la URL
            url_kwargs = audit_data.get('url_kwargs', {})
            if url_kwargs:
                details['url_kwargs'] = url_kwargs
            
            # Información del response
            # Evitar acceder a response.content antes del render para prevenir ContentNotRenderedError
            if hasattr(response, 'content') and hasattr(response, 'is_rendered'):
                if response.is_rendered:
                    content_length = len(response.content)
                    details['response_size_bytes'] = content_length
            elif hasattr(response, 'content') and not hasattr(response, 'is_rendered'):
                # Para responses que no son TemplateResponse
                try:
                    content_length = len(response.content)
                    details['response_size_bytes'] = content_length
                except Exception:
                    # Si falla, no incluir el tamaño del contenido
                    pass
            
            # Content type
            content_type = response.get('Content-Type', '')
            if content_type:
                details['content_type'] = content_type
            
            # Información adicional para acciones específicas
            self._add_action_specific_details(request, response, details)
            
        except Exception as e:
            self.logger.warning(f"Error extrayendo detalles: {str(e)}")
            details['extraction_error'] = str(e)
        
        return details
    
    def _add_action_specific_details(self, request: HttpRequest, response: HttpResponse, details: Dict[str, Any]) -> None:
        """
        Añade detalles específicos según el tipo de acción.
        
        Args:
            request: Request HTTP
            response: Response HTTP
            details: Diccionario de detalles a modificar
        """
        try:
            path = request.path
            method = request.method
            
            # Detalles para login
            if 'login' in path and method == 'POST':
                if hasattr(request, 'POST'):
                    details['login_method'] = 'form'
                    if 'remember_me' in request.POST:
                        details['remember_me'] = bool(request.POST.get('remember_me'))
            
            # Detalles para logout
            elif 'logout' in path:
                details['logout_method'] = 'manual'
            
            # Detalles para cambio de contraseña
            elif 'password' in path and method == 'POST':
                details['password_change_method'] = 'user_initiated'
            
            # Detalles para gestión de sesiones
            elif 'session' in path and method == 'POST':
                if 'terminate' in path:
                    details['session_action'] = 'terminate'
                    if 'all' in path or 'others' in path:
                        details['terminate_scope'] = 'multiple'
                    else:
                        details['terminate_scope'] = 'single'
            
            # Detalles para perfil
            elif 'profile' in path and method in ['POST', 'PUT', 'PATCH']:
                details['profile_action'] = 'update'
            
            # Detalles para configuraciones de seguridad
            elif 'security' in path and method in ['POST', 'PUT', 'PATCH']:
                details['security_action'] = 'settings_update'
                
        except Exception as e:
            self.logger.warning(f"Error añadiendo detalles específicos: {str(e)}")
    
    def _sanitize_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitiza parámetros removiendo información sensible.
        
        Args:
            params: Parámetros originales
            
        Returns:
            dict: Parámetros sanitizados
        """
        sensitive_keys = [
            'password', 'token', 'secret', 'key', 'csrf', 'session',
            'api_key', 'auth', 'credential', 'private'
        ]
        
        sanitized = {}
        for key, value in params.items():
            key_lower = key.lower()
            if any(sensitive in key_lower for sensitive in sensitive_keys):
                sanitized[key] = '[REDACTED]'
            else:
                sanitized[key] = value
        
        return sanitized
    
    def _is_successful_response(self, response: HttpResponse) -> bool:
        """
        Determina si la response indica una acción exitosa.
        
        Args:
            response: Response HTTP
            
        Returns:
            bool: True si fue exitosa
        """
        # Considerar exitosas las responses 2xx y 3xx
        return 200 <= response.status_code < 400
    
    def _create_audit_log(self, agent: Optional[Agent], action: str, request_data: Dict[str, Any], 
                         details: Dict[str, Any], success: bool) -> None:
        """
        Crea un registro de auditoría en la base de datos.
        
        Args:
            agent: Usuario que realizó la acción (puede ser None)
            action: Acción realizada
            request_data: Datos de la request
            details: Detalles adicionales
            success: Si la acción fue exitosa
        """
        try:
            # Determinar el tipo de recurso basado en la acción y path
            resource_type = self._determine_resource_type(request_data.get('path', ''), action)
            
            # Crear el log de auditoría
            AuditLog.objects.create(
                agent=agent,
                action=action,
                resource_type=resource_type,
                resource_id=request_data.get('url_kwargs', {}).get('pk') or 
                           request_data.get('url_kwargs', {}).get('id'),
                ip_address=request_data.get('ip_address', '127.0.0.1'),
                user_agent=request_data.get('user_agent', ''),
                details=details,
                success=success,
                session_key=request_data.get('session_key')
            )
            
            self.logger.debug(f"Audit log created: {action} by {agent} - Success: {success}")
            
        except Exception as e:
            self.logger.error(f"Error creando log de auditoría: {str(e)}")
    
    def _determine_resource_type(self, path: str, action: str) -> str:
        """
        Determina el tipo de recurso basado en el path y acción.
        
        Args:
            path: Path de la request
            action: Acción realizada
            
        Returns:
            str: Tipo de recurso
        """
        try:
            # Mapeo de paths a tipos de recurso
            if '/agents/' in path:
                if 'profile' in path:
                    return 'user_profile'
                elif 'security' in path:
                    return 'security_settings'
                elif 'session' in path:
                    return 'user_session'
                else:
                    return 'agent'
            elif '/properties/' in path:
                return 'property'
            elif '/contracts/' in path:
                return 'contract'
            elif '/customers/' in path:
                return 'customer'
            elif '/payments/' in path:
                return 'payment'
            
            # Tipos basados en acción
            if 'login' in action or 'logout' in action or 'password' in action:
                return 'authentication'
            elif 'session' in action:
                return 'user_session'
            elif 'profile' in action:
                return 'user_profile'
            elif 'security' in action:
                return 'security_settings'
            
            return 'system'
            
        except Exception as e:
            self.logger.warning(f"Error determinando tipo de recurso: {str(e)}")
            return 'unknown'
    
    def _get_client_ip(self, request: HttpRequest) -> str:
        """
        Obtiene la dirección IP del cliente.
        
        Args:
            request: Request HTTP
            
        Returns:
            str: Dirección IP del cliente
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '127.0.0.1')
        return ip