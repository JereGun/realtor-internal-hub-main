"""
Tests de integración para vistas de recuperación de contraseña.

Este módulo contiene tests completos para el flujo de recuperación
de contraseñas, incluyendo solicitud, confirmación y notificaciones.
"""

import json
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core import mail
from unittest.mock import patch, MagicMock

from agents.models import Agent, UserProfile, SecuritySettings, AuditLog
from agents.services.authentication_service import AuthenticationService
from agents.services.email_service import EmailService


class PasswordRecoveryViewsIntegrationTest(TestCase):
    """
    Tests de integración para vistas de recuperación de contraseña.
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
        
        # Crear perfil y configuraciones
        self.profile = UserProfile.objects.create(agent=self.agent)
        self.security_settings = SecuritySettings.objects.create(agent=self.agent)
        
        # Inicializar servicios
        self.auth_service = AuthenticationService()
        self.email_service = EmailService()
        
        # Limpiar logs y emails
        AuditLog.objects.all().delete()
        mail.outbox = []
    
    def test_password_reset_request_view_get(self):
        """Test de vista de solicitud de reset (GET)."""
        response = self.client.get(reverse('agents:password_reset_request'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Recuperar Contraseña')
        self.assertContains(response, 'form')
        self.assertContains(response, 'email')
    
    def test_password_reset_request_valid_email(self):
        """Test de solicitud de reset con email válido."""
        response = self.client.post(reverse('agents:password_reset_request'), {
            'email': 'test@example.com'
        })
        
        # Verificar redirección
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('agents:password_reset_sent'))
        
        # Verificar que se generó token
        self.profile.refresh_from_db()
        self.assertIsNotNone(self.profile.password_reset_token)
        self.assertIsNotNone(self.profile.password_reset_expires)
        
        # Verificar que se registró en auditoría
        audit_logs = AuditLog.objects.filter(
            agent=self.agent,
            action='password_reset_request'
        )
        self.assertTrue(audit_logs.exists())
    
    def test_password_reset_request_invalid_email(self):
        """Test de solicitud de reset con email inválido."""
        response = self.client.post(reverse('agents:password_reset_request'), {
            'email': 'nonexistent@example.com'
        })
        
        # Debe redirigir igual por seguridad
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('agents:password_reset_sent'))
        
        # No debe haber token generado
        self.profile.refresh_from_db()
        self.assertIsNone(self.profile.password_reset_token)
    
    def test_password_reset_sent_view(self):
        """Test de vista de confirmación de envío."""
        response = self.client.get(reverse('agents:password_reset_sent'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Email Enviado')
        self.assertContains(response, 'instrucciones')
        self.assertContains(response, 'próximos minutos')
    
    def test_password_reset_confirm_view_valid_token(self):
        """Test de vista de confirmación con token válido."""
        # Generar token válido
        token = self.auth_service.generate_password_reset_token(self.agent)
        
        response = self.client.get(
            reverse('agents:password_reset_confirm', kwargs={'token': token})
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Cambiar Contraseña')
        self.assertContains(response, self.agent.get_full_name())
        self.assertContains(response, 'form')
    
    def test_password_reset_confirm_view_invalid_token(self):
        """Test de vista de confirmación con token inválido."""
        response = self.client.get(
            reverse('agents:password_reset_confirm', kwargs={'token': 'invalid_token'})
        )
        
        # Debe redirigir a solicitud de reset
        self.assertEqual(response.status_code, 302)
        self.assertIn('password-reset', response.url)
    
    def test_password_reset_confirm_view_expired_token(self):
        """Test de vista de confirmación con token expirado."""
        # Generar token y expirarlo
        token = self.auth_service.generate_password_reset_token(self.agent)
        self.profile.password_reset_expires = timezone.now() - timezone.timedelta(hours=1)
        self.profile.save()
        
        response = self.client.get(
            reverse('agents:password_reset_confirm', kwargs={'token': token})
        )
        
        # Debe redirigir a solicitud de reset
        self.assertEqual(response.status_code, 302)
        self.assertIn('password-reset', response.url)
    
    def test_password_reset_confirm_post_valid_data(self):
        """Test de confirmación de reset con datos válidos."""
        # Generar token válido
        token = self.auth_service.generate_password_reset_token(self.agent)
        
        response = self.client.post(
            reverse('agents:password_reset_confirm', kwargs={'token': token}),
            {
                'new_password1': 'newpassword123',
                'new_password2': 'newpassword123'
            }
        )
        
        # Verificar redirección al login
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('agents:login'))
        
        # Verificar que la contraseña cambió
        self.agent.refresh_from_db()
        self.assertTrue(self.agent.check_password('newpassword123'))
        
        # Verificar que el token se limpió
        self.profile.refresh_from_db()
        self.assertIsNone(self.profile.password_reset_token)
        self.assertIsNone(self.profile.password_reset_expires)
        
        # Verificar configuraciones de seguridad
        self.security_settings.refresh_from_db()
        self.assertFalse(self.security_settings.require_password_change)
        
        # Verificar log de auditoría
        audit_logs = AuditLog.objects.filter(
            agent=self.agent,
            action='password_change'
        )
        self.assertTrue(audit_logs.exists())
        
        log = audit_logs.first()
        self.assertEqual(log.details['method'], 'password_reset')
        self.assertTrue(log.success)
    
    def test_password_reset_confirm_post_invalid_data(self):
        """Test de confirmación de reset con datos inválidos."""
        # Generar token válido
        token = self.auth_service.generate_password_reset_token(self.agent)
        
        response = self.client.post(
            reverse('agents:password_reset_confirm', kwargs={'token': token}),
            {
                'new_password1': 'newpassword123',
                'new_password2': 'differentpassword'  # No coinciden
            }
        )
        
        # Debe mostrar el formulario con errores
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'form')
        self.assertTrue(response.context['form'].errors)
        
        # La contraseña no debe haber cambiado
        self.agent.refresh_from_db()
        self.assertTrue(self.agent.check_password('testpass123'))
    
    def test_change_password_view_authenticated_user(self):
        """Test de vista de cambio de contraseña para usuario autenticado."""
        self.client.login(email='test@example.com', password='testpass123')
        
        response = self.client.get(reverse('agents:change_password'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Cambiar Contraseña')
        self.assertContains(response, 'form')
        self.assertContains(response, 'old_password')
        self.assertContains(response, 'new_password1')
        self.assertContains(response, 'new_password2')
    
    def test_change_password_view_unauthenticated_user(self):
        """Test de vista de cambio de contraseña para usuario no autenticado."""
        response = self.client.get(reverse('agents:change_password'))
        
        # Debe redirigir al login
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)
    
    def test_change_password_post_valid_data(self):
        """Test de cambio de contraseña con datos válidos."""
        self.client.login(email='test@example.com', password='testpass123')
        
        response = self.client.post(reverse('agents:change_password'), {
            'old_password': 'testpass123',
            'new_password1': 'newpassword123',
            'new_password2': 'newpassword123'
        })
        
        # Verificar redirección al perfil
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('agents:profile'))
        
        # Verificar que la contraseña cambió
        self.agent.refresh_from_db()
        self.assertTrue(self.agent.check_password('newpassword123'))
        
        # Verificar configuraciones de seguridad
        self.security_settings.refresh_from_db()
        self.assertFalse(self.security_settings.require_password_change)
        
        # Verificar log de auditoría
        audit_logs = AuditLog.objects.filter(
            agent=self.agent,
            action='password_change'
        )
        self.assertTrue(audit_logs.exists())
        
        log = audit_logs.first()
        self.assertEqual(log.details['method'], 'user_initiated')
        self.assertTrue(log.success)
    
    def test_change_password_post_wrong_old_password(self):
        """Test de cambio de contraseña con contraseña actual incorrecta."""
        self.client.login(email='test@example.com', password='testpass123')
        
        response = self.client.post(reverse('agents:change_password'), {
            'old_password': 'wrongpassword',
            'new_password1': 'newpassword123',
            'new_password2': 'newpassword123'
        })
        
        # Debe mostrar el formulario con errores
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'form')
        self.assertTrue(response.context['form'].errors)
        
        # La contraseña no debe haber cambiado
        self.agent.refresh_from_db()
        self.assertTrue(self.agent.check_password('testpass123'))
    
    @patch('agents.services.email_service.EmailService.send_password_reset_email')
    def test_password_reset_email_integration(self, mock_send_email):
        """Test de integración con servicio de email."""
        mock_send_email.return_value = True
        
        response = self.client.post(reverse('agents:password_reset_request'), {
            'email': 'test@example.com'
        })
        
        # Verificar que se llamó al servicio de email
        mock_send_email.assert_called_once()
        
        # Verificar argumentos de la llamada
        call_args = mock_send_email.call_args
        self.assertEqual(call_args[0][0], self.agent)  # agent
        self.assertIsNotNone(call_args[0][1])  # token
        self.assertIsNotNone(call_args[0][2])  # request
    
    @patch('agents.services.email_service.EmailService.send_password_changed_notification')
    def test_password_change_notification_integration(self, mock_send_notification):
        """Test de integración con notificación de cambio de contraseña."""
        mock_send_notification.return_value = True
        
        self.client.login(email='test@example.com', password='testpass123')
        
        response = self.client.post(reverse('agents:change_password'), {
            'old_password': 'testpass123',
            'new_password1': 'newpassword123',
            'new_password2': 'newpassword123'
        })
        
        # Verificar que se llamó al servicio de notificación
        mock_send_notification.assert_called_once()
        
        # Verificar argumentos de la llamada
        call_args = mock_send_notification.call_args
        self.assertEqual(call_args[0][0], self.agent)  # agent
        self.assertIsNotNone(call_args[0][1])  # ip_address
    
    def test_password_reset_flow_complete(self):
        """Test del flujo completo de recuperación de contraseña."""
        # 1. Solicitar reset
        response = self.client.post(reverse('agents:password_reset_request'), {
            'email': 'test@example.com'
        })
        self.assertEqual(response.status_code, 302)
        
        # 2. Verificar token generado
        self.profile.refresh_from_db()
        token = self.profile.password_reset_token
        self.assertIsNotNone(token)
        
        # 3. Acceder a página de confirmación
        response = self.client.get(
            reverse('agents:password_reset_confirm', kwargs={'token': token})
        )
        self.assertEqual(response.status_code, 200)
        
        # 4. Cambiar contraseña
        response = self.client.post(
            reverse('agents:password_reset_confirm', kwargs={'token': token}),
            {
                'new_password1': 'newpassword123',
                'new_password2': 'newpassword123'
            }
        )
        self.assertEqual(response.status_code, 302)
        
        # 5. Verificar que la contraseña cambió
        self.agent.refresh_from_db()
        self.assertTrue(self.agent.check_password('newpassword123'))
        
        # 6. Verificar que el token se limpió
        self.profile.refresh_from_db()
        self.assertIsNone(self.profile.password_reset_token)
        
        # 7. Verificar que se puede hacer login con nueva contraseña
        login_success = self.client.login(email='test@example.com', password='newpassword123')
        self.assertTrue(login_success)
    
    def test_password_reset_security_measures(self):
        """Test de medidas de seguridad en reset de contraseña."""
        # Generar token y cambiar contraseña
        token = self.auth_service.generate_password_reset_token(self.agent)
        
        # Simular sesiones activas
        from agents.models import UserSession
        session1 = UserSession.objects.create(
            agent=self.agent,
            session_key='session1',
            ip_address='192.168.1.100',
            user_agent='Browser 1',
            expires_at=timezone.now() + timezone.timedelta(hours=8)
        )
        session2 = UserSession.objects.create(
            agent=self.agent,
            session_key='session2',
            ip_address='192.168.1.101',
            user_agent='Browser 2',
            expires_at=timezone.now() + timezone.timedelta(hours=8)
        )
        
        # Cambiar contraseña
        response = self.client.post(
            reverse('agents:password_reset_confirm', kwargs={'token': token}),
            {
                'new_password1': 'newpassword123',
                'new_password2': 'newpassword123'
            }
        )
        
        # Verificar que todas las sesiones se terminaron
        session1.refresh_from_db()
        session2.refresh_from_db()
        self.assertFalse(session1.is_active)
        self.assertFalse(session2.is_active)
        
        # Verificar configuraciones de seguridad actualizadas
        self.security_settings.refresh_from_db()
        self.assertFalse(self.security_settings.require_password_change)
    
    def test_password_reset_token_single_use(self):
        """Test de que el token de reset solo se puede usar una vez."""
        # Generar token
        token = self.auth_service.generate_password_reset_token(self.agent)
        
        # Usar token primera vez
        response = self.client.post(
            reverse('agents:password_reset_confirm', kwargs={'token': token}),
            {
                'new_password1': 'newpassword123',
                'new_password2': 'newpassword123'
            }
        )
        self.assertEqual(response.status_code, 302)
        
        # Intentar usar token segunda vez
        response = self.client.get(
            reverse('agents:password_reset_confirm', kwargs={'token': token})
        )
        
        # Debe redirigir porque el token ya no existe
        self.assertEqual(response.status_code, 302)
        self.assertIn('password-reset', response.url)
    
    def test_password_reset_audit_logging(self):
        """Test de que todas las acciones se registren en auditoría."""
        # Solicitar reset
        self.client.post(reverse('agents:password_reset_request'), {
            'email': 'test@example.com'
        })
        
        # Verificar log de solicitud
        request_logs = AuditLog.objects.filter(
            agent=self.agent,
            action='password_reset_request'
        )
        self.assertTrue(request_logs.exists())
        
        # Cambiar contraseña
        token = self.profile.password_reset_token
        self.client.post(
            reverse('agents:password_reset_confirm', kwargs={'token': token}),
            {
                'new_password1': 'newpassword123',
                'new_password2': 'newpassword123'
            }
        )
        
        # Verificar log de cambio
        change_logs = AuditLog.objects.filter(
            agent=self.agent,
            action='password_change'
        )
        self.assertTrue(change_logs.exists())
        
        change_log = change_logs.first()
        self.assertEqual(change_log.details['method'], 'password_reset')
        self.assertTrue(change_log.success)
    
    def tearDown(self):
        """Limpieza después de cada test."""
        AuditLog.objects.all().delete()
        mail.outbox = []