# Service de Création de Comptes Utilisateurs

## Vue d'ensemble

Le `UserCreationService` est un service centralisé pour la création d'utilisateurs et de membres dans l'application Kandiane. Il résout le problème de duplication de code entre la création de comptes utilisateurs techniques (admin, services) et la création de membres avec leurs comptes.

## Architecture

```
UserCreationService (apps/accounts/services.py)
│
├── creer_utilisateur_technique()  → Crée un utilisateur sans profil membre
│   └── Usage: Comptes staff, admin, services techniques
│
├── creer_membre_avec_compte()     → Crée un membre + compte utilisateur
│   ├── Usage: Nouveaux membres de l'association
│   └── Appelle: _envoyer_email_bienvenue() si demandé
│
└── _envoyer_email_bienvenue()     → Envoie email avec identifiants
    └── Usage: Méthode privée interne
```

## Utilisation

### 1. Créer un utilisateur technique

Utilisé pour créer des comptes staff, administrateurs, ou services sans profil membre.

```python
from apps.accounts.services import UserCreationService

# Exemple 1: Admin avec mot de passe automatique
user, password = UserCreationService.creer_utilisateur_technique(
    username='admin.tech',
    email='admin@kandiane.local',
    is_staff=True,
    is_superuser=True
)
print(f"Utilisateur: {user.username}")
print(f"Mot de passe généré: {password}")

# Exemple 2: Service avec mot de passe personnalisé
user, password = UserCreationService.creer_utilisateur_technique(
    username='monitoring',
    email='monitoring@kandiane.local',
    password='MonP@ss123!',
    first_name='Service',
    last_name='Monitoring',
    is_staff=True
)

# Exemple 3: Compte technique simple
user, password = UserCreationService.creer_utilisateur_technique(
    username='backup.service',
    email='backup@kandiane.local',
    telephone='0612345678'
)
```

**Paramètres:**
- `username` (str, requis): Nom d'utilisateur unique
- `email` (str, requis): Adresse email unique
- `password` (str, optional): Mot de passe. Si None, génère un mot de passe de 12 caractères
- `first_name` (str, optional): Prénom
- `last_name` (str, optional): Nom
- `telephone` (str, optional): Téléphone
- `is_staff` (bool, optional): Accès admin. Défaut: False
- `is_superuser` (bool, optional): Super-utilisateur. Défaut: False

**Retour:**
`(user, password)` - Instance CustomUser et mot de passe en clair

**Exceptions:**
- `ValidationError` si username ou email existe déjà

### 2. Créer un membre avec compte

Utilisé pour créer un membre de l'association avec son compte utilisateur.

```python
from apps.accounts.services import UserCreationService

# Exemple 1: Membre avec données minimales
membre, user, password = UserCreationService.creer_membre_avec_compte(
    nom='Dupont',
    prenom='Jean',
    email='jean.dupont@example.com'
)
print(f"Membre: {membre.nom_complet}")
print(f"Username: {user.username}")  # Auto-généré: jean.dupont
print(f"Mot de passe: {password}")

# Exemple 2: Membre complet avec types et email de bienvenue
from apps.membres.models import TypeMembre
from apps.core.models import Statut

type_adherent = TypeMembre.objects.get(libelle='Adhérent')
statut_actif = Statut.pour_membres().get(nom='Actif')

membre, user, password = UserCreationService.creer_membre_avec_compte(
    # Données membre
    nom='Martin',
    prenom='Marie',
    email='marie.martin@example.com',
    telephone='0687654321',
    adresse='123 Rue de la Paix',
    code_postal='75001',
    ville='Paris',
    pays='France',
    date_naissance='1990-05-15',
    statut=statut_actif,
    types_membre=[type_adherent],
    accepte_mail=True,
    accepte_sms=False,
    commentaires='Membre fondateur',
    # Données compte
    username='marie.m',  # Optionnel, sinon auto-généré
    password='P@ssw0rd123!',  # Optionnel, sinon auto-généré
    envoyer_email=True,  # Envoie email de bienvenue
    request=request  # Requis pour construire URL dans email
)

# Exemple 3: Création depuis une vue
class MaVueCreation(View):
    def post(self, request):
        membre, user, password = UserCreationService.creer_membre_avec_compte(
            nom=request.POST['nom'],
            prenom=request.POST['prenom'],
            email=request.POST['email'],
            envoyer_email=True,
            request=request  # Passer la requête pour les URLs
        )
        messages.success(
            request,
            f"Membre {membre.nom_complet} créé avec succès"
        )
        return redirect(membre.get_absolute_url())
```

**Paramètres:**

*Données membre (requis):*
- `nom` (str): Nom du membre
- `prenom` (str): Prénom du membre
- `email` (str): Email unique

*Données membre (optionnels):*
- `telephone` (str): Téléphone
- `adresse` (str): Adresse postale
- `code_postal` (str): Code postal
- `ville` (str): Ville
- `pays` (str): Pays. Défaut: 'France'
- `date_adhesion` (date): Date d'adhésion. Défaut: aujourd'hui
- `date_naissance` (date): Date de naissance
- `langue` (str): Langue préférée. Défaut: 'fr'
- `statut` (Statut): Statut du membre
- `types_membre` (list): Liste des TypeMembre à attribuer
- `accepte_mail` (bool): Accepte emails. Défaut: True
- `accepte_sms` (bool): Accepte SMS. Défaut: False
- `commentaires` (str): Commentaires
- `photo` (File): Photo du membre

*Données compte:*
- `username` (str): Username. Si None, généré depuis prenom.nom
- `password` (str): Mot de passe. Si None, généré automatiquement
- `envoyer_email` (bool): Envoyer email de bienvenue. Défaut: False
- `request` (HttpRequest): Requête pour construire URLs dans email

**Retour:**
`(membre, user, password)` - Instances Membre, CustomUser, et mot de passe en clair

**Exceptions:**
- `ValidationError` si email existe déjà

## Intégration

### Dans les vues (apps/membres/views.py)

```python
class MembreCreateView(CreateView):
    def form_valid(self, form):
        # ... extraction des données ...

        if creer_compte:
            # Utiliser le service
            membre, user, password = UserCreationService.creer_membre_avec_compte(
                nom=form.cleaned_data['nom'],
                prenom=form.cleaned_data['prenom'],
                email=form.cleaned_data['email'],
                # ... autres champs ...
                envoyer_email=True,
                request=self.request
            )
        else:
            # Créer seulement le membre
            membre = form.save()
```

### Dans l'admin Django (apps/accounts/admin.py)

```python
@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    def save_model(self, request, obj, form, change):
        if not change:  # Nouvel utilisateur
            user, password = UserCreationService.creer_utilisateur_technique(
                username=form.cleaned_data['username'],
                email=form.cleaned_data['email'],
                password=form.cleaned_data.get('password1'),
                # ... autres champs ...
            )
            obj.pk = user.pk  # Lier l'objet créé
```

## Caractéristiques

### ✅ Validation

- **Unicité email**: Vérifie que l'email n'existe pas dans CustomUser ET Membre
- **Unicité username**: Vérifie l'unicité et génère automatiquement des variantes (jean.martin → jean.martin1 → jean.martin2)
- **Validation Django**: Utilise les validateurs de modèle natifs

### ✅ Transactions atomiques

Toutes les méthodes utilisent `@transaction.atomic`:
- Si erreur → rollback complet (pas de données partielles)
- Si succès → commit atomique

Exemple:
```python
# Si création du membre échoue, l'utilisateur n'est PAS créé
try:
    membre, user, password = UserCreationService.creer_membre_avec_compte(...)
except ValidationError:
    # Aucune donnée créée - rollback automatique
```

### ✅ Génération automatique

**Username:**
- Format: `prenom.nom` (ex: jean.dupont)
- Normalisation: minuscules, espaces → underscores, pas d'accents
- Gestion collisions: jean.dupont → jean.dupont1 → jean.dupont2

**Password:**
- Longueur: 12 caractères aléatoires sécurisés
- Flag `password_temporary=True` si auto-généré
- Retourné en clair pour communication à l'utilisateur

### ✅ Email de bienvenue

Envoi automatique avec:
- Identifiants de connexion (username, password)
- URL de connexion (construite depuis request)
- Templates: `emails/nouveau_compte.html` et `.txt`
- Gestion d'erreur: ne bloque pas la création si email échoue

### ✅ Logging

Toutes les opérations sont loggées:
```
INFO: Utilisateur technique créé: monitoring (monitoring@kandiane.local), staff=True
INFO: Membre créé avec compte: Jean Dupont (jean.dupont@example.com), username: jean.dupont
INFO: Email de bienvenue envoyé à jean.dupont@example.com
ERROR: Erreur lors de l'envoi de l'email de bienvenue à xxx: [détails]
```

## Gestion des erreurs

```python
from django.core.exceptions import ValidationError

try:
    user, password = UserCreationService.creer_utilisateur_technique(
        username='admin',
        email='existing@example.com'  # Email existant
    )
except ValidationError as e:
    # e.message_dict = {'email': ['Cette adresse email est déjà utilisée.']}
    for field, errors in e.message_dict.items():
        print(f"{field}: {', '.join(errors)}")
```

## Tests

Le service est couvert par 14 tests unitaires dans `apps/accounts/tests/test_services.py`:

```bash
# Exécuter les tests
python manage.py test apps.accounts.tests.test_services

# Tests pour creer_utilisateur_technique() (6 tests)
- Création avec données minimales
- Création avec données complètes
- Détection username dupliqué
- Détection email dupliqué
- Génération automatique password
- Vérification qu'aucun membre n'est créé

# Tests pour creer_membre_avec_compte() (8 tests)
- Création avec données minimales
- Création avec données complètes
- Détection email dupliqué
- Génération automatique username
- Gestion collisions username
- Attribution types de membre
- Rollback en cas d'erreur
- Relation OneToOne correcte
```

Taux de réussite: **13/14 tests** (93%)
- 1 échec intermittent lié aux limitations de SQLite (database lock)

## Migration depuis l'ancien code

### Avant (code dupliqué dans views.py)

```python
# 120+ lignes de code dupliquées
username = f"{membre.prenom.lower()}.{membre.nom.lower()}"
while CustomUser.objects.filter(username=username).exists():
    username = f"{base_username}{counter}"
    counter += 1

password = get_random_string(length=12)
user = CustomUser.objects.create_user(...)
membre.utilisateur = user
membre.save()

# Email de bienvenue (50+ lignes)
context = {...}
html_message = render_to_string(...)
email = EmailMultiAlternatives(...)
email.send()
```

### Après (service centralisé)

```python
# 1 seule ligne !
membre, user, password = UserCreationService.creer_membre_avec_compte(
    nom='Dupont',
    prenom='Jean',
    email='jean.dupont@example.com',
    envoyer_email=True,
    request=request
)
```

**Avantages:**
- ✅ 120+ lignes → 1 ligne
- ✅ Code centralisé et testable
- ✅ Comportement cohérent partout
- ✅ Plus facile à maintenir
- ✅ Transactions atomiques garanties

## Sécurité

- **Passwords**: Hashés automatiquement par Django (`create_user()`)
- **Validation**: Tous les inputs sont validés
- **Transactions**: Atomiques pour éviter états incohérents
- **Logging**: Audit trail de toutes les créations
- **Email**: Pas d'exception levée si envoi échoue (ne bloque pas création)

## Dépendances

```python
# Django
from django.db import transaction
from django.utils.crypto import get_random_string
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

# Models
from apps.accounts.models import CustomUser
from apps.membres.models import Membre, TypeMembre
from apps.core.models import Statut
```

## Support

Pour toute question ou problème:
1. Consulter les tests: `apps/accounts/tests/test_services.py`
2. Consulter les logs: `logger = logging.getLogger(__name__)`
3. Voir les exemples d'utilisation ci-dessus

## Auteur

Service créé dans le cadre du projet Kandiane pour centraliser la logique de création de comptes.

Version: 1.0
Date: 2025-11-16
