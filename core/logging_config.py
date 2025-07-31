"""
Logging configuration module for the real estate management system.

This module provides centralized configuration and initialization
for the structured logging system using structlog and Django's
logging framework.
"""

import logging
import logging.config
import structlog
from django.conf import settings
from pathlib import Path


class LoggingConfig:
    """
    Centralized logging configuration class.
    
    This class handles the setup and configuration of both Django's
    logging system and structlog for structured logging throughout
    the application.
    """
    
    @staticmethod
    def configure_structlog():
        """
        Configure structlog with custom processors and settings.
        
        This method sets up structlog with processors for context,
        sanitization, and JSON formatting.
        """
        # Import custom processors
        from .logging.processors import (
            ContextProcessor,
            SanitizationProcessor,
            BusinessContextProcessor
        )
        
        custom_processors = [
            ContextProcessor(),
            SanitizationProcessor(),
            BusinessContextProcessor(),
        ]
        
        # Configure structlog
        structlog.configure(
            processors=[
                *custom_processors,
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer()
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )
    
    @staticmethod
    def configure_django_logging():
        """
        Configure Django's logging system.
        
        This method applies the logging configuration from settings
        and ensures all loggers are properly configured.
        """
        if hasattr(settings, 'LOGGING'):
            logging.config.dictConfig(settings.LOGGING)
        
        # Set up root logger
        root_logger = logging.getLogger()
        if not root_logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            root_logger.addHandler(handler)
            root_logger.setLevel(logging.INFO)
    
    @staticmethod
    def get_logger(name):
        """
        Get a configured logger instance.
        
        Args:
            name (str): Logger name, typically __name__
            
        Returns:
            structlog.BoundLogger: Configured logger instance
        """
        return structlog.get_logger(name)
    
    @staticmethod
    def setup_log_directories():
        """
        Ensure all required log directories exist.
        
        Creates the logs directory and any subdirectories needed
        for different types of logs.
        """
        base_dir = Path(settings.BASE_DIR)
        logs_dir = base_dir / 'logs'
        
        # Create main logs directory
        logs_dir.mkdir(exist_ok=True)
        
        # Create subdirectories for different log types
        subdirs = ['audit', 'performance', 'errors', 'security']
        for subdir in subdirs:
            (logs_dir / subdir).mkdir(exist_ok=True)
    
    @classmethod
    def initialize(cls):
        """
        Initialize the complete logging system.
        
        This method should be called during Django startup to
        configure all logging components.
        """
        # Setup directories
        cls.setup_log_directories()
        
        # Configure Django logging
        cls.configure_django_logging()
        
        # Configure structlog
        cls.configure_structlog()
        
        # Log initialization
        logger = cls.get_logger(__name__)
        logger.info("Logging system initialized", 
                   environment=getattr(settings, 'ENVIRONMENT', 'development'))


def get_logger(name):
    """
    Convenience function to get a configured logger.
    
    Args:
        name (str): Logger name, typically __name__
        
    Returns:
        structlog.BoundLogger: Configured logger instance
    """
    return LoggingConfig.get_logger(name)


# Initialize logging when module is imported
try:
    LoggingConfig.initialize()
except Exception as e:
    # Fallback to basic logging if initialization fails
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logging.getLogger(__name__).error(f"Failed to initialize logging: {e}")