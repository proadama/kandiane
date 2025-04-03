# apps/core/models.py
from django.db import models
from django.utils import timezone
from .managers import BaseManager

class BaseModel(models.Model):
    """
    Modèle de base avec des champs communs pour toutes les entités.
    """
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Date de modification")
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name="Date de suppression")
    
    objects = BaseManager()

    class Meta:
        abstract = True
        ordering = ['-created_at']
    
    def delete(self, hard=False, *args, **kwargs):
        """
        Surcharge de la méthode delete pour faire une suppression logique.
        Le paramètre hard=True permet de faire une suppression physique.
        """
        if hard:
            return super().delete(*args, **kwargs)
        
        self.deleted_at = timezone.now()
        self.save(update_fields=['deleted_at'])

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