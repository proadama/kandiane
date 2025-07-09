
# apps/evenements/apps.py
from django.apps import AppConfig


class EvenementsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.evenements'
    verbose_name = "Événements"
    
    def ready(self):
        """Import des signaux lors du démarrage de l'application"""
        try:
            import apps.evenements.signals
        except ImportError:
            pass