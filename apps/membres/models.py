from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.urls import reverse

from apps.core.models import BaseModel, Statut
from apps.accounts.models import CustomUser
from apps.membres.managers import MembreManager, TypeMembreManager, MembreTypeMembreManager
import datetime


class TypeMembre(BaseModel):
    """
    Modèle représentant les différents types/catégories de membres
    (exemples: membre actif, membre honoraire, bienfaiteur, etc.)
    """
    libelle = models.CharField(
        max_length=100, 
        unique=True, 
        verbose_name=_("Libellé")
    )
    description = models.TextField(
        null=True, 
        blank=True, 
        verbose_name=_("Description")
    )
    cotisation_requise = models.BooleanField(
        default=True, 
        verbose_name=_("Cotisation requise")
    )
    ordre_affichage = models.PositiveSmallIntegerField(
        default=0, 
        verbose_name=_("Ordre d'affichage")
    )
    
    # Utiliser le gestionnaire personnalisé
    objects = TypeMembreManager()
    
    class Meta:
        verbose_name = _("Type de membre")
        verbose_name_plural = _("Types de membres")
        ordering = ['ordre_affichage', 'libelle']
    
    def __str__(self):
        return self.libelle
    
    def get_absolute_url(self):
        return reverse('membres:type_membre_modifier', kwargs={'pk': self.pk})
    
    def get_membres_actifs(self):
        """Retourne les membres actifs de ce type"""
        return self.membres.filter(
            membretypemembre__date_debut__lte=timezone.now().date(),
            membretypemembre__date_fin__isnull=True
        ).distinct()
    
    def nb_membres_actifs(self):
        """Retourne le nombre de membres actifs de ce type"""
        today = timezone.now().date()
        return self.membres_historique.filter(
            date_debut__lte=today,
            date_fin__isnull=True
        ).values('membre').distinct().count()


class Membre(BaseModel):
    """
    Modèle représentant un membre de l'association avec toutes
    ses informations personnelles et associatives
    """
    # Informations personnelles
    nom = models.CharField(
        max_length=100, 
        verbose_name=_("Nom")
    )
    prenom = models.CharField(
        max_length=100, 
        verbose_name=_("Prénom")
    )
    email = models.EmailField(
        unique=True, 
        verbose_name=_("Email")
    )
    telephone = models.CharField(
        max_length=100, 
        blank=True, 
        null=True, 
        verbose_name=_("Téléphone")
    )
    adresse = models.CharField(
        max_length=255, 
        blank=True, 
        null=True, 
        verbose_name=_("Adresse")
    )
    code_postal = models.CharField(
        max_length=20, 
        blank=True, 
        null=True, 
        verbose_name=_("Code postal")
    )
    ville = models.CharField(
        max_length=100, 
        blank=True, 
        null=True, 
        verbose_name=_("Ville")
    )
    date_adhesion = models.DateField(
        default=timezone.now, 
        verbose_name=_("Date d'adhésion")
    )
    date_naissance = models.DateField(
        blank=True, 
        null=True, 
        verbose_name=_("Date de naissance")
    )
    
    # Relation avec le système d'utilisateurs
    utilisateur = models.OneToOneField(
        CustomUser, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='membre',
        verbose_name=_("Compte utilisateur")
    )
    
    # Préférences et statut
    langue = models.CharField(
        max_length=2, 
        default='fr',
        choices=[('fr', 'Français'), ('en', 'Anglais'), ('de', 'Allemand'), ('es', 'Espagnol')],
        verbose_name=_("Langue préférée")
    )
    pays = models.CharField(
        max_length=50, 
        blank=True, 
        null=True, 
        default='France',
        verbose_name=_("Pays")
    )
    statut = models.ForeignKey(
        Statut, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name=_("Statut")
    )
    
    # Relations avec d'autres modèles
    types = models.ManyToManyField(
        TypeMembre, 
        through='MembreTypeMembre',
        related_name='membres',
        verbose_name=_("Types de membre")
    )
    
    # Champs supplémentaires pour la gestion
    commentaires = models.TextField(
        blank=True, 
        null=True,
        verbose_name=_("Commentaires")
    )
    photo = models.ImageField(
        upload_to='membres/photos/', 
        blank=True, 
        null=True,
        verbose_name=_("Photo")
    )
    
    # Préférences de communication
    accepte_mail = models.BooleanField(
        default=True,
        verbose_name=_("Accepte les communications par email")
    )
    accepte_sms = models.BooleanField(
        default=False,
        verbose_name=_("Accepte les communications par SMS")
    )
    
    # Utiliser le gestionnaire personnalisé
    objects = MembreManager()
    
    class Meta:
        verbose_name = _("Membre")
        verbose_name_plural = _("Membres")
        ordering = ['nom', 'prenom']
        indexes = [
            models.Index(fields=['nom', 'prenom']),
            models.Index(fields=['email']),
            models.Index(fields=['date_adhesion']),
        ]
    
    def __str__(self):
        return f"{self.prenom} {self.nom}"
    
    def get_absolute_url(self):
        return reverse('membres:membre_modifier', kwargs={'pk': self.pk})
      
    def delete(self, hard=False, *args, **kwargs):
        """
        Suppression logique par défaut.
        Si hard=True, suppression physique.
        """
        import logging
        logger = logging.getLogger(__name__)
        
        if hard:
            # Suppression physique - bypasser complètement la logique de soft delete
            logger.info(f"Suppression physique de {self.__class__.__name__} ID={self.id}")
            # Désactiver tous les signaux qui pourraient interférer
            from django.db.models.signals import pre_save, post_save
            post_save.disconnect(dispatch_uid=None, sender=self.__class__)
            
            # Appeler la méthode delete() du parent (models.Model)
            # pour éviter toute logique de soft delete dans la hiérarchie d'héritage
            return models.Model.delete(self, *args, **kwargs)
        else:
            # Suppression logique
            logger.info(f"Suppression logique de {self.__class__.__name__} ID={self.id}")
            self.deleted_at = timezone.now()
            self.save(update_fields=['deleted_at'])
            return 1, {}  # Simuler le retour de la méthode delete() standard
    
    def delete_permanent(self):
        """
        Suppression définitive qui contourne complètement le mécanisme de soft delete
        en utilisant une requête SQL directe.
        """
        import logging
        from django.db import connection
        
        logger = logging.getLogger(__name__)
        logger.info(f"Suppression définitive du membre ID={self.id}, nom={self.nom}")
        
        membre_id = self.id
        
        with connection.cursor() as cursor:
            # Supprimer d'abord les relations
            cursor.execute("DELETE FROM membres_membretypemembre WHERE membre_id = %s", [membre_id])
            cursor.execute("DELETE FROM membres_historiquemembre WHERE membre_id = %s", [membre_id])
            
            # Puis supprimer le membre lui-même
            cursor.execute("DELETE FROM membres_membre WHERE id = %s", [membre_id])
            
            # Loguer le nombre de lignes supprimées
            rows_deleted = cursor.rowcount
            logger.info(f"Membre ID={membre_id} supprimé définitivement ({rows_deleted} lignes)")
            
        return rows_deleted

    def clean(self):
        # Vérifier que la date de naissance n'est pas dans le futur
        if self.date_naissance:
            today = timezone.now().date()
            # Convertir date_naissance en date si c'est un datetime
            date_naissance = self.date_naissance.date() if isinstance(self.date_naissance, datetime.datetime) else self.date_naissance
            if date_naissance > today:
                raise ValidationError({
                    'date_naissance': _("La date de naissance ne peut pas être dans le futur")
                })
        
        # Vérifier que la date d'adhésion n'est pas dans le futur
        if self.date_adhesion:
            today = timezone.now().date()
            # Convertir date_adhesion en date si c'est un datetime
            date_adhesion = self.date_adhesion.date() if isinstance(self.date_adhesion, datetime.datetime) else self.date_adhesion
            if date_adhesion > today:
                raise ValidationError({
                    'date_adhesion': _("La date d'adhésion ne peut pas être dans le futur")
                })

    
    def save(self, *args, **kwargs):
        """Surcharge de la méthode save pour la validation"""
        self.clean()
        super().save(*args, **kwargs)
    
    def get_types_actifs(self):
        """Retourne les types de membre actifs"""
        return TypeMembre.objects.filter(
            membres_historique__membre=self,
            membres_historique__date_debut__lte=timezone.now().date(),
            membres_historique__date_fin__isnull=True
        ).distinct()
    
    def get_types_historiques(self):
        """Retourne tous les types de membre, y compris ceux qui ne sont plus actifs"""
        return TypeMembre.objects.filter(
            membretypemembre__membre=self
        ).distinct()
    
    def est_type_actif(self, type_membre):
        """Vérifie si le membre a un type de membre actif spécifique"""
        return MembreTypeMembre.objects.filter(
            membre=self,
            type_membre=type_membre,
            date_debut__lte=timezone.now().date(),
            date_fin__isnull=True
        ).exists()
    
    def ajouter_type(self, type_membre, date_debut=None):
        """Ajoute un type de membre au membre"""
        if date_debut is None:
            date_debut = timezone.now().date()
        
        # Terminer les types existants du même type
        MembreTypeMembre.objects.filter(
            membre=self,
            type_membre=type_membre,
            date_fin__isnull=True
        ).update(date_fin=date_debut)
        
        # Créer le nouveau type
        return MembreTypeMembre.objects.create(
            membre=self,
            type_membre=type_membre,
            date_debut=date_debut
        )
    
    def supprimer_type(self, type_membre, date_fin=None):
        """Retire un type de membre au membre à la date spécifiée"""
        if date_fin is None:
            date_fin = timezone.now().date()
            
        return MembreTypeMembre.objects.filter(
            membre=self,
            type_membre=type_membre,
            date_fin__isnull=True
        ).update(date_fin=date_fin)
    
    def age(self):
        """Calcule l'âge du membre"""
        if not self.date_naissance:
            return None
        
        today = timezone.now().date()
        born = self.date_naissance
        
        # Gestion correcte des années bissextiles
        age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
        return age
    
    def creer_compte_utilisateur(self, username=None, password=None):
        """Crée un compte utilisateur pour ce membre s'il n'en a pas déjà un"""
        if self.utilisateur:
            return self.utilisateur
            
        if not username:
            # Générer un nom d'utilisateur basé sur l'email ou le nom/prénom
            username = self.email.split('@')[0]
        
        from apps.accounts.models import CustomUser
        user = CustomUser.objects.create_user(
            username=username,
            email=self.email,
            password=password
        )
        
        self.utilisateur = user
        self.save(update_fields=['utilisateur'])
        
        return user
    
    def get_cotisations(self):
        """Retourne les cotisations du membre"""
        # Import ici pour éviter les imports circulaires
        from apps.cotisations.models import Cotisation
        return Cotisation.objects.filter(membre=self)
    
    def get_cotisations_impayees(self):
        """Retourne les cotisations impayées du membre"""
        # Import ici pour éviter les imports circulaires
        from apps.cotisations.models import Cotisation
        return Cotisation.objects.filter(
            membre=self, 
            statut_paiement__in=['non_payée', 'partiellement_payée']
        )
    
    def get_evenements_inscrits(self):
        """Retourne les événements auxquels le membre est inscrit"""
        # Import ici pour éviter les imports circulaires
        from apps.evenements.models import Evenement
        return Evenement.objects.filter(inscriptions__membre=self)

    # Ajouter ces méthodes à la classe Membre
    def _log_deletion(self, user):
        """Journaliser la suppression logique d'un membre."""
        from apps.membres.models import HistoriqueMembre
        
        if not user:
            return
            
        HistoriqueMembre.objects.create(
            membre=self,
            utilisateur=user,
            action='suppression',
            description=_("Suppression du membre (placé dans la corbeille)"),
            donnees_avant={
                'nom': self.nom,
                'prenom': self.prenom,
                'email': self.email,
                'deleted_at': None
            },
            donnees_apres={
                'deleted_at': str(self.deleted_at)
            }
        )
    
    def _log_restoration(self, user):
        """Journaliser la restauration d'un membre."""
        from apps.membres.models import HistoriqueMembre
        
        if not user:
            return
            
        HistoriqueMembre.objects.create(
            membre=self,
            utilisateur=user,
            action='restauration',
            description=_("Restauration du membre depuis la corbeille"),
            donnees_avant={
                'deleted_at': str(self.deleted_at)
            },
            donnees_apres={
                'deleted_at': None
            }
        )
    
    @property
    def nom_complet(self):
        """Retourne le nom complet du membre"""
        return f"{self.prenom} {self.nom}"
    
    @property
    def adresse_complete(self):
        """Retourne l'adresse complète formatée"""
        parts = []
        if self.adresse:
            parts.append(self.adresse)
        if self.code_postal or self.ville:
            parts.append(f"{self.code_postal or ''} {self.ville or ''}".strip())
        if self.pays and self.pays != 'France':
            parts.append(self.pays)
        return "\n".join(parts)


class MembreTypeMembre(models.Model):
    """
    Table de liaison entre Membre et TypeMembre avec historisation
    (permet de suivre les changements de type de membre au fil du temps)
    """
    membre = models.ForeignKey(
        Membre, 
        on_delete=models.CASCADE,
        related_name='types_historique',
        verbose_name=_("Membre")
    )
    type_membre = models.ForeignKey(
        TypeMembre, 
        on_delete=models.CASCADE,
        related_name='membres_historique',
        verbose_name=_("Type de membre")
    )
    date_debut = models.DateField(
        verbose_name=_("Date de début")
    )
    date_fin = models.DateField(
        null=True, 
        blank=True,
        verbose_name=_("Date de fin")
    )
    
    # Champs supplémentaires pour l'audit
    commentaire = models.TextField(
        blank=True, 
        null=True,
        verbose_name=_("Commentaire")
    )
    modifie_par = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='modifications_types_membres',
        verbose_name=_("Modifié par")
    )
    
    # Utiliser le gestionnaire personnalisé
    objects = MembreTypeMembreManager()
    
    class Meta:
        verbose_name = _("Historique de type de membre")
        verbose_name_plural = _("Historiques de types de membres")
        ordering = ['-date_debut']
        unique_together = ('membre', 'type_membre', 'date_debut')
        indexes = [
            models.Index(fields=['membre', 'type_membre']),
            models.Index(fields=['date_debut', 'date_fin']),
        ]
    
    def __str__(self):
        statut = _("actif") if self.est_actif else _("terminé")
        return f"{self.membre} - {self.type_membre} ({statut})"
    
    def clean(self):
        """Validation personnalisée du modèle"""
        # Vérifier que la date de fin est postérieure à la date de début
        if self.date_fin and self.date_fin < self.date_debut:
            raise ValidationError({
                'date_fin': _("La date de fin doit être postérieure à la date de début")
            })
    
    def save(self, *args, **kwargs):
        """Surcharge de la méthode save pour la validation et la mise à jour du cache"""
        self.clean()
        
        # Sauvegarde des valeurs précédentes pour vérifier les changements
        if self.pk:
            old_instance = MembreTypeMembre.objects.get(pk=self.pk)
            date_fin_changed = old_instance.date_fin != self.date_fin
        else:
            date_fin_changed = False
        
        # Sauvegarde normale
        result = super().save(*args, **kwargs)
        
        # Si la date de fin a changé, forcer la mise à jour du cache des types actifs du membre
        if date_fin_changed and self.membre:
            # Forcer le rechargement des types actifs si nécessaire
            try:
                # Cette ligne force Django à recalculer les types actifs
                # en invalidant le cache QuerySet
                refresh_types = list(self.membre.get_types_actifs())
            except Exception:
                pass  # Ignorer les erreurs potentielles
        
        return result
    
    @property
    def est_actif(self):
        """Vérifie si cette association est active"""
        today = timezone.now().date()
        # Une association est active si sa date de début est dans le passé
        # et si sa date de fin est soit nulle, soit dans le futur
        return (
            self.date_debut <= today and 
            (self.date_fin is None or self.date_fin > today)  # Utiliser > au lieu de >=
        )


class HistoriqueMembre(BaseModel):
    """
    Modèle pour enregistrer l'historique des modifications des membres
    """
    membre = models.ForeignKey(
        Membre, 
        on_delete=models.CASCADE,
        related_name='historique',
        verbose_name=_("Membre")
    )
    utilisateur = models.ForeignKey(
        CustomUser, 
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='historique_membres',
        verbose_name=_("Utilisateur")
    )
    action = models.CharField(
        max_length=50,
        verbose_name=_("Action")
    )
    description = models.TextField(
        verbose_name=_("Description")
    )
    donnees_avant = models.JSONField(
        null=True,
        blank=True,
        verbose_name=_("Données avant")
    )
    donnees_apres = models.JSONField(
        null=True,
        blank=True,
        verbose_name=_("Données après")
    )
    
    class Meta:
        verbose_name = _("Historique de membre")
        verbose_name_plural = _("Historique des membres")
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['membre', '-created_at']),
            models.Index(fields=['action']),
        ]
    
    def __str__(self):
        return f"{self.action} - {self.membre} - {self.created_at}"