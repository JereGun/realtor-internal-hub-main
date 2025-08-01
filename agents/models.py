
from django.contrib.auth.models import AbstractUser
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
import json
import secrets
from core.models import BaseModel


class Agent(AbstractUser, BaseModel):
    """
    Modelo de Agente que extiende el modelo de Usuario de Django.
    
    Representa a los agentes inmobiliarios del sistema con información
    personal y profesional como número de licencia, biografía e imagen.
    Utiliza el email como campo de autenticación principal.
    """
    first_name = models.CharField(max_length=150, verbose_name="Nombre")
    last_name = models.CharField(max_length=150, verbose_name="Apellido")
    email = models.EmailField(unique=True, verbose_name="Email")
    phone = models.CharField(max_length=20, blank=True, verbose_name="Teléfono")
    license_number = models.CharField(max_length=50, unique=True, verbose_name="Número de Matrícula")
    is_active = models.BooleanField(default=True, verbose_name="Activo")
    image_path = models.ImageField(upload_to='agents/', blank=True, null=True, verbose_name="Foto de Perfil")
    bio = models.TextField(blank=True, verbose_name="Biografía")
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']
    
    class Meta:
        verbose_name = "Agente"
        verbose_name_plural = "Agentes"
    
    def __str__(self):
        return f"{self.first_name} {self.last_name}"
    
    @property
    def full_name(self):
        """
        Propiedad que devuelve el nombre completo del agente.
        
        Returns:
            str: Nombre y apellido concatenados del agente.
        """
        return f"{self.first_name} {self.last_name}"
    
    def get_full_name(self):
        """
        Método para obtener el nombre completo del agente - compatible con el modelo User de Django.
        
        Este método sobrescribe el método get_full_name de AbstractUser para proporcionar
        una implementación consistente con el resto del sistema.
        
        Returns:
            str: Nombre completo del agente (nombre y apellido concatenados).
        """
        return f"{self.first_name} {self.last_name}".strip()


class UserProfile(BaseModel):
    """
    Perfil extendido del usuario con información adicional.
    
    Almacena configuraciones personales, preferencias y datos
    adicionales del perfil que no están en el modelo Agent base.
    """
    agent = models.OneToOneField(Agent, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True, verbose_name="Avatar")
    timezone = models.CharField(max_length=50, default='America/Argentina/Buenos_Aires', verbose_name="Zona Horaria")
    language = models.CharField(max_length=5, default='es', verbose_name="Idioma")
    theme = models.CharField(max_length=20, default='light', choices=[
        ('light', 'Claro'),
        ('dark', 'Oscuro'),
        ('auto', 'Automático')
    ], verbose_name="Tema")
    email_verified = models.BooleanField(default=False, verbose_name="Email Verificado")
    email_verification_token = models.CharField(max_length=255, null=True, blank=True)
    phone_verified = models.BooleanField(default=False, verbose_name="Teléfono Verificado")
    two_factor_enabled = models.BooleanField(default=False, verbose_name="2FA Habilitado")
    two_factor_secret = models.CharField(max_length=32, null=True, blank=True)
    backup_codes = models.JSONField(default=list, verbose_name="Códigos de Respaldo")
    profile_completion = models.IntegerField(default=0, verbose_name="Completitud del Perfil (%)")
    last_profile_update = models.DateTimeField(auto_now=True, verbose_name="Última Actualización")
    password_reset_token = models.CharField(max_length=255, null=True, blank=True, verbose_name="Token de Reset")
    password_reset_expires = models.DateTimeField(null=True, blank=True, verbose_name="Expira Token Reset")
    
    class Meta:
        verbose_name = "Perfil de Usuario"
        verbose_name_plural = "Perfiles de Usuario"
    
    def __str__(self):
        return f"Perfil de {self.agent.get_full_name()}"
    
    def generate_email_verification_token(self):
        """Genera un token único para verificación de email"""
        self.email_verification_token = secrets.token_urlsafe(32)
        self.save()
        return self.email_verification_token
    
    def generate_backup_codes(self, count=10):
        """Genera códigos de respaldo para 2FA"""
        codes = [secrets.token_hex(4).upper() for _ in range(count)]
        self.backup_codes = codes
        self.save()
        return codes
    
    def use_backup_code(self, code):
        """Usa un código de respaldo y lo elimina de la lista"""
        if code.upper() in self.backup_codes:
            self.backup_codes.remove(code.upper())
            self.save()
            return True
        return False


class Role(BaseModel):
    """
    Roles del sistema con permisos asociados.
    
    Define los diferentes roles que pueden tener los usuarios
    y los permisos asociados a cada rol.
    """
    name = models.CharField(max_length=50, unique=True, verbose_name="Nombre")
    description = models.TextField(blank=True, verbose_name="Descripción")
    permissions = models.ManyToManyField('Permission', blank=True, verbose_name="Permisos")
    is_system_role = models.BooleanField(default=False, verbose_name="Rol del Sistema")
    agents = models.ManyToManyField(Agent, through='AgentRole', through_fields=('role', 'agent'), related_name='roles')
    
    class Meta:
        verbose_name = "Rol"
        verbose_name_plural = "Roles"
    
    def __str__(self):
        return self.name
    
    def add_permission(self, permission):
        """Añade un permiso al rol"""
        self.permissions.add(permission)
    
    def remove_permission(self, permission):
        """Elimina un permiso del rol"""
        self.permissions.remove(permission)
    
    def has_permission(self, permission_codename):
        """Verifica si el rol tiene un permiso específico"""
        return self.permissions.filter(codename=permission_codename).exists()


class Permission(BaseModel):
    """
    Permisos granulares del sistema.
    
    Define permisos específicos que pueden ser asignados a roles
    para controlar el acceso a diferentes funcionalidades.
    """
    codename = models.CharField(max_length=100, unique=True, verbose_name="Código")
    name = models.CharField(max_length=255, verbose_name="Nombre")
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, verbose_name="Tipo de Contenido", related_name='custom_permissions')
    description = models.TextField(blank=True, verbose_name="Descripción")
    
    class Meta:
        verbose_name = "Permiso"
        verbose_name_plural = "Permisos"
        unique_together = ['content_type', 'codename']
    
    def __str__(self):
        return f"{self.content_type.name} | {self.name}"


class AgentRole(BaseModel):
    """
    Relación entre Agent y Role con información adicional.
    
    Permite asignar roles a usuarios con fechas de asignación
    y información adicional sobre la asignación.
    """
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE)
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    assigned_by = models.ForeignKey(Agent, on_delete=models.SET_NULL, null=True, related_name='role_assignments_made')
    assigned_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Asignación de Rol"
        verbose_name_plural = "Asignaciones de Roles"
        unique_together = ['agent', 'role']
    
    def __str__(self):
        return f"{self.agent.get_full_name()} - {self.role.name}"


class UserSession(BaseModel):
    """
    Gestión avanzada de sesiones de usuario.
    
    Almacena información detallada sobre las sesiones activas
    de los usuarios para control y auditoría.
    """
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name='sessions')
    session_key = models.CharField(max_length=40, unique=True, verbose_name="Clave de Sesión")
    ip_address = models.GenericIPAddressField(verbose_name="Dirección IP")
    user_agent = models.TextField(verbose_name="User Agent")
    device_info = models.JSONField(default=dict, verbose_name="Información del Dispositivo")
    location = models.JSONField(default=dict, verbose_name="Ubicación")
    is_active = models.BooleanField(default=True, verbose_name="Activa")
    last_activity = models.DateTimeField(auto_now=True, verbose_name="Última Actividad")
    expires_at = models.DateTimeField(verbose_name="Expira en")
    
    class Meta:
        verbose_name = "Sesión de Usuario"
        verbose_name_plural = "Sesiones de Usuario"
        ordering = ['-last_activity']
    
    def __str__(self):
        return f"Sesión de {self.agent.get_full_name()} - {self.ip_address}"
    
    def is_expired(self):
        """Verifica si la sesión ha expirado"""
        return timezone.now() > self.expires_at
    
    def extend_session(self, minutes=480):
        """Extiende la duración de la sesión"""
        self.expires_at = timezone.now() + timezone.timedelta(minutes=minutes)
        self.save()
    
    def terminate(self):
        """Termina la sesión"""
        self.is_active = False
        self.save()


class SecuritySettings(BaseModel):
    """
    Configuraciones de seguridad por usuario.
    
    Almacena configuraciones específicas de seguridad para cada usuario,
    incluyendo políticas de contraseña y configuraciones de sesión.
    """
    agent = models.OneToOneField(Agent, on_delete=models.CASCADE, related_name='security_settings')
    login_attempts = models.IntegerField(default=0, verbose_name="Intentos de Login")
    locked_until = models.DateTimeField(null=True, blank=True, verbose_name="Bloqueado Hasta")
    password_changed_at = models.DateTimeField(auto_now_add=True, verbose_name="Contraseña Cambiada")
    require_password_change = models.BooleanField(default=False, verbose_name="Requiere Cambio de Contraseña")
    allowed_ip_addresses = models.JSONField(default=list, verbose_name="IPs Permitidas")
    suspicious_activity_alerts = models.BooleanField(default=True, verbose_name="Alertas de Actividad Sospechosa")
    session_timeout_minutes = models.IntegerField(default=480, verbose_name="Timeout de Sesión (minutos)")
    last_password_reset = models.DateTimeField(null=True, blank=True, verbose_name="Último Reset de Contraseña")
    
    class Meta:
        verbose_name = "Configuración de Seguridad"
        verbose_name_plural = "Configuraciones de Seguridad"
    
    def __str__(self):
        return f"Seguridad de {self.agent.get_full_name()}"
    
    def is_locked(self):
        """Verifica si la cuenta está bloqueada"""
        if self.locked_until:
            return timezone.now() < self.locked_until
        return False
    
    def lock_account(self, minutes=15):
        """Bloquea la cuenta por un tiempo determinado"""
        self.locked_until = timezone.now() + timezone.timedelta(minutes=minutes)
        self.save()
    
    def unlock_account(self):
        """Desbloquea la cuenta"""
        self.locked_until = None
        self.login_attempts = 0
        self.save()
    
    def increment_login_attempts(self):
        """Incrementa el contador de intentos fallidos"""
        self.login_attempts += 1
        if self.login_attempts >= 3:
            self.lock_account()
        self.save()
    
    def reset_login_attempts(self):
        """Resetea el contador de intentos fallidos"""
        self.login_attempts = 0
        self.save()


class AuditLog(BaseModel):
    """
    Log de auditoría para acciones de usuario.
    
    Registra todas las acciones importantes realizadas por los usuarios
    para auditoría y seguimiento de seguridad.
    """
    ACTION_CHOICES = [
        ('login', 'Inicio de Sesión'),
        ('logout', 'Cierre de Sesión'),
        ('password_change', 'Cambio de Contraseña'),
        ('profile_update', 'Actualización de Perfil'),
        ('role_assigned', 'Rol Asignado'),
        ('permission_granted', 'Permiso Otorgado'),
        ('data_export', 'Exportación de Datos'),
        ('security_settings_change', 'Cambio de Configuración de Seguridad'),
        ('suspicious_activity', 'Actividad Sospechosa'),
        ('account_locked', 'Cuenta Bloqueada'),
        ('account_unlocked', 'Cuenta Desbloqueada'),
        ('2fa_enabled', '2FA Habilitado'),
        ('2fa_disabled', '2FA Deshabilitado'),
    ]
    
    agent = models.ForeignKey(Agent, on_delete=models.SET_NULL, null=True, verbose_name="Usuario")
    action = models.CharField(max_length=100, choices=ACTION_CHOICES, verbose_name="Acción")
    resource_type = models.CharField(max_length=50, verbose_name="Tipo de Recurso")
    resource_id = models.CharField(max_length=50, null=True, blank=True, verbose_name="ID del Recurso")
    ip_address = models.GenericIPAddressField(verbose_name="Dirección IP")
    user_agent = models.TextField(verbose_name="User Agent")
    details = models.JSONField(default=dict, verbose_name="Detalles")
    success = models.BooleanField(default=True, verbose_name="Exitoso")
    session_key = models.CharField(max_length=40, null=True, blank=True, verbose_name="Clave de Sesión")
    
    class Meta:
        verbose_name = "Log de Auditoría"
        verbose_name_plural = "Logs de Auditoría"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['agent', 'action']),
            models.Index(fields=['created_at']),
            models.Index(fields=['ip_address']),
        ]
    
    def __str__(self):
        agent_name = self.agent.get_full_name() if self.agent else "Usuario Desconocido"
        return f"{agent_name} - {self.get_action_display()} - {self.created_at}"