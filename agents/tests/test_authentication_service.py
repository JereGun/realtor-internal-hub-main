"""
Tests para AuthenticationService.
"""

from django.test import TestCase, RequestFactory
from django.core.exceptions import ValidationError
from django.utils import timezone
from unittest.mock import patch, MagicMock
from datetime import timedelta

from agents.models import Agent, UserProfile, SecuritySettings, AuditLog
from agents.services.authentication_service import AuthenticationService


class AuthenticationServiceTest(TestCase):
    """Tests para AuthenticationService"""
    
    def setUp(self):
        self.service = AuthenticationService()
        self.factory = RequestFactory()
        
        # Crear usuario de prueba
        self.agent = Agent.objects.create_user(
            username='test_user',
            email='test@example.com',
            password='TestPassword123!',
            first_name='Test',
            last_name='User',
            license_number='LIC123'
        )
        
        # Crear perfil y configuraciones de seguridad
        self.profile = UserProfile.objects.create(agent=self.agent)
        self.security_settings = SecuritySettings.objects.create(agent=self.agent)
    
    def test_authenticate_user_success(self):
        """Test autenticación exitosa"""
        request = self.factory.post('/login/', {
            'email': 'test@example.com',
            'password': 'TestPassword123!'
        })
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        request.META['HTTP_USER_AGENT'] = 'Test Browser'
        
        agent, result = self.service.authenticate_user(
            'test@example.com', 
            'TestPassword123!', 
            request
        )
        
        self.assertEqual(agent, self.agent)
        self.assertTrue(result['success'])
        self.assertEqual(result['message'], 'Autenticación exitosa')
        
        # Verificar que se registró el login exitoso
        audit_log = AuditLog.objects.filter(
            agent=self.agent,
            action='login',
            success=True
        ).first()
        self.assertIsNotNone(audit_log)
    
    def test_authenticate_user_invalid_email(self):
        """Test autenticación con email inválido"""
        request = self.factory.post('/login/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        request.META['HTTP_USER_AGENT'] = 'Test Browser'
        
        with self.assertRaises(ValidationError) as context:
            self.service.authenticate_user(
                'nonexistent@example.com',
                'TestPassword123!',
                request
            )
        
        self.assertIn("Credenciales inválidas", str(context.exception))
    
    def test_authenticate_user_invalid_password(self):
        """Test autenticación con contraseña inválida"""
        request = self.factory.post('/login/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        request.META['HTTP_USER_AGENT'] = 'Test Browser'
        
        with self.assertRaises(ValidationError) as context:
            self.service.authenticate_user(
                'test@example.com',
                'WrongPassword',
                request
            )
        
        self.assertIn("Credenciales inválidas", str(context.exception))
        
        # Verificar que se incrementaron los intentos fallidos
        self.security_settings.refresh_from_db()
        self.assertEqual(self.security_settings.login_attempts, 1)
    
    def test_authenticate_user_account_locked(self):
        """Test autenticación con cuenta bloqueada"""
        # Bloquear cuenta
        self.security_settings.locked_until = timezone.now() + timedelta(minutes=15)
        self.security_settings.save()
        
        request = self.factory.post('/login/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        request.META['HTTP_USER_AGENT'] = 'Test Browser'
        
        with self.assertRaises(ValidationError) as context:
            self.service.authenticate_user(
                'test@example.com',
                'TestPassword123!',
                request
            )
        
        self.assertIn("Cuenta bloqueada temporalmente", str(context.exception))
    
    def test_authenticate_user_inactive_account(self):
        """Test autenticación con cuenta inactiva"""
        self.agent.is_active = False
        self.agent.save()
        
        request = self.factory.post('/login/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        request.META['HTTP_USER_AGENT'] = 'Test Browser'
        
        with self.assertRaises(ValidationError) as context:
            self.service.authenticate_user(
                'test@example.com',
                'TestPassword123!',
                request
            )
        
        self.assertIn("Cuenta inactiva", str(context.exception))
    
    def test_authenticate_user_requires_2fa(self):
        """Test autenticación que requiere 2FA"""
        # Habilitar 2FA
        self.profile.two_factor_enabled = True
        self.profile.two_factor_secret = 'TESTSECRET123456'
        self.profile.save()
        
        request = self.factory.post('/login/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        request.META['HTTP_USER_AGENT'] = 'Test Browser'
        
        agent, result = self.service.authenticate_user(
            'test@example.com',
            'TestPassword123!',
            request
        )
        
        self.assertEqual(agent, self.agent)
        self.assertTrue(result['requires_2fa'])
        self.assertIn('Código de autenticación de dos factores requerido', result['message'])
    
    @patch('agents.services.authentication_service.pyotp.TOTP')
    def test_authenticate_user_with_valid_2fa(self, mock_totp):
        """Test autenticación con 2FA válido"""
        # Configurar 2FA
        self.profile.two_factor_enabled = True
        self.profile.two_factor_secret = 'TESTSECRET123456'
        self.profile.save()
        
        # Mock del TOTP
        mock_totp_instance = MagicMock()
        mock_totp_instance.verify.return_value = True
        mock_totp.return_value = mock_totp_instance
        
        request = self.factory.post('/login/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        request.META['HTTP_USER_AGENT'] = 'Test Browser'
        
        agent, result = self.service.authenticate_user(
            'test@example.com',
            'TestPassword123!',
            request,
            two_factor_code='123456'
        )
        
        self.assertEqual(agent, self.agent)
        self.assertTrue(result['success'])
    
    @patch('agents.services.authentication_service.pyotp.TOTP')
    def test_authenticate_user_with_invalid_2fa(self, mock_totp):
        """Test autenticación con 2FA inválido"""
        # Configurar 2FA
        self.profile.two_factor_enabled = True
        self.profile.two_factor_secret = 'TESTSECRET123456'
        self.profile.save()
        
        # Mock del TOTP
        mock_totp_instance = MagicMock()
        mock_totp_instance.verify.return_value = False
        mock_totp.return_value = mock_totp_instance
        
        request = self.factory.post('/login/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        request.META['HTTP_USER_AGENT'] = 'Test Browser'
        
        with self.assertRaises(ValidationError) as context:
            self.service.authenticate_user(
                'test@example.com',
                'TestPassword123!',
                request,
                two_factor_code='wrong_code'
            )
        
        self.assertIn("Código de autenticación inválido", str(context.exception))
    
    def test_generate_password_reset_token(self):
        """Test generación de token de recuperación"""
        token = self.service.generate_password_reset_token(self.agent)
        
        self.assertIsNotNone(token)
        self.assertTrue(len(token) > 20)
        
        # Verificar que se guardó en el perfil
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.password_reset_token, token)
        self.assertIsNotNone(self.profile.password_reset_expires)
        
        # Verificar que se registró en auditoría
        audit_log = AuditLog.objects.filter(
            agent=self.agent,
            action='password_reset_requested'
        ).first()
        self.assertIsNotNone(audit_log)
    
    @patch('agents.services.authentication_service.pyotp.random_base32')
    @patch('agents.services.authentication_service.qrcode.QRCode')
    def test_setup_two_factor_auth(self, mock_qr, mock_random):
        """Test configuración de 2FA"""
        # Mock de la generación de secreto
        mock_random.return_value = 'TESTSECRET123456'
        
        # Mock del QR code
        mock_qr_instance = MagicMock()
        mock_img = MagicMock()
        mock_qr_instance.make_image.return_value = mock_img
        mock_qr.return_value = mock_qr_instance
        
        result = self.service.setup_two_factor_auth(self.agent)
        
        # Verificar resultado
        self.assertEqual(result['secret'], 'TESTSECRET123456')
        self.assertIn('qr_code', result)
        self.assertIn('backup_codes', result)
        self.assertIn('provisioning_uri', result)
        
        # Verificar que se guardó el secreto
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.two_factor_secret, 'TESTSECRET123456')
        self.assertEqual(len(self.profile.backup_codes), 10)
    
    @patch('agents.services.authentication_service.pyotp.TOTP')
    def test_verify_two_factor_code_valid(self, mock_totp):
        """Test verificación de código 2FA válido"""
        # Configurar 2FA
        self.profile.two_factor_enabled = True
        self.profile.two_factor_secret = 'TESTSECRET123456'
        self.profile.save()
        
        # Mock del TOTP
        mock_totp_instance = MagicMock()
        mock_totp_instance.verify.return_value = True
        mock_totp.return_value = mock_totp_instance
        
        result = self.service.verify_two_factor_code(self.agent, '123456')
        
        self.assertTrue(result)
    
    @patch('agents.services.authentication_service.pyotp.TOTP')
    def test_verify_two_factor_code_invalid(self, mock_totp):
        """Test verificación de código 2FA inválido"""
        # Configurar 2FA
        self.profile.two_factor_enabled = True
        self.profile.two_factor_secret = 'TESTSECRET123456'
        self.profile.save()
        
        # Mock del TOTP
        mock_totp_instance = MagicMock()
        mock_totp_instance.verify.return_value = False
        mock_totp.return_value = mock_totp_instance
        
        result = self.service.verify_two_factor_code(self.agent, 'wrong_code')
        
        self.assertFalse(result)
    
    def test_verify_two_factor_code_backup_code(self):
        """Test verificación con código de respaldo"""
        # Configurar 2FA con códigos de respaldo
        self.profile.two_factor_enabled = True
        self.profile.two_factor_secret = 'TESTSECRET123456'
        self.profile.backup_codes = ['BACKUP123', 'BACKUP456']
        self.profile.save()
        
        result = self.service.verify_two_factor_code(self.agent, 'BACKUP123')
        
        self.assertTrue(result)
        
        # Verificar que el código se eliminó
        self.profile.refresh_from_db()
        self.assertNotIn('BACKUP123', self.profile.backup_codes)
        self.assertIn('BACKUP456', self.profile.backup_codes)
    
    def test_detect_suspicious_activity_unusual_ip(self):
        """Test detección de actividad sospechosa por IP inusual"""
        from agents.models import UserSession
        
        # Crear sesiones con IPs conocidas
        UserSession.objects.create(
            agent=self.agent,
            session_key='session1',
            ip_address='192.168.1.1',
            user_agent='Browser 1',
            expires_at=timezone.now() + timedelta(hours=1)
        )
        
        # Request desde IP diferente
        request = self.factory.post('/login/')
        request.META['REMOTE_ADDR'] = '10.0.0.1'  # IP diferente
        request.META['HTTP_USER_AGENT'] = 'Browser 1'  # Mismo browser
        
        is_suspicious = self.service.detect_suspicious_activity(self.agent, request)
        
        # Solo una IP diferente no debería ser suficiente para marcar como sospechoso
        # (necesita al menos 2 indicadores)
        self.assertFalse(is_suspicious)
    
    def test_detect_suspicious_activity_multiple_indicators(self):
        """Test detección con múltiples indicadores sospechosos"""
        from agents.models import UserSession
        
        # Crear sesiones con patrones conocidos
        UserSession.objects.create(
            agent=self.agent,
            session_key='session1',
            ip_address='192.168.1.1',
            user_agent='Browser 1',
            expires_at=timezone.now() + timedelta(hours=1),
            created_at=timezone.now() - timedelta(days=1)
        )
        
        # Crear intentos fallidos recientes
        for i in range(3):
            AuditLog.objects.create(
                agent=self.agent,
                action='login',
                resource_type='authentication',
                ip_address='10.0.0.1',
                user_agent='Different Browser',
                success=False,
                created_at=timezone.now() - timedelta(minutes=30)
            )
        
        # Request con IP y browser diferentes
        request = self.factory.post('/login/')
        request.META['REMOTE_ADDR'] = '10.0.0.1'  # IP diferente
        request.META['HTTP_USER_AGENT'] = 'Different Browser'  # Browser diferente
        
        is_suspicious = self.service.detect_suspicious_activity(self.agent, request)
        
        # Múltiples indicadores deberían marcar como sospechoso
        self.assertTrue(is_suspicious)
    
    def test_handle_failed_login(self):
        """Test manejo de login fallido"""
        result = self.service.handle_failed_login(
            'test@example.com',
            '192.168.1.1',
            'invalid_password'
        )
        
        self.assertTrue(result)
        
        # Verificar que se registró en auditoría
        audit_log = AuditLog.objects.filter(
            agent=self.agent,
            action='login',
            success=False
        ).first()
        self.assertIsNotNone(audit_log)
        self.assertEqual(audit_log.details['reason'], 'invalid_password')
    
    def test_handle_failed_login_nonexistent_user(self):
        """Test manejo de login fallido para usuario inexistente"""
        result = self.service.handle_failed_login(
            'nonexistent@example.com',
            '192.168.1.1',
            'user_not_found'
        )
        
        self.assertTrue(result)
        
        # Verificar que se registró en auditoría sin agente
        audit_log = AuditLog.objects.filter(
            agent=None,
            action='login',
            success=False
        ).first()
        self.assertIsNotNone(audit_log)
    
    @patch('agents.services.authentication_service.pyotp.TOTP')
    def test_enable_two_factor_auth(self, mock_totp):
        """Test habilitación de 2FA"""
        # Configurar secreto
        self.profile.two_factor_secret = 'TESTSECRET123456'
        self.profile.save()
        
        # Mock del TOTP
        mock_totp_instance = MagicMock()
        mock_totp_instance.verify.return_value = True
        mock_totp.return_value = mock_totp_instance
        
        result = self.service.enable_two_factor_auth(self.agent, '123456')
        
        self.assertTrue(result)
        
        # Verificar que se habilitó
        self.profile.refresh_from_db()
        self.assertTrue(self.profile.two_factor_enabled)
        
        # Verificar auditoría
        audit_log = AuditLog.objects.filter(
            agent=self.agent,
            action='2fa_enabled'
        ).first()
        self.assertIsNotNone(audit_log)
    
    def test_disable_two_factor_auth(self):
        """Test deshabilitación de 2FA"""
        # Configurar 2FA habilitado
        self.profile.two_factor_enabled = True
        self.profile.two_factor_secret = 'TESTSECRET123456'
        self.profile.backup_codes = ['CODE1', 'CODE2']
        self.profile.save()
        
        result = self.service.disable_two_factor_auth(self.agent, 'TestPassword123!')
        
        self.assertTrue(result)
        
        # Verificar que se deshabilitó
        self.profile.refresh_from_db()
        self.assertFalse(self.profile.two_factor_enabled)
        self.assertIsNone(self.profile.two_factor_secret)
        self.assertEqual(self.profile.backup_codes, [])
        
        # Verificar auditoría
        audit_log = AuditLog.objects.filter(
            agent=self.agent,
            action='2fa_disabled'
        ).first()
        self.assertIsNotNone(audit_log)
    
    def test_disable_two_factor_auth_wrong_password(self):
        """Test deshabilitación de 2FA con contraseña incorrecta"""
        # Configurar 2FA habilitado
        self.profile.two_factor_enabled = True
        self.profile.two_factor_secret = 'TESTSECRET123456'
        self.profile.save()
        
        result = self.service.disable_two_factor_auth(self.agent, 'WrongPassword')
        
        self.assertFalse(result)
        
        # Verificar que no se deshabilitó
        self.profile.refresh_from_db()
        self.assertTrue(self.profile.two_factor_enabled)