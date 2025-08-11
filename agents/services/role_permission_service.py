"""
Servicio para gestión de roles y permisos.

Este servicio maneja todas las operaciones relacionadas con la asignación
de roles, verificación de permisos y gestión del sistema de autorización.
"""

import logging
from typing import List, Dict, Any, Optional, Set
from django.db import transaction
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db.models import QuerySet, Count, Q
from django.db import models

from agents.models import Agent, Role, Permission, AgentRole, AuditLog


logger = logging.getLogger(__name__)


class RolePermissionService:
    """
    Servicio para gestión de roles y permisos.

    Proporciona métodos centralizados para asignar roles, verificar permisos
    y gestionar el sistema de autorización granular.
    """

    def __init__(self):
        """Inicializa el servicio de roles y permisos."""
        self.logger = logging.getLogger(f"{__name__}.RolePermissionService")

    def assign_role(
        self, agent: Agent, role: Role, assigned_by: Optional[Agent] = None
    ) -> bool:
        """
        Asigna un rol a un usuario.

        Args:
            agent: Usuario al que asignar el rol
            role: Rol a asignar
            assigned_by: Usuario que realiza la asignación

        Returns:
            bool: True si se asignó correctamente
        """
        try:
            with transaction.atomic():
                # Verificar si ya tiene el rol asignado
                existing_assignment = AgentRole.objects.filter(
                    agent=agent, role=role, is_active=True
                ).first()

                if existing_assignment:
                    self.logger.warning(
                        f"Usuario {agent.email} ya tiene el rol {role.name} asignado"
                    )
                    return False

                # Crear nueva asignación
                agent_role = AgentRole.objects.create(
                    agent=agent, role=role, assigned_by=assigned_by, is_active=True
                )

                # Registrar en auditoría
                AuditLog.objects.create(
                    agent=assigned_by if assigned_by else agent,
                    action="role_assigned",
                    resource_type="role",
                    resource_id=str(role.id),
                    ip_address="127.0.0.1",  # Sistema interno
                    user_agent="System",
                    details={
                        "target_agent_id": agent.id,
                        "target_agent_email": agent.email,
                        "role_name": role.name,
                        "role_id": role.id,
                    },
                    success=True,
                )

                self.logger.info(f"Rol {role.name} asignado a usuario {agent.email}")
                return True

        except Exception as e:
            self.logger.error(
                f"Error asignando rol {role.name} a {agent.email}: {str(e)}"
            )
            return False

    def revoke_role(
        self, agent: Agent, role: Role, revoked_by: Optional[Agent] = None
    ) -> bool:
        """
        Revoca un rol de un usuario.

        Args:
            agent: Usuario del que revocar el rol
            role: Rol a revocar
            revoked_by: Usuario que realiza la revocación

        Returns:
            bool: True si se revocó correctamente
        """
        try:
            with transaction.atomic():
                # Buscar asignación activa
                agent_role = AgentRole.objects.filter(
                    agent=agent, role=role, is_active=True
                ).first()

                if not agent_role:
                    self.logger.warning(
                        f"Usuario {agent.email} no tiene el rol {role.name} asignado"
                    )
                    return False

                # Desactivar asignación
                agent_role.is_active = False
                agent_role.save()

                # Registrar en auditoría
                AuditLog.objects.create(
                    agent=revoked_by if revoked_by else agent,
                    action="role_revoked",
                    resource_type="role",
                    resource_id=str(role.id),
                    ip_address="127.0.0.1",
                    user_agent="System",
                    details={
                        "target_agent_id": agent.id,
                        "target_agent_email": agent.email,
                        "role_name": role.name,
                        "role_id": role.id,
                    },
                    success=True,
                )

                self.logger.info(f"Rol {role.name} revocado de usuario {agent.email}")
                return True

        except Exception as e:
            self.logger.error(
                f"Error revocando rol {role.name} de {agent.email}: {str(e)}"
            )
            return False

    def check_permission(self, agent: Agent, permission_codename: str) -> bool:
        """
        Verifica si el usuario tiene un permiso específico.

        Args:
            agent: Usuario a verificar
            permission_codename: Código del permiso a verificar

        Returns:
            bool: True si tiene el permiso
        """
        try:
            # Obtener roles activos del usuario
            active_roles = self.get_user_roles(agent)

            # Verificar si algún rol tiene el permiso
            for role in active_roles:
                if role.has_permission(permission_codename):
                    return True

            return False

        except Exception as e:
            self.logger.error(
                f"Error verificando permiso {permission_codename} para {agent.email}: {str(e)}"
            )
            return False

    def get_user_permissions(self, agent: Agent) -> QuerySet:
        """
        Obtiene todos los permisos del usuario.

        Args:
            agent: Usuario para obtener permisos

        Returns:
            QuerySet: Permisos del usuario
        """
        try:
            # Obtener roles activos del usuario
            active_roles = self.get_user_roles(agent)

            # Obtener todos los permisos de los roles
            permission_ids = set()
            for role in active_roles:
                permission_ids.update(role.permissions.values_list("id", flat=True))

            return Permission.objects.filter(id__in=permission_ids)

        except Exception as e:
            self.logger.error(f"Error obteniendo permisos para {agent.email}: {str(e)}")
            return Permission.objects.none()

    def get_user_roles(self, agent: Agent) -> QuerySet:
        """
        Obtiene todos los roles activos del usuario.

        Args:
            agent: Usuario para obtener roles

        Returns:
            QuerySet: Roles activos del usuario
        """
        try:
            return Role.objects.filter(
                agentrole__agent=agent, agentrole__is_active=True
            ).distinct()

        except Exception as e:
            self.logger.error(f"Error obteniendo roles para {agent.email}: {str(e)}")
            return Role.objects.none()

    def create_custom_role(
        self,
        name: str,
        description: str = "",
        permissions: List[Permission] = None,
        created_by: Optional[Agent] = None,
    ) -> Role:
        """
        Crea un rol personalizado.

        Args:
            name: Nombre del rol
            description: Descripción del rol
            permissions: Lista de permisos a asignar
            created_by: Usuario que crea el rol

        Returns:
            Role: Rol creado

        Raises:
            ValidationError: Si el nombre ya existe o es inválido
        """
        try:
            with transaction.atomic():
                # Verificar que el nombre no exista
                if Role.objects.filter(name=name).exists():
                    raise ValidationError(f"Ya existe un rol con el nombre '{name}'")

                # Crear rol
                role = Role.objects.create(
                    name=name, description=description, is_system_role=False
                )

                # Asignar permisos si se proporcionaron
                if permissions:
                    role.permissions.set(permissions)

                # Registrar en auditoría
                AuditLog.objects.create(
                    agent=created_by,
                    action="role_created",
                    resource_type="role",
                    resource_id=str(role.id),
                    ip_address="127.0.0.1",
                    user_agent="System",
                    details={
                        "role_name": name,
                        "role_description": description,
                        "permissions_count": len(permissions) if permissions else 0,
                    },
                    success=True,
                )

                self.logger.info(f"Rol personalizado creado: {name}")
                return role

        except ValidationError:
            raise
        except Exception as e:
            self.logger.error(f"Error creando rol personalizado {name}: {str(e)}")
            raise ValidationError(f"Error creando rol: {str(e)}")

    def create_permission(
        self, codename: str, name: str, content_type: ContentType, description: str = ""
    ) -> Permission:
        """
        Crea un nuevo permiso.

        Args:
            codename: Código único del permiso
            name: Nombre descriptivo del permiso
            content_type: Tipo de contenido asociado
            description: Descripción del permiso

        Returns:
            Permission: Permiso creado

        Raises:
            ValidationError: Si el código ya existe
        """
        try:
            with transaction.atomic():
                # Verificar que el codename no exista
                if Permission.objects.filter(codename=codename).exists():
                    raise ValidationError(
                        f"Ya existe un permiso con el código '{codename}'"
                    )

                # Crear permiso
                permission = Permission.objects.create(
                    codename=codename,
                    name=name,
                    content_type=content_type,
                    description=description,
                )

                self.logger.info(f"Permiso creado: {codename}")
                return permission

        except ValidationError:
            raise
        except Exception as e:
            self.logger.error(f"Error creando permiso {codename}: {str(e)}")
            raise ValidationError(f"Error creando permiso: {str(e)}")

    def get_role_hierarchy(self) -> Dict[str, Any]:
        """
        Obtiene la jerarquía de roles del sistema.

        Returns:
            dict: Estructura jerárquica de roles
        """
        try:
            roles_data = []

            for role in Role.objects.all().order_by("name"):
                permissions_data = []
                for permission in role.permissions.all():
                    permissions_data.append(
                        {
                            "id": permission.id,
                            "codename": permission.codename,
                            "name": permission.name,
                            "content_type": permission.content_type.name,
                        }
                    )

                # Contar usuarios con este rol
                users_count = AgentRole.objects.filter(
                    role=role, is_active=True
                ).count()

                roles_data.append(
                    {
                        "id": role.id,
                        "name": role.name,
                        "description": role.description,
                        "is_system_role": role.is_system_role,
                        "permissions": permissions_data,
                        "users_count": users_count,
                        "created_at": role.created_at,
                    }
                )

            return {
                "roles": roles_data,
                "total_roles": len(roles_data),
                "system_roles": len([r for r in roles_data if r["is_system_role"]]),
                "custom_roles": len([r for r in roles_data if not r["is_system_role"]]),
            }

        except Exception as e:
            self.logger.error(f"Error obteniendo jerarquía de roles: {str(e)}")
            return {}

    def get_permission_matrix(self) -> Dict[str, Any]:
        """
        Obtiene una matriz de permisos por rol.

        Returns:
            dict: Matriz de permisos
        """
        try:
            roles = Role.objects.all().prefetch_related("permissions")
            permissions = Permission.objects.all().order_by(
                "content_type__name", "name"
            )

            matrix = {}

            # Crear estructura de la matriz
            for permission in permissions:
                content_type_name = permission.content_type.name
                if content_type_name not in matrix:
                    matrix[content_type_name] = {}

                matrix[content_type_name][permission.codename] = {
                    "permission_name": permission.name,
                    "description": permission.description,
                    "roles": [],
                }

                # Verificar qué roles tienen este permiso
                for role in roles:
                    if role.has_permission(permission.codename):
                        matrix[content_type_name][permission.codename]["roles"].append(
                            {
                                "id": role.id,
                                "name": role.name,
                                "is_system_role": role.is_system_role,
                            }
                        )

            return matrix

        except Exception as e:
            self.logger.error(f"Error obteniendo matriz de permisos: {str(e)}")
            return {}

    def bulk_assign_roles(
        self, agent: Agent, role_ids: List[int], assigned_by: Optional[Agent] = None
    ) -> Dict[str, Any]:
        """
        Asigna múltiples roles a un usuario en una sola operación.

        Args:
            agent: Usuario al que asignar roles
            role_ids: Lista de IDs de roles a asignar
            assigned_by: Usuario que realiza la asignación

        Returns:
            dict: Resultado de la operación
        """
        try:
            with transaction.atomic():
                results = {"assigned": [], "already_assigned": [], "errors": []}

                for role_id in role_ids:
                    try:
                        role = Role.objects.get(id=role_id)

                        if self.assign_role(agent, role, assigned_by):
                            results["assigned"].append(
                                {"id": role.id, "name": role.name}
                            )
                        else:
                            results["already_assigned"].append(
                                {"id": role.id, "name": role.name}
                            )

                    except Role.DoesNotExist:
                        results["errors"].append(f"Rol con ID {role_id} no existe")
                    except Exception as e:
                        results["errors"].append(
                            f"Error asignando rol {role_id}: {str(e)}"
                        )

                self.logger.info(
                    f"Asignación masiva de roles para {agent.email}: {len(results['assigned'])} asignados"
                )
                return results

        except Exception as e:
            self.logger.error(
                f"Error en asignación masiva de roles para {agent.email}: {str(e)}"
            )
            return {"assigned": [], "already_assigned": [], "errors": [str(e)]}

    def get_users_by_permission(self, permission_codename: str) -> QuerySet:
        """
        Obtiene todos los usuarios que tienen un permiso específico.

        Args:
            permission_codename: Código del permiso

        Returns:
            QuerySet: Usuarios con el permiso
        """
        try:
            # Obtener roles que tienen el permiso
            roles_with_permission = Role.objects.filter(
                permissions__codename=permission_codename
            )

            # Obtener usuarios con esos roles
            return Agent.objects.filter(
                agentrole__role__in=roles_with_permission, agentrole__is_active=True
            ).distinct()

        except Exception as e:
            self.logger.error(
                f"Error obteniendo usuarios con permiso {permission_codename}: {str(e)}"
            )
            return Agent.objects.none()

    def get_role_statistics(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas del sistema de roles.

        Returns:
            dict: Estadísticas de roles y permisos
        """
        try:
            # Estadísticas básicas
            total_roles = Role.objects.count()
            system_roles = Role.objects.filter(is_system_role=True).count()
            custom_roles = total_roles - system_roles
            total_permissions = Permission.objects.count()

            # Usuarios con roles
            users_with_roles = (
                Agent.objects.filter(agentrole__is_active=True).distinct().count()
            )

            # Roles más asignados
            most_assigned_roles = Role.objects.annotate(
                users_count=models.Count(
                    "agentrole", filter=models.Q(agentrole__is_active=True)
                )
            ).order_by("-users_count")[:5]

            # Permisos por tipo de contenido
            permissions_by_content_type = {}
            for permission in Permission.objects.select_related("content_type"):
                content_type_name = permission.content_type.name
                if content_type_name not in permissions_by_content_type:
                    permissions_by_content_type[content_type_name] = 0
                permissions_by_content_type[content_type_name] += 1

            return {
                "total_roles": total_roles,
                "system_roles": system_roles,
                "custom_roles": custom_roles,
                "total_permissions": total_permissions,
                "users_with_roles": users_with_roles,
                "most_assigned_roles": [
                    {"id": role.id, "name": role.name, "users_count": role.users_count}
                    for role in most_assigned_roles
                ],
                "permissions_by_content_type": permissions_by_content_type,
            }

        except Exception as e:
            self.logger.error(f"Error obteniendo estadísticas de roles: {str(e)}")
            return {}

    def validate_role_assignment(self, agent: Agent, role: Role) -> Dict[str, Any]:
        """
        Valida si un rol puede ser asignado a un usuario.

        Args:
            agent: Usuario para validar
            role: Rol a validar

        Returns:
            dict: Resultado de la validación
        """
        try:
            validation_result = {"valid": True, "warnings": [], "errors": []}

            # Verificar si ya tiene el rol
            if AgentRole.objects.filter(
                agent=agent, role=role, is_active=True
            ).exists():
                validation_result["valid"] = False
                validation_result["errors"].append(
                    f"El usuario ya tiene el rol '{role.name}' asignado"
                )

            # Verificar si el usuario está activo
            if not agent.is_active:
                validation_result["warnings"].append("El usuario está inactivo")

            # Verificar conflictos de roles (si se implementa lógica específica)
            current_roles = self.get_user_roles(agent)
            for current_role in current_roles:
                if self._roles_conflict(current_role, role):
                    validation_result["warnings"].append(
                        f"Posible conflicto con el rol existente '{current_role.name}'"
                    )

            return validation_result

        except Exception as e:
            self.logger.error(
                f"Error validando asignación de rol para {agent.email}: {str(e)}"
            )
            return {
                "valid": False,
                "warnings": [],
                "errors": [f"Error de validación: {str(e)}"],
            }

    def _roles_conflict(self, role1: Role, role2: Role) -> bool:
        """
        Verifica si dos roles tienen conflictos.

        Args:
            role1: Primer rol
            role2: Segundo rol

        Returns:
            bool: True si hay conflicto
        """
        # Implementar lógica específica de conflictos si es necesario
        # Por ejemplo, "Admin" y "ReadOnly" podrían ser conflictivos
        conflicting_pairs = [("Admin", "ReadOnly"), ("SuperAdmin", "Guest")]

        for pair in conflicting_pairs:
            if role1.name in pair and role2.name in pair:
                return True

        return False

    def create_default_roles(self) -> List[Role]:
        """
        Crea los roles por defecto del sistema.

        Returns:
            List[Role]: Lista de roles creados
        """
        try:
            default_roles_data = [
                {
                    "name": "Agente Básico",
                    "description": "Rol básico para agentes inmobiliarios",
                    "permissions": [
                        "view_property",
                        "add_property",
                        "change_own_property",
                    ],
                },
                {
                    "name": "Supervisor",
                    "description": "Supervisor de agentes con permisos adicionales",
                    "permissions": [
                        "view_property",
                        "add_property",
                        "change_property",
                        "view_reports",
                    ],
                },
                {
                    "name": "Administrador",
                    "description": "Administrador del sistema con todos los permisos",
                    "permissions": ["*"],  # Todos los permisos
                },
            ]

            created_roles = []

            with transaction.atomic():
                for role_data in default_roles_data:
                    # Verificar si el rol ya existe
                    if Role.objects.filter(name=role_data["name"]).exists():
                        continue

                    role = Role.objects.create(
                        name=role_data["name"],
                        description=role_data["description"],
                        is_system_role=True,
                    )

                    # Asignar permisos (implementar lógica específica según necesidades)
                    # Por ahora solo creamos el rol

                    created_roles.append(role)
                    self.logger.info(f"Rol por defecto creado: {role.name}")

            return created_roles

        except Exception as e:
            self.logger.error(f"Error creando roles por defecto: {str(e)}")
            return []
