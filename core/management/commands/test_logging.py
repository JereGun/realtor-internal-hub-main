"""
Management command to test the logging system configuration.

This command verifies that the logging system is properly configured
and can write to all configured handlers.
"""

from django.core.management.base import BaseCommand
from core.logging_config import get_logger
import logging


class Command(BaseCommand):
    help = 'Test the logging system configuration'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--level',
            type=str,
            default='info',
            choices=['debug', 'info', 'warning', 'error', 'critical'],
            help='Log level to test'
        )
    
    def handle(self, *args, **options):
        """Test logging configuration."""
        level = options['level'].upper()
        
        # Test structured logging
        logger = get_logger(__name__)
        
        self.stdout.write(
            self.style.SUCCESS('Testing logging system...')
        )
        
        # Test different log levels
        test_messages = {
            'DEBUG': 'This is a debug message',
            'INFO': 'This is an info message',
            'WARNING': 'This is a warning message',
            'ERROR': 'This is an error message',
            'CRITICAL': 'This is a critical message'
        }
        
        # Test structured logging with business context
        for log_level, message in test_messages.items():
            if hasattr(logger, log_level.lower()):
                getattr(logger, log_level.lower())(
                    message,
                    test_context={'command': 'test_logging', 'level': log_level},
                    property_id=123,
                    contract_id=456,
                    customer_id=789,
                    # Test sensitive data sanitization
                    password='secret123',
                    token='abc123xyz'
                )
        
        # Test Django logging
        django_logger = logging.getLogger('real_estate_management')
        django_logger.info('Testing Django logger integration')
        
        # Test audit logging
        audit_logger = logging.getLogger('audit')
        audit_logger.info('Testing audit logger', extra={
            'user': 'test_user',
            'action': 'test_logging',
            'resource': 'logging_system'
        })
        
        # Test performance logging
        performance_logger = logging.getLogger('performance')
        performance_logger.info('Testing performance logger', extra={
            'duration': 0.123,
            'endpoint': '/test/',
            'method': 'GET'
        })
        
        self.stdout.write(
            self.style.SUCCESS('Logging test completed. Check log files in logs/ directory.')
        )
        
        # Display log file locations
        self.stdout.write('\nLog files created:')
        self.stdout.write('- logs/app.log (general application logs)')
        self.stdout.write('- logs/error.log (error logs)')
        self.stdout.write('- logs/audit.log (audit logs)')
        self.stdout.write('- logs/performance.log (performance logs)')
        
        self.stdout.write(
            self.style.WARNING('\nNote: Some logs may only appear in console during development.')
        )