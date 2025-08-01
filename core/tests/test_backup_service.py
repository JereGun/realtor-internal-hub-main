"""
Pruebas para el servicio BackupService.

Estas pruebas verifican la funcionalidad del servicio de respaldo y restauración
de configuraciones de empresa.
"""

import json
import tempfile
import os
from django.test import TestCase
from django.core.exceptions import ValidationError
from unittest.mock import patch, mock_open

from core.models import (
    Company, 
    CompanyConfiguration, 
    DocumentTemplate, 
    NotificationSettings, 
    SystemConfiguration
)
from core.services.backup_service import BackupService


class BackupServiceTest(TestCase):
    """Pruebas para el servicio BackupService"""
    
    def setUp(self):
        """Configuración inicial para las pruebas"""
        self.company = Company.objects.create(
            name="Empresa Test S.L.",
            address="Calle Test 123, Madrid",
            phone="+34 912 345 678",
            email="test@empresa.com",
            website="https://www.empresa-test.com",
            tax_id="B12345678"
        )
        self.service = BackupService(self.company)
        
        # Crear datos de prueba
        self._create_test_data()
    
    def _create_test_data(self):
        """Crea datos de prueba para las configuraciones"""
        # Configuraciones generales
        CompanyConfiguration.objects.create(
            company=self.company,
            config_key="test_config",
            config_value="test_value",
            config_type="string"
        )
        
        # Plantilla de documento
        DocumentTemplate.objects.create(
            company=self.company,
            template_name="test_template",
            template_type="invoice",
            header_content="<h1>{{company.name}}</h1>",
            footer_content="<p>Footer</p>",
            custom_css="h1 { color: blue; }",
            is_active=True
        )
        
        # Configuración de notificaciones
        NotificationSettings.objects.create(
            company=self.company,
            notification_type="payment_reminder",
            is_enabled=True,
            email_template="Recordatorio de pago",
            frequency_days=7
        )
        
        # Configuración del sistema
        SystemConfiguration.objects.create(
            company=self.company,
            currency="EUR",
            timezone="Europe/Madrid",
            date_format="DD/MM/YYYY",
            language="es"
        )
    
    def test_export_configurations_success(self):
        """Prueba exportación exitosa de configuraciones"""
        result = self.service.export_configurations()
        
        # Verificar estructura básica
        self.assertIn("backup_info", result)
        self.assertIn("company_data", result)
        self.assertIn("configurations", result)
        self.assertIn("document_templates", result)
        self.assertIn("notification_settings", result)
        self.assertIn("system_configuration", result)
        
        # Verificar información del respaldo
        backup_info = result["backup_info"]
        self.assertEqual(backup_info["version"], "1.0")
        self.assertEqual(backup_info["company_id"], self.company.id)
        self.assertEqual(backup_info["company_name"], self.company.name)
        
        # Verificar datos de empresa
        company_data = result["company_data"]
        self.assertEqual(company_data["name"], "Empresa Test S.L.")
        self.assertEqual(company_data["email"], "test@empresa.com")
        
        # Verificar configuraciones
        configurations = result["configurations"]
        self.assertEqual(len(configurations), 1)
        self.assertEqual(configurations[0]["config_key"], "test_config")
        
        # Verificar plantillas
        templates = result["document_templates"]
        self.assertEqual(len(templates), 1)
        self.assertEqual(templates[0]["template_name"], "test_template")
        
        # Verificar notificaciones
        notifications = result["notification_settings"]
        self.assertEqual(len(notifications), 1)
        self.assertEqual(notifications[0]["notification_type"], "payment_reminder")
        
        # Verificar configuración del sistema
        sys_config = result["system_configuration"]
        self.assertEqual(sys_config["currency"], "EUR")
    
    def test_validate_backup_data_valid(self):
        """Prueba validación de datos de respaldo válidos"""
        valid_backup = {
            "backup_info": {
                "version": "1.0",
                "created_at": "2024-01-01T12:00:00Z",
                "company_id": 1,
                "company_name": "Test Company"
            },
            "company_data": {
                "name": "Test Company",
                "email": "test@test.com"
            },
            "configurations": [],
            "document_templates": [],
            "notification_settings": [],
            "system_configuration": None
        }
        
        is_valid, error_msg = self.service.validate_backup_data(valid_backup)
        
        self.assertTrue(is_valid)
        self.assertIsNone(error_msg)
    
    def test_validate_backup_data_invalid_structure(self):
        """Prueba validación con estructura inválida"""
        invalid_backup = "not a dictionary"
        
        is_valid, error_msg = self.service.validate_backup_data(invalid_backup)
        
        self.assertFalse(is_valid)
        self.assertIn("must be a dictionary", error_msg)
    
    def test_validate_backup_data_missing_backup_info(self):
        """Prueba validación sin información de respaldo"""
        invalid_backup = {
            "company_data": {}
        }
        
        is_valid, error_msg = self.service.validate_backup_data(invalid_backup)
        
        self.assertFalse(is_valid)
        self.assertIn("Missing backup_info", error_msg)
    
    def test_validate_backup_data_unsupported_version(self):
        """Prueba validación con versión no soportada"""
        invalid_backup = {
            "backup_info": {
                "version": "2.0",
                "created_at": "2024-01-01T12:00:00Z",
                "company_id": 1,
                "company_name": "Test"
            }
        }
        
        is_valid, error_msg = self.service.validate_backup_data(invalid_backup)
        
        self.assertFalse(is_valid)
        self.assertIn("Unsupported backup version", error_msg)
    
    def test_import_configurations_success(self):
        """Prueba importación exitosa de configuraciones"""
        # Crear datos de respaldo
        backup_data = {
            "backup_info": {
                "version": "1.0",
                "created_at": "2024-01-01T12:00:00Z",
                "company_id": self.company.id,
                "company_name": self.company.name
            },
            "company_data": {
                "name": "Empresa Actualizada S.L.",
                "phone": "+34 999 888 777"
            },
            "configurations": [
                {
                    "config_key": "new_config",
                    "config_value": "new_value",
                    "config_type": "string"
                }
            ],
            "document_templates": [
                {
                    "template_name": "new_template",
                    "template_type": "contract",
                    "header_content": "<h1>New Template</h1>",
                    "footer_content": "<p>New Footer</p>",
                    "custom_css": "body { margin: 0; }"
                }
            ],
            "notification_settings": [
                {
                    "notification_type": "new_notification",
                    "is_enabled": True,
                    "email_template": "New notification template",
                    "frequency_days": 3
                }
            ],
            "system_configuration": {
                "currency": "USD",
                "timezone": "America/New_York",
                "date_format": "MM/DD/YYYY",
                "language": "en"
            }
        }
        
        result = self.service.import_configurations(backup_data, overwrite_existing=True)
        
        # Verificar resumen de cambios
        self.assertTrue(result["company_data"]["updated"])
        self.assertEqual(result["configurations"]["created"], 1)
        self.assertEqual(result["document_templates"]["created"], 1)
        self.assertEqual(result["notification_settings"]["created"], 1)
        self.assertTrue(result["system_configuration"]["updated"])
        
        # Verificar que los datos se importaron correctamente
        self.company.refresh_from_db()
        self.assertEqual(self.company.name, "Empresa Actualizada S.L.")
        self.assertEqual(self.company.phone, "+34 999 888 777")
        
        # Verificar nueva configuración
        new_config = CompanyConfiguration.objects.get(
            company=self.company, 
            config_key="new_config"
        )
        self.assertEqual(new_config.config_value, "new_value")
        
        # Verificar nueva plantilla
        new_template = DocumentTemplate.objects.get(
            company=self.company,
            template_name="new_template"
        )
        self.assertEqual(new_template.template_type, "contract")
        
        # Verificar nueva notificación
        new_notification = NotificationSettings.objects.get(
            company=self.company,
            notification_type="new_notification"
        )
        self.assertTrue(new_notification.is_enabled)
        
        # Verificar configuración del sistema actualizada
        sys_config = SystemConfiguration.objects.get(company=self.company)
        self.assertEqual(sys_config.currency, "USD")
    
    def test_import_configurations_invalid_backup(self):
        """Prueba importación con respaldo inválido"""
        invalid_backup = {
            "backup_info": {
                "version": "999.0"  # Versión no soportada
            }
        }
        
        with self.assertRaises(ValidationError):
            self.service.import_configurations(invalid_backup)
    
    def test_import_configurations_without_overwrite(self):
        """Prueba importación sin sobrescribir datos existentes"""
        backup_data = {
            "backup_info": {
                "version": "1.0",
                "created_at": "2024-01-01T12:00:00Z",
                "company_id": self.company.id,
                "company_name": self.company.name
            },
            "configurations": [
                {
                    "config_key": "test_config",  # Ya existe
                    "config_value": "updated_value",
                    "config_type": "string"
                }
            ]
        }
        
        result = self.service.import_configurations(backup_data, overwrite_existing=False)
        
        # Verificar que no se actualizó la configuración existente
        self.assertEqual(result["configurations"]["skipped"], 1)
        self.assertEqual(result["configurations"]["updated"], 0)
        
        # Verificar que el valor original se mantiene
        config = CompanyConfiguration.objects.get(
            company=self.company,
            config_key="test_config"
        )
        self.assertEqual(config.config_value, "test_value")  # Valor original
    
    @patch("builtins.open", new_callable=mock_open)
    @patch("json.dump")
    def test_create_backup_file_success(self, mock_json_dump, mock_file):
        """Prueba creación exitosa de archivo de respaldo"""
        file_path = self.service.create_backup_file("test_backup.json")
        
        self.assertEqual(file_path, "test_backup.json")
        mock_file.assert_called_once_with("test_backup.json", 'w', encoding='utf-8')
        mock_json_dump.assert_called_once()
    
    @patch("builtins.open", new_callable=mock_open)
    @patch("json.dump")
    def test_create_backup_file_auto_name(self, mock_json_dump, mock_file):
        """Prueba creación de archivo con nombre automático"""
        with patch('core.services.backup_service.datetime') as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = "20240101_120000"
            
            file_path = self.service.create_backup_file()
            
            expected_name = "backup_Empresa_Test_SL_20240101_120000.json"
            self.assertEqual(file_path, expected_name)
    
    @patch("builtins.open", new_callable=mock_open, read_data='{"test": "data"}')
    @patch("json.load")
    def test_load_backup_file_success(self, mock_json_load, mock_file):
        """Prueba carga exitosa de archivo de respaldo"""
        mock_json_load.return_value = {"test": "data"}
        
        result = self.service.load_backup_file("test_backup.json")
        
        self.assertEqual(result, {"test": "data"})
        mock_file.assert_called_once_with("test_backup.json", 'r', encoding='utf-8')
        mock_json_load.assert_called_once()
    
    @patch("builtins.open", side_effect=FileNotFoundError)
    def test_load_backup_file_not_found(self, mock_file):
        """Prueba carga de archivo inexistente"""
        with self.assertRaises(FileNotFoundError):
            self.service.load_backup_file("nonexistent.json")
    
    @patch("builtins.open", new_callable=mock_open, read_data='invalid json')
    @patch("json.load", side_effect=json.JSONDecodeError("msg", "doc", 0))
    def test_load_backup_file_invalid_json(self, mock_json_load, mock_file):
        """Prueba carga de archivo con JSON inválido"""
        with self.assertRaises(json.JSONDecodeError):
            self.service.load_backup_file("invalid.json")
    
    def test_export_company_data(self):
        """Prueba exportación de datos de empresa"""
        result = self.service._export_company_data()
        
        expected_data = {
            "name": "Empresa Test S.L.",
            "address": "Calle Test 123, Madrid",
            "phone": "+34 912 345 678",
            "email": "test@empresa.com",
            "website": "https://www.empresa-test.com",
            "tax_id": "B12345678"
        }
        
        self.assertEqual(result, expected_data)
    
    def test_export_company_configurations(self):
        """Prueba exportación de configuraciones generales"""
        result = self.service._export_company_configurations()
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["config_key"], "test_config")
        self.assertEqual(result[0]["config_value"], "test_value")
        self.assertEqual(result[0]["config_type"], "string")
    
    def test_export_document_templates(self):
        """Prueba exportación de plantillas de documentos"""
        result = self.service._export_document_templates()
        
        self.assertEqual(len(result), 1)
        template = result[0]
        self.assertEqual(template["template_name"], "test_template")
        self.assertEqual(template["template_type"], "invoice")
        self.assertEqual(template["header_content"], "<h1>{{company.name}}</h1>")
    
    def test_export_notification_settings(self):
        """Prueba exportación de configuraciones de notificaciones"""
        result = self.service._export_notification_settings()
        
        self.assertEqual(len(result), 1)
        setting = result[0]
        self.assertEqual(setting["notification_type"], "payment_reminder")
        self.assertTrue(setting["is_enabled"])
        self.assertEqual(setting["frequency_days"], 7)
    
    def test_export_system_configuration(self):
        """Prueba exportación de configuración del sistema"""
        result = self.service._export_system_configuration()
        
        self.assertIsNotNone(result)
        self.assertEqual(result["currency"], "EUR")
        self.assertEqual(result["timezone"], "Europe/Madrid")
        self.assertEqual(result["date_format"], "DD/MM/YYYY")
        self.assertEqual(result["language"], "es")
    
    def test_export_system_configuration_not_exists(self):
        """Prueba exportación cuando no existe configuración del sistema"""
        # Eliminar configuración del sistema
        SystemConfiguration.objects.filter(company=self.company).delete()
        
        result = self.service._export_system_configuration()
        
        self.assertIsNone(result)
    
    def test_import_company_data_with_overwrite(self):
        """Prueba importación de datos de empresa con sobrescritura"""
        data = {
            "name": "Empresa Actualizada",
            "email": "nuevo@email.com"
        }
        
        result = self.service._import_company_data(data, overwrite=True)
        
        self.assertTrue(result["updated"])
        self.assertEqual(len(result["changes"]), 2)
        
        self.company.refresh_from_db()
        self.assertEqual(self.company.name, "Empresa Actualizada")
        self.assertEqual(self.company.email, "nuevo@email.com")
    
    def test_import_company_data_without_overwrite(self):
        """Prueba importación de datos sin sobrescritura"""
        data = {
            "name": "Empresa Actualizada",
            "address": ""  # Campo vacío, debería actualizarse
        }
        
        result = self.service._import_company_data(data, overwrite=False)
        
        # Solo debería actualizar campos vacíos
        self.company.refresh_from_db()
        self.assertEqual(self.company.name, "Empresa Test S.L.")  # No cambia
        # address podría cambiar si estaba vacío originalmente
    
    def test_validate_section_company_data_valid(self):
        """Prueba validación de sección company_data válida"""
        is_valid, error = self.service._validate_section("company_data", {"name": "Test"})
        
        self.assertTrue(is_valid)
        self.assertIsNone(error)
    
    def test_validate_section_company_data_invalid(self):
        """Prueba validación de sección company_data inválida"""
        is_valid, error = self.service._validate_section("company_data", "not a dict")
        
        self.assertFalse(is_valid)
        self.assertIn("must be a dictionary", error)
    
    def test_validate_section_configurations_valid(self):
        """Prueba validación de sección configurations válida"""
        is_valid, error = self.service._validate_section("configurations", [])
        
        self.assertTrue(is_valid)
        self.assertIsNone(error)
    
    def test_validate_section_configurations_invalid(self):
        """Prueba validación de sección configurations inválida"""
        is_valid, error = self.service._validate_section("configurations", "not a list")
        
        self.assertFalse(is_valid)
        self.assertIn("must be a list", error)