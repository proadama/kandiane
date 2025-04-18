# Application Accounts

## Présentation
L'application **Accounts** fournit un système d'authentification personnalisé et de gestion des utilisateurs pour le projet de gestion d'association. Elle étend les fonctionnalités standard de Django pour offrir un contrôle d'accès basé sur les rôles, une gestion de profil utilisateur avancée, et un suivi des activités de connexion.

## Fonctionnalités principales

- 🔐 **Authentification personnalisée** avec email comme identifiant principal
- 👥 **Système de rôles et permissions** pour contrôler l'accès aux fonctionnalités
- 📧 **Activation de compte par email** avec lien de confirmation
- 🔑 **Réinitialisation de mot de passe** sécurisée
- 👤 **Gestion de profil utilisateur** avec informations supplémentaires
- 📊 **Historisation des connexions** pour l'audit de sécurité
- ⏱️ **Session à expiration automatique** pour renforcer la sécurité
- 🛡️ **Middleware de contrôle d'accès** basé sur les permissions

## Prérequis

- Python 3.8+
- Django 4.2+
- Pillow (pour les avatars utilisateurs)
- Un serveur SMTP configuré pour l'envoi d'emails

## Installation

L'application est intégrée au projet principal. Aucune installation séparée n'est nécessaire.

Pour intégrer l'application Accounts dans un autre projet:

1. Copier le répertoire `apps/accounts` dans votre projet
2. Ajouter `'apps.accounts'` à la liste `INSTALLED_APPS` dans settings.py
3. Configurer `AUTH_USER_MODEL = 'accounts.CustomUser'` dans settings.py
4. Ajouter les middlewares personnalisés:
   ```python
   MIDDLEWARE = [
       # ...
       'apps.accounts.middleware.LastUserActivityMiddleware',
       'apps.accounts.middleware.SessionExpiryMiddleware', 
       'apps.accounts.middleware.RolePermissionMiddleware',
   ]
   ```
5. Inclure les URLs de l'application:
   ```python
   urlpatterns = [
       # ...
       path('accounts/', include('apps.accounts.urls')),
   ]
   ```
6. Configurer les paramètres email dans settings.py
7. Exécuter les migrations:
   ```
   python manage.py makemigrations accounts
   python manage.py migrate
   ```

## Structure de l'application

```
apps/accounts/
├── __init__.py
├── admin.py            # Configuration de l'interface d'administration
├── apps.py             # Configuration de l'application
├── forms.py            # Formulaires pour l'authentification et la gestion des profils
├── managers.py         # Gestionnaires personnalisés pour les modèles
├── middleware.py       # Middleware pour la sécurité et le contrôle d'accès
├── migrations/         # Migrations de base de données
├── models.py           # Modèles de données (User, Role, Permission, etc.)
├── signals.py          # Gestionnaires de signaux pour les événements système
├── templates/          # Templates HTML de l'interface utilisateur
│   └── accounts/
│       ├── login.html
│       ├── register.html
│       ├── profile.html
│       └── ...
├── tests/              # Tests unitaires et d'intégration
│   ├── __init__.py
│   ├── test_forms.py
│   ├── test_models.py
│   ├── test_views.py
│   └── test_integration.py
├── urls.py             # Configuration des URLs
└── views.py            # Vues pour les fonctionnalités
```

## Modèles principaux

### CustomUser
Extension du modèle User standard de Django avec des fonctionnalités supplémentaires:
- Email comme identifiant principal (USERNAME_FIELD = 'email')
- Association avec un rôle pour les permissions
- Historique des connexions
- Avatar et informations supplémentaires
- Clé d'activation pour la vérification par email

### Role
Définit les rôles disponibles dans le système:
- Nom et description du rôle
- Rôle par défaut pour les nouveaux utilisateurs
- Relations avec les permissions

### Permission
Gère les permissions granulaires pour contrôler l'accès aux fonctionnalités:
- Code unique pour la vérification programmatique
- Nom et description pour l'interface utilisateur
- Association avec des rôles via RolePermission

### UserProfile
Stocke les informations supplémentaires sur l'utilisateur:
- Informations personnelles (date de naissance, adresse, etc.)
- Préférences utilisateur
- Créé automatiquement pour chaque nouvel utilisateur

### UserLoginHistory
Enregistre les activités de connexion pour l'audit de sécurité:
- Horodatage de la connexion/déconnexion
- Adresse IP et user agent
- Statut (succès, échec, déconnexion)

## Flux d'authentification

1. **Inscription**:
   - L'utilisateur remplit le formulaire d'inscription
   - Un compte désactivé est créé
   - Un email avec un lien d'activation est envoyé

2. **Activation**:
   - L'utilisateur clique sur le lien d'activation dans l'email
   - Le compte est activé et l'utilisateur peut se connecter

3. **Connexion**:
   - L'utilisateur se connecte avec son email et mot de passe
   - La connexion est enregistrée dans UserLoginHistory
   - La dernière activité est mise à jour pour le suivi de session

4. **Contrôle d'accès**:
   - RolePermissionMiddleware vérifie les permissions pour chaque requête
   - Les vues peuvent être décorées avec @required_permission pour exiger des permissions spécifiques

5. **Expiration de session**:
   - SessionExpiryMiddleware vérifie l'inactivité de l'utilisateur
   - L'utilisateur est déconnecté après la période d'inactivité définie (SESSION_IDLE_TIMEOUT)

## Utilisation des permissions

Pour protéger une vue avec une permission spécifique:

```python
from apps.accounts.views import required_permission

@required_permission('can_view_dashboard')
def dashboard_view(request):
    # Cette vue n'est accessible qu'aux utilisateurs 
    # ayant la permission 'can_view_dashboard'
    return render(request, 'dashboard.html')
```

Pour vérifier les permissions dans un template:

```html
{% if user.has_permission('can_manage_users') %}
    <a href="{% url 'admin:users' %}" class="btn btn-primary">
        Gérer les utilisateurs
    </a>
{% endif %}
```

## Tests

L'application dispose d'une suite de tests complète:

```
python manage.py test apps.accounts
```

Les tests couvrent:
- Modèles et leurs relations
- Formulaires et validation
- Vues et flux d'authentification
- Middlewares et sécurité
- Intégration entre les composants

## Configuration

Paramètres configurables dans settings.py:

```python
# Durée d'inactivité avant déconnexion (en secondes)
SESSION_IDLE_TIMEOUT = 1800  # 30 minutes par défaut

# URL du site pour les emails d'activation
SITE_URL = 'https://example.com'

# Nom du site pour les communications
SITE_NAME = 'Mon Association'
```

## Évolutions futures

- Authentification à deux facteurs (2FA)
- Connexion via réseaux sociaux (OAuth)
- Interface d'administration des permissions améliorée
- Détection des comportements suspects
- Authentification par clé unique à usage unique (TOTP)

## Contribution

Pour contribuer à l'application accounts:
1. Créer une branche pour votre fonctionnalité (`git checkout -b feature/ma-fonctionnalite`)
2. Développer et tester votre code
3. S'assurer que tous les tests passent
4. Soumettre une pull request

## Licence

Cette application est développée dans le cadre du projet de gestion d'association et est soumise aux mêmes conditions de licence que le projet principal.