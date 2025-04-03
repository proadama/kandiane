# config/settings/__init__.py
import os

# Par défaut, utiliser les paramètres de développement
env = os.environ.get('DJANGO_ENV', 'development')

if env == 'production':
    from .production import *
else:
    from .development import *