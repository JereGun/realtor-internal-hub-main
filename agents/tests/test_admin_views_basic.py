"""
Tests básicos para verificar que las vistas de administración están correctamente configuradas.
"""

from django.test import TestCase
from django.urls import reverse, resolve
from django.contrib.auth import get_user_model

from agents.views.admin_views import (
    AdminUserListView, AdminUserDetailView, AdminAuditLogView,
    admin_dashboard, admin_user_toggle_status, admin_assign_role,
    admin_remove_role, admin_export_audit_logs, admin_terminate_session
)


class AdminViewsBasicTest(TestCase):
    """Tests básicos para verificar configuración de vistas de administración."""
    
    def test_admin_urls_resolve_correctly(self):
        """Test que todas las URLs de administración se resuelven correctamente."""
        url_patterns = [
            ('agents:admin_dashboard', admin_dashboard),
            ('agents:admin_user_list', AdminUserListView),
            ('agents:admin_audit_logs', AdminAuditLogView),
            ('agents:admin_export_audit_logs', admin_export_audit_logs),
        ]
        
        for url_name, expected_view in url_patterns:
            url = reverse(url_name)
            resolved = resolve(url)
            
            if hasattr(expected_view, 'as_view'):
                # Para vistas basadas en clase
                self.assertEqual(resolved.func.view_class, expected_view)
            else:
                # Para vistas basadas en función
                self.assertEqual(resolved.func, expected_view)
    
    def test_admin_user_detail_url_with_parameter(self):
        """Test que la URL de detalle de usuario acepta parámetros."""
        url = reverse('agents:admin_user_detail', kwargs={'pk': 1})
        resolved = resolve(url)
        
        self.assertEqual(resolved.func.view_class, AdminUserDetailView)
        self.assertEqual(resolved.kwargs['pk'], 1)
    
    def test_admin_toggle_status_url_with_parameter(self):
        """Test que la URL de cambio de estado acepta parámetros."""
        url = reverse('agents:admin_user_toggle_status', kwargs={'user_id': 1})
        resolved = resolve(url)
        
        self.assertEqual(resolved.func, admin_user_toggle_status)
        self.assertEqual(resolved.kwargs['user_id'], 1)
    
    def test_admin_assign_role_url_with_parameter(self):
        """Test que la URL de asignación de rol acepta parámetros."""
        url = reverse('agents:admin_assign_role', kwargs={'user_id': 1})
        resolved = resolve(url)
        
        self.assertEqual(resolved.func, admin_assign_role)
        self.assertEqual(resolved.kwargs['user_id'], 1)
    
    def test_admin_remove_role_url_with_parameters(self):
        """Test que la URL de remoción de rol acepta múltiples parámetros."""
        url = reverse('agents:admin_remove_role', kwargs={'user_id': 1, 'role_id': 2})
        resolved = resolve(url)
        
        self.assertEqual(resolved.func, admin_remove_role)
        self.assertEqual(resolved.kwargs['user_id'], 1)
        self.assertEqual(resolved.kwargs['role_id'], 2)
    
    def test_admin_terminate_session_url_with_parameter(self):
        """Test que la URL de terminación de sesión acepta parámetros."""
        url = reverse('agents:admin_terminate_session', kwargs={'session_key': 'test_key'})
        resolved = resolve(url)
        
        self.assertEqual(resolved.func, admin_terminate_session)
        self.assertEqual(resolved.kwargs['session_key'], 'test_key')
    
    def test_admin_views_import_successfully(self):
        """Test que todas las vistas de administración se importan correctamente."""
        from agents.views.admin_views import (
            AdminUserListView, AdminUserDetailView, AdminAuditLogView,
            admin_dashboard, admin_user_toggle_status, admin_assign_role,
            admin_remove_role, admin_export_audit_logs, admin_terminate_session,
            is_admin_user
        )
        
        # Verificar que todas las importaciones son exitosas
        self.assertIsNotNone(AdminUserListView)
        self.assertIsNotNone(AdminUserDetailView)
        self.assertIsNotNone(AdminAuditLogView)
        self.assertIsNotNone(admin_dashboard)
        self.assertIsNotNone(admin_user_toggle_status)
        self.assertIsNotNone(admin_assign_role)
        self.assertIsNotNone(admin_remove_role)
        self.assertIsNotNone(admin_export_audit_logs)
        self.assertIsNotNone(admin_terminate_session)
        self.assertIsNotNone(is_admin_user)
    
    def test_admin_templates_exist(self):
        """Test que los templates de administración existen."""
        import os
        from django.conf import settings
        
        template_files = [
            'agents/admin/dashboard.html',
            'agents/admin/user_list.html',
            'agents/admin/user_detail.html',
            'agents/admin/audit_logs.html'
        ]
        
        for template_file in template_files:
            template_path = os.path.join('templates', template_file)
            self.assertTrue(
                os.path.exists(template_path),
                f"Template {template_file} no existe"
            )