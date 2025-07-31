"""
Middleware for logging context management.

This middleware captures request context and makes it available
to logging processors throughout the request lifecycle.
"""

import uuid
import time
from django.utils.deprecation import MiddlewareMixin
from core.logging.processors import set_request_context, clear_request_context
from core.logging_config import get_logger


class LoggingContextMiddleware(MiddlewareMixin):
    """
    Middleware that manages logging context for requests.
    
    This middleware:
    1. Generates unique request IDs
    2. Sets request context for logging processors
    3. Logs request start and completion
    4. Cleans up context after request processing
    """
    
    def __init__(self, get_response=None):
        """Initialize the middleware."""
        super().__init__(get_response)
        self.logger = get_logger(__name__)
    
    def process_request(self, request):
        """
        Process incoming request and set up logging context.
        
        Args:
            request: Django HttpRequest object
        """
        # Generate unique request ID
        request.id = str(uuid.uuid4())
        
        # Record request start time for performance monitoring
        request._logging_start_time = time.time()
        
        # Set request context for logging processors
        set_request_context(request)
        
        # Log request start
        self.logger.info(
            "Request started",
            request_id=request.id,
            method=request.method,
            path=request.path,
            user_id=getattr(request.user, 'id', None) if hasattr(request, 'user') and request.user.is_authenticated else None,
            ip_address=self._get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:200]  # Truncate long user agents
        )
    
    def process_response(self, request, response):
        """
        Process response and log request completion.
        
        Args:
            request: Django HttpRequest object
            response: Django HttpResponse object
            
        Returns:
            HttpResponse: The response object
        """
        # Calculate request duration
        duration = None
        if hasattr(request, '_logging_start_time'):
            duration = time.time() - request._logging_start_time
        
        # Log request completion
        self.logger.info(
            "Request completed",
            request_id=getattr(request, 'id', None),
            method=request.method,
            path=request.path,
            status_code=response.status_code,
            duration=duration,
            user_id=getattr(request.user, 'id', None) if hasattr(request, 'user') and request.user.is_authenticated else None
        )
        
        # Log slow requests
        if duration and duration > 5.0:  # 5 seconds threshold
            self.logger.warning(
                "Slow request detected",
                request_id=getattr(request, 'id', None),
                method=request.method,
                path=request.path,
                duration=duration,
                status_code=response.status_code
            )
        
        # Clear request context
        clear_request_context()
        
        return response
    
    def process_exception(self, request, exception):
        """
        Process exceptions and log them with context.
        
        Args:
            request: Django HttpRequest object
            exception: Exception that occurred
        """
        # Calculate request duration up to exception
        duration = None
        if hasattr(request, '_logging_start_time'):
            duration = time.time() - request._logging_start_time
        
        # Log exception with context
        self.logger.error(
            "Request failed with exception",
            request_id=getattr(request, 'id', None),
            method=request.method,
            path=request.path,
            exception_type=type(exception).__name__,
            exception_message=str(exception),
            duration=duration,
            user_id=getattr(request.user, 'id', None) if hasattr(request, 'user') and request.user.is_authenticated else None,
            exc_info=True
        )
        
        # Don't clear context here - let process_response handle it
        # in case the exception is handled and a response is still generated
        
        return None  # Let Django handle the exception normally
    
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