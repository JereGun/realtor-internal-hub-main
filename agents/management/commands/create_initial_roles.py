"""
Comando de gestión Django para crear roles y permisos iniciales del sistema.

Este comando crea los roles básicos del sistema con sus permisos correspondientes
y asigna automáticamente el rol "Agente Básico" a usuarios existentes que no tengan roles.
"""

import logging
from typing import Dict, List, Any
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError

from agents.models import Agent, Role, Permission, AgentRole
from agents.services.role_permission_service import RolePermissionService


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Comando para crear roles y permisos iniciales del sistema.
    
    Este comando:
    1. Crea los roles básicos del sistema
    2. Crea los permisos necesarios para cada módulo
    3. Asigna permisos a los roles correspondientes
    4. Asigna el rol "Agente Básico" a usuarios sin roles
    """
    
    help = 'Crea roles y permisos iniciales del sistema'
    
    def add_arguments(self, parser):
        """Añade argumentos al comando."""
        parser.add_argument(
            '--force',
            action='store_true',
            help='Fuerza la recreación de roles existentes',
        )
        
        parser.add_argument(
            '--assign-basic-role',
            action='store_true',
            help='Asigna rol básico a usuarios sin roles',
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Muestra qué se haría sin ejecutar cambios',
        )
        
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Muestra información detallada',
        )
    
    def handle(self, *args, **options):
        """Ejecuta el comando."""
        self.verbosity = options.get('verbosity', 1)
        self.force = options.get('force', False)
        self.assign_basic_role = options.get('assign_basic_role', False)
        self.dry_run = options.get('dry_run', False)
        self.verbose = options.get('verbose', False)
        
        if self.dry_run:
            self.stdout.write(
                self.style.WARNING('MODO DRY-RUN: No se realizarán cambios reales')
            )
        
        try:
            with transaction.atomic():
                # Crear permisos del sistema
                self.create_system_permissions()
                
                # Crear roles del sistema
                self.create_system_roles()
                
                # Asignar permisos a roles
                self.assign_permissions_to_roles()
                
                # Asignar rol básico a usuarios sin roles
                if self.assign_basic_role:
                    self.assign_basic_role_to_users()
                
                if self.dry_run:
                    # Hacer rollback en dry-run
                    transaction.set_rollback(True)
                    self.stdout.write(
                        self.style.SUCCESS('DRY-RUN completado exitosamente')
                    )
                else:
                    self.stdout.write(
                        self.style.SUCCESS('Roles y permisos creados exitosamente')
                    )
                
        except Exception as e:
            logger.error(f"Error ejecutando comando create_initial_roles: {str(e)}")
            raise CommandError(f'Error creando roles: {str(e)}')
    
    def create_system_permissions(self):
        """Crea los permisos básicos del sistema."""
        self.stdout.write('Creando permisos del sistema...')
        
        # Definir permisos por módulo
        permissions_data = self.get_permissions_data()
        
        created_count = 0
        updated_count = 0
        
        for module_name, perms in permissions_data.items():
            if self.verbose:
                self.stdout.write(f'  Procesando módulo: {module_name}')
            
            # Obtener content type para el módulo
            try:
                if module_name == 'agents':
                    content_type = ContentType.objects.get_for_model(Agent)
                elif module_name == 'properties':
                    # Importar dinámicamente si existe
                    try:
                        from properties.models import Property
                        content_type = ContentType.objects.get_for_model(Property)
                    except ImportError:
                        if self.verbose:
                            self.stdout.write(f'    Módulo {module_name} no encontrado, omitiendo...')
                        continue
                elif module_name == 'contracts':
                    try:
                        from contracts.models import Contract
                        content_type = ContentType.objects.get_for_model(Contract)
                    except ImportError:
                        if self.verbose:
                            self.stdout.write(f'    Módulo {module_name} no encontrado, omitiendo...')
                        continue
                elif module_name == 'customers':
                    try:
                        from customers.models import Customer
                        content_type = ContentType.objects.get_for_model(Customer)
                    except ImportError:
                        if self.verbose:
                            self.stdout.write(f'    Módulo {module_name} no encontrado, omitiendo...')
                        continue
                elif module_name == 'payments':
                    try:
                        from payments.models import Payment
                        content_type = ContentType.objects.get_for_model(Payment)
                    except ImportError:
                        if self.verbose:
                            self.stdout.write(f'    Módulo {module_name} no encontrado, omitiendo...')
                        continue
                else:
                    # Usar Agent como fallback
                    content_type = ContentType.objects.get_for_model(Agent)
                
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f'    Error obteniendo content type para {module_name}: {str(e)}')
                )
                continue
            
            # Crear permisos
            for perm_data in perms:
                codename = perm_data['codename']
                name = perm_data['name']
                description = perm_data.get('description', '')
                
                if not self.dry_run:
                    permission, created = Permission.objects.get_or_create(
                        codename=codename,
                        defaults={
                            'name': name,
                            'content_type': content_type,
                            'description': description,
                        }
                    )
                    
                    if created:
                        created_count += 1
                        if self.verbose:
                            self.stdout.write(f'    ✓ Creado permiso: {codename}')
                    else:
                        # Actualizar si es necesario
                        if permission.name != name or permission.description != description:
                            permission.name = name
                            permission.description = description
                            permission.save()
                            updated_count += 1
                            if self.verbose:
                                self.stdout.write(f'    ↻ Actualizado permiso: {codename}')
                        elif self.verbose:
                            self.stdout.write(f'    - Ya existe permiso: {codename}')
                else:
                    # Dry run
                    exists = Permission.objects.filter(codename=codename).exists()
                    if exists:
                        if self.verbose:
                            self.stdout.write(f'    - Ya existe permiso: {codename}')
                    else:
                        created_count += 1
                        if self.verbose:
                            self.stdout.write(f'    ✓ Se crearía permiso: {codename}')
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Permisos procesados: {created_count} creados, {updated_count} actualizados'
            )
        )
    
    def create_system_roles(self):
        """Crea los roles básicos del sistema."""
        self.stdout.write('Creando roles del sistema...')
        
        roles_data = self.get_roles_data()
        
        created_count = 0
        updated_count = 0
        
        for role_data in roles_data:
            name = role_data['name']
            description = role_data['description']
            
            if not self.dry_run:
                role, created = Role.objects.get_or_create(
                    name=name,
                    defaults={
                        'description': description,
                        'is_system_role': True,
                    }
                )
                
                if created:
                    created_count += 1
                    if self.verbose:
                        self.stdout.write(f'  ✓ Creado rol: {name}')
                else:
                    # Actualizar descripción si es necesario
                    if role.description != description:
                        role.description = description
                        role.save()
                        updated_count += 1
                        if self.verbose:
                            self.stdout.write(f'  ↻ Actualizado rol: {name}')
                    elif self.verbose:
                        self.stdout.write(f'  - Ya existe rol: {name}')
            else:
                # Dry run
                exists = Role.objects.filter(name=name).exists()
                if exists:
                    if self.verbose:
                        self.stdout.write(f'  - Ya existe rol: {name}')
                else:
                    created_count += 1
                    if self.verbose:
                        self.stdout.write(f'  ✓ Se crearía rol: {name}')
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Roles procesados: {created_count} creados, {updated_count} actualizados'
            )
        )
    
    def assign_permissions_to_roles(self):
        """Asigna permisos a los roles correspondientes."""
        self.stdout.write('Asignando permisos a roles...')
        
        role_permissions = self.get_role_permissions_mapping()
        
        assigned_count = 0
        
        for role_name, permission_codenames in role_permissions.items():
            if not self.dry_run:
                try:
                    role = Role.objects.get(name=role_name)
                except Role.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(f'  Rol no encontrado: {role_name}')
                    )
                    continue
                
                if self.verbose:
                    self.stdout.write(f'  Procesando rol: {role_name}')
                
                for codename in permission_codenames:
                    try:
                        permission = Permission.objects.get(codename=codename)
                        
                        # Verificar si ya tiene el permiso
                        if not role.permissions.filter(id=permission.id).exists():
                            role.permissions.add(permission)
                            assigned_count += 1
                            if self.verbose:
                                self.stdout.write(f'    ✓ Asignado permiso: {codename}')
                        elif self.verbose:
                            self.stdout.write(f'    - Ya tiene permiso: {codename}')
                            
                    except Permission.DoesNotExist:
                        if self.verbose:
                            self.stdout.write(
                                self.style.WARNING(f'    Permiso no encontrado: {codename}')
                            )
                        continue
            else:
                # Dry run
                if self.verbose:
                    self.stdout.write(f'  Se procesaría rol: {role_name}')
                    for codename in permission_codenames:
                        self.stdout.write(f'    ✓ Se asignaría permiso: {codename}')
                assigned_count += len(permission_codenames)
        
        self.stdout.write(
            self.style.SUCCESS(f'Permisos asignados: {assigned_count}')
        )
    
    def assign_basic_role_to_users(self):
        """Asigna el rol básico a usuarios que no tienen roles."""
        self.stdout.write('Asignando rol básico a usuarios sin roles...')
        
        try:
            if not self.dry_run:
                basic_role = Role.objects.get(name='Agente Básico')
            else:
                # En dry run, verificar que existe
                if not Role.objects.filter(name='Agente Básico').exists():
                    self.stdout.write(
                        self.style.WARNING('  Rol "Agente Básico" no existe')
                    )
                    return
        except Role.DoesNotExist:
            self.stdout.write(
                self.style.WARNING('  Rol "Agente Básico" no encontrado')
            )
            return
        
        # Obtener usuarios sin roles activos
        users_without_roles = Agent.objects.filter(
            agentrole__isnull=True
        ).distinct() | Agent.objects.exclude(
            agentrole__is_active=True
        ).distinct()
        
        assigned_count = 0
        
        for agent in users_without_roles:
            if not self.dry_run:
                # Verificar que no tenga ya el rol básico activo
                if not AgentRole.objects.filter(
                    agent=agent,
                    role=basic_role,
                    is_active=True
                ).exists():
                    AgentRole.objects.create(
                        agent=agent,
                        role=basic_role,
                        is_active=True
                    )
                    assigned_count += 1
                    if self.verbose:
                        self.stdout.write(f'  ✓ Asignado rol básico a: {agent.email}')
                elif self.verbose:
                    self.stdout.write(f'  - Ya tiene rol básico: {agent.email}')
            else:
                # Dry run
                assigned_count += 1
                if self.verbose:
                    self.stdout.write(f'  ✓ Se asignaría rol básico a: {agent.email}')
        
        self.stdout.write(
            self.style.SUCCESS(f'Rol básico asignado a {assigned_count} usuarios')
        )
    
    def get_permissions_data(self) -> Dict[str, List[Dict[str, str]]]:
        """
        Obtiene la definición de permisos por módulo.
        
        Returns:
            Dict: Permisos organizados por módulo
        """
        return {
            'agents': [
                {
                    'codename': 'view_agent_profile',
                    'name': 'Can view agent profile',
                    'description': 'Permite ver perfiles de agentes'
                },
                {
                    'codename': 'change_own_profile',
                    'name': 'Can change own profile',
                    'description': 'Permite modificar el propio perfil'
                },
                {
                    'codename': 'view_all_agents',
                    'name': 'Can view all agents',
                    'description': 'Permite ver todos los agentes'
                },
                {
                    'codename': 'manage_agents',
                    'name': 'Can manage agents',
                    'description': 'Permite gestionar agentes (crear, editar, desactivar)'
                },
                {
                    'codename': 'assign_roles',
                    'name': 'Can assign roles',
                    'description': 'Permite asignar roles a usuarios'
                },
                {
                    'codename': 'view_audit_logs',
                    'name': 'Can view audit logs',
                    'description': 'Permite ver logs de auditoría'
                },
                {
                    'codename': 'manage_security_settings',
                    'name': 'Can manage security settings',
                    'description': 'Permite gestionar configuraciones de seguridad'
                },
            ],
            'properties': [
                {
                    'codename': 'view_property',
                    'name': 'Can view property',
                    'description': 'Permite ver propiedades'
                },
                {
                    'codename': 'add_property',
                    'name': 'Can add property',
                    'description': 'Permite agregar propiedades'
                },
                {
                    'codename': 'change_own_property',
                    'name': 'Can change own property',
                    'description': 'Permite modificar propias propiedades'
                },
                {
                    'codename': 'change_any_property',
                    'name': 'Can change any property',
                    'description': 'Permite modificar cualquier propiedad'
                },
                {
                    'codename': 'delete_property',
                    'name': 'Can delete property',
                    'description': 'Permite eliminar propiedades'
                },
                {
                    'codename': 'publish_property',
                    'name': 'Can publish property',
                    'description': 'Permite publicar propiedades'
                },
            ],
            'contracts': [
                {
                    'codename': 'view_contract',
                    'name': 'Can view contract',
                    'description': 'Permite ver contratos'
                },
                {
                    'codename': 'add_contract',
                    'name': 'Can add contract',
                    'description': 'Permite crear contratos'
                },
                {
                    'codename': 'change_own_contract',
                    'name': 'Can change own contract',
                    'description': 'Permite modificar propios contratos'
                },
                {
                    'codename': 'change_any_contract',
                    'name': 'Can change any contract',
                    'description': 'Permite modificar cualquier contrato'
                },
                {
                    'codename': 'approve_contract',
                    'name': 'Can approve contract',
                    'description': 'Permite aprobar contratos'
                },
                {
                    'codename': 'cancel_contract',
                    'name': 'Can cancel contract',
                    'description': 'Permite cancelar contratos'
                },
            ],
            'customers': [
                {
                    'codename': 'view_customer',
                    'name': 'Can view customer',
                    'description': 'Permite ver clientes'
                },
                {
                    'codename': 'add_customer',
                    'name': 'Can add customer',
                    'description': 'Permite agregar clientes'
                },
                {
                    'codename': 'change_customer',
                    'name': 'Can change customer',
                    'description': 'Permite modificar clientes'
                },
                {
                    'codename': 'delete_customer',
                    'name': 'Can delete customer',
                    'description': 'Permite eliminar clientes'
                },
            ],
            'payments': [
                {
                    'codename': 'view_payment',
                    'name': 'Can view payment',
                    'description': 'Permite ver pagos'
                },
                {
                    'codename': 'add_payment',
                    'name': 'Can add payment',
                    'description': 'Permite registrar pagos'
                },
                {
                    'codename': 'change_payment',
                    'name': 'Can change payment',
                    'description': 'Permite modificar pagos'
                },
                {
                    'codename': 'approve_payment',
                    'name': 'Can approve payment',
                    'description': 'Permite aprobar pagos'
                },
            ],
            'reports': [
                {
                    'codename': 'view_basic_reports',
                    'name': 'Can view basic reports',
                    'description': 'Permite ver reportes básicos'
                },
                {
                    'codename': 'view_advanced_reports',
                    'name': 'Can view advanced reports',
                    'description': 'Permite ver reportes avanzados'
                },
                {
                    'codename': 'export_reports',
                    'name': 'Can export reports',
                    'description': 'Permite exportar reportes'
                },
            ],
        }
    
    def get_roles_data(self) -> List[Dict[str, str]]:
        """
        Obtiene la definición de roles del sistema.
        
        Returns:
            List: Lista de roles con sus descripciones
        """
        return [
            {
                'name': 'Agente Básico',
                'description': 'Rol básico para agentes inmobiliarios con permisos limitados'
            },
            {
                'name': 'Agente Senior',
                'description': 'Agente con experiencia y permisos adicionales'
            },
            {
                'name': 'Supervisor',
                'description': 'Supervisor de agentes con permisos de gestión'
            },
            {
                'name': 'Administrador',
                'description': 'Administrador del sistema con todos los permisos'
            },
            {
                'name': 'Solo Lectura',
                'description': 'Acceso de solo lectura al sistema'
            },
        ]
    
    def get_role_permissions_mapping(self) -> Dict[str, List[str]]:
        """
        Obtiene el mapeo de permisos por rol.
        
        Returns:
            Dict: Permisos asignados a cada rol
        """
        return {
            'Agente Básico': [
                # Permisos básicos de agente
                'view_agent_profile',
                'change_own_profile',
                'view_property',
                'add_property',
                'change_own_property',
                'view_customer',
                'add_customer',
                'change_customer',
                'view_contract',
                'add_contract',
                'change_own_contract',
                'view_payment',
                'add_payment',
                'view_basic_reports',
            ],
            'Agente Senior': [
                # Todos los permisos de Agente Básico más adicionales
                'view_agent_profile',
                'change_own_profile',
                'view_property',
                'add_property',
                'change_own_property',
                'publish_property',
                'view_customer',
                'add_customer',
                'change_customer',
                'delete_customer',
                'view_contract',
                'add_contract',
                'change_own_contract',
                'view_payment',
                'add_payment',
                'change_payment',
                'view_basic_reports',
                'view_advanced_reports',
                'export_reports',
            ],
            'Supervisor': [
                # Permisos de supervisión
                'view_agent_profile',
                'change_own_profile',
                'view_all_agents',
                'view_property',
                'add_property',
                'change_own_property',
                'change_any_property',
                'publish_property',
                'view_customer',
                'add_customer',
                'change_customer',
                'delete_customer',
                'view_contract',
                'add_contract',
                'change_own_contract',
                'change_any_contract',
                'approve_contract',
                'view_payment',
                'add_payment',
                'change_payment',
                'approve_payment',
                'view_basic_reports',
                'view_advanced_reports',
                'export_reports',
                'view_audit_logs',
            ],
            'Administrador': [
                # Todos los permisos del sistema
                'view_agent_profile',
                'change_own_profile',
                'view_all_agents',
                'manage_agents',
                'assign_roles',
                'view_property',
                'add_property',
                'change_own_property',
                'change_any_property',
                'delete_property',
                'publish_property',
                'view_customer',
                'add_customer',
                'change_customer',
                'delete_customer',
                'view_contract',
                'add_contract',
                'change_own_contract',
                'change_any_contract',
                'approve_contract',
                'cancel_contract',
                'view_payment',
                'add_payment',
                'change_payment',
                'approve_payment',
                'view_basic_reports',
                'view_advanced_reports',
                'export_reports',
                'view_audit_logs',
                'manage_security_settings',
            ],
            'Solo Lectura': [
                # Solo permisos de visualización
                'view_agent_profile',
                'view_property',
                'view_customer',
                'view_contract',
                'view_payment',
                'view_basic_reports',
            ],
        }