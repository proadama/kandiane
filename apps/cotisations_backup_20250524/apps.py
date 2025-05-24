# apps/cotisations/apps.py
from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class CotisationsConfig(AppConfig):
    name = 'apps.cotisations'
    verbose_name = _("Cotisations")
    
    def ready(self):
        # Éviter de démarrer le scheduler pendant les commandes 'migrate' ou 'makemigrations'
        import sys
        if 'migrate' not in sys.argv and 'makemigrations' not in sys.argv:
            # Importer ici pour éviter des imports circulaires
            from django.contrib.sites.models import Site
            from django.contrib.auth.models import User
            # Utiliser un léger délai pour s'assurer que Django est complètement chargé
            import threading
            import time
            
            def delayed_start():
                time.sleep(5)  # Attendre 5 secondes
                from apps.cotisations.scheduler import start
                start()
            
            threading.Thread(target=delayed_start).start()