# apps/accounts/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordResetForm, SetPasswordForm
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from .models import Role, Permission, UserProfile, CustomUser
from django.contrib.auth.forms import PasswordResetForm
from django.core.exceptions import ValidationError

User = get_user_model()


class CustomAuthenticationForm(AuthenticationForm):
    """
    Formulaire d'authentification personnalisé.
    """
    username = forms.EmailField(
        label=_("Adresse email"),
        widget=forms.EmailInput(attrs={'autofocus': True, 'class': 'form-control', 'placeholder': _("Email")})
    )
    password = forms.CharField(
        label=_("Mot de passe"),
        strip=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': _("Mot de passe")})
    )
    
    error_messages = {
        'invalid_login': _(
            "Veuillez saisir une adresse email et un mot de passe valides. "
            "Notez que les deux champs sont sensibles à la casse."
        ),
        'inactive': _("Ce compte est inactif."),
    }
    
    class Meta:
        model = User
        fields = ('username', 'password')


class CustomUserCreationForm(UserCreationForm):
    """
    Formulaire d'inscription personnalisé.
    """
    email = forms.EmailField(
        label=_("Adresse email"),
        max_length=254,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': _("Email")})
    )
    username = forms.CharField(
        label=_("Nom d'utilisateur"),
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': _("Nom d'utilisateur")})
    )
    first_name = forms.CharField(
        label=_("Prénom"),
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': _("Prénom")})
    )
    last_name = forms.CharField(
        label=_("Nom"),
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': _("Nom")})
    )
    password1 = forms.CharField(
        label=_("Mot de passe"),
        strip=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': _("Mot de passe")})
    )
    password2 = forms.CharField(
        label=_("Confirmation du mot de passe"),
        strip=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': _("Confirmation du mot de passe")})
    )
    accepte_communications = forms.BooleanField(
        label=_("J'accepte de recevoir des communications"),
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    accept_terms = forms.BooleanField(
        required=True,
        label=_("J'accepte les termes et conditions d'utilisation"),
        error_messages={
            'required': _("Vous devez accepter les termes et conditions pour créer un compte.")
        },
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    class Meta:
        model = CustomUser
        fields = ('email', 'username', 'first_name', 'last_name', 'password1', 'password2')
    
    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get('accept_terms'):
            raise forms.ValidationError(_("Vous devez accepter les termes et conditions."))
        return cleaned_data
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.is_active = False  # L'utilisateur doit confirmer son email
        user.generate_activation_key()
        
        if commit:
            user.save()
        return user


class CustomPasswordResetForm(PasswordResetForm):
    """
    Formulaire de réinitialisation de mot de passe personnalisé.
    """
    email = forms.EmailField(
        label=_("Adresse email"),
        max_length=254,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': _("Email")})
    )


class CustomSetPasswordForm(SetPasswordForm):
    """
    Formulaire de définition d'un nouveau mot de passe personnalisé.
    """
    new_password1 = forms.CharField(
        label=_("Nouveau mot de passe"),
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': _("Nouveau mot de passe")}),
        strip=False,
    )
    new_password2 = forms.CharField(
        label=_("Confirmation du nouveau mot de passe"),
        strip=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': _("Confirmation du nouveau mot de passe")}),
    )


class UserProfileForm(forms.ModelForm):
    """
    Formulaire de mise à jour du profil utilisateur.
    """
    first_name = forms.CharField(
        label=_("Prénom"),
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    last_name = forms.CharField(
        label=_("Nom"),
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    telephone = forms.CharField(
        label=_("Téléphone"),
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    avatar = forms.ImageField(
        label=_("Avatar"),
        required=False,
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = UserProfile
        fields = ('bio', 'date_naissance', 'adresse', 'ville', 'code_postal', 'pays')
        widgets = {
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'date_naissance': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'adresse': forms.TextInput(attrs={'class': 'form-control'}),
            'ville': forms.TextInput(attrs={'class': 'form-control'}),
            'code_postal': forms.TextInput(attrs={'class': 'form-control'}),
            'pays': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(UserProfileForm, self).__init__(*args, **kwargs)
        
        if user:
            self.fields['first_name'].initial = user.first_name
            self.fields['last_name'].initial = user.last_name
            self.fields['telephone'].initial = user.telephone
    
    def save(self, user=None, commit=True):
        profile = super().save(commit=False)
        
        if user:
            user.first_name = self.cleaned_data['first_name']
            user.last_name = self.cleaned_data['last_name']
            user.telephone = self.cleaned_data['telephone']
            if self.cleaned_data['avatar']:
                user.avatar = self.cleaned_data['avatar']
            user.save()
        
        if commit:
            profile.save()
        return profile


class RoleForm(forms.ModelForm):
    """
    Formulaire pour créer et modifier des rôles.
    """
    permissions = forms.ModelMultipleChoiceField(
        queryset=Permission.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'})
    )
    
    class Meta:
        model = Role
        fields = ('nom', 'description', 'is_default')
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_default': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super(RoleForm, self).__init__(*args, **kwargs)
        
        if self.instance.pk:
            self.fields['permissions'].initial = Permission.objects.filter(
                roles__role=self.instance
            )
    
    def save(self, commit=True):
        role = super().save(commit=commit)
        
        if commit:
            # Mettre à jour les permissions
            role.permissions.all().delete()
            for permission in self.cleaned_data['permissions']:
                role.permissions.create(permission=permission)
        
        return role

class CustomPasswordResetForm(PasswordResetForm):
    """
    Formulaire personnalisé pour la réinitialisation de mot de passe.
    Vérifie que l'email existe et correspond à un compte actif avant d'envoyer l'email.
    """
    def clean_email(self):
        email = self.cleaned_data.get('email')
        # Récupérer le modèle utilisateur
        User = self.user_model
        
        # Vérifier si l'email existe et correspond à un compte actif
        if not User.objects.filter(email=email, is_active=True).exists():
            raise ValidationError(_("Aucun compte actif n'est associé à cette adresse email."))
        
        return email

    # Surcharge de la propriété pour éviter la circularité d'import
    @property
    def user_model(self):
        from django.contrib.auth import get_user_model
        return get_user_model()