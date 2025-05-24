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

from .validators import (
    RappelTypeValidator, 
    SujetRappelValidator, 
    DateEnvoiRappelValidator,
    VariablesRappelValidator
)
from .type_rappel_config import TypeRappelConfig

# Constantes pour les états des rappels
RAPPEL_ETAT_PLANIFIE = 'planifie'
RAPPEL_ETAT_ENVOYE = 'envoye'
RAPPEL_ETAT_ECHOUE = 'echoue'
RAPPEL_ETAT_LU = 'lu'

RAPPEL_ETAT_CHOICES = [
    (RAPPEL_ETAT_PLANIFIE, _('Planifié')),
    (RAPPEL_ETAT_ENVOYE, _('Envoyé')),
    (RAPPEL_ETAT_ECHOUE, _('Échoué')),
    (RAPPEL_ETAT_LU, _('Lu')),
]

RAPPEL_TYPE_CHOICES = [
    ('email', _('Email')),
    ('sms', _('SMS')),
    ('courrier', _('Courrier')),
    ('appel', _('Appel téléphonique')),
]

# Autres constantes utiles
COTISATION_STATUT_NON_PAYEE = 'non_payee'
COTISATION_STATUT_PARTIELLEMENT_PAYEE = 'partiellement_payee'
COTISATION_STATUT_PAYEE = 'payee'

# Types de transactions pour les paiements
PAIEMENT_TYPE_PAIEMENT = 'paiement'
PAIEMENT_TYPE_REMBOURSEMENT = 'remboursement'
PAIEMENT_TYPE_REJET = 'rejet'

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

    def restore(self):
        """
        Restaure une cotisation qui a été supprimée logiquement.
        """
        if self.deleted_at:
            self.deleted_at = None
            self.save(update_fields=['deleted_at'])
            # Si vous avez un historique des actions, vous pourriez vouloir l'enregistrer ici
            # Par exemple:
            # if hasattr(self, 'log_action'):
            #     self.log_action('restauration')
        return self

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
            
            # Attribuer un statut par défaut si aucun n'est défini
            if self.statut is None:
                # Import local pour éviter les imports circulaires
                from apps.core.models import Statut
                
                # Chercher un statut approprié pour les paiements
                default_status = Statut.objects.filter(nom__iexact='Validé').first()
                if not default_status:
                    default_status = Statut.objects.filter(nom__iexact='Non payé').first()
                if not default_status:
                    # Si aucun statut spécifique n'existe, créer un statut "Validé"
                    default_status = Statut.objects.create(
                        nom='Validé',
                        description='Statut par défaut pour les paiements validés'
                    )
                self.statut = default_status
        
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

class RappelTemplate(BaseModel):
    """
    Modèle amélioré pour les templates de rappel avec contraintes intelligentes.
    """
    TEMPLATE_TYPE_CHOICES = [
        ('standard', _('Standard')),
        ('urgent', _('Urgent')),
        ('formal', _('Formel/Mise en demeure')),
        ('custom', _('Personnalisé')),
    ]
    
    RAPPEL_TYPE_CHOICES = [
        ('email', _('Email')),
        ('sms', _('SMS')),
        ('courrier', _('Courrier')),
        ('appel', _('Appel téléphonique')),
    ]
    
    nom = models.CharField(
        max_length=100,
        verbose_name=_("Nom du template"),
        help_text=_("Nom descriptif pour identifier le template")
    )
    
    type_template = models.CharField(
        max_length=20,
        choices=TEMPLATE_TYPE_CHOICES,
        default='standard',
        verbose_name=_("Type de template")
    )
    
    type_rappel = models.CharField(
        max_length=20,
        choices=RAPPEL_TYPE_CHOICES,
        default='email',
        verbose_name=_("Type de rappel"),
        help_text=_("Pour quel mode de communication ce template est destiné")
    )
    
    sujet = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_("Sujet"),
        help_text=_("Sujet du message (pour emails principalement)")
    )
    
    contenu = models.TextField(
        verbose_name=_("Contenu du template"),
        help_text=_(
            "Variables disponibles: {prenom}, {nom}, {reference}, {montant}, "
            "{date_echeance}, {date_limite}, {jours_retard}, {association_nom}"
        )
    )
    
    langue = models.CharField(
        max_length=5,
        default='fr',
        verbose_name=_("Langue"),
        help_text=_("Code langue (fr, en, etc.)")
    )
    
    actif = models.BooleanField(
        default=True,
        verbose_name=_("Actif"),
        help_text=_("Template disponible pour utilisation")
    )
    
    niveau_min = models.PositiveIntegerField(
        default=1,
        verbose_name=_("Niveau minimum"),
        help_text=_("Niveau de rappel minimum pour utiliser ce template")
    )
    
    niveau_max = models.PositiveIntegerField(
        default=5,
        verbose_name=_("Niveau maximum"),
        help_text=_("Niveau de rappel maximum pour utiliser ce template")
    )
    
    ordre_affichage = models.PositiveIntegerField(
        default=10,
        verbose_name=_("Ordre d'affichage"),
        help_text=_("Ordre dans la liste des templates")
    )
    
    # Nouvelles métadonnées pour les contraintes intelligentes
    variables_supplementaires = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Variables supplémentaires"),
        help_text=_("Variables personnalisées pour ce template")
    )
    
    # Statistiques d'utilisation
    nb_utilisations = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Nombre d'utilisations"),
        help_text=_("Compteur d'utilisation du template")
    )
    
    derniere_utilisation = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Dernière utilisation")
    )
    
    # Métadonnées de performance
    taux_efficacite = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_("Taux d'efficacité"),
        help_text=_("Pourcentage de rappels ayant obtenu une réponse")
    )
    
    class Meta:
        verbose_name = _("Template de rappel")
        verbose_name_plural = _("Templates de rappels")
        ordering = ['type_template', 'ordre_affichage', 'nom']
        unique_together = ['nom', 'type_template', 'type_rappel', 'langue']
        indexes = [
            models.Index(fields=['type_rappel', 'type_template', 'actif']),
            models.Index(fields=['niveau_min', 'niveau_max']),
            models.Index(fields=['langue', 'actif']),
        ]
    
    def __str__(self):
        return f"{self.nom} ({self.get_type_template_display()}) - {self.get_type_rappel_display()}"
    
    def clean(self):
        """
        Validation personnalisée avec contraintes intelligentes.
        """
        from django.core.exceptions import ValidationError
        
        super().clean()
        
        # Validation niveau min/max
        if self.niveau_max < self.niveau_min:
            raise ValidationError({
                'niveau_max': _("Le niveau maximum doit être supérieur ou égal au niveau minimum.")
            })
        
        # Validation intelligente du sujet
        try:
            validator_sujet = SujetRappelValidator(self.type_rappel)
            validator_sujet(self.sujet)
        except ValidationError as e:
            raise ValidationError({'sujet': e.message})
        
        # Validation intelligente du contenu
        try:
            validator_contenu = RappelTypeValidator(self.type_rappel)
            validator_contenu(self.contenu)
        except ValidationError as e:
            raise ValidationError({'contenu': e.message})
        
        # Validation des variables
        try:
            validator_variables = VariablesRappelValidator(self.type_rappel)
            validator_variables(self.contenu)
        except ValidationError as e:
            # Pour les variables, on ne bloque pas mais on warning
            import logging
            logger = logging.getLogger('cotisations.models')
            logger.warning(f"Variables dans template {self.nom}: {e.message}")
    
    def save(self, *args, **kwargs):
        """
        Sauvegarde avec validation et optimisation automatique.
        """
        # Validation complète avant sauvegarde
        try:
            self.full_clean()
        except ValidationError as e:
            # Log les erreurs mais ne bloque pas si c'est un template existant
            import logging
            logger = logging.getLogger('cotisations.models')
            logger.error(f"Erreurs validation template {self.nom}: {e}")
        
        # Optimisation automatique du contenu si demandée
        if hasattr(self, '_auto_optimize') and self._auto_optimize:
            self.contenu = self._optimiser_contenu()
        
        super().save(*args, **kwargs)
    
    def generer_contenu(self, cotisation, variables_custom=None, optimiser=False):
        """
        Génère le contenu du rappel avec contraintes intelligentes.
        
        Args:
            cotisation: Instance de Cotisation
            variables_custom: Dict de variables supplémentaires
            optimiser: Boolean pour optimiser automatiquement
        
        Returns:
            str: Contenu avec variables remplacées et validé
        """
        import re
        from datetime import timedelta
        
        membre = cotisation.membre
        
        # Variables de base
        variables = {
            'prenom': membre.prenom,
            'nom': membre.nom,
            'email': membre.email,
            'reference': cotisation.reference,
            'montant': f"{cotisation.montant_restant:.2f}",
            'montant_total': f"{cotisation.montant:.2f}",
            'date_echeance': cotisation.date_echeance.strftime('%d/%m/%Y'),
            'jours_retard': str(cotisation.jours_retard) if cotisation.est_en_retard else '0',
            'association_nom': getattr(settings, 'ASSOCIATION_NAME', 'Notre Association'),
        }
        
        # Date limite de paiement (par défaut +15 jours)
        date_limite = timezone.now().date() + timedelta(days=15)
        variables['date_limite'] = date_limite.strftime('%d/%m/%Y')
        
        # Variables spécialisées selon le type
        variables_speciales = self._get_variables_speciales(cotisation)
        variables.update(variables_speciales)
        
        # Ajouter les variables supplémentaires du template
        if self.variables_supplementaires:
            variables.update(self.variables_supplementaires)
        
        # Ajouter les variables personnalisées
        if variables_custom:
            variables.update(variables_custom)
        
        # Remplacer les variables dans le contenu
        contenu = self.contenu
        for var, valeur in variables.items():
            contenu = contenu.replace(f'{{{var}}}', str(valeur))
        
        # Optimisation intelligente si demandée
        if optimiser:
            from .validators import _optimiser_contenu_automatique
            contenu = _optimiser_contenu_automatique(self.type_rappel, contenu, 1)
        
        # Validation finale du contenu généré
        try:
            validator = RappelTypeValidator(self.type_rappel)
            validator(contenu)
        except ValidationError as e:
            import logging
            logger = logging.getLogger('cotisations.models')
            logger.warning(f"Contenu généré non optimal pour {self.nom}: {e}")
        
        return contenu
    
    def _get_variables_speciales(self, cotisation):
        """
        Génère les variables spécialisées selon le type de rappel.
        """
        variables = {}
        
        if self.type_rappel == 'email':
            variables.update({
                'lien_paiement': f"/cotisations/{cotisation.id}/payer/",
                'signature_html': self._get_signature_html(),
                'bouton_contact': self._get_bouton_contact_html(),
            })
        
        elif self.type_rappel == 'sms':
            variables.update({
                'lien_court': f"pay.ly/{cotisation.reference[-6:]}",  # Lien raccourci simulé
                'tel_urgence': getattr(settings, 'PHONE_NUMBER', '0123456789'),
                'ref_courte': cotisation.reference[-6:],
                'nom_court': cotisation.membre.nom[:10],
                'montant_simple': f"{cotisation.montant_restant:.0f}",
            })
        
        elif self.type_rappel == 'courrier':
            variables.update({
                'adresse_complete': self._format_adresse_complete(cotisation.membre),
                'mentions_legales': self._get_mentions_legales(),
                'cachet': '[CACHET DE L\'ASSOCIATION]',
                'signature_manuscrite': '[SIGNATURE]',
                'en_tete_officiel': self._get_en_tete_officiel(),
                'date_envoi_courrier': timezone.now().strftime('%d %B %Y'),
            })
        
        return variables
    
    def _get_signature_html(self):
        """Génère une signature HTML pour les emails."""
        return f"""
        <div style="margin-top: 20px; padding-top: 15px; border-top: 1px solid #ddd;">
            <p style="margin: 5px 0;"><strong>{getattr(settings, 'ASSOCIATION_NAME', 'Notre Association')}</strong></p>
            <p style="margin: 5px 0; color: #666;">
                {getattr(settings, 'ASSOCIATION_ADDRESS', '[Adresse]')}<br>
                Tél: {getattr(settings, 'PHONE_NUMBER', '[Téléphone]')}<br>
                Email: {getattr(settings, 'EMAIL_ADDRESS', '[Email]')}
            </p>
        </div>
        """
    
    def _get_bouton_contact_html(self):
        """Génère un bouton de contact HTML."""
        return f"""
        <div style="text-align: center; margin: 20px 0;">
            <a href="mailto:{getattr(settings, 'EMAIL_ADDRESS', 'contact@association.fr')}" 
               style="display: inline-block; padding: 10px 20px; background-color: #007bff; 
                      color: white; text-decoration: none; border-radius: 5px;">
                Nous contacter
            </a>
        </div>
        """
    
    def _format_adresse_complete(self, membre):
        """Formate l'adresse complète du membre pour courrier."""
        adresse_parts = [membre.nom.upper(), membre.prenom]
        if membre.adresse:
            adresse_parts.append(membre.adresse)
        return '\n'.join(filter(None, adresse_parts))
    
    def _get_mentions_legales(self):
        """Récupère les mentions légales pour courrier."""
        return f"""
Association régie par la loi du 1er juillet 1901
SIRET: {getattr(settings, 'SIRET_NUMBER', '[SIRET]')}
Déclaration préfectorale: {getattr(settings, 'PREFECTURE_NUMBER', '[N° Préfecture]')}
        """.strip()
    
    def _get_en_tete_officiel(self):
        """Génère l'en-tête officiel pour courrier."""
        return f"""
{getattr(settings, 'ASSOCIATION_NAME', 'NOTRE ASSOCIATION')}
{getattr(settings, 'ASSOCIATION_ADDRESS', '[Adresse complète]')}
Tél: {getattr(settings, 'PHONE_NUMBER', '[Téléphone]')}
Email: {getattr(settings, 'EMAIL_ADDRESS', '[Email]')}
        """.strip()
    
    def incrementer_utilisation(self):
        """
        Incrémente le compteur d'utilisation du template.
        """
        self.nb_utilisations += 1
        self.derniere_utilisation = timezone.now()
        self.save(update_fields=['nb_utilisations', 'derniere_utilisation'])
    
    def calculer_efficacite(self, rappels_reussis, rappels_totaux):
        """
        Calcule et met à jour le taux d'efficacité du template.
        """
        if rappels_totaux > 0:
            self.taux_efficacite = (rappels_reussis / rappels_totaux) * 100
            self.save(update_fields=['taux_efficacite'])
    
    def get_contraintes(self):
        """
        Récupère les contraintes spécifiques à ce template.
        """
        return TypeRappelConfig.get_contraintes_ui(self.type_rappel)
    
    def valider_avec_contraintes(self):
        """
        Valide le template avec toutes les contraintes intelligentes.
        """
        from .validators import valider_rappel_complet
        
        return valider_rappel_complet(
            self.type_rappel,
            self.sujet,
            self.contenu
        )
    
    @classmethod
    def get_templates_intelligents(cls, type_rappel, niveau=1, langue='fr', cotisation=None):
        """
        Récupère les templates avec recommandations intelligentes.
        """
        templates = cls.get_templates_pour_type(type_rappel, niveau, langue)
        
        # Si on a une cotisation, on peut faire des recommandations plus précises
        if cotisation:
            jours_retard = cotisation.jours_retard if cotisation.est_en_retard else 0
            niveau_recommande = TypeRappelConfig.get_niveau_recommande(type_rappel, jours_retard)
            
            # Prioriser les templates du niveau recommandé
            templates_recommandes = templates.filter(type_template=niveau_recommande)
            templates_autres = templates.exclude(type_template=niveau_recommande)
            
            # Combiner avec priorité aux recommandés
            templates = list(templates_recommandes) + list(templates_autres)
        
        return templates
    
    @classmethod
    def analyser_performance_templates(cls):
        """
        Analyse la performance de tous les templates.
        """
        from django.db.models import Avg, Count
        
        stats = cls.objects.aggregate(
            utilisation_moyenne=Avg('nb_utilisations'),
            efficacite_moyenne=Avg('taux_efficacite'),
            total_templates=Count('id')
        )
        
        # Templates les plus utilisés
        top_templates = cls.objects.order_by('-nb_utilisations')[:5]
        
        # Templates les plus efficaces
        best_templates = cls.objects.filter(
            taux_efficacite__isnull=False
        ).order_by('-taux_efficacite')[:5]
        
        return {
            'statistiques_globales': stats,
            'templates_populaires': top_templates,
            'templates_efficaces': best_templates
        }

class Rappel(BaseModel):
    """
    Modèle pour les rappels de cotisations avec validation intelligente.
    """
    membre = models.ForeignKey(
        'membres.Membre',
        on_delete=models.CASCADE,
        verbose_name=_("Membre"),
        help_text=_("Membre destinataire du rappel")
    )
    
    cotisation = models.ForeignKey(
        Cotisation,
        on_delete=models.CASCADE,
        related_name='rappels',
        verbose_name=_("Cotisation"),
        help_text=_("Cotisation concernée par le rappel")
    )
    
    type_rappel = models.CharField(
        max_length=20,
        choices=RAPPEL_TYPE_CHOICES,
        default='email',
        verbose_name=_("Type de rappel"),
        help_text=_("Mode d'envoi du rappel")
    )
    
    niveau = models.PositiveIntegerField(
        default=1,
        verbose_name=_("Niveau de rappel"),
        help_text=_("Niveau d'urgence du rappel (1: Premier rappel, 2: Relance, etc.)")
    )
    
    contenu = models.TextField(
        default="Rappel de cotisation - Veuillez procéder au règlement de votre cotisation.",
        verbose_name=_("Contenu du rappel"),
        help_text=_("Message à envoyer au membre")
    )
    
    date_envoi = models.DateTimeField(
        verbose_name=_("Date d'envoi"),
        help_text=_("Date et heure d'envoi du rappel")
    )
    
    etat = models.CharField(
        max_length=20,
        choices=RAPPEL_ETAT_CHOICES,
        default=RAPPEL_ETAT_PLANIFIE,
        verbose_name=_("État"),
        help_text=_("État actuel du rappel")
    )
    
    resultat = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("Résultat"),
        help_text=_("Résultat de l'envoi (erreur, accusé de réception, etc.)")
    )
    
    # Champs optionnels qui peuvent exister selon votre implémentation
    cree_par = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Créé par"),
        help_text=_("Utilisateur qui a créé le rappel")
    )
    
    # NOUVEAUX CHAMPS pour les templates matriciels
    template_utilise = models.ForeignKey(
        RappelTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Template utilisé"),
        help_text=_("Template ayant servi à générer ce rappel")
    )
    
    # Métadonnées de validation
    valide_contraintes = models.BooleanField(
        default=True,
        verbose_name=_("Valide selon contraintes"),
        help_text=_("Le rappel respecte-t-il les contraintes de son type")
    )
    
    erreurs_validation = models.JSONField(
        default=list,
        blank=True,
        verbose_name=_("Erreurs de validation"),
        help_text=_("Liste des erreurs de validation détectées")
    )
    
    class Meta:
        verbose_name = _("Rappel")
        verbose_name_plural = _("Rappels")
        ordering = ['-date_envoi']
        indexes = [
            models.Index(fields=['date_envoi']),
            models.Index(fields=['etat']),
            models.Index(fields=['membre', 'cotisation']),
        ]
    
    def __str__(self):
        return f"Rappel {self.get_type_rappel_display()} - {self.membre} - {self.date_envoi.strftime('%d/%m/%Y')}"
    
    @property
    def est_envoye(self):
        """Retourne True si le rappel a été envoyé."""
        return self.etat in [RAPPEL_ETAT_ENVOYE, RAPPEL_ETAT_LU]
    
    @property
    def peut_etre_modifie(self):
        """Retourne True si le rappel peut encore être modifié."""
        return self.etat == RAPPEL_ETAT_PLANIFIE
    
    def marquer_comme_envoye(self):
        """Marque le rappel comme envoyé."""
        self.etat = RAPPEL_ETAT_ENVOYE
        if not self.date_envoi or self.date_envoi > timezone.now():
            self.date_envoi = timezone.now()
        self.save(update_fields=['etat', 'date_envoi'])
    
    def marquer_comme_echoue(self, raison=None):
        """Marque le rappel comme échoué."""
        self.etat = RAPPEL_ETAT_ECHOUE
        if raison:
            self.resultat = str(raison)
        self.save(update_fields=['etat', 'resultat'])
    
    def clean(self):
        """
        Validation intelligente du rappel.
        """
        super().clean()
        
        # Validation avec contraintes intelligentes
        valide, erreurs = self._valider_avec_contraintes()
        
        self.valide_contraintes = valide
        self.erreurs_validation = [
            {'champ': err[0], 'message': err[1]} 
            for err in erreurs
        ]
        
        # Si validation échoue, lever une exception
        if not valide and erreurs:
            from django.core.exceptions import ValidationError
            raise ValidationError({
                err[0]: err[1] for err in erreurs[:3]  # Max 3 erreurs affichées
            })
    
    def _valider_avec_contraintes(self):
        """
        Valide le rappel avec les contraintes intelligentes.
        """
        try:
            from .validators import valider_rappel_complet
            return valider_rappel_complet(
                self.type_rappel,
                '',  # Pas de sujet dans le modèle Rappel actuel
                self.contenu,
                self.date_envoi,
                1  # Un seul destinataire
            )
        except ImportError:
            # Si les validators n'existent pas encore, retourner True
            return True, []
    
    def save(self, *args, **kwargs):
        """
        Sauvegarde avec validation intelligente.
        """
        # Validation avant sauvegarde
        if not kwargs.get('skip_validation', False):
            try:
                self.full_clean()
            except ValidationError as e:
                import logging
                logger = logging.getLogger('cotisations.models')
                logger.error(f"Erreurs validation rappel {self.id}: {e}")
        
        # Incrémenter le compteur d'utilisation du template
        if self.template_utilise:
            self.template_utilise.incrementer_utilisation()
        
        super().save(*args, **kwargs)
    
    def marquer_comme_reussi(self):
        """
        Marque le rappel comme réussi et met à jour les stats du template.
        """
        self.etat = 'lu'  # ou autre état de succès
        self.save()
        
        # Mettre à jour les statistiques du template
        if self.template_utilise:
            rappels_template = Rappel.objects.filter(template_utilise=self.template_utilise)
            rappels_reussis = rappels_template.filter(etat='lu').count()
            rappels_totaux = rappels_template.count()
            
            self.template_utilise.calculer_efficacite(rappels_reussis, rappels_totaux)


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

class HistoriqueTransaction(models.Model):
    """
    Modèle pour enregistrer l'historique des transactions (cotisations et paiements)
    """
    TYPE_CHOICES = (
        ('cotisation', 'Cotisation'),
        ('paiement', 'Paiement'),
    )
    
    ACTION_CHOICES = (
        ('creation', 'Création'),
        ('modification', 'Modification'),
        ('suppression', 'Suppression'),
    )
    
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    reference_id = models.IntegerField()
    action = models.CharField(max_length=12, choices=ACTION_CHOICES)
    details = models.JSONField(null=True, blank=True)
    utilisateur_id = models.IntegerField(null=True, blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'historique_transactions'  # Nom exact de la table dans la base de données
        verbose_name = "Historique de transaction"
        verbose_name_plural = "Historique des transactions"
        
    def __str__(self):
        return f"{self.get_type_display()} - {self.get_action_display()} - {self.date_creation}"
    
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