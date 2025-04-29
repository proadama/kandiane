from django import template

register = template.Library()

@register.simple_tag(takes_context=True)
def url_replace(context, **kwargs):
    """
    Remplace ou ajoute des paramètres dans l'URL actuelle
    Usage: {% url_replace page=2 %}
    """
    query = context['request'].GET.copy()
    for key, value in kwargs.items():
        query[key] = value
    return query.urlencode()