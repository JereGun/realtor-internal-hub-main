# Initialize logging system when core app is loaded
try:
    from .logging_config import LoggingConfig
    # Logging will be initialized when the module is imported
except ImportError:
    # Fallback if logging config is not available
    import logging
    logging.basicConfig(level=logging.INFO)