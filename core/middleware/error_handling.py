"""
Error handling middleware for the real estate management system.

This middleware provides global error handling, logging, and consistent
error responses throughout the application.
"""

import json
import traceback
from django.http import JsonResponse, HttpResponse
from django.template.response import TemplateResponse
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from django.core.exceptions import PermissionDenied, ValidationError as DjangoValidationError
from django.http import Http404
from core.logging_config import get_logger
from core.exceptions import (
    BaseBusinessException,
    ValidationError,
    AuthorizationError,
    BusinessLogicError,
    ExternalServiceError
)


class ErrorHandlingMiddleware(MiddlewareMixin):
    """
    Middleware for global error handling and logging.
    
    This middleware:
    1. Captures unhandled exceptions
    2. Logs errors with full context
    3. Returns appropriate error responses
    4. Sanitizes sensitive information
    5. Notifies administrators of critical errors
    """
    
    def __init__(self, get_response=None):
        """Initialize the middleware."""
        super().__init__(get_response)
        self.logger = get_logger(__name__)
    
    def process_exception(self, request, exception):
        """
        Process unhandled exceptions and return appropriate responses.
        
        Args:
            request: Django HttpRequest object
            exception: Exception that occurred
            
        Returns:
            HttpResponse or None: Error response or None to let Django handle
        """
        # Log the error with full context
        self._log_error(request, exception)
        
        # Determine error type and create appropriate response
        if isinstance(exception, BaseBusinessException):
            return self._handle_business_exception(request, exception)
        elif isinstance(exception, DjangoValidationError):
            return self._handle_validation_error(request, exception)
        elif isinstance(exception, PermissionDenied):
            return self._handle_permission_error(request, exception)
        elif isinstance(exception, Http404):
            return self._handle_not_found_error(request, exception)
        else:
            return self._handle_system_error(request, exception)
    
    def _log_error(self, request, exception):
        """
        Log error with full context information.
        
        Args:
            request: Django HttpRequest object
            exception: Exception that occurred
        """
        # Gather context information
        context = {
            'request_id': getattr(request, 'id', None),
            'user_id': getattr(request.user, 'id', None) if hasattr(request, 'user') and request.user.is_authenticated else None,
            'user_email': getattr(request.user, 'email', None) if hasattr(request, 'user') and request.user.is_authenticated else None,
            'request_method': request.method,
            'request_path': request.path,
            'request_data': self._sanitize_request_data(request),
            'ip_address': self._get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT', '')[:200],
            'exception_type': type(exception).__name__,
            'exception_message': str(exception),
            'exception_module': getattr(exception, '__module__', 'unknown'),
        }
        
        # Add business context if it's a business exception
        if isinstance(exception, BaseBusinessException):
            context.update({
                'error_code': exception.error_code,
                'business_context': exception.context,
                'is_business_error': True
            })
        else:
            context['is_business_error'] = False
        
        # Log with appropriate level
        if isinstance(exception, (Http404, PermissionDenied)):
            # These are expected errors, log as warning
            self.logger.warning(
                "Expected error occurred",
                **context
            )
        elif isinstance(exception, BaseBusinessException):
            # Business errors are usually not critical system issues
            self.logger.error(
                "Business logic error occurred",
                **context
            )
        else:
            # System errors are critical
            self.logger.critical(
                "System error occurred",
                **context,
                exc_info=True  # Include full stack trace
            )
            
            # Notify administrators for critical errors
            self._notify_administrators(request, exception, context)
    
    def _handle_business_exception(self, request, exception):
        """
        Handle business logic exceptions.
        
        Args:
            request: Django HttpRequest object
            exception: BaseBusinessException instance
            
        Returns:
            HttpResponse: Appropriate error response
        """
        error_data = {
            'error': True,
            'error_type': 'business_error',
            'error_code': exception.error_code,
            'message': exception.message,
            'details': exception.context if not settings.DEBUG else exception.context
        }
        
        # Determine HTTP status code based on exception type
        if isinstance(exception, ValidationError):
            status_code = 400  # Bad Request
        elif isinstance(exception, AuthorizationError):
            status_code = 403  # Forbidden
        elif isinstance(exception, ExternalServiceError):
            status_code = 502  # Bad Gateway
        else:
            status_code = 422  # Unprocessable Entity
        
        return self._create_error_response(request, error_data, status_code)
    
    def _handle_validation_error(self, request, exception):
        """
        Handle Django validation errors.
        
        Args:
            request: Django HttpRequest object
            exception: ValidationError instance
            
        Returns:
            HttpResponse: Validation error response
        """
        error_data = {
            'error': True,
            'error_type': 'validation_error',
            'message': 'Validation failed',
            'details': self._format_validation_errors(exception)
        }
        
        return self._create_error_response(request, error_data, 400)
    
    def _handle_permission_error(self, request, exception):
        """
        Handle permission denied errors.
        
        Args:
            request: Django HttpRequest object
            exception: PermissionDenied instance
            
        Returns:
            HttpResponse: Permission error response
        """
        error_data = {
            'error': True,
            'error_type': 'permission_error',
            'message': 'Access denied',
            'details': str(exception) if str(exception) else 'You do not have permission to access this resource'
        }
        
        return self._create_error_response(request, error_data, 403)
    
    def _handle_not_found_error(self, request, exception):
        """
        Handle 404 not found errors.
        
        Args:
            request: Django HttpRequest object
            exception: Http404 instance
            
        Returns:
            HttpResponse: Not found error response
        """
        error_data = {
            'error': True,
            'error_type': 'not_found_error',
            'message': 'Resource not found',
            'details': str(exception) if str(exception) else 'The requested resource was not found'
        }
        
        return self._create_error_response(request, error_data, 404)
    
    def _handle_system_error(self, request, exception):
        """
        Handle system/unexpected errors.
        
        Args:
            request: Django HttpRequest object
            exception: Exception instance
            
        Returns:
            HttpResponse: System error response
        """
        # Don't expose internal error details in production
        if settings.DEBUG:
            error_message = str(exception)
            error_details = {
                'exception_type': type(exception).__name__,
                'traceback': traceback.format_exc()
            }
        else:
            error_message = 'An internal server error occurred'
            error_details = None
        
        error_data = {
            'error': True,
            'error_type': 'system_error',
            'message': error_message,
            'details': error_details
        }
        
        return self._create_error_response(request, error_data, 500)
    
    def _create_error_response(self, request, error_data, status_code):
        """
        Create appropriate error response based on request type.
        
        Args:
            request: Django HttpRequest object
            error_data: Error information dictionary
            status_code: HTTP status code
            
        Returns:
            HttpResponse: Appropriate error response
        """
        # Check if request expects JSON response
        if self._is_ajax_request(request) or self._accepts_json(request):
            return JsonResponse(error_data, status=status_code)
        
        # For HTML requests, render error template
        template_name = f'errors/{status_code}.html'
        fallback_template = 'errors/generic_error.html'
        
        try:
            return TemplateResponse(
                request,
                template_name,
                context={
                    'error_data': error_data,
                    'status_code': status_code
                },
                status=status_code
            )
        except:
            # Fallback to generic error template
            try:
                return TemplateResponse(
                    request,
                    fallback_template,
                    context={
                        'error_data': error_data,
                        'status_code': status_code
                    },
                    status=status_code
                )
            except:
                # Ultimate fallback to simple HTTP response
                return HttpResponse(
                    f"Error {status_code}: {error_data.get('message', 'An error occurred')}",
                    status=status_code,
                    content_type='text/plain'
                )
    
    def _sanitize_request_data(self, request):
        """
        Sanitize request data to remove sensitive information.
        
        Args:
            request: Django HttpRequest object
            
        Returns:
            dict: Sanitized request data
        """
        sensitive_fields = {
            'password', 'token', 'api_key', 'secret', 'authorization',
            'csrf_token', 'csrfmiddlewaretoken', 'credit_card', 'ssn'
        }
        
        def sanitize_dict(data):
            if not isinstance(data, dict):
                return data
            
            sanitized = {}
            for key, value in data.items():
                if key.lower() in sensitive_fields:
                    sanitized[key] = '***SANITIZED***'
                elif isinstance(value, dict):
                    sanitized[key] = sanitize_dict(value)
                else:
                    sanitized[key] = value
            return sanitized
        
        # Sanitize GET and POST data
        sanitized_data = {}
        
        if hasattr(request, 'GET') and request.GET:
            sanitized_data['GET'] = sanitize_dict(dict(request.GET))
        
        if hasattr(request, 'POST') and request.POST:
            sanitized_data['POST'] = sanitize_dict(dict(request.POST))
        
        return sanitized_data
    
    def _format_validation_errors(self, exception):
        """
        Format Django validation errors for response.
        
        Args:
            exception: ValidationError instance
            
        Returns:
            dict or list: Formatted validation errors
        """
        if hasattr(exception, 'error_dict'):
            # Field-specific errors
            return {
                field: [str(error) for error in errors]
                for field, errors in exception.error_dict.items()
            }
        elif hasattr(exception, 'error_list'):
            # General errors
            return [str(error) for error in exception.error_list]
        else:
            # Single error message
            return [str(exception)]
    
    def _is_ajax_request(self, request):
        """
        Check if request is an AJAX request.
        
        Args:
            request: Django HttpRequest object
            
        Returns:
            bool: True if AJAX request
        """
        return (
            request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest' or
            request.path.startswith('/api/')
        )
    
    def _accepts_json(self, request):
        """
        Check if request accepts JSON response.
        
        Args:
            request: Django HttpRequest object
            
        Returns:
            bool: True if accepts JSON
        """
        accept_header = request.META.get('HTTP_ACCEPT', '')
        return 'application/json' in accept_header
    
    def _get_client_ip(self, request):
        """
        Extract client IP address from request.
        
        Args:
            request: Django HttpRequest object
            
        Returns:
            str: Client IP address
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '')
        return ip
    
    def _notify_administrators(self, request, exception, context):
        """
        Notify administrators of critical errors.
        
        Args:
            request: Django HttpRequest object
            exception: Exception that occurred
            context: Error context information
        """
        # This would integrate with notification system
        # For now, we'll just log it as a critical error
        self.logger.critical(
            "Critical error notification",
            notification_type="admin_alert",
            **context
        )
        
        # TODO: Integrate with email notifications, Slack, etc.
        # TODO: Create error report in database
        # TODO: Integrate with external monitoring services