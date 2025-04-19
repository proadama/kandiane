# Application Core

## Vue d'ensemble

L'application Core est le composant fondamental de notre système de gestion d'association. Elle fournit les fonctionnalités communes, les modèles de base et les utilitaires réutilisables par toutes les autres applications du projet.

## Fonctionnalités principales

- Modèle de base avec tracking automatique des dates (création, modification)
- Système de suppression logique (soft delete)
- Gestionnaire personnalisé pour les requêtes de modèles
- Middlewares de journalisation et de mode maintenance
- Mixins pour les vues avec contrôle d'accès
- Fonctions utilitaires pour la manipulation de fichiers et de slugs
- Templates de base avec Bootstrap

## Structure de l'application

```
core/
├── __init__.py
├── admin.py           # Configuration de l'admin Django
├── apps.py            # Configuration de l'application
├── managers.py        # Gestionnaires personnalisés
├── middleware.py      # Middlewares personnalisés
├── mixins.py          # Mixins pour les vues
├── models.py          # Modèles de base
├── signals.py         # Signaux et handlers
├── tests.py           # Tests unitaires
├── urls.py            # Configuration des URLs
├── utils.py           # Fonctions utilitaires
└── views.py           # Vues de base
```

## Composants principaux

### Modèles

#### BaseModel

`BaseModel` est un modèle abstrait qui fournit des champs communs et des fonctionnalités de base pour tous les modèles de l'application.

```python
from apps.core.models import BaseModel

class MonModele(BaseModel):
    nom = models.CharField(max_length=100)
    # autres champs spécifiques...
```

Champs automatiquement inclus :
- `created_at` - Date et heure de création
- `updated_at` - Date et heure de dernière modification
- `deleted_at` - Date et heure de suppression logique (si applicable)

Méthodes principales :
- `delete(hard=False)` - Suppression logique par défaut, physique si `hard=True`

#### Statut

Le modèle `Statut` est utilisé pour stocker les différents statuts qui peuvent être attribués à d'autres entités dans le système.

```python
from apps.core.models import Statut

# Récupérer un statut existant
statut_actif = Statut.objects.get(nom="Actif")

# Utiliser le statut dans un modèle
membre.statut = statut_actif
membre.save()
```

### Gestionnaires

#### BaseManager

`BaseManager` est un gestionnaire personnalisé qui filtre automatiquement les objets supprimés logiquement.

```python
# Par défaut, n'inclut pas les objets supprimés
objets = MonModele.objects.all()

# Inclut les objets supprimés
tous_les_objets = MonModele.objects.with_deleted()

# Uniquement les objets supprimés
objets_supprimes = MonModele.objects.only_deleted()
```

### Middlewares

#### RequestLogMiddleware

Middleware qui journalise les informations sur chaque requête HTTP.

Configuration dans settings :
```python
MIDDLEWARE = [
    # ...
    'apps.core.middleware.RequestLogMiddleware',
    # ...
]
```

#### MaintenanceModeMiddleware

Middleware pour activer facilement un mode maintenance sur l'application.

Configuration dans settings :
```python
MIDDLEWARE = [
    # ...
    'apps.core.middleware.MaintenanceModeMiddleware',
    # ...
]

# Pour activer le mode maintenance
MAINTENANCE_MODE = True
MAINTENANCE_CONTEXT = {
    'title': 'Site en maintenance',
    'message': 'Notre site est en cours de maintenance. Merci de revenir plus tard.'
}
```

### Mixins

#### StaffRequiredMixin

Mixin qui restreint l'accès aux utilisateurs avec le statut "staff".

```python
from apps.core.mixins import StaffRequiredMixin
from django.views.generic import TemplateView

class MaVueRestreinte(StaffRequiredMixin, TemplateView):
    template_name = 'ma_vue.html'
```

#### PermissionRequiredMixin

Mixin pour vérifier qu'un utilisateur possède une permission spécifique.

```python
from apps.core.mixins import PermissionRequiredMixin
from django.views.generic import ListView

class ListeUtilisateursView(PermissionRequiredMixin, ListView):
    permission_required = 'voir_utilisateurs'
    model = User
    template_name = 'liste_utilisateurs.html'
```

### Utilitaires

#### get_file_path

Fonction pour générer des chemins de fichier uniques avec UUID.

```python
from apps.core.utils import get_file_path
from django.db import models

class Document(models.Model):
    fichier = models.FileField(upload_to=get_file_path)
```

#### get_unique_slug

Fonction pour générer des slugs uniques pour un modèle.

```python
from apps.core.utils import get_unique_slug
from django.db import models

class Article(models.Model):
    titre = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, unique=True)
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = get_unique_slug(self, 'titre')
        super().save(*args, **kwargs)
```

## Vues principales

### HomeView

Vue de la page d'accueil.

### DashboardView

Vue du tableau de bord, accessible uniquement aux utilisateurs connectés.

## Templates

L'application inclut des templates de base :
- `layouts/base.html` - Template principal avec Bootstrap
- `includes/header.html` - En-tête du site
- `includes/footer.html` - Pied de page
- `includes/messages.html` - Affichage des messages flash
- `core/home.html` - Page d'accueil
- `core/dashboard.html` - Tableau de bord
- `core/maintenance.html` - Page de maintenance

## Tests

L'application inclut une suite complète de tests unitaires. Pour exécuter uniquement les tests de cette application :

```bash
python manage.py test apps.core
```

## Conventions

- Tous les modèles métier doivent hériter de `BaseModel`
- Utiliser la suppression logique (`model.delete()`) par défaut
- Préférer la suppression physique (`model.delete(hard=True)`) uniquement pour les données temporaires
- Documenter toutes les nouvelles fonctions avec des docstrings

## Documentation des composants

Pour plus de détails sur l'implémentation, consultez les commentaires et docstrings dans le code source.

## Dépendances

- Django 4.2.10
- django-environ 0.12.0
- django-debug-toolbar 5.1.0
- Pillow 11.1.0
- django-extensions 3.2.3