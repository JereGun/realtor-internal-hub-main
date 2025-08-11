"""
Tests para los formularios mejorados de usuarios.
"""

from django.test import TestCase, RequestFactory
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from unittest.mock import patch, MagicMock

from agents.models import Agent, UserProfile, SecuritySettings
from agents.forms import (
    EnhancedLoginForm, ProfileUpdateForm, SecuritySettingsForm,
    PasswordResetRequestForm, PasswordResetForm, EnhancedPasswordChangeForm
)


class EnhancedLoginFormTest(TestCase):
    """Tests para EnhancedLoginForm"""
    
    def setUp(self):
        self.factory = RequestFactory()
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
    
    def _create_request(self):
        """Helper para crear request de prueba"""
        request = self.factory.post('/login/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        request.META['HTTP_USER_AGENT'] = 'Test Browser'
        return request
    
    @patch('agents.forms.AuthenticationService')
    def test_valid_login_without_2fa(self, mock_auth_service):
        """Test login válido sin 2FA"""
        # Mock del servicio de autenticación
        mock_auth_instance = MagicMock()
        mock_auth_instance.authenticate_user.return_value = (
            self.agent, 
            {'success': True, 'message': 'Autenticación exitosa'}
        )
        mock_auth_service.return_value = mock_auth_instance
        
        request = self._create_request()
        form = EnhancedLoginForm(request=request, data={
            'email': 'test@example.com',
            'password': 'TestPassword123!',
            'remember_me': True
        })
        
        self.assertTrue(form.is_valid())
        self.assertEqual(form.get_user(), self.agent)
    
    @patch('agents.forms.AuthenticationService')
    def test_login_requires_2fa(self, mock_auth_service):
        """Test login que requiere 2FA"""
        # Mock del servicio de autenticación
        mock_auth_instance = MagicMock()
        mock_auth_instance.authenticate_user.return_value = (
            self.agent,
            {'requires_2fa': True, 'message': 'Se requiere 2FA'}
        )
        mock_auth_service.return_value = mock_auth_instance
        
        request = self._create_request()
        form = EnhancedLoginForm(request=request, data={
            'email': 'test@example.com',
            'password': 'TestPassword123!'
        })
        
        self.assertFalse(form.is_valid())
        self.assertIn('Se requiere código de autenticación de dos factores', str(form.errors))
        self.assertEqual(form.get_user(), self.agent)  # Usuario se almacena para siguiente intento
    
    @patch('agents.forms.AuthenticationService')
    def test_login_with_2fa_code(self, mock_auth_service):
        """Test login con código 2FA"""
        # Mock del servicio de autenticación
        mock_auth_instance = MagicMock()
        mock_auth_instance.authenticate_user.return_value = (
            self.agent,
            {'success': True, 'message': 'Autenticación exitosa'}
        )
        mock_auth_service.return_value = mock_auth_instance
        
        request = self._create_request()
        form = EnhancedLoginForm(request=request, data={
            'email': 'test@example.com',
            'password': 'TestPassword123!',
            'two_factor_code': '123456'
        })
        
        self.assertTrue(form.is_valid())
        self.assertEqual(form.get_user(), self.agent)
    
    @patch('agents.forms.AuthenticationService')
    def test_invalid_credentials(self, mock_auth_service):
        """Test credenciales inválidas"""
        # Mock del servicio de autenticación
        mock_auth_instance = MagicMock()
        mock_auth_instance.authenticate_user.side_effect = ValidationError('Credenciales inválidas')
        mock_auth_service.return_value = mock_auth_instance
        
        request = self._create_request()
        form = EnhancedLoginForm(request=request, data={
            'email': 'test@example.com',
            'password': 'WrongPassword'
        })
        
        self.assertFalse(form.is_valid())
        self.assertIn('Credenciales inválidas', str(form.errors))
    
    def test_form_fields_attributes(self):
        """Test atributos de los campos del formulario"""
        form = EnhancedLoginForm()
        
        # Verificar campo email
        email_field = form.fields['email']
        self.assertEqual(email_field.widget.attrs['class'], 'form-control')
        self.assertEqual(email_field.widget.attrs['autocomplete'], 'email')
        
        # Verificar campo password
        password_field = form.fields['password']
        self.assertEqual(password_field.widget.attrs['class'], 'form-control')
        self.assertEqual(password_field.widget.attrs['autocomplete'], 'current-password')
        
        # Verificar campo 2FA
        two_factor_field = form.fields['two_factor_code']
        self.assertEqual(two_factor_field.max_length, 6)
        self.assertFalse(two_factor_field.required)
        self.assertEqual(two_factor_field.widget.attrs['pattern'], '[0-9]{6}')


class ProfileUpdateFormTest(TestCase):
    """Tests para ProfileUpdateForm"""
    
    def setUp(self):
        self.agent = Agent.objects.create_user(
            username='test_user',
            email='test@example.com',
            password='TestPassword123!',
            first_name='Test',
            last_name='User',
            license_number='LIC123'
        )
        self.profile = UserProfile.objects.create(agent=self.agent)
    
    def test_form_initialization_with_agent(self):
        """Test inicialización del formulario con datos del agente"""
        form = ProfileUpdateForm(agent=self.agent, instance=self.profile)
        
        self.assertEqual(form.fields['first_name'].initial, 'Test')
        self.assertEqual(form.fields['last_name'].initial, 'User')
    
    def test_valid_profile_update(self):
        """Test actualización válida de perfil"""
        form_data = {
            'first_name': 'Updated',
            'last_name': 'Name',
            'phone': '+54 11 1234-5678',
            'bio': 'Updated bio',
            'timezone': 'Europe/Madrid',
            'language': 'en',
            'theme': 'dark'
        }
        
        form = ProfileUpdateForm(data=form_data, agent=self.agent, instance=self.profile)
        
        self.assertTrue(form.is_valid())
        
        # Guardar y verificar cambios
        updated_profile = form.save()
        self.agent.refresh_from_db()
        
        self.assertEqual(self.agent.first_name, 'Updated')
        self.assertEqual(self.agent.last_name, 'Name')
        self.assertEqual(self.agent.phone, '+54 11 1234-5678')
        self.assertEqual(self.agent.bio, 'Updated bio')
        self.assertEqual(updated_profile.timezone, 'Europe/Madrid')
        self.assertEqual(updated_profile.language, 'en')
        self.assertEqual(updated_profile.theme, 'dark')
    
    def test_phone_validation_too_short(self):
        """Test validación de teléfono muy corto"""
        form_data = {
            'first_name': 'Test',
            'last_name': 'User',
            'phone': '123',  # Muy corto
            'timezone': 'America/Argentina/Buenos_Aires',
            'language': 'es',
            'theme': 'light'
        }
        
        form = ProfileUpdateForm(data=form_data, agent=self.agent, instance=self.profile)
        
        self.assertFalse(form.is_valid())
        self.assertIn('phone', form.errors)
        self.assertIn('al menos 8 dígitos', str(form.errors['phone']))
    
    def test_avatar_validation_size(self):
        """Test validación de tamaño de avatar"""
        # Crear archivo muy grande (simulado)
        large_file = SimpleUploadedFile(
            "large_avatar.jpg",
            b"x" * (3 * 1024 * 1024),  # 3MB
            content_type="image/jpeg"
        )
        
        form_data = {
            'first_name': 'Test',
            'last_name': 'User',
            'timezone': 'America/Argentina/Buenos_Aires',
            'language': 'es',
            'theme': 'light'
        }
        
        form = ProfileUpdateForm(
            data=form_data, 
            files={'avatar': large_file},
            agent=self.agent, 
            instance=self.profile
        )
        
        self.assertFalse(form.is_valid())
        self.assertIn('avatar', form.errors)
        self.assertIn('muy grande', str(form.errors['avatar']))
    
    def test_avatar_validation_type(self):
        """Test validación de tipo de archivo de avatar"""
        # Crear archivo de tipo no permitido
        invalid_file = SimpleUploadedFile(
            "avatar.txt",
            b"not an image",
            content_type="text/plain"
        )
        
        form_data = {
            'first_name': 'Test',
            'last_name': 'User',
            'timezone': 'America/Argentina/Buenos_Aires',
            'language': 'es',
            'theme': 'light'
        }
        
        form = ProfileUpdateForm(
            data=form_data,
            files={'avatar': invalid_file},
            agent=self.agent,
            instance=self.profile
        )
        
        self.assertFalse(form.is_valid())
        self.assertIn('avatar', form.errors)
        self.assertIn('Formato no soportado', str(form.errors['avatar']))
    
    def test_valid_avatar_upload(self):
        """Test subida válida de avatar"""
        valid_file = SimpleUploadedFile(
            "avatar.jpg",
            b"fake image content",
            content_type="image/jpeg"
        )
        
        form_data = {
            'first_name': 'Test',
            'last_name': 'User',
            'timezone': 'America/Argentina/Buenos_Aires',
            'language': 'es',
            'theme': 'light'
        }
        
        form = ProfileUpdateForm(
            data=form_data,
            files={'avatar': valid_file},
            agent=self.agent,
            instance=self.profile
        )
        
        self.assertTrue(form.is_valid())


class SecuritySettingsFormTest(TestCase):
    """Tests para SecuritySettingsForm"""
    
    def setUp(self):
        self.agent = Agent.objects.create_user(
            username='test_user',
            email='test@example.com',
            password='TestPassword123!',
            first_name='Test',
            last_name='User',
            license_number='LIC123'
        )
        self.profile = UserProfile.objects.create(agent=self.agent, two_factor_enabled=True)
        self.security_settings = SecuritySettings.objects.create(agent=self.agent)
    
    def test_form_initialization_with_2fa_status(self):
        """Test inicialización del formulario con estado de 2FA"""
        form = SecuritySettingsForm(agent=self.agent, instance=self.security_settings)
        
        self.assertTrue(form.fields['enable_2fa'].initial)
    
    def test_valid_security_settings_update(self):
        """Test actualización válida de configuraciones de seguridad"""
        form_data = {
            'session_timeout_minutes': 240,
            'suspicious_activity_alerts': True,
            'allowed_ip_addresses': '192.168.1.100\n10.0.0.*\n203.0.113.1',
            'enable_2fa': False
        }
        
        form = SecuritySettingsForm(
            data=form_data,
            agent=self.agent,
            instance=self.security_settings
        )
        
        self.assertTrue(form.is_valid())
        
        # Verificar que las IPs se convierten a lista
        cleaned_ips = form.cleaned_data['allowed_ip_addresses']
        expected_ips = ['192.168.1.100', '10.0.0.*', '203.0.113.1']
        self.assertEqual(cleaned_ips, expected_ips)
    
    def test_session_timeout_validation_too_low(self):
        """Test validación de timeout muy bajo"""
        form_data = {
            'session_timeout_minutes': 15,  # Muy bajo
            'suspicious_activity_alerts': True,
            'allowed_ip_addresses': ''
        }
        
        form = SecuritySettingsForm(
            data=form_data,
            agent=self.agent,
            instance=self.security_settings
        )
        
        self.assertFalse(form.is_valid())
        self.assertIn('session_timeout_minutes', form.errors)
        self.assertIn('entre 30 y 1440', str(form.errors['session_timeout_minutes']))
    
    def test_session_timeout_validation_too_high(self):
        """Test validación de timeout muy alto"""
        form_data = {
            'session_timeout_minutes': 2000,  # Muy alto
            'suspicious_activity_alerts': True,
            'allowed_ip_addresses': ''
        }
        
        form = SecuritySettingsForm(
            data=form_data,
            agent=self.agent,
            instance=self.security_settings
        )
        
        self.assertFalse(form.is_valid())
        self.assertIn('session_timeout_minutes', form.errors)
    
    def test_ip_validation_invalid_format(self):
        """Test validación de formato de IP inválido"""
        form_data = {
            'session_timeout_minutes': 480,
            'suspicious_activity_alerts': True,
            'allowed_ip_addresses': '192.168.1.300\n999.999.999.999'  # IPs inválidas
        }
        
        form = SecuritySettingsForm(
            data=form_data,
            agent=self.agent,
            instance=self.security_settings
        )
        
        self.assertFalse(form.is_valid())
        self.assertIn('allowed_ip_addresses', form.errors)
        self.assertIn('Formato de IP inválido', str(form.errors['allowed_ip_addresses']))
    
    def test_ip_validation_valid_wildcards(self):
        """Test validación de IPs con wildcards válidos"""
        form_data = {
            'session_timeout_minutes': 480,
            'suspicious_activity_alerts': True,
            'allowed_ip_addresses': '192.168.*.*\n10.0.0.*\n*.*.*.1'
        }
        
        form = SecuritySettingsForm(
            data=form_data,
            agent=self.agent,
            instance=self.security_settings
        )
        
        self.assertTrue(form.is_valid())
        
        cleaned_ips = form.cleaned_data['allowed_ip_addresses']
        expected_ips = ['192.168.*.*', '10.0.0.*', '*.*.*.1']
        self.assertEqual(cleaned_ips, expected_ips)
    
    def test_empty_ip_list(self):
        """Test lista de IPs vacía"""
        form_data = {
            'session_timeout_minutes': 480,
            'suspicious_activity_alerts': True,
            'allowed_ip_addresses': ''
        }
        
        form = SecuritySettingsForm(
            data=form_data,
            agent=self.agent,
            instance=self.security_settings
        )
        
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['allowed_ip_addresses'], [])


class PasswordResetRequestFormTest(TestCase):
    """Tests para PasswordResetRequestForm"""
    
    def setUp(self):
        self.agent = Agent.objects.create_user(
            username='test_user',
            email='test@example.com',
            password='TestPassword123!',
            first_name='Test',
            last_name='User',
            license_number='LIC123'
        )
    
    def test_valid_email_request(self):
        """Test solicitud válida de reset de contraseña"""
        form = PasswordResetRequestForm(data={
            'email': 'test@example.com'
        })
        
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['email'], 'test@example.com')
    
    def test_nonexistent_email_request(self):
        """Test solicitud con email inexistente (no debe revelar si existe)"""
        form = PasswordResetRequestForm(data={
            'email': 'nonexistent@example.com'
        })
        
        # El formulario debe ser válido por seguridad (no revelar si el email existe)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['email'], 'nonexistent@example.com')
    
    def test_invalid_email_format(self):
        """Test formato de email inválido"""
        form = PasswordResetRequestForm(data={
            'email': 'invalid-email'
        })
        
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)


class PasswordResetFormTest(TestCase):
    """Tests para PasswordResetForm"""
    
    def setUp(self):
        self.agent = Agent.objects.create_user(
            username='test_user',
            email='test@example.com',
            password='TestPassword123!',
            first_name='Test',
            last_name='User',
            license_number='LIC123'
        )
    
    def test_valid_password_reset(self):
        """Test reset válido de contraseña"""
        form = PasswordResetForm(user=self.agent, data={
            'new_password1': 'NewStrongPassword123!',
            'new_password2': 'NewStrongPassword123!'
        })
        
        self.assertTrue(form.is_valid())
    
    def test_password_mismatch(self):
        """Test contraseñas que no coinciden"""
        form = PasswordResetForm(user=self.agent, data={
            'new_password1': 'NewStrongPassword123!',
            'new_password2': 'DifferentPassword123!'
        })
        
        self.assertFalse(form.is_valid())
        self.assertIn('new_password2', form.errors)
    
    def test_weak_password(self):
        """Test contraseña débil"""
        form = PasswordResetForm(user=self.agent, data={
            'new_password1': '123',
            'new_password2': '123'
        })
        
        self.assertFalse(form.is_valid())
        self.assertIn('new_password1', form.errors)


class EnhancedPasswordChangeFormTest(TestCase):
    """Tests para EnhancedPasswordChangeForm"""
    
    def setUp(self):
        self.agent = Agent.objects.create_user(
            username='test_user',
            email='test@example.com',
            password='TestPassword123!',
            first_name='Test',
            last_name='User',
            license_number='LIC123'
        )
    
    def test_valid_password_change(self):
        """Test cambio válido de contraseña"""
        form = EnhancedPasswordChangeForm(user=self.agent, data={
            'old_password': 'TestPassword123!',
            'new_password1': 'NewStrongPassword123!',
            'new_password2': 'NewStrongPassword123!'
        })
        
        self.assertTrue(form.is_valid())
    
    def test_wrong_old_password(self):
        """Test contraseña actual incorrecta"""
        form = EnhancedPasswordChangeForm(user=self.agent, data={
            'old_password': 'WrongPassword',
            'new_password1': 'NewStrongPassword123!',
            'new_password2': 'NewStrongPassword123!'
        })
        
        self.assertFalse(form.is_valid())
        self.assertIn('old_password', form.errors)
    
    def test_new_password_mismatch(self):
        """Test nuevas contraseñas que no coinciden"""
        form = EnhancedPasswordChangeForm(user=self.agent, data={
            'old_password': 'TestPassword123!',
            'new_password1': 'NewStrongPassword123!',
            'new_password2': 'DifferentPassword123!'
        })
        
        self.assertFalse(form.is_valid())
        self.assertIn('new_password2', form.errors)
    
    def test_form_field_attributes(self):
        """Test atributos de los campos del formulario"""
        form = EnhancedPasswordChangeForm(user=self.agent)
        
        # Verificar atributos de campos
        self.assertEqual(form.fields['old_password'].widget.attrs['class'], 'form-control')
        self.assertEqual(form.fields['new_password1'].widget.attrs['class'], 'form-control')
        self.assertEqual(form.fields['new_password2'].widget.attrs['class'], 'form-control')
        
        # Verificar autocomplete
        self.assertEqual(form.fields['old_password'].widget.attrs['autocomplete'], 'current-password')
        self.assertEqual(form.fields['new_password1'].widget.attrs['autocomplete'], 'new-password')
        self.assertEqual(form.fields['new_password2'].widget.attrs['autocomplete'], 'new-password')