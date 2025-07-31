"""
Tests for logging processors.

This module contains unit tests for the custom logging processors
that handle context, sanitization, and business-specific information.
"""

import unittest
from unittest.mock import Mock, patch
from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from core.logging.processors import (
    ContextProcessor,
    SanitizationProcessor,
    BusinessContextProcessor,
    set_request_context,
    clear_request_context,
    get_request_context
)


class ContextProcessorTest(TestCase):
    """Tests for the ContextProcessor."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.processor = ContextProcessor()
        self.factory = RequestFactory()
        self.User = get_user_model()
        
        # Create a test user
        self.user = self.User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def tearDown(self):
        """Clean up after tests."""
        clear_request_context()
    
    def test_context_processor_without_request(self):
        """Test processor when no request context is available."""
        event_dict = {'event': 'test message'}
        
        result = self.processor(None, 'info', event_dict)
        
        # Should add timestamp and process info
        self.assertIn('timestamp', result)
        self.assertIn('process_id', result)
        self.assertIn('thread_id', result)
        self.assertIn('thread_name', result)
        
        # Should not have request-specific fields
        self.assertNotIn('request_id', result)
        self.assertNotIn('user_id', result)
    
    def test_context_processor_with_request(self):
        """Test processor with request context."""
        request = self.factory.get('/test/')
        request.user = self.user
        request.session = Mock()
        request.session.session_key = 'test_session_key'
        
        set_request_context(request)
        
        event_dict = {'event': 'test message'}
        result = self.processor(None, 'info', event_dict)
        
        # Should add request context
        self.assertIn('request_id', result)
        self.assertEqual(result['user_id'], self.user.id)
        self.assertEqual(result['user_email'], self.user.email)
        self.assertEqual(result['request_method'], 'GET')
        self.assertEqual(result['request_path'], '/test/')
        self.assertEqual(result['session_id'], 'test_session_key')
        self.assertIn('ip_address', result)
        self.assertIn('user_agent', result)
    
    def test_context_processor_with_anonymous_user(self):
        """Test processor with anonymous user."""
        request = self.factory.get('/test/')
        request.user = Mock()
        request.user.is_authenticated = False
        
        set_request_context(request)
        
        event_dict = {'event': 'test message'}
        result = self.processor(None, 'info', event_dict)
        
        # Should not have user-specific fields
        self.assertIsNone(result['user_id'])
        self.assertIsNone(result['user_email'])
    
    def test_get_client_ip_with_forwarded_header(self):
        """Test IP extraction with X-Forwarded-For header."""
        request = self.factory.get('/test/')
        request.META['HTTP_X_FORWARDED_FOR'] = '192.168.1.1, 10.0.0.1'
        
        ip = self.processor._get_client_ip(request)
        self.assertEqual(ip, '192.168.1.1')
    
    def test_get_client_ip_without_forwarded_header(self):
        """Test IP extraction without X-Forwarded-For header."""
        request = self.factory.get('/test/')
        request.META['REMOTE_ADDR'] = '127.0.0.1'
        
        ip = self.processor._get_client_ip(request)
        self.assertEqual(ip, '127.0.0.1')


class SanitizationProcessorTest(TestCase):
    """Tests for the SanitizationProcessor."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.processor = SanitizationProcessor()
    
    def test_sanitize_password_in_message(self):
        """Test sanitization of password in log message."""
        event_dict = {'event': 'User login with password=secret123'}
        
        result = self.processor(None, 'info', event_dict)
        
        self.assertIn('password=***MASKED***', result['event'])
        self.assertNotIn('secret123', result['event'])
    
    def test_sanitize_token_in_message(self):
        """Test sanitization of token in log message."""
        event_dict = {'event': 'API call with token="abc123xyz"'}
        
        result = self.processor(None, 'info', event_dict)
        
        self.assertIn('token=***MASKED***', result['event'])
        self.assertNotIn('abc123xyz', result['event'])
    
    def test_sanitize_sensitive_fields(self):
        """Test sanitization of sensitive fields in event dict."""
        event_dict = {
            'event': 'User action',
            'password': 'secret123',
            'token': 'abc123xyz',
            'api_key': 'key_12345',
            'normal_field': 'normal_value'
        }
        
        result = self.processor(None, 'info', event_dict)
        
        # Sensitive fields should be masked
        self.assertEqual(result['password'], 'se***23')
        self.assertEqual(result['token'], 'ab***yz')
        self.assertEqual(result['api_key'], 'ke***45')
        
        # Normal fields should remain unchanged
        self.assertEqual(result['normal_field'], 'normal_value')
    
    def test_sanitize_nested_dict(self):
        """Test sanitization of nested dictionaries."""
        event_dict = {
            'event': 'User action',
            'user_data': {
                'username': 'testuser',
                'password': 'secret123',
                'profile': {
                    'email': 'test@example.com',
                    'api_key': 'nested_key_123'
                }
            }
        }
        
        result = self.processor(None, 'info', event_dict)
        
        # Check nested sanitization
        self.assertEqual(result['user_data']['password'], 'se***23')
        self.assertEqual(result['user_data']['profile']['api_key'], 'ne***23')
        
        # Non-sensitive fields should remain
        self.assertEqual(result['user_data']['username'], 'testuser')
        self.assertEqual(result['user_data']['profile']['email'], 'test@example.com')
    
    def test_mask_short_values(self):
        """Test masking of short sensitive values."""
        short_value = 'abc'
        masked = self.processor._mask_value(short_value)
        self.assertEqual(masked, '***')
    
    def test_mask_none_value(self):
        """Test masking of None values."""
        masked = self.processor._mask_value(None)
        self.assertIsNone(masked)


class BusinessContextProcessorTest(TestCase):
    """Tests for the BusinessContextProcessor."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.processor = BusinessContextProcessor()
    
    @patch('core.logging.processors.settings')
    def test_add_environment_info(self, mock_settings):
        """Test addition of environment information."""
        mock_settings.ENVIRONMENT = 'test'
        mock_settings.DEBUG = True
        
        event_dict = {'event': 'test message'}
        result = self.processor(None, 'info', event_dict)
        
        self.assertEqual(result['environment'], 'test')
        self.assertTrue(result['debug_mode'])
    
    def test_business_domain_detection(self):
        """Test business domain detection based on logger name."""
        test_cases = [
            ('properties.views', 'property_management'),
            ('contracts.models', 'contract_management'),
            ('customers.services', 'customer_management'),
            ('payments.utils', 'payment_processing'),
            ('accounting.views', 'financial_management'),
            ('agents.forms', 'agent_management'),
            ('core.utils', 'general'),
        ]
        
        for logger_name, expected_domain in test_cases:
            event_dict = {'event': 'test', 'logger': logger_name}
            result = self.processor(None, 'info', event_dict)
            self.assertEqual(result['business_domain'], expected_domain)
    
    def test_entity_id_extraction(self):
        """Test extraction of business entity IDs."""
        event_dict = {
            'event': 'test message',
            'property_id': 123,
            'contract': 456,
            'customer_id': 789,
            'some_other_field': 'value'
        }
        
        result = self.processor(None, 'info', event_dict)
        
        # Should extract entity IDs
        self.assertEqual(result['property_id'], 123)
        self.assertEqual(result['contract_id'], 456)
        self.assertEqual(result['customer_id'], 789)
        
        # Should preserve original fields
        self.assertEqual(result['contract'], 456)
        self.assertEqual(result['some_other_field'], 'value')


class RequestContextTest(TestCase):
    """Tests for request context management functions."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.factory = RequestFactory()
    
    def tearDown(self):
        """Clean up after tests."""
        clear_request_context()
    
    def test_set_and_get_request_context(self):
        """Test setting and getting request context."""
        request = self.factory.get('/test/')
        
        # Initially no context
        self.assertIsNone(get_request_context())
        
        # Set context
        set_request_context(request)
        
        # Should be able to retrieve it
        retrieved_request = get_request_context()
        self.assertEqual(retrieved_request, request)
    
    def test_clear_request_context(self):
        """Test clearing request context."""
        request = self.factory.get('/test/')
        
        # Set context
        set_request_context(request)
        self.assertIsNotNone(get_request_context())
        
        # Clear context
        clear_request_context()
        self.assertIsNone(get_request_context())
    
    def test_multiple_clear_context(self):
        """Test that clearing context multiple times doesn't raise errors."""
        clear_request_context()
        clear_request_context()  # Should not raise an error