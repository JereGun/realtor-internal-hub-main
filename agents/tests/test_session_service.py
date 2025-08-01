"""
Tests para SessionService.
"""

from django.test import TestCase, RequestFactory
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch, MagicMock

from agents.models import Agent, UserSession, AuditLog, SecuritySettings
from agents.services.session_service import SessionService


class SessionServiceTest(TestCase):
    """Tests para SessionService"""
    
    def setUp(self):
        self.service = SessionService()
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
        
        # Crear configuraciones de seguridad
        self.security_settings = SecuritySettings.objects.create(
            agent=self.agent,
            session_timeout_minutes=240  # 4 horas
        )
    
    def test_create_session_success(self):
        """Test creación exitosa de sesión"""
        request = self.factory.post('/login/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        request.META['HTTP_USER_AGENT'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        
        session = self.service.create_session(self.agent, request)
        
        # Verificar que la sesión se creó correctamente
        self.assertEqual(session.agent, self.agent)
        self.assertEqual(session.ip_address, '192.168.1.1')
        self.assertTrue(session.is_active)
        self.assertIsNotNone(session.session_key)
        self.assertTrue(len(session.session_key) > 20)
        
        # Verificar que se usó el timeout de configuración
        expected_expiry = timezone.now() + timedelta(minutes=240)
        self.assertAlmostEqual(
            session.expires_at.timestamp(),
            expected_expiry.timestamp(),
            delta=60  # 1 minuto de tolerancia
        )
        
        # Verificar información del dispositivo
        self.assertIn('device_type', session.device_info)
        self.assertIn('browser', session.device_info)
        self.assertIn('os', session.device_info)
        
        # Verificar que se registró en auditoría
        audit_log = AuditLog.objects.filter(
            agent=self.agent,
            action='session_created',
            session_key=session.session_key
        ).first()
        self.assertIsNotNone(audit_log)
    
    def test_create_session_custom_timeout(self):
        """Test creación de sesión con timeout personalizado"""
        request = self.factory.post('/login/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        request.META['HTTP_USER_AGENT'] = 'Test Browser'
        
        custom_timeout = 120  # 2 horas
        session = self.service.create_session(self.agent, request, custom_timeout)
        
        # Verificar que se usó el timeout personalizado
        expected_expiry = timezone.now() + timedelta(minutes=custom_timeout)
        self.assertAlmostEqual(
            session.expires_at.timestamp(),
            expected_expiry.timestamp(),
            delta=60
        )
    
    def test_create_session_default_timeout(self):
        """Test creación de sesión con timeout por defecto cuando no hay configuración"""
        # Eliminar configuraciones de seguridad
        self.security_settings.delete()
        
        request = self.factory.post('/login/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        request.META['HTTP_USER_AGENT'] = 'Test Browser'
        
        session = self.service.create_session(self.agent, request)
        
        # Verificar que se usó el timeout por defecto (480 minutos = 8 horas)
        expected_expiry = timezone.now() + timedelta(minutes=480)
        self.assertAlmostEqual(
            session.expires_at.timestamp(),
            expected_expiry.timestamp(),
            delta=60
        )
    
    def test_get_active_sessions(self):
        """Test obtención de sesiones activas"""
        # Crear sesiones de prueba
        active_session = UserSession.objects.create(
            agent=self.agent,
            session_key='active_session',
            ip_address='192.168.1.1',
            user_agent='Browser 1',
            expires_at=timezone.now() + timedelta(hours=1)
        )
        
        # Sesión expirada
        UserSession.objects.create(
            agent=self.agent,
            session_key='expired_session',
            ip_address='192.168.1.2',
            user_agent='Browser 2',
            expires_at=timezone.now() - timedelta(hours=1)
        )
        
        # Sesión inactiva
        UserSession.objects.create(
            agent=self.agent,
            session_key='inactive_session',
            ip_address='192.168.1.3',
            user_agent='Browser 3',
            expires_at=timezone.now() + timedelta(hours=1),
            is_active=False
        )
        
        active_sessions = self.service.get_active_sessions(self.agent)
        
        # Solo debería devolver la sesión activa
        self.assertEqual(active_sessions.count(), 1)
        self.assertEqual(active_sessions.first(), active_session)
    
    def test_terminate_session_success(self):
        """Test terminación exitosa de sesión"""
        session = UserSession.objects.create(
            agent=self.agent,
            session_key='test_session',
            ip_address='192.168.1.1',
            user_agent='Test Browser',
            expires_at=timezone.now() + timedelta(hours=1)
        )
        
        result = self.service.terminate_session('test_session', 'user_logout')
        
        self.assertTrue(result)
        
        # Verificar que la sesión se terminó
        session.refresh_from_db()
        self.assertFalse(session.is_active)
        
        # Verificar que se registró en auditoría
        audit_log = AuditLog.objects.filter(
            agent=self.agent,
            action='session_terminated',
            session_key='test_session'
        ).first()
        self.assertIsNotNone(audit_log)
        self.assertEqual(audit_log.details['reason'], 'user_logout')
    
    def test_terminate_session_not_found(self):
        """Test terminación de sesión inexistente"""
        result = self.service.terminate_session('nonexistent_session')
        
        self.assertFalse(result)
    
    def test_terminate_all_sessions(self):
        """Test terminación de todas las sesiones"""
        # Crear múltiples sesiones
        session1 = UserSession.objects.create(
            agent=self.agent,
            session_key='session1',
            ip_address='192.168.1.1',
            user_agent='Browser 1',
            expires_at=timezone.now() + timedelta(hours=1)
        )
        
        session2 = UserSession.objects.create(
            agent=self.agent,
            session_key='session2',
            ip_address='192.168.1.2',
            user_agent='Browser 2',
            expires_at=timezone.now() + timedelta(hours=1)
        )
        
        current_session = UserSession.objects.create(
            agent=self.agent,
            session_key='current_session',
            ip_address='192.168.1.3',
            user_agent='Browser 3',
            expires_at=timezone.now() + timedelta(hours=1)
        )
        
        # Terminar todas excepto la sesión actual
        terminated_count = self.service.terminate_all_sessions(
            self.agent, 
            except_current='current_session'
        )
        
        self.assertEqual(terminated_count, 2)
        
        # Verificar que las sesiones se terminaron
        session1.refresh_from_db()
        session2.refresh_from_db()
        current_session.refresh_from_db()
        
        self.assertFalse(session1.is_active)
        self.assertFalse(session2.is_active)
        self.assertTrue(current_session.is_active)  # Esta debería seguir activa
    
    def test_terminate_all_sessions_no_exception(self):
        """Test terminación de todas las sesiones sin excepción"""
        # Crear sesiones
        UserSession.objects.create(
            agent=self.agent,
            session_key='session1',
            ip_address='192.168.1.1',
            user_agent='Browser 1',
            expires_at=timezone.now() + timedelta(hours=1)
        )
        
        UserSession.objects.create(
            agent=self.agent,
            session_key='session2',
            ip_address='192.168.1.2',
            user_agent='Browser 2',
            expires_at=timezone.now() + timedelta(hours=1)
        )
        
        # Terminar todas las sesiones
        terminated_count = self.service.terminate_all_sessions(self.agent)
        
        self.assertEqual(terminated_count, 2)
        
        # Verificar que no hay sesiones activas
        active_sessions = UserSession.objects.filter(agent=self.agent, is_active=True)
        self.assertEqual(active_sessions.count(), 0)
    
    def test_cleanup_expired_sessions(self):
        """Test limpieza de sesiones expiradas"""
        # Crear sesiones expiradas
        expired_session1 = UserSession.objects.create(
            agent=self.agent,
            session_key='expired1',
            ip_address='192.168.1.1',
            user_agent='Browser 1',
            expires_at=timezone.now() - timedelta(hours=1)
        )
        
        expired_session2 = UserSession.objects.create(
            agent=self.agent,
            session_key='expired2',
            ip_address='192.168.1.2',
            user_agent='Browser 2',
            expires_at=timezone.now() - timedelta(hours=2)
        )
        
        # Crear sesión válida
        valid_session = UserSession.objects.create(
            agent=self.agent,
            session_key='valid',
            ip_address='192.168.1.3',
            user_agent='Browser 3',
            expires_at=timezone.now() + timedelta(hours=1)
        )
        
        cleaned_count = self.service.cleanup_expired_sessions()
        
        self.assertEqual(cleaned_count, 2)
        
        # Verificar que las sesiones expiradas se terminaron
        expired_session1.refresh_from_db()
        expired_session2.refresh_from_db()
        valid_session.refresh_from_db()
        
        self.assertFalse(expired_session1.is_active)
        self.assertFalse(expired_session2.is_active)
        self.assertTrue(valid_session.is_active)
    
    def test_extend_session(self):
        """Test extensión de sesión"""
        session = UserSession.objects.create(
            agent=self.agent,
            session_key='test_session',
            ip_address='192.168.1.1',
            user_agent='Test Browser',
            expires_at=timezone.now() + timedelta(hours=1)
        )
        
        original_expiry = session.expires_at
        
        result = self.service.extend_session('test_session', minutes=120)
        
        self.assertTrue(result)
        
        # Verificar que se extendió la sesión
        session.refresh_from_db()
        self.assertGreater(session.expires_at, original_expiry)
        
        # Verificar que se registró en auditoría
        audit_log = AuditLog.objects.filter(
            agent=self.agent,
            action='session_extended',
            session_key='test_session'
        ).first()
        self.assertIsNotNone(audit_log)
        self.assertEqual(audit_log.details['extended_minutes'], 120)
    
    def test_extend_session_not_found(self):
        """Test extensión de sesión inexistente"""
        result = self.service.extend_session('nonexistent_session')
        
        self.assertFalse(result)
    
    def test_get_session_info(self):
        """Test obtención de información de sesión"""
        session = UserSession.objects.create(
            agent=self.agent,
            session_key='test_session',
            ip_address='192.168.1.1',
            user_agent='Test Browser',
            device_info={'device_type': 'desktop', 'browser': 'Chrome'},
            location={'country': 'Argentina', 'city': 'Buenos Aires'},
            expires_at=timezone.now() + timedelta(hours=1)
        )
        
        session_info = self.service.get_session_info('test_session')
        
        self.assertIsNotNone(session_info)
        self.assertEqual(session_info['session_key'], 'test_session')
        self.assertEqual(session_info['agent']['email'], 'test@example.com')
        self.assertEqual(session_info['ip_address'], '192.168.1.1')
        self.assertTrue(session_info['is_active'])
        self.assertFalse(session_info['is_expired'])
        self.assertIsNotNone(session_info['time_remaining'])
    
    def test_get_session_info_not_found(self):
        """Test obtención de información de sesión inexistente"""
        session_info = self.service.get_session_info('nonexistent_session')
        
        self.assertIsNone(session_info)
    
    def test_get_user_session_statistics(self):
        """Test obtención de estadísticas de sesiones"""
        # Crear sesiones de prueba
        UserSession.objects.create(
            agent=self.agent,
            session_key='session1',
            ip_address='192.168.1.1',
            user_agent='Browser 1',
            device_info={'device_type': 'desktop'},
            expires_at=timezone.now() + timedelta(hours=1)
        )
        
        UserSession.objects.create(
            agent=self.agent,
            session_key='session2',
            ip_address='192.168.1.2',
            user_agent='Browser 2',
            device_info={'device_type': 'mobile'},
            expires_at=timezone.now() + timedelta(hours=1)
        )
        
        # Sesión inactiva
        UserSession.objects.create(
            agent=self.agent,
            session_key='session3',
            ip_address='192.168.1.3',
            user_agent='Browser 3',
            device_info={'device_type': 'tablet'},
            expires_at=timezone.now() + timedelta(hours=1),
            is_active=False
        )
        
        statistics = self.service.get_user_session_statistics(self.agent)
        
        # Verificar estadísticas
        self.assertEqual(statistics['total_sessions'], 3)
        self.assertEqual(statistics['active_sessions'], 2)
        self.assertEqual(statistics['unique_devices'], 3)  # desktop, mobile, tablet
        self.assertEqual(statistics['unique_ips'], 3)
        self.assertIsNotNone(statistics['latest_session'])
        self.assertIsInstance(statistics['average_session_duration_hours'], float)
    
    def test_extract_device_info_chrome_windows(self):
        """Test extracción de información de dispositivo Chrome en Windows"""
        user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        
        device_info = self.service._extract_device_info(user_agent)
        
        self.assertEqual(device_info['device_type'], 'desktop')
        self.assertEqual(device_info['browser'], 'Chrome')
        self.assertEqual(device_info['os'], 'Windows')
    
    def test_extract_device_info_mobile_android(self):
        """Test extracción de información de dispositivo móvil Android"""
        user_agent = 'Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36'
        
        device_info = self.service._extract_device_info(user_agent)
        
        self.assertEqual(device_info['device_type'], 'mobile')
        self.assertEqual(device_info['browser'], 'Chrome')
        self.assertEqual(device_info['os'], 'Android')
    
    def test_extract_device_info_ipad_safari(self):
        """Test extracción de información de iPad con Safari"""
        user_agent = 'Mozilla/5.0 (iPad; CPU OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1'
        
        device_info = self.service._extract_device_info(user_agent)
        
        self.assertEqual(device_info['device_type'], 'tablet')
        self.assertEqual(device_info['browser'], 'Safari')
        self.assertEqual(device_info['os'], 'iOS')
    
    def test_get_location_info_local_ip(self):
        """Test obtención de información de ubicación para IP local"""
        location_info = self.service._get_location_info('192.168.1.1')
        
        self.assertTrue(location_info['is_local'])
        self.assertEqual(location_info['country'], 'Local')
        self.assertEqual(location_info['city'], 'Local')
    
    def test_get_location_info_localhost(self):
        """Test obtención de información de ubicación para localhost"""
        location_info = self.service._get_location_info('127.0.0.1')
        
        self.assertTrue(location_info['is_local'])
        self.assertEqual(location_info['country'], 'Local')
        self.assertEqual(location_info['city'], 'Local')
    
    def test_get_location_info_public_ip(self):
        """Test obtención de información de ubicación para IP pública"""
        location_info = self.service._get_location_info('8.8.8.8')
        
        self.assertFalse(location_info['is_local'])
        self.assertEqual(location_info['country'], 'unknown')
        self.assertEqual(location_info['city'], 'unknown')
    
    def test_generate_session_key_unique(self):
        """Test generación de clave de sesión única"""
        # Crear sesión existente
        UserSession.objects.create(
            agent=self.agent,
            session_key='existing_key',
            ip_address='192.168.1.1',
            user_agent='Test Browser',
            expires_at=timezone.now() + timedelta(hours=1)
        )
        
        # Generar nueva clave
        new_key = self.service._generate_session_key()
        
        # Verificar que es única
        self.assertNotEqual(new_key, 'existing_key')
        self.assertTrue(len(new_key) > 20)
        self.assertFalse(UserSession.objects.filter(session_key=new_key).exists())
    
    def test_calculate_time_remaining_valid_session(self):
        """Test cálculo de tiempo restante para sesión válida"""
        session = UserSession.objects.create(
            agent=self.agent,
            session_key='test_session',
            ip_address='192.168.1.1',
            user_agent='Test Browser',
            expires_at=timezone.now() + timedelta(hours=2)
        )
        
        time_remaining = self.service._calculate_time_remaining(session)
        
        self.assertIsNotNone(time_remaining)
        self.assertGreater(time_remaining, 110)  # Debería ser cerca de 120 minutos
        self.assertLess(time_remaining, 130)
    
    def test_calculate_time_remaining_expired_session(self):
        """Test cálculo de tiempo restante para sesión expirada"""
        session = UserSession.objects.create(
            agent=self.agent,
            session_key='test_session',
            ip_address='192.168.1.1',
            user_agent='Test Browser',
            expires_at=timezone.now() - timedelta(hours=1)
        )
        
        time_remaining = self.service._calculate_time_remaining(session)
        
        self.assertIsNone(time_remaining)
    
    def test_get_client_ip_direct(self):
        """Test obtención de IP directa"""
        request = self.factory.get('/')
        request.META['REMOTE_ADDR'] = '192.168.1.100'
        
        ip = self.service._get_client_ip(request)
        
        self.assertEqual(ip, '192.168.1.100')
    
    def test_get_client_ip_forwarded(self):
        """Test obtención de IP con X-Forwarded-For"""
        request = self.factory.get('/')
        request.META['HTTP_X_FORWARDED_FOR'] = '203.0.113.1, 192.168.1.1'
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        
        ip = self.service._get_client_ip(request)
        
        self.assertEqual(ip, '203.0.113.1')  # Debería tomar la primera IP