"""
Servicio para gestión de configuraciones de empresa.

Este servicio proporciona una interfaz centralizada para gestionar
todas las configuraciones relacionadas con la empresa, incluyendo
configuraciones flexibles, configuraciones del sistema y aplicación
de cambios en tiempo real.
"""

import logging
from typing import Any, Dict, Optional, Union
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from core.models import Company, CompanyConfiguration, SystemConfiguration

logger = logging.getLogger(__name__)


class CompanyConfigurationService:
    """
    Servicio para gestión centralizada de configuraciones de empresa.
    
    Proporciona métodos para obtener, establecer y validar configuraciones,
    así como aplicar configuraciones del sistema en tiempo real.
    """
    
    def __init__(self, company: Company):
        """
        Inicializa el servicio con una instancia de empresa.
        
        Args:
            company: Instancia del modelo Company
        """
        self.company = company
        self.logger = logging.getLogger(f"{__name__}.{company.id}")
    
    def get_configuration(self, key: str, default: Any = None) -> Any:
        """
        Obtiene una configuración específica de la empresa.
        
        Args:
            key: Clave de configuración
            default: Valor por defecto si no existe la configuración
            
        Returns:
            Valor de la configuración convertido al tipo apropiado
        """
        try:
            config = self.company.configurations.get(config_key=key)
            value = config.get_value()
            self.logger.debug(f"Configuration retrieved: {key} = {value}")
            return value
        except CompanyConfiguration.DoesNotExist:
            self.logger.debug(f"Configuration not found: {key}, returning default: {default}")
            return default
    
    def set_configuration(self, key: str, value: Any, config_type: str = 'string') -> CompanyConfiguration:
        """
        Establece una configuración específica de la empresa.
        
        Args:
            key: Clave de configuración
            value: Valor a establecer
            config_type: Tipo de dato ('string', 'boolean', 'integer', 'decimal', 'json', 'file')
            
        Returns:
            Instancia de CompanyConfiguration creada o actualizada
            
        Raises:
            ValidationError: Si el valor no es válido para el tipo especificado
        """
        if not self.validate_configuration(key, value, config_type):
            raise ValidationError(f"Invalid value '{value}' for configuration '{key}' of type '{config_type}'")
        
        try:
            with transaction.atomic():
                config, created = self.company.configurations.get_or_create(
                    config_key=key,
                    defaults={'config_type': config_type}
                )
                
                # Si ya existe pero el tipo es diferente, actualizar el tipo
                if not created and config.config_type != config_type:
                    config.config_type = config_type
                
                config.set_value(value)
                config.save()
                
                action = "created" if created else "updated"
                self.logger.info(f"Configuration {action}: {key} = {value} (type: {config_type})")
                
                return config
                
        except Exception as e:
            self.logger.error(f"Error setting configuration {key}: {str(e)}")
            raise
    
    def get_all_configurations(self) -> Dict[str, Any]:
        """
        Obtiene todas las configuraciones de la empresa.
        
        Returns:
            Diccionario con todas las configuraciones clave-valor
        """
        configurations = {}
        
        for config in self.company.configurations.all():
            configurations[config.config_key] = config.get_value()
        
        self.logger.debug(f"Retrieved {len(configurations)} configurations")
        return configurations
    
    def delete_configuration(self, key: str) -> bool:
        """
        Elimina una configuración específica.
        
        Args:
            key: Clave de configuración a eliminar
            
        Returns:
            True si se eliminó, False si no existía
        """
        try:
            config = self.company.configurations.get(config_key=key)
            config.delete()
            self.logger.info(f"Configuration deleted: {key}")
            return True
        except CompanyConfiguration.DoesNotExist:
            self.logger.warning(f"Attempted to delete non-existent configuration: {key}")
            return False
    
    def validate_configuration(self, key: str, value: Any, config_type: str = 'string') -> bool:
        """
        Valida que un valor sea apropiado para el tipo de configuración especificado.
        
        Args:
            key: Clave de configuración
            value: Valor a validar
            config_type: Tipo de dato esperado
            
        Returns:
            True si el valor es válido, False en caso contrario
        """
        if value is None:
            return True
        
        try:
            if config_type == 'boolean':
                if isinstance(value, bool):
                    return True
                if isinstance(value, str):
                    return value.lower() in ['true', 'false', '1', '0', 'yes', 'no', 'on', 'off']
                return False
                
            elif config_type == 'integer':
                int(value)
                return True
                
            elif config_type == 'decimal':
                float(value)
                return True
                
            elif config_type == 'json':
                import json
                if isinstance(value, (dict, list)):
                    return True
                if isinstance(value, str):
                    json.loads(value)
                    return True
                return False
                
            elif config_type == 'string':
                return isinstance(value, (str, int, float))
                
            elif config_type == 'file':
                return isinstance(value, str)  # Asumimos que es una ruta de archivo
                
            else:
                self.logger.warning(f"Unknown configuration type: {config_type}")
                return False
                
        except (ValueError, TypeError, json.JSONDecodeError) as e:
            self.logger.debug(f"Validation failed for {key}: {str(e)}")
            return False
    
    def apply_system_configurations(self) -> bool:
        """
        Aplica las configuraciones del sistema en tiempo real.
        
        Actualiza configuraciones que afectan el comportamiento global
        del sistema como zona horaria, formato de fecha, etc.
        
        Returns:
            True si se aplicaron correctamente, False en caso contrario
        """
        try:
            system_config = self.company.get_system_config()
            
            # Aplicar configuración de zona horaria
            if system_config.timezone:
                import os
                os.environ['TZ'] = system_config.timezone
                self.logger.info(f"Applied timezone: {system_config.timezone}")
            
            # Aplicar configuraciones de formato
            self.set_configuration('active_currency', system_config.currency, 'string')
            self.set_configuration('active_date_format', system_config.date_format, 'string')
            self.set_configuration('active_language', system_config.language, 'string')
            self.set_configuration('active_decimal_places', system_config.decimal_places, 'integer')
            
            # Registrar aplicación de configuraciones
            self.set_configuration('last_config_applied', timezone.now().isoformat(), 'string')
            
            self.logger.info("System configurations applied successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error applying system configurations: {str(e)}")
            return False
    
    def get_system_configuration(self) -> SystemConfiguration:
        """
        Obtiene la configuración del sistema para la empresa.
        
        Returns:
            Instancia de SystemConfiguration
        """
        return self.company.get_system_config()
    
    def update_system_configuration(self, **kwargs) -> SystemConfiguration:
        """
        Actualiza la configuración del sistema.
        
        Args:
            **kwargs: Campos a actualizar
            
        Returns:
            Instancia actualizada de SystemConfiguration
        """
        try:
            with transaction.atomic():
                system_config = self.get_system_configuration()
                
                for field, value in kwargs.items():
                    if hasattr(system_config, field):
                        setattr(system_config, field, value)
                        self.logger.info(f"System config updated: {field} = {value}")
                    else:
                        self.logger.warning(f"Unknown system config field: {field}")
                
                system_config.save()
                
                # Aplicar configuraciones inmediatamente
                self.apply_system_configurations()
                
                return system_config
                
        except Exception as e:
            self.logger.error(f"Error updating system configuration: {str(e)}")
            raise
    
    def export_configurations(self) -> Dict[str, Any]:
        """
        Exporta todas las configuraciones de la empresa.
        
        Returns:
            Diccionario con todas las configuraciones para respaldo
        """
        try:
            export_data = {
                'company_id': self.company.id,
                'company_name': self.company.name,
                'export_timestamp': timezone.now().isoformat(),
                'configurations': {},
                'system_configuration': {}
            }
            
            # Exportar configuraciones flexibles
            for config in self.company.configurations.all():
                export_data['configurations'][config.config_key] = {
                    'value': config.config_value,
                    'type': config.config_type,
                    'created_at': config.created_at.isoformat(),
                    'updated_at': config.updated_at.isoformat()
                }
            
            # Exportar configuración del sistema
            try:
                system_config = self.get_system_configuration()
                export_data['system_configuration'] = {
                    'currency': system_config.currency,
                    'timezone': system_config.timezone,
                    'date_format': system_config.date_format,
                    'language': system_config.language,
                    'decimal_places': system_config.decimal_places,
                    'tax_rate': str(system_config.tax_rate),
                    'invoice_prefix': system_config.invoice_prefix,
                    'contract_prefix': system_config.contract_prefix
                }
            except SystemConfiguration.DoesNotExist:
                export_data['system_configuration'] = {}
            
            self.logger.info(f"Exported {len(export_data['configurations'])} configurations")
            return export_data
            
        except Exception as e:
            self.logger.error(f"Error exporting configurations: {str(e)}")
            raise
    
    def get_configuration_history(self, key: str, limit: int = 10) -> list:
        """
        Obtiene el historial de cambios de una configuración específica.
        
        Args:
            key: Clave de configuración
            limit: Número máximo de registros a retornar
            
        Returns:
            Lista de cambios históricos
        """
        # Esta funcionalidad requeriría un modelo adicional para auditoría
        # Por ahora retornamos información básica
        try:
            config = self.company.configurations.get(config_key=key)
            return [{
                'key': config.config_key,
                'current_value': config.get_value(),
                'type': config.config_type,
                'created_at': config.created_at.isoformat(),
                'updated_at': config.updated_at.isoformat()
            }]
        except CompanyConfiguration.DoesNotExist:
            return []
    
    def bulk_update_configurations(self, configurations: Dict[str, Dict[str, Any]]) -> Dict[str, bool]:
        """
        Actualiza múltiples configuraciones en una sola transacción.
        
        Args:
            configurations: Diccionario con configuraciones a actualizar
                          Formato: {key: {'value': value, 'type': type}}
        
        Returns:
            Diccionario con el resultado de cada actualización
        """
        results = {}
        
        try:
            with transaction.atomic():
                for key, config_data in configurations.items():
                    try:
                        value = config_data.get('value')
                        config_type = config_data.get('type', 'string')
                        
                        self.set_configuration(key, value, config_type)
                        results[key] = True
                        
                    except Exception as e:
                        self.logger.error(f"Error updating configuration {key}: {str(e)}")
                        results[key] = False
                
                self.logger.info(f"Bulk update completed: {sum(results.values())}/{len(results)} successful")
                
        except Exception as e:
            self.logger.error(f"Error in bulk update: {str(e)}")
            # En caso de error, marcar todas como fallidas
            results = {key: False for key in configurations.keys()}
        
        return results