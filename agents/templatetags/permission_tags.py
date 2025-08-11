"""
Template tags y filtros para verificación de permisos y roles.

Este módulo proporciona template tags y filtros que permiten verificar
permisos y roles directamente en las plantillas Django.
"""

import logging
from typing import Union, List, Any
from django import template
from django.contrib.auth.models import AnonymousUser
from django.template.context import RequestContext

from agents.models import Agent, Role
from agents.services.role_permission_service import RolePermissionService


logger = logging.getLogger(__name__)
register = template.Library()


@register.simple_tag(takes_context=True)
def has_permission(context, permission: str) -> bool:
    """
    Template tag para verificar si el usuario actual tiene un permiso específico.
    
    Args:
        context: Contexto del template
        permission: Código del permiso a verificar
        
    Returns:
        bool: True si el usuario tiene el permiso
        
    Example:
        {% load permission_tags %}
        {% has_permission 'view_property' as can_view %}
        {% if can_view %}
            <a href="{% url 'properties:list' %}">Ver Propiedades</a>
        {% endif %}
    """
    try:
        request = context.get('request')
        if not request or not hasattr(request, 'user'):
            return False
        
        user = request.user
        if not user.is_authenticated or not isinstance(user, Agent):
            return False
        
        role_service = RolePermissionService()
        return role_service.check_permission(user, permission)
        
    except Exception as e:
        logger.error(f"Error verificando permiso {permission}: {str(e)}")
        return False


@register.simple_tag(takes_context=True)
def has_any_permission(context, *permissions) -> bool:
    """
    Template tag para verificar si el usuario tiene al menos uno de los permisos especificados.
    
    Args:
        context: Contexto del template
        *permissions: Lista de permisos a verificar
        
    Returns:
        bool: True si el usuario tiene al menos uno de los permisos
        
    Example:
        {% load permission_tags %}
        {% has_any_permission 'add_property' 'change_property' as can_edit %}
        {% if can_edit %}
            <button>Editar</button>
        {% endif %}
    """
    try:
        request = context.get('request')
        if not request or not hasattr(request, 'user'):
            return False
        
        user = request.user
        if not user.is_authenticated or not isinstance(user, Agent):
            return False
        
        role_service = RolePermissionService()
        
        for permission in permissions:
            if role_service.check_permission(user, permission):
                return True
        
        return False
        
    except Exception as e:
        logger.error(f"Error verificando permisos {permissions}: {str(e)}")
        return False


@register.simple_tag(takes_context=True)
def has_all_permissions(context, *permissions) -> bool:
    """
    Template tag para verificar si el usuario tiene todos los permisos especificados.
    
    Args:
        context: Contexto del template
        *permissions: Lista de permisos a verificar
        
    Returns:
        bool: True si el usuario tiene todos los permisos
        
    Example:
        {% load permission_tags %}
        {% has_all_permissions 'view_property' 'change_property' as can_manage %}
        {% if can_manage %}
            <div class="admin-panel">...</div>
        {% endif %}
    """
    try:
        request = context.get('request')
        if not request or not hasattr(request, 'user'):
            return False
        
        user = request.user
        if not user.is_authenticated or not isinstance(user, Agent):
            return False
        
        role_service = RolePermissionService()
        
        for permission in permissions:
            if not role_service.check_permission(user, permission):
                return False
        
        return True
        
    except Exception as e:
        logger.error(f"Error verificando permisos {permissions}: {str(e)}")
        return False


@register.simple_tag(takes_context=True)
def has_role(context, role_name: str) -> bool:
    """
    Template tag para verificar si el usuario tiene un rol específico.
    
    Args:
        context: Contexto del template
        role_name: Nombre del rol a verificar
        
    Returns:
        bool: True si el usuario tiene el rol
        
    Example:
        {% load permission_tags %}
        {% has_role 'Administrador' as is_admin %}
        {% if is_admin %}
            <div class="admin-menu">...</div>
        {% endif %}
    """
    try:
        request = context.get('request')
        if not request or not hasattr(request, 'user'):
            return False
        
        user = request.user
        if not user.is_authenticated or not isinstance(user, Agent):
            return False
        
        role_service = RolePermissionService()
        user_roles = role_service.get_user_roles(user)
        user_role_names = [r.name for r in user_roles]
        
        return role_name in user_role_names
        
    except Exception as e:
        logger.error(f"Error verificando rol {role_name}: {str(e)}")
        return False


@register.simple_tag(takes_context=True)
def has_any_role(context, *role_names) -> bool:
    """
    Template tag para verificar si el usuario tiene al menos uno de los roles especificados.
    
    Args:
        context: Contexto del template
        *role_names: Lista de nombres de roles a verificar
        
    Returns:
        bool: True si el usuario tiene al menos uno de los roles
        
    Example:
        {% load permission_tags %}
        {% has_any_role 'Supervisor' 'Administrador' as is_manager %}
        {% if is_manager %}
            <div class="manager-tools">...</div>
        {% endif %}
    """
    try:
        request = context.get('request')
        if not request or not hasattr(request, 'user'):
            return False
        
        user = request.user
        if not user.is_authenticated or not isinstance(user, Agent):
            return False
        
        role_service = RolePermissionService()
        user_roles = role_service.get_user_roles(user)
        user_role_names = [r.name for r in user_roles]
        
        return any(role_name in user_role_names for role_name in role_names)
        
    except Exception as e:
        logger.error(f"Error verificando roles {role_names}: {str(e)}")
        return False


@register.simple_tag(takes_context=True)
def is_superuser(context) -> bool:
    """
    Template tag para verificar si el usuario es superusuario.
    
    Args:
        context: Contexto del template
        
    Returns:
        bool: True si el usuario es superusuario
        
    Example:
        {% load permission_tags %}
        {% is_superuser as is_super %}
        {% if is_super %}
            <div class="superuser-panel">...</div>
        {% endif %}
    """
    try:
        request = context.get('request')
        if not request or not hasattr(request, 'user'):
            return False
        
        user = request.user
        return user.is_authenticated and user.is_superuser
        
    except Exception as e:
        logger.error(f"Error verificando superusuario: {str(e)}")
        return False


@register.simple_tag(takes_context=True)
def is_staff(context) -> bool:
    """
    Template tag para verificar si el usuario es staff.
    
    Args:
        context: Contexto del template
        
    Returns:
        bool: True si el usuario es staff
        
    Example:
        {% load permission_tags %}
        {% is_staff as is_staff_user %}
        {% if is_staff_user %}
            <div class="staff-panel">...</div>
        {% endif %}
    """
    try:
        request = context.get('request')
        if not request or not hasattr(request, 'user'):
            return False
        
        user = request.user
        return user.is_authenticated and user.is_staff
        
    except Exception as e:
        logger.error(f"Error verificando staff: {str(e)}")
        return False


@register.simple_tag(takes_context=True)
def is_admin(context) -> bool:
    """
    Template tag para verificar si el usuario es administrador (superusuario o rol Administrador).
    
    Args:
        context: Contexto del template
        
    Returns:
        bool: True si el usuario es administrador
        
    Example:
        {% load permission_tags %}
        {% is_admin as is_admin_user %}
        {% if is_admin_user %}
            <div class="admin-controls">...</div>
        {% endif %}
    """
    try:
        request = context.get('request')
        if not request or not hasattr(request, 'user'):
            return False
        
        user = request.user
        if not user.is_authenticated:
            return False
        
        # Verificar superusuario primero
        if user.is_superuser:
            return True
        
        # Verificar que sea un Agent
        if not isinstance(user, Agent):
            return False
        
        # Verificar rol de Administrador
        role_service = RolePermissionService()
        user_roles = role_service.get_user_roles(user)
        user_role_names = [r.name for r in user_roles]
        
        return 'Administrador' in user_role_names
        
    except Exception as e:
        logger.error(f"Error verificando administrador: {str(e)}")
        return False


@register.simple_tag(takes_context=True)
def is_supervisor_or_admin(context) -> bool:
    """
    Template tag para verificar si el usuario es supervisor o administrador.
    
    Args:
        context: Contexto del template
        
    Returns:
        bool: True si el usuario es supervisor o administrador
        
    Example:
        {% load permission_tags %}
        {% is_supervisor_or_admin as can_supervise %}
        {% if can_supervise %}
            <div class="supervisor-tools">...</div>
        {% endif %}
    """
    try:
        request = context.get('request')
        if not request or not hasattr(request, 'user'):
            return False
        
        user = request.user
        if not user.is_authenticated:
            return False
        
        # Verificar superusuario primero
        if user.is_superuser:
            return True
        
        # Verificar que sea un Agent
        if not isinstance(user, Agent):
            return False
        
        # Verificar roles de Supervisor o Administrador
        role_service = RolePermissionService()
        user_roles = role_service.get_user_roles(user)
        user_role_names = [r.name for r in user_roles]
        
        allowed_roles = ['Supervisor', 'Administrador']
        return any(role_name in user_role_names for role_name in allowed_roles)
        
    except Exception as e:
        logger.error(f"Error verificando supervisor o administrador: {str(e)}")
        return False


@register.simple_tag(takes_context=True)
def get_user_roles(context) -> List[str]:
    """
    Template tag para obtener la lista de roles del usuario actual.
    
    Args:
        context: Contexto del template
        
    Returns:
        List[str]: Lista de nombres de roles del usuario
        
    Example:
        {% load permission_tags %}
        {% get_user_roles as user_roles %}
        {% for role in user_roles %}
            <span class="badge">{{ role }}</span>
        {% endfor %}
    """
    try:
        request = context.get('request')
        if not request or not hasattr(request, 'user'):
            return []
        
        user = request.user
        if not user.is_authenticated or not isinstance(user, Agent):
            return []
        
        role_service = RolePermissionService()
        user_roles = role_service.get_user_roles(user)
        
        return [role.name for role in user_roles]
        
    except Exception as e:
        logger.error(f"Error obteniendo roles del usuario: {str(e)}")
        return []


@register.simple_tag(takes_context=True)
def get_user_permissions(context) -> List[str]:
    """
    Template tag para obtener la lista de permisos del usuario actual.
    
    Args:
        context: Contexto del template
        
    Returns:
        List[str]: Lista de códigos de permisos del usuario
        
    Example:
        {% load permission_tags %}
        {% get_user_permissions as user_permissions %}
        {% if 'add_property' in user_permissions %}
            <button>Agregar Propiedad</button>
        {% endif %}
    """
    try:
        request = context.get('request')
        if not request or not hasattr(request, 'user'):
            return []
        
        user = request.user
        if not user.is_authenticated or not isinstance(user, Agent):
            return []
        
        role_service = RolePermissionService()
        user_permissions = role_service.get_user_permissions(user)
        
        return [perm.codename for perm in user_permissions]
        
    except Exception as e:
        logger.error(f"Error obteniendo permisos del usuario: {str(e)}")
        return []


@register.simple_tag(takes_context=True)
def is_owner(context, obj, owner_field: str = 'agent') -> bool:
    """
    Template tag para verificar si el usuario actual es propietario de un objeto.
    
    Args:
        context: Contexto del template
        obj: Objeto a verificar
        owner_field: Campo que identifica al propietario
        
    Returns:
        bool: True si el usuario es propietario
        
    Example:
        {% load permission_tags %}
        {% is_owner property 'agent' as is_property_owner %}
        {% if is_property_owner %}
            <button>Editar</button>
        {% endif %}
    """
    try:
        request = context.get('request')
        if not request or not hasattr(request, 'user'):
            return False
        
        user = request.user
        if not user.is_authenticated or not isinstance(user, Agent):
            return False
        
        if not obj:
            return False
        
        try:
            owner = getattr(obj, owner_field)
            return owner == user
        except AttributeError:
            logger.error(f"Campo propietario '{owner_field}' no encontrado en {obj.__class__.__name__}")
            return False
        
    except Exception as e:
        logger.error(f"Error verificando propiedad: {str(e)}")
        return False


# Filtros de template
@register.filter
def has_perm(user, permission: str) -> bool:
    """
    Filtro para verificar si un usuario tiene un permiso específico.
    
    Args:
        user: Usuario a verificar
        permission: Código del permiso
        
    Returns:
        bool: True si el usuario tiene el permiso
        
    Example:
        {% load permission_tags %}
        {% if user|has_perm:'view_property' %}
            <div>Contenido visible</div>
        {% endif %}
    """
    try:
        if not user or not user.is_authenticated or not isinstance(user, Agent):
            return False
        
        role_service = RolePermissionService()
        return role_service.check_permission(user, permission)
        
    except Exception as e:
        logger.error(f"Error verificando permiso {permission} para usuario {user}: {str(e)}")
        return False


@register.filter
def has_role_filter(user, role_name: str) -> bool:
    """
    Filtro para verificar si un usuario tiene un rol específico.
    
    Args:
        user: Usuario a verificar
        role_name: Nombre del rol
        
    Returns:
        bool: True si el usuario tiene el rol
        
    Example:
        {% load permission_tags %}
        {% if user|has_role_filter:'Administrador' %}
            <div>Panel de administrador</div>
        {% endif %}
    """
    try:
        if not user or not user.is_authenticated or not isinstance(user, Agent):
            return False
        
        role_service = RolePermissionService()
        user_roles = role_service.get_user_roles(user)
        user_role_names = [r.name for r in user_roles]
        
        return role_name in user_role_names
        
    except Exception as e:
        logger.error(f"Error verificando rol {role_name} para usuario {user}: {str(e)}")
        return False


@register.filter
def is_admin_filter(user) -> bool:
    """
    Filtro para verificar si un usuario es administrador.
    
    Args:
        user: Usuario a verificar
        
    Returns:
        bool: True si el usuario es administrador
        
    Example:
        {% load permission_tags %}
        {% if user|is_admin_filter %}
            <div>Controles de administrador</div>
        {% endif %}
    """
    try:
        if not user or not user.is_authenticated:
            return False
        
        # Verificar superusuario primero
        if user.is_superuser:
            return True
        
        # Verificar que sea un Agent
        if not isinstance(user, Agent):
            return False
        
        # Verificar rol de Administrador
        role_service = RolePermissionService()
        user_roles = role_service.get_user_roles(user)
        user_role_names = [r.name for r in user_roles]
        
        return 'Administrador' in user_role_names
        
    except Exception as e:
        logger.error(f"Error verificando administrador para usuario {user}: {str(e)}")
        return False


@register.filter
def is_supervisor_or_admin_filter(user) -> bool:
    """
    Filtro para verificar si un usuario es supervisor o administrador.
    
    Args:
        user: Usuario a verificar
        
    Returns:
        bool: True si el usuario es supervisor o administrador
        
    Example:
        {% load permission_tags %}
        {% if user|is_supervisor_or_admin_filter %}
            <div>Herramientas de supervisión</div>
        {% endif %}
    """
    try:
        if not user or not user.is_authenticated:
            return False
        
        # Verificar superusuario primero
        if user.is_superuser:
            return True
        
        # Verificar que sea un Agent
        if not isinstance(user, Agent):
            return False
        
        # Verificar roles de Supervisor o Administrador
        role_service = RolePermissionService()
        user_roles = role_service.get_user_roles(user)
        user_role_names = [r.name for r in user_roles]
        
        allowed_roles = ['Supervisor', 'Administrador']
        return any(role_name in user_role_names for role_name in allowed_roles)
        
    except Exception as e:
        logger.error(f"Error verificando supervisor o administrador para usuario {user}: {str(e)}")
        return False


@register.inclusion_tag('agents/includes/permission_debug.html', takes_context=True)
def permission_debug(context):
    """
    Template tag de inclusión para mostrar información de debug sobre permisos del usuario.
    
    Args:
        context: Contexto del template
        
    Returns:
        dict: Contexto para el template de debug
        
    Example:
        {% load permission_tags %}
        {% permission_debug %}
    """
    try:
        request = context.get('request')
        if not request or not hasattr(request, 'user'):
            return {'debug_info': None}
        
        user = request.user
        if not user.is_authenticated or not isinstance(user, Agent):
            return {'debug_info': None}
        
        role_service = RolePermissionService()
        user_roles = role_service.get_user_roles(user)
        user_permissions = role_service.get_user_permissions(user)
        
        debug_info = {
            'user': user,
            'is_superuser': user.is_superuser,
            'is_staff': user.is_staff,
            'roles': [{'name': role.name, 'description': role.description} for role in user_roles],
            'permissions': [{'codename': perm.codename, 'name': perm.name} for perm in user_permissions],
            'total_roles': len(user_roles),
            'total_permissions': len(user_permissions),
        }
        
        return {'debug_info': debug_info}
        
    except Exception as e:
        logger.error(f"Error generando información de debug: {str(e)}")
        return {'debug_info': None}


@register.simple_tag
def permission_check_js(permission: str) -> str:
    """
    Template tag para generar código JavaScript que verifica permisos.
    
    Args:
        permission: Código del permiso a verificar
        
    Returns:
        str: Código JavaScript para verificación de permisos
        
    Example:
        {% load permission_tags %}
        <script>
            {% permission_check_js 'view_property' %}
        </script>
    """
    try:
        js_code = f"""
        function hasPermission_{permission.replace('.', '_')}() {{
            return fetch('/api/permissions/check/', {{
                method: 'POST',
                headers: {{
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                }},
                body: JSON.stringify({{
                    'permission': '{permission}'
                }})
            }})
            .then(response => response.json())
            .then(data => data.has_permission)
            .catch(error => {{
                console.error('Error checking permission:', error);
                return false;
            }});
        }}
        """
        
        return js_code
        
    except Exception as e:
        logger.error(f"Error generando código JavaScript para permiso {permission}: {str(e)}")
        return ""