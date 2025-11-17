# Solution au problème de duplication de création de comptes

## 🎯 Problème identifié

Duplication de la logique de création de comptes utilisateur dans deux endroits :
1. `/admin/accounts/customuser/add/` - Crée un utilisateur Django
2. `/membres/nouveau/` - Crée un membre + utilisateur

## 📋 Solutions proposées

---

### **Solution 1 : Admin personnalisé avec inline** ⭐ Recommandée

Créer un formulaire inline dans l'admin pour créer automatiquement un membre lors de la création d'un utilisateur.

#### Fichier : `apps/accounts/admin.py`

```python
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from .models import CustomUser, UserProfile
from apps.membres.models import Membre


class MembreInline(admin.StackedInline):
    """Inline pour créer un membre en même temps qu'un utilisateur"""
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
    extra = 0  # Ne pas afficher de formulaire vide par défaut


class CustomUserAdmin(UserAdmin):
    """Admin personnalisé pour les utilisateurs"""
    inlines = []  # Pas d'inline par défaut

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Informations personnelles'), {
            'fields': ('first_name', 'last_name', 'email', 'telephone')
        }),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'classes': ('collapse',)
        }),
        (_('Dates importantes'), {
            'fields': ('last_login', 'date_joined'),
            'classes': ('collapse',)
        }),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2'),
        }),
        (_('Type de compte'), {
            'classes': ('wide',),
            'fields': ('est_membre',),
            'description': _("Cochez si cet utilisateur est un membre de l'association")
        }),
    )

    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'est_membre_display')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups')
    search_fields = ('username', 'first_name', 'last_name', 'email')

    def get_form(self, request, obj=None, **kwargs):
        """Personnaliser le formulaire selon l'action"""
        form = super().get_form(request, obj, **kwargs)

        # Pour la création d'un nouvel utilisateur
        if not obj:
            # Ajouter le champ "est_membre"
            from django import forms
            form.base_fields['est_membre'] = forms.BooleanField(
                label=_("Créer un profil membre"),
                required=False,
                initial=False,
                help_text=_("Cochez pour créer automatiquement un profil membre pour cet utilisateur")
            )

        return form

    def get_inlines(self, request, obj):
        """Afficher l'inline membre seulement si l'utilisateur le demande"""
        # Si l'utilisateur a coché "est_membre" dans le POST
        if request.method == 'POST' and request.POST.get('est_membre'):
            return [MembreInline]
        # Si on édite un utilisateur qui a déjà un membre
        elif obj and hasattr(obj, 'membre'):
            return [MembreInline]
        return []

    def save_model(self, request, obj, form, change):
        """Sauvegarder l'utilisateur et créer un membre si demandé"""
        super().save_model(request, obj, form, change)

        # Si c'est une création et que "est_membre" est coché
        if not change and form.cleaned_data.get('est_membre'):
            # Créer un membre automatiquement
            if not hasattr(obj, 'membre'):
                Membre.objects.create(
                    utilisateur=obj,
                    nom=obj.last_name or '',
                    prenom=obj.first_name or '',
                    email=obj.email,
                    telephone=obj.telephone or '',
                )

    def est_membre_display(self, obj):
        """Afficher si l'utilisateur est un membre"""
        return hasattr(obj, 'membre')
    est_membre_display.boolean = True
    est_membre_display.short_description = _('Est membre')


admin.site.unregister(CustomUser)  # Désenregistrer l'admin par défaut
admin.site.register(CustomUser, CustomUserAdmin)
```

#### Avantages ✅
- Formulaire unique dans l'admin
- Choix explicite : utilisateur technique OU membre
- Pas de duplication de code
- Interface cohérente

#### Inconvénients ⚠️
- Nécessite de personnaliser l'admin Django
- Logique partagée entre admin et vues

---

### **Solution 2 : Service centralisé de création de comptes** 🏆 La plus robuste

Créer un service Django qui centralise toute la logique de création de comptes.

#### Fichier : `apps/accounts/services.py` (nouveau)

```python
from django.db import transaction
from django.utils.crypto import get_random_string
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from apps.membres.models import Membre
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


class UserCreationService:
    """
    Service centralisé pour la création d'utilisateurs.

    Gère la création d'utilisateurs techniques ET de membres.
    """

    @staticmethod
    @transaction.atomic
    def creer_utilisateur_technique(
        username,
        email,
        password=None,
        first_name='',
        last_name='',
        is_staff=False,
        is_superuser=False,
        **kwargs
    ):
        """
        Crée un utilisateur technique (sans profil membre).

        Args:
            username: Nom d'utilisateur unique
            email: Adresse email
            password: Mot de passe (généré si None)
            first_name: Prénom
            last_name: Nom
            is_staff: Est membre du staff
            is_superuser: Est super-utilisateur

        Returns:
            CustomUser: L'utilisateur créé

        Raises:
            ValidationError: Si les données sont invalides
        """
        # Valider l'unicité
        if User.objects.filter(username=username).exists():
            raise ValidationError({'username': 'Ce nom d\'utilisateur existe déjà.'})

        if User.objects.filter(email=email).exists():
            raise ValidationError({'email': 'Cette adresse email est déjà utilisée.'})

        # Générer un mot de passe si nécessaire
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

        logger.info(f"Utilisateur technique créé: {username} ({email})")
        return user, password

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
        statut=None,
        types_membre=None,
        # Données compte utilisateur
        username=None,
        password=None,
        envoyer_email=False,
        **kwargs
    ):
        """
        Crée un membre ET son compte utilisateur associé.

        Args:
            nom: Nom du membre
            prenom: Prénom du membre
            email: Email (unique)
            telephone: Téléphone
            adresse: Adresse postale
            code_postal: Code postal
            ville: Ville
            pays: Pays
            date_adhesion: Date d'adhésion
            date_naissance: Date de naissance
            statut: Statut du membre
            types_membre: Liste des types de membre
            username: Username (généré si None)
            password: Mot de passe (généré si None)
            envoyer_email: Envoyer email de bienvenue

        Returns:
            tuple: (membre, utilisateur, password)

        Raises:
            ValidationError: Si les données sont invalides
        """
        from django.utils import timezone

        # Valider l'unicité de l'email
        if User.objects.filter(email=email).exists():
            raise ValidationError({'email': 'Un utilisateur avec cet email existe déjà.'})

        if Membre.objects.filter(email=email).exists():
            raise ValidationError({'email': 'Un membre avec cet email existe déjà.'})

        # Générer username si nécessaire
        if not username:
            username = f"{prenom.lower()}.{nom.lower()}".replace(' ', '_').replace("'", '')
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
            statut=statut,
            **kwargs
        )

        # Ajouter les types de membre
        if types_membre:
            for type_membre in types_membre:
                membre.ajouter_type(type_membre)

        # Envoyer email de bienvenue si demandé
        if envoyer_email:
            UserCreationService._envoyer_email_bienvenue(
                membre, user, username, password
            )

        logger.info(f"Membre créé avec compte: {prenom} {nom} ({email})")
        return membre, user, password

    @staticmethod
    def _envoyer_email_bienvenue(membre, user, username, password):
        """Envoie un email de bienvenue avec les identifiants"""
        try:
            from django.core.mail import EmailMultiAlternatives
            from django.template.loader import render_to_string
            from django.urls import reverse
            from django.conf import settings

            context = {
                'membre': membre,
                'username': username,
                'password': password,
                'login_url': f"{settings.SITE_URL}{reverse('accounts:login')}",
            }

            html_message = render_to_string('emails/nouveau_compte.html', context)
            text_message = render_to_string('emails/nouveau_compte.txt', context)

            email = EmailMultiAlternatives(
                subject="Bienvenue - Vos identifiants de connexion",
                body=text_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[membre.email]
            )
            email.attach_alternative(html_message, "text/html")
            email.send()

            logger.info(f"Email de bienvenue envoyé à {membre.email}")
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi de l'email: {str(e)}")
```

#### Utilisation dans `apps/membres/views.py`

```python
# Dans MembreCreateView.form_valid()
from apps.accounts.services import UserCreationService

def form_valid(self, form):
    try:
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
            'statut': form.cleaned_data.get('statut'),
            'types_membre': form.cleaned_data.get('types_membre', []),
        }

        if form.cleaned_data.get('creer_compte'):
            membre, user, password = UserCreationService.creer_membre_avec_compte(
                password=form.cleaned_data.get('password'),
                envoyer_email=True,
                **membre_data
            )
            messages.success(
                self.request,
                _(f"Le membre {membre.nom_complet} a été créé avec un compte utilisateur (username: {user.username})")
            )
        else:
            membre = form.save()
            messages.success(
                self.request,
                _(f"Le membre {membre.nom_complet} a été créé sans compte utilisateur")
            )

        self.object = membre
        return redirect(self.get_success_url())

    except ValidationError as e:
        for field, errors in e.message_dict.items():
            for error in errors:
                messages.error(self.request, f"{field}: {error}")
        return self.form_invalid(form)
```

#### Utilisation dans l'admin Django

```python
# Dans apps/accounts/admin.py
from apps.accounts.services import UserCreationService

class CustomUserAdmin(UserAdmin):
    def save_model(self, request, obj, form, change):
        if not change:  # Nouvelle création
            # Utiliser le service
            est_membre = form.cleaned_data.get('est_membre', False)

            if est_membre:
                # Créer via le service (membre + utilisateur)
                membre, user, password = UserCreationService.creer_membre_avec_compte(
                    nom=obj.last_name,
                    prenom=obj.first_name,
                    email=obj.email,
                    username=obj.username,
                    password=form.cleaned_data['password1'],
                )
                # Remplacer obj par l'utilisateur créé
                obj = user
            else:
                # Créer utilisateur technique
                user, password = UserCreationService.creer_utilisateur_technique(
                    username=obj.username,
                    email=obj.email,
                    password=form.cleaned_data['password1'],
                    first_name=obj.first_name,
                    last_name=obj.last_name,
                    is_staff=obj.is_staff,
                    is_superuser=obj.is_superuser,
                )
                obj = user

        super().save_model(request, obj, form, change)
```

#### Avantages ✅
- **Logique centralisée** : Un seul endroit pour créer des comptes
- **Validation cohérente** : Mêmes règles partout
- **Traçabilité** : Logs centralisés
- **Testabilité** : Facile à tester
- **Réutilisable** : Peut être utilisé par l'API, les commandes management, etc.
- **Transaction atomique** : Rollback automatique en cas d'erreur

#### Inconvénients ⚠️
- Plus de code à écrire initialement
- Nécessite de modifier les vues existantes

---

### **Solution 3 : Signal Django pour synchronisation automatique** 🔄

Utiliser les signaux Django pour créer automatiquement un membre lors de la création d'un utilisateur (ou vice-versa).

#### Fichier : `apps/accounts/signals.py`

```python
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from apps.membres.models import Membre
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


@receiver(post_save, sender=User)
def creer_membre_pour_nouvel_utilisateur(sender, instance, created, **kwargs):
    """
    Signal qui crée automatiquement un membre quand un utilisateur est créé
    (sauf si c'est un compte technique)
    """
    if created and not instance.is_superuser and not instance.is_staff:
        # Vérifier si l'utilisateur n'a pas déjà un membre
        if not hasattr(instance, 'membre'):
            # Créer le membre automatiquement
            Membre.objects.create(
                utilisateur=instance,
                nom=instance.last_name or '',
                prenom=instance.first_name or '',
                email=instance.email,
            )
            logger.info(f"Membre créé automatiquement pour {instance.username}")


@receiver(post_save, sender=Membre)
def creer_utilisateur_pour_nouveau_membre(sender, instance, created, **kwargs):
    """
    Signal qui crée automatiquement un utilisateur quand un membre est créé sans compte
    """
    if created and not instance.utilisateur:
        from django.utils.crypto import get_random_string

        # Générer username
        username = f"{instance.prenom.lower()}.{instance.nom.lower()}".replace(' ', '_')
        base_username = username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1

        # Créer l'utilisateur
        password = get_random_string(length=12)
        user = User.objects.create_user(
            username=username,
            email=instance.email,
            password=password,
            first_name=instance.prenom,
            last_name=instance.nom,
            password_temporary=True
        )

        # Lier au membre
        instance.utilisateur = user
        instance.save(update_fields=['utilisateur'])

        logger.info(f"Utilisateur créé automatiquement pour le membre {instance.nom_complet}")
```

#### Activation dans `apps/accounts/apps.py`

```python
from django.apps import AppConfig

class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.accounts'

    def ready(self):
        import apps.accounts.signals  # Importer les signaux
```

#### Avantages ✅
- Synchronisation automatique
- Pas de modification du code existant
- Transparent pour les développeurs

#### Inconvénients ⚠️
- **Comportement implicite** (peut être surprenant)
- Difficile à déboguer
- Peut causer des effets de bord inattendus
- Pas de contrôle fin sur quand créer un membre ou non

---

## 🏆 Recommandation finale

**Pour votre cas, je recommande la Solution 2 (Service centralisé)** car :

1. ✅ **Explicite et prévisible** : Vous contrôlez exactement quand créer un membre/utilisateur
2. ✅ **Maintenable** : Toute la logique est à un endroit
3. ✅ **Évolutif** : Facile d'ajouter des règles métier (validation email, workflow d'approbation, etc.)
4. ✅ **Testable** : Peut être testé indépendamment
5. ✅ **Cohérent** : Mêmes validations partout

---

## 📝 Plan de migration

### Étape 1 : Créer le service
1. Créer `apps/accounts/services.py`
2. Implémenter `UserCreationService`
3. Écrire les tests unitaires

### Étape 2 : Migrer les vues
1. Modifier `MembreCreateView` pour utiliser le service
2. Tester la création de membres

### Étape 3 : Migrer l'admin
1. Personnaliser `CustomUserAdmin`
2. Ajouter le choix "est_membre"
3. Utiliser le service dans `save_model()`

### Étape 4 : Cleanup
1. Supprimer l'ancienne logique de création dans `MembreCreateView`
2. Documenter l'utilisation du service
3. Ajouter des logs

---

## 🧪 Tests à effectuer

```python
# tests/test_user_creation_service.py
from django.test import TestCase
from apps.accounts.services import UserCreationService
from apps.accounts.models import CustomUser
from apps.membres.models import Membre

class UserCreationServiceTest(TestCase):

    def test_creer_utilisateur_technique(self):
        """Test création d'un utilisateur technique"""
        user, password = UserCreationService.creer_utilisateur_technique(
            username='admin.tech',
            email='admin@example.com',
            is_staff=True
        )

        self.assertEqual(user.username, 'admin.tech')
        self.assertFalse(hasattr(user, 'membre'))

    def test_creer_membre_avec_compte(self):
        """Test création d'un membre avec compte"""
        membre, user, password = UserCreationService.creer_membre_avec_compte(
            nom='Dupont',
            prenom='Jean',
            email='jean.dupont@example.com',
        )

        self.assertEqual(membre.nom, 'Dupont')
        self.assertEqual(user.email, 'jean.dupont@example.com')
        self.assertEqual(membre.utilisateur, user)

    def test_email_unique(self):
        """Test que l'email doit être unique"""
        UserCreationService.creer_membre_avec_compte(
            nom='Dupont',
            prenom='Jean',
            email='test@example.com',
        )

        with self.assertRaises(ValidationError):
            UserCreationService.creer_membre_avec_compte(
                nom='Martin',
                prenom='Marie',
                email='test@example.com',  # Même email
            )
```

---

## 📚 Documentation pour l'équipe

### Pour créer un utilisateur technique (staff, service, etc.)

```python
from apps.accounts.services import UserCreationService

user, password = UserCreationService.creer_utilisateur_technique(
    username='monitoring.service',
    email='monitoring@example.com',
    is_staff=True
)
print(f"Utilisateur créé : {user.username}, mot de passe : {password}")
```

### Pour créer un membre de l'association

```python
from apps.accounts.services import UserCreationService

membre, user, password = UserCreationService.creer_membre_avec_compte(
    nom='Dupont',
    prenom='Jean',
    email='jean.dupont@example.com',
    telephone='0612345678',
    envoyer_email=True  # Envoie un email de bienvenue
)
print(f"Membre créé : {membre.nom_complet}, username : {user.username}")
```

---

**Prêt à implémenter la Solution 2 ?** Je peux créer tous les fichiers nécessaires ! 🚀
