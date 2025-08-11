"""
Mixins personalizados para control de permisos y roles en vistas basadas en clases.

Este módulo proporciona mixins que pueden ser utilizados con vistas basadas en clases
para verificar permisos, roles y otros requisitos de autorización.
"""

import logging
from typing import Union, List, Optional
from django.contrib.auth.mixins import AccessMixin
from django.core.exceptions import PermissionDenied
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.http import HttpRequest, HttpResponse

from agents.models import Agent
from agents.services.role_permission_service import RolePermissionService


logger = logging.getLogger(__name__)


class PermissionRequiredMixin(AccessMixin):
    """
    Mixin que verifica permisos específicos para vistas basadas en clases.
    
    Attributes:
        permission_required: Permiso o lista de permisos requeridos
        raise_exception: Si True, lanza PermissionDenied en lugar de redirigir
        permission_denied_message: Mensaje personalizado cuando se deniega el acceso
        redirect_url: URL específica de redirección si no tiene permisos
        
    Example:
        class PropertyListView(PermissionRequiredMixin, ListView):
            permission_required = 'view_property'
            model = Property
            
        class PropertyEditView(PermissionRequiredMixin, UpdateView):
            permission_required = ['change_property', 'view_property']
            model = Property
    """
    permission_required: Union[str, List[str]] = None
    raise_exception: bool = False
    permission_denied_message: str = None
    redirect_url: str = None
    
    def get_permission_required(self) -> List[str]:
        """
        Obtiene la lista de permisos requeridos.
        
        Returns:
            List[str]: Lista de permisos requeridos
        """
        if self.permission_required is None:
            raise ValueError(
                f"{self.__class__.__name__} debe definir 'permission_required'"
            )
        
        if isinstance(self.permission_required, str):
            return [self.permission_required]
        
        return list(self.permission_required)
    
    def get_permission_denied_message(self) -> str:
        """
        Obtiene el mensaje de permiso denegado.
        
        Returns:
            str: Mensaje de error personalizado
        """
        if self.permission_denied_message:
            return self.permission_denied_message
        
        permissions = self.get_permission_required()
        return f"No tienes permisos para realizar esta acción. Permisos requeridos: {', '.join(permissions)}"
    
    def has_permission(self) -> bool:
        """
        Verifica si el usuario tiene los permisos requeridos.
        
        Returns:
            bool: True si tiene todos los permisos requeridos
        """
        if not isinstance(self.request.user, Agent):
            return False
        
        role_service = RolePermissionService()
        permissions = self.get_permission_required()
        
        for permission in permissions:
            if not role_service.check_permission(self.request.user, permission):
                return False
        
        return True
    
    def dispatch(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """
        Verifica permisos antes de procesar la vista.
        
        Args:
            request: Objeto HttpRequest
            *args: Argumentos posicionales
            **kwargs: Argumentos de palabra clave
            
        Returns:
            HttpResponse: Respuesta de la vista o redirección
        """
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        
        if not isinstance(request.user, Agent):
            logger.warning(f"Usuario {request.user} no es un Agent")
            messages.error(request, "Usuario no válido")
            return redirect('agents:agent_login')
        
        if not self.has_permission():
            permissions = self.get_permission_required()
            logger.warning(
                f"Usuario {request.user.email} no tiene permisos: {permissions}"
            )
            
            if self.raise_exception:
                raise PermissionDenied(self.get_permission_denied_message())
            
            messages.error(request, self.get_permission_denied_message())
            
            if self.redirect_url:
                return redirect(self.redirect_url)
            
            return redirect('core:dashboard')
        
        return super().dispatch(request, *args, **kwargs)


class RoleRequiredMixin(AccessMixin):
    """
    Mixin que verifica roles específicos para vistas basadas en clases.
    
    Attributes:
        role_required: Rol o lista de roles requeridos
        raise_exception: Si True, lanza PermissionDenied en lugar de redirigir
        role_denied_message: Mensaje personalizado cuando se deniega el acceso
        redirect_url: URL específica de redirección si no tiene el rol
        
    Example:
        class AdminPanelView(RoleRequiredMixin, TemplateView):
            role_required = 'Administrador'
            template_name = 'admin/panel.html'
            
        class SupervisorReportsView(RoleRequiredMixin, ListView):
            role_required = ['Supervisor', 'Administrador']
            model = Report
    """
    role_required: Union[str, List[str]] = None
    raise_exception: bool = False
    role_denied_message: str = None
    redirect_url: str = None
    
    def get_role_required(self) -> List[str]:
        """
        Obtiene la lista de roles requeridos.
        
        Returns:
            List[str]: Lista de roles requeridos
        """
        if self.role_required is None:
            raise ValueError(
                f"{self.__class__.__name__} debe definir 'role_required'"
            )
        
        if isinstance(self.role_required, str):
            return [self.role_required]
        
        return list(self.role_required)
    
    def get_role_denied_message(self) -> str:
        """
        Obtiene el mensaje de rol denegado.
        
        Returns:
            str: Mensaje de error personalizado
        """
        if self.role_denied_message:
            return self.role_denied_message
        
        roles = self.get_role_required()
        return f"No tienes el rol necesario para acceder a esta sección. Roles requeridos: {', '.join(roles)}"
    
    def has_role(self) -> bool:
        """
        Verifica si el usuario tiene alguno de los roles requeridos.
        
        Returns:
            bool: True si tiene al menos uno de los roles requeridos
        """
        if not isinstance(self.request.user, Agent):
            return False
        
        role_service = RolePermissionService()
        user_roles = role_service.get_user_roles(self.request.user)
        user_role_names = [r.name for r in user_roles]
        
        required_roles = self.get_role_required()
        
        return any(role_name in user_role_names for role_name in required_roles)
    
    def dispatch(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """
        Verifica roles antes de procesar la vista.
        
        Args:
            request: Objeto HttpRequest
            *args: Argumentos posicionales
            **kwargs: Argumentos de palabra clave
            
        Returns:
            HttpResponse: Respuesta de la vista o redirección
        """
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        
        if not isinstance(request.user, Agent):
            logger.warning(f"Usuario {request.user} no es un Agent")
            messages.error(request, "Usuario no válido")
            return redirect('agents:agent_login')
        
        if not self.has_role():
            required_roles = self.get_role_required()
            logger.warning(
                f"Usuario {request.user.email} no tiene roles requeridos: {required_roles}"
            )
            
            if self.raise_exception:
                raise PermissionDenied(self.get_role_denied_message())
            
            messages.error(request, self.get_role_denied_message())
            
            if self.redirect_url:
                return redirect(self.redirect_url)
            
            return redirect('core:dashboard')
        
        return super().dispatch(request, *args, **kwargs)


class SuperuserRequiredMixin(AccessMixin):
    """
    Mixin que verifica que el usuario sea superusuario.
    
    Attributes:
        raise_exception: Si True, lanza PermissionDenied en lugar de redirigir
        superuser_denied_message: Mensaje personalizado cuando se deniega el acceso
        redirect_url: URL específica de redirección si no es superusuario
        
    Example:
        class SystemSettingsView(SuperuserRequiredMixin, TemplateView):
            template_name = 'admin/system_settings.html'
    """
    raise_exception: bool = False
    superuser_denied_message: str = "Se requieren privilegios de superusuario"
    redirect_url: str = None
    
    def dispatch(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """
        Verifica superusuario antes de procesar la vista.
        
        Args:
            request: Objeto HttpRequest
            *args: Argumentos posicionales
            **kwargs: Argumentos de palabra clave
            
        Returns:
            HttpResponse: Respuesta de la vista o redirección
        """
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        
        if not request.user.is_superuser:
            logger.warning(f"Usuario {request.user.email} no es superusuario")
            
            if self.raise_exception:
                raise PermissionDenied(self.superuser_denied_message)
            
            messages.error(request, self.superuser_denied_message)
            
            if self.redirect_url:
                return redirect(self.redirect_url)
            
            return redirect('core:dashboard')
        
        return super().dispatch(request, *args, **kwargs)


class StaffRequiredMixin(AccessMixin):
    """
    Mixin que verifica que el usuario sea staff.
    
    Attributes:
        raise_exception: Si True, lanza PermissionDenied en lugar de redirigir
        staff_denied_message: Mensaje personalizado cuando se deniega el acceso
        redirect_url: URL específica de redirección si no es staff
        
    Example:
        class AdminDashboardView(StaffRequiredMixin, TemplateView):
            template_name = 'admin/dashboard.html'
    """
    raise_exception: bool = False
    staff_denied_message: str = "Se requieren privilegios de staff"
    redirect_url: str = None
    
    def dispatch(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """
        Verifica staff antes de procesar la vista.
        
        Args:
            request: Objeto HttpRequest
            *args: Argumentos posicionales
            **kwargs: Argumentos de palabra clave
            
        Returns:
            HttpResponse: Respuesta de la vista o redirección
        """
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        
        if not request.user.is_staff:
            logger.warning(f"Usuario {request.user.email} no es staff")
            
            if self.raise_exception:
                raise PermissionDenied(self.staff_denied_message)
            
            messages.error(request, self.staff_denied_message)
            
            if self.redirect_url:
                return redirect(self.redirect_url)
            
            return redirect('core:dashboard')
        
        return super().dispatch(request, *args, **kwargs)


class AdminRequiredMixin(AccessMixin):
    """
    Mixin combinado que verifica rol de Administrador o superusuario.
    
    Attributes:
        raise_exception: Si True, lanza PermissionDenied en lugar de redirigir
        admin_denied_message: Mensaje personalizado cuando se deniega el acceso
        redirect_url: URL específica de redirección si no tiene acceso
        
    Example:
        class AdminPanelView(AdminRequiredMixin, TemplateView):
            template_name = 'admin/panel.html'
    """
    raise_exception: bool = False
    admin_denied_message: str = "No tienes permisos de administrador para acceder a esta sección"
    redirect_url: str = None
    
    def has_admin_access(self) -> bool:
        """
        Verifica si el usuario tiene acceso de administrador.
        
        Returns:
            bool: True si es superusuario o tiene rol de Administrador
        """
        # Verificar superusuario primero
        if self.request.user.is_superuser:
            return True
        
        # Verificar que sea un Agent
        if not isinstance(self.request.user, Agent):
            return False
        
        # Verificar rol de Administrador
        role_service = RolePermissionService()
        user_roles = role_service.get_user_roles(self.request.user)
        user_role_names = [r.name for r in user_roles]
        
        return 'Administrador' in user_role_names
    
    def dispatch(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """
        Verifica acceso de administrador antes de procesar la vista.
        
        Args:
            request: Objeto HttpRequest
            *args: Argumentos posicionales
            **kwargs: Argumentos de palabra clave
            
        Returns:
            HttpResponse: Respuesta de la vista o redirección
        """
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        
        if not self.has_admin_access():
            logger.warning(f"Usuario {request.user.email} no tiene acceso de administrador")
            
            if self.raise_exception:
                raise PermissionDenied(self.admin_denied_message)
            
            messages.error(request, self.admin_denied_message)
            
            if self.redirect_url:
                return redirect(self.redirect_url)
            
            return redirect('core:dashboard')
        
        return super().dispatch(request, *args, **kwargs)


class SupervisorOrAdminRequiredMixin(AccessMixin):
    """
    Mixin que verifica rol de Supervisor, Administrador o superusuario.
    
    Attributes:
        raise_exception: Si True, lanza PermissionDenied en lugar de redirigir
        supervisor_denied_message: Mensaje personalizado cuando se deniega el acceso
        redirect_url: URL específica de redirección si no tiene acceso
        
    Example:
        class SupervisorReportsView(SupervisorOrAdminRequiredMixin, ListView):
            model = Report
            template_name = 'reports/supervisor.html'
    """
    raise_exception: bool = False
    supervisor_denied_message: str = "No tienes permisos de supervisor o administrador para acceder a esta sección"
    redirect_url: str = None
    
    def has_supervisor_access(self) -> bool:
        """
        Verifica si el usuario tiene acceso de supervisor o administrador.
        
        Returns:
            bool: True si es superusuario o tiene rol de Supervisor/Administrador
        """
        # Verificar superusuario primero
        if self.request.user.is_superuser:
            return True
        
        # Verificar que sea un Agent
        if not isinstance(self.request.user, Agent):
            return False
        
        # Verificar roles de Supervisor o Administrador
        role_service = RolePermissionService()
        user_roles = role_service.get_user_roles(self.request.user)
        user_role_names = [r.name for r in user_roles]
        
        allowed_roles = ['Supervisor', 'Administrador']
        return any(role_name in user_role_names for role_name in allowed_roles)
    
    def dispatch(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """
        Verifica acceso de supervisor o administrador antes de procesar la vista.
        
        Args:
            request: Objeto HttpRequest
            *args: Argumentos posicionales
            **kwargs: Argumentos de palabra clave
            
        Returns:
            HttpResponse: Respuesta de la vista o redirección
        """
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        
        if not self.has_supervisor_access():
            logger.warning(f"Usuario {request.user.email} no tiene acceso de supervisor o administrador")
            
            if self.raise_exception:
                raise PermissionDenied(self.supervisor_denied_message)
            
            messages.error(request, self.supervisor_denied_message)
            
            if self.redirect_url:
                return redirect(self.redirect_url)
            
            return redirect('core:dashboard')
        
        return super().dispatch(request, *args, **kwargs)


class OwnerRequiredMixin(AccessMixin):
    """
    Mixin que verifica que el usuario sea el propietario del objeto.
    
    Attributes:
        owner_field: Campo que identifica al propietario (por defecto 'agent')
        raise_exception: Si True, lanza PermissionDenied en lugar de redirigir
        owner_denied_message: Mensaje personalizado cuando se deniega el acceso
        redirect_url: URL específica de redirección si no es propietario
        allow_admin_access: Si True, permite acceso a administradores
        
    Example:
        class PropertyUpdateView(OwnerRequiredMixin, UpdateView):
            model = Property
            owner_field = 'agent'
            allow_admin_access = True
    """
    owner_field: str = 'agent'
    raise_exception: bool = False
    owner_denied_message: str = "Solo puedes acceder a tus propios recursos"
    redirect_url: str = None
    allow_admin_access: bool = True
    
    def get_owner_field(self) -> str:
        """
        Obtiene el campo que identifica al propietario.
        
        Returns:
            str: Nombre del campo propietario
        """
        return self.owner_field
    
    def is_owner(self, obj) -> bool:
        """
        Verifica si el usuario es propietario del objeto.
        
        Args:
            obj: Objeto a verificar
            
        Returns:
            bool: True si es propietario
        """
        if not isinstance(self.request.user, Agent):
            return False
        
        owner_field = self.get_owner_field()
        
        try:
            owner = getattr(obj, owner_field)
            return owner == self.request.user
        except AttributeError:
            logger.error(f"Campo propietario '{owner_field}' no encontrado en {obj.__class__.__name__}")
            return False
    
    def has_admin_access(self) -> bool:
        """
        Verifica si el usuario tiene acceso de administrador.
        
        Returns:
            bool: True si tiene acceso de administrador
        """
        if not self.allow_admin_access:
            return False
        
        # Verificar superusuario
        if self.request.user.is_superuser:
            return True
        
        # Verificar que sea un Agent
        if not isinstance(self.request.user, Agent):
            return False
        
        # Verificar rol de Administrador
        role_service = RolePermissionService()
        user_roles = role_service.get_user_roles(self.request.user)
        user_role_names = [r.name for r in user_roles]
        
        return 'Administrador' in user_role_names
    
    def dispatch(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """
        Verifica propiedad antes de procesar la vista.
        
        Args:
            request: Objeto HttpRequest
            *args: Argumentos posicionales
            **kwargs: Argumentos de palabra clave
            
        Returns:
            HttpResponse: Respuesta de la vista o redirección
        """
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        
        # Obtener el objeto
        obj = self.get_object()
        
        # Verificar si es propietario o tiene acceso de administrador
        if not (self.is_owner(obj) or self.has_admin_access()):
            logger.warning(
                f"Usuario {request.user.email} no es propietario de {obj.__class__.__name__} {obj.pk}"
            )
            
            if self.raise_exception:
                raise PermissionDenied(self.owner_denied_message)
            
            messages.error(request, self.owner_denied_message)
            
            if self.redirect_url:
                return redirect(self.redirect_url)
            
            return redirect('core:dashboard')
        
        return super().dispatch(request, *args, **kwargs)