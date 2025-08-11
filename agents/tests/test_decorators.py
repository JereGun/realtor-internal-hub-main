"""
Tests para decoradores de permisos y roles.

Este módulo contiene tests unitarios para verificar el funcionamiento
correcto de los decoradores personalizados de permisos y roles.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase, RequestFactory
from django.contrib.auth.models import AnonymousUser
from django.contrib.messages import get_messages
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import redirect

from agents.models import Agent, Role, Permission, AgentRole
from agents.decorators import (
    permission_required,
    role_required,
    superuser_required,
    staff_required,
    admin_required,
    supervisor_or_admin_required
)
from agents.services.role_permission_service import RolePermissionService


class DecoratorTestCase(TestCase):
    """Clase base para tests de decoradores."""
    
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
        
        # Vista de prueba simple
        def test_view(request):
            return HttpResponse("Test view")
        
        self.test_view = test_view


class PermissionRequiredDecoratorTest(DecoratorTestCase):
    """Tests para el decorador permission_required."""
    
    def test_permission_required_with_authenticated_user_and_permission(self):
        """Test: Usuario autenticado con permiso puede acceder."""
        # Asignar permiso al rol y rol al usuario
        self.basic_role.permissions.add(self.view_permission)
        AgentRole.objects.create(agent=self.agent, role=self.basic_role, is_active=True)
        
        # Decorar vista
        decorated_view = permission_required('view_test')(self.test_view)
        
        # Crear request
        request = self.factory.get('/test/')
        request.user = self.agent
        
        # Mock del servicio de permisos
        with patch.object(RolePermissionService, 'check_permission', return_value=True):
            response = decorated_view(request)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), "Test view")
    
    def test_permission_required_with_authenticated_user_without_permission(self):
        """Test: Usuario autenticado sin permiso es redirigido."""
        # Crear request
        request = self.factory.get('/test/')
        request.user = self.agent
        request._messages = MagicMock()
        
        # Decorar vista
        decorated_view = permission_required('view_test')(self.test_view)
        
        # Mock del servicio de permisos
        with patch.object(RolePermissionService, 'check_permission', return_value=False):
            response = decorated_view(request)
        
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith('/dashboard/'))
    
    def test_permission_required_with_unauthenticated_user(self):
        """Test: Usuario no autenticado es redirigido al login."""
        # Crear request con usuario anónimo
        request = self.factory.get('/test/')
        request.user = AnonymousUser()
        
        # Decorar vista
        decorated_view = permission_required('view_test')(self.test_view)
        
        response = decorated_view(request)
        
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith('/agents/login/'))
    
    def test_permission_required_with_multiple_permissions(self):
        """Test: Verificación de múltiples permisos."""
        # Asignar permisos al rol y rol al usuario
        self.basic_role.permissions.add(self.view_permission, self.edit_permission)
        AgentRole.objects.create(agent=self.agent, role=self.basic_role, is_active=True)
        
        # Decorar vista con múltiples permisos
        decorated_view = permission_required(['view_test', 'edit_test'])(self.test_view)
        
        # Crear request
        request = self.factory.get('/test/')
        request.user = self.agent
        
        # Mock del servicio de permisos - ambos permisos
        with patch.object(RolePermissionService, 'check_permission', return_value=True):
            response = decorated_view(request)
        
        self.assertEqual(response.status_code, 200)
    
    def test_permission_required_with_raise_exception(self):
        """Test: Decorador con raise_exception=True lanza excepción."""
        # Decorar vista con raise_exception
        decorated_view = permission_required('view_test', raise_exception=True)(self.test_view)
        
        # Crear request
        request = self.factory.get('/test/')
        request.user = self.agent
        
        # Mock del servicio de permisos
        with patch.object(RolePermissionService, 'check_permission', return_value=False):
            with self.assertRaises(PermissionDenied):
                decorated_view(request)
    
    def test_permission_required_with_custom_redirect_url(self):
        """Test: Decorador con URL de redirección personalizada."""
        # Decorar vista con URL personalizada
        decorated_view = permission_required('view_test', redirect_url='/custom-redirect/')(self.test_view)
        
        # Crear request
        request = self.factory.get('/test/')
        request.user = self.agent
        request._messages = MagicMock()
        
        # Mock del servicio de permisos
        with patch.object(RolePermissionService, 'check_permission', return_value=False):
            response = decorated_view(request)
        
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/custom-redirect/')


class RoleRequiredDecoratorTest(DecoratorTestCase):
    """Tests para el decorador role_required."""
    
    def test_role_required_with_authenticated_user_and_role(self):
        """Test: Usuario autenticado con rol puede acceder."""
        # Asignar rol al usuario
        AgentRole.objects.create(agent=self.agent, role=self.basic_role, is_active=True)
        
        # Decorar vista
        decorated_view = role_required('Agente Básico')(self.test_view)
        
        # Crear request
        request = self.factory.get('/test/')
        request.user = self.agent
        
        # Mock del servicio de roles
        with patch.object(RolePermissionService, 'get_user_roles') as mock_get_roles:
            mock_get_roles.return_value = [self.basic_role]
            response = decorated_view(request)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), "Test view")
    
    def test_role_required_with_authenticated_user_without_role(self):
        """Test: Usuario autenticado sin rol es redirigido."""
        # Crear request
        request = self.factory.get('/test/')
        request.user = self.agent
        request._messages = MagicMock()
        
        # Decorar vista
        decorated_view = role_required('Administrador')(self.test_view)
        
        # Mock del servicio de roles - sin roles
        with patch.object(RolePermissionService, 'get_user_roles') as mock_get_roles:
            mock_get_roles.return_value = []
            response = decorated_view(request)
        
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith('/dashboard/'))
    
    def test_role_required_with_multiple_roles(self):
        """Test: Verificación de múltiples roles (OR lógico)."""
        # Asignar rol de supervisor al usuario
        AgentRole.objects.create(agent=self.agent, role=self.supervisor_role, is_active=True)
        
        # Decorar vista con múltiples roles
        decorated_view = role_required(['Supervisor', 'Administrador'])(self.test_view)
        
        # Crear request
        request = self.factory.get('/test/')
        request.user = self.agent
        
        # Mock del servicio de roles
        with patch.object(RolePermissionService, 'get_user_roles') as mock_get_roles:
            mock_get_roles.return_value = [self.supervisor_role]
            response = decorated_view(request)
        
        self.assertEqual(response.status_code, 200)
    
    def test_role_required_with_unauthenticated_user(self):
        """Test: Usuario no autenticado es redirigido al login."""
        # Crear request con usuario anónimo
        request = self.factory.get('/test/')
        request.user = AnonymousUser()
        
        # Decorar vista
        decorated_view = role_required('Administrador')(self.test_view)
        
        response = decorated_view(request)
        
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith('/agents/login/'))


class SuperuserRequiredDecoratorTest(DecoratorTestCase):
    """Tests para el decorador superuser_required."""
    
    def test_superuser_required_with_superuser(self):
        """Test: Superusuario puede acceder."""
        # Hacer al usuario superusuario
        self.agent.is_superuser = True
        self.agent.save()
        
        # Decorar vista
        decorated_view = superuser_required()(self.test_view)
        
        # Crear request
        request = self.factory.get('/test/')
        request.user = self.agent
        
        response = decorated_view(request)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), "Test view")
    
    def test_superuser_required_with_regular_user(self):
        """Test: Usuario regular es redirigido."""
        # Crear request
        request = self.factory.get('/test/')
        request.user = self.agent
        request._messages = MagicMock()
        
        # Decorar vista
        decorated_view = superuser_required()(self.test_view)
        
        response = decorated_view(request)
        
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith('/dashboard/'))
    
    def test_superuser_required_with_raise_exception(self):
        """Test: Decorador con raise_exception=True lanza excepción."""
        # Decorar vista con raise_exception
        decorated_view = superuser_required(raise_exception=True)(self.test_view)
        
        # Crear request
        request = self.factory.get('/test/')
        request.user = self.agent
        
        with self.assertRaises(PermissionDenied):
            decorated_view(request)


class StaffRequiredDecoratorTest(DecoratorTestCase):
    """Tests para el decorador staff_required."""
    
    def test_staff_required_with_staff_user(self):
        """Test: Usuario staff puede acceder."""
        # Hacer al usuario staff
        self.agent.is_staff = True
        self.agent.save()
        
        # Decorar vista
        decorated_view = staff_required()(self.test_view)
        
        # Crear request
        request = self.factory.get('/test/')
        request.user = self.agent
        
        response = decorated_view(request)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), "Test view")
    
    def test_staff_required_with_regular_user(self):
        """Test: Usuario regular es redirigido."""
        # Crear request
        request = self.factory.get('/test/')
        request.user = self.agent
        request._messages = MagicMock()
        
        # Decorar vista
        decorated_view = staff_required()(self.test_view)
        
        response = decorated_view(request)
        
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith('/dashboard/'))


class AdminRequiredDecoratorTest(DecoratorTestCase):
    """Tests para el decorador admin_required."""
    
    def test_admin_required_with_superuser(self):
        """Test: Superusuario puede acceder."""
        # Hacer al usuario superusuario
        self.agent.is_superuser = True
        self.agent.save()
        
        # Decorar vista
        decorated_view = admin_required()(self.test_view)
        
        # Crear request
        request = self.factory.get('/test/')
        request.user = self.agent
        
        response = decorated_view(request)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), "Test view")
    
    def test_admin_required_with_admin_role(self):
        """Test: Usuario con rol de Administrador puede acceder."""
        # Asignar rol de administrador al usuario
        AgentRole.objects.create(agent=self.agent, role=self.admin_role, is_active=True)
        
        # Decorar vista
        decorated_view = admin_required()(self.test_view)
        
        # Crear request
        request = self.factory.get('/test/')
        request.user = self.agent
        
        # Mock del servicio de roles
        with patch.object(RolePermissionService, 'get_user_roles') as mock_get_roles:
            mock_get_roles.return_value = [self.admin_role]
            response = decorated_view(request)
        
        self.assertEqual(response.status_code, 200)
    
    def test_admin_required_with_regular_user(self):
        """Test: Usuario regular es redirigido."""
        # Crear request
        request = self.factory.get('/test/')
        request.user = self.agent
        request._messages = MagicMock()
        
        # Decorar vista
        decorated_view = admin_required()(self.test_view)
        
        # Mock del servicio de roles - sin roles de admin
        with patch.object(RolePermissionService, 'get_user_roles') as mock_get_roles:
            mock_get_roles.return_value = [self.basic_role]
            response = decorated_view(request)
        
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith('/dashboard/'))


class SupervisorOrAdminRequiredDecoratorTest(DecoratorTestCase):
    """Tests para el decorador supervisor_or_admin_required."""
    
    def test_supervisor_or_admin_required_with_supervisor(self):
        """Test: Usuario con rol de Supervisor puede acceder."""
        # Asignar rol de supervisor al usuario
        AgentRole.objects.create(agent=self.agent, role=self.supervisor_role, is_active=True)
        
        # Decorar vista
        decorated_view = supervisor_or_admin_required()(self.test_view)
        
        # Crear request
        request = self.factory.get('/test/')
        request.user = self.agent
        
        # Mock del servicio de roles
        with patch.object(RolePermissionService, 'get_user_roles') as mock_get_roles:
            mock_get_roles.return_value = [self.supervisor_role]
            response = decorated_view(request)
        
        self.assertEqual(response.status_code, 200)
    
    def test_supervisor_or_admin_required_with_admin(self):
        """Test: Usuario con rol de Administrador puede acceder."""
        # Asignar rol de administrador al usuario
        AgentRole.objects.create(agent=self.agent, role=self.admin_role, is_active=True)
        
        # Decorar vista
        decorated_view = supervisor_or_admin_required()(self.test_view)
        
        # Crear request
        request = self.factory.get('/test/')
        request.user = self.agent
        
        # Mock del servicio de roles
        with patch.object(RolePermissionService, 'get_user_roles') as mock_get_roles:
            mock_get_roles.return_value = [self.admin_role]
            response = decorated_view(request)
        
        self.assertEqual(response.status_code, 200)
    
    def test_supervisor_or_admin_required_with_superuser(self):
        """Test: Superusuario puede acceder."""
        # Hacer al usuario superusuario
        self.agent.is_superuser = True
        self.agent.save()
        
        # Decorar vista
        decorated_view = supervisor_or_admin_required()(self.test_view)
        
        # Crear request
        request = self.factory.get('/test/')
        request.user = self.agent
        
        response = decorated_view(request)
        
        self.assertEqual(response.status_code, 200)
    
    def test_supervisor_or_admin_required_with_basic_user(self):
        """Test: Usuario básico es redirigido."""
        # Asignar rol básico al usuario
        AgentRole.objects.create(agent=self.agent, role=self.basic_role, is_active=True)
        
        # Crear request
        request = self.factory.get('/test/')
        request.user = self.agent
        request._messages = MagicMock()
        
        # Decorar vista
        decorated_view = supervisor_or_admin_required()(self.test_view)
        
        # Mock del servicio de roles
        with patch.object(RolePermissionService, 'get_user_roles') as mock_get_roles:
            mock_get_roles.return_value = [self.basic_role]
            response = decorated_view(request)
        
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith('/dashboard/'))


class DecoratorIntegrationTest(DecoratorTestCase):
    """Tests de integración para decoradores."""
    
    def test_decorator_with_non_agent_user(self):
        """Test: Decorador con usuario que no es Agent."""
        from django.contrib.auth.models import User
        
        # Crear usuario regular de Django
        regular_user = User.objects.create_user(
            username='regular_user',
            email='regular@example.com',
            password='testpass123'
        )
        
        # Decorar vista
        decorated_view = permission_required('view_test')(self.test_view)
        
        # Crear request
        request = self.factory.get('/test/')
        request.user = regular_user
        request._messages = MagicMock()
        
        response = decorated_view(request)
        
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith('/agents/login/'))
    
    def test_decorator_error_handling(self):
        """Test: Manejo de errores en decoradores."""
        # Decorar vista
        decorated_view = permission_required('view_test')(self.test_view)
        
        # Crear request
        request = self.factory.get('/test/')
        request.user = self.agent
        request._messages = MagicMock()
        
        # Mock del servicio de permisos para lanzar excepción
        with patch.object(RolePermissionService, 'check_permission', side_effect=Exception("Test error")):
            response = decorated_view(request)
        
        # Debe redirigir por seguridad
        self.assertEqual(response.status_code, 302)
    
    def test_decorator_with_custom_login_url(self):
        """Test: Decorador con URL de login personalizada."""
        # Decorar vista con login URL personalizada
        decorated_view = permission_required('view_test', login_url='/custom-login/')(self.test_view)
        
        # Crear request con usuario anónimo
        request = self.factory.get('/test/')
        request.user = AnonymousUser()
        
        response = decorated_view(request)
        
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/custom-login/')