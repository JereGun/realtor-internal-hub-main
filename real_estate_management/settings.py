"""
Django settings for real_estate_management project.
"""

from pathlib import Path
import os
from decouple import config
from celery import Celery

# Initialize Celery
app = Celery('real_estate_management')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY', default='django-insecure-your-secret-key-here')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=True, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=lambda v: [s.strip() for s in v.split(',')])

# Celery Configuration
CELERY_BROKER_URL = config('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND', default='redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'America/Argentina/Buenos_Aires'

# Celery Beat Configuration for Notification Tasks
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    # Contract expiration notifications - daily at 8:00 AM
    'check-contract-expirations': {
        'task': 'user_notifications.tasks.check_contract_expirations',
        'schedule': crontab(hour=8, minute=0),
        'options': {
            'expires': 3600,  # Task expires after 1 hour if not executed
            'retry': True,
            'retry_policy': {
                'max_retries': 3,
                'interval_start': 0,
                'interval_step': 0.2,
                'interval_max': 0.2,
            }
        }
    },
    
    # Invoice overdue notifications - daily at 9:00 AM
    'check-invoice-overdue': {
        'task': 'user_notifications.tasks.check_invoice_overdue',
        'schedule': crontab(hour=9, minute=0),
        'options': {
            'expires': 3600,
            'retry': True,
            'retry_policy': {
                'max_retries': 3,
                'interval_start': 0,
                'interval_step': 0.2,
                'interval_max': 0.2,
            }
        }
    },
    
    # Rent increase notifications - daily at 10:00 AM
    'check-rent-increases': {
        'task': 'user_notifications.tasks.check_rent_increases',
        'schedule': crontab(hour=10, minute=0),
        'options': {
            'expires': 3600,
            'retry': True,
            'retry_policy': {
                'max_retries': 3,
                'interval_start': 0,
                'interval_step': 0.2,
                'interval_max': 0.2,
            }
        }
    },
    
    # Invoice due soon notifications - daily at 11:00 AM
    'check-invoice-due-soon': {
        'task': 'user_notifications.tasks.check_invoice_due_soon',
        'schedule': crontab(hour=11, minute=0),
        'options': {
            'expires': 3600,
            'retry': True,
            'retry_policy': {
                'max_retries': 3,
                'interval_start': 0,
                'interval_step': 0.2,
                'interval_max': 0.2,
            }
        }
    },
    
    # Process notification batches - daily at 6:00 PM
    'process-notification-batches': {
        'task': 'user_notifications.tasks.process_notification_batches',
        'schedule': crontab(hour=18, minute=0),
        'options': {
            'expires': 3600,
            'retry': True,
            'retry_policy': {
                'max_retries': 3,
                'interval_start': 0,
                'interval_step': 0.2,
                'interval_max': 0.2,
            }
        }
    },
}

# Additional Celery configuration for monitoring and failure handling
CELERY_TASK_ROUTES = {
    'user_notifications.tasks.*': {'queue': 'notifications'},
}

CELERY_TASK_ANNOTATIONS = {
    'user_notifications.tasks.*': {
        'rate_limit': '10/m',  # Limit notification tasks to 10 per minute
        'time_limit': 300,     # 5 minute time limit
        'soft_time_limit': 240, # 4 minute soft time limit
    }
}

# Task result expiration
CELERY_RESULT_EXPIRES = 3600  # Results expire after 1 hour

# Worker configuration
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_WORKER_MAX_TASKS_PER_CHILD = 1000

# Error handling
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_TASK_ACKS_LATE = True

# Application definition
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'django.contrib.sites',  # Agregado para el modelo Site
]

# Configuración del modelo Site
SITE_ID = 1

LOCAL_APPS = [
    'public',
    'agents',
    'properties',
    'customers',
    'contracts',
    'payments',
    'user_notifications',
    'core',
    'accounting',
    'locations',
]

THIRD_PARTY_APPS = [
    'crispy_forms',
    'crispy_bootstrap4',
    'rest_framework',  # Agregada DRF
    'celery',
    'django_celery_beat',  # For database-backed periodic tasks
    'widget_tweaks',  # For template form field customization
]

INSTALLED_APPS = DJANGO_APPS + LOCAL_APPS + THIRD_PARTY_APPS

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'core.middleware.logging_middleware.LoggingContextMiddleware',
    'core.middleware.error_handling.ErrorHandlingMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'agents.middleware.security_middleware.SecurityMiddleware',
    # 'agents.middleware.audit_middleware.AuditMiddleware',  # Temporalmente deshabilitado para debug
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'real_estate_management.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'user_notifications.context_processors.unread_notifications_count',
                'core.context_processors.configuration_status',
                'core.context_processors.company_data',
            ],
        },
    },
]

WSGI_APPLICATION = 'real_estate_management.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME', default='test'),
        'USER': config('DB_USER', default='testuser'),
        'PASSWORD': config('DB_PASSWORD', default='password'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'es-es'
TIME_ZONE = 'America/Argentina/Buenos_Aires'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom User Model
AUTH_USER_MODEL = 'agents.Agent'

# Login URLs
LOGIN_URL = '/agents/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/agents/login/'

# Crispy Forms
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap4"
CRISPY_TEMPLATE_PACK = "bootstrap4"

# Email settings (using Gmail SMTP)
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='noreply@tuempresa.com')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@tuempresa.com')

# Logging Configuration
# Create logs directory if it doesn't exist
LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(exist_ok=True)

# Environment-specific configuration
ENVIRONMENT = config('ENVIRONMENT', default='development')

# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {name} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {asctime} {name} {message}',
            'style': '{',
        },
        'json': {
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'format': '%(asctime)s %(name)s %(levelname)s %(message)s %(pathname)s %(lineno)d %(funcName)s'
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'filters': ['require_debug_true'],
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'app.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'formatter': 'json',
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'error.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'formatter': 'json',
        },
        'audit_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'audit.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 10,
            'formatter': 'json',
        },
        'performance_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'performance.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'formatter': 'json',
        },
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler',
            'formatter': 'verbose'
        }
    },
    'root': {
        'level': 'INFO',
        'handlers': ['console', 'file'],
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file', 'mail_admins'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['error_file', 'mail_admins'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['error_file', 'mail_admins'],
            'level': 'ERROR',
            'propagate': False,
        },
        'real_estate_management': {
            'handlers': ['console', 'file', 'error_file'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
        'audit': {
            'handlers': ['audit_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'performance': {
            'handlers': ['performance_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'security': {
            'handlers': ['error_file', 'mail_admins'],
            'level': 'WARNING',
            'propagate': False,
        },
        # Application-specific loggers
        'agents': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True,
        },
        'properties': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True,
        },
        'contracts': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True,
        },
        'customers': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True,
        },
        'payments': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True,
        },
        'accounting': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True,
        },
        'user_notifications': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True,
        },
        'celery': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True,
        },
        'celery.task': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True,
        },
    }
}

# Sentry configuration (will be configured in next task)
SENTRY_DSN = config('SENTRY_DSN', default='')
SENTRY_ENVIRONMENT = ENVIRONMENT

# Structlog configuration
STRUCTLOG_CONFIG = {
    'processors': [
        'structlog.stdlib.filter_by_level',
        'structlog.stdlib.add_logger_name',
        'structlog.stdlib.add_log_level',
        'structlog.stdlib.PositionalArgumentsFormatter',
        'structlog.processors.TimeStamper',
        'structlog.processors.StackInfoRenderer',
        'structlog.processors.format_exc_info',
        'structlog.processors.UnicodeDecoder',
        'structlog.processors.JSONRenderer'
    ],
    'context_class': dict,
    'logger_factory': 'structlog.stdlib.LoggerFactory',
    'wrapper_class': 'structlog.stdlib.BoundLogger',
    'cache_logger_on_first_use': True,
}

# Error handling configuration
ERROR_HANDLING_CONFIG = {
    'capture_unhandled_exceptions': True,
    'log_stack_trace_in_production': False,
    'sanitize_sensitive_data': True,
    'notify_admins_on_error': True,
    'error_response_format': 'json',
}

# Performance monitoring configuration
PERFORMANCE_MONITORING_CONFIG = {
    'enabled': True,
    'slow_request_threshold': 5.0,  # seconds
    'log_sql_queries': DEBUG,
    'monitor_memory_usage': True,
    'alert_thresholds': {
        'response_time': 10.0,  # seconds
        'memory_usage': 80,     # percentage
        'error_rate': 5,        # errors per minute
    }
}
