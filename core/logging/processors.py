"""
Custom processors for structured logging.

This module provides custom processors for structlog that add
context, sanitize sensitive data, and provide business-specific
information to log entries.
"""

import re
import threading
from typing import Dict, Any, Optional
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist


# Thread-local storage for request context
_local = threading.local()


class ContextProcessor:
    """
    Processor that adds request context to log entries.
    
    This processor extracts information from the current request
    and adds it to the log entry for better traceability.
    """
    
    def __call__(self, logger, method_name, event_dict):
        """
        Add request context to the log entry.
        
        Args:
            logger: The logger instance
            method_name: The logging method name (info, error, etc.)
            event_dict: The event dictionary to process
            
        Returns:
            dict: Enhanced event dictionary with context
        """
        # Add request context if available
        request = getattr(_local, 'request', None)
        if request:
            event_dict.update({
                'request_id': getattr(request, 'id', None) or self._generate_request_id(),
                'user_id': getattr(request.user, 'id', None) if hasattr(request, 'user') and request.user.is_authenticated else None,
                'user_email': getattr(request.user, 'email', None) if hasattr(request, 'user') and request.user.is_authenticated else None,
                'ip_address': self._get_client_ip(request),
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                'request_method': request.method,
                'request_path': request.path,
                'session_id': request.session.session_key if hasattr(request, 'session') else None,
            })
        
        # Add timestamp if not present
        if 'timestamp' not in event_dict:
            import datetime
            event_dict['timestamp'] = datetime.datetime.utcnow().isoformat()
        
        # Add process and thread information
        import os
        import threading
        event_dict.update({
            'process_id': os.getpid(),
            'thread_id': threading.get_ident(),
            'thread_name': threading.current_thread().name,
        })
        
        return event_dict
    
    def _generate_request_id(self):
        """Generate a unique request ID."""
        import uuid
        return str(uuid.uuid4())
    
    def _get_client_ip(self, request):
        """Extract client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class SanitizationProcessor:
    """
    Processor that sanitizes sensitive data from log entries.
    
    This processor removes or masks sensitive information like
    passwords, tokens, and personal data from log entries.
    """
    
    # Patterns for sensitive data
    SENSITIVE_PATTERNS = [
        (re.compile(r'password["\']?\s*[:=]\s*["\']?([^"\'}\s,]+)', re.IGNORECASE), 'password'),
        (re.compile(r'token["\']?\s*[:=]\s*["\']?([^"\'}\s,]+)', re.IGNORECASE), 'token'),
        (re.compile(r'api[_-]?key["\']?\s*[:=]\s*["\']?([^"\'}\s,]+)', re.IGNORECASE), 'api_key'),
        (re.compile(r'secret["\']?\s*[:=]\s*["\']?([^"\'}\s,]+)', re.IGNORECASE), 'secret'),
        (re.compile(r'authorization["\']?\s*[:=]\s*["\']?([^"\'}\s,]+)', re.IGNORECASE), 'authorization'),
    ]
    
    # Fields that should be sanitized
    SENSITIVE_FIELDS = {
        'password', 'token', 'api_key', 'secret', 'authorization',
        'credit_card', 'ssn', 'social_security', 'passport',
        'csrf_token', 'csrfmiddlewaretoken'
    }
    
    def __call__(self, logger, method_name, event_dict):
        """
        Sanitize sensitive data from the log entry.
        
        Args:
            logger: The logger instance
            method_name: The logging method name
            event_dict: The event dictionary to process
            
        Returns:
            dict: Sanitized event dictionary
        """
        # Sanitize the main event message
        if 'event' in event_dict:
            event_dict['event'] = self._sanitize_string(event_dict['event'])
        
        # Sanitize all dictionary values
        event_dict = self._sanitize_dict(event_dict)
        
        return event_dict
    
    def _sanitize_dict(self, data):
        """
        Recursively sanitize a dictionary.
        
        Args:
            data: Dictionary to sanitize
            
        Returns:
            dict: Sanitized dictionary
        """
        if not isinstance(data, dict):
            return data
        
        sanitized = {}
        for key, value in data.items():
            # Check if key is sensitive
            if key.lower() in self.SENSITIVE_FIELDS:
                sanitized[key] = self._mask_value(value)
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_dict(value)
            elif isinstance(value, list):
                sanitized[key] = [self._sanitize_dict(item) if isinstance(item, dict) else item for item in value]
            elif isinstance(value, str):
                sanitized[key] = self._sanitize_string(value)
            else:
                sanitized[key] = value
        
        return sanitized
    
    def _sanitize_string(self, text):
        """
        Sanitize sensitive patterns in a string.
        
        Args:
            text: String to sanitize
            
        Returns:
            str: Sanitized string
        """
        if not isinstance(text, str):
            return text
        
        for pattern, field_type in self.SENSITIVE_PATTERNS:
            text = pattern.sub(f'{field_type}=***MASKED***', text)
        
        return text
    
    def _mask_value(self, value):
        """
        Mask a sensitive value.
        
        Args:
            value: Value to mask
            
        Returns:
            str: Masked value
        """
        if value is None:
            return None
        
        value_str = str(value)
        if len(value_str) <= 4:
            return '***'
        else:
            return f"{value_str[:2]}***{value_str[-2:]}"


class BusinessContextProcessor:
    """
    Processor that adds business-specific context to log entries.
    
    This processor adds context specific to the real estate
    management domain, such as property IDs, contract information,
    and customer details.
    """
    
    def __call__(self, logger, method_name, event_dict):
        """
        Add business context to the log entry.
        
        Args:
            logger: The logger instance
            method_name: The logging method name
            event_dict: The event dictionary to process
            
        Returns:
            dict: Enhanced event dictionary with business context
        """
        # Add business context based on logger name
        logger_name = event_dict.get('logger', '')
        
        if 'properties' in logger_name:
            event_dict['business_domain'] = 'property_management'
        elif 'contracts' in logger_name:
            event_dict['business_domain'] = 'contract_management'
        elif 'customers' in logger_name:
            event_dict['business_domain'] = 'customer_management'
        elif 'payments' in logger_name:
            event_dict['business_domain'] = 'payment_processing'
        elif 'accounting' in logger_name:
            event_dict['business_domain'] = 'financial_management'
        elif 'agents' in logger_name:
            event_dict['business_domain'] = 'agent_management'
        else:
            event_dict['business_domain'] = 'general'
        
        # Extract business entity IDs from context
        self._extract_entity_ids(event_dict)
        
        # Add environment information
        from django.conf import settings
        event_dict['environment'] = getattr(settings, 'ENVIRONMENT', 'unknown')
        event_dict['debug_mode'] = getattr(settings, 'DEBUG', False)
        
        return event_dict
    
    def _extract_entity_ids(self, event_dict):
        """
        Extract business entity IDs from the event context.
        
        Args:
            event_dict: Event dictionary to enhance
        """
        # Look for common entity IDs in the event data
        entity_patterns = {
            'property_id': ['property_id', 'property', 'prop_id'],
            'contract_id': ['contract_id', 'contract', 'cont_id'],
            'customer_id': ['customer_id', 'customer', 'client_id'],
            'agent_id': ['agent_id', 'agent', 'user_id'],
            'payment_id': ['payment_id', 'payment', 'pay_id'],
            'invoice_id': ['invoice_id', 'invoice', 'inv_id'],
        }
        
        for entity_type, possible_keys in entity_patterns.items():
            for key in possible_keys:
                if key in event_dict and event_dict[key]:
                    event_dict[entity_type] = event_dict[key]
                    break


def set_request_context(request):
    """
    Set the current request in thread-local storage.
    
    This function should be called by middleware to make
    request context available to the ContextProcessor.
    
    Args:
        request: Django request object
    """
    _local.request = request


def clear_request_context():
    """
    Clear the request context from thread-local storage.
    
    This function should be called after request processing
    is complete to prevent memory leaks.
    """
    if hasattr(_local, 'request'):
        delattr(_local, 'request')


def get_request_context():
    """
    Get the current request from thread-local storage.
    
    Returns:
        HttpRequest or None: Current request object
    """
    return getattr(_local, 'request', None)