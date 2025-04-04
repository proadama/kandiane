from django.apps import AppConfig


class MembresConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.membres'
    verbose_name = 'Gestion des membres'

    def ready(self):
        # Importer les signaux
        import apps.membres.signals
