# apps/core/models.py
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

class BaseModel(models.Model):
    """
    Modèle de base avec des champs communs pour toutes les entités.
    """
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Date de création"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Date de modification"))
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Date de suppression"))
    
    class Meta:
        abstract = True
    
    def delete(self, hard=False, user=None, *args, **kwargs):
        """
        Suppression logique par défaut, avec option de suppression physique.
        
        Args:
            hard (bool): Si True, effectue une suppression physique
            user (User): Utilisateur qui effectue la suppression (pour journalisation)
        """
        if hard:
            # Suppression physique
            return super().delete(*args, **kwargs)
        else:
            # Suppression logique
            self.deleted_at = timezone.now()
            self.save(update_fields=['deleted_at'])
            
            # Journaliser l'action (si applicable)
            self._log_deletion(user)
            
            return 1, {}  # Simuler le retour de la méthode delete() standard
    
    def restore(self, user=None):
        """
        Restaure un objet supprimé logiquement.
        
        Args:
            user (User): Utilisateur qui effectue la restauration (pour journalisation)
        
        Returns:
            bool: True si la restauration a réussi, False sinon
        """
        if self.deleted_at is None:
            return False  # Déjà actif
        
        self.deleted_at = None
        self.save(update_fields=['deleted_at'])
        
        # Journaliser l'action (si applicable)
        self._log_restoration(user)
        
        return True
    
    def is_deleted(self):
        """Vérifie si l'objet est supprimé logiquement."""
        return self.deleted_at is not None
    
    def _log_deletion(self, user):
        """Méthode à surcharger pour journaliser la suppression."""
        pass
    
    def _log_restoration(self, user):
        """Méthode à surcharger pour journaliser la restauration."""
        pass

class Statut(BaseModel):
    """
    Modèle pour stocker les différents statuts utilisés dans l'application.
    """
    nom = models.CharField(max_length=50, unique=True, verbose_name="Nom")
    description = models.TextField(null=True, blank=True, verbose_name="Description")
    
    class Meta:
        verbose_name = "Statut"
        verbose_name_plural = "Statuts"
        
    def __str__(self):
        return self.nom