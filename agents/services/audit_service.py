"""
Servicio de auditoría para logging manual y análisis de logs.

Este servicio complementa el AuditMiddleware proporcionando métodos
para crear logs de auditoría manuales y analizar patrones de actividad.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import timedelta
from django.utils import timezone
from django.db.models import Count, Q, Avg
from django.db import transaction

from agents.models import Agent, AuditLog


logger = logging.getLogger(__name__)


class AuditService:
    """
    Servicio para gestión manual de auditoría y análisis de logs.
    
    Proporciona métodos para crear logs de auditoría manuales,
    analizar patrones de actividad y detectar anomalías.
    """
    
    def __init__(self):
        """Inicializa el servicio de auditoría."""
        self.logger = logging.getLogger(f"{__name__}.AuditService")
    
    def log_user_action(self, agent: Optional[Agent], action: str, resource_type: str = 'system',
                       resource_id: Optional[str] = None, ip_address: str = '127.0.0.1',
                       user_agent: str = 'System', details: Optional[Dict[str, Any]] = None,
                       success: bool = True, session_key: Optional[str] = None) -> AuditLog:
        """
        Crea un log de auditoría manual.
        
        Args:
            agent: Usuario que realizó la acción
            action: Acción realizada
            resource_type: Tipo de recurso afectado
            resource_id: ID del recurso afectado
            ip_address: Dirección IP del usuario
            user_agent: User agent del navegador
            details: Detalles adicionales de la acción
            success: Si la acción fue exitosa
            session_key: Clave de sesión del usuario
            
        Returns:
            AuditLog: Log de auditoría creado
        """
        try:
            audit_log = AuditLog.objects.create(
                agent=agent,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                ip_address=ip_address,
                user_agent=user_agent,
                details=details or {},
                success=success,
                session_key=session_key
            )
            
            self.logger.debug(f"Manual audit log created: {action} by {agent} - Success: {success}")
            return audit_log
            
        except Exception as e:
            self.logger.error(f"Error creating manual audit log: {str(e)}")
            raise
    
    def log_security_event(self, agent: Optional[Agent], event_type: str, severity: str = 'medium',
                          ip_address: str = '127.0.0.1', details: Optional[Dict[str, Any]] = None) -> AuditLog:
        """
        Registra un evento de seguridad específico.
        
        Args:
            agent: Usuario relacionado con el evento
            event_type: Tipo de evento de seguridad
            severity: Severidad del evento (low, medium, high, critical)
            ip_address: Dirección IP relacionada
            details: Detalles del evento de seguridad
            
        Returns:
            AuditLog: Log de auditoría del evento de seguridad
        """
        try:
            security_details = details or {}
            security_details.update({
                'event_type': event_type,
                'severity': severity,
                'timestamp': timezone.now().isoformat()
            })
            
            return self.log_user_action(
                agent=agent,
                action='security_event',
                resource_type='security',
                ip_address=ip_address,
                user_agent='SecuritySystem',
                details=security_details,
                success=True
            )
            
        except Exception as e:
            self.logger.error(f"Error logging security event: {str(e)}")
            raise
    
    def get_user_activity_summary(self, agent: Agent, days: int = 30) -> Dict[str, Any]:
        """
        Obtiene un resumen de actividad del usuario.
        
        Args:
            agent: Usuario para analizar
            days: Número de días hacia atrás
            
        Returns:
            dict: Resumen de actividad del usuario
        """
        try:
            start_date = timezone.now() - timedelta(days=days)
            
            # Logs del usuario en el período
            user_logs = AuditLog.objects.filter(
                agent=agent,
                created_at__gte=start_date
            )
            
            # Estadísticas básicas
            total_actions = user_logs.count()
            successful_actions = user_logs.filter(success=True).count()
            failed_actions = user_logs.filter(success=False).count()
            
            # Acciones más frecuentes
            top_actions = user_logs.values('action').annotate(
                count=Count('id')
            ).order_by('-count')[:5]
            
            # IPs utilizadas
            unique_ips = user_logs.values_list('ip_address', flat=True).distinct().count()
            
            # Actividad por día
            daily_activity = self._get_daily_activity_for_user(user_logs)
            
            # Eventos de seguridad
            security_events = user_logs.filter(
                action__in=[
                    'login', 'logout', 'password_change', 'password_reset',
                    'security_settings_change', 'session_terminated',
                    'suspicious_activity', 'account_locked'
                ]
            ).count()
            
            return {
                'period_days': days,
                'total_actions': total_actions,
                'successful_actions': successful_actions,
                'failed_actions': failed_actions,
                'success_rate': (successful_actions / total_actions * 100) if total_actions > 0 else 0,
                'top_actions': list(top_actions),
                'unique_ips': unique_ips,
                'daily_activity': daily_activity,
                'security_events': security_events,
                'last_activity': user_logs.order_by('-created_at').first().created_at if user_logs.exists() else None
            }
            
        except Exception as e:
            self.logger.error(f"Error getting user activity summary for {agent.email}: {str(e)}")
            return {}
    
    def detect_suspicious_activity(self, agent: Optional[Agent] = None, days: int = 7) -> List[Dict[str, Any]]:
        """
        Detecta actividad sospechosa en los logs de auditoría.
        
        Args:
            agent: Usuario específico a analizar (None para todos)
            days: Número de días hacia atrás para analizar
            
        Returns:
            list: Lista de actividades sospechosas detectadas
        """
        try:
            start_date = timezone.now() - timedelta(days=days)
            suspicious_activities = []
            
            # Query base
            logs_query = AuditLog.objects.filter(created_at__gte=start_date)
            if agent:
                logs_query = logs_query.filter(agent=agent)
            
            # 1. Múltiples intentos de login fallidos
            failed_logins = logs_query.filter(
                action='login',
                success=False
            ).values('agent', 'ip_address').annotate(
                count=Count('id')
            ).filter(count__gte=5)
            
            for login_attempt in failed_logins:
                agent_obj = Agent.objects.get(id=login_attempt['agent']) if login_attempt['agent'] else None
                suspicious_activities.append({
                    'type': 'multiple_failed_logins',
                    'severity': 'high',
                    'agent': agent_obj,
                    'ip_address': login_attempt['ip_address'],
                    'count': login_attempt['count'],
                    'description': f"Múltiples intentos de login fallidos ({login_attempt['count']})"
                })
            
            # 2. Acceso desde múltiples IPs en poco tiempo
            if agent:
                recent_ips = logs_query.filter(
                    agent=agent,
                    created_at__gte=timezone.now() - timedelta(hours=2)
                ).values_list('ip_address', flat=True).distinct()
                
                if len(recent_ips) >= 3:
                    suspicious_activities.append({
                        'type': 'multiple_ips_short_time',
                        'severity': 'medium',
                        'agent': agent,
                        'ip_addresses': list(recent_ips),
                        'count': len(recent_ips),
                        'description': f"Acceso desde {len(recent_ips)} IPs diferentes en 2 horas"
                    })
            
            # 3. Actividad fuera de horario normal
            night_activity = logs_query.filter(
                created_at__time__range=('00:00:00', '06:00:00')
            ).exclude(action__in=['session_expired', 'cleanup'])
            
            if agent:
                night_activity = night_activity.filter(agent=agent)
            
            night_count = night_activity.count()
            if night_count >= 10:
                suspicious_activities.append({
                    'type': 'unusual_hours_activity',
                    'severity': 'low',
                    'agent': agent,
                    'count': night_count,
                    'description': f"Actividad inusual en horario nocturno ({night_count} acciones)"
                })
            
            # 4. Cambios de configuración de seguridad frecuentes
            security_changes = logs_query.filter(
                action='security_settings_change'
            )
            
            if agent:
                security_changes = security_changes.filter(agent=agent)
            
            security_count = security_changes.count()
            if security_count >= 5:
                suspicious_activities.append({
                    'type': 'frequent_security_changes',
                    'severity': 'medium',
                    'agent': agent,
                    'count': security_count,
                    'description': f"Cambios frecuentes en configuración de seguridad ({security_count})"
                })
            
            # 5. Terminación masiva de sesiones
            session_terminations = logs_query.filter(
                action__in=['sessions_terminated', 'session_terminated']
            )
            
            if agent:
                session_terminations = session_terminations.filter(agent=agent)
            
            termination_count = session_terminations.count()
            if termination_count >= 10:
                suspicious_activities.append({
                    'type': 'mass_session_termination',
                    'severity': 'medium',
                    'agent': agent,
                    'count': termination_count,
                    'description': f"Terminación masiva de sesiones ({termination_count})"
                })
            
            return suspicious_activities
            
        except Exception as e:
            self.logger.error(f"Error detecting suspicious activity: {str(e)}")
            return []
    
    def generate_audit_report(self, start_date: timezone.datetime, end_date: timezone.datetime,
                            agent: Optional[Agent] = None, actions: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Genera un reporte de auditoría detallado.
        
        Args:
            start_date: Fecha de inicio del reporte
            end_date: Fecha de fin del reporte
            agent: Usuario específico (None para todos)
            actions: Lista de acciones específicas a incluir
            
        Returns:
            dict: Reporte de auditoría detallado
        """
        try:
            # Query base
            logs_query = AuditLog.objects.filter(
                created_at__range=[start_date, end_date]
            )
            
            if agent:
                logs_query = logs_query.filter(agent=agent)
            
            if actions:
                logs_query = logs_query.filter(action__in=actions)
            
            # Estadísticas generales
            total_logs = logs_query.count()
            successful_logs = logs_query.filter(success=True).count()
            failed_logs = logs_query.filter(success=False).count()
            
            # Usuarios más activos
            top_users = logs_query.exclude(agent=None).values(
                'agent__email', 'agent__first_name', 'agent__last_name'
            ).annotate(count=Count('id')).order_by('-count')[:10]
            
            # Acciones más frecuentes
            top_actions = logs_query.values('action').annotate(
                count=Count('id')
            ).order_by('-count')[:10]
            
            # IPs más activas
            top_ips = logs_query.values('ip_address').annotate(
                count=Count('id')
            ).order_by('-count')[:10]
            
            # Actividad por día
            daily_activity = self._get_daily_activity_report(logs_query)
            
            # Eventos de seguridad
            security_events = logs_query.filter(
                action__in=[
                    'login', 'logout', 'password_change', 'password_reset',
                    'security_settings_change', 'suspicious_activity',
                    'account_locked', 'account_unlocked'
                ]
            ).values('action').annotate(count=Count('id')).order_by('-count')
            
            # Acciones fallidas por tipo
            failed_actions = logs_query.filter(success=False).values('action').annotate(
                count=Count('id')
            ).order_by('-count')[:5]
            
            return {
                'period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'days': (end_date - start_date).days
                },
                'summary': {
                    'total_logs': total_logs,
                    'successful_logs': successful_logs,
                    'failed_logs': failed_logs,
                    'success_rate': (successful_logs / total_logs * 100) if total_logs > 0 else 0
                },
                'top_users': list(top_users),
                'top_actions': list(top_actions),
                'top_ips': list(top_ips),
                'daily_activity': daily_activity,
                'security_events': list(security_events),
                'failed_actions': list(failed_actions),
                'generated_at': timezone.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error generating audit report: {str(e)}")
            return {}
    
    def cleanup_old_logs(self, days: int = 90, keep_critical: bool = True, batch_size: int = 1000) -> int:
        """
        Limpia logs de auditoría antiguos.
        
        Args:
            days: Días de logs a mantener
            keep_critical: Mantener logs críticos de seguridad
            batch_size: Tamaño del lote para eliminación
            
        Returns:
            int: Número de logs eliminados
        """
        try:
            cutoff_date = timezone.now() - timedelta(days=days)
            
            # Query base
            logs_query = AuditLog.objects.filter(created_at__lt=cutoff_date)
            
            # Excluir logs críticos si se especifica
            if keep_critical:
                critical_actions = [
                    'login', 'logout', 'password_change', 'password_reset',
                    '2fa_enabled', '2fa_disabled', 'account_locked', 'account_unlocked',
                    'suspicious_activity', 'security_settings_change'
                ]
                logs_query = logs_query.exclude(action__in=critical_actions)
            
            # Eliminar en lotes
            deleted_count = 0
            while True:
                batch_ids = list(logs_query.values_list('id', flat=True)[:batch_size])
                if not batch_ids:
                    break
                
                with transaction.atomic():
                    batch_deleted = AuditLog.objects.filter(id__in=batch_ids).delete()[0]
                    deleted_count += batch_deleted
            
            self.logger.info(f"Cleaned up {deleted_count} old audit logs")
            return deleted_count
            
        except Exception as e:
            self.logger.error(f"Error cleaning up old logs: {str(e)}")
            return 0
    
    def _get_daily_activity_for_user(self, logs_query) -> List[Dict[str, Any]]:
        """Obtiene actividad diaria para un usuario específico."""
        from django.db.models.functions import TruncDate
        
        daily_stats = logs_query.annotate(
            date=TruncDate('created_at')
        ).values('date').annotate(
            count=Count('id')
        ).order_by('-date')[:14]
        
        return [
            {
                'date': stat['date'].strftime('%Y-%m-%d'),
                'count': stat['count']
            }
            for stat in daily_stats
        ]
    
    def _get_daily_activity_report(self, logs_query) -> List[Dict[str, Any]]:
        """Obtiene actividad diaria para el reporte general."""
        from django.db.models.functions import TruncDate
        
        daily_stats = logs_query.annotate(
            date=TruncDate('created_at')
        ).values('date').annotate(
            total=Count('id'),
            successful=Count('id', filter=Q(success=True)),
            failed=Count('id', filter=Q(success=False))
        ).order_by('-date')
        
        return [
            {
                'date': stat['date'].strftime('%Y-%m-%d'),
                'total': stat['total'],
                'successful': stat['successful'],
                'failed': stat['failed']
            }
            for stat in daily_stats
        ]