# apps/cotisations/apps.py
from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class CotisationsConfig(AppConfig):
    name = 'apps.cotisations'
    verbose_name = _("Cotisations")
    
    def ready(self):
        """Importer les signaux lorsque l'application est prête"""
        import apps.cotisations.signals