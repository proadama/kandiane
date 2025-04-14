# apps/accounts/apps.py
from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.accounts'
    verbose_name = 'Gestion des comptes'

    def ready(self):
        # Cette méthode est appelée lorsque l'application est prête
        # C'est ici qu'on importe les signaux pour les activer
        import apps.accounts.signals
