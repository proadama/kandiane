from django import forms
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from apps.core.models import Statut
from apps.membres.models import Membre, TypeMembre, MembreTypeMembre, HistoriqueMembre


# Mise à jour de MembreForm dans apps/membres/forms.py

class MembreForm(forms.ModelForm):
    """
    Formulaire pour la création et l'édition d'un membre
    """
    types_membre = forms.ModelMultipleChoiceField(
        queryset=TypeMembre.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label=_("Types de membre")
    )

    creer_compte = forms.BooleanField(
        label=_("Créer un compte utilisateur"),
        required=False,
        initial=True,
        help_text=_("Permettre à ce membre de se connecter à l'application")
    )
    
    password = forms.CharField(
        label=_("Mot de passe"),
        required=False,
        widget=forms.PasswordInput,
        help_text=_("Laissez vide pour générer un mot de passe aléatoire ou entrez un mot de passe fort")
    )
    
    password_confirm = forms.CharField(
        label=_("Confirmer le mot de passe"),
        required=False,
        widget=forms.PasswordInput,
        help_text=_("Entrez à nouveau le mot de passe pour confirmation")
    )
    
    class Meta:
        model = Membre
        fields = [
            'nom', 'prenom', 'email', 'telephone', 'adresse',
            'code_postal', 'ville', 'pays', 'date_adhesion', 'date_naissance',
            'langue', 'statut', 'accepte_mail', 'accepte_sms',
            'commentaires', 'photo'
        ]
        widgets = {
            'date_adhesion': forms.DateInput(
                attrs={'type': 'date', 'class': 'form-control'},
                format='%Y-%m-%d'
            ),
            'date_naissance': forms.DateInput(
                attrs={'type': 'date', 'class': 'form-control'},
                format='%Y-%m-%d'
            ),
            'commentaires': forms.Textarea(
                attrs={'rows': 3, 'class': 'form-control'}
            ),
            'adresse': forms.Textarea(
                attrs={'rows': 2, 'class': 'form-control'}
            ),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Ajouter des classes CSS pour le styling
        for field_name, field in self.fields.items():
            if field.widget.__class__.__name__ not in ['CheckboxInput', 'CheckboxSelectMultiple', 'RadioSelect']:
                field.widget.attrs.update({'class': 'form-control'})
        
        # Pour les nouveaux membres, forcer la création d'un compte utilisateur
        if not self.instance.pk:
            self.fields['creer_compte'].initial = True
            self.fields['creer_compte'].help_text = _("Un compte utilisateur sera automatiquement créé pour ce membre")
        # Si le membre a déjà un compte, désactiver l'option
        elif self.instance and self.instance.pk and self.instance.utilisateur:
            self.fields['creer_compte'].initial = False
            self.fields['creer_compte'].disabled = True
            self.fields['creer_compte'].help_text = _("Ce membre a déjà un compte utilisateur")
            self.fields['password'].widget = forms.HiddenInput()
            
        # Initialiser les types de membre si on édite un membre existant
        if self.instance.pk:
            self.fields['types_membre'].initial = [
                tm.type_membre.id for tm in MembreTypeMembre.objects.filter(
                    membre=self.instance,
                    date_fin__isnull=True
                )
            ]
    
    def clean(self):
        """Validation globale du formulaire"""
        cleaned_data = super().clean()
        
        # Vérifier que les mots de passe correspondent
        creer_compte = cleaned_data.get('creer_compte')
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')
        
        if creer_compte and not self.instance.utilisateur:
            if password:
                # Vérifier que les mots de passe correspondent
                if password != password_confirm:
                    self.add_error('password_confirm', _("Les mots de passe ne correspondent pas."))
                
                # Vérifier la force du mot de passe avec les validateurs Django
                try:
                    # Utiliser validate_password pour vérifier la conformité du mot de passe
                    validate_password(password)
                except DjangoValidationError as e:
                    # Ajouter chaque erreur au champ password
                    self.add_error('password', e)
        
        return cleaned_data
    
    def clean_email(self):
        """Valider que l'email est unique"""
        email = self.cleaned_data.get('email')
        if email:
            # Vérifier si l'email existe déjà pour un autre membre
            if Membre.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
                raise ValidationError(_("Un membre avec cet email existe déjà."))
        return email
    
    def clean_date_naissance(self):
        """Valider la date de naissance"""
        date_naissance = self.cleaned_data.get('date_naissance')
        if date_naissance and date_naissance > timezone.now().date():
            raise ValidationError(_("La date de naissance ne peut pas être dans le futur."))
        return date_naissance
    
    def clean_date_adhesion(self):
        """Valider la date d'adhésion"""
        date_adhesion = self.cleaned_data.get('date_adhesion')
        if date_adhesion and date_adhesion > timezone.now().date():
            raise ValidationError(_("La date d'adhésion ne peut pas être dans le futur."))
        return date_adhesion
    
    def save(self, commit=True):
        """
        Surcharger la méthode save pour gérer les types de membre
        """
        membre = super().save(commit=commit)
        
        if commit:
            # Gérer les types de membre
            types_membre_selectionnes = set(self.cleaned_data.get('types_membre', []))
            
            # Ne procéder que si l'instance a déjà été sauvegardée
            if membre.pk:
                types_membre_actuels = set(
                    type_membre.type_membre for type_membre in 
                    MembreTypeMembre.objects.filter(
                        membre=membre, 
                        date_fin__isnull=True
                    )
                )
                
                # Types à ajouter (nouveaux)
                for type_membre in types_membre_selectionnes - types_membre_actuels:
                    membre.ajouter_type(type_membre)
                
                # Types à supprimer (plus sélectionnés)
                for type_membre in types_membre_actuels - types_membre_selectionnes:
                    membre.supprimer_type(type_membre)
            
            # Enregistrer l'historique
            if hasattr(self, 'changed_data') and self.changed_data:
                HistoriqueMembre.objects.create(
                    membre=membre,
                    utilisateur=self.user,
                    action='modification',
                    description=f"Modification des champs: {', '.join(self.changed_data)}",
                    donnees_avant={
                        field: str(getattr(self.instance, field)) 
                        for field in self.changed_data 
                        if hasattr(self.instance, field)
                    },
                    donnees_apres={
                        field: str(self.cleaned_data.get(field))
                        for field in self.changed_data
                    }
                )
            
        return membre


class TypeMembreForm(forms.ModelForm):
    """
    Formulaire pour la création et l'édition d'un type de membre
    """
    class Meta:
        model = TypeMembre
        fields = ['libelle', 'description', 'cotisation_requise', 'ordre_affichage']
        widgets = {
            'description': forms.Textarea(
                attrs={'rows': 3, 'class': 'form-control'}
            ),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Ajouter des classes CSS pour le styling
        for field_name, field in self.fields.items():
            if field.widget.__class__.__name__ not in ['CheckboxInput']:
                field.widget.attrs.update({'class': 'form-control'})


class MembreTypeMembreForm(forms.ModelForm):
    """
    Formulaire pour ajouter un type de membre à un membre
    """
    class Meta:
        model = MembreTypeMembre
        fields = ['type_membre', 'date_debut', 'commentaire']
        widgets = {
            'date_debut': forms.DateInput(
                attrs={'type': 'date', 'class': 'form-control'},
                format='%Y-%m-%d'
            ),
            'commentaire': forms.Textarea(
                attrs={'rows': 2, 'class': 'form-control'}
            ),
        }
    
    def __init__(self, *args, **kwargs):
        self.membre = kwargs.pop('membre', None)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Définir le membre automatiquement
        if self.membre:
            self.instance.membre = self.membre
        
        # Enregistrer l'utilisateur qui fait la modification
        if self.user and not self.user.is_anonymous:  # Vérifiez que l'utilisateur est authentifié
            self.instance.modifie_par = self.user
        
        # Définir la date de début par défaut
        if not self.instance.pk and 'date_debut' not in self.initial:
            self.initial['date_debut'] = timezone.now().date()
        
        # Ajouter des classes CSS pour le styling
        for field_name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control'})
        
        # Filtrer les types déjà actifs pour ce membre
        if self.membre and not self.instance.pk:
            types_ids = MembreTypeMembre.objects.filter(
                membre=self.membre,
                date_fin__isnull=True
            ).values_list('type_membre_id', flat=True)
            
            self.fields['type_membre'].queryset = TypeMembre.objects.exclude(
                id__in=types_ids
            )
    
    def clean_date_debut(self):
        """Valider la date de début"""
        date_debut = self.cleaned_data.get('date_debut')
        if date_debut and date_debut > timezone.now().date():
            raise ValidationError(_("La date de début ne peut pas être dans le futur."))
        return date_debut
    
    def clean(self):
        """Validation supplémentaire"""
        cleaned_data = super().clean()
        type_membre = cleaned_data.get('type_membre')
        date_debut = cleaned_data.get('date_debut')
        
        # Vérifier s'il y a déjà une association active pour ce type de membre
        if self.membre and type_membre and date_debut and not self.instance.pk:
            if MembreTypeMembre.objects.filter(
                membre=self.membre,
                type_membre=type_membre,
                date_fin__isnull=True
            ).exists():
                raise ValidationError(
                    _("Ce membre a déjà un type de membre actif '%(type)s'."),
                    params={'type': type_membre.libelle}
                )
        
        return cleaned_data


class MembreImportForm(forms.Form):
    """
    Formulaire pour l'importation de membres depuis un fichier CSV ou Excel
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
        initial=',',
        label=_("Séparateur (pour CSV)"),
        required=False
    )
    header = forms.BooleanField(
        initial=True,
        required=False,
        label=_("Le fichier contient une ligne d'en-tête"),
        help_text=_("Cochez si la première ligne contient les noms des colonnes")
    )
    type_membre = forms.ModelChoiceField(
        queryset=TypeMembre.objects.all(),
        required=True,
        label=_("Type de membre à attribuer"),
        help_text=_("Type de membre par défaut pour les membres importés")
    )
    statut = forms.ModelChoiceField(
        queryset=Statut.objects.all(),
        required=False,
        label=_("Statut à attribuer"),
        help_text=_("Statut par défaut pour les membres importés")
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Ajouter des classes CSS pour le styling
        for field_name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control'})
    
    def clean_fichier(self):
        """Valider le fichier importé"""
        fichier = self.cleaned_data.get('fichier')
        if fichier:
            extension = fichier.name.split('.')[-1].lower()
            if extension not in ['csv', 'xlsx', 'xls']:
                raise ValidationError(
                    _("Format de fichier non supporté. Utilisez CSV ou Excel (.xlsx, .xls).")
                )
        return fichier


class MembreSearchForm(forms.Form):
    """
    Formulaire de recherche avancée des membres
    """
    terme = forms.CharField(
        required=False,
        label=_("Rechercher"),
        widget=forms.TextInput(attrs={
            'placeholder': _("Nom, prénom, email, téléphone..."),
            'class': 'form-control'
        })
    )
    type_membre = forms.ModelChoiceField(
        queryset=TypeMembre.objects.all(),
        required=False,
        empty_label=_("Tous les types"),
        label=_("Type de membre"),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    statut = forms.ModelChoiceField(
        queryset=Statut.objects.all(),
        required=False,
        empty_label=_("Tous les statuts"),
        label=_("Statut"),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    date_adhesion_min = forms.DateField(
        required=False,
        label=_("Adhésion depuis le"),
        widget=forms.DateInput(
            attrs={'type': 'date', 'class': 'form-control'},
            format='%Y-%m-%d'
        )
    )
    date_adhesion_max = forms.DateField(
        required=False,
        label=_("Adhésion jusqu'au"),
        widget=forms.DateInput(
            attrs={'type': 'date', 'class': 'form-control'},
            format='%Y-%m-%d'
        )
    )
    age_min = forms.IntegerField(
        required=False,
        min_value=0,
        max_value=120,
        label=_("Âge minimum"),
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    age_max = forms.IntegerField(
        required=False,
        min_value=0,
        max_value=120,
        label=_("Âge maximum"),
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    cotisations_impayees = forms.BooleanField(
        required=False,
        label=_("Avec cotisations impayées"),
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    avec_compte = forms.ChoiceField(
        choices=[
            ('', _("Indifférent")),
            ('avec', _("Avec compte utilisateur")),
            ('sans', _("Sans compte utilisateur"))
        ],
        required=False,
        label=_("Compte utilisateur"),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    actif = forms.ChoiceField(
        choices=[
            ('', _("Tous")),
            ('actif', _("Membres actifs")),
            ('inactif', _("Membres inactifs"))
        ],
        required=False,
        label=_("Statut d'activité"),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    def clean(self):
        """Validation croisée des champs"""
        cleaned_data = super().clean()
        date_adhesion_min = cleaned_data.get('date_adhesion_min')
        date_adhesion_max = cleaned_data.get('date_adhesion_max')
        age_min = cleaned_data.get('age_min')
        age_max = cleaned_data.get('age_max')
        
        # Vérifier la cohérence des dates d'adhésion
        if date_adhesion_min and date_adhesion_max and date_adhesion_min > date_adhesion_max:
            self.add_error(
                'date_adhesion_max',
                _("La date de fin doit être postérieure à la date de début.")
            )
        
        # Vérifier la cohérence des âges
        if age_min is not None and age_max is not None and age_min > age_max:
            self.add_error(
                'age_max',
                _("L'âge maximum doit être supérieur à l'âge minimum.")
            )
        
        return cleaned_data