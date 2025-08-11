"""
Tests para template tags y filtros de permisos.

Este módulo contiene tests unitarios para verificar el funcionamiento
correcto de los template tags y filtros de permisos y roles.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase, RequestFactory
from django.template import Context, Template
from django.contrib.auth.models import AnonymousUser
from django.template.context import RequestContext

from agents.models import Agent, Role, Permission, AgentRole
from agents.services.role_permission_service import RolePermissionService


class TemplateTagsTestCase(TestCase):
    """Clase base para tests de template tags."""
    
    def setUp(self):
        """Configuración inicial para los tests."""
        self.factory = RequestFactory()
        
        # Crear usuario de prueba
        self.agent = Agent.objects.create_user(
            username='test_agent',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='Agent',
            license_number='TEST001'
        )
        
        # Crear segundo usuario para tests
        self.other_agent = Agent.objects.create_user(
            username='other_agent',
            email='other@example.com',
            password='testpass123',
            first_name='Other',
            last_name='Agent',
            license_number='TEST002'
        )
        
        # Crear roles de prueba
        self.basic_role = Role.objects.create(
            name='Agente Básico',
            description='Rol básico para agentes',
            is_system_role=True
        )
        
        self.supervisor_role = Role.objects.create(
            name='Supervisor',
            description='Rol de supervisor',
            is_system_role=True
        )
        
        self.admin_role = Role.objects.create(
            name='Administrador',
            description='Rol de administrador',
            is_system_role=True
        )
        
        # Crear permisos de prueba
        from django.contrib.contenttypes.models import ContentType
        content_type = ContentType.objects.get_for_model(Agent)
        
        self.view_permission = Permission.objects.create(
            codename='view_test',
            name='Can view test',
            content_type=content_type
        )
        
        self.edit_permission = Permission.objects.create(
            codename='edit_test',
            name='Can edit test',
            content_type=content_type
        )
    
    def render_template(self, template_string, context_dict=None):
        """
        Helper para renderizar templates con contexto.
        
        Args:
            template_string: String del template
            context_dict: Diccionario de contexto
            
        Returns:
            str: Template renderizado
        """
        if context_dict is None:
            context_dict = {}
        
        # Crear request mock
        request = self.factory.get('/')
        request.user = context_dict.get('user', self.agent)
        context_dict['request'] = request
        
        template = Template(template_string)
        context = Context(context_dict)
        return template.render(context)


class HasPermissionTagTest(TemplateTagsTestCase):
    """Tests para el template tag has_permission."""
    
    def test_has_permission_with_permission(self):
        """Test: Usuario con permiso."""
        template_string = """
        {% load permission_tags %}
        {% has_permission 'view_test' as can_view %}
        {% if can_view %}YES{% else %}NO{% endif %}
        """
        
        # Mock del servicio de permisos
        with patch.object(RolePermissionService, 'check_permission', return_value=True):
            result = self.render_template(template_string, {'user': self.agent})
        
        self.assertIn('YES', result.strip())
    
    def test_has_permission_without_permission(self):
        """Test: Usuario sin permiso."""
        template_string = """
        {% load permission_tags %}
        {% has_permission 'view_test' as can_view %}
        {% if can_view %}YES{% else %}NO{% endif %}
        """
        
        # Mock del servicio de permisos
        with patch.object(RolePermissionService, 'check_permission', return_value=False):
            result = self.render_template(template_string, {'user': self.agent})
        
        self.assertIn('NO', result.strip())
    
    def test_has_permission_with_unauthenticated_user(self):
        """Test: Usuario no autenticado."""
        template_string = """
        {% load permission_tags %}
        {% has_permission 'view_test' as can_view %}
        {% if can_view %}YES{% else %}NO{% endif %}
        """
        
        result = self.render_template(template_string, {'user': AnonymousUser()})
        self.assertIn('NO', result.strip())
    
    def test_has_permission_without_request(self):
        """Test: Sin request en el contexto."""
        template_string = """
        {% load permission_tags %}
        {% has_permission 'view_test' as can_view %}
        {% if can_view %}YES{% else %}NO{% endif %}
        """
        
        template = Template(template_string)
        context = Context({'user': self.agent})  # Sin request
        result = template.render(context)
        
        self.assertIn('NO', result.strip())


class HasAnyPermissionTagTest(TemplateTagsTestCase):
    """Tests para el template tag has_any_permission."""
    
    def test_has_any_permission_with_one_permission(self):
        """Test: Usuario con uno de los permisos."""
        template_string = """
        {% load permission_tags %}
        {% has_any_permission 'view_test' 'edit_test' as can_access %}
        {% if can_access %}YES{% else %}NO{% endif %}
        """
        
        # Mock del servicio - primer permiso True, segundo False
        with patch.object(RolePermissionService, 'check_permission', side_effect=[True, False]):
            result = self.render_template(template_string, {'user': self.agent})
        
        self.assertIn('YES', result.strip())
    
    def test_has_any_permission_without_permissions(self):
        """Test: Usuario sin ningún permiso."""
        template_string = """
        {% load permission_tags %}
        {% has_any_permission 'view_test' 'edit_test' as can_access %}
        {% if can_access %}YES{% else %}NO{% endif %}
        """
        
        # Mock del servicio - ambos permisos False
        with patch.object(RolePermissionService, 'check_permission', return_value=False):
            result = self.render_template(template_string, {'user': self.agent})
        
        self.assertIn('NO', result.strip())


class HasAllPermissionsTagTest(TemplateTagsTestCase):
    """Tests para el template tag has_all_permissions."""
    
    def test_has_all_permissions_with_all_permissions(self):
        """Test: Usuario con todos los permisos."""
        template_string = """
        {% load permission_tags %}
        {% has_all_permissions 'view_test' 'edit_test' as can_manage %}
        {% if can_manage %}YES{% else %}NO{% endif %}
        """
        
        # Mock del servicio - ambos permisos True
        with patch.object(RolePermissionService, 'check_permission', return_value=True):
            result = self.render_template(template_string, {'user': self.agent})
        
        self.assertIn('YES', result.strip())
    
    def test_has_all_permissions_with_partial_permissions(self):
        """Test: Usuario con solo algunos permisos."""
        template_string = """
        {% load permission_tags %}
        {% has_all_permissions 'view_test' 'edit_test' as can_manage %}
        {% if can_manage %}YES{% else %}NO{% endif %}
        """
        
        # Mock del servicio - primer permiso True, segundo False
        with patch.object(RolePermissionService, 'check_permission', side_effect=[True, False]):
            result = self.render_template(template_string, {'user': self.agent})
        
        self.assertIn('NO', result.strip())


class HasRoleTagTest(TemplateTagsTestCase):
    """Tests para el template tag has_role."""
    
    def test_has_role_with_role(self):
        """Test: Usuario con el rol."""
        template_string = """
        {% load permission_tags %}
        {% has_role 'Administrador' as is_admin %}
        {% if is_admin %}YES{% else %}NO{% endif %}
        """
        
        # Mock del servicio de roles
        with patch.object(RolePermissionService, 'get_user_roles') as mock_get_roles:
            mock_get_roles.return_value = [self.admin_role]
            result = self.render_template(template_string, {'user': self.agent})
        
        self.assertIn('YES', result.strip())
    
    def test_has_role_without_role(self):
        """Test: Usuario sin el rol."""
        template_string = """
        {% load permission_tags %}
        {% has_role 'Administrador' as is_admin %}
        {% if is_admin %}YES{% else %}NO{% endif %}
        """
        
        # Mock del servicio de roles - sin roles
        with patch.object(RolePermissionService, 'get_user_roles') as mock_get_roles:
            mock_get_roles.return_value = [self.basic_role]
            result = self.render_template(template_string, {'user': self.agent})
        
        self.assertIn('NO', result.strip())


class HasAnyRoleTagTest(TemplateTagsTestCase):
    """Tests para el template tag has_any_role."""
    
    def test_has_any_role_with_one_role(self):
        """Test: Usuario con uno de los roles."""
        template_string = """
        {% load permission_tags %}
        {% has_any_role 'Supervisor' 'Administrador' as is_manager %}
        {% if is_manager %}YES{% else %}NO{% endif %}
        """
        
        # Mock del servicio de roles
        with patch.object(RolePermissionService, 'get_user_roles') as mock_get_roles:
            mock_get_roles.return_value = [self.supervisor_role]
            result = self.render_template(template_string, {'user': self.agent})
        
        self.assertIn('YES', result.strip())
    
    def test_has_any_role_without_roles(self):
        """Test: Usuario sin ninguno de los roles."""
        template_string = """
        {% load permission_tags %}
        {% has_any_role 'Supervisor' 'Administrador' as is_manager %}
        {% if is_manager %}YES{% else %}NO{% endif %}
        """
        
        # Mock del servicio de roles
        with patch.object(RolePermissionService, 'get_user_roles') as mock_get_roles:
            mock_get_roles.return_value = [self.basic_role]
            result = self.render_template(template_string, {'user': self.agent})
        
        self.assertIn('NO', result.strip())


class IsSuperuserTagTest(TemplateTagsTestCase):
    """Tests para el template tag is_superuser."""
    
    def test_is_superuser_with_superuser(self):
        """Test: Usuario superusuario."""
        template_string = """
        {% load permission_tags %}
        {% is_superuser as is_super %}
        {% if is_super %}YES{% else %}NO{% endif %}
        """
        
        # Hacer al usuario superusuario
        self.agent.is_superuser = True
        self.agent.save()
        
        result = self.render_template(template_string, {'user': self.agent})
        self.assertIn('YES', result.strip())
    
    def test_is_superuser_with_regular_user(self):
        """Test: Usuario regular."""
        template_string = """
        {% load permission_tags %}
        {% is_superuser as is_super %}
        {% if is_super %}YES{% else %}NO{% endif %}
        """
        
        result = self.render_template(template_string, {'user': self.agent})
        self.assertIn('NO', result.strip())


class IsStaffTagTest(TemplateTagsTestCase):
    """Tests para el template tag is_staff."""
    
    def test_is_staff_with_staff_user(self):
        """Test: Usuario staff."""
        template_string = """
        {% load permission_tags %}
        {% is_staff as is_staff_user %}
        {% if is_staff_user %}YES{% else %}NO{% endif %}
        """
        
        # Hacer al usuario staff
        self.agent.is_staff = True
        self.agent.save()
        
        result = self.render_template(template_string, {'user': self.agent})
        self.assertIn('YES', result.strip())
    
    def test_is_staff_with_regular_user(self):
        """Test: Usuario regular."""
        template_string = """
        {% load permission_tags %}
        {% is_staff as is_staff_user %}
        {% if is_staff_user %}YES{% else %}NO{% endif %}
        """
        
        result = self.render_template(template_string, {'user': self.agent})
        self.assertIn('NO', result.strip())


class IsAdminTagTest(TemplateTagsTestCase):
    """Tests para el template tag is_admin."""
    
    def test_is_admin_with_superuser(self):
        """Test: Superusuario es admin."""
        template_string = """
        {% load permission_tags %}
        {% is_admin as is_admin_user %}
        {% if is_admin_user %}YES{% else %}NO{% endif %}
        """
        
        # Hacer al usuario superusuario
        self.agent.is_superuser = True
        self.agent.save()
        
        result = self.render_template(template_string, {'user': self.agent})
        self.assertIn('YES', result.strip())
    
    def test_is_admin_with_admin_role(self):
        """Test: Usuario con rol de Administrador."""
        template_string = """
        {% load permission_tags %}
        {% is_admin as is_admin_user %}
        {% if is_admin_user %}YES{% else %}NO{% endif %}
        """
        
        # Mock del servicio de roles
        with patch.object(RolePermissionService, 'get_user_roles') as mock_get_roles:
            mock_get_roles.return_value = [self.admin_role]
            result = self.render_template(template_string, {'user': self.agent})
        
        self.assertIn('YES', result.strip())
    
    def test_is_admin_with_regular_user(self):
        """Test: Usuario regular no es admin."""
        template_string = """
        {% load permission_tags %}
        {% is_admin as is_admin_user %}
        {% if is_admin_user %}YES{% else %}NO{% endif %}
        """
        
        # Mock del servicio de roles
        with patch.object(RolePermissionService, 'get_user_roles') as mock_get_roles:
            mock_get_roles.return_value = [self.basic_role]
            result = self.render_template(template_string, {'user': self.agent})
        
        self.assertIn('NO', result.strip())


class GetUserRolesTagTest(TemplateTagsTestCase):
    """Tests para el template tag get_user_roles."""
    
    def test_get_user_roles_with_roles(self):
        """Test: Usuario con roles."""
        template_string = """
        {% load permission_tags %}
        {% get_user_roles as user_roles %}
        {% for role in user_roles %}{{ role }}{% if not forloop.last %},{% endif %}{% endfor %}
        """
        
        # Mock del servicio de roles
        with patch.object(RolePermissionService, 'get_user_roles') as mock_get_roles:
            mock_get_roles.return_value = [self.basic_role, self.supervisor_role]
            result = self.render_template(template_string, {'user': self.agent})
        
        self.assertIn('Agente Básico', result)
        self.assertIn('Supervisor', result)
    
    def test_get_user_roles_without_roles(self):
        """Test: Usuario sin roles."""
        template_string = """
        {% load permission_tags %}
        {% get_user_roles as user_roles %}
        {% if user_roles %}HAS_ROLES{% else %}NO_ROLES{% endif %}
        """
        
        # Mock del servicio de roles - sin roles
        with patch.object(RolePermissionService, 'get_user_roles') as mock_get_roles:
            mock_get_roles.return_value = []
            result = self.render_template(template_string, {'user': self.agent})
        
        self.assertIn('NO_ROLES', result.strip())


class GetUserPermissionsTagTest(TemplateTagsTestCase):
    """Tests para el template tag get_user_permissions."""
    
    def test_get_user_permissions_with_permissions(self):
        """Test: Usuario con permisos."""
        template_string = """
        {% load permission_tags %}
        {% get_user_permissions as user_permissions %}
        {% for perm in user_permissions %}{{ perm }}{% if not forloop.last %},{% endif %}{% endfor %}
        """
        
        # Mock del servicio de permisos
        with patch.object(RolePermissionService, 'get_user_permissions') as mock_get_perms:
            mock_get_perms.return_value = [self.view_permission, self.edit_permission]
            result = self.render_template(template_string, {'user': self.agent})
        
        self.assertIn('view_test', result)
        self.assertIn('edit_test', result)
    
    def test_get_user_permissions_without_permissions(self):
        """Test: Usuario sin permisos."""
        template_string = """
        {% load permission_tags %}
        {% get_user_permissions as user_permissions %}
        {% if user_permissions %}HAS_PERMS{% else %}NO_PERMS{% endif %}
        """
        
        # Mock del servicio de permisos - sin permisos
        with patch.object(RolePermissionService, 'get_user_permissions') as mock_get_perms:
            mock_get_perms.return_value = []
            result = self.render_template(template_string, {'user': self.agent})
        
        self.assertIn('NO_PERMS', result.strip())


class IsOwnerTagTest(TemplateTagsTestCase):
    """Tests para el template tag is_owner."""
    
    def test_is_owner_with_owner(self):
        """Test: Usuario es propietario."""
        template_string = """
        {% load permission_tags %}
        {% is_owner test_object 'agent' as is_property_owner %}
        {% if is_property_owner %}YES{% else %}NO{% endif %}
        """
        
        # Crear objeto mock
        test_object = Mock()
        test_object.agent = self.agent
        
        result = self.render_template(template_string, {
            'user': self.agent,
            'test_object': test_object
        })
        
        self.assertIn('YES', result.strip())
    
    def test_is_owner_with_non_owner(self):
        """Test: Usuario no es propietario."""
        template_string = """
        {% load permission_tags %}
        {% is_owner test_object 'agent' as is_property_owner %}
        {% if is_property_owner %}YES{% else %}NO{% endif %}
        """
        
        # Crear objeto mock con otro propietario
        test_object = Mock()
        test_object.agent = self.other_agent
        
        result = self.render_template(template_string, {
            'user': self.agent,
            'test_object': test_object
        })
        
        self.assertIn('NO', result.strip())
    
    def test_is_owner_with_invalid_field(self):
        """Test: Campo propietario inválido."""
        template_string = """
        {% load permission_tags %}
        {% is_owner test_object 'invalid_field' as is_property_owner %}
        {% if is_property_owner %}YES{% else %}NO{% endif %}
        """
        
        # Crear objeto mock sin el campo
        test_object = Mock()
        del test_object.invalid_field  # Asegurar que no existe
        
        result = self.render_template(template_string, {
            'user': self.agent,
            'test_object': test_object
        })
        
        self.assertIn('NO', result.strip())


class PermissionFiltersTest(TemplateTagsTestCase):
    """Tests para los filtros de permisos."""
    
    def test_has_perm_filter_with_permission(self):
        """Test: Filtro has_perm con permiso."""
        template_string = """
        {% load permission_tags %}
        {% if user|has_perm:'view_test' %}YES{% else %}NO{% endif %}
        """
        
        # Mock del servicio de permisos
        with patch.object(RolePermissionService, 'check_permission', return_value=True):
            result = self.render_template(template_string, {'user': self.agent})
        
        self.assertIn('YES', result.strip())
    
    def test_has_perm_filter_without_permission(self):
        """Test: Filtro has_perm sin permiso."""
        template_string = """
        {% load permission_tags %}
        {% if user|has_perm:'view_test' %}YES{% else %}NO{% endif %}
        """
        
        # Mock del servicio de permisos
        with patch.object(RolePermissionService, 'check_permission', return_value=False):
            result = self.render_template(template_string, {'user': self.agent})
        
        self.assertIn('NO', result.strip())
    
    def test_has_role_filter_with_role(self):
        """Test: Filtro has_role_filter con rol."""
        template_string = """
        {% load permission_tags %}
        {% if user|has_role_filter:'Administrador' %}YES{% else %}NO{% endif %}
        """
        
        # Mock del servicio de roles
        with patch.object(RolePermissionService, 'get_user_roles') as mock_get_roles:
            mock_get_roles.return_value = [self.admin_role]
            result = self.render_template(template_string, {'user': self.agent})
        
        self.assertIn('YES', result.strip())
    
    def test_has_role_filter_without_role(self):
        """Test: Filtro has_role_filter sin rol."""
        template_string = """
        {% load permission_tags %}
        {% if user|has_role_filter:'Administrador' %}YES{% else %}NO{% endif %}
        """
        
        # Mock del servicio de roles
        with patch.object(RolePermissionService, 'get_user_roles') as mock_get_roles:
            mock_get_roles.return_value = [self.basic_role]
            result = self.render_template(template_string, {'user': self.agent})
        
        self.assertIn('NO', result.strip())
    
    def test_is_admin_filter_with_admin(self):
        """Test: Filtro is_admin_filter con administrador."""
        template_string = """
        {% load permission_tags %}
        {% if user|is_admin_filter %}YES{% else %}NO{% endif %}
        """
        
        # Hacer al usuario superusuario
        self.agent.is_superuser = True
        self.agent.save()
        
        result = self.render_template(template_string, {'user': self.agent})
        self.assertIn('YES', result.strip())
    
    def test_is_admin_filter_with_regular_user(self):
        """Test: Filtro is_admin_filter con usuario regular."""
        template_string = """
        {% load permission_tags %}
        {% if user|is_admin_filter %}YES{% else %}NO{% endif %}
        """
        
        # Mock del servicio de roles
        with patch.object(RolePermissionService, 'get_user_roles') as mock_get_roles:
            mock_get_roles.return_value = [self.basic_role]
            result = self.render_template(template_string, {'user': self.agent})
        
        self.assertIn('NO', result.strip())


class TemplateTagsIntegrationTest(TemplateTagsTestCase):
    """Tests de integración para template tags."""
    
    def test_template_tags_with_non_agent_user(self):
        """Test: Template tags con usuario que no es Agent."""
        from django.contrib.auth.models import User
        
        # Crear usuario regular de Django
        regular_user = User.objects.create_user(
            username='regular_user',
            email='regular@example.com',
            password='testpass123'
        )
        
        template_string = """
        {% load permission_tags %}
        {% has_permission 'view_test' as can_view %}
        {% if can_view %}YES{% else %}NO{% endif %}
        """
        
        result = self.render_template(template_string, {'user': regular_user})
        self.assertIn('NO', result.strip())
    
    def test_template_tags_error_handling(self):
        """Test: Manejo de errores en template tags."""
        template_string = """
        {% load permission_tags %}
        {% has_permission 'view_test' as can_view %}
        {% if can_view %}YES{% else %}NO{% endif %}
        """
        
        # Mock del servicio para lanzar excepción
        with patch.object(RolePermissionService, 'check_permission', side_effect=Exception("Test error")):
            result = self.render_template(template_string, {'user': self.agent})
        
        # Debe devolver False por seguridad
        self.assertIn('NO', result.strip())
    
    def test_permission_debug_tag(self):
        """Test: Template tag de debug."""
        template_string = """
        {% load permission_tags %}
        {% permission_debug %}
        """
        
        # Mock de los servicios
        with patch.object(RolePermissionService, 'get_user_roles') as mock_get_roles, \
             patch.object(RolePermissionService, 'get_user_permissions') as mock_get_perms:
            
            mock_get_roles.return_value = [self.basic_role]
            mock_get_perms.return_value = [self.view_permission]
            
            result = self.render_template(template_string, {
                'user': self.agent,
                'debug': True  # Simular modo DEBUG
            })
        
        # El template de debug debe renderizarse
        self.assertIsInstance(result, str)
    
    def test_permission_check_js_tag(self):
        """Test: Template tag para JavaScript."""
        template_string = """
        {% load permission_tags %}
        {% permission_check_js 'view_test' %}
        """
        
        template = Template(template_string)
        context = Context({})
        result = template.render(context)
        
        # Debe generar código JavaScript
        self.assertIn('function hasPermission_view_test', result)
        self.assertIn('fetch', result)
        self.assertIn('view_test', result)