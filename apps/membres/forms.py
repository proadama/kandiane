from django import forms
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.db.models import Q
from apps.core.models import Statut
from apps.membres.models import Membre, TypeMembre, MembreTypeMembre, HistoriqueMembre
from dal import autocomplete

# Mise à jour de MembreForm dans apps/membres/forms.py

class MembreForm(forms.ModelForm):
    """
    Formulaire pour la création et l'édition d'un profil membre.

    Le membre est lié à un utilisateur existant. Les informations de base
    (nom, prénom, email, téléphone) sont récupérées depuis l'utilisateur.
    """
    types_membre = forms.ModelMultipleChoiceField(
        queryset=TypeMembre.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label=_("Types de membre")
    )

    utilisateur = forms.ModelChoiceField(
        queryset=None,  # Sera défini dans __init__
        required=True,
        label=_("Utilisateur"),
        help_text=_("Sélectionner un utilisateur existant sans profil membre"),
        widget=autocomplete.ModelSelect2(
            url='accounts:user-autocomplete',
            attrs={
                'data-placeholder': _('Rechercher un utilisateur...'),
                'data-minimum-input-length': 0,
            }
        )
    )
    
    class Meta:
        model = Membre
        fields = [
            'utilisateur', 'adresse',
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

        # Filtrer les statuts pour n'afficher que ceux applicables aux membres
        self.fields['statut'].queryset = Statut.pour_membres()

        # Ajouter des classes CSS pour le styling
        for field_name, field in self.fields.items():
            if field.widget.__class__.__name__ not in ['CheckboxInput', 'CheckboxSelectMultiple', 'RadioSelect']:
                field.widget.attrs.update({'class': 'form-control'})

        # Configurer le champ utilisateur
        from apps.accounts.models import CustomUser
        if not self.instance.pk:
            # Nouveau membre : seulement les utilisateurs sans profil membre
            self.fields['utilisateur'].queryset = CustomUser.objects.filter(
                membre__isnull=True
            ).order_by('username')
        else:
            # Édition : l'utilisateur actuel ou ceux sans membre
            if self.instance.utilisateur:
                self.fields['utilisateur'].queryset = CustomUser.objects.filter(
                    Q(membre__isnull=True) | Q(pk=self.instance.utilisateur.pk)
                ).order_by('username')
            else:
                self.fields['utilisateur'].queryset = CustomUser.objects.filter(
                    membre__isnull=True
                ).order_by('username')

        # Initialiser les types de membre si on édite un membre existant
        if self.instance.pk:
            self.fields['types_membre'].initial = [
                tm.type_membre.id for tm in MembreTypeMembre.objects.filter(
                    membre=self.instance,
                    date_fin__isnull=True
                )
            ]
    
    def clean_utilisateur(self):
        """Valider que l'utilisateur sélectionné n'a pas déjà un profil membre"""
        utilisateur = self.cleaned_data.get('utilisateur')
        if utilisateur:
            # Vérifier si l'utilisateur a déjà un profil membre (sauf pour l'édition)
            if not self.instance.pk or (self.instance.utilisateur and self.instance.utilisateur.pk != utilisateur.pk):
                if hasattr(utilisateur, 'membre'):
                    raise ValidationError(_("Cet utilisateur a déjà un profil membre."))
        return utilisateur
    
    def clean_date_naissance(self):
        """Valider la date de naissance"""
        date_naissance = self.cleaned_data.get('date_naissance')
        if date_naissance:
            # Vérifier que la date n'est pas dans le futur
            if date_naissance > timezone.now().date():
                raise ValidationError(_("La date de naissance ne peut pas être dans le futur."))
                
            # Vérifier que la date n'est pas trop ancienne
            # Limite à 120 ans dans le passé, ce qui est généralement l'âge maximum atteignable
            limite_minimale = timezone.now().date().replace(year=timezone.now().date().year - 120)
            if date_naissance < limite_minimale:
                raise ValidationError(_("La date de naissance ne peut pas être antérieure à {0}.").format(limite_minimale.year))
                
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
    Formulaire amélioré pour l'importation de membres depuis un fichier CSV ou Excel
    """
    DELIMITERS = [
        (',', _('Virgule (,)')),
        (';', _('Point-virgule (;)')),
        ('\t', _('Tabulation')),
    ]
    
    ENCODINGS = [
        ('utf-8', 'UTF-8'),
        ('iso-8859-1', 'ISO-8859-1 (Latin-1)'),
        ('iso-8859-15', 'ISO-8859-15'),
        ('cp1252', 'Windows-1252'),
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
        choices=ENCODINGS,
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
    creer_comptes = forms.BooleanField(
        initial=False,
        required=False,
        label=_("Créer des comptes utilisateurs"),
        help_text=_("Créer automatiquement des comptes utilisateurs pour les membres importés")
    )
    envoyer_emails = forms.BooleanField(
        initial=False,
        required=False,
        label=_("Envoyer emails de bienvenue"),
        help_text=_("Envoyer un email de bienvenue avec les identifiants aux nouveaux membres")
    )
    update_existing = forms.BooleanField(
        initial=True,
        required=False,
        label=_("Mettre à jour les membres existants"),
        help_text=_("Mettre à jour les informations des membres existants (selon l'email)")
    )
    
    # Mapping des colonnes
    colonne_nom = forms.CharField(
        required=True,
        label=_("Colonne pour le nom"),
        initial="nom"
    )
    colonne_prenom = forms.CharField(
        required=True,
        label=_("Colonne pour le prénom"),
        initial="prenom"
    )
    colonne_email = forms.CharField(
        required=True,
        label=_("Colonne pour l'email"),
        initial="email"
    )
    colonne_telephone = forms.CharField(
        required=False,
        label=_("Colonne pour le téléphone"),
        initial="telephone"
    )
    colonne_adresse = forms.CharField(
        required=False,
        label=_("Colonne pour l'adresse"),
        initial="adresse"
    )
    colonne_code_postal = forms.CharField(
        required=False,
        label=_("Colonne pour le code postal"),
        initial="code_postal"
    )
    colonne_ville = forms.CharField(
        required=False,
        label=_("Colonne pour la ville"),
        initial="ville"
    )
    colonne_pays = forms.CharField(
        required=False,
        label=_("Colonne pour le pays"),
        initial="pays"
    )
    colonne_date_naissance = forms.CharField(
        required=False,
        label=_("Colonne pour la date de naissance"),
        initial="date_naissance"
    )
    colonne_date_adhesion = forms.CharField(
        required=False,
        label=_("Colonne pour la date d'adhésion"),
        initial="date_adhesion"
    )
    format_date = forms.ChoiceField(
        choices=[
            ('auto', _('Auto-détection')),
            ('YYYY-MM-DD', 'YYYY-MM-DD'),
            ('DD/MM/YYYY', 'DD/MM/YYYY'),
            ('MM/DD/YYYY', 'MM/DD/YYYY'),
        ],
        initial='auto',
        label=_("Format des dates"),
        required=False
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
        """Valider le fichier importé"""
        fichier = self.cleaned_data.get('fichier')
        if fichier:
            extension = fichier.name.split('.')[-1].lower()
            if extension not in ['csv', 'xlsx', 'xls']:
                raise ValidationError(
                    _("Format de fichier non supporté. Utilisez CSV ou Excel (.xlsx, .xls).")
                )
            
            # Vérifier la taille du fichier (max 10MB)
            if fichier.size > 10 * 1024 * 1024:  # 10MB
                raise ValidationError(
                    _("Le fichier est trop volumineux. La taille maximale est de 10MB.")
                )
        return fichier

# Modifier dans apps/membres/forms.py
# Assurez-vous que la classe MembreSearchForm définit les bonnes valeurs par défaut

class MembreSearchForm(forms.Form):
    """
    Formulaire de recherche avancée pour les membres - Version corrigée
    """
    terme = forms.CharField(
        label=_("Recherche"),
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _("Nom, prénom, email, téléphone...")
        })
    )
    
    type_membre = forms.ModelChoiceField(
        queryset=TypeMembre.objects.all().order_by('ordre_affichage', 'libelle'),
        required=False,
        empty_label=_("Tous les types"),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    statut = forms.ModelChoiceField(
        queryset=Statut.objects.all(),
        required=False,
        empty_label=_("Tous les statuts"),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    date_adhesion_min = forms.DateField(
        label=_("Adhésion depuis"),
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    date_adhesion_max = forms.DateField(
        label=_("Adhésion jusqu'au"),
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    age_min = forms.IntegerField(
        label=_("Âge min"),
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    
    age_max = forms.IntegerField(
        label=_("Âge max"),
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    
    cotisations_impayees = forms.BooleanField(
        label=_("Avec cotisations impayées"),
        required=False,
        initial=False,  # Assurez-vous que c'est False par défaut
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    avec_compte = forms.ChoiceField(
        label=_("Compte utilisateur"),
        choices=[
            ('', _("Indifférent")),
            ('avec', _("Avec compte")),
            ('sans', _("Sans compte"))
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    actif = forms.ChoiceField(
        label=_("Statut d'activité"),
        choices=[
            ('', _("Tous")),
            ('actif', _("Membres actifs")),
            ('inactif', _("Membres inactifs"))
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Ne proposer que les statuts qui sont attribués à au moins un membre
        statuts_utilises = Statut.objects.filter(membre__isnull=False).distinct()
        self.fields['statut'].queryset = statuts_utilises
        
        # Assurez-vous que les modèles sont bien disponibles pour les menus déroulants
        if not self.fields['type_membre'].queryset.exists():
            from django.db.models import Count
            # Récupérer tous les types de membres, même sans membres associés
            self.fields['type_membre'].queryset = TypeMembre.objects.annotate(
                count=Count('id')).order_by('ordre_affichage', 'libelle')
    
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
