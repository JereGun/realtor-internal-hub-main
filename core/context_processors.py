"""
Context processors for the core application.

Provides global template variables for configuration-related functionality.
"""

from django.conf import settings
from .models import Company, CompanyConfiguration, SystemConfiguration, DocumentTemplate, NotificationSettings


def configuration_status(request):
    """
    Context processor that provides configuration status information.
    
    Returns:
        dict: Context variables for configuration status including:
            - has_pending_config_changes: Boolean indicating if there are incomplete configurations
            - config_completion_status: Dictionary with completion status for each section
    """
    context = {
        'has_pending_config_changes': False,
        'config_completion_status': {
            'basic_info': True,
            'contact_info': True,
            'system_config': True,
            'templates': True,
            'notifications': True,
        }
    }
    
    # Only check for authenticated users
    if not request.user.is_authenticated:
        return context
    
    try:
        # Get or create company instance
        company, created = Company.objects.get_or_create(
            id=1,
            defaults={'name': 'Mi Empresa'}
        )
        
        # If company was just created, it needs configuration
        if created:
            context['has_pending_config_changes'] = True
            context['config_completion_status'] = {
                'basic_info': False,
                'contact_info': False,
                'system_config': False,
                'templates': False,
                'notifications': False,
            }
            return context
        
        # Check basic company information completeness
        basic_info_complete = all([
            company.name and company.name != 'Mi Empresa',
            company.address,
            company.phone,
            company.email,
        ])
        context['config_completion_status']['basic_info'] = basic_info_complete
        
        # Check contact information (using company fields for now)
        contact_info_complete = all([
            company.address,
            company.phone,
            company.email,
        ])
        context['config_completion_status']['contact_info'] = contact_info_complete
        
        # Check system configuration
        try:
            sys_config = SystemConfiguration.objects.get(company=company)
            system_config_complete = all([
                sys_config.currency,
                sys_config.timezone,
                sys_config.date_format,
                sys_config.language,
            ])
        except SystemConfiguration.DoesNotExist:
            system_config_complete = False
        
        context['config_completion_status']['system_config'] = system_config_complete
        
        # Check document templates (at least one active template should exist)
        templates_exist = DocumentTemplate.objects.filter(
            company=company,
            is_active=True
        ).exists()
        context['config_completion_status']['templates'] = templates_exist
        
        # Check notification settings (at least one notification should be configured)
        notifications_exist = NotificationSettings.objects.filter(
            company=company
        ).exists()
        context['config_completion_status']['notifications'] = notifications_exist
        
        # Determine if there are pending changes
        context['has_pending_config_changes'] = not all(
            context['config_completion_status'].values()
        )
        
    except Exception as e:
        # In case of any error, assume no pending changes to avoid breaking the UI
        # Log the error if logging is configured
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Error checking configuration status: {str(e)}")
        
        context['has_pending_config_changes'] = False
    
    return context


def company_data(request):
    """
    Context processor that provides company data globally to all templates.
    
    Returns:
        dict: Context variables including:
            - company: Company instance with all basic data
            - company_config: Dictionary with additional configurations
            - system_config: System configuration instance
    """
    context = {
        'company': None,
        'company_config': {},
        'system_config': None,
    }
    
    try:
        # Get or create company instance
        company, created = Company.objects.get_or_create(
            id=1,
            defaults={
                'name': 'Mi Empresa',
                'address': '',
                'phone': '',
                'email': '',
                'website': '',
                'tax_id': '',
            }
        )
        
        context['company'] = company
        
        # Get additional company configurations
        configurations = CompanyConfiguration.objects.filter(company=company)
        company_config = {}
        for config in configurations:
            company_config[config.config_key] = config.get_value()
        
        context['company_config'] = company_config
        
        # Get system configuration
        try:
            system_config = SystemConfiguration.objects.get(company=company)
            context['system_config'] = system_config
        except SystemConfiguration.DoesNotExist:
            # Create default system configuration
            system_config = SystemConfiguration.objects.create(
                company=company,
                currency='EUR',
                timezone='Europe/Madrid',
                date_format='DD/MM/YYYY',
                language='es'
            )
            context['system_config'] = system_config
            
    except Exception as e:
        # In case of any error, provide default values
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Error loading company data: {str(e)}")
        
        # Provide minimal default company data
        context['company'] = type('Company', (), {
            'name': 'Mi Empresa',
            'address': '',
            'phone': '',
            'email': '',
            'website': '',
            'logo': None,
            'tax_id': '',
        })()
        
    return context