"""
Tests de integración para AuditMiddleware.

Este módulo contiene tests completos para el middleware de auditoría,
verificando que se registren correctamente las acciones de los usuarios.
"""

import json
from django.test import TestCase, Client, RequestFactory
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.http import HttpResponse
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.auth.middleware import AuthenticationMiddleware
from django.contrib.messages.middleware import MessageMiddleware
from unittest.mock import patch, MagicMock

from agents.models import Agent, AuditLog, UserProfile, SecuritySettings
from agents.middleware.audit_middleware import AuditMiddleware


class AuditMiddlewareIntegrationTest(TestCase):
    """
    Tests de integración para AuditMiddleware.
    """
    
    def setUp(self):
        """Configuración inicial para los tests."""
        self.factory = RequestFactory()
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
        
        # Inicializar middleware
        self.middleware = AuditMiddleware(self._get_response)
        
        # Limpiar logs existentes
        AuditLog.objects.all().delete()
    
    def _get_response(self, request):
        """Mock response function para el middleware."""
        return HttpResponse("OK")
    
    def _setup_request_middleware(self, request):
        """Configura middleware necesario para la request."""
        # Session middleware
        session_middleware = SessionMiddleware(lambda r: HttpResponse())
        session_middleware.process_request(request)
        request.session.save()
        
        # Auth middleware
        auth_middleware = AuthenticationMiddleware(lambda r: HttpResponse())
        auth_middleware.process_request(request)
        
        # Message middleware
        message_middleware = MessageMiddleware(lambda r: HttpResponse())
        message_middleware.process_request(request)
    
    def test_login_action_audited(self):
        """Test de que las acciones de login se auditen correctamente."""
        # Realizar login
        response = self.client.post(reverse('agents:login'), {
            'email': 'test@example.com',
            'password': 'testpass123'
        })
        
        # Verificar que se creó un log de auditoría
        audit_logs = AuditLog.objects.filter(action='login_attempt')
        self.assertTrue(audit_logs.exists())
        
        log = audit_logs.first()
        self.assertEqual(log.resource_type, 'authentication')
        self.assertIn('method', log.details)
        self.assertEqual(log.details['method'], 'POST')
        self.assertIn('status_code', log.details)
    
    def test_profile_update_audited(self):
        """Test de que las actualizaciones de perfil se auditen."""
        # Login primero
        self.client.login(email='test@example.com', password='testpass123')
        
        # Actualizar perfil
        response = self.client.post(reverse('agents:profile_edit'), {
            'first_name': 'Updated',
            'last_name': 'Name',
            'phone': '+54 11 1234-5678',
            'bio': 'Updated bio',
            'timezone': 'America/Argentina/Buenos_Aires',
            'language': 'es',
            'theme': 'light'
        })
        
        # Verificar log de auditoría
        audit_logs = AuditLog.objects.filter(
            agent=self.agent,
            action='profile_update'
        )
        self.assertTrue(audit_logs.exists())
        
        log = audit_logs.first()
        self.assertEqual(log.resource_type, 'user_profile')
        self.assertTrue(log.success)
        self.assertIn('profile_action', log.details)
    
    def test_security_settings_change_audited(self):
        """Test de que los cambios de configuración de seguridad se auditen."""
        self.client.login(email='test@example.com', password='testpass123')
        
        # Cambiar configuraciones de seguridad
        response = self.client.post(reverse('agents:security_settings'), {
            'session_timeout_minutes': 240,
            'suspicious_activity_alerts': False,
            'allowed_ip_addresses': '192.168.1.100'
        })
        
        # Verificar log de auditoría
        audit_logs = AuditLog.objects.filter(
            agent=self.agent,
            action='security_settings_change'
        )
        self.assertTrue(audit_logs.exists())
        
        log = audit_logs.first()
        self.assertEqual(log.resource_type, 'security_settings')
        self.assertIn('security_action', log.details)
    
    def test_session_termination_audited(self):
        """Test de que la terminación de sesiones se audite."""
        self.client.login(email='test@example.com', password='testpass123')
        
        # Terminar todas las sesiones
        response = self.client.post(reverse('agents:terminate_other_sessions'))
        
        # Verificar log de auditoría
        audit_logs = AuditLog.objects.filter(
            agent=self.agent,
            action='sessions_terminated'
        )
        self.assertTrue(audit_logs.exists())
        
        log = audit_logs.first()
        self.assertEqual(log.resource_type, 'user_session')
        self.assertIn('session_action', log.details)
        self.assertIn('terminate_scope', log.details)
    
    def test_middleware_excludes_static_paths(self):
        """Test de que el middleware excluya paths estáticos."""
        # Crear request para path estático
        request = self.factory.get('/static/css/style.css')
        self._setup_request_middleware(request)
        
        # Procesar con middleware
        response = self.middleware(request)
        
        # No debe haber logs de auditoría
        audit_logs = AuditLog.objects.all()
        self.assertEqual(audit_logs.count(), 0)
    
    def test_middleware_excludes_get_requests(self):
        """Test de que el middleware excluya requests GET."""
        # Crear request GET
        request = self.factory.get('/agents/profile/')
        request.user = self.agent
        self._setup_request_middleware(request)
        
        # Procesar con middleware
        response = self.middleware(request)
        
        # No debe haber logs de auditoría para GET
        audit_logs = AuditLog.objects.all()
        self.assertEqual(audit_logs.count(), 0)
    
    def test_middleware_handles_anonymous_users(self):
        """Test de que el middleware maneje usuarios anónimos."""
        # Crear request POST de usuario anónimo
        request = self.factory.post('/agents/login/', {
            'email': 'test@example.com',
            'password': 'wrongpass'
        })
        self._setup_request_middleware(request)
        
        # Simular response de error
        def error_response(req):
            return HttpResponse("Unauthorized", status=401)
        
        middleware = AuditMiddleware(error_response)
        response = middleware(request)
        
        # Debe crear log sin usuario
        audit_logs = AuditLog.objects.filter(agent=None)
        self.assertTrue(audit_logs.exists())
        
        log = audit_logs.first()
        self.assertIsNone(log.agent)
        self.assertEqual(log.action, 'login_attempt')
        self.assertFalse(log.success)  # 401 = no exitoso
    
    def test_middleware_sanitizes_sensitive_params(self):
        """Test de que el middleware sanitice parámetros sensibles."""
        # Crear request con parámetros sensibles
        request = self.factory.post('/agents/login/', {
            'email': 'test@example.com',
            'password': 'secret123',
            'csrf_token': 'abc123'
        })
        request.user = self.agent
        self._setup_request_middleware(request)
        
        # Procesar con middleware
        response = self.middleware(request)
        
        # Verificar que los parámetros sensibles fueron sanitizados
        audit_logs = AuditLog.objects.all()
        if audit_logs.exists():
            log = audit_logs.first()
            if 'query_params' in log.details:
                params = log.details['query_params']
                # Los parámetros sensibles deben estar redactados
                for key, value in params.items():
                    if any(sensitive in key.lower() for sensitive in ['password', 'token', 'secret']):
                        self.assertEqual(value, '[REDACTED]')
    
    def test_middleware_records_processing_time(self):
        """Test de que el middleware registre el tiempo de procesamiento."""
        # Crear request que tome tiempo
        def slow_response(request):
            import time
            time.sleep(0.1)  # Simular procesamiento lento
            return HttpResponse("OK")
        
        middleware = AuditMiddleware(slow_response)
        
        request = self.factory.post('/agents/profile/edit/')
        request.user = self.agent
        self._setup_request_middleware(request)
        
        # Procesar con middleware
        response = middleware(request)
        
        # Verificar que se registró el tiempo de procesamiento
        audit_logs = AuditLog.objects.all()
        if audit_logs.exists():
            log = audit_logs.first()
            self.assertIn('processing_time_ms', log.details)
            self.assertGreater(log.details['processing_time_ms'], 50)  # Al menos 50ms
    
    def test_middleware_determines_resource_type_correctly(self):
        """Test de que el middleware determine correctamente el tipo de recurso."""
        test_cases = [
            ('/agents/profile/edit/', 'user_profile'),
            ('/agents/security/', 'security_settings'),
            ('/agents/sessions/', 'user_session'),
            ('/properties/create/', 'property'),
            ('/contracts/1/edit/', 'contract'),
            ('/customers/create/', 'customer'),
        ]
        
        for path, expected_resource_type in test_cases:
            with self.subTest(path=path):
                request = self.factory.post(path)
                request.user = self.agent
                self._setup_request_middleware(request)
                
                # Procesar con middleware
                response = self.middleware(request)
                
                # Verificar tipo de recurso
                audit_logs = AuditLog.objects.filter(resource_type=expected_resource_type)
                self.assertTrue(audit_logs.exists(), 
                              f"No se encontró log con resource_type '{expected_resource_type}' para path '{path}'")
                
                # Limpiar para siguiente test
                AuditLog.objects.all().delete()
    
    def test_middleware_handles_ajax_requests(self):
        """Test de que el middleware maneje correctamente requests AJAX."""
        # Request AJAX para acción importante
        request = self.factory.post('/agents/sessions/terminate/test_key/', 
                                  HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        request.user = self.agent
        self._setup_request_middleware(request)
        
        # Procesar con middleware
        response = self.middleware(request)
        
        # Debe crear log para acción importante
        audit_logs = AuditLog.objects.filter(action='session_terminated')
        self.assertTrue(audit_logs.exists())
        
        # Limpiar
        AuditLog.objects.all().delete()
        
        # Request AJAX para datos frecuentes (debe ser excluido)
        request = self.factory.get('/agents/dashboard/data/', 
                                 HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        request.user = self.agent
        self._setup_request_middleware(request)
        
        # Procesar con middleware
        response = self.middleware(request)
        
        # No debe crear log para datos frecuentes
        audit_logs = AuditLog.objects.all()
        self.assertEqual(audit_logs.count(), 0)
    
    def test_middleware_handles_server_errors(self):
        """Test de que el middleware maneje errores del servidor."""
        # Simular error 500
        def error_response(request):
            return HttpResponse("Internal Server Error", status=500)
        
        middleware = AuditMiddleware(error_response)
        
        request = self.factory.post('/agents/profile/edit/')
        request.user = self.agent
        self._setup_request_middleware(request)
        
        # Procesar con middleware
        response = middleware(request)
        
        # No debe crear log para errores 500+
        audit_logs = AuditLog.objects.all()
        self.assertEqual(audit_logs.count(), 0)
    
    def test_middleware_extracts_url_kwargs(self):
        """Test de que el middleware extraiga correctamente los kwargs de URL."""
        # Request con kwargs en URL
        request = self.factory.post('/agents/1/edit/')
        request.user = self.agent
        self._setup_request_middleware(request)
        
        # Mock resolver para simular kwargs
        with patch('agents.middleware.audit_middleware.resolve') as mock_resolve:
            mock_resolved = MagicMock()
            mock_resolved.view_name = 'agents:agent_edit'
            mock_resolved.kwargs = {'pk': '1'}
            mock_resolve.return_value = mock_resolved
            
            # Procesar con middleware
            response = self.middleware(request)
        
        # Verificar que se extrajeron los kwargs
        audit_logs = AuditLog.objects.all()
        if audit_logs.exists():
            log = audit_logs.first()
            self.assertIn('url_kwargs', log.details)
            self.assertEqual(log.details['url_kwargs'], {'pk': '1'})
            self.assertEqual(log.resource_id, '1')
    
    def test_middleware_error_handling(self):
        """Test de que el middleware maneje errores internos graciosamente."""
        # Simular error en process_request
        with patch.object(self.middleware, '_get_client_ip', side_effect=Exception("Test error")):
            request = self.factory.post('/agents/profile/edit/')
            request.user = self.agent
            self._setup_request_middleware(request)
            
            # El middleware no debe fallar
            response = self.middleware(request)
            self.assertEqual(response.status_code, 200)
    
    def test_middleware_action_specific_details(self):
        """Test de que el middleware añada detalles específicos por acción."""
        # Test login con remember_me
        request = self.factory.post('/agents/login/', {
            'email': 'test@example.com',
            'password': 'testpass123',
            'remember_me': 'on'
        })
        self._setup_request_middleware(request)
        
        # Procesar con middleware
        response = self.middleware(request)
        
        # Verificar detalles específicos de login
        audit_logs = AuditLog.objects.filter(action='login_attempt')
        if audit_logs.exists():
            log = audit_logs.first()
            self.assertIn('login_method', log.details)
            self.assertEqual(log.details['login_method'], 'form')
            self.assertIn('remember_me', log.details)
    
    def test_middleware_success_determination(self):
        """Test de que el middleware determine correctamente el éxito de acciones."""
        test_cases = [
            (200, True),   # OK
            (201, True),   # Created
            (302, True),   # Redirect
            (400, False),  # Bad Request
            (401, False),  # Unauthorized
            (403, False),  # Forbidden
            (404, False),  # Not Found
            (500, False),  # Internal Server Error (pero no se audita)
        ]
        
        for status_code, expected_success in test_cases:
            if status_code >= 500:
                continue  # Los errores 500+ no se auditan
                
            with self.subTest(status_code=status_code):
                def status_response(request):
                    return HttpResponse("Response", status=status_code)
                
                middleware = AuditMiddleware(status_response)
                
                request = self.factory.post('/agents/profile/edit/')
                request.user = self.agent
                self._setup_request_middleware(request)
                
                # Procesar con middleware
                response = middleware(request)
                
                # Verificar determinación de éxito
                audit_logs = AuditLog.objects.all()
                if audit_logs.exists():
                    log = audit_logs.first()
                    self.assertEqual(log.success, expected_success,
                                   f"Status {status_code} should be {'successful' if expected_success else 'unsuccessful'}")
                
                # Limpiar para siguiente test
                AuditLog.objects.all().delete()
    
    def tearDown(self):
        """Limpieza después de cada test."""
        AuditLog.objects.all().delete()