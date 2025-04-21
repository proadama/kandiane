# apps/cotisations/forms.py
from django import forms
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from decimal import Decimal

from apps.membres.models import Membre, TypeMembre
from apps.core.models import Statut

from .models import (
    Cotisation, Paiement, ModePaiement, BaremeCotisation, 
    Rappel, ConfigurationCotisation
)


class BaremeCotisationForm(forms.ModelForm):
    """
    Formulaire pour créer ou modifier un barème de cotisation.
    """
    class Meta:
        model = BaremeCotisation
        fields = [
            'type_membre', 'montant', 'periodicite', 'date_debut_validite',
            'date_fin_validite', 'description'
        ]
        widgets = {
            'date_debut_validite': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'date_fin_validite': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Ajouter des classes CSS pour le styling
        for field_name, field in self.fields.items():
            if field.widget.__class__.__name__ not in ['CheckboxInput', 'RadioSelect']:
                field.widget.attrs.update({'class': 'form-control'})
        
        # Définir la date par défaut
        if not self.instance.pk and not self.initial.get('date_debut_validite'):
            self.initial['date_debut_validite'] = timezone.now().date()
    
    def clean(self):
        cleaned_data = super().clean()
        date_debut = cleaned_data.get('date_debut_validite')
        date_fin = cleaned_data.get('date_fin_validite')
        
        # Vérifier que la date de fin est postérieure à la date de début
        if date_fin and date_debut and date_fin <= date_debut:
            self.add_error('date_fin_validite', 
                _("La date de fin doit être postérieure à la date de début."))
        
        return cleaned_data


class CotisationForm(forms.ModelForm):
    """
    Formulaire pour créer ou modifier une cotisation.
    """
    generer_reference = forms.BooleanField(
        required=False,
        initial=True,
        label=_("Générer une référence automatiquement"),
        help_text=_("Décochez pour spécifier manuellement une référence.")
    )
    
    utiliser_bareme = forms.BooleanField(
        required=False,
        initial=True,
        label=_("Utiliser un barème pour calculer le montant"),
        help_text=_("Le montant sera calculé en fonction du barème sélectionné.")
    )
    
    class Meta:
        model = Cotisation
        fields = [
            'membre', 'type_membre', 'bareme', 'montant', 'reference',
            'date_emission', 'date_echeance', 'periode_debut', 'periode_fin',
            'statut', 'commentaire'
        ]
        widgets = {
            'date_emission': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'date_echeance': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'periode_debut': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'periode_fin': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'commentaire': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Ajouter des classes CSS pour le styling
        for field_name, field in self.fields.items():
            if field.widget.__class__.__name__ not in ['CheckboxInput', 'RadioSelect']:
                field.widget.attrs.update({'class': 'form-control'})
        
        # Définir les dates par défaut pour un nouveau formulaire
        if not self.instance.pk:
            today = timezone.now().date()
            default_echeance = today + timezone.timedelta(days=30)
            
            self.initial.update({
                'date_emission': today,
                'date_echeance': default_echeance,
                'periode_debut': today,
                'periode_fin': today.replace(year=today.year + 1) - timezone.timedelta(days=1),
            })
            
            # Masquer le champ référence si génération automatique
            self.fields['reference'].widget = forms.HiddenInput()
        else:
            # Pour une modification, on ne peut pas changer certains champs
            self.fields['membre'].disabled = True
            self.fields['type_membre'].disabled = True
            self.fields['bareme'].disabled = True
            self.fields['montant'].disabled = True
            self.fields['reference'].disabled = True
            
            # Cacher les champs spécifiques à la création
            self.fields['generer_reference'].widget = forms.HiddenInput()
            self.fields['utiliser_bareme'].widget = forms.HiddenInput()
        
        # Filtrer les barèmes en fonction du type de membre sélectionné
        # (Note: ceci sera complété par JavaScript côté client)
        if 'type_membre' in self.data:
            try:
                type_id = int(self.data.get('type_membre'))
                self.fields['bareme'].queryset = BaremeCotisation.objects.filter(
                    type_membre_id=type_id
                ).order_by('-date_debut_validite')
            except (ValueError, TypeError):
                pass
    
    def clean(self):
        cleaned_data = super().clean()
        date_emission = cleaned_data.get('date_emission')
        date_echeance = cleaned_data.get('date_echeance')
        periode_debut = cleaned_data.get('periode_debut')
        periode_fin = cleaned_data.get('periode_fin')
        
        # Vérifications des dates
        if date_echeance and date_emission and date_echeance < date_emission:
            self.add_error('date_echeance',
                _("La date d'échéance doit être postérieure à la date d'émission."))
        
        if periode_fin and periode_debut and periode_fin < periode_debut:
            self.add_error('periode_fin',
                _("La fin de période doit être postérieure au début de période."))
        
        # Vérifier le montant
        montant = cleaned_data.get('montant')
        if montant is not None and montant <= 0:
            self.add_error('montant', _("Le montant doit être supérieur à zéro."))
        
        # Pour un nouvel enregistrement
        if not self.instance.pk:
            # Vérifier si la référence doit être générée ou est requise
            generer_reference = cleaned_data.get('generer_reference')
            reference = cleaned_data.get('reference')
            
            if not generer_reference and not reference:
                self.add_error('reference', 
                    _("Une référence est requise si la génération automatique est désactivée."))
        
        return cleaned_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Si c'est une nouvelle cotisation
        if not self.instance.pk:
            # Récupérer l'année et le mois
            if instance.periode_debut:
                instance.annee = instance.periode_debut.year
                instance.mois = instance.periode_debut.month
            
            # Initialiser le montant restant
            instance.montant_restant = instance.montant
            
            # Enregistrer l'utilisateur qui crée la cotisation
            if self.user:
                instance.cree_par = self.user
            
            # Générer une référence si demandé
            if self.cleaned_data.get('generer_reference'):
                # La référence sera générée dans la méthode save() du modèle
                instance.reference = ''
        else:
            # Pour une modification, enregistrer l'utilisateur qui modifie
            if self.user:
                instance.modifie_par = self.user
        
        if commit:
            instance.save()
        
        return instance


class PaiementForm(forms.ModelForm):
    """
    Formulaire pour créer ou modifier un paiement.
    """
    class Meta:
        model = Paiement
        fields = [
            'montant', 'mode_paiement', 'reference_paiement',
            'date_paiement', 'type_transaction', 'commentaire'
        ]
        widgets = {
            'date_paiement': forms.DateTimeInput(
                attrs={'type': 'datetime-local', 'class': 'form-control'}
            ),
            'commentaire': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.cotisation = kwargs.pop('cotisation', None)
        super().__init__(*args, **kwargs)
        
        # Ajouter des classes CSS pour le styling
        for field_name, field in self.fields.items():
            if field.widget.__class__.__name__ not in ['CheckboxInput', 'RadioSelect']:
                field.widget.attrs.update({'class': 'form-control'})
        
        # Définir les valeurs par défaut
        if not self.instance.pk:
            self.initial.update({
                'date_paiement': timezone.now(),
                'type_transaction': 'paiement',
            })
            
            # Si la cotisation est fournie, suggérer le montant restant
            if self.cotisation:
                self.initial['montant'] = self.cotisation.montant_restant
        else:
            # Pour une modification, on ne peut pas changer certains champs
            if self.instance.cotisation.est_complete:
                self.fields['montant'].disabled = True
    
    def clean_montant(self):
        montant = self.cleaned_data.get('montant')
        if montant <= 0:
            raise ValidationError(_("Le montant doit être supérieur à zéro."))
        
        # Si c'est un nouveau paiement et qu'on a une cotisation
        if not self.instance.pk and self.cotisation:
            # Pour les paiements (pas les remboursements), vérifier que le montant 
            # n'est pas supérieur au montant restant
            type_transaction = self.data.get('type_transaction')
            if type_transaction == 'paiement' and montant > self.cotisation.montant_restant:
                raise ValidationError(
                    _("Le montant du paiement ne peut pas dépasser le montant restant à payer (%(restant)s €).") % 
                    {'restant': self.cotisation.montant_restant}
                )
        
        return montant
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Associer à la cotisation si fournie
        if not self.instance.pk and self.cotisation:
            instance.cotisation = self.cotisation
        
        # Enregistrer l'utilisateur qui crée/modifie le paiement
        if self.user and hasattr(self.user, 'is_authenticated') and self.user.is_authenticated:
            if not self.instance.pk:
                # Nouvel objet - utilisateur créateur
                instance.cree_par = self.user
            else:
                # Mise à jour - utilisateur modificateur
                instance.modifie_par = self.user
        
        if commit:
            instance.save()
        
        return instance


class RappelForm(forms.ModelForm):
    """
    Formulaire pour créer ou modifier un rappel.
    """
    class Meta:
        model = Rappel
        fields = [
            'type_rappel', 'contenu', 'niveau'
        ]
        widgets = {
            'contenu': forms.Textarea(attrs={'rows': 5, 'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.cotisation = kwargs.pop('cotisation', None)
        self.membre = kwargs.pop('membre', None)
        super().__init__(*args, **kwargs)
        
        # Ajouter des classes CSS pour le styling
        for field_name, field in self.fields.items():
            if field.widget.__class__.__name__ not in ['CheckboxInput', 'RadioSelect']:
                field.widget.attrs.update({'class': 'form-control'})
        
        # Déterminer le niveau du rappel en fonction des rappels existants
        if self.cotisation and not self.instance.pk:
            dernier_niveau = Rappel.objects.filter(
                cotisation=self.cotisation
            ).order_by('-niveau').values_list('niveau', flat=True).first() or 0
            
            self.initial['niveau'] = dernier_niveau + 1
        
        # Préparer un contenu par défaut
        if not self.instance.pk and self.cotisation and self.cotisation.membre:
            membre = self.cotisation.membre
            montant = self.cotisation.montant_restant
            date_echeance = self.cotisation.date_echeance
            
            self.initial['contenu'] = _(
                "Cher/Chère %(prenom)s %(nom)s,\n\n"
                "Nous vous rappelons que votre cotisation (réf. %(reference)s) "
                "d'un montant restant dû de %(montant)s € "
                "est arrivée à échéance le %(date)s.\n\n"
                "Nous vous remercions de bien vouloir procéder au règlement "
                "dans les meilleurs délais.\n\n"
                "Cordialement,\n"
                "L'équipe de l'association"
            ) % {
                'prenom': membre.prenom,
                'nom': membre.nom,
                'reference': self.cotisation.reference,
                'montant': montant,
                'date': date_echeance.strftime('%d/%m/%Y')
            }
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Associer à la cotisation et au membre si fournis
        if not self.instance.pk:
            if self.cotisation:
                instance.cotisation = self.cotisation
            if self.membre or (self.cotisation and self.cotisation.membre):
                instance.membre = self.membre or self.cotisation.membre
            
            # Initialiser le statut à 'planifié'
            instance.etat = 'planifie'
            
            # Enregistrer l'utilisateur qui crée le rappel
            if self.user and hasattr(self.user, 'is_authenticated') and self.user.is_authenticated:
                instance.cree_par = self.user
        
        if commit:
            instance.save()
        
        return instance


class CotisationSearchForm(forms.Form):
    """
    Formulaire de recherche avancée pour les cotisations.
    """
    membre = forms.ModelChoiceField(
        queryset=Membre.objects.all(),
        required=False,
        empty_label=_("Tous les membres"),
        label=_("Membre")
    )
    
    type_membre = forms.ModelChoiceField(
        queryset=TypeMembre.objects.all(),
        required=False,
        empty_label=_("Tous les types"),
        label=_("Type de membre")
    )
    
    statut_paiement = forms.ChoiceField(
        choices=[
            ('', _("Tous les statuts")),
            ('non_payee', _("Non payée")),
            ('partiellement_payee', _("Partiellement payée")),
            ('payee', _("Payée"))
        ],
        required=False,
        label=_("Statut de paiement")
    )
    
    date_emission_debut = forms.DateField(
        required=False,
        label=_("Date d'émission (début)"),
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    
    date_emission_fin = forms.DateField(
        required=False,
        label=_("Date d'émission (fin)"),
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    
    date_echeance_debut = forms.DateField(
        required=False,
        label=_("Date d'échéance (début)"),
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    
    date_echeance_fin = forms.DateField(
        required=False,
        label=_("Date d'échéance (fin)"),
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    
    montant_min = forms.DecimalField(
        required=False,
        min_value=0,
        label=_("Montant minimum"),
        help_text=_("En euros")
    )
    
    montant_max = forms.DecimalField(
        required=False,
        min_value=0,
        label=_("Montant maximum"),
        help_text=_("En euros")
    )
    
    annee = forms.IntegerField(
        required=False,
        label=_("Année"),
        min_value=2000,
        max_value=2099
    )
    
    mois = forms.ChoiceField(
        choices=[
            ('', _("Tous les mois")),
            ('1', _("Janvier")),
            ('2', _("Février")),
            ('3', _("Mars")),
            ('4', _("Avril")),
            ('5', _("Mai")),
            ('6', _("Juin")),
            ('7', _("Juillet")),
            ('8', _("Août")),
            ('9', _("Septembre")),
            ('10', _("Octobre")),
            ('11', _("Novembre")),
            ('12', _("Décembre"))
        ],
        required=False,
        label=_("Mois")
    )
    
    reference = forms.CharField(
        required=False,
        label=_("Référence"),
        max_length=50
    )
    
    en_retard = forms.BooleanField(
        required=False,
        label=_("Seulement les cotisations en retard"),
        initial=False
    )
    
    terme = forms.CharField(
        required=False,
        label=_("Recherche"),
        max_length=100,
        widget=forms.TextInput(attrs={
            'placeholder': _("Référence, nom du membre, commentaire...")
        })
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Ajouter des classes CSS pour le styling
        for field_name, field in self.fields.items():
            if field.widget.__class__.__name__ not in ['CheckboxInput']:
                field.widget.attrs.update({'class': 'form-control'})
            else:
                field.widget.attrs.update({'class': 'form-check-input'})
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Vérifier la cohérence des dates d'émission
        date_emission_debut = cleaned_data.get('date_emission_debut')
        date_emission_fin = cleaned_data.get('date_emission_fin')
        
        if date_emission_debut and date_emission_fin and date_emission_debut > date_emission_fin:
            self.add_error('date_emission_fin', 
                _("La date de fin doit être postérieure à la date de début."))
        
        # Vérifier la cohérence des dates d'échéance
        date_echeance_debut = cleaned_data.get('date_echeance_debut')
        date_echeance_fin = cleaned_data.get('date_echeance_fin')
        
        if date_echeance_debut and date_echeance_fin and date_echeance_debut > date_echeance_fin:
            self.add_error('date_echeance_fin', 
                _("La date de fin doit être postérieure à la date de début."))
        
        # Vérifier la cohérence des montants
        montant_min = cleaned_data.get('montant_min')
        montant_max = cleaned_data.get('montant_max')
        
        if montant_min is not None and montant_max is not None and montant_min > montant_max:
            self.add_error('montant_max', 
                _("Le montant maximum doit être supérieur au montant minimum."))
        
        return cleaned_data


class ImportCotisationsForm(forms.Form):
    """
    Formulaire pour l'importation de cotisations depuis un fichier CSV ou Excel.
    """
    DELIMITERS = [
        (',', _('Virgule (,)')),
        (';', _('Point-virgule (;)')),
        ('\t', _('Tabulation')),
    ]
    
    fichier = forms.FileField(
        label=_("Fichier CSV/Excel"),
        help_text=_("Formats acceptés: .csv, .xlsx, .xls")
    )
    
    delimiter = forms.ChoiceField(
        choices=DELIMITERS,
        initial=';',
        label=_("Séparateur (pour CSV)"),
        required=False
    )
    
    encoding = forms.ChoiceField(
        choices=[
            ('utf-8', 'UTF-8'),
            ('iso-8859-1', 'ISO-8859-1 (Latin-1)'),
            ('windows-1252', 'Windows-1252')
        ],
        initial='utf-8',
        label=_("Encodage (pour CSV)"),
        required=False
    )
    
    header = forms.BooleanField(
        initial=True,
        required=False,
        label=_("Le fichier contient une ligne d'en-tête"),
        help_text=_("Cochez si la première ligne contient les noms des colonnes")
    )
    
    date_emission = forms.DateField(
        initial=timezone.now().date(),
        label=_("Date d'émission"),
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    
    jours_echeance = forms.IntegerField(
        initial=30,
        min_value=1,
        label=_("Jours avant échéance"),
        help_text=_("Nombre de jours entre la date d'émission et la date d'échéance")
    )
    
    statut = forms.ModelChoiceField(
        queryset=Statut.objects.all(),
        required=True,
        label=_("Statut initial des cotisations")
    )
    
    # Mapping des colonnes
    colonne_membre_email = forms.CharField(
        initial='email',
        label=_("Colonne email du membre"),
        help_text=_("Nom de la colonne contenant l'email du membre")
    )
    
    colonne_montant = forms.CharField(
        initial='montant',
        label=_("Colonne montant"),
        help_text=_("Nom de la colonne contenant le montant de la cotisation")
    )
    
    colonne_reference = forms.CharField(
        required=False,
        label=_("Colonne référence"),
        help_text=_("Laissez vide pour générer automatiquement")
    )
    
    colonne_type_membre = forms.CharField(
        required=False,
        label=_("Colonne type de membre"),
        help_text=_("Nom de la colonne contenant le type de membre")
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Ajouter des classes CSS pour le styling
        for field_name, field in self.fields.items():
            if field.widget.__class__.__name__ not in ['CheckboxInput']:
                field.widget.attrs.update({'class': 'form-control'})
            else:
                field.widget.attrs.update({'class': 'form-check-input'})
    
    def clean_fichier(self):
        fichier = self.cleaned_data.get('fichier')
        if fichier:
            ext = fichier.name.split('.')[-1].lower()
            if ext not in ['csv', 'xlsx', 'xls']:
                raise ValidationError(
                    _("Format de fichier non supporté. Utilisez CSV ou Excel (.xlsx, .xls).")
                )
        return fichier


class ConfigurationCotisationForm(forms.ModelForm):
    """
    Formulaire pour modifier les configurations de cotisation.
    """
    class Meta:
        model = ConfigurationCotisation
        fields = ['valeur', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Ajouter des classes CSS pour le styling
        for field_name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control'})