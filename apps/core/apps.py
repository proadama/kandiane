# apps/core/apps.py
from django.apps import AppConfig

class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.core'  # Vérifiez que le nom est correct
    verbose_name = 'Application Core'
    
    def ready(self):
        # Importer les signaux
        import apps.core.signals