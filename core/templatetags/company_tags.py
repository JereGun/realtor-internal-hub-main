"""
Template tags for company data access.

Provides convenient template tags for accessing company information
throughout the application templates.
"""

from django import template
from django.utils.safestring import mark_safe
from ..models import Company, CompanyConfiguration, SystemConfiguration

register = template.Library()


@register.simple_tag
def company_name():
    """Returns the company name or default value."""
    try:
        company = Company.objects.get(id=1)
        return company.name if company.name else "Mi Empresa"
    except Company.DoesNotExist:
        return "Mi Empresa"


@register.simple_tag
def company_logo():
    """Returns the company logo URL or None."""
    try:
        company = Company.objects.get(id=1)
        return company.logo.url if company.logo else None
    except (Company.DoesNotExist, ValueError):
        return None


@register.simple_tag
def company_contact(field):
    """Returns a specific company contact field."""
    try:
        company = Company.objects.get(id=1)
        return getattr(company, field, '')
    except Company.DoesNotExist:
        return ''


@register.simple_tag
def company_config(key, default=''):
    """Returns a company configuration value."""
    try:
        company = Company.objects.get(id=1)
        config = CompanyConfiguration.objects.get(company=company, config_key=key)
        return config.get_value()
    except (Company.DoesNotExist, CompanyConfiguration.DoesNotExist):
        return default


@register.simple_tag
def system_config(field, default=''):
    """Returns a system configuration field."""
    try:
        company = Company.objects.get(id=1)
        sys_config = SystemConfiguration.objects.get(company=company)
        return getattr(sys_config, field, default)
    except (Company.DoesNotExist, SystemConfiguration.DoesNotExist):
        return default


@register.inclusion_tag('core/tags/company_logo.html')
def render_company_logo(height=32, classes=''):
    """Renders the company logo with fallback icon."""
    try:
        company = Company.objects.get(id=1)
        return {
            'company': company,
            'height': height,
            'classes': classes,
        }
    except Company.DoesNotExist:
        return {
            'company': None,
            'height': height,
            'classes': classes,
        }


@register.inclusion_tag('core/tags/company_contact_info.html')
def render_company_contact():
    """Renders company contact information."""
    try:
        company = Company.objects.get(id=1)
        
        # Get additional configurations
        configs = {}
        try:
            configurations = CompanyConfiguration.objects.filter(company=company)
            for config in configurations:
                configs[config.config_key] = config.get_value()
        except:
            pass
            
        return {
            'company': company,
            'configs': configs,
        }
    except Company.DoesNotExist:
        return {
            'company': None,
            'configs': {},
        }


@register.filter
def company_data_or_default(value, default):
    """Filter to return company data or default value."""
    return value if value else default


@register.simple_tag
def company_schema_data():
    """Returns structured data for the company."""
    try:
        company = Company.objects.get(id=1)
        
        # Get additional configurations
        configs = {}
        try:
            configurations = CompanyConfiguration.objects.filter(company=company)
            for config in configurations:
                configs[config.config_key] = config.get_value()
        except:
            pass
        
        schema = {
            "name": company.name or "Mi Empresa",
            "telephone": company.phone or "",
            "email": company.email or "",
            "address": {
                "streetAddress": company.address or "",
                "addressLocality": configs.get('city', ''),
                "addressRegion": configs.get('state_province', ''),
                "addressCountry": configs.get('country', 'ES')
            }
        }
        
        return schema
    except Company.DoesNotExist:
        return {
            "name": "Mi Empresa",
            "telephone": "",
            "email": "",
            "address": {
                "streetAddress": "",
                "addressLocality": "",
                "addressRegion": "",
                "addressCountry": "ES"
            }
        }