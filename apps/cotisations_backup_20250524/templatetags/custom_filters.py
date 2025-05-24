# apps/cotisations/templatetags/custom_filters.py
from django import template
from datetime import datetime, timedelta

register = template.Library()

@register.filter(name='split')
def split_filter(value, arg):
    """
    Divise une chaîne en utilisant le séparateur spécifié et renvoie une liste.
    
    Exemple d'utilisation: {{ "a,b,c"|split:"," }}
    Résultat: ['a', 'b', 'c']
    """
    return value.split(arg)

@register.filter(name='sub')
def subtract(value, arg):
    """
    Soustrait l'argument de la valeur.
    
    Exemple d'utilisation: {{ 10|sub:5 }}
    Résultat: 5
    """
    return value - arg

@register.filter(name='add_days')
def add_days(value, days):
    """
    Ajoute un nombre de jours à une date.
    
    Exemple d'utilisation: {{ date|add_days:30 }}
    Résultat: date + 30 jours
    """
    if isinstance(value, str):
        try:
            # Si la valeur est une chaîne formatée en date
            dt = datetime.strptime(value, '%Y-%m-%d')
            return (dt + timedelta(days=int(days))).strftime('%Y-%m-%d')
        except ValueError:
            return value
    elif hasattr(value, 'year') and hasattr(value, 'month'):
        # Si c'est un objet date ou datetime
        return value + timedelta(days=int(days))
    return value  # Retourne la valeur inchangée si on ne peut pas l'interpréter