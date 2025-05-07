# apps/cotisations/models.py
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from decimal import Decimal

from apps.core.models import BaseModel, Statut
from apps.membres.models import Membre, TypeMembre
from apps.accounts.models import CustomUser

from .managers import CotisationManager, PaiementManager


class BaremeCotisation(BaseModel):
    """
    Modèle définissant les montants de cotisation par type de membre.
    """
    type_membre = models.ForeignKey(
        TypeMembre,
        on_delete=models.CASCADE,
        related_name='baremes',
        verbose_name=_("Type de membre")
    )
    montant = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_("Montant")
    )
    date_debut_validite = models.DateField(
        verbose_name=_("Date de début de validité"),
        default=timezone.now
    )
    date_fin_validite = models.DateField(
        verbose_name=_("Date de fin de validité"),
        null=True,
        blank=True
    )
    periodicite = models.CharField(
        max_length=20,
        choices=[
            ('mensuelle', _('Mensuelle')),
            ('trimestrielle', _('Trimestrielle')),
            ('semestrielle', _('Semestrielle')),
            ('annuelle', _('Annuelle')),
            ('unique', _('Unique')),
        ],
        default='annuelle',
        verbose_name=_("Périodicité")
    )
    description = models.TextField(
        null=True,
        blank=True,
        verbose_name=_("Description")
    )
    
    class Meta:
        verbose_name = _("Barème de cotisation")
        verbose_name_plural = _("Barèmes de cotisations")
        ordering = ['-date_debut_validite']
    
    def __str__(self):
        return f"{self.type_membre.libelle} - {self.montant} € ({self.get_periodicite_display()})"
    
    def get_absolute_url(self):
        return reverse('cotisations:bareme_detail', kwargs={'pk': self.pk})
    
    def est_actif(self):
        """Vérifie si le barème est actuellement en vigueur"""
        today = timezone.now().date()
        return (self.date_debut_validite <= today and 
                (self.date_fin_validite is None or self.date_fin_validite >= today))
    
    def calculer_montant_prorata(self, date_debut, date_fin=None):
        """
        Calcule le montant de la cotisation au prorata de la période spécifiée.
        
        Args:
            date_debut (date): Date de début de la période
            date_fin (date, optional): Date de fin de la période. Si non spécifiée,
                                    considère une durée de 1 jour.
        
        Returns:
            Decimal: Montant proratisé de la cotisation
        """
        from decimal import Decimal
        import datetime
        
        # Vérification des entrées
        if not date_debut:
            return self.montant
        
        if not date_fin:
            date_fin = date_debut
        
        # S'assurer que la date de fin n'est pas antérieure à la date de début
        if date_fin < date_debut:
            date_fin = date_debut
        
        # Pour une périodicité unique, pas de prorata
        if self.periodicite == 'unique':
            return self.montant
        
        # Calcul de la période de base selon la périodicité
        if self.periodicite == 'mensuelle':
            # Une période = 30 jours
            periode_base = 30
        elif self.periodicite == 'trimestrielle':
            # Une période = 90 jours
            periode_base = 90
        elif self.periodicite == 'semestrielle':
            # Une période = 180 jours
            periode_base = 180
        else:  # annuelle
            # Une période = 365 jours
            periode_base = 365
        
        # Calcul de la durée effective en jours
        duree_effective = (date_fin - date_debut).days + 1  # +1 pour inclure le jour de début
        
        # Calcul du ratio (minimum 1 jour)
        ratio = max(1, duree_effective) / periode_base
        
        # Si la durée est supérieure à la période, on plafonne à 1 
        # (sauf pour périodicité annuelle où on peut dépasser)
        if self.periodicite != 'annuelle' and ratio > 1:
            ratio = 1
        
        # Calcul du montant proratisé (arrondi à 2 décimales)
        montant_proratise = self.montant * Decimal(ratio)
        return montant_proratise.quantize(Decimal('0.01'))

    def clean(self):
        from django.core.exceptions import ValidationError
        
        # Vérifier que le montant est positif
        if self.montant is not None and self.montant <= 0:
            raise ValidationError(_("Le montant doit être supérieur à zéro."))
        
        # Vérifier que la date de fin est postérieure à la date de début (si définie)
        if self.date_fin_validite and self.date_debut_validite and self.date_fin_validite <= self.date_debut_validite:
            raise ValidationError(_("La date de fin de validité doit être postérieure à la date de début."))


class ModePaiement(BaseModel):
    """
    Modèle pour les différents modes de paiement.
    """
    libelle = models.CharField(
        max_length=50,
        unique=True,
        verbose_name=_("Libellé")
    )
    description = models.TextField(
        null=True,
        blank=True,
        verbose_name=_("Description")
    )
    actif = models.BooleanField(
        default=True,
        verbose_name=_("Actif")
    )
    
    class Meta:
        verbose_name = _("Mode de paiement")
        verbose_name_plural = _("Modes de paiement")
        ordering = ['libelle']
    
    def __str__(self):
        return self.libelle


class Cotisation(BaseModel):
    """
    Modèle principal pour les cotisations des membres.
    """
    membre = models.ForeignKey(
        Membre,
        on_delete=models.CASCADE,
        related_name='cotisations',
        verbose_name=_("Membre")
    )
    montant = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_("Montant")
    )
    date_emission = models.DateField(
        default=timezone.now,
        verbose_name=_("Date d'émission")
    )
    date_echeance = models.DateField(
        verbose_name=_("Date d'échéance")
    )
    periode_debut = models.DateField(
        verbose_name=_("Début de période couverte")
    )
    periode_fin = models.DateField(
        verbose_name=_("Fin de période couverte"),
        null=True,
        blank=True
    )
    mois = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_("Mois")
    )
    annee = models.IntegerField(
        verbose_name=_("Année")
    )
    statut = models.ForeignKey(
        Statut,
        on_delete=models.SET_NULL,
        null=True,
        related_name='cotisations',
        verbose_name=_("Statut")
    )
    statut_paiement = models.CharField(
        max_length=20,
        choices=[
            ('non_payee', _('Non payée')),
            ('partiellement_payee', _('Partiellement payée')),
            ('payee', _('Payée')),
        ],
        default='non_payee',
        verbose_name=_("Statut de paiement")
    )
    montant_restant = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_("Montant restant à payer")
    )
    type_membre = models.ForeignKey(
        TypeMembre,
        on_delete=models.SET_NULL,
        null=True,
        related_name='cotisations',
        verbose_name=_("Type de membre")
    )
    bareme = models.ForeignKey(
        BaremeCotisation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cotisations',
        verbose_name=_("Barème utilisé")
    )
    reference = models.CharField(
        max_length=50,
        unique=True,
        verbose_name=_("Référence"),
        help_text=_("Référence unique de la cotisation")
    )
    commentaire = models.TextField(
        null=True,
        blank=True,
        verbose_name=_("Commentaire")
    )
    cree_par = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cotisations_creees',
        verbose_name=_("Créée par")
    )
    modifie_par = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cotisations_modifiees',
        verbose_name=_("Modifiée par")
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Métadonnées")
    )
    
    # Utiliser le gestionnaire personnalisé
    objects = CotisationManager()
    
    class Meta:
        verbose_name = _("Cotisation")
        verbose_name_plural = _("Cotisations")
        ordering = ['-date_emission']
        indexes = [
            models.Index(fields=['membre']),
            models.Index(fields=['date_echeance']),
            models.Index(fields=['statut_paiement']),
            models.Index(fields=['annee', 'mois']),
        ]
    
    def __str__(self):
        return f"{self.membre} - {self.montant} € ({self.date_emission})"
    
    def get_absolute_url(self):
        return reverse('cotisations:cotisation_detail', kwargs={'pk': self.pk})
    
    def save(self, *args, **kwargs):
        """
        Surcharge de save pour initialiser les champs calculés et générer une référence.
        """
        # Si c'est une création (pas d'id)
        if not self.pk:
            # S'assurer que le montant restant est égal au montant total
            if self.montant_restant is None or self.montant_restant == 0:
                self.montant_restant = self.montant
            
            # Génération de référence améliorée
            if not self.reference or self.reference == 'auto':
                self.reference = self._generer_reference()
                
            # Vérification de sécurité: pas de cotisation sans référence
            if not self.reference:
                raise ValueError("Impossible de créer une cotisation sans référence")
            
            # Extraire mois et année si non définis
            if not self.mois and self.periode_debut:
                self.mois = self.periode_debut.month
            
            if not self.annee and self.periode_debut:
                self.annee = self.periode_debut.year
        
        # Mettre à jour le statut de paiement en fonction du montant restant
        self._mettre_a_jour_statut_paiement()
        
        # Sauvegarder l'objet
        super().save(*args, **kwargs)
    
    def clean(self):
        from django.core.exceptions import ValidationError
        
        # Vérifier que le montant est positif
        if self.montant is not None and self.montant <= 0:
            raise ValidationError(_("Le montant doit être supérieur à zéro."))
        
        # Vérifier que la date d'échéance est postérieure à la date d'émission
        if self.date_echeance and self.date_emission and self.date_echeance < self.date_emission:
            raise ValidationError(_("La date d'échéance doit être postérieure à la date d'émission."))
        
        # Vérifier les dates de période
        if self.periode_fin and self.periode_debut and self.periode_fin < self.periode_debut:
            raise ValidationError(_("La fin de période doit être postérieure au début de période."))
    
    def _generer_reference(self):
        """
        Génère une référence unique pour la cotisation.
        Format: COT-YYYYMM-XXXXX (année, mois, numéro séquentiel)
        """
        import random
        import string
        
        prefix = 'COT'
        date_part = timezone.now().strftime('%Y%m')
        
        # Générer un identifiant aléatoire de 5 caractères
        chars = string.ascii_uppercase + string.digits
        random_part = ''.join(random.choice(chars) for _ in range(5))
        
        # Si le membre a un id, l'inclure dans la référence
        if self.membre and self.membre.id:
            membre_part = f"{self.membre.id:04d}"
            reference = f"{prefix}-{date_part}-{membre_part}-{random_part}"
        else:
            reference = f"{prefix}-{date_part}-{random_part}"
        
        # S'assurer que la référence est unique
        while Cotisation.objects.filter(reference=reference).exists():
            random_part = ''.join(random.choice(chars) for _ in range(5))
            reference = f"{prefix}-{date_part}-{random_part}"
        
        return reference
    
    def _mettre_a_jour_statut_paiement(self):
        """
        Met à jour le statut de paiement en fonction du montant restant.
        """
        if self.montant_restant <= 0:
            self.statut_paiement = 'payee'
        elif self.montant_restant < self.montant:
            self.statut_paiement = 'partiellement_payee'
        else:
            self.statut_paiement = 'non_payee'
    
    def get_montant_paye(self):
        """
        Calcule le montant total des paiements pour cette cotisation.
        """
        montant_paye = Decimal('0.00')
        for paiement in self.paiements.filter(deleted_at__isnull=True):
            # Ajouter les paiements positifs, soustraire les remboursements
            if paiement.type_transaction == 'paiement':
                montant_paye += paiement.montant
            elif paiement.type_transaction == 'remboursement':
                montant_paye -= paiement.montant
        
        return montant_paye
    
    def recalculer_montant_restant(self):
        """
        Recalcule le montant restant à payer et met à jour le statut.
        """
        montant_paye = self.get_montant_paye()
        self.montant_restant = max(Decimal('0'), self.montant - montant_paye)
        self._mettre_a_jour_statut_paiement()
        return self.montant_restant
    
    def to_json_dict(self):
        """
        Convertit les données du modèle en dictionnaire compatible JSON.
        Utilisé pour les champs JSON et l'historisation.
        """
        from decimal import Decimal
        
        # Créer un dictionnaire de base
        data = {
            'id': self.id,
            'reference': self.reference,
            'montant': float(self.montant) if isinstance(self.montant, Decimal) else self.montant,
            'montant_restant': float(self.montant_restant) if isinstance(self.montant_restant, Decimal) else self.montant_restant,
            'statut_paiement': self.statut_paiement,
            'date_emission': self.date_emission.isoformat() if self.date_emission else None,
            'date_echeance': self.date_echeance.isoformat() if self.date_echeance else None,
        }
        
        return data

    @property
    def est_en_retard(self):
        """
        Vérifie si la cotisation est en retard de paiement.
        """
        return (self.date_echeance < timezone.now().date() and 
                self.statut_paiement != 'payee')
    
    @property
    def jours_retard(self):
        """
        Calcule le nombre de jours de retard.
        """
        if self.est_en_retard:
            delta = timezone.now().date() - self.date_echeance
            return delta.days
        return 0
    
    @property
    def est_complete(self):
        """
        Vérifie si la cotisation est complètement payée.
        """
        return self.statut_paiement == 'payee'


class Paiement(BaseModel):
    """
    Modèle pour les paiements associés aux cotisations.
    """
    cotisation = models.ForeignKey(
        Cotisation,
        on_delete=models.CASCADE,
        related_name='paiements',
        verbose_name=_("Cotisation")
    )
    montant = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_("Montant")
    )
    date_paiement = models.DateTimeField(
        default=timezone.now,
        verbose_name=_("Date de paiement")
    )
    mode_paiement = models.ForeignKey(
        ModePaiement,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='paiements',
        verbose_name=_("Mode de paiement")
    )
    reference_paiement = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name=_("Référence de paiement")
    )
    statut = models.ForeignKey(
        Statut,
        on_delete=models.SET_NULL,
        null=True,
        related_name='paiements',
        verbose_name=_("Statut")
    )
    devise = models.CharField(
        max_length=3,
        default='EUR',
        verbose_name=_("Devise")
    )
    type_transaction = models.CharField(
        max_length=20,
        choices=[
            ('paiement', _('Paiement')),
            ('remboursement', _('Remboursement')),
            ('rejet', _('Rejet')),
        ],
        default='paiement',
        verbose_name=_("Type de transaction")
    )
    recu_envoye = models.BooleanField(
        default=False,
        verbose_name=_("Reçu envoyé")
    )
    commentaire = models.TextField(
        null=True,
        blank=True,
        verbose_name=_("Commentaire")
    )
    cree_par = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='paiements_crees',
        verbose_name=_("Créé par")
    )
    modifie_par = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='paiements_modifies',
        verbose_name=_("Modifié par")
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Métadonnées")
    )
    
    # Utiliser le gestionnaire personnalisé
    objects = PaiementManager()
    
    class Meta:
        verbose_name = _("Paiement")
        verbose_name_plural = _("Paiements")
        ordering = ['-date_paiement']
        indexes = [
            models.Index(fields=['cotisation']),
            models.Index(fields=['date_paiement']),
            models.Index(fields=['type_transaction']),
        ]
    
    def __str__(self):
        return f"{self.cotisation.membre} - {self.montant} € ({self.date_paiement})"
    
    def get_absolute_url(self):
        return reverse('cotisations:paiement_detail', kwargs={'pk': self.pk})
    
    # Dans apps/cotisations/models.py, classe Paiement

    def _generer_reference(self):
        """
        Génère une référence unique pour le paiement basée sur le type de transaction.
        Format: [PAI|RMB|REJ]-YYYYMMDD-XXXXX
        """
        import random
        import string
        
        # Préfixe selon le type de transaction
        prefixes = {
            'paiement': 'PAI',
            'remboursement': 'RMB',
            'rejet': 'REJ'
        }
        prefix = prefixes.get(self.type_transaction, 'PAI')
        
        # Date au format YYYYMMDD
        date_part = timezone.now().strftime('%Y%m%d')
        
        # Identifiant de la cotisation
        cotisation_part = f"{self.cotisation.id:04d}" if self.cotisation else "0000"
        
        # Partie aléatoire
        chars = string.ascii_uppercase + string.digits
        random_part = ''.join(random.choice(chars) for _ in range(4))
        
        # Assembler la référence
        reference = f"{prefix}-{date_part}-{cotisation_part}-{random_part}"
        
        # Vérifier l'unicité
        while Paiement.objects.filter(reference_paiement=reference).exists():
            random_part = ''.join(random.choice(chars) for _ in range(4))
            reference = f"{prefix}-{date_part}-{cotisation_part}-{random_part}"
        
        return reference

    def save(self, *args, **kwargs):
        """
        Surcharge de save pour mettre à jour le montant restant de la cotisation et générer une référence.
        """
        # Valider les données
        self.clean()
        
        # Générer une référence si nouvelle instance
        is_new = self.pk is None
        if is_new:
            self.reference_paiement = self._generer_reference()
        
        # Sauvegarder le paiement
        super().save(*args, **kwargs)
        
        # Mettre à jour le montant restant de la cotisation
        if is_new or kwargs.get('update_fields') is None or 'montant' in kwargs.get('update_fields', []):
            self.cotisation.recalculer_montant_restant()
            self.cotisation.save(update_fields=['montant_restant', 'statut_paiement'])
    
    def delete(self, hard=False, *args, **kwargs):
        """
        Surcharge de delete pour mettre à jour le montant restant de la cotisation.
        """
        cotisation = self.cotisation  # Stocker la référence avant suppression
        result = super().delete(hard=hard, *args, **kwargs)
        
        # Mettre à jour le montant restant si suppression physique ou logique
        cotisation.recalculer_montant_restant()
        cotisation.save(update_fields=['montant_restant', 'statut_paiement'])
        
        return result
    
    def clean(self):
        from django.core.exceptions import ValidationError
        
        # Vérifier que le montant est positif
        if self.montant is not None and self.montant <= 0:
            raise ValidationError(_("Le montant doit être supérieur à zéro."))


class Rappel(BaseModel):
    """
    Modèle pour les rappels de cotisations.
    """
    membre = models.ForeignKey(
        Membre,
        on_delete=models.CASCADE,
        related_name='rappels',
        verbose_name=_("Membre")
    )
    cotisation = models.ForeignKey(
        Cotisation,
        on_delete=models.CASCADE,
        related_name='rappels',
        verbose_name=_("Cotisation")
    )
    date_envoi = models.DateTimeField(
        default=timezone.now,
        verbose_name=_("Date d'envoi")
    )
    type_rappel = models.CharField(
        max_length=20,
        choices=[
            ('email', _('Email')),
            ('sms', _('SMS')),
            ('courrier', _('Courrier')),
            ('appel', _('Appel téléphonique')),
        ],
        verbose_name=_("Type de rappel")
    )
    contenu = models.TextField(
        null=True,
        blank=True,
        verbose_name=_("Contenu")
    )
    etat = models.CharField(
        max_length=20,
        choices=[
            ('planifie', _('Planifié')),
            ('envoye', _('Envoyé')),
            ('echoue', _('Échoué')),
            ('lu', _('Lu')),
        ],
        default='planifie',
        verbose_name=_("État")
    )
    niveau = models.PositiveSmallIntegerField(
        default=1,
        verbose_name=_("Niveau de rappel"),
        help_text=_("Niveau de priorité/sévérité du rappel (1: premier rappel, 2: relance, etc.)")
    )
    # Date de création (toujours maintenant)
    date_creation = models.DateTimeField(
        verbose_name=_("Date de création"),
        default=timezone.now,
        editable=False
    )
    # Date d'envoi (peut être dans le futur si planifié)
    date_envoi = models.DateTimeField(
        verbose_name=_("Date d'envoi"),
        default=timezone.now
    )
    cree_par = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='rappels_crees',
        verbose_name=_("Créé par")
    )
    resultat = models.TextField(
        null=True,
        blank=True,
        verbose_name=_("Résultat/Retour"),
        help_text=_("Résultat de l'envoi ou commentaire sur le suivi")
    )
    
    class Meta:
        verbose_name = _("Rappel")
        verbose_name_plural = _("Rappels")
        ordering = ['-date_envoi']
        indexes = [
            models.Index(fields=['membre']),
            models.Index(fields=['cotisation']),
            models.Index(fields=['date_envoi']),
            models.Index(fields=['etat']),
        ]
    
    def __str__(self):
        return f"{self.membre} - {self.get_type_rappel_display()} ({self.date_envoi})"
    
    def get_absolute_url(self):
        return reverse('cotisations:rappel_detail', kwargs={'pk': self.pk})


class HistoriqueCotisation(BaseModel):
    """
    Modèle pour l'historique des modifications de cotisations.
    """
    cotisation = models.ForeignKey(
        Cotisation,
        on_delete=models.CASCADE,
        related_name='historique',
        verbose_name=_("Cotisation")
    )
    action = models.CharField(
        max_length=50,
        verbose_name=_("Action")
    )
    details = models.JSONField(
        default=dict,
        verbose_name=_("Détails")
    )
    date_action = models.DateTimeField(
        default=timezone.now,
        verbose_name=_("Date de l'action")
    )
    utilisateur = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='historique_cotisations',
        verbose_name=_("Utilisateur")
    )
    adresse_ip = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name=_("Adresse IP")
    )
    commentaire = models.TextField(
        null=True,
        blank=True,
        verbose_name=_("Commentaire")
    )
    
    class Meta:
        verbose_name = _("Historique de cotisation")
        verbose_name_plural = _("Historique des cotisations")
        ordering = ['-date_action']
        indexes = [
            models.Index(fields=['cotisation']),
            models.Index(fields=['date_action']),
            models.Index(fields=['action']),
        ]
    
    def __str__(self):
        return f"{self.action} - {self.cotisation} - {self.date_action}"


class ConfigurationCotisation(BaseModel):
    """
    Modèle pour les configurations générales des cotisations.
    """
    cle = models.CharField(
        max_length=50,
        unique=True,
        verbose_name=_("Clé")
    )
    valeur = models.TextField(
        verbose_name=_("Valeur")
    )
    description = models.TextField(
        null=True,
        blank=True,
        verbose_name=_("Description")
    )
    
    class Meta:
        verbose_name = _("Configuration de cotisation")
        verbose_name_plural = _("Configurations de cotisations")
        ordering = ['cle']
    
    def __str__(self):
        return self.cle