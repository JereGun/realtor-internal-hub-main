"""
Tests para las vistas de administración de usuarios.

Este módulo contiene tests de integración para todas las vistas
de administración, incluyendo gestión de usuarios, roles y auditoría.
"""

import json
from datetime import timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.http import HttpResponse

from agents.models import (
    Agent, UserProfile, SecuritySettings, AuditLog, Role, 
    Permission, AgentRole, UserSession
)
from agents.services.user_management_service import UserManagementService
from agents.services.audit_service import AuditService


class AdminViewsTestCase(TestCase):
    """Clase base para tests de vistas de administración."""
    
    def setUp(self):
        """Configuración inicial para los tests."""
        self.client = Client()
        
        # Crear usuario administrador
        self.admin_user = Agent.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            first_name='Admin',
            last_name='User',
            license_number='ADMIN001',
            is_staff=True,
            is_superuser=True
        )
        
        # Crear usuario normal
        self.normal_user = Agent.objects.create_user(
            username='user',
            email='user@test.com',
            password='testpass123',
            first_name='Normal',
            last_name='User',
            license_number='USER001'
        )
        
        # Crear perfil para usuario normal
        UserProfile.objects.create(
            agent=self.normal_user,
            profile_completion=75
        )
        
        # Crear configuraciones de seguridad
        SecuritySettings.objects.create(agent=self.normal_user)
        
        # Crear roles de prueba
        self.admin_role = Role.objects.create(
            name='Administrador',
            description='Rol de administrador del sistema',
            is_system_role=True
        )
        
        self.agent_role = Role.objects.create(
            name='Agente Básico',
            description='Rol básico para agentes',
            is_system_role=True
        )
        
        # Asignar rol de administrador
        AgentRole.objects.create(
            agent=self.admin_user,
            role=self.admin_role,
            assigned_by=self.admin_user
        )
        
        # Crear algunos logs de auditoría
        AuditLog.objects.create(
            agent=self.normal_user,
            action='login',
            resource_type='agent',
            ip_address='192.168.1.1',
            user_agent='Test Browser',
            success=True
        )
        
        AuditLog.objects.create(
            agent=self.normal_user,
            action='profile_update',
            resource_type='user_profile',
            ip_address='192.168.1.1',
            user_agent='Test Browser',
            success=False
        )
    
    def login_as_admin(self):
        """Helper para hacer login como administrador."""
        self.client.login(email='admin@test.com', password='testpass123')
    
    def login_as_user(self):
        """Helper para hacer login como usuario normal."""
        self.client.login(email='user@test.com', password='testpass123')


class AdminDashboardViewTest(AdminViewsTestCase):
    """Tests para la vista del dashboard de administración."""
    
    def test_admin_dashboard_access_as_admin(self):
        """Test que el administrador puede acceder al dashboard."""
        self.login_as_admin()
        response = self.client.get(reverse('agents:admin_dashboard'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Panel de Administración')
        self.assertContains(response, 'Total Usuarios')
        self.assertContains(response, 'Usuarios Activos')
    
    def test_admin_dashboard_access_as_normal_user(self):
        """Test que un usuario normal no puede acceder al dashboard."""
        self.login_as_user()
        response = self.client.get(reverse('agents:admin_dashboard'))
        
        # Debería redirigir o devolver 403
        self.assertIn(response.status_code, [302, 403])
    
    def test_admin_dashboard_context_data(self):
        """Test que el dashboard contiene los datos correctos."""
        self.login_as_admin()
        response = self.client.get(reverse('agents:admin_dashboard'))
        
        self.assertEqual(response.context['total_users'], 2)
        self.assertEqual(response.context['active_users'], 2)
        self.assertEqual(response.context['inactive_users'], 0)
        self.assertIsNotNone(response.context['recent_activity'])


class AdminUserListViewTest(AdminViewsTestCase):
    """Tests para la vista de lista de usuarios."""
    
    def test_user_list_access_as_admin(self):
        """Test que el administrador puede ver la lista de usuarios."""
        self.login_as_admin()
        response = self.client.get(reverse('agents:admin_user_list'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Gestión de Usuarios')
        self.assertContains(response, self.normal_user.email)
        self.assertContains(response, self.admin_user.email)
    
    def test_user_list_search_filter(self):
        """Test que los filtros de búsqueda funcionan correctamente."""
        self.login_as_admin()
        
        # Buscar por email
        response = self.client.get(reverse('agents:admin_user_list'), {
            'search': 'user@test.com'
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.normal_user.email)
        self.assertNotContains(response, self.admin_user.email)
    
    def test_user_list_status_filter(self):
        """Test que el filtro de estado funciona."""
        # Desactivar usuario normal
        self.normal_user.is_active = False
        self.normal_user.save()
        
        self.login_as_admin()
        
        # Filtrar solo activos
        response = self.client.get(reverse('agents:admin_user_list'), {
            'status': 'active'
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.admin_user.email)
        self.assertNotContains(response, self.normal_user.email)
    
    def test_user_list_pagination(self):
        """Test que la paginación funciona correctamente."""
        # Crear más usuarios para probar paginación
        for i in range(30):
            Agent.objects.create_user(
                username=f'user{i}',
                email=f'user{i}@test.com',
                password='testpass123',
                first_name=f'User{i}',
                last_name='Test',
                license_number=f'LIC{i:03d}'
            )
        
        self.login_as_admin()
        response = self.client.get(reverse('agents:admin_user_list'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['is_paginated'])
        self.assertEqual(len(response.context['users']), 25)  # paginate_by = 25


class AdminUserDetailViewTest(AdminViewsTestCase):
    """Tests para la vista de detalle de usuario."""
    
    def test_user_detail_access_as_admin(self):
        """Test que el administrador puede ver detalles de usuario."""
        self.login_as_admin()
        response = self.client.get(
            reverse('agents:admin_user_detail', kwargs={'pk': self.normal_user.pk})
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.normal_user.get_full_name())
        self.assertContains(response, self.normal_user.email)
        self.assertContains(response, 'Estadísticas del Usuario')
    
    def test_user_detail_context_data(self):
        """Test que la vista de detalle contiene todos los datos necesarios."""
        self.login_as_admin()
        response = self.client.get(
            reverse('agents:admin_user_detail', kwargs={'pk': self.normal_user.pk})
        )
        
        self.assertIn('user_stats', response.context)
        self.assertIn('recent_activity', response.context)
        self.assertIn('security_settings', response.context)
        self.assertIn('profile_completion', response.context)
    
    def test_user_detail_nonexistent_user(self):
        """Test que se maneja correctamente un usuario inexistente."""
        self.login_as_admin()
        response = self.client.get(
            reverse('agents:admin_user_detail', kwargs={'pk': 99999})
        )
        
        self.assertEqual(response.status_code, 404)


class AdminUserToggleStatusTest(AdminViewsTestCase):
    """Tests para la funcionalidad de activar/desactivar usuarios."""
    
    def test_toggle_user_status_success(self):
        """Test que se puede cambiar el estado de un usuario."""
        self.login_as_admin()
        
        # Usuario inicialmente activo
        self.assertTrue(self.normal_user.is_active)
        
        response = self.client.post(
            reverse('agents:admin_user_toggle_status', kwargs={'user_id': self.normal_user.pk})
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(data['new_status'], 'inactive')
        
        # Verificar que el usuario fue desactivado
        self.normal_user.refresh_from_db()
        self.assertFalse(self.normal_user.is_active)
    
    def test_toggle_own_status_forbidden(self):
        """Test que un admin no puede desactivar su propia cuenta."""
        self.login_as_admin()
        
        response = self.client.post(
            reverse('agents:admin_user_toggle_status', kwargs={'user_id': self.admin_user.pk})
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertFalse(data.get('success', True))
        self.assertIn('error', data)
    
    def test_toggle_status_creates_audit_log(self):
        """Test que se crea un log de auditoría al cambiar estado."""
        self.login_as_admin()
        
        initial_logs = AuditLog.objects.count()
        
        self.client.post(
            reverse('agents:admin_user_toggle_status', kwargs={'user_id': self.normal_user.pk})
        )
        
        # Verificar que se creó un nuevo log
        self.assertEqual(AuditLog.objects.count(), initial_logs + 1)
        
        # Verificar el contenido del log
        log = AuditLog.objects.latest('created_at')
        self.assertEqual(log.action, 'user_status_changed')
        self.assertEqual(log.agent, self.admin_user)


class AdminRoleManagementTest(AdminViewsTestCase):
    """Tests para la gestión de roles."""
    
    def test_assign_role_success(self):
        """Test que se puede asignar un rol a un usuario."""
        self.login_as_admin()
        
        response = self.client.post(
            reverse('agents:admin_assign_role', kwargs={'user_id': self.normal_user.pk}),
            {'role_id': self.agent_role.pk}
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        
        # Verificar que el rol fue asignado
        self.assertTrue(
            AgentRole.objects.filter(
                agent=self.normal_user,
                role=self.agent_role,
                is_active=True
            ).exists()
        )
    
    def test_assign_duplicate_role(self):
        """Test que no se puede asignar un rol duplicado."""
        # Asignar rol primero
        AgentRole.objects.create(
            agent=self.normal_user,
            role=self.agent_role,
            assigned_by=self.admin_user
        )
        
        self.login_as_admin()
        
        response = self.client.post(
            reverse('agents:admin_assign_role', kwargs={'user_id': self.normal_user.pk}),
            {'role_id': self.agent_role.pk}
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertFalse(data.get('success', True))
        self.assertIn('error', data)
    
    def test_remove_role_success(self):
        """Test que se puede remover un rol de un usuario."""
        # Asignar rol primero
        agent_role = AgentRole.objects.create(
            agent=self.normal_user,
            role=self.agent_role,
            assigned_by=self.admin_user
        )
        
        self.login_as_admin()
        
        response = self.client.post(
            reverse('agents:admin_remove_role', kwargs={
                'user_id': self.normal_user.pk,
                'role_id': self.agent_role.pk
            })
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        
        # Verificar que el rol fue desactivado
        agent_role.refresh_from_db()
        self.assertFalse(agent_role.is_active)
    
    def test_remove_nonexistent_role(self):
        """Test que se maneja correctamente remover un rol no asignado."""
        self.login_as_admin()
        
        response = self.client.post(
            reverse('agents:admin_remove_role', kwargs={
                'user_id': self.normal_user.pk,
                'role_id': self.agent_role.pk
            })
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertFalse(data.get('success', True))
        self.assertIn('error', data)


class AdminAuditLogViewTest(AdminViewsTestCase):
    """Tests para la vista de logs de auditoría."""
    
    def test_audit_logs_access_as_admin(self):
        """Test que el administrador puede ver los logs de auditoría."""
        self.login_as_admin()
        response = self.client.get(reverse('agents:admin_audit_logs'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Logs de Auditoría')
        self.assertContains(response, 'login')
        self.assertContains(response, 'profile_update')
    
    def test_audit_logs_filters(self):
        """Test que los filtros de logs funcionan correctamente."""
        self.login_as_admin()
        
        # Filtrar por usuario
        response = self.client.get(reverse('agents:admin_audit_logs'), {
            'user': self.normal_user.pk
        })
        
        self.assertEqual(response.status_code, 200)
        # Verificar que solo aparecen logs del usuario filtrado
        for log in response.context['audit_logs']:
            self.assertEqual(log.agent, self.normal_user)
    
    def test_audit_logs_action_filter(self):
        """Test que el filtro por acción funciona."""
        self.login_as_admin()
        
        response = self.client.get(reverse('agents:admin_audit_logs'), {
            'action': 'login'
        })
        
        self.assertEqual(response.status_code, 200)
        # Verificar que solo aparecen logs de login
        for log in response.context['audit_logs']:
            self.assertEqual(log.action, 'login')
    
    def test_audit_logs_success_filter(self):
        """Test que el filtro por éxito/fallo funciona."""
        self.login_as_admin()
        
        response = self.client.get(reverse('agents:admin_audit_logs'), {
            'success': 'false'
        })
        
        self.assertEqual(response.status_code, 200)
        # Verificar que solo aparecen logs fallidos
        for log in response.context['audit_logs']:
            self.assertFalse(log.success)
    
    def test_audit_logs_date_filter(self):
        """Test que los filtros de fecha funcionan."""
        self.login_as_admin()
        
        today = timezone.now().date()
        response = self.client.get(reverse('agents:admin_audit_logs'), {
            'date_from': today.strftime('%Y-%m-%d'),
            'date_to': today.strftime('%Y-%m-%d')
        })
        
        self.assertEqual(response.status_code, 200)
        # Verificar que solo aparecen logs de hoy
        for log in response.context['audit_logs']:
            self.assertEqual(log.created_at.date(), today)


class AdminExportAuditLogsTest(AdminViewsTestCase):
    """Tests para la exportación de logs de auditoría."""
    
    def test_export_audit_logs_success(self):
        """Test que se pueden exportar los logs de auditoría."""
        self.login_as_admin()
        
        response = self.client.get(reverse('agents:admin_export_audit_logs'))
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertIn('attachment', response['Content-Disposition'])
    
    def test_export_audit_logs_with_filters(self):
        """Test que la exportación respeta los filtros aplicados."""
        self.login_as_admin()
        
        response = self.client.get(reverse('agents:admin_export_audit_logs'), {
            'action': 'login',
            'success': 'true'
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        
        # Verificar que el contenido CSV contiene los datos esperados
        content = response.content.decode('utf-8')
        self.assertIn('login', content)
    
    def test_export_creates_audit_log(self):
        """Test que la exportación crea un log de auditoría."""
        self.login_as_admin()
        
        initial_logs = AuditLog.objects.count()
        
        self.client.get(reverse('agents:admin_export_audit_logs'))
        
        # Verificar que se creó un nuevo log
        self.assertEqual(AuditLog.objects.count(), initial_logs + 1)
        
        # Verificar el contenido del log
        log = AuditLog.objects.latest('created_at')
        self.assertEqual(log.action, 'audit_logs_exported')
        self.assertEqual(log.agent, self.admin_user)


class AdminSessionManagementTest(AdminViewsTestCase):
    """Tests para la gestión de sesiones desde administración."""
    
    def setUp(self):
        super().setUp()
        
        # Crear una sesión de prueba
        self.test_session = UserSession.objects.create(
            agent=self.normal_user,
            session_key='test_session_key_123',
            ip_address='192.168.1.100',
            user_agent='Test Browser',
            expires_at=timezone.now() + timedelta(hours=8)
        )
    
    def test_terminate_session_success(self):
        """Test que se puede terminar una sesión desde administración."""
        self.login_as_admin()
        
        response = self.client.post(
            reverse('agents:admin_terminate_session', kwargs={
                'session_key': self.test_session.session_key
            })
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        
        # Verificar que la sesión fue terminada
        self.test_session.refresh_from_db()
        self.assertFalse(self.test_session.is_active)
    
    def test_terminate_nonexistent_session(self):
        """Test que se maneja correctamente una sesión inexistente."""
        self.login_as_admin()
        
        response = self.client.post(
            reverse('agents:admin_terminate_session', kwargs={
                'session_key': 'nonexistent_session'
            })
        )
        
        self.assertEqual(response.status_code, 404)
    
    def test_terminate_session_creates_audit_log(self):
        """Test que terminar una sesión crea un log de auditoría."""
        self.login_as_admin()
        
        initial_logs = AuditLog.objects.count()
        
        self.client.post(
            reverse('agents:admin_terminate_session', kwargs={
                'session_key': self.test_session.session_key
            })
        )
        
        # Verificar que se creó un nuevo log
        self.assertEqual(AuditLog.objects.count(), initial_logs + 1)
        
        # Verificar el contenido del log
        log = AuditLog.objects.latest('created_at')
        self.assertEqual(log.action, 'session_terminated_by_admin')
        self.assertEqual(log.agent, self.admin_user)


class AdminViewsPermissionsTest(AdminViewsTestCase):
    """Tests para verificar permisos de las vistas de administración."""
    
    def test_all_admin_views_require_admin_permission(self):
        """Test que todas las vistas de admin requieren permisos de administrador."""
        admin_urls = [
            'agents:admin_dashboard',
            'agents:admin_user_list',
            'agents:admin_audit_logs',
            'agents:admin_export_audit_logs',
        ]
        
        # Test sin login
        for url_name in admin_urls:
            response = self.client.get(reverse(url_name))
            self.assertIn(response.status_code, [302, 403])  # Redirect to login or forbidden
        
        # Test con usuario normal
        self.login_as_user()
        for url_name in admin_urls:
            response = self.client.get(reverse(url_name))
            self.assertIn(response.status_code, [302, 403])  # Forbidden or redirect
    
    def test_admin_views_accessible_to_admin(self):
        """Test que las vistas de admin son accesibles para administradores."""
        self.login_as_admin()
        
        admin_urls = [
            'agents:admin_dashboard',
            'agents:admin_user_list',
            'agents:admin_audit_logs',
        ]
        
        for url_name in admin_urls:
            response = self.client.get(reverse(url_name))
            self.assertEqual(response.status_code, 200)


class AdminViewsIntegrationTest(AdminViewsTestCase):
    """Tests de integración para las vistas de administración."""
    
    def test_complete_user_management_workflow(self):
        """Test del flujo completo de gestión de usuarios."""
        self.login_as_admin()
        
        # 1. Ver lista de usuarios
        response = self.client.get(reverse('agents:admin_user_list'))
        self.assertEqual(response.status_code, 200)
        
        # 2. Ver detalle de usuario
        response = self.client.get(
            reverse('agents:admin_user_detail', kwargs={'pk': self.normal_user.pk})
        )
        self.assertEqual(response.status_code, 200)
        
        # 3. Asignar rol
        response = self.client.post(
            reverse('agents:admin_assign_role', kwargs={'user_id': self.normal_user.pk}),
            {'role_id': self.agent_role.pk}
        )
        self.assertEqual(response.status_code, 200)
        
        # 4. Verificar que el rol fue asignado
        self.assertTrue(
            AgentRole.objects.filter(
                agent=self.normal_user,
                role=self.agent_role,
                is_active=True
            ).exists()
        )
        
        # 5. Desactivar usuario
        response = self.client.post(
            reverse('agents:admin_user_toggle_status', kwargs={'user_id': self.normal_user.pk})
        )
        self.assertEqual(response.status_code, 200)
        
        # 6. Verificar que el usuario fue desactivado
        self.normal_user.refresh_from_db()
        self.assertFalse(self.normal_user.is_active)
        
        # 7. Ver logs de auditoría
        response = self.client.get(reverse('agents:admin_audit_logs'))
        self.assertEqual(response.status_code, 200)
        
        # 8. Exportar logs
        response = self.client.get(reverse('agents:admin_export_audit_logs'))
        self.assertEqual(response.status_code, 200)
    
    def test_audit_trail_completeness(self):
        """Test que todas las acciones de administración generan logs de auditoría."""
        self.login_as_admin()
        
        initial_logs = AuditLog.objects.count()
        
        # Realizar varias acciones administrativas
        actions = [
            # Cambiar estado de usuario
            lambda: self.client.post(
                reverse('agents:admin_user_toggle_status', kwargs={'user_id': self.normal_user.pk})
            ),
            # Asignar rol
            lambda: self.client.post(
                reverse('agents:admin_assign_role', kwargs={'user_id': self.normal_user.pk}),
                {'role_id': self.agent_role.pk}
            ),
            # Exportar logs
            lambda: self.client.get(reverse('agents:admin_export_audit_logs')),
        ]
        
        for action in actions:
            action()
        
        # Verificar que se crearon logs para todas las acciones
        final_logs = AuditLog.objects.count()
        self.assertGreater(final_logs, initial_logs)
        
        # Verificar que todos los logs tienen el administrador como agente
        recent_logs = AuditLog.objects.filter(
            created_at__gte=timezone.now() - timedelta(minutes=1)
        )
        
        for log in recent_logs:
            if log.agent:  # Algunos logs pueden ser del sistema
                self.assertEqual(log.agent, self.admin_user)