# Application "Membres" - Gestion d'Association

## Description

L'application "Membres" est un module central du système de gestion d'association permettant d'administrer efficacement la base de membres de votre organisation. Elle s'intègre avec l'application "Accounts" pour fournir une gestion unifiée des membres et de leurs comptes utilisateurs dans l'application.

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![Status](https://img.shields.io/badge/status-stable-green)

## Table des matières

- [Fonctionnalités](#fonctionnalités)
- [Architecture technique](#architecture-technique)
- [Installation et configuration](#installation-et-configuration)
- [Guide d'utilisation](#guide-dutilisation)
- [Intégration avec d'autres modules](#intégration-avec-dautres-modules)
- [Personnalisation et extension](#personnalisation-et-extension)
- [Fonctionnalités avancées](#fonctionnalités-avancées)
- [Tests](#tests)
- [FAQ et résolution de problèmes](#faq-et-résolution-de-problèmes)
- [Roadmap](#roadmap)

## Fonctionnalités

### Gestion des membres
- ✅ **Création, modification et suppression** de membres
- ✅ **Recherche avancée** avec filtres multiples (nom, email, type, statut, etc.)
- ✅ **Historisation** de toutes les modifications
- ✅ **Suppression logique** avec corbeille pour restauration
- ✅ **Dashboard** avec statistiques et visualisations

### Gestion des types de membres
- ✅ **Types personnalisables** (actif, honoraire, bienfaiteur, etc.)
- ✅ **Association temporelle** entre membres et types
- ✅ **Historique des types** par membre
- ✅ **Statistiques par type** de membre

### Import/Export
- ✅ **Import CSV/Excel** avec mappage de colonnes
- ✅ **Export CSV/Excel** des résultats de recherche
- ✅ **Export de statistiques** pour rapports

### Intégration Membres-Utilisateurs
- ✅ **Synchronisation bidirectionnelle** entre membres et comptes utilisateurs
- ✅ **Création automatique** de comptes lors de l'ajout de membres
- ✅ **Gestion unifiée** des données personnelles

## Architecture technique

### Modèles principaux
- `Membre` : Informations personnelles et associatives sur un membre
- `TypeMembre` : Catégories de membres (ex: actif, honoraire, bienfaiteur)
- `MembreTypeMembre` : Liaison temporelle entre un membre et un type
- `HistoriqueMembre` : Suivi complet des modifications

### Gestionnaires personnalisés
- `MembreManager` : Méthodes spécifiques pour la recherche et le filtrage
- `TypeMembreManager` : Gestion des types de membres
- `MembreTypeMembreManager` : Gestion des associations membres-types

### Vues clés
- `DashboardView` : Statistiques et visualisations
- `MembreListView` : Liste filtrée des membres
- `MembreDetailView` : Informations détaillées sur un membre
- `MembreCorbeillePage` : Gestion des membres supprimés

### Fonctionnalités sous-jacentes
- Suppression logique (soft delete)
- Validation des dates
- Calcul automatique de l'âge
- Synchronisation avec les comptes utilisateurs

## Installation et configuration

### Prérequis
- Django 5.1+
- Python 3.10+
- Modules: django-environ, Pillow, openpyxl

### Configuration

1. Assurez-vous que l'application `membres` est incluse dans `INSTALLED_APPS` :

```python
INSTALLED_APPS = [
    # ...
    'apps.core',
    'apps.accounts',
    'apps.membres',
    # ...
]
```

2. Configurez les URLs dans votre fichier `urls.py` principal :

```python
urlpatterns = [
    # ...
    path('membres/', include('apps.membres.urls')),
    # ...
]
```

3. Exécutez les migrations :

```bash
python manage.py makemigrations
python manage.py migrate
```

## Guide d'utilisation

### Dashboard des membres

Accédez au tableau de bord pour une vue d'ensemble de vos membres :
```
/membres/
```

Le dashboard fournit :
- Statistiques globales (total membres, membres actifs, etc.)
- Visualisations graphiques (répartition par type, par âge, etc.)
- Liste des adhésions récentes

### Gestion des membres

- **Liste des membres** : `/membres/liste/`
- **Ajout d'un membre** : `/membres/nouveau/`
- **Détail d'un membre** : `/membres/<id>/`
- **Modification** : `/membres/<id>/modifier/`
- **Suppression** : `/membres/<id>/supprimer/`

### Types de membres

- **Liste des types** : `/membres/types/`
- **Ajout d'un type** : `/membres/types/nouveau/`
- **Modification** : `/membres/types/<id>/modifier/`

### Corbeille et restauration

- **Voir les membres supprimés** : `/membres/corbeille/`
- **Restaurer un membre** : Action disponible depuis la corbeille
- **Supprimer définitivement** : Action disponible depuis la corbeille

### Import/Export

- **Import de membres** : `/membres/importer/`
- **Export de membres** : Options disponibles depuis la liste

## Intégration avec d'autres modules

### Application Accounts

L'application `membres` est synchronisée avec l'application `accounts` :
- La création d'un membre peut générer automatiquement un compte utilisateur
- La création d'un utilisateur génère automatiquement un membre associé
- Les modifications de données personnelles sont répliquées entre les deux entités

### Application Core

L'application utilise les fonctionnalités de base fournies par `core` :
- `BaseModel` pour la gestion de la suppression logique
- `Statut` pour les différents états des membres
- Mixins pour les contrôles d'accès et les vues spécifiques

### Intégrations futures

Des points d'extension sont prévus pour :
- **Cotisations** : Gestion des cotisations liées aux membres
- **Événements** : Gestion des inscriptions des membres aux événements
- **Documents** : Stockage de documents liés aux membres

## Personnalisation et extension

### Types de membres personnalisés

Vous pouvez créer des types de membres spécifiques à votre organisation via l'interface d'administration ou la vue dédiée.

### Champs personnalisés

Pour ajouter des champs supplémentaires au modèle `Membre` :

1. Créez une migration pour ajouter les nouveaux champs
2. Mettez à jour le formulaire `MembreForm`
3. Mettez à jour les templates concernés

### Statistiques personnalisées

Vous pouvez étendre `DashboardView` pour ajouter vos propres statistiques et visualisations.

## Fonctionnalités avancées

### Suppression logique et Corbeille

L'application implémente une approche hybride :
- Suppression logique au niveau du modèle (`deleted_at`)
- Interface Corbeille pour voir et restaurer les éléments supprimés

#### Comment ça fonctionne

1. Les éléments "supprimés" sont marqués avec un timestamp dans `deleted_at`
2. Ils n'apparaissent plus dans les requêtes standard
3. Ils sont accessibles via la corbeille ou l'administration
4. Ils peuvent être restaurés ou supprimés définitivement

### Synchronisation Membres-Utilisateurs

La synchronisation bidirectionnelle est gérée par des signaux Django :
- `post_save` sur `CustomUser` crée/met à jour un `Membre`
- `post_save` sur `Membre` crée/met à jour un `CustomUser` (si option activée)

## Tests

L'application inclut plusieurs tests pour valider son fonctionnement :

- **Test MEM-01** : Test du tableau de bord des membres
- **Test MEM-02** : Test de la liste des membres avec filtres
- **Test MEM-03** : Test de création d'un nouveau membre
- **Test MEM-04** : Test de modification d'un membre
- **Test MEM-05** : Test de suppression logique d'un membre
- **Test MEM-06** : Test de restauration d'un membre supprimé
- **Test MEM-07** : Test de gestion des types de membres
- **Test MEM-08** : Test d'import et export de membres
- **Test MEM-09** : Test de vérification de l'historique des membres

Pour exécuter les tests :

```bash
python manage.py test apps.membres
```

## FAQ et résolution de problèmes

### Q: Un membre créé n'a pas de compte utilisateur associé

**R:** Assurez-vous que :
1. L'option "Créer un compte utilisateur" est cochée lors de la création
2. Les signaux sont correctement activés dans `apps/membres/apps.py` et `apps/accounts/apps.py`
3. Aucune erreur ne se produit lors de la création du compte

### Q: La corbeille n'affiche pas les membres supprimés

**R:** Vérifiez que :
1. La suppression logique fonctionne correctement (le champ `deleted_at` est rempli)
2. Le gestionnaire `only_deleted()` retourne correctement les objets supprimés
3. Les mixins `TrashViewMixin` et `RestoreViewMixin` sont correctement configurés

### Q: Après modification, la redirection ne fonctionne pas correctement

**R:** Modifiez la méthode `form_valid` de `MembreUpdateView` pour rediriger vers la destination souhaitée :

```python
def form_valid(self, form):
    membre = form.save()
    messages.success(self.request, _(f"Le membre {membre.nom_complet} a été modifié avec succès."))
    return redirect('membres:membre_liste')  # Redirection vers la liste
```

## Roadmap

### Améliorations prévues

- 🔲 **Interface de corbeille améliorée** avec restauration par lot
- 🔲 **Filtres de recherche avancés** supplémentaires
- 🔲 **Dashboard interactif** avec filtres dynamiques
- 🔲 **Gestion des données RGPD** (exports, anonymisation)
- 🔲 **Carte interactive** des membres
- 🔲 **Système de tags** pour catégoriser les membres
- 🔲 **Importation améliorée** avec mise à jour des données existantes

### Intégrations futures

- 🔲 **Module Cotisations** : Gestion des paiements et des rappels
- 🔲 **Module Événements** : Inscriptions et présences
- 🔲 **Module Documents** : Stockage de documents par membre
- 🔲 **Module Notifications** : Communications automatisées

---

Développé dans le cadre du projet de gestion d'association.  
Version: 1.0.0 | Dernière mise à jour: Avril 2025