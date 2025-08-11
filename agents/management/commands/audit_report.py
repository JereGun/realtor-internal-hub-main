"""
Comando de gestión Django para generar reportes de auditoría.

Este comando genera reportes detallados de actividad de usuarios
y eventos de seguridad basados en los logs de auditoría.
"""

import csv
import json
import logging
from datetime import timedelta, datetime
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db.models import Count, Q
from django.conf import settings

from agents.models import AuditLog, Agent


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Comando para generar reportes de auditoría.
    
    Uso:
        python manage.py audit_report --days 30 --format csv --output report.csv
        python manage.py audit_report --user test@example.com --format json
        python manage.py audit_report --security-only --days 7
    """
    
    help = 'Genera reportes de auditoría basados en logs del sistema'
    
    def add_arguments(self, parser):
        """Añade argumentos al comando."""
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Número de días hacia atrás para el reporte (por defecto: 30)'
        )
        
        parser.add_argument(
            '--user',
            type=str,
            help='Email del usuario específico para el reporte'
        )
        
        parser.add_argument(
            '--action',
            type=str,
            help='Acción específica a incluir en el reporte'
        )
        
        parser.add_argument(
            '--security-only',
            action='store_true',
            help='Incluir solo eventos relacionados con seguridad'
        )
        
        parser.add_argument(
            '--failed-only',
            action='store_true',
            help='Incluir solo acciones fallidas'
        )
        
        parser.add_argument(
            '--format',
            choices=['csv', 'json', 'summary'],
            default='summary',
            help='Formato del reporte (por defecto: summary)'
        )
        
        parser.add_argument(
            '--output',
            type=str,
            help='Archivo de salida (por defecto: stdout)'
        )
        
        parser.add_argument(
            '--include-details',
            action='store_true',
            help='Incluir detalles completos de cada log'
        )
    
    def handle(self, *args, **options):
        """Ejecuta el comando de generación de reportes."""
        days = options['days']
        user_email = options['user']
        action = options['action']
        security_only = options['security_only']
        failed_only = options['failed_only']
        format_type = options['format']
        output_file = options['output']
        include_details = options['include_details']
        
        # Validar argumentos
        if days <= 0:
            raise CommandError('El número de días debe ser mayor a 0')
        
        # Calcular fecha de inicio
        start_date = timezone.now() - timedelta(days=days)
        
        self.stdout.write(
            self.style.SUCCESS(f'Generando reporte de auditoría...')
        )
        self.stdout.write(f'Período: {start_date.strftime("%Y-%m-%d")} a {timezone.now().strftime("%Y-%m-%d")}')
        
        # Construir query base
        logs_query = AuditLog.objects.filter(created_at__gte=start_date)
        
        # Aplicar filtros
        if user_email:
            try:
                user = Agent.objects.get(email=user_email)
                logs_query = logs_query.filter(agent=user)
                self.stdout.write(f'Usuario: {user_email}')
            except Agent.DoesNotExist:
                raise CommandError(f'Usuario no encontrado: {user_email}')
        
        if action:
            logs_query = logs_query.filter(action=action)
            self.stdout.write(f'Acción: {action}')
        
        if security_only:
            security_actions = [
                'login', 'logout', 'password_change', 'password_reset',
                '2fa_enabled', '2fa_disabled', 'account_locked', 'account_unlocked',
                'suspicious_activity', 'security_settings_change', 'session_terminated'
            ]
            logs_query = logs_query.filter(action__in=security_actions)
            self.stdout.write('Filtro: Solo eventos de seguridad')
        
        if failed_only:
            logs_query = logs_query.filter(success=False)
            self.stdout.write('Filtro: Solo acciones fallidas')
        
        # Ordenar por fecha
        logs_query = logs_query.order_by('-created_at')
        
        # Generar reporte según formato
        if format_type == 'summary':
            self._generate_summary_report(logs_query, output_file)
        elif format_type == 'csv':
            self._generate_csv_report(logs_query, output_file, include_details)
        elif format_type == 'json':
            self._generate_json_report(logs_query, output_file, include_details)
        
        total_logs = logs_query.count()
        self.stdout.write(
            self.style.SUCCESS(f'Reporte generado exitosamente ({total_logs:,} registros)')
        )
    
    def _generate_summary_report(self, logs_query, output_file):
        """Genera un reporte resumen."""
        output = []
        
        # Estadísticas generales
        total_logs = logs_query.count()
        successful_logs = logs_query.filter(success=True).count()
        failed_logs = logs_query.filter(success=False).count()
        
        output.append("REPORTE DE AUDITORÍA - RESUMEN")
        output.append("=" * 50)
        output.append(f"Total de registros: {total_logs:,}")
        output.append(f"Acciones exitosas: {successful_logs:,} ({successful_logs/total_logs*100:.1f}%)" if total_logs > 0 else "Acciones exitosas: 0")
        output.append(f"Acciones fallidas: {failed_logs:,} ({failed_logs/total_logs*100:.1f}%)" if total_logs > 0 else "Acciones fallidas: 0")
        output.append("")
        
        # Top acciones
        action_stats = logs_query.values('action').annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        
        output.append("TOP 10 ACCIONES:")
        output.append("-" * 30)
        for stat in action_stats:
            action = stat['action']
            count = stat['count']
            percentage = count / total_logs * 100 if total_logs > 0 else 0
            output.append(f"{action:25} {count:>6,} ({percentage:4.1f}%)")
        output.append("")
        
        # Top usuarios
        user_stats = logs_query.exclude(agent=None).values(
            'agent__email', 'agent__first_name', 'agent__last_name'
        ).annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        
        if user_stats:
            output.append("TOP 10 USUARIOS MÁS ACTIVOS:")
            output.append("-" * 40)
            for stat in user_stats:
                email = stat['agent__email']
                name = f"{stat['agent__first_name']} {stat['agent__last_name']}"
                count = stat['count']
                output.append(f"{name:25} {email:25} {count:>6,}")
            output.append("")
        
        # Actividad por día
        daily_stats = self._get_daily_activity(logs_query)
        if daily_stats:
            output.append("ACTIVIDAD POR DÍA:")
            output.append("-" * 25)
            for date, count in daily_stats:
                output.append(f"{date} {count:>8,}")
            output.append("")
        
        # Eventos de seguridad críticos
        security_events = logs_query.filter(
            action__in=[
                'account_locked', 'suspicious_activity', 'password_reset',
                '2fa_disabled', 'security_settings_change'
            ]
        ).count()
        
        if security_events > 0:
            output.append("EVENTOS DE SEGURIDAD CRÍTICOS:")
            output.append("-" * 35)
            output.append(f"Total de eventos críticos: {security_events:,}")
            
            critical_stats = logs_query.filter(
                action__in=[
                    'account_locked', 'suspicious_activity', 'password_reset',
                    '2fa_disabled', 'security_settings_change'
                ]
            ).values('action').annotate(count=Count('id')).order_by('-count')
            
            for stat in critical_stats:
                action = stat['action']
                count = stat['count']
                output.append(f"{action:25} {count:>6,}")
            output.append("")
        
        # Acciones fallidas por tipo
        failed_stats = logs_query.filter(success=False).values('action').annotate(
            count=Count('id')
        ).order_by('-count')[:5]
        
        if failed_stats:
            output.append("TOP 5 ACCIONES FALLIDAS:")
            output.append("-" * 30)
            for stat in failed_stats:
                action = stat['action']
                count = stat['count']
                output.append(f"{action:25} {count:>6,}")
            output.append("")
        
        # Escribir salida
        report_content = "\n".join(output)
        
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report_content)
            self.stdout.write(f'Reporte guardado en: {output_file}')
        else:
            self.stdout.write("\n" + report_content)
    
    def _generate_csv_report(self, logs_query, output_file, include_details):
        """Genera un reporte en formato CSV."""
        if not output_file:
            output_file = f'audit_report_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv'
        
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'fecha', 'usuario', 'accion', 'recurso_tipo', 'recurso_id',
                'ip_address', 'exitoso', 'user_agent'
            ]
            
            if include_details:
                fieldnames.append('detalles')
            
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for log in logs_query.iterator(chunk_size=1000):
                row = {
                    'fecha': log.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    'usuario': log.agent.email if log.agent else 'Anónimo',
                    'accion': log.action,
                    'recurso_tipo': log.resource_type,
                    'recurso_id': log.resource_id or '',
                    'ip_address': log.ip_address,
                    'exitoso': 'Sí' if log.success else 'No',
                    'user_agent': log.user_agent[:100] + '...' if len(log.user_agent) > 100 else log.user_agent
                }
                
                if include_details:
                    row['detalles'] = json.dumps(log.details, ensure_ascii=False)
                
                writer.writerow(row)
        
        self.stdout.write(f'Reporte CSV guardado en: {output_file}')
    
    def _generate_json_report(self, logs_query, output_file, include_details):
        """Genera un reporte en formato JSON."""
        if not output_file:
            output_file = f'audit_report_{timezone.now().strftime("%Y%m%d_%H%M%S")}.json'
        
        report_data = {
            'generated_at': timezone.now().isoformat(),
            'total_records': logs_query.count(),
            'logs': []
        }
        
        for log in logs_query.iterator(chunk_size=1000):
            log_data = {
                'id': log.id,
                'timestamp': log.created_at.isoformat(),
                'user': {
                    'email': log.agent.email if log.agent else None,
                    'name': log.agent.get_full_name() if log.agent else None
                },
                'action': log.action,
                'resource_type': log.resource_type,
                'resource_id': log.resource_id,
                'ip_address': log.ip_address,
                'success': log.success,
                'user_agent': log.user_agent
            }
            
            if include_details:
                log_data['details'] = log.details
            
            report_data['logs'].append(log_data)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        self.stdout.write(f'Reporte JSON guardado en: {output_file}')
    
    def _get_daily_activity(self, logs_query):
        """Obtiene estadísticas de actividad por día."""
        from django.db.models import DateField
        from django.db.models.functions import Cast
        
        daily_stats = logs_query.extra(
            select={'date': 'DATE(created_at)'}
        ).values('date').annotate(
            count=Count('id')
        ).order_by('-date')[:14]  # Últimos 14 días
        
        return [(stat['date'], stat['count']) for stat in daily_stats]