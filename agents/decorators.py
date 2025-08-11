"""
Decoradores personalizados para control de permisos y roles.

Este módulo proporciona decoradores para verificar permisos y roles
en vistas basadas en funciones y mixins para vistas basadas en clases.
"""

import logging
from functools import wraps
from typing import Union, List, Callable, Any
from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.generic import View
from django.contrib.auth.mixins import AccessMixin

from agents.models import Agent
from agents.services.role_permission_service import RolePermissionService


logger = logging.getLogger(__name__)


def permission_required(
    permission: Union[str, List[str]], 
    login_url: str = None,
    raise_exception: bool = False,
    redirect_url: str = None
):
    """
    Decorador personalizado para verificar permisos específicos.
    
    Args:
        permission: Permiso o lista de permisos requeridos
        login_url: URL de redirección si no está autenticado
        raise_exception: Si True, lanza PermissionDenied en lugar de redirigir
        redirect_url: URL específica de redirección si no tiene permisos
        
    Returns:
        Decorador que verifica los permisos
        
    Example:
        @permission_required('view_property')
        def property_list(request):
            return render(request, 'properties/list.html')
            
        @permission_required(['add_property', 'change_property'])
        def property_edit(request):
            return render(request, 'properties/edit.html')
    """
    def decorator(view_func: Callable) -> Callable:
        @wraps(view_func)
        def wrapper(request: HttpRequest, *args, **kwargs) -> HttpResponse:
            # Verificar autenticación
            if not request.user.is_authenticated:
                if login_url:
                    return redirect(login_url)
                return redirect('agents:agent_login')
            
            # Verificar que sea un Agent
            if not isinstance(request.user, Agent):
                logger.warning(f"Usuario {request.user} no es un Agent")
                if raise_exception:
                    raise PermissionDenied("Usuario no válido")
                messages.error(request, "Usuario no válido")
                return redirect('agents:agent_login')
            
            # Verificar permisos
            role_service = RolePermissionService()
            permissions_to_check = permission if isinstance(permission, list) else [permission]
            
            has_permission = True
            missing_permissions = []
            
            for perm in permissions_to_check:
                if not role_service.check_permission(request.user, perm):
                    has_permission = False
                    missing_permissions.append(perm)
            
            if not has_permission:
                logger.warning(
                    f"Usuario {request.user.email} no tiene permisos: {missing_permissions}"
                )
                
                if raise_exception:
                    raise PermissionDenied(f"Permisos requeridos: {', '.join(missing_permissions)}")
                
                messages.error(
                    request, 
                    f"No tienes permisos para realizar esta acción. Permisos requeridos: {', '.join(missing_permissions)}"
                )
                
                if redirect_url:
                    return redirect(redirect_url)
                
                # Redirigir al dashboard por defecto
                return redirect('core:dashboard')
            
            return view_func(request, *args, **kwargs)
        
        return wrapper
    return decorator


def role_required(
    role: Union[str, List[str]], 
    login_url: str = None,
    raise_exception: bool = False,
    redirect_url: str = None
):
    """
    Decorador personalizado para verificar roles específicos.
    
    Args:
        role: Rol o lista de roles requeridos
        login_url: URL de redirección si no está autenticado
        raise_exception: Si True, lanza PermissionDenied en lugar de redirigir
        redirect_url: URL específica de redirección si no tiene el rol
        
    Returns:
        Decorador que verifica los roles
        
    Example:
        @role_required('Administrador')
        def admin_panel(request):
            return render(request, 'admin/panel.html')
            
        @role_required(['Supervisor', 'Administrador'])
        def supervisor_reports(request):
            return render(request, 'reports/supervisor.html')
    """
    def decorator(view_func: Callable) -> Callable:
        @wraps(view_func)
        def wrapper(request: HttpRequest, *args, **kwargs) -> HttpResponse:
            # Verificar autenticación
            if not request.user.is_authenticated:
                if login_url:
                    return redirect(login_url)
                return redirect('agents:agent_login')
            
            # Verificar que sea un Agent
            if not isinstance(request.user, Agent):
                logger.warning(f"Usuario {request.user} no es un Agent")
                if raise_exception:
                    raise PermissionDenied("Usuario no válido")
                messages.error(request, "Usuario no válido")
                return redirect('agents:agent_login')
            
            # Verificar roles
            role_service = RolePermissionService()
            user_roles = role_service.get_user_roles(request.user)
            user_role_names = [r.name for r in user_roles]
            
            roles_to_check = role if isinstance(role, list) else [role]
            
            has_role = any(role_name in user_role_names for role_name in roles_to_check)
            
            if not has_role:
                logger.warning(
                    f"Usuario {request.user.email} no tiene roles requeridos: {roles_to_check}. "
                    f"Roles actuales: {user_role_names}"
                )
                
                if raise_exception:
                    raise PermissionDenied(f"Roles requeridos: {', '.join(roles_to_check)}")
                
                messages.error(
                    request, 
                    f"No tienes el rol necesario para acceder a esta sección. Roles requeridos: {', '.join(roles_to_check)}"
                )
                
                if redirect_url:
                    return redirect(redirect_url)
                
                # Redirigir al dashboard por defecto
                return redirect('core:dashboard')
            
            return view_func(request, *args, **kwargs)
        
        return wrapper
    return decorator


def superuser_required(
    login_url: str = None,
    raise_exception: bool = False,
    redirect_url: str = None
):
    """
    Decorador para verificar que el usuario sea superusuario.
    
    Args:
        login_url: URL de redirección si no está autenticado
        raise_exception: Si True, lanza PermissionDenied en lugar de redirigir
        redirect_url: URL específica de redirección si no es superusuario
        
    Returns:
        Decorador que verifica superusuario
        
    Example:
        @superuser_required
        def system_settings(request):
            return render(request, 'admin/system_settings.html')
    """
    def decorator(view_func: Callable) -> Callable:
        @wraps(view_func)
        def wrapper(request: HttpRequest, *args, **kwargs) -> HttpResponse:
            # Verificar autenticación
            if not request.user.is_authenticated:
                if login_url:
                    return redirect(login_url)
                return redirect('agents:agent_login')
            
            # Verificar superusuario
            if not request.user.is_superuser:
                logger.warning(f"Usuario {request.user.email} no es superusuario")
                
                if raise_exception:
                    raise PermissionDenied("Se requieren privilegios de superusuario")
                
                messages.error(request, "No tienes privilegios de superusuario para acceder a esta sección")
                
                if redirect_url:
                    return redirect(redirect_url)
                
                return redirect('core:dashboard')
            
            return view_func(request, *args, **kwargs)
        
        return wrapper
    return decorator


def staff_required(
    login_url: str = None,
    raise_exception: bool = False,
    redirect_url: str = None
):
    """
    Decorador para verificar que el usuario sea staff.
    
    Args:
        login_url: URL de redirección si no está autenticado
        raise_exception: Si True, lanza PermissionDenied en lugar de redirigir
        redirect_url: URL específica de redirección si no es staff
        
    Returns:
        Decorador que verifica staff
        
    Example:
        @staff_required
        def admin_dashboard(request):
            return render(request, 'admin/dashboard.html')
    """
    def decorator(view_func: Callable) -> Callable:
        @wraps(view_func)
        def wrapper(request: HttpRequest, *args, **kwargs) -> HttpResponse:
            # Verificar autenticación
            if not request.user.is_authenticated:
                if login_url:
                    return redirect(login_url)
                return redirect('agents:agent_login')
            
            # Verificar staff
            if not request.user.is_staff:
                logger.warning(f"Usuario {request.user.email} no es staff")
                
                if raise_exception:
                    raise PermissionDenied("Se requieren privilegios de staff")
                
                messages.error(request, "No tienes privilegios de staff para acceder a esta sección")
                
                if redirect_url:
                    return redirect(redirect_url)
                
                return redirect('core:dashboard')
            
            return view_func(request, *args, **kwargs)
        
        return wrapper
    return decorator


# Decoradores combinados para casos comunes
def admin_required(
    login_url: str = None,
    raise_exception: bool = False,
    redirect_url: str = None
):
    """
    Decorador combinado que verifica rol de Administrador o superusuario.
    
    Args:
        login_url: URL de redirección si no está autenticado
        raise_exception: Si True, lanza PermissionDenied en lugar de redirigir
        redirect_url: URL específica de redirección si no tiene acceso
        
    Returns:
        Decorador que verifica acceso de administrador
    """
    def decorator(view_func: Callable) -> Callable:
        @wraps(view_func)
        def wrapper(request: HttpRequest, *args, **kwargs) -> HttpResponse:
            # Verificar autenticación
            if not request.user.is_authenticated:
                if login_url:
                    return redirect(login_url)
                return redirect('agents:agent_login')
            
            # Verificar superusuario primero
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            
            # Verificar que sea un Agent
            if not isinstance(request.user, Agent):
                logger.warning(f"Usuario {request.user} no es un Agent")
                if raise_exception:
                    raise PermissionDenied("Usuario no válido")
                messages.error(request, "Usuario no válido")
                return redirect('agents:agent_login')
            
            # Verificar rol de Administrador
            role_service = RolePermissionService()
            user_roles = role_service.get_user_roles(request.user)
            user_role_names = [r.name for r in user_roles]
            
            if 'Administrador' not in user_role_names:
                logger.warning(
                    f"Usuario {request.user.email} no tiene rol de Administrador. "
                    f"Roles actuales: {user_role_names}"
                )
                
                if raise_exception:
                    raise PermissionDenied("Se requiere rol de Administrador")
                
                messages.error(request, "No tienes permisos de administrador para acceder a esta sección")
                
                if redirect_url:
                    return redirect(redirect_url)
                
                return redirect('core:dashboard')
            
            return view_func(request, *args, **kwargs)
        
        return wrapper
    return decorator


def supervisor_or_admin_required(
    login_url: str = None,
    raise_exception: bool = False,
    redirect_url: str = None
):
    """
    Decorador que verifica rol de Supervisor, Administrador o superusuario.
    
    Args:
        login_url: URL de redirección si no está autenticado
        raise_exception: Si True, lanza PermissionDenied en lugar de redirigir
        redirect_url: URL específica de redirección si no tiene acceso
        
    Returns:
        Decorador que verifica acceso de supervisor o administrador
    """
    def decorator(view_func: Callable) -> Callable:
        @wraps(view_func)
        def wrapper(request: HttpRequest, *args, **kwargs) -> HttpResponse:
            # Verificar autenticación
            if not request.user.is_authenticated:
                if login_url:
                    return redirect(login_url)
                return redirect('agents:agent_login')
            
            # Verificar superusuario primero
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            
            # Verificar que sea un Agent
            if not isinstance(request.user, Agent):
                logger.warning(f"Usuario {request.user} no es un Agent")
                if raise_exception:
                    raise PermissionDenied("Usuario no válido")
                messages.error(request, "Usuario no válido")
                return redirect('agents:agent_login')
            
            # Verificar roles de Supervisor o Administrador
            role_service = RolePermissionService()
            user_roles = role_service.get_user_roles(request.user)
            user_role_names = [r.name for r in user_roles]
            
            allowed_roles = ['Supervisor', 'Administrador']
            has_allowed_role = any(role_name in user_role_names for role_name in allowed_roles)
            
            if not has_allowed_role:
                logger.warning(
                    f"Usuario {request.user.email} no tiene roles de Supervisor o Administrador. "
                    f"Roles actuales: {user_role_names}"
                )
                
                if raise_exception:
                    raise PermissionDenied("Se requiere rol de Supervisor o Administrador")
                
                messages.error(request, "No tienes permisos de supervisor o administrador para acceder a esta sección")
                
                if redirect_url:
                    return redirect(redirect_url)
                
                return redirect('core:dashboard')
            
            return view_func(request, *args, **kwargs)
        
        return wrapper
    return decorator