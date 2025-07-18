# apps/core/models.py
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.db.models import Q
from .managers import BaseManager
from django.conf import settings
import json

class BaseModel(models.Model):
    """
    Modèle de base avec des champs communs pour toutes les entités.
    """
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Date de création"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Date de modification"))
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Date de suppression"))
    
    objects = BaseManager()

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
    TYPE_CHOICES = [
        ('global', _('Global')),
        ('membre', _('Membre')),
        ('cotisation', _('Cotisation')),
        ('paiement', _('Paiement')),
        ('evenement', _('Événement')),
    ]
    
    nom = models.CharField(max_length=50, unique=True, verbose_name=_("Nom"))
    description = models.TextField(null=True, blank=True, verbose_name=_("Description"))
    type_entite = models.CharField(
        max_length=20, 
        choices=TYPE_CHOICES,
        default='global',
        verbose_name=_("Type d'entité")
    )
    
    class Meta:
        verbose_name = _("Statut")
        verbose_name_plural = _("Statuts")
        ordering = ['type_entite', 'nom']
        
    def __str__(self):
        return self.nom
    
    @classmethod
    def pour_membres(cls):
        """Retourne les statuts applicables aux membres."""
        return cls.objects.filter(Q(type_entite='membre') | Q(type_entite='global'))
    
    @classmethod
    def pour_cotisations(cls):
        """Retourne les statuts applicables aux cotisations."""
        return cls.objects.filter(Q(type_entite='cotisation') | Q(type_entite='global'))
    
    @classmethod
    def pour_paiements(cls):
        """Retourne les statuts applicables aux paiements."""
        return cls.objects.filter(Q(type_entite='paiement') | Q(type_entite='global'))
    
    
    def get_badge_class(self):
        """
        Retourne la classe CSS Bootstrap appropriée en fonction du nom du statut
        et du contexte de son utilisation (type d'entité).
        """
        nom_lower = self.nom.lower() if self.nom else ""
        
        # Statuts de Cotisation
        if nom_lower == 'payée':
            return 'success'
        elif nom_lower == 'en retard':
            return 'warning'
        elif nom_lower == 'non payée':
            return 'secondary'
        elif nom_lower == 'annulée':
            return 'danger'
        elif nom_lower == 'partiellement payée':
            return 'info'
        
        # Statuts de Membre
        elif nom_lower == 'actif':
            return 'success'
        elif nom_lower == 'suspendu':
            return 'warning'
        elif nom_lower == 'bloqué':
            return 'danger'
        elif nom_lower == 'désactivé':
            return 'secondary'
        
        # Statuts de Paiement
        elif nom_lower == 'validé':
            return 'success'
        elif nom_lower == 'en attente':
            return 'warning'
        elif nom_lower in ['annulé', 'rejeté']:
            return 'danger'
        
        # Statut par défaut
        else:
            return 'secondary'


class Log(models.Model):
    """
    Modèle pour l'historique des actions utilisateur
    """
    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL,  # Utiliser settings.AUTH_USER_MODEL au lieu de get_user_model()
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='logs_actions'
    )
    
    action = models.CharField(
        max_length=100,
        help_text="Type d'action effectuée"
    )
    
    details = models.JSONField(
        default=dict,
        blank=True,
        help_text="Détails de l'action en JSON"
    )
    
    adresse_ip = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="Adresse IP de l'utilisateur"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Date et heure de l'action"
    )
    
    class Meta:
        db_table = 'core_log'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['utilisateur']),
            models.Index(fields=['action']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        username = self.utilisateur.username if self.utilisateur else 'Anonyme'
        return f"{username} - {self.action} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"
    
    @property
    def details_formatted(self):
        """Retourne les détails formatés pour l'affichage"""
        if isinstance(self.details, dict):
            return json.dumps(self.details, indent=2, ensure_ascii=False)
        return str(self.details)

    def get_details_json(self):
        """Retourne les détails formatés en JSON"""
        try:
            return json.dumps(self.details, indent=2, ensure_ascii=False)
        except:
            return str(self.details)