"""
Tests para RolePermissionService.
"""

from django.test import TestCase
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError

from agents.models import Agent, Role, Permission, AgentRole, AuditLog
from agents.services.role_permission_service import RolePermissionService


class RolePermissionServiceTest(TestCase):
    """Tests para RolePermissionService"""
    
    def setUp(self):
        self.service = RolePermissionService()
        
        # Crear usuarios de prueba
        self.agent = Agent.objects.create_user(
            username='test_agent',
            email='test@example.com',
            password='TestPassword123!',
            first_name='Test',
            last_name='Agent',
            license_number='LIC123'
        )
        
        self.admin_agent = Agent.objects.create_user(
            username='admin_agent',
            email='admin@example.com',
            password='AdminPassword123!',
            first_name='Admin',
            last_name='Agent',
            license_number='LIC456'
        )
        
        # Crear content type y permisos de prueba
        self.content_type = ContentType.objects.get_for_model(Agent)
        
        self.permission1 = Permission.objects.create(
            codename='view_agent',
            name='Can view agent',
            content_type=self.content_type,
            description='Permission to view agents'
        )
        
        self.permission2 = Permission.objects.create(
            codename='edit_agent',
            name='Can edit agent',
            content_type=self.content_type,
            description='Permission to edit agents'
        )
        
        # Crear roles de prueba
        self.basic_role = Role.objects.create(
            name='Basic Role',
            description='Basic role for testing',
            is_system_role=False
        )
        self.basic_role.permissions.add(self.permission1)
        
        self.admin_role = Role.objects.create(
            name='Admin Role',
            description='Admin role for testing',
            is_system_role=True
        )
        self.admin_role.permissions.add(self.permission1, self.permission2)
    
    def test_assign_role_success(self):
        """Test asignación exitosa de rol"""
        result = self.service.assign_role(self.agent, self.basic_role, self.admin_agent)
        
        self.assertTrue(result)
        
        # Verificar que se creó la asignación
        assignment = AgentRole.objects.filter(
            agent=self.agent,
            role=self.basic_role,
            is_active=True
        ).first()
        self.assertIsNotNone(assignment)
        self.assertEqual(assignment.assigned_by, self.admin_agent)
        
        # Verificar que se registró en auditoría
        audit_log = AuditLog.objects.filter(
            agent=self.admin_agent,
            action='role_assigned',
            resource_id=str(self.basic_role.id)
        ).first()
        self.assertIsNotNone(audit_log)
        self.assertEqual(audit_log.details['target_agent_email'], self.agent.email)
    
    def test_assign_role_already_assigned(self):
        """Test asignación de rol ya asignado"""
        # Asignar rol por primera vez
        self.service.assign_role(self.agent, self.basic_role)
        
        # Intentar asignar el mismo rol nuevamente
        result = self.service.assign_role(self.agent, self.basic_role)
        
        self.assertFalse(result)
        
        # Verificar que solo hay una asignación
        assignments_count = AgentRole.objects.filter(
            agent=self.agent,
            role=self.basic_role,
            is_active=True
        ).count()
        self.assertEqual(assignments_count, 1)
    
    def test_revoke_role_success(self):
        """Test revocación exitosa de rol"""
        # Asignar rol primero
        self.service.assign_role(self.agent, self.basic_role)
        
        # Revocar rol
        result = self.service.revoke_role(self.agent, self.basic_role, self.admin_agent)
        
        self.assertTrue(result)
        
        # Verificar que la asignación se desactivó
        assignment = AgentRole.objects.filter(
            agent=self.agent,
            role=self.basic_role
        ).first()
        self.assertIsNotNone(assignment)
        self.assertFalse(assignment.is_active)
        
        # Verificar que se registró en auditoría
        audit_log = AuditLog.objects.filter(
            agent=self.admin_agent,
            action='role_revoked',
            resource_id=str(self.basic_role.id)
        ).first()
        self.assertIsNotNone(audit_log)
    
    def test_revoke_role_not_assigned(self):
        """Test revocación de rol no asignado"""
        result = self.service.revoke_role(self.agent, self.basic_role)
        
        self.assertFalse(result)
    
    def test_check_permission_has_permission(self):
        """Test verificación de permiso que el usuario tiene"""
        # Asignar rol con permiso
        self.service.assign_role(self.agent, self.basic_role)
        
        # Verificar permiso
        has_permission = self.service.check_permission(self.agent, 'view_agent')
        
        self.assertTrue(has_permission)
    
    def test_check_permission_no_permission(self):
        """Test verificación de permiso que el usuario no tiene"""
        # Asignar rol con permiso limitado
        self.service.assign_role(self.agent, self.basic_role)
        
        # Verificar permiso que no tiene
        has_permission = self.service.check_permission(self.agent, 'edit_agent')
        
        self.assertFalse(has_permission)
    
    def test_check_permission_no_roles(self):
        """Test verificación de permiso sin roles asignados"""
        has_permission = self.service.check_permission(self.agent, 'view_agent')
        
        self.assertFalse(has_permission)
    
    def test_get_user_permissions(self):
        """Test obtención de permisos del usuario"""
        # Asignar rol con permisos
        self.service.assign_role(self.agent, self.admin_role)
        
        permissions = self.service.get_user_permissions(self.agent)
        
        # Verificar que obtiene los permisos correctos
        permission_codes = list(permissions.values_list('codename', flat=True))
        self.assertIn('view_agent', permission_codes)
        self.assertIn('edit_agent', permission_codes)
        self.assertEqual(len(permission_codes), 2)
    
    def test_get_user_permissions_no_roles(self):
        """Test obtención de permisos sin roles asignados"""
        permissions = self.service.get_user_permissions(self.agent)
        
        self.assertEqual(permissions.count(), 0)
    
    def test_get_user_roles(self):
        """Test obtención de roles del usuario"""
        # Asignar múltiples roles
        self.service.assign_role(self.agent, self.basic_role)
        self.service.assign_role(self.agent, self.admin_role)
        
        roles = self.service.get_user_roles(self.agent)
        
        # Verificar que obtiene ambos roles
        role_names = list(roles.values_list('name', flat=True))
        self.assertIn('Basic Role', role_names)
        self.assertIn('Admin Role', role_names)
        self.assertEqual(len(role_names), 2)
    
    def test_get_user_roles_inactive_role(self):
        """Test obtención de roles excluyendo roles inactivos"""
        # Asignar rol y luego revocarlo
        self.service.assign_role(self.agent, self.basic_role)
        self.service.revoke_role(self.agent, self.basic_role)
        
        roles = self.service.get_user_roles(self.agent)
        
        # No debería devolver roles inactivos
        self.assertEqual(roles.count(), 0)
    
    def test_create_custom_role_success(self):
        """Test creación exitosa de rol personalizado"""
        permissions = [self.permission1, self.permission2]
        
        role = self.service.create_custom_role(
            name='Custom Role',
            description='Custom role for testing',
            permissions=permissions,
            created_by=self.admin_agent
        )
        
        # Verificar que se creó correctamente
        self.assertEqual(role.name, 'Custom Role')
        self.assertEqual(role.description, 'Custom role for testing')
        self.assertFalse(role.is_system_role)
        
        # Verificar permisos asignados
        role_permissions = list(role.permissions.all())
        self.assertEqual(len(role_permissions), 2)
        self.assertIn(self.permission1, role_permissions)
        self.assertIn(self.permission2, role_permissions)
        
        # Verificar que se registró en auditoría
        audit_log = AuditLog.objects.filter(
            agent=self.admin_agent,
            action='role_created',
            resource_id=str(role.id)
        ).first()
        self.assertIsNotNone(audit_log)
    
    def test_create_custom_role_duplicate_name(self):
        """Test creación de rol con nombre duplicado"""
        with self.assertRaises(ValidationError) as context:
            self.service.create_custom_role(
                name='Basic Role',  # Nombre ya existe
                description='Duplicate role'
            )
        
        self.assertIn("Ya existe un rol con el nombre 'Basic Role'", str(context.exception))
    
    def test_create_permission_success(self):
        """Test creación exitosa de permiso"""
        permission = self.service.create_permission(
            codename='delete_agent',
            name='Can delete agent',
            content_type=self.content_type,
            description='Permission to delete agents'
        )
        
        # Verificar que se creó correctamente
        self.assertEqual(permission.codename, 'delete_agent')
        self.assertEqual(permission.name, 'Can delete agent')
        self.assertEqual(permission.content_type, self.content_type)
        self.assertEqual(permission.description, 'Permission to delete agents')
    
    def test_create_permission_duplicate_codename(self):
        """Test creación de permiso con código duplicado"""
        with self.assertRaises(ValidationError) as context:
            self.service.create_permission(
                codename='view_agent',  # Código ya existe
                name='Duplicate permission',
                content_type=self.content_type
            )
        
        self.assertIn("Ya existe un permiso con el código 'view_agent'", str(context.exception))
    
    def test_get_role_hierarchy(self):
        """Test obtención de jerarquía de roles"""
        # Asignar rol a usuario
        self.service.assign_role(self.agent, self.basic_role)
        
        hierarchy = self.service.get_role_hierarchy()
        
        # Verificar estructura
        self.assertIn('roles', hierarchy)
        self.assertIn('total_roles', hierarchy)
        self.assertIn('system_roles', hierarchy)
        self.assertIn('custom_roles', hierarchy)
        
        # Verificar datos de roles
        roles = hierarchy['roles']
        self.assertGreaterEqual(len(roles), 2)  # Al menos basic_role y admin_role
        
        # Buscar basic_role en la jerarquía
        basic_role_data = next((r for r in roles if r['name'] == 'Basic Role'), None)
        self.assertIsNotNone(basic_role_data)
        self.assertEqual(basic_role_data['users_count'], 1)
        self.assertGreaterEqual(len(basic_role_data['permissions']), 1)
    
    def test_get_permission_matrix(self):
        """Test obtención de matriz de permisos"""
        matrix = self.service.get_permission_matrix()
        
        # Verificar que contiene el content type
        content_type_name = self.content_type.name
        self.assertIn(content_type_name, matrix)
        
        # Verificar permisos
        permissions_data = matrix[content_type_name]
        self.assertIn('view_agent', permissions_data)
        self.assertIn('edit_agent', permissions_data)
        
        # Verificar estructura de permiso
        view_permission = permissions_data['view_agent']
        self.assertIn('permission_name', view_permission)
        self.assertIn('description', view_permission)
        self.assertIn('roles', view_permission)
        
        # Verificar que basic_role aparece en view_agent
        role_names = [r['name'] for r in view_permission['roles']]
        self.assertIn('Basic Role', role_names)
    
    def test_bulk_assign_roles(self):
        """Test asignación masiva de roles"""
        role_ids = [self.basic_role.id, self.admin_role.id]
        
        results = self.service.bulk_assign_roles(self.agent, role_ids, self.admin_agent)
        
        # Verificar resultados
        self.assertEqual(len(results['assigned']), 2)
        self.assertEqual(len(results['already_assigned']), 0)
        self.assertEqual(len(results['errors']), 0)
        
        # Verificar que se asignaron los roles
        assigned_roles = self.service.get_user_roles(self.agent)
        self.assertEqual(assigned_roles.count(), 2)
    
    def test_bulk_assign_roles_with_existing(self):
        """Test asignación masiva con roles ya asignados"""
        # Asignar un rol previamente
        self.service.assign_role(self.agent, self.basic_role)
        
        role_ids = [self.basic_role.id, self.admin_role.id]
        results = self.service.bulk_assign_roles(self.agent, role_ids)
        
        # Verificar resultados
        self.assertEqual(len(results['assigned']), 1)  # Solo admin_role
        self.assertEqual(len(results['already_assigned']), 1)  # basic_role ya asignado
        self.assertEqual(len(results['errors']), 0)
    
    def test_bulk_assign_roles_with_invalid_id(self):
        """Test asignación masiva con ID inválido"""
        role_ids = [self.basic_role.id, 99999]  # ID inexistente
        
        results = self.service.bulk_assign_roles(self.agent, role_ids)
        
        # Verificar resultados
        self.assertEqual(len(results['assigned']), 1)  # Solo basic_role
        self.assertEqual(len(results['already_assigned']), 0)
        self.assertEqual(len(results['errors']), 1)  # Error por ID inexistente
    
    def test_get_users_by_permission(self):
        """Test obtención de usuarios por permiso"""
        # Asignar roles a usuarios
        self.service.assign_role(self.agent, self.basic_role)  # Tiene view_agent
        self.service.assign_role(self.admin_agent, self.admin_role)  # Tiene view_agent y edit_agent
        
        # Obtener usuarios con permiso view_agent
        users_with_view = self.service.get_users_by_permission('view_agent')
        user_emails = list(users_with_view.values_list('email', flat=True))
        
        self.assertIn(self.agent.email, user_emails)
        self.assertIn(self.admin_agent.email, user_emails)
        self.assertEqual(len(user_emails), 2)
        
        # Obtener usuarios con permiso edit_agent
        users_with_edit = self.service.get_users_by_permission('edit_agent')
        edit_user_emails = list(users_with_edit.values_list('email', flat=True))
        
        self.assertNotIn(self.agent.email, edit_user_emails)  # basic_role no tiene edit_agent
        self.assertIn(self.admin_agent.email, edit_user_emails)
        self.assertEqual(len(edit_user_emails), 1)
    
    def test_get_role_statistics(self):
        """Test obtención de estadísticas de roles"""
        # Asignar algunos roles
        self.service.assign_role(self.agent, self.basic_role)
        self.service.assign_role(self.admin_agent, self.admin_role)
        
        statistics = self.service.get_role_statistics()
        
        # Verificar estructura
        expected_keys = [
            'total_roles', 'system_roles', 'custom_roles', 'total_permissions',
            'users_with_roles', 'most_assigned_roles', 'permissions_by_content_type'
        ]
        for key in expected_keys:
            self.assertIn(key, statistics)
        
        # Verificar valores
        self.assertGreaterEqual(statistics['total_roles'], 2)
        self.assertGreaterEqual(statistics['total_permissions'], 2)
        self.assertEqual(statistics['users_with_roles'], 2)
        self.assertGreaterEqual(len(statistics['most_assigned_roles']), 1)
    
    def test_validate_role_assignment_valid(self):
        """Test validación de asignación de rol válida"""
        validation = self.service.validate_role_assignment(self.agent, self.basic_role)
        
        self.assertTrue(validation['valid'])
        self.assertEqual(len(validation['errors']), 0)
    
    def test_validate_role_assignment_already_assigned(self):
        """Test validación de rol ya asignado"""
        # Asignar rol primero
        self.service.assign_role(self.agent, self.basic_role)
        
        # Validar asignación del mismo rol
        validation = self.service.validate_role_assignment(self.agent, self.basic_role)
        
        self.assertFalse(validation['valid'])
        self.assertGreater(len(validation['errors']), 0)
        self.assertIn("ya tiene el rol", validation['errors'][0])
    
    def test_validate_role_assignment_inactive_user(self):
        """Test validación con usuario inactivo"""
        # Desactivar usuario
        self.agent.is_active = False
        self.agent.save()
        
        validation = self.service.validate_role_assignment(self.agent, self.basic_role)
        
        # Debería ser válido pero con advertencia
        self.assertTrue(validation['valid'])
        self.assertGreater(len(validation['warnings']), 0)
        self.assertIn("inactivo", validation['warnings'][0])
    
    def test_create_default_roles(self):
        """Test creación de roles por defecto"""
        # Limpiar roles existentes para la prueba
        Role.objects.all().delete()
        
        created_roles = self.service.create_default_roles()
        
        # Verificar que se crearon roles
        self.assertGreater(len(created_roles), 0)
        
        # Verificar que son roles del sistema
        for role in created_roles:
            self.assertTrue(role.is_system_role)
        
        # Verificar nombres esperados
        role_names = [role.name for role in created_roles]
        expected_names = ['Agente Básico', 'Supervisor', 'Administrador']
        for expected_name in expected_names:
            self.assertIn(expected_name, role_names)
    
    def test_create_default_roles_no_duplicates(self):
        """Test que no se crean roles duplicados"""
        # Crear roles por defecto por primera vez
        first_creation = self.service.create_default_roles()
        
        # Intentar crear nuevamente
        second_creation = self.service.create_default_roles()
        
        # La segunda vez no debería crear roles duplicados
        self.assertEqual(len(second_creation), 0)
    
    def test_roles_conflict_detection(self):
        """Test detección de conflictos entre roles"""
        # Crear roles conflictivos para la prueba
        admin_role = Role.objects.create(name='Admin', description='Admin role')
        readonly_role = Role.objects.create(name='ReadOnly', description='ReadOnly role')
        
        # Verificar conflicto
        has_conflict = self.service._roles_conflict(admin_role, readonly_role)
        self.assertTrue(has_conflict)
        
        # Verificar no conflicto
        no_conflict = self.service._roles_conflict(self.basic_role, self.admin_role)
        self.assertFalse(no_conflict)