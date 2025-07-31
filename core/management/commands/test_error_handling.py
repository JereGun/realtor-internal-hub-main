"""
Management command to test the error handling system.

This command tests different types of errors and verifies that they
are properly handled, logged, and responded to by the error handling middleware.
"""

from django.core.management.base import BaseCommand
from django.test import RequestFactory
from django.contrib.auth import get_user_model
from core.middleware.error_handling import ErrorHandlingMiddleware
from core.exceptions import (
    ValidationError,
    AuthorizationError,
    BusinessLogicError,
    ExternalServiceError
)
from core.logging_config import get_logger
from unittest.mock import Mock


class Command(BaseCommand):
    help = 'Test the error handling system'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--error-type',
            type=str,
            default='all',
            choices=['all', 'business', 'validation', 'authorization', 'system', 'django'],
            help='Type of error to test'
        )
    
    def handle(self, *args, **options):
        """Test error handling system."""
        error_type = options['error_type']
        
        self.stdout.write(
            self.style.SUCCESS('Testing error handling system...')
        )
        
        # Setup
        factory = RequestFactory()
        User = get_user_model()
        
        # Create test user
        try:
            user = User.objects.get(email='test@example.com')
        except User.DoesNotExist:
            user = User.objects.create_user(
                username='testuser',
                email='test@example.com',
                password='testpass123'
            )
        
        # Create middleware instance
        def mock_get_response(request):
            response = Mock()
            response.status_code = 200
            return response
        
        middleware = ErrorHandlingMiddleware(mock_get_response)
        
        # Test different error types
        if error_type in ['all', 'business']:
            self._test_business_errors(middleware, factory, user)
        
        if error_type in ['all', 'validation']:
            self._test_validation_errors(middleware, factory, user)
        
        if error_type in ['all', 'authorization']:
            self._test_authorization_errors(middleware, factory, user)
        
        if error_type in ['all', 'system']:
            self._test_system_errors(middleware, factory, user)
        
        if error_type in ['all', 'django']:
            self._test_django_errors(middleware, factory, user)
        
        self.stdout.write(
            self.style.SUCCESS('Error handling test completed. Check log files for error entries.')
        )
    
    def _test_business_errors(self, middleware, factory, user):
        """Test business exception handling."""
        self.stdout.write('Testing business errors...')
        
        # Test ValidationError
        request = factory.post('/test/', {'field': 'invalid_value'})
        request.user = user
        request.id = 'test-validation-error'
        
        validation_error = ValidationError(
            "Invalid field value",
            error_code="INVALID_FIELD",
            context={'field': 'field', 'value': 'invalid_value'}
        )
        
        response = middleware.process_exception(request, validation_error)
        self.stdout.write(f'  ✅ ValidationError handled: {response.status_code}')
        
        # Test AuthorizationError
        request = factory.get('/admin/')
        request.user = user
        request.id = 'test-authorization-error'
        
        auth_error = AuthorizationError(
            "Insufficient permissions",
            error_code="INSUFFICIENT_PERMISSIONS",
            context={'required_permission': 'admin_access'}
        )
        
        response = middleware.process_exception(request, auth_error)
        self.stdout.write(f'  ✅ AuthorizationError handled: {response.status_code}')
        
        # Test BusinessLogicError
        request = factory.post('/contracts/', {'property_id': 999})
        request.user = user
        request.id = 'test-business-logic-error'
        
        business_error = BusinessLogicError(
            "Property not available for contract",
            error_code="PROPERTY_NOT_AVAILABLE",
            context={'property_id': 999, 'status': 'sold'}
        )
        
        response = middleware.process_exception(request, business_error)
        self.stdout.write(f'  ✅ BusinessLogicError handled: {response.status_code}')
        
        # Test ExternalServiceError
        request = factory.post('/payments/', {'amount': 1000})
        request.user = user
        request.id = 'test-external-service-error'
        
        external_error = ExternalServiceError(
            "Payment gateway unavailable",
            error_code="PAYMENT_GATEWAY_DOWN",
            context={'gateway': 'stripe', 'error_code': 'connection_timeout'}
        )
        
        response = middleware.process_exception(request, external_error)
        self.stdout.write(f'  ✅ ExternalServiceError handled: {response.status_code}')
    
    def _test_validation_errors(self, middleware, factory, user):
        """Test Django validation error handling."""
        self.stdout.write('Testing Django validation errors...')
        
        from django.core.exceptions import ValidationError as DjangoValidationError
        
        request = factory.post('/test/', {'email': 'invalid-email'})
        request.user = user
        request.id = 'test-django-validation-error'
        
        django_validation_error = DjangoValidationError({
            'email': ['Enter a valid email address.'],
            'password': ['This field is required.']
        })
        
        response = middleware.process_exception(request, django_validation_error)
        self.stdout.write(f'  ✅ Django ValidationError handled: {response.status_code}')
    
    def _test_authorization_errors(self, middleware, factory, user):
        """Test Django permission error handling."""
        self.stdout.write('Testing Django authorization errors...')
        
        from django.core.exceptions import PermissionDenied
        
        request = factory.get('/admin/sensitive/')
        request.user = user
        request.id = 'test-permission-denied'
        
        permission_error = PermissionDenied("You don't have permission to access this resource")
        
        response = middleware.process_exception(request, permission_error)
        self.stdout.write(f'  ✅ PermissionDenied handled: {response.status_code}')
    
    def _test_system_errors(self, middleware, factory, user):
        """Test system error handling."""
        self.stdout.write('Testing system errors...')
        
        # Test generic Exception
        request = factory.get('/test/')
        request.user = user
        request.id = 'test-system-error'
        
        system_error = Exception("Unexpected system error occurred")
        
        response = middleware.process_exception(request, system_error)
        self.stdout.write(f'  ✅ System Exception handled: {response.status_code}')
        
        # Test specific system errors
        request = factory.get('/test/')
        request.user = user
        request.id = 'test-attribute-error'
        
        attribute_error = AttributeError("'NoneType' object has no attribute 'method'")
        
        response = middleware.process_exception(request, attribute_error)
        self.stdout.write(f'  ✅ AttributeError handled: {response.status_code}')
    
    def _test_django_errors(self, middleware, factory, user):
        """Test Django-specific errors."""
        self.stdout.write('Testing Django-specific errors...')
        
        from django.http import Http404
        
        # Test Http404
        request = factory.get('/nonexistent/')
        request.user = user
        request.id = 'test-http-404'
        
        not_found_error = Http404("Property not found")
        
        response = middleware.process_exception(request, not_found_error)
        self.stdout.write(f'  ✅ Http404 handled: {response.status_code}')
    
    def _create_test_request_with_sensitive_data(self, factory, user):
        """Create a test request with sensitive data to test sanitization."""
        request = factory.post('/test/', {
            'username': 'testuser',
            'password': 'secret123',
            'token': 'bearer_token_abc123',
            'api_key': 'api_key_xyz789',
            'normal_field': 'normal_value'
        })
        request.user = user
        request.id = 'test-sensitive-data'
        return request