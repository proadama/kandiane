# apps/core/managers.py
from django.db import models
from django.db.models import Q
from django.utils import timezone

class BaseManager(models.Manager):
    """
    Gestionnaire de modèles personnalisé qui exclut les objets supprimés logiquement.
    """
    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)
    
    def with_deleted(self):
        """
        Inclure les objets supprimés logiquement dans les résultats.
        """
        return super().get_queryset()
    
    def only_deleted(self):
        """
        Retourner uniquement les objets supprimés logiquement.
        """
        return super().get_queryset().filter(deleted_at__isnull=False)

    def recent_deleted(self, days=30):
        """Objets supprimés récemment (dans les X derniers jours)."""
        from django.utils import timezone
        date_limit = timezone.now() - timezone.timedelta(days=days)
        return self.only_deleted().filter(deleted_at__gte=date_limit)
    
    def get_or_none(self, **kwargs):
        """
        Récupérer un objet ou None s'il n'existe pas.
        """
        try:
            return self.get(**kwargs)
        except self.model.DoesNotExist:
            return None