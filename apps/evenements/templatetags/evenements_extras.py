from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter
def div(value, arg):
    """
    Divise la valeur par l'argument
    Usage: {{ value|div:arg }}
    """
    try:
        return float(value) / float(arg)
    except (ValueError, ZeroDivisionError, TypeError):
        return 0