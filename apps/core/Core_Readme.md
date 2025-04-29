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

# README - Séparation des statuts membres et cotisations

## Problématique

Dans le système de gestion d'association, les entités "Membre" et "Cotisation" partageaient une même table de statuts (`Statut`), ce qui créait une confusion lors de la création/modification des cotisations. Les formulaires affichaient tous les statuts disponibles, y compris ceux spécifiques aux membres qui n'avaient pas de sens pour les cotisations.

## Solution implémentée

Nous avons ajouté un champ `type_entite` au modèle `Statut` pour catégoriser les statuts selon leur utilisation. Cette approche conserve l'avantage d'une table unique tout en permettant de filtrer les statuts selon le contexte d'utilisation.

## Modifications effectuées

### 1. Modèle Statut

Ajout d'un champ `type_entite` pour différencier les types de statuts :

```python
# apps/core/models.py
class Statut(BaseModel):
    TYPE_CHOICES = [
        ('global', _('Global')),
        ('membre', _('Membre')),
        ('cotisation', _('Cotisation')),
        ('paiement', _('Paiement')),
        ('evenement', _('Événement')),
    ]
    
    nom = models.CharField(max_length=50, unique=True, verbose_name=_("Nom"))
    description = models.TextField(null=True, blank=True, verbose_name=_("Description"))
    type_entite = models.CharField(
        max_length=20, 
        choices=TYPE_CHOICES,
        default='global',
        verbose_name=_("Type d'entité")
    )
    
    # Méthodes pour filtrer les statuts
    @classmethod
    def pour_membres(cls):
        """Retourne les statuts applicables aux membres."""
        return cls.objects.filter(Q(type_entite='membre') | Q(type_entite='global'))
    
    @classmethod
    def pour_cotisations(cls):
        """Retourne les statuts applicables aux cotisations."""
        return cls.objects.filter(Q(type_entite='cotisation') | Q(type_entite='global'))
```

### 2. Migration de la base de données

Migration créée pour ajouter le champ et classifier les statuts existants :

```python
# apps/core/migrations/0002_alter_statut_options_statut_type_entite.py
def classifier_statuts_existants(apps, schema_editor):
    Statut = apps.get_model('core', 'Statut')
    
    # Mapping des statuts selon leur usage prévu
    statuts_membres = ['Actif', 'En attente', 'Suspendu', 'Désactivé', 'Honoraire']
    statuts_cotisations = ['En attente de paiement', 'Payée', 'En retard', 'Annulée']
    statuts_paiements = ['Validé', 'En attente', 'Annulé', 'Rejeté']
    
    # Mettre à jour par nom (case insensitive)
    for statut in Statut.objects.all():
        nom_lower = statut.nom.lower()
        if any(s.lower() in nom_lower for s in statuts_membres):
            statut.type_entite = 'membre'
        elif any(s.lower() in nom_lower for s in statuts_cotisations):
            statut.type_entite = 'cotisation'
        elif any(s.lower() in nom_lower for s in statuts_paiements):
            statut.type_entite = 'paiement'
        statut.save()
```

### 3. Mise à jour des formulaires

#### Formulaire des membres

```python
# apps/membres/forms.py
def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    
    # Filtrer les statuts pour n'afficher que ceux applicables aux membres
    self.fields['statut'].queryset = Statut.pour_membres()
```

#### Formulaire des cotisations

```python
# apps/cotisations/forms.py
def __init__(self, *args, **kwargs):
    self.user = kwargs.pop('user', None)
    super().__init__(*args, **kwargs)
    
    # Filtrer les statuts pour n'afficher que ceux applicables aux cotisations
    self.fields['statut'].queryset = Statut.pour_cotisations()
```

### 4. Tests unitaires

Tests pour valider le bon fonctionnement de la catégorisation des statuts :

```python
def test_pour_membres(self):
    """Test que pour_membres retourne les statuts corrects"""
    statuts = Statut.pour_membres()
    self.assertTrue(statuts.filter(nom="Statut global").exists())
    self.assertTrue(statuts.filter(nom="Statut membre").exists())
    self.assertFalse(statuts.filter(nom="Statut cotisation").exists())

def test_pour_cotisations(self):
    """Test que pour_cotisations retourne les statuts corrects"""
    statuts = Statut.pour_cotisations()
    self.assertTrue(statuts.filter(nom="Statut global").exists())
    self.assertTrue(statuts.filter(nom="Statut cotisation").exists())
    self.assertFalse(statuts.filter(nom="Statut membre").exists())
```

## Comment ça fonctionne

1. **Catégorisation** : Chaque statut est maintenant associé à un type d'entité ('membre', 'cotisation', 'paiement', 'global', etc.)
2. **Filtrage automatique** : Les formulaires utilisent les méthodes `pour_membres()` et `pour_cotisations()` pour n'afficher que les statuts pertinents
3. **Statuts globaux** : Les statuts de type 'global' sont disponibles pour toutes les entités
4. **Interface d'administration** : Les statuts peuvent être facilement gérés par type dans l'interface d'administration

## Recommandations pour l'utilisation

1. **Création de nouveaux statuts**
   - Utilisez toujours le type d'entité approprié lors de la création de nouveaux statuts
   - Réservez le type 'global' pour les statuts véritablement applicables à toutes les entités

2. **Statuts par défaut**
   - Pour les membres : 'Actif', 'En attente', 'Suspendu', 'Désactivé', 'Honoraire'
   - Pour les cotisations : 'En attente de paiement', 'Payée', 'En retard', 'Annulée'
   - Pour les paiements : 'Validé', 'En attente', 'Annulé', 'Rejeté'

3. **Extension à d'autres entités**
   - La solution est conçue pour être facilement étendue à d'autres entités comme les événements, les documents, etc.
   - Il suffit d'ajouter un nouveau type dans `TYPE_CHOICES` et une méthode correspondante (ex: `pour_evenements()`)

## Avantages de cette implémentation

1. **Facilité d'utilisation** : Les utilisateurs ne voient que les statuts pertinents dans chaque formulaire
2. **Flexibilité** : La solution permet d'avoir des statuts spécifiques par entité ainsi que des statuts communs
3. **Évolutivité** : Il est facile d'étendre le système à de nouvelles entités
4. **Maintenance simplifiée** : Une seule table à gérer plutôt que des tables séparées pour chaque type de statut
5. **Migration douce** : La modification a été réalisée sans impact sur les données existantes

En résumé, cette implémentation répond efficacement au problème tout en préservant la simplicité de la structure de données et en offrant une flexibilité pour les évolutions futures.

## Dépendances

- Django 4.2.10
- django-environ 0.12.0
- django-debug-toolbar 5.1.0
- Pillow 11.1.0
- django-extensions 3.2.3