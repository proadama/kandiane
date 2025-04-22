# Version idéale de cotisations_extras.py
from django import template
from .custom_filters import split_filter, subtract, add_days

register = template.Library()

# Réexporter les filtres
register.filter('split', split_filter)
register.filter('sub', subtract)
register.filter('add_days', add_days)