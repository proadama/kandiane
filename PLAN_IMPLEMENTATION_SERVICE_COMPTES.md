# Plan d'implémentation - Service centralisé de création de comptes

**Solution 2 : UserCreationService**
**Date de début** : 16 novembre 2025
**Objectif** : Éliminer la duplication de logique de création de comptes entre l'admin et les vues membres

---

## 📊 Vue d'ensemble

### Problème à résoudre
Duplication de la logique de création de comptes dans 2 endroits :
- `/admin/accounts/customuser/add/` → Crée un `CustomUser`
- `/membres/nouveau/` → Crée un `Membre` + `CustomUser`

### Solution
Créer un service centralisé `UserCreationService` dans `apps/accounts/services.py` qui :
- Crée des utilisateurs techniques (staff, services)
- Crée des membres avec leur compte utilisateur
- Gère la validation, les transactions, les emails
- Est utilisé par l'admin ET les vues

### Bénéfices attendus
- ✅ Pas de duplication de code
- ✅ Validation cohérente partout
- ✅ Facilité de maintenance
- ✅ Testabilité accrue
- ✅ Traçabilité via logs
- ✅ Transactions atomiques

---

## 📝 Étapes d'implémentation

### Phase 1 : Préparation (30 min)

#### ✅ Étape 1.1 : Créer la branche Git
```bash
git checkout -b feature/service-creation-comptes
```

**Objectif** : Travailler sur une branche dédiée
**Validation** : `git branch` montre la nouvelle branche
**Rollback** : `git checkout main`

---

#### ✅ Étape 1.2 : Backup du code existant
```bash
cp apps/membres/views.py apps/membres/views.py.backup
cp apps/accounts/admin.py apps/accounts/admin.py.backup
```

**Objectif** : Sauvegarder les fichiers qui seront modifiés
**Validation** : Fichiers .backup créés
**Rollback** : Restaurer depuis les .backup

---

#### ✅ Étape 1.3 : Lire et comprendre le code existant

**Fichiers à analyser** :
- `apps/membres/views.py:397-530` (MembreCreateView)
- `apps/membres/forms.py:13-205` (MembreForm)
- `apps/accounts/forms.py:40-105` (CustomUserCreationForm)
- `apps/accounts/models.py` (CustomUser)
- `apps/membres/models.py:67-555` (Membre)

**Objectif** : Comprendre la logique actuelle
**Validation** : Liste des fonctionnalités à préserver
**Temps estimé** : 15 min

---

### Phase 2 : Création du service (1h)

#### ✅ Étape 2.1 : Créer le fichier services.py

**Fichier** : `apps/accounts/services.py`

**Contenu** :
```python
from django.db import transaction
from django.utils.crypto import get_random_string
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from apps.membres.models import Membre
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


class UserCreationService:
    """Service centralisé pour la création d'utilisateurs."""

    # Méthodes à implémenter
    pass
```

**Objectif** : Structure de base du service
**Validation** : Fichier créé, import fonctionne
**Tests** : `python -c "from apps.accounts.services import UserCreationService"`

---

#### ✅ Étape 2.2 : Implémenter creer_utilisateur_technique()

**Méthode** : `UserCreationService.creer_utilisateur_technique()`

**Fonctionnalités** :
- Validation de l'unicité (username, email)
- Génération de mot de passe si nécessaire
- Création du CustomUser
- Logging de l'action
- Transaction atomique

**Code** :
```python
@staticmethod
@transaction.atomic
def creer_utilisateur_technique(
    username,
    email,
    password=None,
    first_name='',
    last_name='',
    telephone='',
    is_staff=False,
    is_superuser=False,
    **kwargs
):
    """
    Crée un utilisateur technique (sans profil membre).

    Args:
        username: Nom d'utilisateur unique
        email: Adresse email unique
        password: Mot de passe (généré si None)
        first_name: Prénom
        last_name: Nom
        telephone: Numéro de téléphone
        is_staff: Est membre du staff
        is_superuser: Est super-utilisateur
        **kwargs: Arguments supplémentaires

    Returns:
        tuple: (user, password)

    Raises:
        ValidationError: Si les données sont invalides

    Example:
        >>> user, pwd = UserCreationService.creer_utilisateur_technique(
        ...     username='admin.tech',
        ...     email='admin@example.com',
        ...     is_staff=True
        ... )
    """
    # Validation de l'unicité
    if User.objects.filter(username=username).exists():
        raise ValidationError({
            'username': _("Ce nom d'utilisateur existe déjà.")
        })

    if User.objects.filter(email=email).exists():
        raise ValidationError({
            'email': _("Cette adresse email est déjà utilisée.")
        })

    # Générer mot de passe si nécessaire
    if not password:
        password = get_random_string(length=12)
        password_temporary = True
    else:
        password_temporary = kwargs.pop('password_temporary', False)

    # Créer l'utilisateur
    user = User.objects.create_user(
        username=username,
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name,
        is_staff=is_staff,
        is_superuser=is_superuser,
        password_temporary=password_temporary,
        **kwargs
    )

    # Ajouter le téléphone si fourni
    if telephone:
        user.telephone = telephone
        user.save(update_fields=['telephone'])

    logger.info(f"Utilisateur technique créé: {username} ({email})")

    return user, password
```

**Validation** :
- Import réussi
- Méthode appelable
- Retourne (user, password)

**Tests manuels** :
```python
from apps.accounts.services import UserCreationService
user, pwd = UserCreationService.creer_utilisateur_technique(
    username='test.tech',
    email='test@example.com'
)
print(f"Créé: {user.username}, pwd: {pwd}")
```

---

#### ✅ Étape 2.3 : Implémenter creer_membre_avec_compte()

**Méthode** : `UserCreationService.creer_membre_avec_compte()`

**Fonctionnalités** :
- Validation de l'unicité (email)
- Génération username automatique
- Génération mot de passe automatique
- Création utilisateur + membre
- Association OneToOne
- Attribution types de membre
- Transaction atomique
- Logging détaillé

**Code** :
```python
@staticmethod
@transaction.atomic
def creer_membre_avec_compte(
    # Données membre
    nom,
    prenom,
    email,
    telephone='',
    adresse='',
    code_postal='',
    ville='',
    pays='France',
    date_adhesion=None,
    date_naissance=None,
    langue='fr',
    statut=None,
    types_membre=None,
    accepte_mail=True,
    accepte_sms=False,
    commentaires='',
    photo=None,
    # Données compte utilisateur
    username=None,
    password=None,
    envoyer_email=False,
    request=None,
    **kwargs
):
    """
    Crée un membre ET son compte utilisateur associé.

    Args:
        nom: Nom du membre (requis)
        prenom: Prénom du membre (requis)
        email: Email unique (requis)
        telephone: Téléphone
        adresse: Adresse postale
        code_postal: Code postal
        ville: Ville
        pays: Pays (défaut: 'France')
        date_adhesion: Date d'adhésion (défaut: aujourd'hui)
        date_naissance: Date de naissance
        langue: Langue préférée (défaut: 'fr')
        statut: Statut du membre
        types_membre: Liste des types de membre
        accepte_mail: Accepte les communications email
        accepte_sms: Accepte les communications SMS
        commentaires: Commentaires
        photo: Photo du membre
        username: Username (généré si None)
        password: Mot de passe (généré si None)
        envoyer_email: Envoyer email de bienvenue
        request: HttpRequest pour construire les URLs
        **kwargs: Arguments supplémentaires pour Membre

    Returns:
        tuple: (membre, user, password)

    Raises:
        ValidationError: Si les données sont invalides

    Example:
        >>> membre, user, pwd = UserCreationService.creer_membre_avec_compte(
        ...     nom='Dupont',
        ...     prenom='Jean',
        ...     email='jean.dupont@example.com',
        ...     telephone='0612345678',
        ...     envoyer_email=True,
        ...     request=request
        ... )
    """
    from django.utils import timezone

    # Validation de l'unicité de l'email
    if User.objects.filter(email=email).exists():
        raise ValidationError({
            'email': _("Un utilisateur avec cet email existe déjà.")
        })

    if Membre.objects.filter(email=email).exists():
        raise ValidationError({
            'email': _("Un membre avec cet email existe déjà.")
        })

    # Générer username si nécessaire
    if not username:
        # Nettoyer les caractères spéciaux
        username_base = f"{prenom.lower()}.{nom.lower()}"
        username = username_base.replace(' ', '_').replace("'", '').replace('-', '_')

        # Garantir l'unicité
        base_username = username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1

    # Générer password si nécessaire
    if not password:
        password = get_random_string(length=12)
        password_temporary = True
    else:
        password_temporary = False

    # Créer l'utilisateur
    user = User.objects.create_user(
        username=username,
        email=email,
        password=password,
        first_name=prenom,
        last_name=nom,
        password_temporary=password_temporary,
    )

    # Ajouter le téléphone
    if telephone:
        user.telephone = telephone
        user.save(update_fields=['telephone'])

    # Créer le membre
    membre = Membre.objects.create(
        utilisateur=user,
        nom=nom,
        prenom=prenom,
        email=email,
        telephone=telephone,
        adresse=adresse,
        code_postal=code_postal,
        ville=ville,
        pays=pays,
        date_adhesion=date_adhesion or timezone.now().date(),
        date_naissance=date_naissance,
        langue=langue,
        statut=statut,
        accepte_mail=accepte_mail,
        accepte_sms=accepte_sms,
        commentaires=commentaires,
        photo=photo,
        **kwargs
    )

    # Ajouter les types de membre
    if types_membre:
        for type_membre in types_membre:
            membre.ajouter_type(type_membre)

    # Envoyer email de bienvenue si demandé
    if envoyer_email:
        UserCreationService._envoyer_email_bienvenue(
            membre, user, username, password, request
        )

    logger.info(
        f"Membre créé avec compte: {prenom} {nom} ({email}), "
        f"username: {username}, types: {[str(t) for t in types_membre] if types_membre else []}"
    )

    return membre, user, password
```

**Validation** :
- Méthode créée
- Transaction atomique
- Retourne (membre, user, password)
- Rollback si erreur

**Tests manuels** :
```python
from apps.accounts.services import UserCreationService
membre, user, pwd = UserCreationService.creer_membre_avec_compte(
    nom='Dupont',
    prenom='Jean',
    email='jean@example.com'
)
print(f"Membre: {membre.nom_complet}, User: {user.username}")
```

---

#### ✅ Étape 2.4 : Implémenter _envoyer_email_bienvenue()

**Méthode** : `UserCreationService._envoyer_email_bienvenue()` (privée)

**Fonctionnalités** :
- Rendu des templates email
- Envoi email HTML + texte
- Gestion des erreurs d'envoi
- Logging

**Code** :
```python
@staticmethod
def _envoyer_email_bienvenue(membre, user, username, password, request=None):
    """
    Envoie un email de bienvenue avec les identifiants de connexion.

    Args:
        membre: Instance du membre
        user: Instance de l'utilisateur
        username: Nom d'utilisateur
        password: Mot de passe en clair
        request: HttpRequest pour construire l'URL de connexion
    """
    try:
        from django.core.mail import EmailMultiAlternatives
        from django.template.loader import render_to_string
        from django.urls import reverse
        from django.conf import settings

        # URL de connexion
        if request:
            login_url = request.build_absolute_uri(reverse('accounts:login'))
        else:
            login_url = f"{getattr(settings, 'SITE_URL', 'http://localhost:8000')}{reverse('accounts:login')}"

        # Contexte pour le template
        context = {
            'membre': membre,
            'user': user,
            'username': username,
            'password': password,
            'login_url': login_url,
        }

        # Rendre les templates
        html_message = render_to_string('emails/nouveau_compte.html', context)
        text_message = render_to_string('emails/nouveau_compte.txt', context)

        # Créer et envoyer l'email
        email = EmailMultiAlternatives(
            subject=_("Bienvenue - Vos identifiants de connexion"),
            body=text_message,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@kandiane.local'),
            to=[membre.email]
        )
        email.attach_alternative(html_message, "text/html")
        email.send()

        logger.info(f"Email de bienvenue envoyé à {membre.email}")

    except Exception as e:
        logger.error(f"Erreur lors de l'envoi de l'email de bienvenue à {membre.email}: {str(e)}")
        # Ne pas lever d'exception pour ne pas bloquer la création du compte
```

**Validation** :
- Email envoyé (vérifier les logs)
- Pas d'erreur si l'envoi échoue
- Templates rendus correctement

---

### Phase 3 : Tests unitaires (1h)

#### ✅ Étape 3.1 : Créer le fichier de tests

**Fichier** : `apps/accounts/tests/test_services.py`

**Structure** :
```python
from django.test import TestCase, TransactionTestCase
from django.core.exceptions import ValidationError
from apps.accounts.services import UserCreationService
from apps.accounts.models import CustomUser
from apps.membres.models import Membre, TypeMembre
from apps.core.models import Statut


class UserCreationServiceTest(TransactionTestCase):
    """Tests pour UserCreationService"""

    def setUp(self):
        """Préparation des données de test"""
        # Créer des données de test
        pass

    # Tests à implémenter...
```

**Objectif** : Structure de base des tests
**Validation** : Fichier créé, tests découverts par Django

---

#### ✅ Étape 3.2 : Tests pour creer_utilisateur_technique()

**Tests à implémenter** :

1. **test_creer_utilisateur_technique_minimal**
   - Vérifie création avec données minimales
   - Assert: user créé, password retourné

2. **test_creer_utilisateur_technique_complet**
   - Vérifie création avec toutes les données
   - Assert: tous les champs remplis correctement

3. **test_creer_utilisateur_technique_username_duplicate**
   - Vérifie qu'un username dupliqué lève ValidationError
   - Assert: ValidationError levée

4. **test_creer_utilisateur_technique_email_duplicate**
   - Vérifie qu'un email dupliqué lève ValidationError
   - Assert: ValidationError levée

5. **test_creer_utilisateur_technique_password_genere**
   - Vérifie génération automatique du password
   - Assert: password retourné, utilisateur peut se connecter

6. **test_creer_utilisateur_technique_pas_de_membre**
   - Vérifie qu'aucun membre n'est créé
   - Assert: user.membre n'existe pas

**Commande de test** :
```bash
python manage.py test apps.accounts.tests.test_services.UserCreationServiceTest.test_creer_utilisateur_technique_minimal
```

---

#### ✅ Étape 3.3 : Tests pour creer_membre_avec_compte()

**Tests à implémenter** :

1. **test_creer_membre_avec_compte_minimal**
   - Vérifie création avec données minimales
   - Assert: membre + user créés, liés

2. **test_creer_membre_avec_compte_complet**
   - Vérifie création avec toutes les données
   - Assert: tous les champs OK

3. **test_creer_membre_avec_compte_email_duplicate**
   - Vérifie qu'un email dupliqué lève ValidationError
   - Assert: ValidationError, pas de création

4. **test_creer_membre_avec_compte_username_genere**
   - Vérifie génération automatique du username
   - Assert: username = prenom.nom

5. **test_creer_membre_avec_compte_username_collision**
   - Vérifie gestion des collisions de username
   - Assert: username incrémenté (prenom.nom1, prenom.nom2, etc.)

6. **test_creer_membre_avec_compte_types_membre**
   - Vérifie attribution des types de membre
   - Assert: types correctement associés

7. **test_creer_membre_avec_compte_rollback_si_erreur**
   - Vérifie rollback de la transaction si erreur
   - Assert: ni user ni membre créés en cas d'erreur

8. **test_creer_membre_avec_compte_relation_onetoone**
   - Vérifie la relation OneToOne
   - Assert: membre.utilisateur = user, user.membre = membre

**Commande de test** :
```bash
python manage.py test apps.accounts.tests.test_services
```

---

### Phase 4 : Modification des vues membres (45 min)

#### ✅ Étape 4.1 : Modifier MembreCreateView

**Fichier** : `apps/membres/views.py`

**Modifications** :
1. Importer le service
2. Remplacer la logique dans `form_valid()`
3. Simplifier la gestion des erreurs

**Avant** (lignes 419-530) :
```python
def form_valid(self, form):
    try:
        # Enregistrer le membre
        membre = form.save()

        # Créer un compte utilisateur si demandé
        if form.cleaned_data.get('creer_compte'):
            username = f"{membre.prenom.lower()}.{membre.nom.lower()}".replace(' ', '_')
            # ... 80 lignes de code ...
```

**Après** :
```python
def form_valid(self, form):
    from apps.accounts.services import UserCreationService

    try:
        # Préparer les données du membre
        membre_data = {
            'nom': form.cleaned_data['nom'],
            'prenom': form.cleaned_data['prenom'],
            'email': form.cleaned_data['email'],
            'telephone': form.cleaned_data.get('telephone', ''),
            'adresse': form.cleaned_data.get('adresse', ''),
            'code_postal': form.cleaned_data.get('code_postal', ''),
            'ville': form.cleaned_data.get('ville', ''),
            'pays': form.cleaned_data.get('pays', 'France'),
            'date_adhesion': form.cleaned_data.get('date_adhesion'),
            'date_naissance': form.cleaned_data.get('date_naissance'),
            'langue': form.cleaned_data.get('langue', 'fr'),
            'statut': form.cleaned_data.get('statut'),
            'types_membre': form.cleaned_data.get('types_membre', []),
            'accepte_mail': form.cleaned_data.get('accepte_mail', True),
            'accepte_sms': form.cleaned_data.get('accepte_sms', False),
            'commentaires': form.cleaned_data.get('commentaires', ''),
            'photo': form.cleaned_data.get('photo'),
        }

        # Créer le membre avec ou sans compte
        if form.cleaned_data.get('creer_compte'):
            membre, user, password = UserCreationService.creer_membre_avec_compte(
                password=form.cleaned_data.get('password'),
                envoyer_email=True,
                request=self.request,
                **membre_data
            )

            messages.success(
                self.request,
                _(f"Le membre {membre.nom_complet} a été créé avec un compte utilisateur.")
            )
            messages.info(
                self.request,
                _(f"Username: {user.username}")
            )

            # Si pas de password fourni, afficher le password généré
            if not form.cleaned_data.get('password'):
                messages.warning(
                    self.request,
                    _(f"Mot de passe temporaire généré: {password} (à communiquer au membre)")
                )
        else:
            # Créer seulement le membre sans compte
            membre = form.save()

            messages.success(
                self.request,
                _(f"Le membre {membre.nom_complet} a été créé sans compte utilisateur.")
            )

        self.object = membre
        return redirect(self.get_success_url())

    except ValidationError as e:
        # Gérer les erreurs de validation du service
        if hasattr(e, 'message_dict'):
            for field, errors in e.message_dict.items():
                for error in errors:
                    messages.error(self.request, f"{field}: {error}")
        else:
            messages.error(self.request, str(e))

        return self.form_invalid(form)

    except Exception as e:
        logger.error(f"Erreur lors de la création du membre: {str(e)}", exc_info=True)
        messages.error(
            self.request,
            _(f"Erreur lors de la création du membre: {str(e)}")
        )
        return self.form_invalid(form)
```

**Objectif** : Utiliser le service au lieu de dupliquer la logique
**Validation** :
- Code plus court (~30 lignes vs ~100)
- Même fonctionnalités
- Tests manuels passent

**Tests manuels** :
1. Créer un membre avec compte
2. Créer un membre sans compte
3. Vérifier email envoyé
4. Vérifier messages affichés

---

#### ✅ Étape 4.2 : Nettoyer le code obsolète

**Fichier** : `apps/membres/views.py`

**Suppressions** :
- Lignes 426-530 : Ancien code de création de compte
- Import `get_random_string` (si plus utilisé ailleurs)

**Objectif** : Éliminer le code mort
**Validation** : Aucune référence à l'ancien code

---

### Phase 5 : Modification de l'admin (45 min)

#### ✅ Étape 5.1 : Créer/modifier apps/accounts/admin.py

**Fichier** : `apps/accounts/admin.py`

**Modifications** :

```python
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from django import forms
from .models import CustomUser, UserProfile, Role, Permission
from apps.membres.models import Membre
from apps.accounts.services import UserCreationService
import logging

logger = logging.getLogger(__name__)


class MembreInlineAdmin(admin.StackedInline):
    """Inline pour afficher/modifier le membre lié à un utilisateur"""
    model = Membre
    can_delete = False
    verbose_name_plural = _('Informations Membre')
    fk_name = 'utilisateur'
    fields = (
        'nom', 'prenom', 'telephone', 'adresse',
        'code_postal', 'ville', 'pays',
        'date_adhesion', 'date_naissance',
        'langue', 'statut'
    )
    extra = 0


class CustomUserAdminForm(forms.ModelForm):
    """Formulaire personnalisé pour l'admin des utilisateurs"""

    est_membre = forms.BooleanField(
        label=_("Créer un profil membre"),
        required=False,
        initial=False,
        help_text=_("Cochez pour créer automatiquement un profil membre associé à cet utilisateur")
    )

    class Meta:
        model = CustomUser
        fields = '__all__'


class CustomUserAdmin(UserAdmin):
    """Admin personnalisé pour CustomUser"""

    form = CustomUserAdminForm
    inlines = []

    # Champs affichés dans la liste
    list_display = (
        'username', 'email', 'first_name', 'last_name',
        'is_staff', 'is_active', 'est_membre_display'
    )

    list_filter = (
        'is_staff', 'is_superuser', 'is_active',
        'groups', 'date_joined'
    )

    search_fields = ('username', 'first_name', 'last_name', 'email', 'telephone')

    # Fieldsets pour l'édition
    fieldsets = (
        (None, {
            'fields': ('username', 'password')
        }),
        (_('Informations personnelles'), {
            'fields': ('first_name', 'last_name', 'email', 'telephone')
        }),
        (_('Permissions'), {
            'fields': (
                'is_active', 'is_staff', 'is_superuser',
                'groups', 'user_permissions'
            ),
            'classes': ('collapse',)
        }),
        (_('Dates importantes'), {
            'fields': ('last_login', 'date_joined'),
            'classes': ('collapse',)
        }),
    )

    # Fieldsets pour la création
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2'),
        }),
        (_('Informations personnelles'), {
            'classes': ('wide',),
            'fields': ('first_name', 'last_name', 'telephone'),
        }),
        (_('Type de compte'), {
            'classes': ('wide',),
            'fields': ('est_membre', 'is_staff', 'is_superuser'),
            'description': _(
                "Un utilisateur peut être :\n"
                "- Un membre de l'association (cochez 'Créer un profil membre')\n"
                "- Un compte technique/service (ne cochez rien)\n"
                "- Un administrateur (cochez 'Statut équipe' et/ou 'Statut super-utilisateur')"
            )
        }),
    )

    def get_form(self, request, obj=None, **kwargs):
        """Personnaliser le formulaire selon création/édition"""
        form = super().get_form(request, obj, **kwargs)

        # Pour la création uniquement
        if not obj:
            # Le champ est_membre est déjà dans le formulaire via CustomUserAdminForm
            pass
        else:
            # Pour l'édition, retirer le champ est_membre (déjà créé ou non)
            if 'est_membre' in form.base_fields:
                del form.base_fields['est_membre']

        return form

    def get_inlines(self, request, obj):
        """Afficher l'inline membre si l'utilisateur en a un"""
        if obj and hasattr(obj, 'membre'):
            return [MembreInlineAdmin]
        return []

    def save_model(self, request, obj, form, change):
        """Utiliser le service pour créer les comptes"""

        # Si c'est une modification (pas une création)
        if change:
            super().save_model(request, obj, form, change)
            return

        # Si c'est une création
        try:
            est_membre = form.cleaned_data.get('est_membre', False)

            if est_membre:
                # Créer un membre avec compte via le service
                membre, user, password = UserCreationService.creer_membre_avec_compte(
                    nom=obj.last_name or '',
                    prenom=obj.first_name or '',
                    email=obj.email,
                    telephone=obj.telephone or '',
                    username=obj.username,
                    password=form.cleaned_data['password1'],
                    envoyer_email=False,  # Pas d'email depuis l'admin
                )

                # Remplacer obj par l'utilisateur créé par le service
                # pour que Django l'utilise
                for field in obj._meta.fields:
                    setattr(obj, field.name, getattr(user, field.name))

                # Définir les permissions staff/superuser si nécessaire
                if form.cleaned_data.get('is_staff'):
                    obj.is_staff = True
                if form.cleaned_data.get('is_superuser'):
                    obj.is_superuser = True

                obj.save()

                self.message_user(
                    request,
                    _(f"Membre créé: {membre.nom_complet} avec le compte {user.username}"),
                    level='success'
                )

                if password:
                    self.message_user(
                        request,
                        _(f"Mot de passe généré: {password}"),
                        level='warning'
                    )
            else:
                # Créer un utilisateur technique via le service
                user, password = UserCreationService.creer_utilisateur_technique(
                    username=obj.username,
                    email=obj.email,
                    password=form.cleaned_data['password1'],
                    first_name=obj.first_name,
                    last_name=obj.last_name,
                    telephone=obj.telephone or '',
                    is_staff=form.cleaned_data.get('is_staff', False),
                    is_superuser=form.cleaned_data.get('is_superuser', False),
                )

                # Remplacer obj
                for field in obj._meta.fields:
                    setattr(obj, field.name, getattr(user, field.name))

                self.message_user(
                    request,
                    _(f"Utilisateur technique créé: {user.username}"),
                    level='success'
                )

        except Exception as e:
            logger.error(f"Erreur lors de la création dans l'admin: {str(e)}", exc_info=True)
            self.message_user(
                request,
                _(f"Erreur: {str(e)}"),
                level='error'
            )
            # Ne pas sauvegarder en cas d'erreur
            return

    def est_membre_display(self, obj):
        """Colonne indiquant si l'utilisateur est un membre"""
        return hasattr(obj, 'membre')

    est_membre_display.boolean = True
    est_membre_display.short_description = _('Est membre')


# Enregistrer l'admin personnalisé
admin.site.unregister(CustomUser)  # Désenregistrer l'admin par défaut si existant
admin.site.register(CustomUser, CustomUserAdmin)
```

**Objectif** : Admin qui utilise le service
**Validation** :
- Interface admin fonctionne
- Choix "est_membre" affiché
- Création via service fonctionne

---

#### ✅ Étape 5.2 : Tests manuels de l'admin

**Tests à effectuer** :

1. **Créer un utilisateur technique**
   - Aller sur `/admin/accounts/customuser/add/`
   - Ne pas cocher "est_membre"
   - Remplir username, email, password
   - Sauvegarder
   - Vérifier : user créé, pas de membre

2. **Créer un membre via l'admin**
   - Aller sur `/admin/accounts/customuser/add/`
   - Cocher "est_membre"
   - Remplir les infos
   - Sauvegarder
   - Vérifier : user + membre créés, liés

3. **Modifier un utilisateur existant**
   - Éditer un utilisateur
   - Vérifier inline membre affiché si applicable
   - Modifier et sauvegarder
   - Vérifier modifications OK

**Objectif** : Validation fonctionnelle de l'admin
**Validation** : Tous les tests passent

---

### Phase 6 : Documentation et finalisation (30 min)

#### ✅ Étape 6.1 : Documenter l'utilisation du service

**Fichier** : `apps/accounts/README_SERVICE.md` (nouveau)

**Contenu** :
- Guide d'utilisation du service
- Exemples de code
- Cas d'usage courants
- FAQ

**Objectif** : Faciliter l'utilisation par l'équipe

---

#### ✅ Étape 6.2 : Mettre à jour la documentation principale

**Fichier** : `INSTALLATION_ET_TESTS.md`

**Ajout** : Section "Création de comptes"

```markdown
## Création de comptes utilisateur

### Via le service (recommandé)

```python
from apps.accounts.services import UserCreationService

# Créer un membre
membre, user, password = UserCreationService.creer_membre_avec_compte(
    nom='Dupont',
    prenom='Jean',
    email='jean.dupont@example.com'
)

# Créer un utilisateur technique
user, password = UserCreationService.creer_utilisateur_technique(
    username='monitoring',
    email='monitoring@example.com',
    is_staff=True
)
```

### Via l'interface web

- **Membres** : `/membres/nouveau/`
- **Admin** : `/admin/accounts/customuser/add/`
```

---

#### ✅ Étape 6.3 : Ajouter des logs et commentaires

**Fichiers** : `apps/accounts/services.py`, `apps/membres/views.py`, `apps/accounts/admin.py`

**Ajouts** :
- Docstrings complets
- Commentaires explicatifs
- Messages de log détaillés

**Objectif** : Code auto-documenté et facilement maintenable

---

### Phase 7 : Tests d'intégration (30 min)

#### ✅ Étape 7.1 : Scénarios de test complets

**Scénarios à tester** :

1. **Scénario 1 : Création membre avec compte via formulaire**
   - Aller sur `/membres/nouveau/`
   - Remplir le formulaire
   - Cocher "Créer un compte"
   - Sauvegarder
   - Vérifier : membre créé, compte créé, email envoyé

2. **Scénario 2 : Création membre sans compte via formulaire**
   - Aller sur `/membres/nouveau/`
   - Remplir le formulaire
   - Ne pas cocher "Créer un compte"
   - Sauvegarder
   - Vérifier : membre créé, pas de compte

3. **Scénario 3 : Création utilisateur technique via admin**
   - Aller sur `/admin/accounts/customuser/add/`
   - Ne pas cocher "est_membre"
   - Créer
   - Vérifier : utilisateur créé, pas de membre

4. **Scénario 4 : Création membre via admin**
   - Aller sur `/admin/accounts/customuser/add/`
   - Cocher "est_membre"
   - Créer
   - Vérifier : utilisateur + membre créés

5. **Scénario 5 : Gestion des erreurs**
   - Essayer de créer avec email dupliqué
   - Vérifier : erreur affichée, rien créé

6. **Scénario 6 : Attribution types de membre**
   - Créer un membre
   - Sélectionner des types
   - Vérifier : types correctement attribués

**Objectif** : Validation end-to-end
**Validation** : Tous les scénarios passent

---

#### ✅ Étape 7.2 : Tests de performance

**Tests** :
- Création de 100 membres via le service
- Mesurer le temps d'exécution
- Vérifier pas de N+1 queries

**Commande** :
```python
import time
from apps.accounts.services import UserCreationService

start = time.time()
for i in range(100):
    UserCreationService.creer_membre_avec_compte(
        nom=f'Test{i}',
        prenom=f'User{i}',
        email=f'test{i}@example.com'
    )
end = time.time()
print(f"Temps: {end - start}s pour 100 créations")
```

**Objectif** : Vérifier les performances
**Validation** : < 30s pour 100 créations

---

### Phase 8 : Commit et documentation (15 min)

#### ✅ Étape 8.1 : Commit des changements

**Commandes** :
```bash
# Vérifier les fichiers modifiés
git status

# Ajouter tous les fichiers
git add apps/accounts/services.py
git add apps/accounts/tests/test_services.py
git add apps/accounts/admin.py
git add apps/membres/views.py
git add apps/accounts/README_SERVICE.md
git add INSTALLATION_ET_TESTS.md

# Commit
git commit -m "Feature: Service centralisé de création de comptes

- Ajout de UserCreationService dans apps/accounts/services.py
  * creer_utilisateur_technique() pour comptes staff/services
  * creer_membre_avec_compte() pour membres de l'association
  * Validation centralisée et cohérente
  * Transactions atomiques
  * Logging détaillé

- Modification de MembreCreateView pour utiliser le service
  * Simplification du code (100 lignes → 30 lignes)
  * Élimination de la duplication
  * Meilleure gestion des erreurs

- Personnalisation de l'admin CustomUser
  * Ajout du choix 'est_membre' lors de la création
  * Utilisation du service pour la création
  * Affichage du profil membre si existant

- Tests unitaires complets
  * 14 tests pour le service
  * Couverture: création, validation, rollback, etc.

- Documentation
  * Guide d'utilisation du service
  * Mise à jour INSTALLATION_ET_TESTS.md
  * Docstrings et commentaires

Résout le problème de duplication de logique entre:
- /admin/accounts/customuser/add/
- /membres/nouveau/

Bénéfices:
- Code centralisé et maintenable
- Validation cohérente
- Facilité de test
- Traçabilité via logs

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"

# Pousser sur la branche
git push origin feature/service-creation-comptes
```

**Objectif** : Sauvegarder le travail
**Validation** : Commit créé, pushe sur origin

---

#### ✅ Étape 8.2 : Créer une Pull Request

**Sur GitHub/GitLab** :
1. Créer PR depuis `feature/service-creation-comptes` vers `main`
2. Titre : "Feature: Service centralisé de création de comptes"
3. Description : Copier le message de commit
4. Assigner des reviewers
5. Ajouter des labels : `enhancement`, `refactoring`

**Objectif** : Préparer la revue de code
**Validation** : PR créée

---

## 📊 Récapitulatif

### Fichiers créés
- ✅ `apps/accounts/services.py` (~200 lignes)
- ✅ `apps/accounts/tests/test_services.py` (~300 lignes)
- ✅ `apps/accounts/README_SERVICE.md` (~100 lignes)

### Fichiers modifiés
- ✅ `apps/membres/views.py` (-100 lignes, +30 lignes)
- ✅ `apps/accounts/admin.py` (+150 lignes)
- ✅ `INSTALLATION_ET_TESTS.md` (+50 lignes)

### Métriques
- **Lignes ajoutées** : ~700
- **Lignes supprimées** : ~100
- **Gain net** : Élimination de duplication + meilleure structure
- **Tests** : 14 tests unitaires
- **Temps estimé** : 4-5 heures

### Bénéfices
- ✅ Pas de duplication de code
- ✅ Validation cohérente
- ✅ Facilité de maintenance
- ✅ Testabilité accrue
- ✅ Traçabilité (logs)
- ✅ Transactions atomiques

---

## ✅ Checklist finale

Avant de marquer la tâche comme terminée :

- [ ] Tous les tests unitaires passent
- [ ] Tous les tests d'intégration passent
- [ ] L'admin fonctionne correctement
- [ ] Le formulaire membres fonctionne
- [ ] Les emails sont envoyés
- [ ] La documentation est à jour
- [ ] Le code est commenté
- [ ] Les logs sont en place
- [ ] Pas de régression
- [ ] PR créée et assignée
- [ ] Branche fusionnée (après revue)

---

## 🔄 Plan de rollback

En cas de problème grave :

1. **Rollback Git**
   ```bash
   git checkout main
   git branch -D feature/service-creation-comptes
   ```

2. **Restaurer les backups**
   ```bash
   cp apps/membres/views.py.backup apps/membres/views.py
   cp apps/accounts/admin.py.backup apps/accounts/admin.py
   ```

3. **Supprimer le service**
   ```bash
   rm apps/accounts/services.py
   rm apps/accounts/tests/test_services.py
   ```

4. **Redémarrer le serveur**
   ```bash
   python manage.py runserver
   ```

---

**Prêt à commencer l'implémentation ?** 🚀
