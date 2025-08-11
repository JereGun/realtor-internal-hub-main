"""
Tests para las vistas mejoradas de autenticación.
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user
from django.contrib.messages import get_messages
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch, MagicMock

from agents.models import Agent, UserProfile, SecuritySettings, AuditLog, UserSession


class EnhancedLoginViewTest(TestCase):
    """Tests para EnhancedLoginView"""
    
    def setUp(self):
        self.client = Client()
        self.agent = Agent.objects.create_user(
            username='test_user',
            email='test@example.com',
            password='TestPassword123!',
            first_name='Test',
            last_name='User',
            license_number='LIC123'
        )
        self.profile = UserProfile.objects.create(agent=self.agent)
        self.security_settings = SecuritySettings.objects.create(agent=self.agent)
        self.login_url = reverse('agents:login')
    
    def test_get_login_page(self):
        """Test acceso a la página de login"""
        response = self.client.get(self.login_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Iniciar Sesión')
        self.assertContains(response, 'email')
        self.assertContains(response, 'password')
    
    def test_redirect_authenticated_user(self):
        """Test redirección de usuario ya autenticado"""
        self.client.login(email='test@example.com', password='TestPassword123!')
        
        response = self.client.get(self.login_url)
        
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('agents:dashboard'))
    
    @patch('agents.views.auth_views.SessionService')
    @patch('agents.views.auth_views.AuthenticationService')
    def test_successful_login(self, mock_auth_service, mock_session_service):
        """Test login exitoso"""
        # Mock del servicio de autenticación
        mock_auth_instance = MagicMock()
        mock_auth_instance.authenticate_user.return_value = (
            self.agent,
            {'success': True, 'message': 'Autenticación exitosa'}
        )
        mock_auth_service.return_value = mock_auth_instance
        
        # Mock del servicio de sesiones
        mock_session_instance = MagicMock()
        mock_session_service.return_value = mock_session_instance
        
        response = self.client.post(self.login_url, {
            'email': 'test@example.com',
            'password': 'TestPassword123!',
            'remember_me': True
        })
        
        # Verificar redirección
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('agents:dashboard'))
        
        # Verificar que el usuario está autenticado
        user = get_user(self.client)
        self.assertTrue(user.is_authenticated)
        self.assertEqual(user, self.agent)
        
        # Verificar que se creó el log de auditoría
        audit_log = AuditLog.objects.filter(
            agent=self.agent,
            action='login',
            success=True
        ).first()
        self.assertIsNotNone(audit_log)
        self.assertEqual(audit_log.details['login_method'], 'enhanced_form')
        self.assertTrue(audit_log.details['remember_me'])
    
    @patch('agents.views.auth_views.AuthenticationService')
    def test_login_requires_2fa(self, mock_auth_service):
        """Test login que requiere 2FA"""
        # Mock del servicio de autenticación
        mock_auth_instance = MagicMock()
        mock_auth_instance.authenticate_user.return_value = (
            self.agent,
            {'requires_2fa': True, 'message': 'Se requiere 2FA'}
        )
        mock_auth_service.return_value = mock_auth_instance
        
        response = self.client.post(self.login_url, {
            'email': 'test@example.com',
            'password': 'TestPassword123!'
        })
        
        # Verificar que no se redirige (formulario inválido)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Se requiere código de autenticación')
        
        # Verificar que el usuario no está autenticado
        user = get_user(self.client)
        self.assertFalse(user.is_authenticated)
    
    @patch('agents.views.auth_views.AuthenticationService')
    def test_invalid_credentials(self, mock_auth_service):
        """Test credenciales inválidas"""
        # Mock del servicio de autenticación
        mock_auth_instance = MagicMock()
        mock_auth_instance.authenticate_user.side_effect = Exception('Credenciales inválidas')
        mock_auth_instance.handle_failed_login.return_value = True
        mock_auth_service.return_value = mock_auth_instance
        
        response = self.client.post(self.login_url, {
            'email': 'test@example.com',
            'password': 'WrongPassword'
        })
        
        # Verificar que no se redirige
        self.assertEqual(response.status_code, 200)
        
        # Verificar mensaje de error
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('Error interno' in str(message) for message in messages))
        
        # Verificar que el usuario no está autenticado
        user = get_user(self.client)
        self.assertFalse(user.is_authenticated)
    
    def test_next_url_redirect(self):
        """Test redirección a URL específica después del login"""
        next_url = reverse('agents:profile')
        
        with patch('agents.views.auth_views.AuthenticationService') as mock_auth_service, \
             patch('agents.views.auth_views.SessionService') as mock_session_service:
            
            # Mock del servicio de autenticación
            mock_auth_instance = MagicMock()
            mock_auth_instance.authenticate_user.return_value = (
                self.agent,
                {'success': True, 'message': 'Autenticación exitosa'}
            )
            mock_auth_service.return_value = mock_auth_instance
            
            # Mock del servicio de sesiones
            mock_session_instance = MagicMock()
            mock_session_service.return_value = mock_session_instance
            
            response = self.client.post(f'{self.login_url}?next={next_url}', {
                'email': 'test@example.com',
                'password': 'TestPassword123!'
            })
            
            # Verificar redirección a la URL solicitada
            self.assertEqual(response.status_code, 302)
            self.assertRedirects(response, next_url)


class EnhancedLogoutViewTest(TestCase):
    """Tests para enhanced_logout_view"""
    
    def setUp(self):
        self.client = Client()
        self.agent = Agent.objects.create_user(
            username='test_user',
            email='test@example.com',
            password='TestPassword123!',
            first_name='Test',
            last_name='User',
            license_number='LIC123'
        )
        self.logout_url = reverse('agents:logout')
    
    @patch('agents.views.auth_views.SessionService')
    def test_successful_logout(self, mock_session_service):
        """Test logout exitoso"""
        # Login primero
        self.client.login(email='test@example.com', password='TestPassword123!')
        
        # Mock del servicio de sesiones
        mock_session_instance = MagicMock()
        mock_session_instance.terminate_session.return_value = True
        mock_session_service.return_value = mock_session_instance
        
        response = self.client.get(self.logout_url)
        
        # Verificar redirección
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('agents:login'))
        
        # Verificar que el usuario no está autenticado
        user = get_user(self.client)
        self.assertFalse(user.is_authenticated)
        
        # Verificar que se creó el log de auditoría
        audit_log = AuditLog.objects.filter(
            agent=self.agent,
            action='logout',
            success=True
        ).first()
        self.assertIsNotNone(audit_log)
        self.assertEqual(audit_log.details['logout_method'], 'manual')
    
    def test_logout_without_login(self):
        """Test logout sin estar logueado"""
        response = self.client.get(self.logout_url)
        
        # Debería redirigir al login (por @login_required)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/agents/login/', response.url)


class PasswordResetRequestViewTest(TestCase):
    """Tests para PasswordResetRequestView"""
    
    def setUp(self):
        self.client = Client()
        self.agent = Agent.objects.create_user(
            username='test_user',
            email='test@example.com',
            password='TestPassword123!',
            first_name='Test',
            last_name='User',
            license_number='LIC123'
        )
        self.profile = UserProfile.objects.create(agent=self.agent)
        self.reset_url = reverse('agents:password_reset_request')
    
    def test_get_password_reset_page(self):
        """Test acceso a la página de reset"""
        response = self.client.get(self.reset_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'email')
    
    @patch('agents.views.auth_views.AuthenticationService')
    def test_valid_email_reset_request(self, mock_auth_service):
        """Test solicitud válida de reset"""
        # Mock del servicio de autenticación
        mock_auth_instance = MagicMock()
        mock_auth_instance.generate_password_reset_token.return_value = 'test_token'
        mock_auth_service.return_value = mock_auth_instance
        
        response = self.client.post(self.reset_url, {
            'email': 'test@example.com'
        })
        
        # Verificar redirección
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('agents:password_reset_sent'))
        
        # Verificar mensaje de éxito
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('recibirás instrucciones' in str(message) for message in messages))
    
    def test_nonexistent_email_reset_request(self):
        """Test solicitud con email inexistente"""
        response = self.client.post(self.reset_url, {
            'email': 'nonexistent@example.com'
        })
        
        # Verificar redirección (por seguridad, mismo comportamiento)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('agents:password_reset_sent'))
        
        # Verificar mensaje de éxito (por seguridad)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('recibirás instrucciones' in str(message) for message in messages))
    
    def test_invalid_email_format(self):
        """Test formato de email inválido"""
        response = self.client.post(self.reset_url, {
            'email': 'invalid-email'
        })
        
        # Verificar que no se redirige (formulario inválido)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'email')


class PasswordResetConfirmViewTest(TestCase):
    """Tests para PasswordResetConfirmView"""
    
    def setUp(self):
        self.client = Client()
        self.agent = Agent.objects.create_user(
            username='test_user',
            email='test@example.com',
            password='TestPassword123!',
            first_name='Test',
            last_name='User',
            license_number='LIC123'
        )
        self.profile = UserProfile.objects.create(
            agent=self.agent,
            password_reset_token='valid_token',
            password_reset_expires=timezone.now() + timedelta(hours=1)
        )
        self.security_settings = SecuritySettings.objects.create(agent=self.agent)
    
    def test_get_password_reset_confirm_page(self):
        """Test acceso a la página de confirmación con token válido"""
        url = reverse('agents:password_reset_confirm', kwargs={'token': 'valid_token'})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'new_password1')
        self.assertContains(response, 'new_password2')
    
    def test_invalid_token(self):
        """Test token inválido"""
        url = reverse('agents:password_reset_confirm', kwargs={'token': 'invalid_token'})
        response = self.client.get(url)
        
        # Verificar redirección
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('agents:password_reset_request'))
        
        # Verificar mensaje de error
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('inválido o ha expirado' in str(message) for message in messages))
    
    def test_expired_token(self):
        """Test token expirado"""
        # Hacer que el token expire
        self.profile.password_reset_expires = timezone.now() - timedelta(hours=1)
        self.profile.save()
        
        url = reverse('agents:password_reset_confirm', kwargs={'token': 'valid_token'})
        response = self.client.get(url)
        
        # Verificar redirección
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('agents:password_reset_request'))
    
    @patch('agents.views.auth_views.SessionService')
    def test_successful_password_reset(self, mock_session_service):
        """Test reset exitoso de contraseña"""
        # Mock del servicio de sesiones
        mock_session_instance = MagicMock()
        mock_session_instance.terminate_all_sessions.return_value = 2
        mock_session_service.return_value = mock_session_instance
        
        url = reverse('agents:password_reset_confirm', kwargs={'token': 'valid_token'})
        response = self.client.post(url, {
            'new_password1': 'NewStrongPassword123!',
            'new_password2': 'NewStrongPassword123!'
        })
        
        # Verificar redirección
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('agents:login'))
        
        # Verificar que la contraseña cambió
        self.agent.refresh_from_db()
        self.assertTrue(self.agent.check_password('NewStrongPassword123!'))
        
        # Verificar que el token se limpió
        self.profile.refresh_from_db()
        self.assertIsNone(self.profile.password_reset_token)
        self.assertIsNone(self.profile.password_reset_expires)
        
        # Verificar que se actualizaron las configuraciones de seguridad
        self.security_settings.refresh_from_db()
        self.assertIsNotNone(self.security_settings.password_changed_at)
        self.assertFalse(self.security_settings.require_password_change)
        
        # Verificar que se creó el log de auditoría
        audit_log = AuditLog.objects.filter(
            agent=self.agent,
            action='password_change',
            success=True
        ).first()
        self.assertIsNotNone(audit_log)
        self.assertEqual(audit_log.details['method'], 'password_reset')
        
        # Verificar mensaje de éxito
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('cambiada exitosamente' in str(message) for message in messages))
    
    def test_password_mismatch(self):
        """Test contraseñas que no coinciden"""
        url = reverse('agents:password_reset_confirm', kwargs={'token': 'valid_token'})
        response = self.client.post(url, {
            'new_password1': 'NewStrongPassword123!',
            'new_password2': 'DifferentPassword123!'
        })
        
        # Verificar que no se redirige (formulario inválido)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'new_password1')


class ChangePasswordViewTest(TestCase):
    """Tests para change_password_view"""
    
    def setUp(self):
        self.client = Client()
        self.agent = Agent.objects.create_user(
            username='test_user',
            email='test@example.com',
            password='TestPassword123!',
            first_name='Test',
            last_name='User',
            license_number='LIC123'
        )
        self.security_settings = SecuritySettings.objects.create(agent=self.agent)
        self.change_password_url = reverse('agents:change_password')
    
    def test_get_change_password_page(self):
        """Test acceso a la página de cambio de contraseña"""
        self.client.login(email='test@example.com', password='TestPassword123!')
        
        response = self.client.get(self.change_password_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'old_password')
        self.assertContains(response, 'new_password1')
        self.assertContains(response, 'new_password2')
    
    def test_change_password_requires_login(self):
        """Test que cambio de contraseña requiere login"""
        response = self.client.get(self.change_password_url)
        
        # Debería redirigir al login
        self.assertEqual(response.status_code, 302)
        self.assertIn('/agents/login/', response.url)
    
    def test_successful_password_change(self):
        """Test cambio exitoso de contraseña"""
        self.client.login(email='test@example.com', password='TestPassword123!')
        
        response = self.client.post(self.change_password_url, {
            'old_password': 'TestPassword123!',
            'new_password1': 'NewStrongPassword123!',
            'new_password2': 'NewStrongPassword123!'
        })
        
        # Verificar redirección
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('agents:profile'))
        
        # Verificar que la contraseña cambió
        self.agent.refresh_from_db()
        self.assertTrue(self.agent.check_password('NewStrongPassword123!'))
        
        # Verificar que se actualizaron las configuraciones de seguridad
        self.security_settings.refresh_from_db()
        self.assertIsNotNone(self.security_settings.password_changed_at)
        
        # Verificar que se creó el log de auditoría
        audit_log = AuditLog.objects.filter(
            agent=self.agent,
            action='password_change',
            success=True
        ).first()
        self.assertIsNotNone(audit_log)
        self.assertEqual(audit_log.details['method'], 'user_initiated')
        
        # Verificar mensaje de éxito
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('cambiada exitosamente' in str(message) for message in messages))
    
    def test_wrong_old_password(self):
        """Test contraseña actual incorrecta"""
        self.client.login(email='test@example.com', password='TestPassword123!')
        
        response = self.client.post(self.change_password_url, {
            'old_password': 'WrongPassword',
            'new_password1': 'NewStrongPassword123!',
            'new_password2': 'NewStrongPassword123!'
        })
        
        # Verificar que no se redirige (formulario inválido)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'old_password')


class SessionManagementViewsTest(TestCase):
    """Tests para vistas de gestión de sesiones"""
    
    def setUp(self):
        self.client = Client()
        self.agent = Agent.objects.create_user(
            username='test_user',
            email='test@example.com',
            password='TestPassword123!',
            first_name='Test',
            last_name='User',
            license_number='LIC123'
        )
        
        # Crear sesión de prueba
        self.user_session = UserSession.objects.create(
            agent=self.agent,
            session_key='test_session_key',
            ip_address='192.168.1.1',
            user_agent='Test Browser',
            expires_at=timezone.now() + timedelta(hours=1)
        )
    
    @patch('agents.views.auth_views.SessionService')
    def test_terminate_session_success(self, mock_session_service):
        """Test terminación exitosa de sesión"""
        self.client.login(email='test@example.com', password='TestPassword123!')
        
        # Mock del servicio de sesiones
        mock_session_instance = MagicMock()
        mock_session_instance.get_session_info.return_value = {
            'agent': {'id': self.agent.id},
            'session_key': 'test_session_key'
        }
        mock_session_instance.terminate_session.return_value = True
        mock_session_service.return_value = mock_session_instance
        
        url = reverse('agents:terminate_session', kwargs={'session_key': 'test_session_key'})
        response = self.client.post(url)
        
        # Verificar respuesta JSON exitosa
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['message'], 'Sesión terminada')
    
    @patch('agents.views.auth_views.SessionService')
    def test_terminate_session_not_found(self, mock_session_service):
        """Test terminación de sesión inexistente"""
        self.client.login(email='test@example.com', password='TestPassword123!')
        
        # Mock del servicio de sesiones
        mock_session_instance = MagicMock()
        mock_session_instance.get_session_info.return_value = None
        mock_session_service.return_value = mock_session_instance
        
        url = reverse('agents:terminate_session', kwargs={'session_key': 'nonexistent_key'})
        response = self.client.post(url)
        
        # Verificar respuesta de error
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertEqual(data['error'], 'Sesión no encontrada')
    
    @patch('agents.views.auth_views.SessionService')
    def test_terminate_all_sessions_success(self, mock_session_service):
        """Test terminación exitosa de todas las sesiones"""
        self.client.login(email='test@example.com', password='TestPassword123!')
        
        # Mock del servicio de sesiones
        mock_session_instance = MagicMock()
        mock_session_instance.terminate_all_sessions.return_value = 3
        mock_session_service.return_value = mock_session_instance
        
        url = reverse('agents:terminate_all_sessions')
        response = self.client.post(url)
        
        # Verificar respuesta JSON exitosa
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['terminated_count'], 3)
        
        # Verificar mensaje de éxito
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('Se terminaron 3 sesiones' in str(message) for message in messages))
    
    def test_session_views_require_login(self):
        """Test que vistas de sesión requieren login"""
        # Test terminate_session
        url = reverse('agents:terminate_session', kwargs={'session_key': 'test_key'})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        
        # Test terminate_all_sessions
        url = reverse('agents:terminate_all_sessions')
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
    
    def test_session_views_require_post(self):
        """Test que vistas de sesión requieren método POST"""
        self.client.login(email='test@example.com', password='TestPassword123!')
        
        # Test terminate_session con GET
        url = reverse('agents:terminate_session', kwargs={'session_key': 'test_key'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 405)  # Method Not Allowed
        
        # Test terminate_all_sessions con GET
        url = reverse('agents:terminate_all_sessions')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 405)  # Method Not Allowed