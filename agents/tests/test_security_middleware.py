"""
Tests para SecurityMiddleware.
"""

from django.test import TestCase, RequestFactory
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.auth.middleware import AuthenticationMiddleware
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch, MagicMock

from agents.models import Agent, SecuritySettings, UserSession, AuditLog
from agents.middleware.security_middleware import SecurityMiddleware


class SecurityMiddlewareTest(TestCase):
    """Tests para SecurityMiddleware"""
    
    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = SecurityMiddleware()
        
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
            allowed_ip_addresses=['192.168.1.100', '10.0.0.*'],
            suspicious_activity_alerts=True
        )
    
    def _create_request(self, path='/', method='GET', ip='192.168.1.1', user_agent='Test Browser'):
        """Helper para crear requests de prueba"""
        if method == 'GET':
            request = self.factory.get(path)
        elif method == 'POST':
            request = self.factory.post(path)
        else:
            request = self.factory.generic(method, path)
        
        request.META['REMOTE_ADDR'] = ip
        request.META['HTTP_USER_AGENT'] = user_agent
        request.user = self.agent
        
        # Simular sesión
        request.session = MagicMock()
        request.session.session_key = 'test_session_key'
        
        return request
    
    def test_process_request_exempt_url(self):
        """Test que URLs exentas no son procesadas"""
        request = self._create_request('/agents/login/')
        
        response = self.middleware.process_request(request)
        
        self.assertIsNone(response)
        self.assertFalse(hasattr(request, 'security_info'))
    
    def test_process_request_anonymous_user(self):
        """Test que usuarios anónimos no son procesados"""
        request = self._create_request('/dashboard/')
        request.user = AnonymousUser()
        
        response = self.middleware.process_request(request)
        
        self.assertIsNone(response)
    
    def test_process_request_normal_access(self):
        """Test acceso normal sin problemas de seguridad"""
        request = self._create_request('/dashboard/', ip='192.168.1.100')  # IP permitida
        
        response = self.middleware.process_request(request)
        
        self.assertIsNone(response)
        self.assertTrue(hasattr(request, 'security_info'))
        self.assertEqual(request.security_info['ip_address'], '192.168.1.100')
    
    def test_process_request_locked_account(self):
        """Test acceso con cuenta bloqueada"""
        # Bloquear cuenta
        self.security_settings.locked_until = timezone.now() + timedelta(minutes=15)
        self.security_settings.save()
        
        request = self._create_request('/dashboard/')
        
        response = self.middleware.process_request(request)
        
        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, 302)  # Redirect
        
        # Verificar que se registró en auditoría
        audit_log = AuditLog.objects.filter(
            action='locked_account_access',
            success=False
        ).first()
        self.assertIsNotNone(audit_log)
    
    def test_process_request_locked_account_json(self):
        """Test acceso con cuenta bloqueada para request JSON"""
        # Bloquear cuenta
        self.security_settings.locked_until = timezone.now() + timedelta(minutes=15)
        self.security_settings.save()
        
        request = self._create_request('/dashboard/')
        request.META['HTTP_ACCEPT'] = 'application/json'
        
        response = self.middleware.process_request(request)
        
        self.assertIsInstance(response, JsonResponse)
        self.assertEqual(response.status_code, 403)
    
    def test_process_request_unauthorized_ip(self):
        """Test acceso desde IP no autorizada"""
        request = self._create_request('/dashboard/', ip='203.0.113.1')  # IP no permitida
        
        response = self.middleware.process_request(request)
        
        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, 302)  # Redirect
        
        # Verificar que se registró en auditoría
        audit_log = AuditLog.objects.filter(
            action='unauthorized_ip_access',
            success=False
        ).first()
        self.assertIsNotNone(audit_log)
        self.assertEqual(audit_log.details['unauthorized_ip'], '203.0.113.1')
    
    def test_process_request_unauthorized_ip_json(self):
        """Test acceso desde IP no autorizada para request JSON"""
        request = self._create_request('/dashboard/', ip='203.0.113.1')
        request.META['HTTP_ACCEPT'] = 'application/json'
        
        response = self.middleware.process_request(request)
        
        self.assertIsInstance(response, JsonResponse)
        self.assertEqual(response.status_code, 403)
    
    def test_process_request_wildcard_ip_allowed(self):
        """Test que IPs con wildcard son permitidas"""
        request = self._create_request('/dashboard/', ip='10.0.0.50')  # Coincide con 10.0.0.*
        
        response = self.middleware.process_request(request)
        
        self.assertIsNone(response)  # Debería permitir acceso
    
    @patch('agents.middleware.security_middleware.AuthenticationService')
    def test_process_request_suspicious_activity_critical_url(self, mock_auth_service):
        """Test detección de actividad sospechosa en URL crítica"""
        # Mock del servicio de autenticación
        mock_auth_instance = MagicMock()
        mock_auth_instance.detect_suspicious_activity.return_value = True
        mock_auth_service.return_value = mock_auth_instance
        
        # Recrear middleware para usar el mock
        middleware = SecurityMiddleware()
        
        request = self._create_request('/admin/users/')  # URL crítica
        
        response = middleware.process_request(request)
        
        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, 302)  # Redirect por actividad sospechosa
        
        # Verificar que se registró en auditoría
        audit_log = AuditLog.objects.filter(
            action='suspicious_activity_detected'
        ).first()
        self.assertIsNotNone(audit_log)
    
    @patch('agents.middleware.security_middleware.AuthenticationService')
    def test_process_request_suspicious_activity_normal_url(self, mock_auth_service):
        """Test detección de actividad sospechosa en URL normal"""
        # Mock del servicio de autenticación
        mock_auth_instance = MagicMock()
        mock_auth_instance.detect_suspicious_activity.return_value = True
        mock_auth_service.return_value = mock_auth_instance
        
        # Recrear middleware para usar el mock
        middleware = SecurityMiddleware()
        
        request = self._create_request('/dashboard/')  # URL normal
        
        response = middleware.process_request(request)
        
        # Para URLs normales, solo registra pero no bloquea
        self.assertIsNone(response)
    
    def test_process_response_normal(self):
        """Test procesamiento normal de respuesta"""
        request = self._create_request('/dashboard/')
        request.security_info = {
            'ip_address': '192.168.1.1',
            'user_agent': 'Test Browser',
            'start_time': timezone.now().timestamp(),
            'path': '/dashboard/'
        }
        
        response = HttpResponse('OK')
        
        processed_response = self.middleware.process_response(request, response)
        
        self.assertEqual(processed_response, response)
    
    def test_process_response_slow_request(self):
        """Test procesamiento de request lento"""
        request = self._create_request('/dashboard/')
        request.security_info = {
            'ip_address': '192.168.1.1',
            'user_agent': 'Test Browser',
            'start_time': timezone.now().timestamp() - 15,  # 15 segundos atrás
            'path': '/dashboard/'
        }
        
        response = HttpResponse('OK')
        
        self.middleware.process_response(request, response)
        
        # Verificar que se registró como request lento
        audit_log = AuditLog.objects.filter(
            action='slow_request'
        ).first()
        self.assertIsNotNone(audit_log)
        self.assertGreater(audit_log.details['duration'], 10)
    
    def test_process_response_critical_access(self):
        """Test procesamiento de acceso a URL crítica"""
        request = self._create_request('/admin/users/')
        request.security_info = {
            'ip_address': '192.168.1.1',
            'user_agent': 'Test Browser',
            'start_time': timezone.now().timestamp(),
            'path': '/admin/users/'
        }
        
        response = HttpResponse('OK')
        
        self.middleware.process_response(request, response)
        
        # Verificar que se registró el acceso crítico
        audit_log = AuditLog.objects.filter(
            action='critical_access'
        ).first()
        self.assertIsNotNone(audit_log)
        self.assertEqual(audit_log.details['path'], '/admin/users/')
    
    def test_process_exception(self):
        """Test procesamiento de excepciones"""
        request = self._create_request('/dashboard/')
        request.security_info = {
            'ip_address': '192.168.1.1',
            'user_agent': 'Test Browser',
            'path': '/dashboard/'
        }
        
        exception = ValueError("Test exception")
        
        result = self.middleware.process_exception(request, exception)
        
        self.assertIsNone(result)  # Debe permitir que Django maneje la excepción
        
        # Verificar que se registró la excepción
        audit_log = AuditLog.objects.filter(
            action='security_exception',
            success=False
        ).first()
        self.assertIsNotNone(audit_log)
        self.assertEqual(audit_log.details['exception_type'], 'ValueError')
    
    def test_get_client_ip_direct(self):
        """Test obtención de IP directa"""
        request = self._create_request('/', ip='192.168.1.100')
        
        ip = self.middleware._get_client_ip(request)
        
        self.assertEqual(ip, '192.168.1.100')
    
    def test_get_client_ip_forwarded(self):
        """Test obtención de IP con X-Forwarded-For"""
        request = self._create_request('/')
        request.META['HTTP_X_FORWARDED_FOR'] = '203.0.113.1, 192.168.1.1'
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        
        ip = self.middleware._get_client_ip(request)
        
        self.assertEqual(ip, '203.0.113.1')
    
    def test_is_exempt_url(self):
        """Test verificación de URLs exentas"""
        # URLs exentas
        self.assertTrue(self.middleware._is_exempt_url('/agents/login/'))
        self.assertTrue(self.middleware._is_exempt_url('/static/css/style.css'))
        self.assertTrue(self.middleware._is_exempt_url('/public/about/'))
        
        # URLs no exentas
        self.assertFalse(self.middleware._is_exempt_url('/dashboard/'))
        self.assertFalse(self.middleware._is_exempt_url('/agents/profile/'))
    
    def test_is_critical_url(self):
        """Test verificación de URLs críticas"""
        # URLs críticas
        self.assertTrue(self.middleware._is_critical_url('/admin/users/'))
        self.assertTrue(self.middleware._is_critical_url('/agents/create/'))
        self.assertTrue(self.middleware._is_critical_url('/settings/security/'))
        
        # URLs no críticas
        self.assertFalse(self.middleware._is_critical_url('/dashboard/'))
        self.assertFalse(self.middleware._is_critical_url('/agents/profile/'))
    
    def test_validate_ip_address_exact_match(self):
        """Test validación de IP con coincidencia exacta"""
        allowed_ips = ['192.168.1.100', '10.0.0.1']
        
        self.assertTrue(self.middleware._validate_ip_address('192.168.1.100', allowed_ips))
        self.assertTrue(self.middleware._validate_ip_address('10.0.0.1', allowed_ips))
        self.assertFalse(self.middleware._validate_ip_address('203.0.113.1', allowed_ips))
    
    def test_validate_ip_address_wildcard(self):
        """Test validación de IP con wildcards"""
        allowed_ips = ['192.168.1.*', '10.0.*']
        
        self.assertTrue(self.middleware._validate_ip_address('192.168.1.100', allowed_ips))
        self.assertTrue(self.middleware._validate_ip_address('192.168.1.1', allowed_ips))
        self.assertTrue(self.middleware._validate_ip_address('10.0.0.1', allowed_ips))
        self.assertTrue(self.middleware._validate_ip_address('10.0.5.10', allowed_ips))
        self.assertFalse(self.middleware._validate_ip_address('192.168.2.1', allowed_ips))
        self.assertFalse(self.middleware._validate_ip_address('203.0.113.1', allowed_ips))
    
    def test_update_user_session_extend(self):
        """Test actualización y extensión de sesión"""
        # Crear sesión que está cerca de expirar
        user_session = UserSession.objects.create(
            agent=self.agent,
            session_key='test_session_key',
            ip_address='192.168.1.1',
            user_agent='Test Browser',
            expires_at=timezone.now() + timedelta(minutes=20)  # Expira en 20 minutos
        )
        
        request = self._create_request('/dashboard/')
        request.session.session_key = 'test_session_key'
        
        self.middleware._update_user_session(request)
        
        # Verificar que la sesión se extendió
        user_session.refresh_from_db()
        self.assertGreater(
            user_session.expires_at,
            timezone.now() + timedelta(minutes=400)  # Debería haberse extendido
        )
    
    def test_update_user_session_no_extension_needed(self):
        """Test actualización de sesión que no necesita extensión"""
        # Crear sesión que no está cerca de expirar
        original_expiry = timezone.now() + timedelta(hours=4)
        user_session = UserSession.objects.create(
            agent=self.agent,
            session_key='test_session_key',
            ip_address='192.168.1.1',
            user_agent='Test Browser',
            expires_at=original_expiry
        )
        
        request = self._create_request('/dashboard/')
        request.session.session_key = 'test_session_key'
        
        self.middleware._update_user_session(request)
        
        # Verificar que la sesión no se extendió
        user_session.refresh_from_db()
        self.assertAlmostEqual(
            user_session.expires_at.timestamp(),
            original_expiry.timestamp(),
            delta=60  # 1 minuto de tolerancia
        )
    
    def test_security_settings_created_if_not_exist(self):
        """Test que se crean configuraciones de seguridad si no existen"""
        # Crear usuario sin configuraciones de seguridad
        agent_without_settings = Agent.objects.create_user(
            username='no_settings_user',
            email='nosettings@example.com',
            password='TestPassword123!',
            first_name='No',
            last_name='Settings',
            license_number='LIC999'
        )
        
        request = self._create_request('/dashboard/')
        request.user = agent_without_settings
        
        response = self.middleware.process_request(request)
        
        # Verificar que se crearon las configuraciones
        self.assertTrue(
            SecuritySettings.objects.filter(agent=agent_without_settings).exists()
        )
        
        # El request debería continuar normalmente
        self.assertIsNone(response)
    
    def test_middleware_handles_exceptions_gracefully(self):
        """Test que el middleware maneja excepciones sin fallar"""
        # Crear request que podría causar errores
        request = self._create_request('/dashboard/')
        request.user = None  # Usuario inválido
        
        # No debería lanzar excepción
        response = self.middleware.process_request(request)
        
        # Debería permitir que el request continúe
        self.assertIsNone(response)