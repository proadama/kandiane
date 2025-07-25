# apps/evenements/models.py
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from decimal import Decimal
import uuid

from apps.core.models import BaseModel
from apps.membres.models import Membre
from apps.accounts.models import CustomUser
from apps.cotisations.models import ModePaiement

from .managers import (
    TypeEvenementManager, EvenementManager, InscriptionEvenementManager,
    ValidationEvenementManager, SessionEvenementManager, AccompagnantInviteManager
)

class TypeEvenement(BaseModel):
    """
    Modèle pour les types d'événements (formations, réunions, sorties, etc.)
    """
    COMPORTEMENTS_CHOICES = [
        ('formation', 'Formation'),
        ('reunion', 'Réunion'),
        ('sortie', 'Sortie'),
        ('assemblee_generale', 'Assemblée Générale'),
        ('seminaire', 'Séminaire'),
        ('webinaire', 'Webinaire'),
        ('autre', 'Autre'),
    ]
    
    libelle = models.CharField(
        max_length=100, 
        unique=True,
        verbose_name="Libellé"
    )
    description = models.TextField(
        blank=True, 
        verbose_name="Description"
    )
    couleur_affichage = models.CharField(
        max_length=7, 
        default='#007bff',
        help_text="Code couleur hexadécimal pour l'affichage (ex: #007bff)",
        verbose_name="Couleur d'affichage"
    )
    comportements_specifiques = models.JSONField(
        default=dict,
        blank=True,
        help_text="Configuration des comportements spécifiques à ce type d'événement",
        verbose_name="Comportements spécifiques"
    )
    necessite_validation = models.BooleanField(
        default=False,
        verbose_name="Nécessite une validation"
    )
    permet_accompagnants = models.BooleanField(
        default=True,
        verbose_name="Permet les accompagnants"
    )
    ordre_affichage = models.PositiveIntegerField(
        default=0,
        verbose_name="Ordre d'affichage"
    )

    objects = TypeEvenementManager()

    class Meta:
        db_table = 'types_evenements'
        verbose_name = "Type d'événement"
        verbose_name_plural = "Types d'événements"
        ordering = ['ordre_affichage', 'libelle']

    def __str__(self):
        return self.libelle

    def save(self, *args, **kwargs):
        # Validation de la couleur hexadécimale
        if self.couleur_affichage and not self.couleur_affichage.startswith('#'):
            self.couleur_affichage = f'#{self.couleur_affichage}'
        super().save(*args, **kwargs)


class Evenement(BaseModel):
    """
    Modèle principal pour les événements
    """
    STATUT_CHOICES = [
        ('brouillon', 'Brouillon'),
        ('en_attente_validation', 'En attente de validation'),
        ('publie', 'Publié'),
        ('annule', 'Annulé'),
        ('termine', 'Terminé'),
        ('reporte', 'Reporté'),
    ]

    # Informations de base
    titre = models.CharField(
        max_length=255,
        verbose_name="Titre"
    )
    description = models.TextField(
        verbose_name="Description"
    )
    
    # Dates et heures
    date_debut = models.DateTimeField(
        verbose_name="Date et heure de début"
    )
    date_fin = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Date et heure de fin"
    )
    
    # Lieu
    lieu = models.CharField(
        max_length=255,
        verbose_name="Lieu"
    )
    adresse_complete = models.TextField(
        blank=True,
        verbose_name="Adresse complète"
    )
    
    # Capacité et inscriptions
    capacite_max = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        verbose_name="Capacité maximum"
    )
    inscriptions_ouvertes = models.BooleanField(
        default=True,
        verbose_name="Inscriptions ouvertes"
    )
    date_ouverture_inscriptions = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Date d'ouverture des inscriptions"
    )
    date_fermeture_inscriptions = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Date de fermeture des inscriptions"
    )
    
    # Tarification
    est_payant = models.BooleanField(
        default=False,
        verbose_name="Événement payant"
    )
    tarif_membre = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Tarif membre"
    )
    tarif_salarie = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Tarif salarié"
    )
    tarif_invite = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Tarif invité"
    )
    
    # Accompagnants
    permet_accompagnants = models.BooleanField(
        default=True,
        verbose_name="Permet les accompagnants"
    )
    nombre_max_accompagnants = models.PositiveIntegerField(
        default=2,
        validators=[MinValueValidator(0), MaxValueValidator(10)],
        verbose_name="Nombre maximum d'accompagnants"
    )
    
    # Confirmation
    delai_confirmation = models.PositiveIntegerField(
        default=48,
        help_text="Délai en heures pour confirmer l'inscription",
        verbose_name="Délai de confirmation (heures)"
    )
    
    # Relations
    type_evenement = models.ForeignKey(
        TypeEvenement,
        on_delete=models.PROTECT,
        verbose_name="Type d'événement"
    )
    organisateur = models.ForeignKey(
        CustomUser,
        on_delete=models.PROTECT,
        verbose_name="Organisateur"
    )
    
    # Statut et validation
    statut = models.CharField(
        max_length=25,
        choices=STATUT_CHOICES,
        default='brouillon',
        verbose_name="Statut"
    )
    
    # Informations complémentaires
    instructions_particulieres = models.TextField(
        blank=True,
        verbose_name="Instructions particulières"
    )
    materiel_requis = models.TextField(
        blank=True,
        verbose_name="Matériel requis"
    )
    
    # Récurrence
    est_recurrent = models.BooleanField(
        default=False,
        verbose_name="Événement récurrent"
    )
    evenement_parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name='occurrences',
        verbose_name="Événement parent"
    )
    
    # Métadonnées
    reference = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        verbose_name="Référence"
    )
    image = models.ImageField(
        upload_to='evenements/images/',
        blank=True,
        null=True,
        verbose_name="Image de l'événement"
    )
    
    objects = EvenementManager()

    class Meta:
        db_table = 'evenements'
        verbose_name = "Événement"
        verbose_name_plural = "Événements"
        ordering = ['-date_debut']
        indexes = [
            models.Index(fields=['date_debut']),
            models.Index(fields=['statut']),
            models.Index(fields=['type_evenement']),
            models.Index(fields=['organisateur']),
        ]

    def __str__(self):
        return f"{self.titre} - {self.date_debut.strftime('%d/%m/%Y')}"

    def clean(self):
        """Validation des règles métier"""
        super().clean()
        
        # CORRECTION : Vérifier que les dates existent avant de les comparer
        if self.date_debut and self.date_fin:
            if self.date_debut >= self.date_fin:
                raise ValidationError({
                    'date_fin': 'La date de fin doit être postérieure à la date de début.'
                })
        
        # Validation des dates d'inscription
        if self.date_debut:
            if (self.date_ouverture_inscriptions and 
                self.date_ouverture_inscriptions >= self.date_debut):
                raise ValidationError({
                    'date_ouverture_inscriptions': 
                    'La date d\'ouverture des inscriptions doit être antérieure à la date de début.'
                })
                
            if (self.date_fermeture_inscriptions and 
                self.date_fermeture_inscriptions >= self.date_debut):
                raise ValidationError({
                    'date_fermeture_inscriptions': 
                    'La date de fermeture des inscriptions doit être antérieure à la date de début.'
                })
        
        if (self.date_ouverture_inscriptions and self.date_fermeture_inscriptions and
            self.date_ouverture_inscriptions >= self.date_fermeture_inscriptions):
            raise ValidationError({
                'date_fermeture_inscriptions': 
                'La date de fermeture doit être postérieure à la date d\'ouverture.'
            })
        
        # Validation des tarifs
        if self.est_payant:
            if (not self.tarif_membre and not self.tarif_salarie and not self.tarif_invite):
                raise ValidationError(
                    'Au moins un tarif doit être défini pour un événement payant.'
                )
        
        # Validation des accompagnants
        if self.permet_accompagnants:
            if not self.nombre_max_accompagnants:
                raise ValidationError({
                    'nombre_max_accompagnants': 
                    'Le nombre maximum d\'accompagnants doit être défini.'
                })
            
            # Vérifier la cohérence avec le type d'événement
            if (self.type_evenement and 
                hasattr(self.type_evenement, 'permet_accompagnants') and
                not self.type_evenement.permet_accompagnants):
                raise ValidationError(
                    'Ce type d\'événement n\'autorise pas les accompagnants.'
                )

    def save(self, *args, **kwargs):
        # Génération de la référence unique
        if not self.reference:
            self.reference = self._generer_reference()
        
        # Validation
        self.full_clean()
        
        # Mise à jour des permissions accompagnants selon le type
        if self.type_evenement and not self.type_evenement.permet_accompagnants:
            self.permet_accompagnants = False
            self.nombre_max_accompagnants = 0
        
        super().save(*args, **kwargs)

    def _generer_reference(self):
        """Génère une référence unique pour l'événement"""
        prefix = f"EVT{self.date_debut.year}"
        # Utiliser les 8 premiers caractères d'un UUID
        suffix = str(uuid.uuid4()).upper()[:8]
        return f"{prefix}-{suffix}"

    @property
    def duree_heures(self):
        """Calcule la durée de l'événement en heures"""
        if self.date_fin:
            delta = self.date_fin - self.date_debut
            return delta.total_seconds() / 3600
        return None

    @property
    def est_termine(self):
        """Vérifie si l'événement est terminé"""
        date_reference = self.date_fin if self.date_fin else self.date_debut
        return date_reference < timezone.now()

    # CONSTANTE POUR LA COHÉRENCE
    STATUTS_OCCUPENT_PLACE = ['confirmee', 'presente']
    
    @property  
    def places_disponibles(self):
        """
        Nombre de places disponibles
        Seules les inscriptions confirmées/présentes comptent définitivement
        """
        if not self.capacite_max:
            return float('inf')
        
        total_participants = 0
        inscriptions_definitives = self.inscriptions.filter(
            statut__in=self.STATUTS_OCCUPENT_PLACE
        )
        
        for inscription in inscriptions_definitives:
            # Le membre principal + ses accompagnants
            total_participants += 1 + inscription.nombre_accompagnants
        
        return max(0, self.capacite_max - total_participants)

    @property
    def est_complet(self):
        """
        Vérifie si l'événement est complet
        COHÉRENCE : Même logique que places_disponibles
        """
        return self.places_disponibles <= 0

    @property
    def taux_occupation(self):
        """Calcule le taux d'occupation de l'événement"""
        if self.capacite_max == 0:
            return 0
        inscriptions_confirmees = self.inscriptions.filter(
            statut__in=['confirmee', 'presente']
        ).count()
        return (inscriptions_confirmees / self.capacite_max) * 100

    @property
    def places_en_attente(self):
        """
        NOUVELLE PROPRIÉTÉ : Places temporairement réservées (en_attente)
        Utile pour l'interface utilisateur
        """
        total_en_attente = 0
        inscriptions_en_attente = self.inscriptions.filter(statut='en_attente')
        
        for inscription in inscriptions_en_attente:
            total_en_attente += 1 + inscription.nombre_accompagnants
        
        return total_en_attente
    
    def peut_s_inscrire(self, membre):
        """Vérifie si un membre peut s'inscrire à l'événement"""
        # Vérifications de base
        if not self.inscriptions_ouvertes:
            return False, "Les inscriptions sont fermées"
        
        if self.statut != 'publie':
            return False, "L'événement n'est pas encore publié"
        
        if self.est_termine:
            return False, "L'événement est terminé"
        
        # Vérification si déjà inscrit
        if self.inscriptions.filter(
            membre=membre, 
            statut__in=['en_attente', 'confirmee', 'liste_attente']
        ).exists():
            return False, "Vous êtes déjà inscrit à cet événement"
        
        # CORRECTION : Vérification cohérente de la capacité
        if self.est_complet:
            return False, "L'événement est complet"
        
        # Vérification des dates d'inscription
        now = timezone.now()
        if self.date_ouverture_inscriptions and now < self.date_ouverture_inscriptions:
            return False, "Les inscriptions ne sont pas encore ouvertes"
        
        if self.date_fermeture_inscriptions and now > self.date_fermeture_inscriptions:
            return False, "Les inscriptions sont fermées"
        
        return True, "Inscription possible"

    def calculer_tarif_membre(self, membre):
        """Calcule le tarif applicable pour un membre selon son type"""
        if not self.est_payant:
            return Decimal('0.00')
        
        # Récupérer les types de membre actifs avec leurs priorités tarifaires
        try:
            types_membre_actifs = membre.get_types_actifs()
        except:
            # Si erreur, retourner tarif membre standard
            return self.tarif_membre
        
        if not types_membre_actifs.exists():
            # Membre sans type spécifique = tarif standard membre
            return self.tarif_membre
        
        # CORRECTION : Priorité 1: Salarié (tarif spécifique)
        if types_membre_actifs.filter(libelle__icontains='Salarié').exists():
            return self.tarif_salarie
        
        # Priorité 2: Étudiant
        if types_membre_actifs.filter(libelle__icontains='Étudiant').exists():
            return self.tarif_membre
        
        # Priorité 3: Membre honoraire (gratuit)
        if types_membre_actifs.filter(libelle__icontains='honoraire').exists():
            return Decimal('0.00')
        
        # Priorité 4: Membre bienfaiteur (réduction)
        if types_membre_actifs.filter(libelle__icontains='bienfaiteur').exists():
            return self.tarif_membre * Decimal('0.9')
        
        # Sinon tarif membre standard
        return self.tarif_membre
    
    def _get_tarif_specifique_type_membre(self, types_membre_actifs):
        """Récupère un tarif spécifique selon le type d'événement et de membre"""
        # Logique pour des tarifs spécifiques par combinaison type_evenement/type_membre
        # Par exemple: Formation + Étudiant = tarif spécial
        
        if self.type_evenement.libelle.lower() in ['formation', 'séminaire']:
            if types_membre_actifs.filter(libelle__icontains='étudiant').exists():
                return self.tarif_membre * Decimal('0.5')  # 50% réduction formations pour étudiants
        
        if self.type_evenement.libelle.lower() in ['assemblée générale']:
            # AG généralement gratuite pour tous les membres
            return Decimal('0.00')
        
        return None

    def verifier_eligibilite_membre(self, membre):
        """Vérifie l'éligibilité d'un membre pour cet événement"""
        # Vérification de base déjà dans peut_s_inscrire
        peut_inscrire, message = self.peut_s_inscrire(membre)
        if not peut_inscrire:
            return False, message
        
        # Vérifications spécifiques selon le type de membre
        types_membre_actifs = membre.get_types_actifs()
        
        # Règles d'éligibilité par type d'événement
        restrictions = self.type_evenement.comportements_specifiques.get('restrictions_membres', {})
        
        if restrictions:
            # Vérifier les types requis
            types_requis = restrictions.get('types_requis', [])
            if types_requis:
                types_membre_noms = [t.libelle.lower() for t in types_membre_actifs]
                if not any(tr.lower() in types_membre_noms for tr in types_requis):
                    return False, f"Cet événement est réservé aux membres : {', '.join(types_requis)}"
            
            # Vérifier les types exclus
            types_exclus = restrictions.get('types_exclus', [])
            if types_exclus:
                types_membre_noms = [t.libelle.lower() for t in types_membre_actifs]
                if any(te.lower() in types_membre_noms for te in types_exclus):
                    return False, f"Cet événement n'est pas accessible aux membres : {', '.join(types_exclus)}"
        
        # Vérifications selon l'ancienneté
        anciennete_requise = self.type_evenement.comportements_specifiques.get('anciennete_minimale')
        if anciennete_requise:
            anciennete_membre = (timezone.now().date() - membre.date_adhesion).days
            if anciennete_membre < anciennete_requise:
                return False, f"Ancienneté minimale requise : {anciennete_requise} jours"
        
        return True, "Éligible"

    def promouvoir_liste_attente(self):
        """Promeut les inscrits de la liste d'attente si des places se libèrent"""
        places_libres = self.places_disponibles
        if places_libres > 0:
            inscriptions_attente = self.inscriptions.filter(
                statut='liste_attente'
            ).order_by('date_inscription')[:places_libres]
            
            for inscription in inscriptions_attente:
                inscription.statut = 'en_attente'
                inscription.date_limite_confirmation = timezone.now() + timezone.timedelta(hours=self.delai_confirmation)
                inscription.save(update_fields=['statut', 'date_limite_confirmation'])
                
            # AJOUTER : Retourner le nombre d'inscriptions promues pour feedback
            return len(inscriptions_attente)
        return 0


class EvenementRecurrence(BaseModel):
    """
    Configuration de récurrence pour les événements récurrents
    """
    FREQUENCE_CHOICES = [
        ('hebdomadaire', 'Hebdomadaire'),
        ('mensuelle', 'Mensuelle'),
        ('annuelle', 'Annuelle'),
    ]
    
    JOURS_SEMAINE_CHOICES = [
        (0, 'Lundi'),
        (1, 'Mardi'),
        (2, 'Mercredi'),
        (3, 'Jeudi'),
        (4, 'Vendredi'),
        (5, 'Samedi'),
        (6, 'Dimanche'),
    ]
    
    evenement_parent = models.OneToOneField(
        Evenement,
        on_delete=models.CASCADE,
        related_name='recurrence',
        verbose_name="Événement parent"
    )
    frequence = models.CharField(
        max_length=15,
        choices=FREQUENCE_CHOICES,
        verbose_name="Fréquence"
    )
    intervalle_recurrence = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        help_text="Intervalle entre les occurrences (ex: tous les 2 semaines)",
        verbose_name="Intervalle de récurrence"
    )
    jours_semaine = models.JSONField(
        default=list,
        blank=True,
        help_text="Jours de la semaine pour récurrence hebdomadaire (0=lundi, 6=dimanche)",
        verbose_name="Jours de la semaine"
    )
    date_fin_recurrence = models.DateField(
        blank=True,
        null=True,
        verbose_name="Date de fin de récurrence"
    )
    nombre_occurrences_max = models.PositiveIntegerField(
        blank=True,
        null=True,
        validators=[MinValueValidator(1)],
        verbose_name="Nombre maximum d'occurrences"
    )

    class Meta:
        db_table = 'evenements_recurrence'
        verbose_name = "Récurrence d'événement"
        verbose_name_plural = "Récurrences d'événements"

    def __str__(self):
        return f"Récurrence {self.frequence} - {self.evenement_parent.titre}"

    def clean(self):
        """Validation des règles métier de la récurrence"""
        super().clean()
        
        # CORRECTION : Ajouter la validation des contraintes de fin AVANT le try-except
        # Une récurrence doit avoir soit une date de fin soit un nombre maximum d'occurrences
        if not self.date_fin_recurrence and not self.nombre_occurrences_max:
            raise ValidationError(
                "Une récurrence doit avoir soit une date de fin soit un nombre maximum d'occurrences."
            )
        
        # CORRECTION : Vérifier que les relations existent avant de les utiliser
        try:
            if self.evenement_parent:
                # Vérifier la cohérence des dates
                if (self.date_fin_recurrence and 
                    hasattr(self.evenement_parent, 'date_debut') and 
                    self.evenement_parent.date_debut and
                    self.date_fin_recurrence <= self.evenement_parent.date_debut.date()):
                    raise ValidationError(
                        "La date de fin de récurrence doit être postérieure à la date de début de l'événement."
                    )
                
                # Validation de la fréquence
                if self.frequence == 'hebdomadaire' and not self.jours_semaine:
                    raise ValidationError("Les jours de la semaine sont obligatoires pour une récurrence hebdomadaire.")
                
                # Validation de l'intervalle
                if self.intervalle_recurrence < 1:
                    raise ValidationError("L'intervalle de récurrence doit être d'au moins 1.")
                
                # Validation du nombre d'occurrences
                if (self.nombre_occurrences_max and 
                    self.nombre_occurrences_max < 1):
                    raise ValidationError("Le nombre maximum d'occurrences doit être d'au moins 1.")
                
        except (AttributeError, EvenementRecurrence.DoesNotExist):
            # Les relations ne sont pas encore établies, on passe la validation
            pass
        except Exception as e:
            # Capturer les autres erreurs de relation Django
            if "RelatedObjectDoesNotExist" in str(e):
                pass  # Ignorer les erreurs de relation non établie
            else:
                raise


class SessionEvenement(BaseModel):
    """
    Sessions ou sous-événements pour les événements complexes
    """
    evenement_parent = models.ForeignKey(
        Evenement,
        on_delete=models.CASCADE,
        related_name='sessions',
        verbose_name="Événement parent"
    )
    titre_session = models.CharField(
        max_length=255,
        verbose_name="Titre de la session"
    )
    description_session = models.TextField(
        blank=True,
        verbose_name="Description de la session"
    )
    date_debut_session = models.DateTimeField(
        verbose_name="Date et heure de début de session"
    )
    date_fin_session = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Date et heure de fin de session"
    )
    capacite_session = models.PositiveIntegerField(
        blank=True,
        null=True,
        validators=[MinValueValidator(1)],
        help_text="Si vide, utilise la capacité de l'événement parent",
        verbose_name="Capacité de la session"
    )
    ordre_session = models.PositiveIntegerField(
        default=1,
        verbose_name="Ordre de la session"
    )
    est_obligatoire = models.BooleanField(
        default=True,
        verbose_name="Session obligatoire"
    )
    intervenant = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Intervenant"
    )

    objects = SessionEvenementManager()

    class Meta:
        db_table = 'sessions_evenements'
        verbose_name = "Session d'événement"
        verbose_name_plural = "Sessions d'événements"
        ordering = ['ordre_session', 'date_debut_session']
        unique_together = ['evenement_parent', 'ordre_session']

    def __str__(self):
        return f"{self.evenement_parent.titre} - Session {self.ordre_session}: {self.titre_session}"

    def clean(self):
        """Validation du modèle"""
        errors = {}
        
        # Validation des dates
        if self.date_fin_session and self.date_debut_session >= self.date_fin_session:
            errors['date_fin_session'] = "La date de fin doit être postérieure à la date de début"
        
        # Validation que la session est dans les limites de l'événement parent
        if self.date_debut_session < self.evenement_parent.date_debut:
            errors['date_debut_session'] = "La session ne peut pas commencer avant l'événement parent"
        
        if (self.evenement_parent.date_fin and 
            self.date_fin_session and 
            self.date_fin_session > self.evenement_parent.date_fin):
            errors['date_fin_session'] = "La session ne peut pas finir après l'événement parent"
        
        if errors:
            raise ValidationError(errors)


class InscriptionEvenement(BaseModel):
    """
    Inscriptions des membres aux événements
    """
    STATUT_CHOICES = [
        ('en_attente', 'En attente de confirmation'),
        ('confirmee', 'Confirmée'),
        ('liste_attente', 'Liste d\'attente'),
        ('annulee', 'Annulée'),
        ('presente', 'Présent(e)'),
        ('absente', 'Absent(e)'),
        ('expiree', 'Expirée'),
    ]
    
    # Relations principales
    evenement = models.ForeignKey(
        Evenement,
        on_delete=models.CASCADE,
        related_name='inscriptions',
        verbose_name="Événement"
    )
    membre = models.ForeignKey(
        Membre,
        on_delete=models.CASCADE,
        related_name='inscriptions_evenements',
        verbose_name="Membre"
    )
    
    # Dates importantes
    date_inscription = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Date d'inscription"
    )
    date_confirmation = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Date de confirmation"
    )
    date_limite_confirmation = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Date limite de confirmation"
    )
    
    # Statut et informations
    statut = models.CharField(
        max_length=15,
        choices=STATUT_CHOICES,
        default='en_attente',
        verbose_name="Statut"
    )
    commentaire = models.TextField(
        blank=True,
        verbose_name="Commentaire"
    )
    
    # Accompagnants
    nombre_accompagnants = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Nombre d'accompagnants"
    )
    details_accompagnants = models.JSONField(
        default=list,
        blank=True,
        help_text="Détails des accompagnants (nom, prénom, etc.)",
        verbose_name="Détails des accompagnants"
    )
    
    # Paiement
    montant_paye = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Montant payé"
    )
    mode_paiement = models.ForeignKey(
        ModePaiement,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        verbose_name="Mode de paiement"
    )
    reference_paiement = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Référence de paiement"
    )
    
    # Métadonnées
    code_confirmation = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        verbose_name="Code de confirmation"
    )
    adresse_ip = models.GenericIPAddressField(
        blank=True,
        null=True,
        verbose_name="Adresse IP"
    )
    
    # Sessions spécifiques (pour événements multi-sessions)
    sessions_selectionnees = models.ManyToManyField(
        SessionEvenement,
        blank=True,
        verbose_name="Sessions sélectionnées"
    )

    objects = InscriptionEvenementManager()

    class Meta:
        db_table = 'inscriptions_evenements'
        verbose_name = "Inscription à un événement"
        verbose_name_plural = "Inscriptions aux événements"
        ordering = ['-date_inscription']
        unique_together = ['evenement', 'membre']
        indexes = [
            models.Index(fields=['statut']),
            models.Index(fields=['date_inscription']),
            models.Index(fields=['date_limite_confirmation']),
        ]

    def __str__(self):
        return f"{self.membre} - {self.evenement.titre} ({self.get_statut_display()})"

    def clean(self):
        """Validation des règles métier de l'inscription"""
        super().clean()
        
        # CORRECTION : Vérifier que les relations existent avant de les utiliser
        try:
            if self.evenement and self.membre:
                # Vérifier que l'événement accepte les inscriptions
                if not self.evenement.inscriptions_ouvertes:
                    raise ValidationError("Les inscriptions sont fermées pour cet événement.")
                
                # Vérifier que l'événement n'est pas complet (sauf si en liste d'attente)
                if (self.statut not in ['liste_attente'] and 
                    self.evenement.places_disponibles <= 0):
                    raise ValidationError("Cet événement est complet.")
                
                # Validation des accompagnants
                if hasattr(self, 'nombre_accompagnants') and self.nombre_accompagnants:
                    if not self.evenement.permet_accompagnants:
                        raise ValidationError("Cet événement n'autorise pas les accompagnants.")
                    
                    if self.nombre_accompagnants > self.evenement.nombre_max_accompagnants:
                        raise ValidationError(
                            f"Maximum {self.evenement.nombre_max_accompagnants} accompagnants autorisés."
                        )
                
                # Vérifier les doublons d'inscription
                if self.pk is None:  # Nouvelle inscription
                    existing = InscriptionEvenement.objects.filter(
                        evenement=self.evenement,
                        membre=self.membre,
                        statut__in=['en_attente', 'confirmee', 'liste_attente']
                    ).exists()
                    if existing:
                        raise ValidationError("Vous êtes déjà inscrit à cet événement.")
                
        except (AttributeError, InscriptionEvenement.DoesNotExist):
            # Les relations ne sont pas encore établies, on passe la validation
            pass
        except Exception as e:
            # Capturer les autres erreurs de relation Django
            if "RelatedObjectDoesNotExist" in str(e):
                pass  # Ignorer les erreurs de relation non établie
            else:
                raise

    def save(self, *args, **kwargs):
        # Génération du code de confirmation
        if not self.code_confirmation:
            self.code_confirmation = self._generer_code_confirmation()
        
        # Définition de la date limite de confirmation
        if not self.date_limite_confirmation and self.statut == 'en_attente':
            self.date_limite_confirmation = timezone.now() + timezone.timedelta(
                hours=self.evenement.delai_confirmation
            )
        
        super().save(*args, **kwargs)

    def _generer_code_confirmation(self):
        """Génère un code de confirmation unique"""
        return str(uuid.uuid4()).upper()[:12]

    def calculer_montant_total(self):
        """Calcule le montant total à payer (membre + accompagnants)"""
        if not self.evenement.est_payant:
            return Decimal('0.00')
        
        # Tarif du membre
        montant_membre = self.evenement.calculer_tarif_membre(self.membre)
        
        # Tarif des accompagnants (tarif invité)
        montant_accompagnants = self.evenement.tarif_invite * self.nombre_accompagnants
        
        return montant_membre + montant_accompagnants

    @property
    def montant_restant(self):
        """Calcule le montant restant à payer"""
        return max(Decimal('0.00'), self.calculer_montant_total() - self.montant_paye)

    @property
    def est_payee(self):
        """Vérifie si l'inscription est entièrement payée"""
        return self.montant_restant == Decimal('0.00')

    @property
    def est_en_retard_confirmation(self):
        """Vérifie si l'inscription est en retard de confirmation"""
        if self.statut != 'en_attente' or not self.date_limite_confirmation:
            return False
        return timezone.now() > self.date_limite_confirmation

    def confirmer_inscription(self):
        """Confirme l'inscription"""
        if self.statut == 'en_attente':
            self.statut = 'confirmee'
            self.date_confirmation = timezone.now()
            self.save()
            return True
        return False

    def annuler_inscription(self, raison=""):
        """Annule l'inscription"""
        if self.statut in ['en_attente', 'confirmee']:
            self.statut = 'annulee'
            if raison:
                self.commentaire = f"{self.commentaire}\nAnnulation: {raison}".strip()
            self.save()
            
            # Promouvoir depuis la liste d'attente
            self.evenement.promouvoir_liste_attente()
            return True
        return False

    def placer_en_liste_attente(self):
        """Place l'inscription en liste d'attente"""
        if self.statut == 'en_attente':
            self.statut = 'liste_attente'
            self.date_limite_confirmation = None
            self.save()
            return True
        return False


class AccompagnantInvite(BaseModel):
    """
    Accompagnants et invités pour les inscriptions aux événements
    """
    STATUT_CHOICES = [
        ('invite', 'Invité'),
        ('confirme', 'Confirmé'),
        ('refuse', 'Refusé'),
        ('present', 'Présent'),
        ('absent', 'Absent'),
    ]
    
    # Relation avec l'inscription
    inscription = models.ForeignKey(
        InscriptionEvenement,
        on_delete=models.CASCADE,
        related_name='accompagnants',
        verbose_name="Inscription"
    )
    
    # Informations personnelles
    nom = models.CharField(
        max_length=100,
        verbose_name="Nom"
    )
    prenom = models.CharField(
        max_length=100,
        verbose_name="Prénom"
    )
    email = models.EmailField(
        blank=True,
        verbose_name="Email"
    )
    telephone = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="Téléphone"
    )
    
    # Statut et type
    statut = models.CharField(
        max_length=10,
        choices=STATUT_CHOICES,
        default='invite',
        verbose_name="Statut"
    )
    est_accompagnant = models.BooleanField(
        default=True,
        help_text="True pour accompagnant, False pour invité externe",
        verbose_name="Est un accompagnant"
    )
    
    # Dates
    date_invitation = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Date d'invitation"
    )
    date_reponse = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Date de réponse"
    )
    
    # Informations supplémentaires
    commentaire = models.TextField(
        blank=True,
        verbose_name="Commentaire"
    )
    restrictions_alimentaires = models.TextField(
        blank=True,
        verbose_name="Restrictions alimentaires"
    )

    objects = AccompagnantInviteManager()

    class Meta:
        db_table = 'accompagnants_invites'
        verbose_name = "Accompagnant/Invité"
        verbose_name_plural = "Accompagnants/Invités"
        ordering = ['nom', 'prenom']

    def __str__(self):
        type_personne = "Accompagnant" if self.est_accompagnant else "Invité"
        return f"{type_personne}: {self.prenom} {self.nom}"

    @property
    def nom_complet(self):
        """Retourne le nom complet"""
        return f"{self.prenom} {self.nom}"

    def confirmer_presence(self):
        """Confirme la présence"""
        if self.statut == 'invite':
            self.statut = 'confirme'
            self.date_reponse = timezone.now()
            self.save()
            return True
        return False

    def refuser_invitation(self):
        """Refuse l'invitation"""
        if self.statut in ['invite', 'confirme']:
            self.statut = 'refuse'
            self.date_reponse = timezone.now()
            self.save()
            return True
        return False


class ValidationEvenement(BaseModel):
    """
    Validation des événements par les administrateurs
    """
    STATUT_VALIDATION_CHOICES = [
        ('en_attente', 'En attente'),
        ('approuve', 'Approuvé'),
        ('refuse', 'Refusé'),
    ]
    
    # Relations
    evenement = models.OneToOneField(
        Evenement,
        on_delete=models.CASCADE,
        related_name='validation',
        verbose_name="Événement"
    )
    validateur = models.ForeignKey(
        CustomUser,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        verbose_name="Validateur"
    )
    
    # Validation
    statut_validation = models.CharField(
        max_length=15,
        choices=STATUT_VALIDATION_CHOICES,
        default='en_attente',
        verbose_name="Statut de validation"
    )
    date_validation = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Date de validation"
    )
    commentaire_validation = models.TextField(
        blank=True,
        verbose_name="Commentaire de validation"
    )
    
    # Historique des modifications demandées
    modifications_demandees = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Modifications demandées"
    )

    objects = ValidationEvenementManager()

    class Meta:
        db_table = 'validations_evenements'
        verbose_name = "Validation d'événement"
        verbose_name_plural = "Validations d'événements"
        ordering = ['-created_at']

    def __str__(self):
        return f"Validation: {self.evenement.titre} - {self.get_statut_validation_display()}"

    def approuver(self, validateur, commentaire=""):
        """Approuve l'événement"""
        self.statut_validation = 'approuve'
        self.validateur = validateur
        self.date_validation = timezone.now()
        self.commentaire_validation = commentaire
        self.save()
        
        # Mettre à jour le statut de l'événement
        self.evenement.statut = 'publie'
        self.evenement.save(update_fields=['statut'])

    def refuser(self, validateur, commentaire):
        """Refuse l'événement"""
        self.statut_validation = 'refuse'
        self.validateur = validateur
        self.date_validation = timezone.now()
        self.commentaire_validation = commentaire
        self.save()
        
        # Mettre à jour le statut de l'événement
        self.evenement.statut = 'brouillon'
        self.evenement.save(update_fields=['statut'])

    def demander_modifications(self, validateur, modifications):
        """Demande des modifications"""
        from django.utils import timezone
        
        self.validateur = validateur
        self.date_validation = timezone.now()
        
        # Ajouter les modifications demandées
        if not self.modifications_demandees:
            self.modifications_demandees = []
        
        self.modifications_demandees.append({
            'date': timezone.now().isoformat(),
            'validateur': f"{validateur.first_name} {validateur.last_name}",
            'modifications': modifications
        })
        
        self.save()
        
        # L'événement reste en attente de validation
        self.evenement.statut = 'en_attente_validation'
        self.evenement.save(update_fields=['statut'])