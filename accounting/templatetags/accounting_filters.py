from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """
    Filtro para acceder a un elemento de un diccionario por su clave.
    Uso: {{ dictionary|get_item:key }}
    """
    return dictionary.get(key, 0)