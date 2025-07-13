# apps/evenements/forms.py
from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from decimal import Decimal
import json

from .models import (
    Evenement, TypeEvenement, InscriptionEvenement, 
    AccompagnantInvite, ValidationEvenement, EvenementRecurrence,
    SessionEvenement
)
from .validators import (
    validate_date_evenement, validate_capacite_coherente,
    validate_organisateur_membre, validate_dates_inscriptions,
    validate_tarifs_coherents, validate_accompagnants_coherents,
    validate_inscription_possible, validate_sessions_coherentes,
    validate_montant_paiement, validate_periode_recherche,
    validate_donnees_accompagnant
)
from apps.membres.models import Membre, TypeMembre
from apps.cotisations.models import ModePaiement

User = get_user_model()


class EvenementForm(forms.ModelForm):
    """
    Formulaire pour créer et modifier des événements
    """
    
    class Meta:
        model = Evenement
        fields = [
            'titre', 'description', 'type_evenement', 'date_debut', 'date_fin',
            'lieu', 'adresse_complete', 'capacite_max', 'inscriptions_ouvertes',
            'date_ouverture_inscriptions', 'date_fermeture_inscriptions',
            'est_payant', 'tarif_membre', 'tarif_salarie', 'tarif_invite',
            'permet_accompagnants', 'nombre_max_accompagnants', 'delai_confirmation',
            'instructions_particulieres', 'materiel_requis', 'image'
        ]
        
        widgets = {
            'titre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Titre de l\'événement'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Description de l\'événement'
            }),
            'type_evenement': forms.Select(attrs={'class': 'form-control'}),
            'date_debut': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'date_fin': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'lieu': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Lieu de l\'événement'
            }),
            'adresse_complete': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Adresse complète'
            }),
            'capacite_max': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1'
            }),
            'date_ouverture_inscriptions': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'date_fermeture_inscriptions': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'tarif_membre': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0'
            }),
            'tarif_salarie': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0'
            }),
            'tarif_invite': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0'
            }),
            'nombre_max_accompagnants': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'max': '10'
            }),
            'delai_confirmation': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'max': '168'
            }),
            'instructions_particulieres': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
            'materiel_requis': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2
            }),
            'image': forms.FileInput(attrs={
                'class': 'form-control-file'
            }),
            'inscriptions_ouvertes': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'est_payant': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'permet_accompagnants': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
        
        labels = {
            'titre': 'Titre de l\'événement',
            'description': 'Description',
            'type_evenement': 'Type d\'événement',
            'date_debut': 'Date et heure de début',
            'date_fin': 'Date et heure de fin',
            'lieu': 'Lieu',
            'adresse_complete': 'Adresse complète',
            'capacite_max': 'Capacité maximum',
            'inscriptions_ouvertes': 'Inscriptions ouvertes',
            'date_ouverture_inscriptions': 'Ouverture des inscriptions',
            'date_fermeture_inscriptions': 'Fermeture des inscriptions',
            'est_payant': 'Événement payant',
            'tarif_membre': 'Tarif membre (€)',
            'tarif_salarie': 'Tarif salarié (€)',
            'tarif_invite': 'Tarif invité (€)',
            'permet_accompagnants': 'Autorise les accompagnants',
            'nombre_max_accompagnants': 'Nombre max d\'accompagnants',
            'delai_confirmation': 'Délai de confirmation (heures)',
            'instructions_particulieres': 'Instructions particulières',
            'materiel_requis': 'Matériel requis',
            'image': 'Image de l\'événement'
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Limiter les organisateurs aux membres actifs
        if self.user and self.user.is_staff:
            membres_organisateurs = User.objects.filter(
                membre__deleted_at__isnull=True
            ).distinct()
            self.fields['organisateur'] = forms.ModelChoiceField(
                queryset=membres_organisateurs,
                widget=forms.Select(attrs={'class': 'form-control'}),
                empty_label="Sélectionner un organisateur"
            )
        
        # Configuration des champs selon le type d'événement
        if 'type_evenement' in self.data:
            try:
                type_evenement_id = int(self.data.get('type_evenement'))
                type_evenement = TypeEvenement.objects.get(id=type_evenement_id)
                if not type_evenement.permet_accompagnants:
                    self.fields['permet_accompagnants'].widget.attrs['disabled'] = True
                    self.fields['nombre_max_accompagnants'].widget.attrs['disabled'] = True
            except (ValueError, TypeEvenement.DoesNotExist):
                pass

    def clean_date_debut(self):
        date_debut = self.cleaned_data.get('date_debut')
        if date_debut and date_debut <= timezone.now():
            raise ValidationError("La date de début doit être dans le futur.")
        return date_debut

    def clean_capacite_max(self):
        capacite = self.cleaned_data.get('capacite_max')
        evenement_id = self.instance.id if self.instance.pk else None
        validate_capacite_coherente(capacite, evenement_id)
        return capacite

    def clean_organisateur(self):
        organisateur = self.cleaned_data.get('organisateur') or self.user
        if organisateur:
            # Vérifier que l'organisateur est un membre actif
            try:
                membre = organisateur.membre
                if membre.deleted_at is not None:
                    raise ValidationError("L'organisateur doit être un membre actif.")
            except:
                raise ValidationError("L'organisateur doit être un membre de l'association.")
        return organisateur

    def clean(self):
        cleaned_data = super().clean()
        
        # Validation des dates
        date_debut = cleaned_data.get('date_debut')
        date_fin = cleaned_data.get('date_fin')
        date_ouverture = cleaned_data.get('date_ouverture_inscriptions')
        date_fermeture = cleaned_data.get('date_fermeture_inscriptions')
        
        if date_debut and date_fin and date_debut >= date_fin:
            raise ValidationError({
                'date_fin': 'La date de fin doit être postérieure à la date de début.'
            })
        
        if date_debut and (date_ouverture or date_fermeture):
            try:
                validate_dates_inscriptions(date_ouverture, date_fermeture, date_debut)
            except ValidationError as e:
                raise e
        
        # Validation des tarifs
        est_payant = cleaned_data.get('est_payant')
        tarif_membre = cleaned_data.get('tarif_membre', Decimal('0'))
        tarif_salarie = cleaned_data.get('tarif_salarie', Decimal('0'))
        tarif_invite = cleaned_data.get('tarif_invite', Decimal('0'))
        
        try:
            validate_tarifs_coherents(est_payant, tarif_membre, tarif_salarie, tarif_invite)
        except ValidationError as e:
            raise e
        
        # Validation des accompagnants - CORRECTION
        permet_accompagnants = cleaned_data.get('permet_accompagnants')
        nombre_max_accompagnants = cleaned_data.get('nombre_max_accompagnants', 0)
        type_evenement = cleaned_data.get('type_evenement')
        
        # CORRECTION : Vérifier la cohérence avec le type d'événement
        if type_evenement and permet_accompagnants and not type_evenement.permet_accompagnants:
            raise ValidationError({
                '__all__': "Ce type d'événement n'autorise pas les accompagnants."
            })
        
        try:
            validate_accompagnants_coherents(
                permet_accompagnants, nombre_max_accompagnants, type_evenement
            )
        except ValidationError as e:
            raise e
        
        return cleaned_data

    def save(self, commit=True):
        evenement = super().save(commit=False)
        
        # Définir l'organisateur - CORRECTION
        if not evenement.organisateur_id:  # Utiliser organisateur_id au lieu de organisateur
            evenement.organisateur = self.user
        
        # Statut selon le type d'événement
        if evenement.type_evenement and evenement.type_evenement.necessite_validation:
            evenement.statut = 'en_attente_validation'
        else:
            evenement.statut = 'publie'
        
        if commit:
            evenement.save()
            
            # Créer la validation si nécessaire
            if evenement.type_evenement and evenement.type_evenement.necessite_validation:
                ValidationEvenement.objects.get_or_create(
                    evenement=evenement,
                    defaults={'statut_validation': 'en_attente'}
                )
        
        return evenement


class InscriptionEvenementForm(forms.ModelForm):
    """
    Formulaire pour s'inscrire à un événement
    """
    
    # Champs pour les accompagnants
    accompagnants_data = forms.CharField(
        widget=forms.HiddenInput(),
        required=False,
        help_text="Données JSON des accompagnants"
    )
    
    accepter_conditions = forms.BooleanField(
        required=True,
        label="J'accepte les conditions de participation",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    class Meta:
        model = InscriptionEvenement
        fields = [
            'commentaire', 'nombre_accompagnants',
            'mode_paiement', 'reference_paiement'
        ]
        
        widgets = {
            'commentaire': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Commentaire ou demandes particulières'
            }),
            'nombre_accompagnants': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0'
            }),
            'mode_paiement': forms.Select(attrs={'class': 'form-control'}),
            'reference_paiement': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Référence de paiement'
            })
        }
        
        labels = {
            'commentaire': 'Commentaire',
            'nombre_accompagnants': 'Nombre d\'accompagnants',
            'mode_paiement': 'Mode de paiement',
            'reference_paiement': 'Référence de paiement'
        }

    def __init__(self, *args, **kwargs):
        self.evenement = kwargs.pop('evenement', None)
        self.membre = kwargs.pop('membre', None)
        super().__init__(*args, **kwargs)
        
        # Configuration selon l'événement
        if self.evenement:
            # Limiter les accompagnants
            if not self.evenement.permet_accompagnants:
                self.fields['nombre_accompagnants'].widget.attrs['disabled'] = True
                self.fields['nombre_accompagnants'].initial = 0
            else:
                self.fields['nombre_accompagnants'].widget.attrs['max'] = \
                    self.evenement.nombre_max_accompagnants
            
            # Mode de paiement si payant
            if self.evenement.est_payant:
                self.fields['mode_paiement'].required = True
            else:
                del self.fields['mode_paiement']
                del self.fields['reference_paiement']

    def clean_nombre_accompagnants(self):
        nombre = self.cleaned_data.get('nombre_accompagnants', 0)
        
        if self.evenement and nombre > 0:
            if not self.evenement.permet_accompagnants:
                raise ValidationError("Cet événement n'autorise pas les accompagnants.")
            
            if nombre > self.evenement.nombre_max_accompagnants:
                raise ValidationError(
                    f"Maximum {self.evenement.nombre_max_accompagnants} accompagnants autorisés."
                )
        
        return nombre

    def clean_accompagnants_data(self):
        data = self.cleaned_data.get('accompagnants_data', '[]')
        try:
            accompagnants = json.loads(data)
            nombre_accompagnants = self.cleaned_data.get('nombre_accompagnants', 0)
            
            if len(accompagnants) != nombre_accompagnants:
                raise ValidationError("Le nombre d'accompagnants ne correspond pas aux données.")
            
            # Valider chaque accompagnant
            for accompagnant in accompagnants:
                validate_donnees_accompagnant(
                    accompagnant.get('nom'),
                    accompagnant.get('prenom'),
                    accompagnant.get('email')
                )
            
            return accompagnants
        except json.JSONDecodeError:
            raise ValidationError("Données d'accompagnants invalides.")

    def clean(self):
        cleaned_data = super().clean()
        
        # CORRECTION : Vérifier que les objets existent avant de les utiliser
        if hasattr(self, 'evenement') and hasattr(self, 'membre') and self.evenement and self.membre:
            nombre_accompagnants = cleaned_data.get('nombre_accompagnants', 0)
            
            # Validation simple sans utiliser les relations Django
            if nombre_accompagnants > 0 and not self.evenement.permet_accompagnants:
                self.add_error('nombre_accompagnants', "Cet événement n'autorise pas les accompagnants.")
            
            if nombre_accompagnants > self.evenement.nombre_max_accompagnants:
                self.add_error('nombre_accompagnants', 
                    f"Maximum {self.evenement.nombre_max_accompagnants} accompagnants autorisés.")
        
        return cleaned_data

    def save(self, commit=True):
        inscription = super().save(commit=False)
        
        # Associer l'événement et le membre
        inscription.evenement = self.evenement
        inscription.membre = self.membre
        
        # Calculer le montant total
        montant_total = inscription.calculer_montant_total()
        
        # Déterminer le statut initial
        if self.evenement.places_disponibles > 0:
            inscription.statut = 'en_attente'
            inscription.date_limite_confirmation = timezone.now() + timezone.timedelta(
                hours=self.evenement.delai_confirmation
            )
        else:
            inscription.statut = 'liste_attente'
        
        if commit:
            inscription.save()
            
            # Créer les accompagnants
            accompagnants_data = self.cleaned_data.get('accompagnants_data', [])
            for data_accompagnant in accompagnants_data:
                AccompagnantInvite.objects.create(
                    inscription=inscription,
                    nom=data_accompagnant['nom'],
                    prenom=data_accompagnant['prenom'],
                    email=data_accompagnant.get('email', ''),
                    telephone=data_accompagnant.get('telephone', ''),
                    est_accompagnant=True
                )
        
        return inscription


class EvenementSearchForm(forms.Form):
    """
    Formulaire de recherche d'événements
    """
    
    STATUT_CHOICES = [
        ('', 'Tous les statuts'),
        ('publie', 'Publié'),
        ('brouillon', 'Brouillon'),
        ('en_attente_validation', 'En attente de validation'),
        ('annule', 'Annulé'),
        ('termine', 'Terminé'),
    ]
    
    PERIODE_CHOICES = [
        ('', 'Toutes les dates'),
        ('aujourd_hui', 'Aujourd\'hui'),
        ('cette_semaine', 'Cette semaine'),
        ('ce_mois', 'Ce mois'),
        ('prochains_30_jours', 'Prochains 30 jours'),
        ('personnalisee', 'Période personnalisée'),
    ]
    
    recherche = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Rechercher par titre, description, lieu...'
        }),
        label='Recherche'
    )
    
    type_evenement = forms.ModelChoiceField(
        queryset=TypeEvenement.objects.all(),
        required=False,
        empty_label="Tous les types",
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Type d\'événement'
    )
    
    statut = forms.ChoiceField(
        choices=STATUT_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Statut'
    )
    
    periode = forms.ChoiceField(
        choices=PERIODE_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Période'
    )
    
    date_debut = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label='Date de début'
    )
    
    date_fin = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label='Date de fin'
    )
    
    lieu = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Lieu'
        }),
        label='Lieu'
    )
    
    organisateur = forms.ModelChoiceField(
        queryset=User.objects.filter(membre__deleted_at__isnull=True),
        required=False,
        empty_label="Tous les organisateurs",
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Organisateur'
    )
    
    places_disponibles = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='Avec places disponibles uniquement'
    )
    
    inscriptions_ouvertes = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='Inscriptions ouvertes uniquement'
    )
    
    evenements_payants = forms.ChoiceField(
        choices=[
            ('', 'Tous'),
            ('payants', 'Payants'),
            ('gratuits', 'Gratuits')
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Tarification'
    )

    def clean(self):
        cleaned_data = super().clean()
        
        # Validation de la période personnalisée
        periode = cleaned_data.get('periode')
        date_debut = cleaned_data.get('date_debut')
        date_fin = cleaned_data.get('date_fin')
        
        if periode == 'personnalisee':
            if not date_debut or not date_fin:
                raise ValidationError("Les dates de début et fin sont requises pour une période personnalisée.")
            validate_periode_recherche(date_debut, date_fin)
        
        return cleaned_data


class ValidationEvenementForm(forms.ModelForm):
    """
    Formulaire pour valider ou refuser un événement
    """
    
    DECISION_CHOICES = [
        ('approuver', 'Approuver'),
        ('refuser', 'Refuser'),
        ('demander_modifications', 'Demander des modifications'),
    ]
    
    decision = forms.ChoiceField(
        choices=DECISION_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        label='Décision'
    )
    
    class Meta:
        model = ValidationEvenement
        fields = ['commentaire_validation']
        
        widgets = {
            'commentaire_validation': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Commentaire de validation (obligatoire si refus ou modifications)'
            })
        }
        
        labels = {
            'commentaire_validation': 'Commentaire'
        }

    def clean(self):
        cleaned_data = super().clean()
        decision = cleaned_data.get('decision')
        commentaire = cleaned_data.get('commentaire_validation')
        
        if decision in ['refuser', 'demander_modifications'] and not commentaire:
            raise ValidationError({
                'commentaire_validation': 'Un commentaire est obligatoire pour un refus ou une demande de modifications.'
            })
        
        return cleaned_data


class AccompagnantForm(forms.ModelForm):
    """
    Formulaire pour ajouter un accompagnant
    """
    
    class Meta:
        model = AccompagnantInvite
        fields = [
            'nom', 'prenom', 'email', 'telephone',
            'restrictions_alimentaires', 'commentaire'
        ]
        
        widgets = {
            'nom': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nom'
            }),
            'prenom': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Prénom'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Email (optionnel)'
            }),
            'telephone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Téléphone (optionnel)'
            }),
            'restrictions_alimentaires': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Restrictions alimentaires'
            }),
            'commentaire': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Commentaire'
            })
        }

    def clean(self):
        cleaned_data = super().clean()
        nom = cleaned_data.get('nom')
        prenom = cleaned_data.get('prenom')
        email = cleaned_data.get('email')
        
        validate_donnees_accompagnant(nom, prenom, email)
        
        return cleaned_data


class EvenementRecurrenceForm(forms.ModelForm):
    """
    Formulaire pour configurer la récurrence d'un événement
    """
    
    JOURS_SEMAINE_CHOICES = [
        (0, 'Lundi'),
        (1, 'Mardi'),
        (2, 'Mercredi'),
        (3, 'Jeudi'),
        (4, 'Vendredi'),
        (5, 'Samedi'),
        (6, 'Dimanche'),
    ]
    
    jours_semaine_selection = forms.MultipleChoiceField(
        choices=JOURS_SEMAINE_CHOICES,
        widget=forms.CheckboxSelectMultiple(),
        required=False,
        label='Jours de la semaine'
    )
    
    # AJOUTER le champ evenement_parent
    evenement_parent = forms.ModelChoiceField(
        queryset=Evenement.objects.all(),
        required=False,
        widget=forms.HiddenInput()
    )
    
    jours_semaine_selection = forms.MultipleChoiceField(
        choices=JOURS_SEMAINE_CHOICES,
        widget=forms.CheckboxSelectMultiple(),
        required=False,
        label='Jours de la semaine'
    )
    
    class Meta:
        model = EvenementRecurrence
        fields = [
            'frequence', 'intervalle_recurrence',
            'date_fin_recurrence', 'nombre_occurrences_max'
        ]
        
        widgets = {
            'frequence': forms.Select(attrs={'class': 'form-control'}),
            'intervalle_recurrence': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1'
            }),
            'date_fin_recurrence': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'nombre_occurrences_max': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1'
            })
        }

    def clean(self):
        cleaned_data = super().clean()
        frequence = cleaned_data.get('frequence')
        jours_semaine = cleaned_data.get('jours_semaine_selection', [])
        
        if frequence == 'hebdomadaire' and not jours_semaine:
            raise ValidationError({
                'jours_semaine_selection': 'Vous devez sélectionner au moins un jour de la semaine.'
            })
        
        # Convertir les jours sélectionnés en format JSON
        if jours_semaine:
            cleaned_data['jours_semaine'] = [int(jour) for jour in jours_semaine]
        
        return cleaned_data

    def __init__(self, *args, **kwargs):
        self.evenement_parent = kwargs.pop('evenement_parent', None)
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        recurrence = super().save(commit=False)
        
        # Associer l'événement parent si fourni
        if self.evenement_parent:
            recurrence.evenement_parent = self.evenement_parent
        
        # Sauvegarder les jours de la semaine
        jours_semaine = self.cleaned_data.get('jours_semaine', [])
        recurrence.jours_semaine = jours_semaine
        
        if commit:
            recurrence.save()
        
        return recurrence


class SessionEvenementForm(forms.ModelForm):
    """
    Formulaire pour créer/modifier une session d'événement
    """
    
    class Meta:
        model = SessionEvenement
        fields = [
            'titre_session', 'description_session',
            'date_debut_session', 'date_fin_session',
            'capacite_session', 'ordre_session',
            'est_obligatoire', 'intervenant'
        ]
        
        widgets = {
            'titre_session': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Titre de la session'
            }),
            'description_session': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
            'date_debut_session': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'date_fin_session': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'capacite_session': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1'
            }),
            'ordre_session': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1'
            }),
            'est_obligatoire': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'intervenant': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nom de l\'intervenant'
            })
        }

    def __init__(self, *args, **kwargs):
        self.evenement = kwargs.pop('evenement', None)
        super().__init__(*args, **kwargs)
        
        if self.evenement:
            # Limiter la capacité à celle de l'événement parent
            self.fields['capacite_session'].widget.attrs['max'] = self.evenement.capacite_max

    def clean_capacite_session(self):
        capacite = self.cleaned_data.get('capacite_session')
        if capacite and self.evenement and capacite > self.evenement.capacite_max:
            raise ValidationError(
                f"La capacité ne peut pas dépasser celle de l'événement ({self.evenement.capacite_max})."
            )
        return capacite


class PaiementInscriptionForm(forms.Form):
    """
    Formulaire pour enregistrer un paiement d'inscription
    """
    
    montant = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'min': '0.01'
        }),
        label='Montant payé (€)'
    )
    
    mode_paiement = forms.ModelChoiceField(
        queryset=ModePaiement.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Mode de paiement'
    )
    
    reference_paiement = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Référence, numéro de chèque, etc.'
        }),
        label='Référence de paiement'
    )
    
    def __init__(self, *args, **kwargs):
        self.inscription = kwargs.pop('inscription', None)
        super().__init__(*args, **kwargs)
        
        if self.inscription:
            # Montant maximum = montant restant
            montant_restant = self.inscription.montant_restant
            self.fields['montant'].widget.attrs['max'] = str(montant_restant)
            self.fields['montant'].initial = montant_restant

    def clean_montant(self):
        montant = self.cleaned_data.get('montant')
        if self.inscription:
            montant_attendu = self.inscription.montant_restant
            validate_montant_paiement(montant, montant_attendu)
        return montant


class TypeEvenementForm(forms.ModelForm):
    """
    Formulaire pour créer/modifier un type d'événement
    """
    
    class Meta:
        model = TypeEvenement
        fields = [
            'libelle', 'description', 'couleur_affichage',
            'necessite_validation', 'permet_accompagnants',
            'ordre_affichage'
        ]
        
        widgets = {
            'libelle': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nom du type d\'événement'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
            'couleur_affichage': forms.TextInput(attrs={
                'class': 'form-control',
                'type': 'color'
            }),
            'necessite_validation': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'permet_accompagnants': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'ordre_affichage': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0'
            })
        }


class ExportEvenementsForm(forms.Form):
    """
    Formulaire pour exporter les données d'événements
    """
    
    FORMAT_CHOICES = [
        ('csv', 'CSV'),
        ('excel', 'Excel'),
        ('pdf', 'PDF'),
    ]
    
    format_export = forms.ChoiceField(
        choices=FORMAT_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Format d\'export'
    )
    
    inclure_inscriptions = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='Inclure les inscriptions'
    )
    
    inclure_accompagnants = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='Inclure les accompagnants'
    )
    
    date_debut = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label='Date de début'
    )
    
    date_fin = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label='Date de fin'
    )