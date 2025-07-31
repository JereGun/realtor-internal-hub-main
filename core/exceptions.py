"""
Custom exceptions for the real estate management system.

This module defines a hierarchy of custom exceptions that provide
better error handling and logging capabilities throughout the application.
"""


class BaseBusinessException(Exception):
    """
    Base exception for all business logic errors in the system.
    
    This exception provides a consistent interface for handling business
    errors with additional context and error codes for better debugging
    and user experience.
    """
    
    def __init__(self, message, error_code=None, context=None):
        """
        Initialize the business exception.
        
        Args:
            message (str): Human-readable error message
            error_code (str, optional): Machine-readable error code
            context (dict, optional): Additional context information
        """
        self.message = message
        self.error_code = error_code
        self.context = context or {}
        super().__init__(self.message)
    
    def to_dict(self):
        """
        Convert exception to dictionary for logging and API responses.
        
        Returns:
            dict: Exception data in dictionary format
        """
        return {
            'error_type': self.__class__.__name__,
            'message': self.message,
            'error_code': self.error_code,
            'context': self.context
        }


class ValidationError(BaseBusinessException):
    """
    Exception raised when data validation fails.
    
    Used for form validation, model validation, and any other
    data validation errors in the system.
    """
    pass


class AuthorizationError(BaseBusinessException):
    """
    Exception raised when user lacks permission for an action.
    
    Used for access control violations and permission-related errors.
    """
    pass


class BusinessLogicError(BaseBusinessException):
    """
    Exception raised when business rules are violated.
    
    Used for domain-specific business rule violations that don't
    fit into other exception categories.
    """
    pass


class ExternalServiceError(BaseBusinessException):
    """
    Exception raised when external service calls fail.
    
    Used for API calls, email services, payment processors,
    and other external service integration errors.
    """
    pass


class PropertyError(BusinessLogicError):
    """
    Exception raised for property-specific business logic errors.
    """
    pass


class ContractError(BusinessLogicError):
    """
    Exception raised for contract-specific business logic errors.
    """
    pass


class PaymentError(BusinessLogicError):
    """
    Exception raised for payment-specific business logic errors.
    """
    pass