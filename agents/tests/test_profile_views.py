"""
Tests de integración para vistas de gestión de perfil.

Este módulo contiene tests completos para todas las vistas de gestión
de perfil, incluyendo visualización, edición, configuraciones de seguridad
y gestión de sesiones.
"""

import json
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from unittest.mock import patch, MagicMock

from agents.models import Agent, UserProfile, SecuritySettings, UserSession, AuditLog
from agents.services.user_management_service import UserManagementService
from agents.services.session_service import SessionService


class ProfileViewsIntegrationTest(TestCase):
    """
    Tests de integración para vistas de perfil.
    """
    
    def setUp(self):
        """Configuración inicial para los tests."""
        self.client = Client()
        
        # Crear usuario de prueba
        self.agent = Agent.objects.create_user(
            username='test_agent',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='Agent',
            license_number='LIC123'
        )
        
        # Crear perfil
        self.profile = UserProfile.objects.create(
            agent=self.agent,
            timezone='America/Argentina/Buenos_Aires',
            language='es',
            theme='light'
        )
        
        # Crear configuraciones de seguridad
        self.security_settings = SecuritySettings.objects.create(
            agent=self.agent,
            session_timeout_minutes=480,
            suspicious_activity_alerts=True
        )
        
        # Crear sesión de prueba
        self.session = UserSession.objects.create(
            agent=self.agent,
            session_key='test_session_key',
            ip_address='127.0.0.1',
            user_agent='Test Browser',
            device_info={'device_type': 'desktop', 'browser': 'Chrome'},
            location={'country': 'Argentina', 'city': 'Buenos Aires'},
            expires_at=timezone.now() + timezone.timedelta(hours=8)
        )
        
        # Inicializar servicios
        self.user_service = UserManagementService()
        self.session_service = SessionService()
    
    def test_profile_view_authenticated_user(self):
        """Test de vista de perfil para usuario autenticado."""
        # Login
        self.client.login(email='test@example.com', password='testpass123')
        
        # Acceder a la vista de perfil
        response = self.client.get(reverse('agents:profile_view'))
        
        # Verificar respuesta
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Mi Perfil')
        self.assertContains(response, self.agent.get_full_name())
        self.assertContains(response, self.agent.email)
        
        # Verificar contexto
        self.assertEqual(response.context['agent'], self.agent)
        self.assertEqual(response.context['profile'], self.profile)
        self.assertEqual(response.context['security_settings'], self.security_settings)
        self.assertIn('profile_completion', response.context)
        self.assertIn('active_sessions', response.context)
        self.assertIn('recent_activity', response.context)
        self.assertIn('profile_stats', response.context)
    
    def test_profile_view_unauthenticated_user(self):
        """Test de vista de perfil para usuario no autenticado."""
        response = self.client.get(reverse('agents:profile_view'))
        
        # Debe redirigir al login
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)
    
    def test_profile_edit_view_get(self):
        """Test de vista de edición de perfil (GET)."""
        self.client.login(email='test@example.com', password='testpass123')
        
        response = self.client.get(reverse('agents:profile_edit'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Editar Perfil')
        self.assertContains(response, 'form')
        
        # Verificar que el formulario está pre-poblado
        form = response.context['form']
        self.assertEqual(form.initial.get('first_name'), self.agent.first_name)
        self.assertEqual(form.initial.get('last_name'), self.agent.last_name)
    
    def test_profile_edit_view_post_valid_data(self):
        """Test de actualización de perfil con datos válidos."""
        self.client.login(email='test@example.com', password='testpass123')
        
        # Crear imagen de prueba
        test_image = SimpleUploadedFile(
            "test_avatar.jpg",
            b"fake_image_content",
            content_type="image/jpeg"
        )
        
        # Datos de actualización
        update_data = {
            'first_name': 'Updated',
            'last_name': 'Name',
            'phone': '+54 11 1234-5678',
            'bio': 'Updated bio',
            'avatar': test_image,
            'timezone': 'America/Argentina/Cordoba',
            'language': 'en',
            'theme': 'dark'
        }
        
        response = self.client.post(reverse('agents:profile_edit'), update_data)
        
        # Verificar redirección exitosa
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('agents:profile'))
        
        # Verificar que los datos se actualizaron
        self.agent.refresh_from_db()
        self.profile.refresh_from_db()
        
        self.assertEqual(self.agent.first_name, 'Updated')
        self.assertEqual(self.agent.last_name, 'Name')
        self.assertEqual(self.agent.phone, '+54 11 1234-5678')
        self.assertEqual(self.agent.bio, 'Updated bio')
        self.assertEqual(self.profile.timezone, 'America/Argentina/Cordoba')
        self.assertEqual(self.profile.language, 'en')
        self.assertEqual(self.profile.theme, 'dark')
        
        # Verificar que se creó un log de auditoría
        audit_log = AuditLog.objects.filter(
            agent=self.agent,
            action='profile_update'
        ).first()
        self.assertIsNotNone(audit_log)
        self.assertTrue(audit_log.success)
    
    def test_profile_edit_view_post_invalid_data(self):
        """Test de actualización de perfil con datos inválidos."""
        self.client.login(email='test@example.com', password='testpass123')
        
        # Datos inválidos (teléfono muy corto)
        invalid_data = {
            'first_name': '',  # Campo requerido vacío
            'last_name': 'Name',
            'phone': '123',  # Teléfono muy corto
            'bio': 'Bio',
            'timezone': 'America/Argentina/Buenos_Aires',
            'language': 'es',
            'theme': 'light'
        }
        
        response = self.client.post(reverse('agents:profile_edit'), invalid_data)
        
        # Debe mostrar el formulario con errores
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'form')
        self.assertTrue(response.context['form'].errors)
    
    def test_security_settings_view_get(self):
        """Test de vista de configuraciones de seguridad (GET)."""
        self.client.login(email='test@example.com', password='testpass123')
        
        response = self.client.get(reverse('agents:security_settings'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Configuraciones de Seguridad')
        self.assertContains(response, 'form')
        
        # Verificar contexto
        self.assertIn('security_settings', response.context)
        self.assertIn('security_stats', response.context)
        self.assertIn('show_2fa_setup', response.context)
    
    def test_security_settings_view_post_valid_data(self):
        """Test de actualización de configuraciones de seguridad."""
        self.client.login(email='test@example.com', password='testpass123')
        
        update_data = {
            'session_timeout_minutes': 240,  # 4 horas
            'suspicious_activity_alerts': False,
            'allowed_ip_addresses': '192.168.1.100\n10.0.0.*'
        }
        
        response = self.client.post(reverse('agents:security_settings'), update_data)
        
        # Verificar redirección exitosa
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('agents:security_settings'))
        
        # Verificar que los datos se actualizaron
        self.security_settings.refresh_from_db()
        self.assertEqual(self.security_settings.session_timeout_minutes, 240)
        self.assertFalse(self.security_settings.suspicious_activity_alerts)
        self.assertEqual(
            self.security_settings.allowed_ip_addresses,
            ['192.168.1.100', '10.0.0.*']
        )
        
        # Verificar log de auditoría
        audit_log = AuditLog.objects.filter(
            agent=self.agent,
            action='security_settings_change'
        ).first()
        self.assertIsNotNone(audit_log)
        self.assertTrue(audit_log.success)
    
    def test_security_settings_enable_2fa_redirect(self):
        """Test de habilitación de 2FA redirige a configuración."""
        self.client.login(email='test@example.com', password='testpass123')
        
        update_data = {
            'enable_2fa': True,
            'session_timeout_minutes': 480,
            'suspicious_activity_alerts': True,
            'allowed_ip_addresses': ''
        }
        
        with patch('agents.views.profile_views.redirect') as mock_redirect:
            mock_redirect.return_value = MagicMock()
            response = self.client.post(reverse('agents:security_settings'), update_data)
            
            # Verificar que se intenta redirigir a setup_2fa
            # (aunque la URL no existe en este test, verificamos la lógica)
            self.assertEqual(response.status_code, 302)
    
    def test_session_management_view(self):
        """Test de vista de gestión de sesiones."""
        self.client.login(email='test@example.com', password='testpass123')
        
        response = self.client.get(reverse('agents:session_management'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Gestión de Sesiones')
        
        # Verificar contexto
        self.assertIn('sessions_data', response.context)
        self.assertIn('session_stats', response.context)
        self.assertIn('current_session_key', response.context)
        
        # Verificar que la sesión aparece en los datos
        sessions_data = response.context['sessions_data']
        self.assertTrue(len(sessions_data) > 0)
        
        # Verificar estadísticas
        session_stats = response.context['session_stats']
        self.assertIn('total_active', session_stats)
        self.assertIn('unique_ips', session_stats)
        self.assertIn('unique_devices', session_stats)
    
    def test_terminate_specific_session_view_success(self):
        """Test de terminación de sesión específica exitosa."""
        self.client.login(email='test@example.com', password='testpass123')
        
        # Crear otra sesión para terminar
        other_session = UserSession.objects.create(
            agent=self.agent,
            session_key='other_session_key',
            ip_address='192.168.1.100',
            user_agent='Other Browser',
            device_info={'device_type': 'mobile', 'browser': 'Safari'},
            location={'country': 'Argentina', 'city': 'Cordoba'},
            expires_at=timezone.now() + timezone.timedelta(hours=8)
        )
        
        response = self.client.post(
            reverse('agents:terminate_specific_session', 
                   kwargs={'session_key': other_session.session_key})
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Verificar respuesta JSON
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertIn('message', data)
        
        # Verificar que la sesión se terminó
        other_session.refresh_from_db()
        self.assertFalse(other_session.is_active)
        
        # Verificar log de auditoría
        audit_log = AuditLog.objects.filter(
            agent=self.agent,
            action='session_terminated',
            resource_id=other_session.session_key
        ).first()
        self.assertIsNotNone(audit_log)
    
    def test_terminate_specific_session_view_current_session(self):
        """Test de intento de terminar sesión actual (debe fallar)."""
        self.client.login(email='test@example.com', password='testpass123')
        
        # Simular sesión actual
        session = self.client.session
        session_key = session.session_key
        
        # Crear UserSession correspondiente
        current_session = UserSession.objects.create(
            agent=self.agent,
            session_key=session_key,
            ip_address='127.0.0.1',
            user_agent='Test Browser',
            device_info={'device_type': 'desktop'},
            location={'country': 'Local'},
            expires_at=timezone.now() + timezone.timedelta(hours=8)
        )
        
        response = self.client.post(
            reverse('agents:terminate_specific_session', 
                   kwargs={'session_key': session_key})
        )
        
        self.assertEqual(response.status_code, 400)
        
        # Verificar respuesta JSON de error
        data = json.loads(response.content)
        self.assertFalse(data['success'])
        self.assertIn('No puede terminar su sesión actual', data['error'])
    
    def test_terminate_specific_session_view_not_found(self):
        """Test de terminación de sesión inexistente."""
        self.client.login(email='test@example.com', password='testpass123')
        
        response = self.client.post(
            reverse('agents:terminate_specific_session', 
                   kwargs={'session_key': 'nonexistent_session'})
        )
        
        self.assertEqual(response.status_code, 404)
        
        # Verificar respuesta JSON de error
        data = json.loads(response.content)
        self.assertFalse(data['success'])
        self.assertIn('no encontrada', data['error'])
    
    def test_terminate_other_sessions_view(self):
        """Test de terminación de todas las otras sesiones."""
        self.client.login(email='test@example.com', password='testpass123')
        
        # Crear sesiones adicionales
        session1 = UserSession.objects.create(
            agent=self.agent,
            session_key='session_1',
            ip_address='192.168.1.100',
            user_agent='Browser 1',
            device_info={'device_type': 'desktop'},
            location={'country': 'Argentina'},
            expires_at=timezone.now() + timezone.timedelta(hours=8)
        )
        
        session2 = UserSession.objects.create(
            agent=self.agent,
            session_key='session_2',
            ip_address='192.168.1.101',
            user_agent='Browser 2',
            device_info={'device_type': 'mobile'},
            location={'country': 'Argentina'},
            expires_at=timezone.now() + timezone.timedelta(hours=8)
        )
        
        response = self.client.post(reverse('agents:terminate_other_sessions'))
        
        self.assertEqual(response.status_code, 200)
        
        # Verificar respuesta JSON
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertIn('terminated_count', data)
        
        # Verificar que las sesiones se terminaron
        session1.refresh_from_db()
        session2.refresh_from_db()
        self.assertFalse(session1.is_active)
        self.assertFalse(session2.is_active)
        
        # Verificar logs de auditoría
        audit_logs = AuditLog.objects.filter(
            agent=self.agent,
            action='sessions_terminated'
        )
        self.assertTrue(audit_logs.exists())
    
    def test_profile_completion_data_api(self):
        """Test de API de datos de completitud del perfil."""
        self.client.login(email='test@example.com', password='testpass123')
        
        response = self.client.get(reverse('agents:profile_completion_data'))
        
        self.assertEqual(response.status_code, 200)
        
        # Verificar respuesta JSON
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertIn('completion_percentage', data)
        self.assertIn('completed_fields', data)
        self.assertIn('missing_fields', data)
        self.assertIn('recommendations', data)
        
        # Verificar que el porcentaje es un número válido
        self.assertIsInstance(data['completion_percentage'], int)
        self.assertGreaterEqual(data['completion_percentage'], 0)
        self.assertLessEqual(data['completion_percentage'], 100)
    
    @patch('agents.views.profile_views.UserManagementService')
    def test_profile_view_service_error_handling(self, mock_service_class):
        """Test de manejo de errores en vista de perfil."""
        # Configurar mock para lanzar excepción
        mock_service = MagicMock()
        mock_service.calculate_profile_completion.side_effect = Exception("Service error")
        mock_service_class.return_value = mock_service
        
        self.client.login(email='test@example.com', password='testpass123')
        
        response = self.client.get(reverse('agents:profile_view'))
        
        # Debe manejar el error graciosamente
        self.assertEqual(response.status_code, 200)
        self.assertIn('error', response.context)
        self.assertTrue(response.context['error'])
    
    def test_profile_edit_view_transaction_rollback(self):
        """Test de rollback de transacción en caso de error."""
        self.client.login(email='test@example.com', password='testpass123')
        
        # Datos que causarán error en el servicio
        with patch('agents.services.user_management_service.UserManagementService.calculate_profile_completion') as mock_calc:
            mock_calc.side_effect = Exception("Calculation error")
            
            update_data = {
                'first_name': 'Updated',
                'last_name': 'Name',
                'phone': '+54 11 1234-5678',
                'bio': 'Updated bio',
                'timezone': 'America/Argentina/Buenos_Aires',
                'language': 'es',
                'theme': 'light'
            }
            
            response = self.client.post(reverse('agents:profile_edit'), update_data)
            
            # Debe mostrar error y no actualizar datos
            self.assertEqual(response.status_code, 200)
            
            # Verificar que los datos originales no cambiaron
            self.agent.refresh_from_db()
            self.assertEqual(self.agent.first_name, 'Test')  # Valor original
    
    def test_security_settings_view_ip_validation(self):
        """Test de validación de direcciones IP en configuraciones de seguridad."""
        self.client.login(email='test@example.com', password='testpass123')
        
        # Datos con IP inválida
        invalid_data = {
            'session_timeout_minutes': 480,
            'suspicious_activity_alerts': True,
            'allowed_ip_addresses': '999.999.999.999\ninvalid_ip'
        }
        
        response = self.client.post(reverse('agents:security_settings'), invalid_data)
        
        # Debe mostrar errores de validación
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['form'].errors)
        self.assertIn('allowed_ip_addresses', response.context['form'].errors)
    
    def test_session_management_view_device_detection(self):
        """Test de detección de dispositivos en gestión de sesiones."""
        self.client.login(email='test@example.com', password='testpass123')
        
        # Crear sesiones con diferentes user agents
        mobile_session = UserSession.objects.create(
            agent=self.agent,
            session_key='mobile_session',
            ip_address='192.168.1.100',
            user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15',
            device_info={'device_type': 'mobile', 'browser': 'Safari', 'os': 'iOS'},
            location={'country': 'Argentina'},
            expires_at=timezone.now() + timezone.timedelta(hours=8)
        )
        
        desktop_session = UserSession.objects.create(
            agent=self.agent,
            session_key='desktop_session',
            ip_address='192.168.1.101',
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/91.0.4472.124',
            device_info={'device_type': 'desktop', 'browser': 'Chrome', 'os': 'Windows'},
            location={'country': 'Argentina'},
            expires_at=timezone.now() + timezone.timedelta(hours=8)
        )
        
        response = self.client.get(reverse('agents:session_management'))
        
        self.assertEqual(response.status_code, 200)
        
        # Verificar que se detectaron diferentes tipos de dispositivos
        sessions_data = response.context['sessions_data']
        device_names = [session['device_name'] for session in sessions_data]
        
        self.assertIn('Dispositivo Móvil', device_names)
        self.assertIn('PC Windows', device_names)
    
    def test_profile_views_require_authentication(self):
        """Test de que todas las vistas de perfil requieren autenticación."""
        urls_to_test = [
            'agents:profile_view',
            'agents:profile_edit',
            'agents:security_settings',
            'agents:session_management',
            'agents:profile_completion_data'
        ]
        
        for url_name in urls_to_test:
            response = self.client.get(reverse(url_name))
            self.assertEqual(response.status_code, 302)
            self.assertIn('/login/', response.url)
    
    def test_ajax_views_require_post(self):
        """Test de que las vistas AJAX requieren método POST."""
        self.client.login(email='test@example.com', password='testpass123')
        
        ajax_urls = [
            ('agents:terminate_specific_session', {'session_key': 'test_key'}),
            ('agents:terminate_other_sessions', {})
        ]
        
        for url_name, kwargs in ajax_urls:
            # GET debe fallar
            response = self.client.get(reverse(url_name, kwargs=kwargs))
            self.assertEqual(response.status_code, 405)  # Method Not Allowed
    
    def tearDown(self):
        """Limpieza después de cada test."""
        # Limpiar archivos de avatar si se crearon
        if self.profile.avatar:
            try:
                self.profile.avatar.delete()
            except:
                pass
        
        # Limpiar logs de auditoría
        AuditLog.objects.filter(agent=self.agent).delete()
        
        # Limpiar sesiones
        UserSession.objects.filter(agent=self.agent).delete()