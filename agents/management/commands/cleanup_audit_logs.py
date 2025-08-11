"""
Comando de gestión Django para limpiar logs de auditoría antiguos.

Este comando permite mantener la base de datos limpia eliminando
logs de auditoría antiguos según políticas configurables.
"""

import logging
from datetime import timedelta
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db import transaction
from django.conf import settings

from agents.models import AuditLog


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Comando para limpiar logs de auditoría antiguos.
    
    Uso:
        python manage.py cleanup_audit_logs --days 90
        python manage.py cleanup_audit_logs --days 30 --dry-run
        python manage.py cleanup_audit_logs --keep-critical
    """
    
    help = 'Limpia logs de auditoría antiguos para mantener la base de datos optimizada'
    
    def add_arguments(self, parser):
        """Añade argumentos al comando."""
        parser.add_argument(
            '--days',
            type=int,
            default=90,
            help='Número de días de logs a mantener (por defecto: 90)'
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Mostrar qué se eliminaría sin hacer cambios reales'
        )
        
        parser.add_argument(
            '--keep-critical',
            action='store_true',
            help='Mantener logs críticos de seguridad independientemente de la fecha'
        )
        
        parser.add_argument(
            '--batch-size',
            type=int,
            default=1000,
            help='Tamaño del lote para eliminación (por defecto: 1000)'
        )
        
        parser.add_argument(
            '--force',
            action='store_true',
            help='Forzar eliminación sin confirmación'
        )
    
    def handle(self, *args, **options):
        """Ejecuta el comando de limpieza."""
        days = options['days']
        dry_run = options['dry_run']
        keep_critical = options['keep_critical']
        batch_size = options['batch_size']
        force = options['force']
        
        # Validar argumentos
        if days <= 0:
            raise CommandError('El número de días debe ser mayor a 0')
        
        if batch_size <= 0:
            raise CommandError('El tamaño del lote debe ser mayor a 0')
        
        # Calcular fecha límite
        cutoff_date = timezone.now() - timedelta(days=days)
        
        self.stdout.write(
            self.style.SUCCESS(f'Iniciando limpieza de logs de auditoría...')
        )
        self.stdout.write(f'Fecha límite: {cutoff_date.strftime("%Y-%m-%d %H:%M:%S")}')
        
        # Obtener logs a eliminar
        logs_query = AuditLog.objects.filter(created_at__lt=cutoff_date)
        
        # Excluir logs críticos si se especifica
        if keep_critical:
            critical_actions = [
                'login', 'logout', 'password_change', 'password_reset',
                '2fa_enabled', '2fa_disabled', 'account_locked', 'account_unlocked',
                'suspicious_activity', 'security_settings_change'
            ]
            logs_query = logs_query.exclude(action__in=critical_actions)
            self.stdout.write(f'Manteniendo logs críticos de seguridad')
        
        # Contar logs a eliminar
        total_logs = logs_query.count()
        
        if total_logs == 0:
            self.stdout.write(
                self.style.WARNING('No se encontraron logs para eliminar')
            )
            return
        
        self.stdout.write(f'Logs encontrados para eliminación: {total_logs:,}')
        
        # Mostrar estadísticas por tipo de acción
        self._show_statistics(logs_query)
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('Modo dry-run: No se realizarán cambios')
            )
            return
        
        # Confirmar eliminación
        if not force:
            confirm = input(f'¿Confirma la eliminación de {total_logs:,} logs? (y/N): ')
            if confirm.lower() not in ['y', 'yes', 'sí', 's']:
                self.stdout.write(
                    self.style.WARNING('Operación cancelada por el usuario')
                )
                return
        
        # Realizar eliminación en lotes
        deleted_count = self._delete_in_batches(logs_query, batch_size)
        
        self.stdout.write(
            self.style.SUCCESS(f'Eliminados {deleted_count:,} logs de auditoría exitosamente')
        )
        
        # Mostrar estadísticas finales
        remaining_logs = AuditLog.objects.count()
        self.stdout.write(f'Logs restantes en el sistema: {remaining_logs:,}')
    
    def _show_statistics(self, logs_query):
        """Muestra estadísticas de los logs a eliminar."""
        self.stdout.write('\nEstadísticas de logs a eliminar:')
        self.stdout.write('-' * 40)
        
        # Estadísticas por acción
        action_stats = logs_query.values('action').annotate(
            count=models.Count('id')
        ).order_by('-count')[:10]
        
        for stat in action_stats:
            action = stat['action']
            count = stat['count']
            self.stdout.write(f'{action:25} {count:>8,}')
        
        # Estadísticas por éxito/fallo
        success_stats = logs_query.values('success').annotate(
            count=models.Count('id')
        )
        
        self.stdout.write('\nPor resultado:')
        for stat in success_stats:
            result = 'Exitosos' if stat['success'] else 'Fallidos'
            count = stat['count']
            self.stdout.write(f'{result:25} {count:>8,}')
        
        # Estadísticas por usuario
        user_stats = logs_query.exclude(agent=None).values(
            'agent__email'
        ).annotate(
            count=models.Count('id')
        ).order_by('-count')[:5]
        
        if user_stats:
            self.stdout.write('\nTop 5 usuarios:')
            for stat in user_stats:
                email = stat['agent__email']
                count = stat['count']
                self.stdout.write(f'{email:25} {count:>8,}')
        
        self.stdout.write('-' * 40)
    
    def _delete_in_batches(self, logs_query, batch_size):
        """Elimina logs en lotes para evitar problemas de memoria."""
        deleted_count = 0
        
        while True:
            # Obtener IDs del siguiente lote
            batch_ids = list(
                logs_query.values_list('id', flat=True)[:batch_size]
            )
            
            if not batch_ids:
                break
            
            # Eliminar lote
            with transaction.atomic():
                batch_deleted = AuditLog.objects.filter(
                    id__in=batch_ids
                ).delete()[0]
                
                deleted_count += batch_deleted
                
                self.stdout.write(
                    f'Eliminados {deleted_count:,} logs...',
                    ending='\r'
                )
        
        self.stdout.write('')  # Nueva línea
        return deleted_count


# Importar models después de la definición de la clase para evitar imports circulares
from django.db import models