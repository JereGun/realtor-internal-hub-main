"""
Tests para comandos de gestión Django.

Este módulo contiene tests unitarios para verificar el funcionamiento
correcto de los comandos de gestión personalizados.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from io import StringIO
from django.test import TestCase
from django.core.management import call_command
from django.core.management.base import CommandError
from django.contrib.contenttypes.models import ContentType

from agents.models import Agent, Role, Permission, AgentRole
from agents.management.commands.create_initial_roles import Command


class CreateInitialRolesCommandTest(TestCase):
    """Tests para el comando create_initial_roles."""
    
    def setUp(self):
        """Configuración inicial para los tests."""
        # Crear usuario de prueba
        self.agent = Agent.objects.create_user(
            username='test_agent',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='Agent',
            license_number='TEST001'
        )
        
        # Crear segundo usuario sin roles
        self.agent_without_role = Agent.objects.create_user(
            username='no_role_agent',
            email='norole@example.com',
            password='testpass123',
            first_name='No Role',
            last_name='Agent',
            license_number='TEST002'
        )
    
    def test_command_creates_permissions(self):
        """Test: El comando crea permisos correctamente."""
        # Verificar que no existen permisos inicialmente
        initial_count = Permission.objects.count()
        
        # Ejecutar comando
        out = StringIO()
        call_command('create_initial_roles', stdout=out, verbosity=2)
        
        # Verificar que se crearon permisos
        final_count = Permission.objects.count()
        self.assertGreater(final_count, initial_count)
        
        # Verificar que se crearon permisos específicos
        self.assertTrue(Permission.objects.filter(codename='view_agent_profile').exists())
        self.assertTrue(Permission.objects.filter(codename='view_property').exists())
        self.assertTrue(Permission.objects.filter(codename='add_property').exists())
        
        # Verificar output
        output = out.getvalue()
        self.assertIn('Creando permisos del sistema', output)
        self.assertIn('creados', output)
    
    def test_command_creates_roles(self):
        """Test: El comando crea roles correctamente."""
        # Verificar que no existen roles inicialmente
        initial_count = Role.objects.count()
        
        # Ejecutar comando
        out = StringIO()
        call_command('create_initial_roles', stdout=out, verbosity=2)
        
        # Verificar que se crearon roles
        final_count = Role.objects.count()
        self.assertGreater(final_count, initial_count)
        
        # Verificar que se crearon roles específicos
        self.assertTrue(Role.objects.filter(name='Agente Básico').exists())
        self.assertTrue(Role.objects.filter(name='Supervisor').exists())
        self.assertTrue(Role.objects.filter(name='Administrador').exists())
        
        # Verificar que son roles del sistema
        basic_role = Role.objects.get(name='Agente Básico')
        self.assertTrue(basic_role.is_system_role)
        
        # Verificar output
        output = out.getvalue()
        self.assertIn('Creando roles del sistema', output)
    
    def test_command_assigns_permissions_to_roles(self):
        """Test: El comando asigna permisos a roles correctamente."""
        # Ejecutar comando
        out = StringIO()
        call_command('create_initial_roles', stdout=out, verbosity=2)
        
        # Verificar asignaciones de permisos
        basic_role = Role.objects.get(name='Agente Básico')
        admin_role = Role.objects.get(name='Administrador')
        
        # Verificar que el rol básico tiene permisos básicos
        self.assertTrue(basic_role.permissions.filter(codename='view_agent_profile').exists())
        self.assertTrue(basic_role.permissions.filter(codename='view_property').exists())
        
        # Verificar que el administrador tiene más permisos
        admin_permissions_count = admin_role.permissions.count()
        basic_permissions_count = basic_role.permissions.count()
        self.assertGreater(admin_permissions_count, basic_permissions_count)
        
        # Verificar output
        output = out.getvalue()
        self.assertIn('Asignando permisos a roles', output)
    
    def test_command_assigns_basic_role_to_users(self):
        """Test: El comando asigna rol básico a usuarios sin roles."""
        # Verificar que el usuario no tiene roles inicialmente
        self.assertFalse(AgentRole.objects.filter(agent=self.agent_without_role).exists())
        
        # Ejecutar comando con asignación de rol básico
        out = StringIO()
        call_command('create_initial_roles', '--assign-basic-role', stdout=out, verbosity=2)
        
        # Verificar que se asignó el rol básico
        self.assertTrue(
            AgentRole.objects.filter(
                agent=self.agent_without_role,
                role__name='Agente Básico',
                is_active=True
            ).exists()
        )
        
        # Verificar output
        output = out.getvalue()
        self.assertIn('Asignando rol básico a usuarios sin roles', output)
    
    def test_command_dry_run_mode(self):
        """Test: El comando en modo dry-run no hace cambios reales."""
        # Contar elementos iniciales
        initial_permissions = Permission.objects.count()
        initial_roles = Role.objects.count()
        initial_assignments = AgentRole.objects.count()
        
        # Ejecutar comando en modo dry-run
        out = StringIO()
        call_command(
            'create_initial_roles',
            '--dry-run',
            '--assign-basic-role',
            stdout=out,
            verbosity=2
        )
        
        # Verificar que no se hicieron cambios reales
        self.assertEqual(Permission.objects.count(), initial_permissions)
        self.assertEqual(Role.objects.count(), initial_roles)
        self.assertEqual(AgentRole.objects.count(), initial_assignments)
        
        # Verificar output de dry-run
        output = out.getvalue()
        self.assertIn('MODO DRY-RUN', output)
        self.assertIn('DRY-RUN completado exitosamente', output)
    
    def test_command_force_recreate(self):
        """Test: El comando con --force recrea roles existentes."""
        # Crear un rol existente con descripción diferente
        existing_role = Role.objects.create(
            name='Agente Básico',
            description='Descripción antigua',
            is_system_role=True
        )
        
        # Ejecutar comando con force
        out = StringIO()
        call_command('create_initial_roles', '--force', stdout=out, verbosity=2)
        
        # Verificar que se actualizó la descripción
        updated_role = Role.objects.get(name='Agente Básico')
        self.assertNotEqual(updated_role.description, 'Descripción antigua')
        self.assertIn('básico para agentes inmobiliarios', updated_role.description)
        
        # Verificar output
        output = out.getvalue()
        self.assertIn('Actualizado rol', output)
    
    def test_command_verbose_output(self):
        """Test: El comando con --verbose muestra información detallada."""
        # Ejecutar comando con verbose
        out = StringIO()
        call_command('create_initial_roles', '--verbose', stdout=out, verbosity=2)
        
        output = out.getvalue()
        
        # Verificar que muestra información detallada
        self.assertIn('Procesando módulo:', output)
        self.assertIn('Creado permiso:', output)
        self.assertIn('Creado rol:', output)
        self.assertIn('Procesando rol:', output)
        self.assertIn('Asignado permiso:', output)
    
    def test_command_handles_missing_modules(self):
        """Test: El comando maneja módulos faltantes correctamente."""
        # Ejecutar comando (algunos módulos pueden no existir)
        out = StringIO()
        call_command('create_initial_roles', '--verbose', stdout=out, verbosity=2)
        
        output = out.getvalue()
        
        # El comando debe completarse exitosamente incluso si faltan módulos
        self.assertIn('exitosamente', output)
        
        # Debe crear al menos los permisos básicos de agents
        self.assertTrue(Permission.objects.filter(codename='view_agent_profile').exists())
    
    def test_command_idempotent(self):
        """Test: El comando es idempotente (se puede ejecutar múltiples veces)."""
        # Ejecutar comando primera vez
        out1 = StringIO()
        call_command('create_initial_roles', stdout=out1, verbosity=1)
        
        # Contar elementos después de la primera ejecución
        permissions_count_1 = Permission.objects.count()
        roles_count_1 = Role.objects.count()
        
        # Ejecutar comando segunda vez
        out2 = StringIO()
        call_command('create_initial_roles', stdout=out2, verbosity=1)
        
        # Verificar que no se duplicaron elementos
        permissions_count_2 = Permission.objects.count()
        roles_count_2 = Role.objects.count()
        
        self.assertEqual(permissions_count_1, permissions_count_2)
        self.assertEqual(roles_count_1, roles_count_2)
        
        # Ambas ejecuciones deben ser exitosas
        self.assertIn('exitosamente', out1.getvalue())
        self.assertIn('exitosamente', out2.getvalue())
    
    def test_command_with_existing_role_assignments(self):
        """Test: El comando no duplica asignaciones de roles existentes."""
        # Crear rol básico manualmente
        basic_role = Role.objects.create(
            name='Agente Básico',
            description='Rol básico',
            is_system_role=True
        )
        
        # Asignar rol manualmente al usuario
        AgentRole.objects.create(
            agent=self.agent,
            role=basic_role,
            is_active=True
        )
        
        # Ejecutar comando con asignación de rol básico
        out = StringIO()
        call_command('create_initial_roles', '--assign-basic-role', stdout=out, verbosity=2)
        
        # Verificar que no se duplicó la asignación
        assignments = AgentRole.objects.filter(
            agent=self.agent,
            role__name='Agente Básico',
            is_active=True
        )
        self.assertEqual(assignments.count(), 1)
        
        # Verificar output
        output = out.getvalue()
        self.assertIn('Ya tiene rol básico', output)
    
    def test_command_error_handling(self):
        """Test: El comando maneja errores correctamente."""
        # Mock para simular error en la creación de permisos
        with patch('agents.models.Permission.objects.get_or_create', side_effect=Exception('Test error')):
            with self.assertRaises(CommandError):
                call_command('create_initial_roles')
    
    def test_command_help_text(self):
        """Test: El comando tiene texto de ayuda apropiado."""
        command = Command()
        self.assertIn('roles y permisos iniciales', command.help)
    
    def test_command_arguments(self):
        """Test: El comando acepta los argumentos correctos."""
        # Ejecutar comando con todos los argumentos
        out = StringIO()
        call_command(
            'create_initial_roles',
            '--force',
            '--assign-basic-role',
            '--dry-run',
            '--verbose',
            stdout=out,
            verbosity=0
        )
        
        output = out.getvalue()
        self.assertIn('DRY-RUN', output)
    
    def test_permission_content_types(self):
        """Test: Los permisos se crean con content types correctos."""
        # Ejecutar comando
        call_command('create_initial_roles', verbosity=0)
        
        # Verificar content types de permisos
        agent_permission = Permission.objects.get(codename='view_agent_profile')
        agent_content_type = ContentType.objects.get_for_model(Agent)
        
        self.assertEqual(agent_permission.content_type, agent_content_type)
    
    def test_role_permissions_mapping(self):
        """Test: Los roles tienen los permisos correctos asignados."""
        # Ejecutar comando
        call_command('create_initial_roles', verbosity=0)
        
        # Verificar mapeo específico
        basic_role = Role.objects.get(name='Agente Básico')
        admin_role = Role.objects.get(name='Administrador')
        readonly_role = Role.objects.get(name='Solo Lectura')
        
        # Agente Básico debe tener permisos básicos
        self.assertTrue(basic_role.permissions.filter(codename='view_property').exists())
        self.assertTrue(basic_role.permissions.filter(codename='add_property').exists())
        
        # Administrador debe tener permisos de gestión
        self.assertTrue(admin_role.permissions.filter(codename='manage_agents').exists())
        self.assertTrue(admin_role.permissions.filter(codename='assign_roles').exists())
        
        # Solo Lectura debe tener solo permisos de visualización
        readonly_permissions = readonly_role.permissions.all()
        for perm in readonly_permissions:
            self.assertTrue(perm.codename.startswith('view_'))
    
    def test_users_without_roles_detection(self):
        """Test: El comando detecta correctamente usuarios sin roles."""
        # Crear usuario con rol inactivo
        basic_role = Role.objects.create(name='Test Role', is_system_role=True)
        AgentRole.objects.create(
            agent=self.agent,
            role=basic_role,
            is_active=False  # Rol inactivo
        )
        
        # Ejecutar comando
        out = StringIO()
        call_command('create_initial_roles', '--assign-basic-role', '--verbose', stdout=out, verbosity=2)
        
        # Verificar que detectó al usuario con rol inactivo
        output = out.getvalue()
        self.assertIn(self.agent.email, output)
        
        # Verificar que se asignó el rol básico
        self.assertTrue(
            AgentRole.objects.filter(
                agent=self.agent,
                role__name='Agente Básico',
                is_active=True
            ).exists()
        )