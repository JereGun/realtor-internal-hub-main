"""
Servicio para respaldo y restauración de configuraciones de empresa.

Este servicio proporciona funcionalidades para exportar todas las configuraciones
de la empresa a un archivo JSON y restaurarlas desde un respaldo.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from core.models import (
    Company, 
    CompanyConfiguration, 
    DocumentTemplate, 
    NotificationSettings, 
    SystemConfiguration
)


logger = logging.getLogger(__name__)


class BackupService:
    """
    Servicio para respaldo y restauración de configuraciones.
    
    Proporciona métodos para exportar configuraciones a JSON y restaurarlas
    desde archivos de respaldo con validación de integridad.
    """
    
    BACKUP_VERSION = "1.0"
    SUPPORTED_VERSIONS = ["1.0"]
    
    def __init__(self, company: Company):
        """
        Inicializa el servicio con una instancia de empresa.
        
        Args:
            company: Instancia del modelo Company
        """
        self.company = company
        self.logger = logging.getLogger(f"{__name__}.{company.id}")
    
    def export_configurations(self) -> Dict[str, Any]:
        """
        Exporta todas las configuraciones de la empresa a un diccionario.
        
        Returns:
            Diccionario con todas las configuraciones exportadas
        """
        try:
            export_data = {
                "backup_info": {
                    "version": self.BACKUP_VERSION,
                    "created_at": timezone.now().isoformat(),
                    "company_id": self.company.id,
                    "company_name": self.company.name
                },
                "company_data": self._export_company_data(),
                "configurations": self._export_company_configurations(),
                "document_templates": self._export_document_templates(),
                "notification_settings": self._export_notification_settings(),
                "system_configuration": self._export_system_configuration()
            }
            
            self.logger.info(f"Configuration export completed for company {self.company.name}")
            return export_data
            
        except Exception as e:
            self.logger.error(f"Error exporting configurations: {str(e)}")
            raise
    
    def import_configurations(self, backup_data: Dict[str, Any], 
                            overwrite_existing: bool = False) -> Dict[str, Any]:
        """
        Importa configuraciones desde un diccionario de respaldo.
        
        Args:
            backup_data: Datos del respaldo
            overwrite_existing: Si sobrescribir configuraciones existentes
            
        Returns:
            Diccionario con resumen de cambios aplicados
            
        Raises:
            ValidationError: Si el respaldo no es válido
        """
        try:
            # Validar integridad del respaldo
            is_valid, error_msg = self.validate_backup_data(backup_data)
            if not is_valid:
                raise ValidationError(f"Invalid backup data: {error_msg}")
            
            changes_summary = {
                "company_data": {"updated": False, "changes": []},
                "configurations": {"created": 0, "updated": 0, "skipped": 0},
                "document_templates": {"created": 0, "updated": 0, "skipped": 0},
                "notification_settings": {"created": 0, "updated": 0, "skipped": 0},
                "system_configuration": {"updated": False, "changes": []}
            }
            
            with transaction.atomic():
                # Importar datos de empresa
                if "company_data" in backup_data:
                    changes_summary["company_data"] = self._import_company_data(
                        backup_data["company_data"], overwrite_existing
                    )
                
                # Importar configuraciones generales
                if "configurations" in backup_data:
                    changes_summary["configurations"] = self._import_company_configurations(
                        backup_data["configurations"], overwrite_existing
                    )
                
                # Importar plantillas de documentos
                if "document_templates" in backup_data:
                    changes_summary["document_templates"] = self._import_document_templates(
                        backup_data["document_templates"], overwrite_existing
                    )
                
                # Importar configuraciones de notificaciones
                if "notification_settings" in backup_data:
                    changes_summary["notification_settings"] = self._import_notification_settings(
                        backup_data["notification_settings"], overwrite_existing
                    )
                
                # Importar configuración del sistema
                if "system_configuration" in backup_data:
                    changes_summary["system_configuration"] = self._import_system_configuration(
                        backup_data["system_configuration"], overwrite_existing
                    )
            
            self.logger.info(f"Configuration import completed for company {self.company.name}")
            return changes_summary
            
        except Exception as e:
            self.logger.error(f"Error importing configurations: {str(e)}")
            raise
    
    def validate_backup_data(self, backup_data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Valida la integridad de un archivo de respaldo.
        
        Args:
            backup_data: Datos del respaldo a validar
            
        Returns:
            Tupla (es_válido, mensaje_error)
        """
        try:
            # Verificar estructura básica
            if not isinstance(backup_data, dict):
                return False, "Backup data must be a dictionary"
            
            # Verificar información del respaldo
            if "backup_info" not in backup_data:
                return False, "Missing backup_info section"
            
            backup_info = backup_data["backup_info"]
            
            # Verificar versión
            if "version" not in backup_info:
                return False, "Missing version in backup_info"
            
            version = backup_info["version"]
            if version not in self.SUPPORTED_VERSIONS:
                return False, f"Unsupported backup version: {version}"
            
            # Verificar campos requeridos
            required_fields = ["created_at", "company_id", "company_name"]
            for field in required_fields:
                if field not in backup_info:
                    return False, f"Missing required field in backup_info: {field}"
            
            # Validar secciones de datos
            sections = [
                "company_data", "configurations", "document_templates", 
                "notification_settings", "system_configuration"
            ]
            
            for section in sections:
                if section in backup_data:
                    is_valid, error = self._validate_section(section, backup_data[section])
                    if not is_valid:
                        return False, f"Invalid {section}: {error}"
            
            self.logger.debug("Backup data validation passed")
            return True, None
            
        except Exception as e:
            error_msg = f"Validation error: {str(e)}"
            self.logger.warning(f"Backup validation failed: {error_msg}")
            return False, error_msg
    
    def create_backup_file(self, file_path: Optional[str] = None) -> str:
        """
        Crea un archivo de respaldo en formato JSON.
        
        Args:
            file_path: Ruta del archivo (opcional, se genera automáticamente si no se proporciona)
            
        Returns:
            Ruta del archivo creado
        """
        try:
            # Generar nombre de archivo si no se proporciona
            if not file_path:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                company_name = self.company.name.replace(" ", "_").replace(".", "")
                file_path = f"backup_{company_name}_{timestamp}.json"
            
            # Exportar configuraciones
            backup_data = self.export_configurations()
            
            # Escribir archivo JSON
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Backup file created: {file_path}")
            return file_path
            
        except Exception as e:
            self.logger.error(f"Error creating backup file: {str(e)}")
            raise
    
    def load_backup_file(self, file_path: str) -> Dict[str, Any]:
        """
        Carga un archivo de respaldo desde disco.
        
        Args:
            file_path: Ruta del archivo de respaldo
            
        Returns:
            Datos del respaldo cargados
            
        Raises:
            FileNotFoundError: Si el archivo no existe
            json.JSONDecodeError: Si el archivo no es JSON válido
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            
            self.logger.info(f"Backup file loaded: {file_path}")
            return backup_data
            
        except FileNotFoundError:
            self.logger.error(f"Backup file not found: {file_path}")
            raise
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in backup file {file_path}: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Error loading backup file {file_path}: {str(e)}")
            raise
    
    def _export_company_data(self) -> Dict[str, Any]:
        """Exporta datos básicos de la empresa"""
        return {
            "name": self.company.name,
            "address": self.company.address or "",
            "phone": self.company.phone or "",
            "email": self.company.email or "",
            "website": self.company.website or "",
            "tax_id": self.company.tax_id or "",
            # Nota: logo se maneja por separado por ser un archivo
        }
    
    def _export_company_configurations(self) -> List[Dict[str, Any]]:
        """Exporta configuraciones generales de la empresa"""
        configurations = []
        for config in self.company.configurations.all():
            configurations.append({
                "config_key": config.config_key,
                "config_value": config.config_value,
                "config_type": config.config_type
            })
        return configurations
    
    def _export_document_templates(self) -> List[Dict[str, Any]]:
        """Exporta plantillas de documentos"""
        templates = []
        for template in self.company.document_templates.filter(is_active=True):
            templates.append({
                "template_name": template.template_name,
                "template_type": template.template_type,
                "header_content": template.header_content or "",
                "footer_content": template.footer_content or "",
                "custom_css": template.custom_css or ""
            })
        return templates
    
    def _export_notification_settings(self) -> List[Dict[str, Any]]:
        """Exporta configuraciones de notificaciones"""
        settings = []
        for setting in self.company.notification_settings.all():
            settings.append({
                "notification_type": setting.notification_type,
                "is_enabled": setting.is_enabled,
                "email_template": setting.email_template or "",
                "frequency_days": setting.frequency_days
            })
        return settings
    
    def _export_system_configuration(self) -> Optional[Dict[str, Any]]:
        """Exporta configuración del sistema"""
        try:
            sys_config = self.company.system_configuration
            return {
                "currency": sys_config.currency,
                "timezone": sys_config.timezone,
                "date_format": sys_config.date_format,
                "language": sys_config.language
            }
        except SystemConfiguration.DoesNotExist:
            return None
    
    def _import_company_data(self, data: Dict[str, Any], overwrite: bool) -> Dict[str, Any]:
        """Importa datos básicos de la empresa"""
        changes = []
        
        fields_to_update = ["name", "address", "phone", "email", "website", "tax_id"]
        
        for field in fields_to_update:
            if field in data:
                current_value = getattr(self.company, field) or ""
                new_value = data[field] or ""
                
                if current_value != new_value and (overwrite or not current_value):
                    setattr(self.company, field, new_value)
                    changes.append(f"{field}: '{current_value}' -> '{new_value}'")
        
        if changes:
            self.company.save()
            return {"updated": True, "changes": changes}
        
        return {"updated": False, "changes": []}
    
    def _import_company_configurations(self, data: List[Dict[str, Any]], overwrite: bool) -> Dict[str, int]:
        """Importa configuraciones generales"""
        created = updated = skipped = 0
        
        for config_data in data:
            config_key = config_data["config_key"]
            
            try:
                config = CompanyConfiguration.objects.get(
                    company=self.company, 
                    config_key=config_key
                )
                
                if overwrite:
                    config.config_value = config_data["config_value"]
                    config.config_type = config_data["config_type"]
                    config.save()
                    updated += 1
                else:
                    skipped += 1
                    
            except CompanyConfiguration.DoesNotExist:
                CompanyConfiguration.objects.create(
                    company=self.company,
                    config_key=config_key,
                    config_value=config_data["config_value"],
                    config_type=config_data["config_type"]
                )
                created += 1
        
        return {"created": created, "updated": updated, "skipped": skipped}
    
    def _import_document_templates(self, data: List[Dict[str, Any]], overwrite: bool) -> Dict[str, int]:
        """Importa plantillas de documentos"""
        created = updated = skipped = 0
        
        for template_data in data:
            template_name = template_data["template_name"]
            template_type = template_data["template_type"]
            
            try:
                template = DocumentTemplate.objects.get(
                    company=self.company,
                    template_name=template_name,
                    template_type=template_type
                )
                
                if overwrite:
                    template.header_content = template_data.get("header_content", "")
                    template.footer_content = template_data.get("footer_content", "")
                    template.custom_css = template_data.get("custom_css", "")
                    template.is_active = True
                    template.save()
                    updated += 1
                else:
                    skipped += 1
                    
            except DocumentTemplate.DoesNotExist:
                DocumentTemplate.objects.create(
                    company=self.company,
                    template_name=template_name,
                    template_type=template_type,
                    header_content=template_data.get("header_content", ""),
                    footer_content=template_data.get("footer_content", ""),
                    custom_css=template_data.get("custom_css", ""),
                    is_active=True
                )
                created += 1
        
        return {"created": created, "updated": updated, "skipped": skipped}
    
    def _import_notification_settings(self, data: List[Dict[str, Any]], overwrite: bool) -> Dict[str, int]:
        """Importa configuraciones de notificaciones"""
        created = updated = skipped = 0
        
        for setting_data in data:
            notification_type = setting_data["notification_type"]
            
            try:
                setting = NotificationSettings.objects.get(
                    company=self.company,
                    notification_type=notification_type
                )
                
                if overwrite:
                    setting.is_enabled = setting_data["is_enabled"]
                    setting.email_template = setting_data.get("email_template", "")
                    setting.frequency_days = setting_data["frequency_days"]
                    setting.save()
                    updated += 1
                else:
                    skipped += 1
                    
            except NotificationSettings.DoesNotExist:
                NotificationSettings.objects.create(
                    company=self.company,
                    notification_type=notification_type,
                    is_enabled=setting_data["is_enabled"],
                    email_template=setting_data.get("email_template", ""),
                    frequency_days=setting_data["frequency_days"]
                )
                created += 1
        
        return {"created": created, "updated": updated, "skipped": skipped}
    
    def _import_system_configuration(self, data: Dict[str, Any], overwrite: bool) -> Dict[str, Any]:
        """Importa configuración del sistema"""
        changes = []
        
        try:
            sys_config = self.company.system_configuration
            
            fields_to_update = ["currency", "timezone", "date_format", "language"]
            
            for field in fields_to_update:
                if field in data:
                    current_value = getattr(sys_config, field)
                    new_value = data[field]
                    
                    if current_value != new_value and overwrite:
                        setattr(sys_config, field, new_value)
                        changes.append(f"{field}: '{current_value}' -> '{new_value}'")
            
            if changes:
                sys_config.save()
                return {"updated": True, "changes": changes}
            
        except SystemConfiguration.DoesNotExist:
            # Crear nueva configuración del sistema
            SystemConfiguration.objects.create(
                company=self.company,
                currency=data.get("currency", "EUR"),
                timezone=data.get("timezone", "Europe/Madrid"),
                date_format=data.get("date_format", "DD/MM/YYYY"),
                language=data.get("language", "es")
            )
            return {"updated": True, "changes": ["Created new system configuration"]}
        
        return {"updated": False, "changes": []}
    
    def _validate_section(self, section_name: str, section_data: Any) -> Tuple[bool, Optional[str]]:
        """Valida una sección específica del respaldo"""
        if section_name == "company_data":
            if not isinstance(section_data, dict):
                return False, "company_data must be a dictionary"
            
        elif section_name in ["configurations", "document_templates", "notification_settings"]:
            if not isinstance(section_data, list):
                return False, f"{section_name} must be a list"
            
        elif section_name == "system_configuration":
            if section_data is not None and not isinstance(section_data, dict):
                return False, "system_configuration must be a dictionary or null"
        
        return True, None