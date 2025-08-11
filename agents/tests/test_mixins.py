"""
Tests para mixins de permisos y roles.

Este módulo contiene tests unitarios para verificar el funcionamiento
correcto de los mixins personalizados de permisos y roles.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase, RequestFactory
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.views.generic import TemplateView, DetailView
from django.template.response import TemplateResponse

from agents.models import Agent, Role, Permission, AgentRole
from agents.mixins import (
    PermissionRequiredMixin,
    RoleRequiredMixin,
    SuperuserRequiredMixin,
    StaffRequiredMixin,
    AdminRequiredMixin,
    SupervisorOrAdminRequiredMixin,
    OwnerRequiredMixin
)
from agents.services.role_permission_service import RolePermissionService


class MixinTestCase(TestCase):
    """Clase base para tests de mixins."""
    
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
        
        # Crear segundo usuario para tests de propiedad
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


class PermissionRequiredMixinTest(MixinTestCase):
    """Tests para PermissionRequiredMixin."""
    
    def test_permission_required_mixin_with_permission(self):
        """Test: Usuario con permiso puede acceder."""
        # Crear vista de prueba
        class TestView(PermissionRequiredMixin, TemplateView):
            permission_required = 'view_test'
            template_name = 'test.html'
            
            def get(self, request, *args, **kwargs):
                return HttpResponse("Test view")
        
        # Asignar permiso al rol y rol al usuario
        self.basic_role.permissions.add(self.view_permission)
        AgentRole.objects.create(agent=self.agent, role=self.basic_role, is_active=True)
        
        # Crear request
        request = self.factory.get('/test/')
        request.user = self.agent
        
        # Mock del servicio de permisos
        with patch.object(RolePermissionService, 'check_permission', return_value=True):
            view = TestView.as_view()
            response = view(request)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), "Test view")
    
    def test_permission_required_mixin_without_permission(self):
        """Test: Usuario sin permiso es redirigido."""
        # Crear vista de prueba
        class TestView(PermissionRequiredMixin, TemplateView):
            permission_required = 'view_test'
            template_name = 'test.html'
        
        # Crear request
        request = self.factory.get('/test/')
        request.user = self.agent
        request._messages = MagicMock()
        
        # Mock del servicio de permisos
        with patch.object(RolePermissionService, 'check_permission', return_value=False):
            view = TestView.as_view()
            response = view(request)
        
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith('/dashboard/'))
    
    def test_permission_required_mixin_with_multiple_permissions(self):
        """Test: Verificación de múltiples permisos."""
        # Crear vista de prueba
        class TestView(PermissionRequiredMixin, TemplateView):
            permission_required = ['view_test', 'edit_test']
            template_name = 'test.html'
            
            def get(self, request, *args, **kwargs):
                return HttpResponse("Test view")
        
        # Crear request
        request = self.factory.get('/test/')
        request.user = self.agent
        
        # Mock del servicio de permisos - ambos permisos
        with patch.object(RolePermissionService, 'check_permission', return_value=True):
            view = TestView.as_view()
            response = view(request)
        
        self.assertEqual(response.status_code, 200)
    
    def test_permission_required_mixin_with_raise_exception(self):
        """Test: Mixin con raise_exception=True lanza excepción."""
        # Crear vista de prueba
        class TestView(PermissionRequiredMixin, TemplateView):
            permission_required = 'view_test'
            raise_exception = True
            template_name = 'test.html'
        
        # Crear request
        request = self.factory.get('/test/')
        request.user = self.agent
        
        # Mock del servicio de permisos
        with patch.object(RolePermissionService, 'check_permission', return_value=False):
            view = TestView.as_view()
            with self.assertRaises(PermissionDenied):
                view(request)
    
    def test_permission_required_mixin_without_permission_defined(self):
        """Test: Mixin sin permission_required definido lanza error."""
        # Crear vista de prueba sin permission_required
        class TestView(PermissionRequiredMixin, TemplateView):
            template_name = 'test.html'
        
        # Crear request
        request = self.factory.get('/test/')
        request.user = self.agent
        
        view = TestView.as_view()
        with self.assertRaises(ValueError):
            view(request)
    
    def test_permission_required_mixin_with_unauthenticated_user(self):
        """Test: Usuario no autenticado es redirigido al login."""
        # Crear vista de prueba
        class TestView(PermissionRequiredMixin, TemplateView):
            permission_required = 'view_test'
            template_name = 'test.html'
        
        # Crear request con usuario anónimo
        request = self.factory.get('/test/')
        request.user = AnonymousUser()
        
        view = TestView.as_view()
        response = view(request)
        
        self.assertEqual(response.status_code, 302)


class RoleRequiredMixinTest(MixinTestCase):
    """Tests para RoleRequiredMixin."""
    
    def test_role_required_mixin_with_role(self):
        """Test: Usuario con rol puede acceder."""
        # Crear vista de prueba
        class TestView(RoleRequiredMixin, TemplateView):
            role_required = 'Agente Básico'
            template_name = 'test.html'
            
            def get(self, request, *args, **kwargs):
                return HttpResponse("Test view")
        
        # Asignar rol al usuario
        AgentRole.objects.create(agent=self.agent, role=self.basic_role, is_active=True)
        
        # Crear request
        request = self.factory.get('/test/')
        request.user = self.agent
        
        # Mock del servicio de roles
        with patch.object(RolePermissionService, 'get_user_roles') as mock_get_roles:
            mock_get_roles.return_value = [self.basic_role]
            view = TestView.as_view()
            response = view(request)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), "Test view")
    
    def test_role_required_mixin_without_role(self):
        """Test: Usuario sin rol es redirigido."""
        # Crear vista de prueba
        class TestView(RoleRequiredMixin, TemplateView):
            role_required = 'Administrador'
            template_name = 'test.html'
        
        # Crear request
        request = self.factory.get('/test/')
        request.user = self.agent
        request._messages = MagicMock()
        
        # Mock del servicio de roles - sin roles
        with patch.object(RolePermissionService, 'get_user_roles') as mock_get_roles:
            mock_get_roles.return_value = []
            view = TestView.as_view()
            response = view(request)
        
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith('/dashboard/'))
    
    def test_role_required_mixin_with_multiple_roles(self):
        """Test: Verificación de múltiples roles (OR lógico)."""
        # Crear vista de prueba
        class TestView(RoleRequiredMixin, TemplateView):
            role_required = ['Supervisor', 'Administrador']
            template_name = 'test.html'
            
            def get(self, request, *args, **kwargs):
                return HttpResponse("Test view")
        
        # Asignar rol de supervisor al usuario
        AgentRole.objects.create(agent=self.agent, role=self.supervisor_role, is_active=True)
        
        # Crear request
        request = self.factory.get('/test/')
        request.user = self.agent
        
        # Mock del servicio de roles
        with patch.object(RolePermissionService, 'get_user_roles') as mock_get_roles:
            mock_get_roles.return_value = [self.supervisor_role]
            view = TestView.as_view()
            response = view(request)
        
        self.assertEqual(response.status_code, 200)


class SuperuserRequiredMixinTest(MixinTestCase):
    """Tests para SuperuserRequiredMixin."""
    
    def test_superuser_required_mixin_with_superuser(self):
        """Test: Superusuario puede acceder."""
        # Crear vista de prueba
        class TestView(SuperuserRequiredMixin, TemplateView):
            template_name = 'test.html'
            
            def get(self, request, *args, **kwargs):
                return HttpResponse("Test view")
        
        # Hacer al usuario superusuario
        self.agent.is_superuser = True
        self.agent.save()
        
        # Crear request
        request = self.factory.get('/test/')
        request.user = self.agent
        
        view = TestView.as_view()
        response = view(request)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), "Test view")
    
    def test_superuser_required_mixin_with_regular_user(self):
        """Test: Usuario regular es redirigido."""
        # Crear vista de prueba
        class TestView(SuperuserRequiredMixin, TemplateView):
            template_name = 'test.html'
        
        # Crear request
        request = self.factory.get('/test/')
        request.user = self.agent
        request._messages = MagicMock()
        
        view = TestView.as_view()
        response = view(request)
        
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith('/dashboard/'))


class StaffRequiredMixinTest(MixinTestCase):
    """Tests para StaffRequiredMixin."""
    
    def test_staff_required_mixin_with_staff_user(self):
        """Test: Usuario staff puede acceder."""
        # Crear vista de prueba
        class TestView(StaffRequiredMixin, TemplateView):
            template_name = 'test.html'
            
            def get(self, request, *args, **kwargs):
                return HttpResponse("Test view")
        
        # Hacer al usuario staff
        self.agent.is_staff = True
        self.agent.save()
        
        # Crear request
        request = self.factory.get('/test/')
        request.user = self.agent
        
        view = TestView.as_view()
        response = view(request)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), "Test view")
    
    def test_staff_required_mixin_with_regular_user(self):
        """Test: Usuario regular es redirigido."""
        # Crear vista de prueba
        class TestView(StaffRequiredMixin, TemplateView):
            template_name = 'test.html'
        
        # Crear request
        request = self.factory.get('/test/')
        request.user = self.agent
        request._messages = MagicMock()
        
        view = TestView.as_view()
        response = view(request)
        
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith('/dashboard/'))


class AdminRequiredMixinTest(MixinTestCase):
    """Tests para AdminRequiredMixin."""
    
    def test_admin_required_mixin_with_superuser(self):
        """Test: Superusuario puede acceder."""
        # Crear vista de prueba
        class TestView(AdminRequiredMixin, TemplateView):
            template_name = 'test.html'
            
            def get(self, request, *args, **kwargs):
                return HttpResponse("Test view")
        
        # Hacer al usuario superusuario
        self.agent.is_superuser = True
        self.agent.save()
        
        # Crear request
        request = self.factory.get('/test/')
        request.user = self.agent
        
        view = TestView.as_view()
        response = view(request)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), "Test view")
    
    def test_admin_required_mixin_with_admin_role(self):
        """Test: Usuario con rol de Administrador puede acceder."""
        # Crear vista de prueba
        class TestView(AdminRequiredMixin, TemplateView):
            template_name = 'test.html'
            
            def get(self, request, *args, **kwargs):
                return HttpResponse("Test view")
        
        # Asignar rol de administrador al usuario
        AgentRole.objects.create(agent=self.agent, role=self.admin_role, is_active=True)
        
        # Crear request
        request = self.factory.get('/test/')
        request.user = self.agent
        
        # Mock del servicio de roles
        with patch.object(RolePermissionService, 'get_user_roles') as mock_get_roles:
            mock_get_roles.return_value = [self.admin_role]
            view = TestView.as_view()
            response = view(request)
        
        self.assertEqual(response.status_code, 200)
    
    def test_admin_required_mixin_with_regular_user(self):
        """Test: Usuario regular es redirigido."""
        # Crear vista de prueba
        class TestView(AdminRequiredMixin, TemplateView):
            template_name = 'test.html'
        
        # Crear request
        request = self.factory.get('/test/')
        request.user = self.agent
        request._messages = MagicMock()
        
        # Mock del servicio de roles - sin roles de admin
        with patch.object(RolePermissionService, 'get_user_roles') as mock_get_roles:
            mock_get_roles.return_value = [self.basic_role]
            view = TestView.as_view()
            response = view(request)
        
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith('/dashboard/'))


class SupervisorOrAdminRequiredMixinTest(MixinTestCase):
    """Tests para SupervisorOrAdminRequiredMixin."""
    
    def test_supervisor_or_admin_required_mixin_with_supervisor(self):
        """Test: Usuario con rol de Supervisor puede acceder."""
        # Crear vista de prueba
        class TestView(SupervisorOrAdminRequiredMixin, TemplateView):
            template_name = 'test.html'
            
            def get(self, request, *args, **kwargs):
                return HttpResponse("Test view")
        
        # Asignar rol de supervisor al usuario
        AgentRole.objects.create(agent=self.agent, role=self.supervisor_role, is_active=True)
        
        # Crear request
        request = self.factory.get('/test/')
        request.user = self.agent
        
        # Mock del servicio de roles
        with patch.object(RolePermissionService, 'get_user_roles') as mock_get_roles:
            mock_get_roles.return_value = [self.supervisor_role]
            view = TestView.as_view()
            response = view(request)
        
        self.assertEqual(response.status_code, 200)
    
    def test_supervisor_or_admin_required_mixin_with_admin(self):
        """Test: Usuario con rol de Administrador puede acceder."""
        # Crear vista de prueba
        class TestView(SupervisorOrAdminRequiredMixin, TemplateView):
            template_name = 'test.html'
            
            def get(self, request, *args, **kwargs):
                return HttpResponse("Test view")
        
        # Asignar rol de administrador al usuario
        AgentRole.objects.create(agent=self.agent, role=self.admin_role, is_active=True)
        
        # Crear request
        request = self.factory.get('/test/')
        request.user = self.agent
        
        # Mock del servicio de roles
        with patch.object(RolePermissionService, 'get_user_roles') as mock_get_roles:
            mock_get_roles.return_value = [self.admin_role]
            view = TestView.as_view()
            response = view(request)
        
        self.assertEqual(response.status_code, 200)
    
    def test_supervisor_or_admin_required_mixin_with_basic_user(self):
        """Test: Usuario básico es redirigido."""
        # Crear vista de prueba
        class TestView(SupervisorOrAdminRequiredMixin, TemplateView):
            template_name = 'test.html'
        
        # Asignar rol básico al usuario
        AgentRole.objects.create(agent=self.agent, role=self.basic_role, is_active=True)
        
        # Crear request
        request = self.factory.get('/test/')
        request.user = self.agent
        request._messages = MagicMock()
        
        # Mock del servicio de roles
        with patch.object(RolePermissionService, 'get_user_roles') as mock_get_roles:
            mock_get_roles.return_value = [self.basic_role]
            view = TestView.as_view()
            response = view(request)
        
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith('/dashboard/'))


class OwnerRequiredMixinTest(MixinTestCase):
    """Tests para OwnerRequiredMixin."""
    
    def setUp(self):
        """Configuración adicional para tests de propiedad."""
        super().setUp()
        
        # Crear modelo de prueba simulado
        class TestModel:
            def __init__(self, agent, pk=1):
                self.agent = agent
                self.pk = pk
        
        self.test_object = TestModel(self.agent)
        self.other_test_object = TestModel(self.other_agent)
    
    def test_owner_required_mixin_with_owner(self):
        """Test: Propietario puede acceder."""
        # Crear vista de prueba
        class TestView(OwnerRequiredMixin, DetailView):
            owner_field = 'agent'
            
            def get_object(self):
                return self.test_object
            
            def get(self, request, *args, **kwargs):
                return HttpResponse("Test view")
        
        # Crear request
        request = self.factory.get('/test/')
        request.user = self.agent
        
        view = TestView.as_view()
        response = view(request)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), "Test view")
    
    def test_owner_required_mixin_with_non_owner(self):
        """Test: No propietario es redirigido."""
        # Crear vista de prueba
        class TestView(OwnerRequiredMixin, DetailView):
            owner_field = 'agent'
            
            def get_object(self):
                return self.other_test_object
        
        # Crear request
        request = self.factory.get('/test/')
        request.user = self.agent
        request._messages = MagicMock()
        
        view = TestView.as_view()
        response = view(request)
        
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith('/dashboard/'))
    
    def test_owner_required_mixin_with_admin_access(self):
        """Test: Administrador puede acceder aunque no sea propietario."""
        # Crear vista de prueba
        class TestView(OwnerRequiredMixin, DetailView):
            owner_field = 'agent'
            allow_admin_access = True
            
            def get_object(self):
                return self.other_test_object
            
            def get(self, request, *args, **kwargs):
                return HttpResponse("Test view")
        
        # Asignar rol de administrador al usuario
        AgentRole.objects.create(agent=self.agent, role=self.admin_role, is_active=True)
        
        # Crear request
        request = self.factory.get('/test/')
        request.user = self.agent
        
        # Mock del servicio de roles
        with patch.object(RolePermissionService, 'get_user_roles') as mock_get_roles:
            mock_get_roles.return_value = [self.admin_role]
            view = TestView.as_view()
            response = view(request)
        
        self.assertEqual(response.status_code, 200)
    
    def test_owner_required_mixin_with_superuser_access(self):
        """Test: Superusuario puede acceder aunque no sea propietario."""
        # Crear vista de prueba
        class TestView(OwnerRequiredMixin, DetailView):
            owner_field = 'agent'
            allow_admin_access = True
            
            def get_object(self):
                return self.other_test_object
            
            def get(self, request, *args, **kwargs):
                return HttpResponse("Test view")
        
        # Hacer al usuario superusuario
        self.agent.is_superuser = True
        self.agent.save()
        
        # Crear request
        request = self.factory.get('/test/')
        request.user = self.agent
        
        view = TestView.as_view()
        response = view(request)
        
        self.assertEqual(response.status_code, 200)
    
    def test_owner_required_mixin_with_invalid_owner_field(self):
        """Test: Campo propietario inválido."""
        # Crear vista de prueba
        class TestView(OwnerRequiredMixin, DetailView):
            owner_field = 'invalid_field'
            
            def get_object(self):
                return self.test_object
        
        # Crear request
        request = self.factory.get('/test/')
        request.user = self.agent
        request._messages = MagicMock()
        
        view = TestView.as_view()
        response = view(request)
        
        # Debe redirigir por seguridad cuando el campo no existe
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith('/dashboard/'))


class MixinIntegrationTest(MixinTestCase):
    """Tests de integración para mixins."""
    
    def test_mixin_with_non_agent_user(self):
        """Test: Mixin con usuario que no es Agent."""
        from django.contrib.auth.models import User
        
        # Crear usuario regular de Django
        regular_user = User.objects.create_user(
            username='regular_user',
            email='regular@example.com',
            password='testpass123'
        )
        
        # Crear vista de prueba
        class TestView(PermissionRequiredMixin, TemplateView):
            permission_required = 'view_test'
            template_name = 'test.html'
        
        # Crear request
        request = self.factory.get('/test/')
        request.user = regular_user
        request._messages = MagicMock()
        
        view = TestView.as_view()
        response = view(request)
        
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith('/agents/login/'))
    
    def test_mixin_with_custom_redirect_url(self):
        """Test: Mixin con URL de redirección personalizada."""
        # Crear vista de prueba
        class TestView(PermissionRequiredMixin, TemplateView):
            permission_required = 'view_test'
            redirect_url = '/custom-redirect/'
            template_name = 'test.html'
        
        # Crear request
        request = self.factory.get('/test/')
        request.user = self.agent
        request._messages = MagicMock()
        
        # Mock del servicio de permisos
        with patch.object(RolePermissionService, 'check_permission', return_value=False):
            view = TestView.as_view()
            response = view(request)
        
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/custom-redirect/')
    
    def test_mixin_with_custom_messages(self):
        """Test: Mixin con mensajes personalizados."""
        # Crear vista de prueba
        class TestView(PermissionRequiredMixin, TemplateView):
            permission_required = 'view_test'
            permission_denied_message = 'Mensaje personalizado de error'
            template_name = 'test.html'
        
        # Crear request
        request = self.factory.get('/test/')
        request.user = self.agent
        request._messages = MagicMock()
        
        # Mock del servicio de permisos
        with patch.object(RolePermissionService, 'check_permission', return_value=False):
            view = TestView.as_view()
            response = view(request)
        
        self.assertEqual(response.status_code, 302)
    
    def test_multiple_mixins_combination(self):
        """Test: Combinación de múltiples mixins."""
        # Crear vista de prueba que combina múltiples mixins
        class TestView(PermissionRequiredMixin, RoleRequiredMixin, TemplateView):
            permission_required = 'view_test'
            role_required = 'Agente Básico'
            template_name = 'test.html'
            
            def get(self, request, *args, **kwargs):
                return HttpResponse("Test view")
        
        # Asignar permiso y rol al usuario
        self.basic_role.permissions.add(self.view_permission)
        AgentRole.objects.create(agent=self.agent, role=self.basic_role, is_active=True)
        
        # Crear request
        request = self.factory.get('/test/')
        request.user = self.agent
        
        # Mock de ambos servicios
        with patch.object(RolePermissionService, 'check_permission', return_value=True), \
             patch.object(RolePermissionService, 'get_user_roles') as mock_get_roles:
            mock_get_roles.return_value = [self.basic_role]
            view = TestView.as_view()
            response = view(request)
        
        self.assertEqual(response.status_code, 200)