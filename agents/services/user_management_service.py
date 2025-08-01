"""
Servicio para gestión centralizada de usuarios.

Este servicio proporciona una interfaz unificada para todas las operaciones
relacionadas con la gestión de usuarios, incluyendo creación, actualización,
y cálculo de completitud de perfiles.
"""

import logging
from typing import Dict, Any, Optional
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.auth.password_validation import validate_password

from agents.models import Agent, UserProfile, SecuritySettings


logger = logging.getLogger(__name__)


class UserManagementService:
    """
    Servicio principal para gestión de usuarios.
    
    Proporciona métodos centralizados para crear, actualizar y gestionar
    usuarios y sus perfiles asociados.
    """
    
    def __init__(self):
        """Inicializa el servicio de gestión de usuarios."""
        self.logger = logging.getLogger(f"{__name__}.UserManagementService")
    
    def create_user(self, user_data: Dict[str, Any]) -> Agent:
        """
        Crea un nuevo usuario con perfil completo y configuraciones de seguridad.
        
        Args:
            user_data: Diccionario con datos del usuario
                - email (str): Email del usuario (requerido)
                - password (str): Contraseña (requerido)
                - first_name (str): Nombre (requerido)
                - last_name (str): Apellido (requerido)
                - license_number (str): Número de licencia (requerido)
                - phone (str, opcional): Teléfono
                - bio (str, opcional): Biografía
                - image_path (File, opcional): Imagen de perfil
                - profile_data (dict, opcional): Datos adicionales del perfil
        
        Returns:
            Agent: Instancia del usuario creado
            
        Raises:
            ValidationError: Si los datos no son válidos
        """
        try:
            with transaction.atomic():
                # Validar datos requeridos
                required_fields = ['email', 'password', 'first_name', 'last_name', 'license_number']
                for field in required_fields:
                    if not user_data.get(field):
                        raise ValidationError(f"El campo '{field}' es requerido")
                
                # Validar contraseña
                validate_password(user_data['password'])
                
                # Generar username único basado en email
                username = self._generate_unique_username(user_data['email'])
                
                # Crear usuario
                agent = Agent.objects.create_user(
                    username=username,
                    email=user_data['email'],
                    password=user_data['password'],
                    first_name=user_data['first_name'],
                    last_name=user_data['last_name'],
                    license_number=user_data['license_number'],
                    phone=user_data.get('phone', ''),
                    bio=user_data.get('bio', ''),
                    image_path=user_data.get('image_path')
                )
                
                # Crear perfil de usuario
                profile_data = user_data.get('profile_data', {})
                profile = UserProfile.objects.create(
                    agent=agent,
                    timezone=profile_data.get('timezone', 'America/Argentina/Buenos_Aires'),
                    language=profile_data.get('language', 'es'),
                    theme=profile_data.get('theme', 'light')
                )
                
                # Crear configuraciones de seguridad
                SecuritySettings.objects.create(
                    agent=agent,
                    session_timeout_minutes=480,  # 8 horas por defecto
                    suspicious_activity_alerts=True
                )
                
                # Calcular completitud inicial del perfil
                profile.profile_completion = self.calculate_profile_completion(agent)
                profile.save()
                
                self.logger.info(f"Usuario creado exitosamente: {agent.email}")
                return agent
                
        except Exception as e:
            self.logger.error(f"Error creando usuario: {str(e)}")
            raise
    
    def update_user_profile(self, agent: Agent, profile_data: Dict[str, Any]) -> UserProfile:
        """
        Actualiza el perfil del usuario con validaciones.
        
        Args:
            agent: Instancia del usuario
            profile_data: Datos a actualizar en el perfil
                - avatar (File, opcional): Nueva imagen de avatar
                - timezone (str, opcional): Zona horaria
                - language (str, opcional): Idioma preferido
                - theme (str, opcional): Tema de la interfaz
                - phone (str, opcional): Teléfono (actualiza en Agent)
                - bio (str, opcional): Biografía (actualiza en Agent)
        
        Returns:
            UserProfile: Perfil actualizado
            
        Raises:
            ValidationError: Si los datos no son válidos
        """
        try:
            with transaction.atomic():
                # Obtener o crear perfil
                profile, created = UserProfile.objects.get_or_create(agent=agent)
                
                # Actualizar campos del perfil
                profile_fields = ['avatar', 'timezone', 'language', 'theme']
                for field in profile_fields:
                    if field in profile_data:
                        setattr(profile, field, profile_data[field])
                
                # Actualizar campos del agente si están presentes
                agent_fields = ['phone', 'bio']
                agent_updated = False
                for field in agent_fields:
                    if field in profile_data:
                        setattr(agent, field, profile_data[field])
                        agent_updated = True
                
                if agent_updated:
                    agent.save()
                
                # Actualizar timestamp de última actualización
                profile.last_profile_update = timezone.now()
                
                # Recalcular completitud del perfil
                profile.profile_completion = self.calculate_profile_completion(agent)
                
                profile.save()
                
                self.logger.info(f"Perfil actualizado para usuario: {agent.email}")
                return profile
                
        except Exception as e:
            self.logger.error(f"Error actualizando perfil de {agent.email}: {str(e)}")
            raise
    
    def deactivate_user(self, agent: Agent, reason: str = "") -> bool:
        """
        Desactiva un usuario y registra la acción.
        
        Args:
            agent: Usuario a desactivar
            reason: Razón de la desactivación
            
        Returns:
            bool: True si se desactivó correctamente
        """
        try:
            with transaction.atomic():
                agent.is_active = False
                agent.save()
                
                # Terminar todas las sesiones activas
                from agents.models import UserSession
                UserSession.objects.filter(agent=agent, is_active=True).update(is_active=False)
                
                # Registrar en auditoría
                from agents.models import AuditLog
                AuditLog.objects.create(
                    agent=agent,
                    action='account_deactivated',
                    resource_type='agent',
                    resource_id=str(agent.id),
                    ip_address='127.0.0.1',  # Sistema interno
                    user_agent='System',
                    details={'reason': reason},
                    success=True
                )
                
                self.logger.info(f"Usuario desactivado: {agent.email}, razón: {reason}")
                return True
                
        except Exception as e:
            self.logger.error(f"Error desactivando usuario {agent.email}: {str(e)}")
            return False
    
    def calculate_profile_completion(self, agent: Agent) -> int:
        """
        Calcula el porcentaje de completitud del perfil del usuario.
        
        Args:
            agent: Usuario para calcular completitud
            
        Returns:
            int: Porcentaje de completitud (0-100)
        """
        try:
            total_fields = 0
            completed_fields = 0
            
            # Campos básicos del agente (peso: 60%)
            basic_fields = {
                'first_name': agent.first_name,
                'last_name': agent.last_name,
                'email': agent.email,
                'phone': agent.phone,
                'license_number': agent.license_number,
                'bio': agent.bio,
                'image_path': agent.image_path
            }
            
            for field, value in basic_fields.items():
                total_fields += 1
                if value:
                    completed_fields += 1
            
            # Campos del perfil (peso: 40%)
            try:
                profile = agent.profile
                profile_fields = {
                    'avatar': profile.avatar,
                    'timezone': profile.timezone,
                    'language': profile.language,
                    'theme': profile.theme
                }
                
                for field, value in profile_fields.items():
                    total_fields += 1
                    if value:
                        completed_fields += 1
                        
                # Verificaciones adicionales
                if profile.email_verified:
                    completed_fields += 0.5
                if profile.phone_verified:
                    completed_fields += 0.5
                total_fields += 1  # Para las verificaciones
                
            except UserProfile.DoesNotExist:
                # Si no hay perfil, solo contar campos básicos
                pass
            
            # Calcular porcentaje
            if total_fields == 0:
                return 0
            
            percentage = int((completed_fields / total_fields) * 100)
            return min(percentage, 100)  # Asegurar que no exceda 100%
            
        except Exception as e:
            self.logger.error(f"Error calculando completitud del perfil para {agent.email}: {str(e)}")
            return 0
    
    def get_user_dashboard_data(self, agent: Agent) -> Dict[str, Any]:
        """
        Obtiene datos personalizados para el dashboard del usuario.
        
        Args:
            agent: Usuario para obtener datos
            
        Returns:
            dict: Datos del dashboard personalizados
        """
        try:
            # Obtener perfil
            try:
                profile = agent.profile
            except UserProfile.DoesNotExist:
                profile = UserProfile.objects.create(agent=agent)
            
            # Obtener configuraciones de seguridad
            try:
                security_settings = agent.security_settings
            except SecuritySettings.DoesNotExist:
                security_settings = SecuritySettings.objects.create(agent=agent)
            
            # Obtener sesiones activas
            from agents.models import UserSession
            active_sessions = UserSession.objects.filter(
                agent=agent, 
                is_active=True
            ).count()
            
            # Obtener logs recientes
            from agents.models import AuditLog
            recent_logs = AuditLog.objects.filter(
                agent=agent
            ).order_by('-created_at')[:5]
            
            dashboard_data = {
                'profile_completion': profile.profile_completion,
                'email_verified': profile.email_verified,
                'phone_verified': profile.phone_verified,
                'two_factor_enabled': profile.two_factor_enabled,
                'active_sessions': active_sessions,
                'account_locked': security_settings.is_locked(),
                'last_login': agent.last_login,
                'recent_activity': [
                    {
                        'action': log.get_action_display(),
                        'timestamp': log.created_at,
                        'success': log.success
                    } for log in recent_logs
                ],
                'security_alerts': security_settings.suspicious_activity_alerts,
                'session_timeout': security_settings.session_timeout_minutes
            }
            
            return dashboard_data
            
        except Exception as e:
            self.logger.error(f"Error obteniendo datos del dashboard para {agent.email}: {str(e)}")
            return {}
    
    def _generate_unique_username(self, email: str) -> str:
        """
        Genera un username único basado en el email.
        
        Args:
            email: Email del usuario
            
        Returns:
            str: Username único
        """
        base_username = email.split('@')[0]
        username = base_username
        counter = 1
        
        while Agent.objects.filter(username=username).exists():
            username = f"{base_username}_{counter}"
            counter += 1
        
        return username
    
    def get_user_by_email(self, email: str) -> Optional[Agent]:
        """
        Obtiene un usuario por su email.
        
        Args:
            email: Email del usuario
            
        Returns:
            Agent o None si no existe
        """
        try:
            return Agent.objects.get(email=email, is_active=True)
        except Agent.DoesNotExist:
            return None
    
    def get_user_statistics(self, agent: Agent) -> Dict[str, Any]:
        """
        Obtiene estadísticas del usuario.
        
        Args:
            agent: Usuario para obtener estadísticas
            
        Returns:
            dict: Estadísticas del usuario
        """
        try:
            from agents.models import UserSession, AuditLog
            
            # Contar sesiones totales
            total_sessions = UserSession.objects.filter(agent=agent).count()
            
            # Contar acciones de auditoría
            total_actions = AuditLog.objects.filter(agent=agent).count()
            successful_actions = AuditLog.objects.filter(agent=agent, success=True).count()
            
            # Calcular días desde registro
            days_since_registration = (timezone.now().date() - agent.date_joined.date()).days
            
            statistics = {
                'days_since_registration': days_since_registration,
                'total_sessions': total_sessions,
                'total_actions': total_actions,
                'successful_actions': successful_actions,
                'success_rate': (successful_actions / total_actions * 100) if total_actions > 0 else 100,
                'profile_completion': self.calculate_profile_completion(agent)
            }
            
            return statistics
            
        except Exception as e:
            self.logger.error(f"Error obteniendo estadísticas para {agent.email}: {str(e)}")
            return {}