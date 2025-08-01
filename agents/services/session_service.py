"""
Servicio para gestión de sesiones de usuario.

Este servicio maneja todas las operaciones relacionadas con las sesiones
de usuario, incluyendo creación, terminación, limpieza y monitoreo.
"""

import logging
import secrets
from typing import Dict, Any, Optional
from datetime import timedelta
from django.utils import timezone
from django.db.models import QuerySet
from django.db import transaction

from agents.models import Agent, UserSession, AuditLog


logger = logging.getLogger(__name__)


class SessionService:
    """
    Servicio para gestión de sesiones.
    
    Proporciona métodos centralizados para crear, gestionar y monitorear
    sesiones de usuario con información detallada del dispositivo.
    """
    
    def __init__(self):
        """Inicializa el servicio de gestión de sesiones."""
        self.logger = logging.getLogger(f"{__name__}.SessionService")
    
    def create_session(self, agent: Agent, request, session_timeout_minutes: Optional[int] = None) -> UserSession:
        """
        Crea nueva sesión con información del dispositivo.
        
        Args:
            agent: Usuario para crear sesión
            request: Request HTTP para obtener información del dispositivo
            session_timeout_minutes: Timeout personalizado en minutos
            
        Returns:
            UserSession: Nueva sesión creada
        """
        try:
            # Obtener información del request
            ip_address = self._get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')
            
            # Generar clave de sesión única
            session_key = self._generate_session_key()
            
            # Obtener timeout de sesión
            if session_timeout_minutes is None:
                try:
                    security_settings = agent.security_settings
                    session_timeout_minutes = security_settings.session_timeout_minutes
                except:
                    session_timeout_minutes = 480  # 8 horas por defecto
            
            # Calcular tiempo de expiración
            expires_at = timezone.now() + timedelta(minutes=session_timeout_minutes)
            
            # Extraer información del dispositivo
            device_info = self._extract_device_info(user_agent)
            
            # Obtener información de ubicación (básica basada en IP)
            location_info = self._get_location_info(ip_address)
            
            # Crear sesión
            session = UserSession.objects.create(
                agent=agent,
                session_key=session_key,
                ip_address=ip_address,
                user_agent=user_agent,
                device_info=device_info,
                location=location_info,
                expires_at=expires_at
            )
            
            # Registrar creación de sesión en auditoría
            AuditLog.objects.create(
                agent=agent,
                action='session_created',
                resource_type='session',
                resource_id=session_key,
                ip_address=ip_address,
                user_agent=user_agent,
                details={
                    'session_timeout_minutes': session_timeout_minutes,
                    'device_info': device_info
                },
                success=True,
                session_key=session_key
            )
            
            self.logger.info(f"Sesión creada para usuario {agent.email}: {session_key}")
            return session
            
        except Exception as e:
            self.logger.error(f"Error creando sesión para {agent.email}: {str(e)}")
            raise
    
    def get_active_sessions(self, agent: Agent) -> QuerySet:
        """
        Obtiene sesiones activas del usuario.
        
        Args:
            agent: Usuario para obtener sesiones
            
        Returns:
            QuerySet: Sesiones activas del usuario
        """
        try:
            # Limpiar sesiones expiradas primero
            self._cleanup_expired_sessions_for_user(agent)
            
            # Obtener sesiones activas
            active_sessions = UserSession.objects.filter(
                agent=agent,
                is_active=True,
                expires_at__gt=timezone.now()
            ).order_by('-last_activity')
            
            return active_sessions
            
        except Exception as e:
            self.logger.error(f"Error obteniendo sesiones activas para {agent.email}: {str(e)}")
            return UserSession.objects.none()
    
    def terminate_session(self, session_key: str, reason: str = 'user_request') -> bool:
        """
        Termina una sesión específica.
        
        Args:
            session_key: Clave de la sesión a terminar
            reason: Razón de la terminación
            
        Returns:
            bool: True si se terminó correctamente
        """
        try:
            with transaction.atomic():
                session = UserSession.objects.select_for_update().get(
                    session_key=session_key,
                    is_active=True
                )
                
                # Terminar sesión
                session.terminate()
                
                # Registrar terminación en auditoría
                AuditLog.objects.create(
                    agent=session.agent,
                    action='session_terminated',
                    resource_type='session',
                    resource_id=session_key,
                    ip_address=session.ip_address,
                    user_agent=session.user_agent,
                    details={'reason': reason},
                    success=True,
                    session_key=session_key
                )
                
                self.logger.info(f"Sesión terminada: {session_key}, razón: {reason}")
                return True
                
        except UserSession.DoesNotExist:
            self.logger.warning(f"Intento de terminar sesión inexistente: {session_key}")
            return False
        except Exception as e:
            self.logger.error(f"Error terminando sesión {session_key}: {str(e)}")
            return False
    
    def terminate_all_sessions(self, agent: Agent, except_current: Optional[str] = None) -> int:
        """
        Termina todas las sesiones del usuario.
        
        Args:
            agent: Usuario para terminar sesiones
            except_current: Clave de sesión a excluir (sesión actual)
            
        Returns:
            int: Número de sesiones terminadas
        """
        try:
            with transaction.atomic():
                # Obtener sesiones activas
                sessions_query = UserSession.objects.filter(
                    agent=agent,
                    is_active=True
                )
                
                # Excluir sesión actual si se especifica
                if except_current:
                    sessions_query = sessions_query.exclude(session_key=except_current)
                
                sessions = list(sessions_query.select_for_update())
                terminated_count = 0
                
                for session in sessions:
                    session.terminate()
                    terminated_count += 1
                    
                    # Registrar terminación
                    AuditLog.objects.create(
                        agent=agent,
                        action='session_terminated',
                        resource_type='session',
                        resource_id=session.session_key,
                        ip_address=session.ip_address,
                        user_agent=session.user_agent,
                        details={'reason': 'terminate_all_sessions'},
                        success=True,
                        session_key=session.session_key
                    )
                
                self.logger.info(f"Terminadas {terminated_count} sesiones para usuario {agent.email}")
                return terminated_count
                
        except Exception as e:
            self.logger.error(f"Error terminando todas las sesiones para {agent.email}: {str(e)}")
            return 0
    
    def cleanup_expired_sessions(self) -> int:
        """
        Limpia sesiones expiradas del sistema.
        
        Returns:
            int: Número de sesiones limpiadas
        """
        try:
            with transaction.atomic():
                # Obtener sesiones expiradas
                expired_sessions = UserSession.objects.filter(
                    expires_at__lt=timezone.now(),
                    is_active=True
                ).select_for_update()
                
                cleaned_count = 0
                
                for session in expired_sessions:
                    session.terminate()
                    cleaned_count += 1
                    
                    # Registrar limpieza
                    AuditLog.objects.create(
                        agent=session.agent,
                        action='session_expired',
                        resource_type='session',
                        resource_id=session.session_key,
                        ip_address=session.ip_address,
                        user_agent='System',
                        details={'reason': 'session_expired'},
                        success=True,
                        session_key=session.session_key
                    )
                
                self.logger.info(f"Limpiadas {cleaned_count} sesiones expiradas")
                return cleaned_count
                
        except Exception as e:
            self.logger.error(f"Error limpiando sesiones expiradas: {str(e)}")
            return 0
    
    def extend_session(self, session_key: str, minutes: int = 480) -> bool:
        """
        Extiende la duración de una sesión.
        
        Args:
            session_key: Clave de la sesión a extender
            minutes: Minutos adicionales de duración
            
        Returns:
            bool: True si se extendió correctamente
        """
        try:
            session = UserSession.objects.get(
                session_key=session_key,
                is_active=True
            )
            
            # Extender sesión
            session.extend_session(minutes)
            
            # Registrar extensión
            AuditLog.objects.create(
                agent=session.agent,
                action='session_extended',
                resource_type='session',
                resource_id=session_key,
                ip_address=session.ip_address,
                user_agent=session.user_agent,
                details={'extended_minutes': minutes},
                success=True,
                session_key=session_key
            )
            
            self.logger.info(f"Sesión extendida: {session_key}, {minutes} minutos")
            return True
            
        except UserSession.DoesNotExist:
            self.logger.warning(f"Intento de extender sesión inexistente: {session_key}")
            return False
        except Exception as e:
            self.logger.error(f"Error extendiendo sesión {session_key}: {str(e)}")
            return False
    
    def get_session_info(self, session_key: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene información detallada de una sesión.
        
        Args:
            session_key: Clave de la sesión
            
        Returns:
            dict: Información de la sesión o None si no existe
        """
        try:
            session = UserSession.objects.get(session_key=session_key)
            
            return {
                'session_key': session.session_key,
                'agent': {
                    'id': session.agent.id,
                    'email': session.agent.email,
                    'full_name': session.agent.get_full_name()
                },
                'ip_address': session.ip_address,
                'user_agent': session.user_agent,
                'device_info': session.device_info,
                'location': session.location,
                'is_active': session.is_active,
                'created_at': session.created_at,
                'last_activity': session.last_activity,
                'expires_at': session.expires_at,
                'is_expired': session.is_expired(),
                'time_remaining': self._calculate_time_remaining(session)
            }
            
        except UserSession.DoesNotExist:
            return None
        except Exception as e:
            self.logger.error(f"Error obteniendo información de sesión {session_key}: {str(e)}")
            return None
    
    def get_user_session_statistics(self, agent: Agent) -> Dict[str, Any]:
        """
        Obtiene estadísticas de sesiones del usuario.
        
        Args:
            agent: Usuario para obtener estadísticas
            
        Returns:
            dict: Estadísticas de sesiones
        """
        try:
            # Sesiones totales
            total_sessions = UserSession.objects.filter(agent=agent).count()
            
            # Sesiones activas
            active_sessions = self.get_active_sessions(agent).count()
            
            # Sesión más reciente
            latest_session = UserSession.objects.filter(agent=agent).order_by('-created_at').first()
            
            # Dispositivos únicos
            unique_devices = UserSession.objects.filter(agent=agent).values_list(
                'device_info__device_type', flat=True
            ).distinct().count()
            
            # IPs únicas
            unique_ips = UserSession.objects.filter(agent=agent).values_list(
                'ip_address', flat=True
            ).distinct().count()
            
            # Duración promedio de sesión (aproximada)
            avg_session_duration = self._calculate_average_session_duration(agent)
            
            return {
                'total_sessions': total_sessions,
                'active_sessions': active_sessions,
                'unique_devices': unique_devices,
                'unique_ips': unique_ips,
                'latest_session': {
                    'created_at': latest_session.created_at if latest_session else None,
                    'ip_address': latest_session.ip_address if latest_session else None,
                    'device_info': latest_session.device_info if latest_session else None
                } if latest_session else None,
                'average_session_duration_hours': avg_session_duration
            }
            
        except Exception as e:
            self.logger.error(f"Error obteniendo estadísticas de sesión para {agent.email}: {str(e)}")
            return {}
    
    def _generate_session_key(self) -> str:
        """
        Genera una clave de sesión única.
        
        Returns:
            str: Clave de sesión única
        """
        while True:
            session_key = secrets.token_urlsafe(30)
            if not UserSession.objects.filter(session_key=session_key).exists():
                return session_key
    
    def _get_client_ip(self, request) -> str:
        """
        Extrae la IP del cliente del request.
        
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
    
    def _extract_device_info(self, user_agent: str) -> Dict[str, Any]:
        """
        Extrae información del dispositivo del user agent.
        
        Args:
            user_agent: String del user agent
            
        Returns:
            dict: Información del dispositivo
        """
        device_info = {
            'user_agent': user_agent,
            'device_type': 'unknown',
            'browser': 'unknown',
            'os': 'unknown'
        }
        
        try:
            user_agent_lower = user_agent.lower()
            
            # Detectar tipo de dispositivo
            if 'mobile' in user_agent_lower or 'android' in user_agent_lower or 'iphone' in user_agent_lower:
                device_info['device_type'] = 'mobile'
            elif 'tablet' in user_agent_lower or 'ipad' in user_agent_lower:
                device_info['device_type'] = 'tablet'
            else:
                device_info['device_type'] = 'desktop'
            
            # Detectar navegador
            if 'chrome' in user_agent_lower:
                device_info['browser'] = 'Chrome'
            elif 'firefox' in user_agent_lower:
                device_info['browser'] = 'Firefox'
            elif 'safari' in user_agent_lower and 'chrome' not in user_agent_lower:
                device_info['browser'] = 'Safari'
            elif 'edge' in user_agent_lower:
                device_info['browser'] = 'Edge'
            elif 'opera' in user_agent_lower:
                device_info['browser'] = 'Opera'
            
            # Detectar sistema operativo
            if 'windows' in user_agent_lower:
                device_info['os'] = 'Windows'
            elif 'mac' in user_agent_lower:
                device_info['os'] = 'macOS'
            elif 'linux' in user_agent_lower:
                device_info['os'] = 'Linux'
            elif 'android' in user_agent_lower:
                device_info['os'] = 'Android'
            elif 'ios' in user_agent_lower or 'iphone' in user_agent_lower or 'ipad' in user_agent_lower:
                device_info['os'] = 'iOS'
            
        except Exception as e:
            self.logger.warning(f"Error extrayendo información del dispositivo: {str(e)}")
        
        return device_info
    
    def _get_location_info(self, ip_address: str) -> Dict[str, Any]:
        """
        Obtiene información básica de ubicación basada en IP.
        
        Args:
            ip_address: Dirección IP
            
        Returns:
            dict: Información de ubicación básica
        """
        location_info = {
            'ip_address': ip_address,
            'country': 'unknown',
            'city': 'unknown',
            'is_local': False
        }
        
        try:
            # Detectar IPs locales
            if (ip_address.startswith('192.168.') or 
                ip_address.startswith('10.') or 
                ip_address.startswith('172.') or 
                ip_address == '127.0.0.1' or 
                ip_address == 'localhost'):
                location_info['is_local'] = True
                location_info['country'] = 'Local'
                location_info['city'] = 'Local'
            
            # Para IPs públicas, se podría integrar con un servicio de geolocalización
            # Por ahora, solo marcamos como desconocido
            
        except Exception as e:
            self.logger.warning(f"Error obteniendo información de ubicación para IP {ip_address}: {str(e)}")
        
        return location_info
    
    def _cleanup_expired_sessions_for_user(self, agent: Agent):
        """
        Limpia sesiones expiradas para un usuario específico.
        
        Args:
            agent: Usuario para limpiar sesiones
        """
        try:
            expired_sessions = UserSession.objects.filter(
                agent=agent,
                expires_at__lt=timezone.now(),
                is_active=True
            )
            
            for session in expired_sessions:
                session.terminate()
                
        except Exception as e:
            self.logger.warning(f"Error limpiando sesiones expiradas para {agent.email}: {str(e)}")
    
    def _calculate_time_remaining(self, session: UserSession) -> Optional[int]:
        """
        Calcula el tiempo restante de una sesión en minutos.
        
        Args:
            session: Sesión para calcular tiempo restante
            
        Returns:
            int: Minutos restantes o None si está expirada
        """
        if session.is_expired():
            return None
        
        time_remaining = session.expires_at - timezone.now()
        return int(time_remaining.total_seconds() / 60)
    
    def _calculate_average_session_duration(self, agent: Agent) -> float:
        """
        Calcula la duración promedio de sesiones del usuario.
        
        Args:
            agent: Usuario para calcular promedio
            
        Returns:
            float: Duración promedio en horas
        """
        try:
            # Obtener sesiones terminadas con actividad registrada
            terminated_sessions = UserSession.objects.filter(
                agent=agent,
                is_active=False
            ).exclude(
                last_activity=None
            )[:50]  # Últimas 50 sesiones para el cálculo
            
            if not terminated_sessions:
                return 0.0
            
            total_duration = timedelta()
            count = 0
            
            for session in terminated_sessions:
                if session.last_activity and session.created_at:
                    duration = session.last_activity - session.created_at
                    total_duration += duration
                    count += 1
            
            if count == 0:
                return 0.0
            
            average_duration = total_duration / count
            return average_duration.total_seconds() / 3600  # Convertir a horas
            
        except Exception as e:
            self.logger.warning(f"Error calculando duración promedio de sesión para {agent.email}: {str(e)}")
            return 0.0