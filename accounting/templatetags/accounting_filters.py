from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """
    Filtro para acceder a un elemento de un diccionario por su clave.
    Uso: {{ dictionary|get_item:key }}
    """
    return dictionary.get(key, 0)

@register.filter
def pluralize_es(value, singular_plural=""):
    """
    Filtro para pluralización en español.
    Uso: {{ days|pluralize_es:"día,días" }}
    """
    try:
        count = int(value)
    except (ValueError, TypeError):
        return ""
    
    if not singular_plural:
        return "s" if count != 1 else ""
    
    if "," in singular_plural:
        singular, plural = singular_plural.split(",", 1)
        return singular if count == 1 else plural
    else:
        return singular_plural if count != 1 else ""