"""
Tests para UserManagementService.
"""

from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from unittest.mock import patch, MagicMock

from agents.models import Agent, UserProfile, SecuritySettings, UserSession, AuditLog
from agents.services.user_management_service import UserManagementService


class UserManagementServiceTest(TestCase):
    """Tests para UserManagementService"""
    
    def setUp(self):
        self.service = UserManagementService()
        self.user_data = {
            'email': 'test@example.com',
            'password': 'TestPassword123!',
            'first_name': 'Test',
            'last_name': 'User',
            'license_number': 'LIC123456',
            'phone': '+1234567890',
            'bio': 'Test bio'
        }
    
    def test_create_user_success(self):
        """Test creación exitosa de usuario"""
        agent = self.service.create_user(self.user_data)
        
        # Verificar que el usuario se creó correctamente
        self.assertEqual(agent.email, 'test@example.com')
        self.assertEqual(agent.first_name, 'Test')
        self.assertEqual(agent.last_name, 'User')
        self.assertEqual(agent.license_number, 'LIC123456')
        self.assertTrue(agent.is_active)
        
        # Verificar que se creó el perfil
        self.assertTrue(hasattr(agent, 'profile'))
        profile = agent.profile
        self.assertEqual(profile.timezone, 'America/Argentina/Buenos_Aires')
        self.assertEqual(profile.language, 'es')
        self.assertEqual(profile.theme, 'light')
        
        # Verificar que se crearon las configuraciones de seguridad
        self.assertTrue(hasattr(agent, 'security_settings'))
        security = agent.security_settings
        self.assertEqual(security.session_timeout_minutes, 480)
        self.assertTrue(security.suspicious_activity_alerts)
    
    def test_create_user_with_profile_data(self):
        """Test creación de usuario con datos de perfil personalizados"""
        self.user_data['profile_data'] = {
            'timezone': 'Europe/Madrid',
            'language': 'en',
            'theme': 'dark'
        }
        
        agent = self.service.create_user(self.user_data)
        profile = agent.profile
        
        self.assertEqual(profile.timezone, 'Europe/Madrid')
        self.assertEqual(profile.language, 'en')
        self.assertEqual(profile.theme, 'dark')
    
    def test_create_user_missing_required_field(self):
        """Test creación de usuario con campo requerido faltante"""
        del self.user_data['email']
        
        with self.assertRaises(ValidationError) as context:
            self.service.create_user(self.user_data)
        
        self.assertIn("El campo 'email' es requerido", str(context.exception))
    
    def test_create_user_weak_password(self):
        """Test creación de usuario con contraseña débil"""
        self.user_data['password'] = '123'
        
        with self.assertRaises(ValidationError):
            self.service.create_user(self.user_data)
    
    def test_create_user_duplicate_email(self):
        """Test creación de usuario con email duplicado"""
        # Crear primer usuario
        self.service.create_user(self.user_data)
        
        # Intentar crear segundo usuario con mismo email
        self.user_data['license_number'] = 'LIC789'
        with self.assertRaises(Exception):
            self.service.create_user(self.user_data)
    
    def test_update_user_profile_success(self):
        """Test actualización exitosa de perfil"""
        agent = self.service.create_user(self.user_data)
        
        profile_data = {
            'timezone': 'Europe/London',
            'language': 'en',
            'theme': 'dark',
            'phone': '+9876543210',
            'bio': 'Updated bio'
        }
        
        updated_profile = self.service.update_user_profile(agent, profile_data)
        
        # Verificar actualización del perfil
        self.assertEqual(updated_profile.timezone, 'Europe/London')
        self.assertEqual(updated_profile.language, 'en')
        self.assertEqual(updated_profile.theme, 'dark')
        
        # Verificar actualización del agente
        agent.refresh_from_db()
        self.assertEqual(agent.phone, '+9876543210')
        self.assertEqual(agent.bio, 'Updated bio')
    
    def test_update_user_profile_creates_profile_if_not_exists(self):
        """Test que update_user_profile crea perfil si no existe"""
        # Crear usuario manualmente sin perfil
        agent = Agent.objects.create_user(
            username='test_user',
            email='test@example.com',
            password='TestPassword123!',
            first_name='Test',
            last_name='User',
            license_number='LIC123'
        )
        
        profile_data = {'timezone': 'Europe/Madrid'}
        updated_profile = self.service.update_user_profile(agent, profile_data)
        
        self.assertEqual(updated_profile.timezone, 'Europe/Madrid')
        self.assertTrue(UserProfile.objects.filter(agent=agent).exists())
    
    def test_deactivate_user_success(self):
        """Test desactivación exitosa de usuario"""
        agent = self.service.create_user(self.user_data)
        
        # Crear sesión activa
        UserSession.objects.create(
            agent=agent,
            session_key='test_session',
            ip_address='192.168.1.1',
            user_agent='Test Browser',
            expires_at=timezone.now() + timezone.timedelta(hours=1)
        )
        
        result = self.service.deactivate_user(agent, reason='Test deactivation')
        
        # Verificar desactivación
        self.assertTrue(result)
        agent.refresh_from_db()
        self.assertFalse(agent.is_active)
        
        # Verificar que las sesiones se terminaron
        active_sessions = UserSession.objects.filter(agent=agent, is_active=True)
        self.assertEqual(active_sessions.count(), 0)
        
        # Verificar log de auditoría
        audit_log = AuditLog.objects.filter(
            agent=agent,
            action='account_deactivated'
        ).first()
        self.assertIsNotNone(audit_log)
        self.assertEqual(audit_log.details['reason'], 'Test deactivation')
    
    def test_calculate_profile_completion_basic(self):
        """Test cálculo de completitud de perfil básico"""
        agent = self.service.create_user(self.user_data)
        
        completion = self.service.calculate_profile_completion(agent)
        
        # Debería tener un porcentaje alto ya que se proporcionaron la mayoría de campos
        self.assertGreater(completion, 70)
        self.assertLessEqual(completion, 100)
    
    def test_calculate_profile_completion_minimal(self):
        """Test cálculo de completitud con datos mínimos"""
        minimal_data = {
            'email': 'minimal@example.com',
            'password': 'TestPassword123!',
            'first_name': 'Min',
            'last_name': 'User',
            'license_number': 'LIC999'
        }
        
        agent = self.service.create_user(minimal_data)
        completion = self.service.calculate_profile_completion(agent)
        
        # Debería tener un porcentaje menor
        self.assertGreater(completion, 0)
        self.assertLess(completion, 80)
    
    def test_calculate_profile_completion_with_verifications(self):
        """Test cálculo de completitud con verificaciones"""
        agent = self.service.create_user(self.user_data)
        profile = agent.profile
        
        # Marcar verificaciones como completadas
        profile.email_verified = True
        profile.phone_verified = True
        profile.save()
        
        completion = self.service.calculate_profile_completion(agent)
        
        # Debería tener un porcentaje muy alto
        self.assertGreater(completion, 80)
    
    def test_get_user_dashboard_data(self):
        """Test obtención de datos del dashboard"""
        agent = self.service.create_user(self.user_data)
        
        # Crear algunos datos adicionales
        UserSession.objects.create(
            agent=agent,
            session_key='session1',
            ip_address='192.168.1.1',
            user_agent='Browser 1',
            expires_at=timezone.now() + timezone.timedelta(hours=1)
        )
        
        AuditLog.objects.create(
            agent=agent,
            action='login',
            resource_type='session',
            ip_address='192.168.1.1',
            user_agent='Browser 1',
            success=True
        )
        
        dashboard_data = self.service.get_user_dashboard_data(agent)
        
        # Verificar estructura de datos
        expected_keys = [
            'profile_completion', 'email_verified', 'phone_verified',
            'two_factor_enabled', 'active_sessions', 'account_locked',
            'last_login', 'recent_activity', 'security_alerts', 'session_timeout'
        ]
        
        for key in expected_keys:
            self.assertIn(key, dashboard_data)
        
        # Verificar algunos valores
        self.assertIsInstance(dashboard_data['profile_completion'], int)
        self.assertEqual(dashboard_data['active_sessions'], 1)
        self.assertFalse(dashboard_data['account_locked'])
        self.assertEqual(len(dashboard_data['recent_activity']), 1)
    
    def test_get_user_by_email_exists(self):
        """Test obtener usuario por email existente"""
        agent = self.service.create_user(self.user_data)
        
        found_agent = self.service.get_user_by_email('test@example.com')
        
        self.assertEqual(found_agent, agent)
    
    def test_get_user_by_email_not_exists(self):
        """Test obtener usuario por email inexistente"""
        found_agent = self.service.get_user_by_email('nonexistent@example.com')
        
        self.assertIsNone(found_agent)
    
    def test_get_user_by_email_inactive(self):
        """Test obtener usuario inactivo por email"""
        agent = self.service.create_user(self.user_data)
        agent.is_active = False
        agent.save()
        
        found_agent = self.service.get_user_by_email('test@example.com')
        
        self.assertIsNone(found_agent)
    
    def test_get_user_statistics(self):
        """Test obtención de estadísticas de usuario"""
        agent = self.service.create_user(self.user_data)
        
        # Crear algunos datos para estadísticas
        UserSession.objects.create(
            agent=agent,
            session_key='session1',
            ip_address='192.168.1.1',
            user_agent='Browser 1',
            expires_at=timezone.now() + timezone.timedelta(hours=1)
        )
        
        AuditLog.objects.create(
            agent=agent,
            action='login',
            resource_type='session',
            ip_address='192.168.1.1',
            user_agent='Browser 1',
            success=True
        )
        
        AuditLog.objects.create(
            agent=agent,
            action='logout',
            resource_type='session',
            ip_address='192.168.1.1',
            user_agent='Browser 1',
            success=False
        )
        
        statistics = self.service.get_user_statistics(agent)
        
        # Verificar estructura
        expected_keys = [
            'days_since_registration', 'total_sessions', 'total_actions',
            'successful_actions', 'success_rate', 'profile_completion'
        ]
        
        for key in expected_keys:
            self.assertIn(key, statistics)
        
        # Verificar algunos valores
        self.assertEqual(statistics['total_sessions'], 1)
        self.assertEqual(statistics['total_actions'], 2)
        self.assertEqual(statistics['successful_actions'], 1)
        self.assertEqual(statistics['success_rate'], 50.0)
    
    def test_generate_unique_username(self):
        """Test generación de username único"""
        # Crear usuario con username base
        Agent.objects.create_user(
            username='test',
            email='existing@example.com',
            password='TestPassword123!',
            first_name='Existing',
            last_name='User',
            license_number='LIC000'
        )
        
        # Generar username para nuevo usuario
        username = self.service._generate_unique_username('test@example.com')
        
        # Debería generar un username único
        self.assertEqual(username, 'test_1')
    
    def test_generate_unique_username_no_conflict(self):
        """Test generación de username sin conflicto"""
        username = self.service._generate_unique_username('unique@example.com')
        
        self.assertEqual(username, 'unique')