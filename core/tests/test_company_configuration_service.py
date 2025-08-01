"""
Pruebas para el servicio CompanyConfigurationService.

Estas pruebas verifican la funcionalidad del servicio de configuración
de empresa, incluyendo operaciones CRUD, validación y aplicación de
configuraciones del sistema.
"""

from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from unittest.mock import patch, MagicMock
import json

from core.models import Company, CompanyConfiguration, SystemConfiguration
from core.services.company_configuration_service import CompanyConfigurationService


class CompanyConfigurationServiceTest(TestCase):
    """Pruebas para el servicio CompanyConfigurationService"""
    
    def setUp(self):
        """Configuración inicial para las pruebas"""
        self.company = Company.objects.create(
            name="Test Company",
            email="test@company.com",
            address="Test Address 123",
            phone="+34 123 456 789"
        )
        self.service = CompanyConfigurationService(self.company)
    
    def test_service_initialization(self):
        """Prueba inicialización del servicio"""
        self.assertEqual(self.service.company, self.company)
        self.assertIsNotNone(self.service.logger)
    
    def test_get_configuration_existing(self):
        """Prueba obtención de configuración existente"""
        # Crear configuración de prueba
        CompanyConfiguration.objects.create(
            company=self.company,
            config_key="test_key",
            config_value="test_value",
            config_type="string"
        )
        
        result = self.service.get_configuration("test_key")
        self.assertEqual(result, "test_value")
    
    def test_get_configuration_non_existing(self):
        """Prueba obtención de configuración no existente"""
        result = self.service.get_configuration("non_existing_key", "default_value")
        self.assertEqual(result, "default_value")
        
        result = self.service.get_configuration("non_existing_key")
        self.assertIsNone(result)
    
    def test_set_configuration_new(self):
        """Prueba establecimiento de nueva configuración"""
        config = self.service.set_configuration("new_key", "new_value", "string")
        
        self.assertIsInstance(config, CompanyConfiguration)
        self.assertEqual(config.config_key, "new_key")
        self.assertEqual(config.get_value(), "new_value")
        self.assertEqual(config.config_type, "string")
    
    def test_set_configuration_update_existing(self):
        """Prueba actualización de configuración existente"""
        # Crear configuración inicial
        CompanyConfiguration.objects.create(
            company=self.company,
            config_key="update_key",
            config_value="old_value",
            config_type="string"
        )
        
        # Actualizar configuración
        config = self.service.set_configuration("update_key", "new_value", "string")
        
        self.assertEqual(config.get_value(), "new_value")
        # Verificar que solo hay una configuración con esta clave
        self.assertEqual(
            CompanyConfiguration.objects.filter(
                company=self.company, 
                config_key="update_key"
            ).count(), 
            1
        )
    
    def test_set_configuration_change_type(self):
        """Prueba cambio de tipo de configuración existente"""
        # Crear configuración como string
        CompanyConfiguration.objects.create(
            company=self.company,
            config_key="type_change_key",
            config_value="123",
            config_type="string"
        )
        
        # Cambiar a integer
        config = self.service.set_configuration("type_change_key", 456, "integer")
        
        self.assertEqual(config.config_type, "integer")
        self.assertEqual(config.get_value(), 456)
    
    def test_get_all_configurations(self):
        """Prueba obtención de todas las configuraciones"""
        # Crear múltiples configuraciones
        CompanyConfiguration.objects.create(
            company=self.company,
            config_key="key1",
            config_value="value1",
            config_type="string"
        )
        CompanyConfiguration.objects.create(
            company=self.company,
            config_key="key2",
            config_value="true",
            config_type="boolean"
        )
        CompanyConfiguration.objects.create(
            company=self.company,
            config_key="key3",
            config_value="42",
            config_type="integer"
        )
        
        configs = self.service.get_all_configurations()
        
        self.assertEqual(len(configs), 3)
        self.assertEqual(configs["key1"], "value1")
        self.assertTrue(configs["key2"])
        self.assertEqual(configs["key3"], 42)
    
    def test_delete_configuration_existing(self):
        """Prueba eliminación de configuración existente"""
        CompanyConfiguration.objects.create(
            company=self.company,
            config_key="delete_key",
            config_value="delete_value",
            config_type="string"
        )
        
        result = self.service.delete_configuration("delete_key")
        self.assertTrue(result)
        
        # Verificar que se eliminó
        self.assertFalse(
            CompanyConfiguration.objects.filter(
                company=self.company,
                config_key="delete_key"
            ).exists()
        )
    
    def test_delete_configuration_non_existing(self):
        """Prueba eliminación de configuración no existente"""
        result = self.service.delete_configuration("non_existing_key")
        self.assertFalse(result)
    
    def test_validate_configuration_string(self):
        """Prueba validación de configuración tipo string"""
        self.assertTrue(self.service.validate_configuration("key", "string_value", "string"))
        self.assertTrue(self.service.validate_configuration("key", 123, "string"))
        self.assertTrue(self.service.validate_configuration("key", 3.14, "string"))
        self.assertTrue(self.service.validate_configuration("key", None, "string"))
    
    def test_validate_configuration_boolean(self):
        """Prueba validación de configuración tipo boolean"""
        # Valores válidos
        self.assertTrue(self.service.validate_configuration("key", True, "boolean"))
        self.assertTrue(self.service.validate_configuration("key", False, "boolean"))
        self.assertTrue(self.service.validate_configuration("key", "true", "boolean"))
        self.assertTrue(self.service.validate_configuration("key", "false", "boolean"))
        self.assertTrue(self.service.validate_configuration("key", "1", "boolean"))
        self.assertTrue(self.service.validate_configuration("key", "0", "boolean"))
        self.assertTrue(self.service.validate_configuration("key", "yes", "boolean"))
        self.assertTrue(self.service.validate_configuration("key", "no", "boolean"))
        
        # Valores inválidos
        self.assertFalse(self.service.validate_configuration("key", "invalid", "boolean"))
        self.assertFalse(self.service.validate_configuration("key", 123, "boolean"))
    
    def test_validate_configuration_integer(self):
        """Prueba validación de configuración tipo integer"""
        self.assertTrue(self.service.validate_configuration("key", 123, "integer"))
        self.assertTrue(self.service.validate_configuration("key", "456", "integer"))
        self.assertTrue(self.service.validate_configuration("key", "0", "integer"))
        
        self.assertFalse(self.service.validate_configuration("key", "invalid", "integer"))
        self.assertFalse(self.service.validate_configuration("key", "3.14", "integer"))
    
    def test_validate_configuration_decimal(self):
        """Prueba validación de configuración tipo decimal"""
        self.assertTrue(self.service.validate_configuration("key", 3.14, "decimal"))
        self.assertTrue(self.service.validate_configuration("key", "2.71", "decimal"))
        self.assertTrue(self.service.validate_configuration("key", 42, "decimal"))
        self.assertTrue(self.service.validate_configuration("key", "0", "decimal"))
        
        self.assertFalse(self.service.validate_configuration("key", "invalid", "decimal"))
    
    def test_validate_configuration_json(self):
        """Prueba validación de configuración tipo JSON"""
        self.assertTrue(self.service.validate_configuration("key", {"test": "data"}, "json"))
        self.assertTrue(self.service.validate_configuration("key", [1, 2, 3], "json"))
        self.assertTrue(self.service.validate_configuration("key", '{"valid": "json"}', "json"))
        
        self.assertFalse(self.service.validate_configuration("key", "invalid json", "json"))
        self.assertFalse(self.service.validate_configuration("key", 123, "json"))
    
    def test_validate_configuration_file(self):
        """Prueba validación de configuración tipo file"""
        self.assertTrue(self.service.validate_configuration("key", "/path/to/file.txt", "file"))
        self.assertTrue(self.service.validate_configuration("key", "filename.jpg", "file"))
        
        self.assertFalse(self.service.validate_configuration("key", 123, "file"))
    
    def test_validate_configuration_unknown_type(self):
        """Prueba validación con tipo desconocido"""
        self.assertFalse(self.service.validate_configuration("key", "value", "unknown_type"))
    
    def test_set_configuration_invalid_value(self):
        """Prueba establecimiento de configuración con valor inválido"""
        with self.assertRaises(ValidationError):
            self.service.set_configuration("key", "invalid", "integer")
    
    def test_get_system_configuration(self):
        """Prueba obtención de configuración del sistema"""
        system_config = self.service.get_system_configuration()
        
        self.assertIsInstance(system_config, SystemConfiguration)
        self.assertEqual(system_config.company, self.company)
    
    def test_update_system_configuration(self):
        """Prueba actualización de configuración del sistema"""
        updated_config = self.service.update_system_configuration(
            currency="USD",
            timezone="America/New_York",
            language="en"
        )
        
        self.assertEqual(updated_config.currency, "USD")
        self.assertEqual(updated_config.timezone, "America/New_York")
        self.assertEqual(updated_config.language, "en")
    
    def test_update_system_configuration_invalid_field(self):
        """Prueba actualización con campo inválido"""
        # No debe fallar, solo debe ignorar campos desconocidos
        updated_config = self.service.update_system_configuration(
            currency="USD",
            invalid_field="invalid_value"
        )
        
        self.assertEqual(updated_config.currency, "USD")
        self.assertFalse(hasattr(updated_config, 'invalid_field'))
    
    @patch.dict('os.environ', {}, clear=True)
    def test_apply_system_configurations(self):
        """Prueba aplicación de configuraciones del sistema"""
        # Crear configuración del sistema
        SystemConfiguration.objects.create(
            company=self.company,
            currency="USD",
            timezone="America/New_York",
            date_format="MM/DD/YYYY",
            language="en",
            decimal_places=3
        )
        
        result = self.service.apply_system_configurations()
        self.assertTrue(result)
        
        # Verificar que se aplicaron las configuraciones
        self.assertEqual(self.service.get_configuration("active_currency"), "USD")
        self.assertEqual(self.service.get_configuration("active_date_format"), "MM/DD/YYYY")
        self.assertEqual(self.service.get_configuration("active_language"), "en")
        self.assertEqual(self.service.get_configuration("active_decimal_places"), 3)
        
        # Verificar que se registró la aplicación
        self.assertIsNotNone(self.service.get_configuration("last_config_applied"))
    
    def test_export_configurations(self):
        """Prueba exportación de configuraciones"""
        # Crear configuraciones de prueba
        CompanyConfiguration.objects.create(
            company=self.company,
            config_key="export_key1",
            config_value="export_value1",
            config_type="string"
        )
        CompanyConfiguration.objects.create(
            company=self.company,
            config_key="export_key2",
            config_value="true",
            config_type="boolean"
        )
        
        # Crear configuración del sistema
        SystemConfiguration.objects.create(
            company=self.company,
            currency="USD",
            timezone="America/New_York"
        )
        
        export_data = self.service.export_configurations()
        
        self.assertEqual(export_data['company_id'], self.company.id)
        self.assertEqual(export_data['company_name'], self.company.name)
        self.assertIn('export_timestamp', export_data)
        
        # Verificar configuraciones exportadas
        self.assertIn('export_key1', export_data['configurations'])
        self.assertIn('export_key2', export_data['configurations'])
        
        # Verificar configuración del sistema
        self.assertEqual(export_data['system_configuration']['currency'], "USD")
        self.assertEqual(export_data['system_configuration']['timezone'], "America/New_York")
    
    def test_get_configuration_history(self):
        """Prueba obtención de historial de configuración"""
        CompanyConfiguration.objects.create(
            company=self.company,
            config_key="history_key",
            config_value="history_value",
            config_type="string"
        )
        
        history = self.service.get_configuration_history("history_key")
        
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]['key'], "history_key")
        self.assertEqual(history[0]['current_value'], "history_value")
        self.assertEqual(history[0]['type'], "string")
    
    def test_get_configuration_history_non_existing(self):
        """Prueba historial de configuración no existente"""
        history = self.service.get_configuration_history("non_existing_key")
        self.assertEqual(len(history), 0)
    
    def test_bulk_update_configurations(self):
        """Prueba actualización masiva de configuraciones"""
        configurations = {
            "bulk_key1": {"value": "bulk_value1", "type": "string"},
            "bulk_key2": {"value": True, "type": "boolean"},
            "bulk_key3": {"value": 42, "type": "integer"}
        }
        
        results = self.service.bulk_update_configurations(configurations)
        
        # Verificar que todas las actualizaciones fueron exitosas
        self.assertTrue(all(results.values()))
        self.assertEqual(len(results), 3)
        
        # Verificar que se crearon las configuraciones
        self.assertEqual(self.service.get_configuration("bulk_key1"), "bulk_value1")
        self.assertTrue(self.service.get_configuration("bulk_key2"))
        self.assertEqual(self.service.get_configuration("bulk_key3"), 42)
    
    def test_bulk_update_configurations_with_errors(self):
        """Prueba actualización masiva con errores"""
        configurations = {
            "valid_key": {"value": "valid_value", "type": "string"},
            "invalid_key": {"value": "invalid", "type": "integer"}  # Valor inválido
        }
        
        results = self.service.bulk_update_configurations(configurations)
        
        # La clave válida debe ser exitosa, la inválida debe fallar
        self.assertTrue(results["valid_key"])
        self.assertFalse(results["invalid_key"])
        
        # Verificar que la configuración válida se creó
        self.assertEqual(self.service.get_configuration("valid_key"), "valid_value")
        self.assertIsNone(self.service.get_configuration("invalid_key"))


class CompanyConfigurationServiceIntegrationTest(TestCase):
    """Pruebas de integración para CompanyConfigurationService"""
    
    def setUp(self):
        """Configuración inicial para las pruebas de integración"""
        self.company = Company.objects.create(
            name="Integration Test Company",
            email="integration@test.com"
        )
        self.service = CompanyConfigurationService(self.company)
    
    def test_complete_configuration_workflow(self):
        """Prueba flujo completo de configuración"""
        # 1. Establecer configuraciones iniciales
        self.service.set_configuration("app_name", "Real Estate Manager", "string")
        self.service.set_configuration("max_properties", 1000, "integer")
        self.service.set_configuration("notifications_enabled", True, "boolean")
        
        # 2. Actualizar configuración del sistema
        self.service.update_system_configuration(
            currency="EUR",
            timezone="Europe/Madrid",
            language="es"
        )
        
        # 3. Aplicar configuraciones del sistema
        result = self.service.apply_system_configurations()
        self.assertTrue(result)
        
        # 4. Verificar todas las configuraciones
        all_configs = self.service.get_all_configurations()
        self.assertGreaterEqual(len(all_configs), 3)
        self.assertEqual(all_configs["app_name"], "Real Estate Manager")
        self.assertEqual(all_configs["max_properties"], 1000)
        self.assertTrue(all_configs["notifications_enabled"])
        
        # 5. Exportar configuraciones
        export_data = self.service.export_configurations()
        self.assertIn("app_name", export_data["configurations"])
        self.assertEqual(export_data["system_configuration"]["currency"], "EUR")
        
        # 6. Actualización masiva
        bulk_updates = {
            "app_version": {"value": "1.0.0", "type": "string"},
            "debug_mode": {"value": False, "type": "boolean"}
        }
        results = self.service.bulk_update_configurations(bulk_updates)
        self.assertTrue(all(results.values()))
        
        # Verificar estado final
        final_configs = self.service.get_all_configurations()
        self.assertEqual(final_configs["app_version"], "1.0.0")
        self.assertFalse(final_configs["debug_mode"])