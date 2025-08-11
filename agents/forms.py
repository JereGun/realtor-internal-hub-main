
from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm, SetPasswordForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import authenticate
import re

from .models import Agent, UserProfile, SecuritySettings
from .services.authentication_service import AuthenticationService


class EnhancedLoginForm(forms.Form):
    """
    Formulario de login mejorado con validaciones de seguridad.
    
    Incluye soporte para 2FA, validaciones de seguridad y manejo
    de cuentas bloqueadas.
    """
    email = forms.EmailField(
        label=_('Email'),
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email',
            'autocomplete': 'email',
            'required': True
        })
    )
    
    password = forms.CharField(
        label=_('Contraseña'),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Contraseña',
            'autocomplete': 'current-password',
            'required': True
        })
    )
    
    two_factor_code = forms.CharField(
        label=_('Código de Autenticación'),
        max_length=6,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '000000',
            'maxlength': '6',
            'pattern': '[0-9]{6}',
            'autocomplete': 'one-time-code'
        }),
        help_text=_('Ingrese el código de 6 dígitos de su aplicación de autenticación')
    )
    
    remember_me = forms.BooleanField(
        label=_('Recordarme'),
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    
    def __init__(self, request=None, *args, **kwargs):
        """
        Inicializa el formulario con el request para validaciones de seguridad.
        
        Args:
            request: HttpRequest object para validaciones de seguridad
        """
        super().__init__(*args, **kwargs)
        self.request = request
        self.user_cache = None
        self.auth_service = AuthenticationService()
    
    def clean(self):
        """
        Validación completa del formulario con verificaciones de seguridad.
        
        Returns:
            dict: Datos limpios del formulario
            
        Raises:
            ValidationError: Si las credenciales son inválidas o hay problemas de seguridad
        """
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        password = cleaned_data.get('password')
        two_factor_code = cleaned_data.get('two_factor_code')
        
        if email and password:
            try:
                # Usar el servicio de autenticación para validar
                user, auth_result = self.auth_service.authenticate_user(
                    email=email,
                    password=password,
                    request=self.request,
                    two_factor_code=two_factor_code
                )
                
                if auth_result.get('requires_2fa'):
                    # Almacenar usuario temporalmente para el siguiente intento
                    self.user_cache = user
                    raise ValidationError(
                        _('Se requiere código de autenticación de dos factores.'),
                        code='2fa_required'
                    )
                
                if auth_result.get('success'):
                    self.user_cache = user
                else:
                    raise ValidationError(
                        auth_result.get('message', _('Credenciales inválidas')),
                        code='invalid_credentials'
                    )
                    
            except ValidationError as e:
                # Re-lanzar ValidationError de autenticación
                raise e
            except Exception as e:
                raise ValidationError(
                    _('Error interno del servidor. Intente nuevamente.'),
                    code='server_error'
                )
        
        return cleaned_data
    
    def get_user(self):
        """
        Retorna el usuario autenticado.
        
        Returns:
            Agent: Usuario autenticado o None
        """
        return self.user_cache


class ProfileUpdateForm(forms.ModelForm):
    """
    Formulario para actualización de perfil de usuario.
    
    Incluye campos del Agent y UserProfile con validaciones mejoradas.
    """
    # Campos del Agent
    first_name = forms.CharField(
        label=_('Nombre'),
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nombre'
        })
    )
    
    last_name = forms.CharField(
        label=_('Apellido'),
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Apellido'
        })
    )
    
    phone = forms.CharField(
        label=_('Teléfono'),
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+54 11 1234-5678',
            'pattern': r'[\+]?[0-9\s\-\(\)]+',
        }),
        help_text=_('Formato: +54 11 1234-5678')
    )
    
    bio = forms.CharField(
        label=_('Biografía'),
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Cuéntanos sobre ti...',
            'maxlength': 500
        }),
        help_text=_('Máximo 500 caracteres')
    )
    
    class Meta:
        model = UserProfile
        fields = ['avatar', 'timezone', 'language', 'theme']
        widgets = {
            'avatar': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'timezone': forms.Select(attrs={
                'class': 'form-select'
            }),
            'language': forms.Select(attrs={
                'class': 'form-select'
            }),
            'theme': forms.Select(attrs={
                'class': 'form-select'
            })
        }
        labels = {
            'avatar': _('Foto de Perfil'),
            'timezone': _('Zona Horaria'),
            'language': _('Idioma'),
            'theme': _('Tema')
        }
        help_texts = {
            'avatar': _('Formatos soportados: JPG, PNG, GIF. Tamaño máximo: 2MB'),
            'timezone': _('Seleccione su zona horaria local'),
            'language': _('Idioma de la interfaz'),
            'theme': _('Apariencia de la interfaz')
        }
    
    def __init__(self, *args, **kwargs):
        """Inicializa el formulario con datos del usuario."""
        self.agent = kwargs.pop('agent', None)
        super().__init__(*args, **kwargs)
        
        # Poblar campos del Agent si está disponible
        if self.agent:
            self.fields['first_name'].initial = self.agent.first_name
            self.fields['last_name'].initial = self.agent.last_name
            self.fields['phone'].initial = self.agent.phone
            self.fields['bio'].initial = self.agent.bio
    
    def clean_phone(self):
        """
        Valida el formato del teléfono.
        
        Returns:
            str: Teléfono validado
        """
        phone = self.cleaned_data.get('phone')
        if phone:
            # Remover espacios y caracteres especiales para validación
            clean_phone = re.sub(r'[^\d\+]', '', phone)
            if len(clean_phone) < 8:
                raise ValidationError(_('El teléfono debe tener al menos 8 dígitos'))
        return phone
    
    def clean_avatar(self):
        """
        Valida el archivo de avatar.
        
        Returns:
            File: Archivo de avatar validado
        """
        avatar = self.cleaned_data.get('avatar')
        if avatar:
            # Validar tamaño (2MB máximo)
            if avatar.size > 2 * 1024 * 1024:
                raise ValidationError(_('El archivo es muy grande. Tamaño máximo: 2MB'))
            
            # Validar tipo de archivo
            allowed_types = ['image/jpeg', 'image/png', 'image/gif']
            if avatar.content_type not in allowed_types:
                raise ValidationError(_('Formato no soportado. Use JPG, PNG o GIF'))
        
        return avatar
    
    def save(self, commit=True):
        """
        Guarda el perfil y actualiza los campos del Agent.
        
        Args:
            commit: Si debe guardar en la base de datos
            
        Returns:
            UserProfile: Perfil actualizado
        """
        profile = super().save(commit=False)
        
        # Actualizar campos del Agent
        if self.agent:
            self.agent.first_name = self.cleaned_data['first_name']
            self.agent.last_name = self.cleaned_data['last_name']
            self.agent.phone = self.cleaned_data['phone']
            self.agent.bio = self.cleaned_data['bio']
            
            if commit:
                self.agent.save()
        
        if commit:
            profile.save()
        
        return profile


class SecuritySettingsForm(forms.ModelForm):
    """
    Formulario para configuraciones de seguridad del usuario.
    
    Permite configurar 2FA, timeouts de sesión y alertas de seguridad.
    """
    enable_2fa = forms.BooleanField(
        label=_('Habilitar Autenticación de Dos Factores'),
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        help_text=_('Añade una capa extra de seguridad a tu cuenta')
    )
    
    class Meta:
        model = SecuritySettings
        fields = ['session_timeout_minutes', 'suspicious_activity_alerts', 'allowed_ip_addresses']
        widgets = {
            'session_timeout_minutes': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 30,
                'max': 1440,
                'step': 30
            }),
            'suspicious_activity_alerts': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'allowed_ip_addresses': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': '192.168.1.100\n10.0.0.*\n203.0.113.1'
            })
        }
        labels = {
            'session_timeout_minutes': _('Timeout de Sesión (minutos)'),
            'suspicious_activity_alerts': _('Alertas de Actividad Sospechosa'),
            'allowed_ip_addresses': _('Direcciones IP Permitidas')
        }
        help_texts = {
            'session_timeout_minutes': _('Tiempo antes de cerrar sesión automáticamente (30-1440 minutos)'),
            'suspicious_activity_alerts': _('Recibir alertas por email cuando se detecte actividad inusual'),
            'allowed_ip_addresses': _('Una IP por línea. Use * como comodín (ej: 192.168.1.*)')
        }
    
    def __init__(self, *args, **kwargs):
        """Inicializa el formulario con configuraciones actuales."""
        self.agent = kwargs.pop('agent', None)
        super().__init__(*args, **kwargs)
        
        # Verificar si 2FA está habilitado
        if self.agent and hasattr(self.agent, 'profile'):
            try:
                profile = self.agent.profile
                self.fields['enable_2fa'].initial = profile.two_factor_enabled
            except:
                self.fields['enable_2fa'].initial = False
    
    def clean_session_timeout_minutes(self):
        """
        Valida el timeout de sesión.
        
        Returns:
            int: Timeout validado
        """
        timeout = self.cleaned_data.get('session_timeout_minutes')
        if timeout and (timeout < 30 or timeout > 1440):
            raise ValidationError(_('El timeout debe estar entre 30 y 1440 minutos'))
        return timeout
    
    def clean_allowed_ip_addresses(self):
        """
        Valida las direcciones IP permitidas.
        
        Returns:
            list: Lista de IPs validadas
        """
        ips_text = self.cleaned_data.get('allowed_ip_addresses')
        if not ips_text:
            return []
        
        # Convertir texto a lista
        ip_list = []
        for line in ips_text.strip().split('\n'):
            ip = line.strip()
            if ip:
                # Validación básica de formato IP
                if not self._is_valid_ip_pattern(ip):
                    raise ValidationError(
                        _('Formato de IP inválido: %(ip)s'),
                        params={'ip': ip}
                    )
                ip_list.append(ip)
        
        return ip_list
    
    def _is_valid_ip_pattern(self, ip):
        """
        Valida el patrón de una dirección IP.
        
        Args:
            ip: Dirección IP a validar
            
        Returns:
            bool: True si es válida
        """
        # Patrón básico para IP con wildcards
        pattern = r'^(\d{1,3}|\*)\.(\d{1,3}|\*)\.(\d{1,3}|\*)\.(\d{1,3}|\*)$'
        if not re.match(pattern, ip):
            return False
        
        # Validar que los números estén en rango válido
        parts = ip.split('.')
        for part in parts:
            if part != '*':
                try:
                    num = int(part)
                    if num < 0 or num > 255:
                        return False
                except ValueError:
                    return False
        
        return True


class PasswordResetRequestForm(forms.Form):
    """
    Formulario para solicitar recuperación de contraseña.
    """
    email = forms.EmailField(
        label=_('Email'),
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email',
            'autocomplete': 'email'
        }),
        help_text=_('Ingrese el email asociado a su cuenta')
    )
    
    def clean_email(self):
        """
        Valida que el email exista en el sistema.
        
        Returns:
            str: Email validado
        """
        email = self.cleaned_data.get('email')
        if email:
            try:
                Agent.objects.get(email=email, is_active=True)
            except Agent.DoesNotExist:
                # Por seguridad, no revelar si el email existe o no
                pass
        return email


class PasswordResetForm(SetPasswordForm):
    """
    Formulario para establecer nueva contraseña con token.
    """
    new_password1 = forms.CharField(
        label=_('Nueva Contraseña'),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nueva contraseña',
            'autocomplete': 'new-password'
        }),
        help_text=_('Mínimo 8 caracteres, debe incluir letras y números')
    )
    
    new_password2 = forms.CharField(
        label=_('Confirmar Contraseña'),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirmar contraseña',
            'autocomplete': 'new-password'
        })
    )
    
    def clean_new_password1(self):
        """
        Valida la nueva contraseña con las políticas de seguridad.
        
        Returns:
            str: Contraseña validada
        """
        password = self.cleaned_data.get('new_password1')
        if password:
            validate_password(password, self.user)
        return password


class EnhancedPasswordChangeForm(PasswordChangeForm):
    """
    Formulario mejorado para cambio de contraseña.
    """
    old_password = forms.CharField(
        label=_('Contraseña Actual'),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Contraseña actual',
            'autocomplete': 'current-password'
        })
    )
    
    new_password1 = forms.CharField(
        label=_('Nueva Contraseña'),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nueva contraseña',
            'autocomplete': 'new-password'
        }),
        help_text=_('Mínimo 8 caracteres, debe incluir letras y números')
    )
    
    new_password2 = forms.CharField(
        label=_('Confirmar Nueva Contraseña'),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirmar nueva contraseña',
            'autocomplete': 'new-password'
        })
    )


# Mantener formularios legacy para compatibilidad
class AgentLoginForm(AuthenticationForm):
    """Formulario de login legacy - usar EnhancedLoginForm para nuevas implementaciones"""
    username = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Contraseña'})
    )


class AgentForm(forms.ModelForm):
    """Formulario de agente legacy - usar ProfileUpdateForm para nuevas implementaciones"""
    class Meta:
        model = Agent
        fields = ['first_name', 'last_name', 'email', 'phone', 'license_number', 'bio', 'image_path']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'license_number': forms.TextInput(attrs={'class': 'form-control'}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'image_path': forms.FileInput(attrs={'class': 'form-control'}),
        }
