"""
Tests para los modelos extendidos de gestión de usuarios.
"""

from django.test import TestCase
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import timedelta
import json

from agents.models import (
    Agent, UserProfile, Role, Permission, AgentRole, 
    UserSession, SecuritySettings, AuditLog
)


class UserProfileModelTest(TestCase):
    """Tests para el modelo UserProfile"""
    
    def setUp(self):
        self.agent = Agent.objects.create_user(
            username='test_agent',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='Agent',
            license_number='LIC123'
        )
    
    def test_create_user_profile(self):
        """Test creación de perfil de usuario"""
        profile = UserProfile.objects.create(
            agent=self.agent,
            timezone='America/Argentina/Buenos_Aires',
            language='es',
            theme='light'
        )
        
        self.assertEqual(profile.agent, self.agent)
        self.assertEqual(profile.timezone, 'America/Argentina/Buenos_Aires')
        self.assertEqual(profile.language, 'es')
        self.assertEqual(profile.theme, 'light')
        self.assertFalse(profile.email_verified)
        self.assertFalse(profile.two_factor_enabled)
        self.assertEqual(profile.profile_completion, 0)
    
    def test_generate_email_verification_token(self):
        """Test generación de token de verificación de email"""
        profile = UserProfile.objects.create(agent=self.agent)
        
        token = profile.generate_email_verification_token()
        
        self.assertIsNotNone(token)
        self.assertEqual(profile.email_verification_token, token)
        self.assertTrue(len(token) > 20)  # Token debe ser suficientemente largo
    
    def test_generate_backup_codes(self):
        """Test generación de códigos de respaldo"""
        profile = UserProfile.objects.create(agent=self.agent)
        
        codes = profile.generate_backup_codes(count=5)
        
        self.assertEqual(len(codes), 5)
        self.assertEqual(len(profile.backup_codes), 5)
        for code in codes:
            self.assertTrue(len(code) >= 8)  # Códigos deben tener longitud mínima
    
    def test_use_backup_code(self):
        """Test uso de código de respaldo"""
        profile = UserProfile.objects.create(agent=self.agent)
        codes = profile.generate_backup_codes(count=3)
        
        # Usar código válido
        result = profile.use_backup_code(codes[0])
        self.assertTrue(result)
        self.assertEqual(len(profile.backup_codes), 2)
        self.assertNotIn(codes[0], profile.backup_codes)
        
        # Intentar usar código ya usado
        result = profile.use_backup_code(codes[0])
        self.assertFalse(result)
    
    def test_profile_str_representation(self):
        """Test representación string del perfil"""
        profile = UserProfile.objects.create(agent=self.agent)
        expected = f"Perfil de {self.agent.get_full_name()}"
        self.assertEqual(str(profile), expected)


class RoleModelTest(TestCase):
    """Tests para el modelo Role"""
    
    def setUp(self):
        self.content_type = ContentType.objects.get_for_model(Agent)
        self.permission = Permission.objects.create(
            codename='test_permission',
            name='Test Permission',
            content_type=self.content_type,
            description='Permission for testing'
        )
    
    def test_create_role(self):
        """Test creación de rol"""
        role = Role.objects.create(
            name='Test Role',
            description='Role for testing',
            is_system_role=True
        )
        
        self.assertEqual(role.name, 'Test Role')
        self.assertEqual(role.description, 'Role for testing')
        self.assertTrue(role.is_system_role)
    
    def test_add_permission_to_role(self):
        """Test añadir permiso a rol"""
        role = Role.objects.create(name='Test Role')
        
        role.add_permission(self.permission)
        
        self.assertTrue(role.permissions.filter(id=self.permission.id).exists())
        self.assertTrue(role.has_permission('test_permission'))
    
    def test_remove_permission_from_role(self):
        """Test eliminar permiso de rol"""
        role = Role.objects.create(name='Test Role')
        role.add_permission(self.permission)
        
        role.remove_permission(self.permission)
        
        self.assertFalse(role.permissions.filter(id=self.permission.id).exists())
        self.assertFalse(role.has_permission('test_permission'))
    
    def test_role_str_representation(self):
        """Test representación string del rol"""
        role = Role.objects.create(name='Test Role')
        self.assertEqual(str(role), 'Test Role')


class PermissionModelTest(TestCase):
    """Tests para el modelo Permission"""
    
    def setUp(self):
        self.content_type = ContentType.objects.get_for_model(Agent)
    
    def test_create_permission(self):
        """Test creación de permiso"""
        permission = Permission.objects.create(
            codename='test_permission',
            name='Test Permission',
            content_type=self.content_type,
            description='Permission for testing'
        )
        
        self.assertEqual(permission.codename, 'test_permission')
        self.assertEqual(permission.name, 'Test Permission')
        self.assertEqual(permission.content_type, self.content_type)
        self.assertEqual(permission.description, 'Permission for testing')
    
    def test_permission_unique_constraint(self):
        """Test restricción de unicidad de permisos"""
        Permission.objects.create(
            codename='test_permission',
            name='Test Permission',
            content_type=self.content_type
        )
        
        # Intentar crear permiso duplicado debe fallar
        with self.assertRaises(Exception):
            Permission.objects.create(
                codename='test_permission',
                name='Another Test Permission',
                content_type=self.content_type
            )
    
    def test_permission_str_representation(self):
        """Test representación string del permiso"""
        permission = Permission.objects.create(
            codename='test_permission',
            name='Test Permission',
            content_type=self.content_type
        )
        expected = f"{self.content_type.name} | Test Permission"
        self.assertEqual(str(permission), expected)


class AgentRoleModelTest(TestCase):
    """Tests para el modelo AgentRole"""
    
    def setUp(self):
        self.agent = Agent.objects.create_user(
            username='test_agent',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='Agent',
            license_number='LIC123'
        )
        self.admin_agent = Agent.objects.create_user(
            username='admin_agent',
            email='admin@example.com',
            password='adminpass123',
            first_name='Admin',
            last_name='Agent',
            license_number='LIC456'
        )
        self.role = Role.objects.create(name='Test Role')
    
    def test_create_agent_role(self):
        """Test creación de asignación de rol"""
        agent_role = AgentRole.objects.create(
            agent=self.agent,
            role=self.role,
            assigned_by=self.admin_agent
        )
        
        self.assertEqual(agent_role.agent, self.agent)
        self.assertEqual(agent_role.role, self.role)
        self.assertEqual(agent_role.assigned_by, self.admin_agent)
        self.assertTrue(agent_role.is_active)
        self.assertIsNotNone(agent_role.assigned_at)
    
    def test_agent_role_unique_constraint(self):
        """Test restricción de unicidad de asignación de rol"""
        AgentRole.objects.create(
            agent=self.agent,
            role=self.role,
            assigned_by=self.admin_agent
        )
        
        # Intentar crear asignación duplicada debe fallar
        with self.assertRaises(Exception):
            AgentRole.objects.create(
                agent=self.agent,
                role=self.role,
                assigned_by=self.admin_agent
            )
    
    def test_agent_role_str_representation(self):
        """Test representación string de asignación de rol"""
        agent_role = AgentRole.objects.create(
            agent=self.agent,
            role=self.role
        )
        expected = f"{self.agent.get_full_name()} - {self.role.name}"
        self.assertEqual(str(agent_role), expected)


class UserSessionModelTest(TestCase):
    """Tests para el modelo UserSession"""
    
    def setUp(self):
        self.agent = Agent.objects.create_user(
            username='test_agent',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='Agent',
            license_number='LIC123'
        )
    
    def test_create_user_session(self):
        """Test creación de sesión de usuario"""
        expires_at = timezone.now() + timedelta(hours=8)
        session = UserSession.objects.create(
            agent=self.agent,
            session_key='test_session_key_123',
            ip_address='192.168.1.1',
            user_agent='Mozilla/5.0 Test Browser',
            device_info={'device': 'desktop', 'os': 'Windows'},
            location={'country': 'Argentina', 'city': 'Buenos Aires'},
            expires_at=expires_at
        )
        
        self.assertEqual(session.agent, self.agent)
        self.assertEqual(session.session_key, 'test_session_key_123')
        self.assertEqual(session.ip_address, '192.168.1.1')
        self.assertTrue(session.is_active)
        self.assertEqual(session.expires_at, expires_at)
    
    def test_session_is_expired(self):
        """Test verificación de expiración de sesión"""
        # Sesión expirada
        expired_session = UserSession.objects.create(
            agent=self.agent,
            session_key='expired_session',
            ip_address='192.168.1.1',
            user_agent='Test Browser',
            expires_at=timezone.now() - timedelta(hours=1)
        )
        self.assertTrue(expired_session.is_expired())
        
        # Sesión válida
        valid_session = UserSession.objects.create(
            agent=self.agent,
            session_key='valid_session',
            ip_address='192.168.1.1',
            user_agent='Test Browser',
            expires_at=timezone.now() + timedelta(hours=1)
        )
        self.assertFalse(valid_session.is_expired())
    
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
        session.extend_session(minutes=120)  # 2 horas
        
        self.assertGreater(session.expires_at, original_expiry)
    
    def test_terminate_session(self):
        """Test terminación de sesión"""
        session = UserSession.objects.create(
            agent=self.agent,
            session_key='test_session',
            ip_address='192.168.1.1',
            user_agent='Test Browser',
            expires_at=timezone.now() + timedelta(hours=1)
        )
        
        session.terminate()
        
        self.assertFalse(session.is_active)
    
    def test_session_str_representation(self):
        """Test representación string de sesión"""
        session = UserSession.objects.create(
            agent=self.agent,
            session_key='test_session',
            ip_address='192.168.1.1',
            user_agent='Test Browser',
            expires_at=timezone.now() + timedelta(hours=1)
        )
        expected = f"Sesión de {self.agent.get_full_name()} - 192.168.1.1"
        self.assertEqual(str(session), expected)


class SecuritySettingsModelTest(TestCase):
    """Tests para el modelo SecuritySettings"""
    
    def setUp(self):
        self.agent = Agent.objects.create_user(
            username='test_agent',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='Agent',
            license_number='LIC123'
        )
    
    def test_create_security_settings(self):
        """Test creación de configuraciones de seguridad"""
        settings = SecuritySettings.objects.create(
            agent=self.agent,
            session_timeout_minutes=240,
            allowed_ip_addresses=['192.168.1.1', '10.0.0.1']
        )
        
        self.assertEqual(settings.agent, self.agent)
        self.assertEqual(settings.login_attempts, 0)
        self.assertEqual(settings.session_timeout_minutes, 240)
        self.assertEqual(len(settings.allowed_ip_addresses), 2)
        self.assertTrue(settings.suspicious_activity_alerts)
    
    def test_is_locked(self):
        """Test verificación de bloqueo de cuenta"""
        settings = SecuritySettings.objects.create(agent=self.agent)
        
        # Cuenta no bloqueada
        self.assertFalse(settings.is_locked())
        
        # Bloquear cuenta
        settings.locked_until = timezone.now() + timedelta(minutes=15)
        settings.save()
        self.assertTrue(settings.is_locked())
        
        # Cuenta con bloqueo expirado
        settings.locked_until = timezone.now() - timedelta(minutes=1)
        settings.save()
        self.assertFalse(settings.is_locked())
    
    def test_lock_account(self):
        """Test bloqueo de cuenta"""
        settings = SecuritySettings.objects.create(agent=self.agent)
        
        settings.lock_account(minutes=30)
        
        self.assertIsNotNone(settings.locked_until)
        self.assertTrue(settings.is_locked())
    
    def test_unlock_account(self):
        """Test desbloqueo de cuenta"""
        settings = SecuritySettings.objects.create(
            agent=self.agent,
            login_attempts=3,
            locked_until=timezone.now() + timedelta(minutes=15)
        )
        
        settings.unlock_account()
        
        self.assertIsNone(settings.locked_until)
        self.assertEqual(settings.login_attempts, 0)
        self.assertFalse(settings.is_locked())
    
    def test_increment_login_attempts(self):
        """Test incremento de intentos de login"""
        settings = SecuritySettings.objects.create(agent=self.agent)
        
        # Primer intento
        settings.increment_login_attempts()
        self.assertEqual(settings.login_attempts, 1)
        self.assertFalse(settings.is_locked())
        
        # Segundo intento
        settings.increment_login_attempts()
        self.assertEqual(settings.login_attempts, 2)
        self.assertFalse(settings.is_locked())
        
        # Tercer intento - debe bloquear
        settings.increment_login_attempts()
        self.assertEqual(settings.login_attempts, 3)
        self.assertTrue(settings.is_locked())
    
    def test_reset_login_attempts(self):
        """Test reset de intentos de login"""
        settings = SecuritySettings.objects.create(
            agent=self.agent,
            login_attempts=2
        )
        
        settings.reset_login_attempts()
        
        self.assertEqual(settings.login_attempts, 0)
    
    def test_security_settings_str_representation(self):
        """Test representación string de configuraciones de seguridad"""
        settings = SecuritySettings.objects.create(agent=self.agent)
        expected = f"Seguridad de {self.agent.get_full_name()}"
        self.assertEqual(str(settings), expected)


class AuditLogModelTest(TestCase):
    """Tests para el modelo AuditLog"""
    
    def setUp(self):
        self.agent = Agent.objects.create_user(
            username='test_agent',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='Agent',
            license_number='LIC123'
        )
    
    def test_create_audit_log(self):
        """Test creación de log de auditoría"""
        log = AuditLog.objects.create(
            agent=self.agent,
            action='login',
            resource_type='session',
            resource_id='session_123',
            ip_address='192.168.1.1',
            user_agent='Mozilla/5.0 Test Browser',
            details={'login_method': 'email', 'success': True},
            success=True,
            session_key='session_key_123'
        )
        
        self.assertEqual(log.agent, self.agent)
        self.assertEqual(log.action, 'login')
        self.assertEqual(log.resource_type, 'session')
        self.assertEqual(log.resource_id, 'session_123')
        self.assertEqual(log.ip_address, '192.168.1.1')
        self.assertTrue(log.success)
        self.assertEqual(log.details['login_method'], 'email')
    
    def test_audit_log_without_agent(self):
        """Test log de auditoría sin agente (usuario anónimo)"""
        log = AuditLog.objects.create(
            agent=None,
            action='login',
            resource_type='session',
            ip_address='192.168.1.1',
            user_agent='Mozilla/5.0 Test Browser',
            success=False
        )
        
        self.assertIsNone(log.agent)
        self.assertFalse(log.success)
    
    def test_audit_log_str_representation(self):
        """Test representación string de log de auditoría"""
        log = AuditLog.objects.create(
            agent=self.agent,
            action='login',
            resource_type='session',
            ip_address='192.168.1.1',
            user_agent='Test Browser'
        )
        
        expected_start = f"{self.agent.get_full_name()} - Inicio de Sesión -"
        self.assertTrue(str(log).startswith(expected_start))
    
    def test_audit_log_str_representation_no_agent(self):
        """Test representación string de log sin agente"""
        log = AuditLog.objects.create(
            agent=None,
            action='login',
            resource_type='session',
            ip_address='192.168.1.1',
            user_agent='Test Browser'
        )
        
        expected_start = "Usuario Desconocido - Inicio de Sesión -"
        self.assertTrue(str(log).startswith(expected_start))