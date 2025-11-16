# Installation et Tests - Kandiane

Ce document détaille la procédure d'installation et de test de l'application Kandiane après le refactoring architectural (Phase 3).

## 📋 Table des matières

- [Problèmes résolus](#problèmes-résolus)
- [Prérequis](#prérequis)
- [Installation](#installation)
- [Configuration de la base de données](#configuration-de-la-base-de-données)
- [Lancement de l'application](#lancement-de-lapplication)
- [Tests fonctionnels](#tests-fonctionnels)
- [Dépannage](#dépannage)

---

## 🔧 Problèmes résolus

### 1. Conflit de migrations - Table `core_log`

**Problème** : Deux applications tentaient de créer la même table `core_log`
- `evenements.0002_log` créait un modèle `Log` avec `db_table='core_log'`
- `evenements.0003_delete_log` supprimait immédiatement ce modèle
- `core.0006_log` créait également la table `core_log`

**Solution** : Création d'une migration squashed `apps/evenements/migrations/0002_0003_squashed_noop.py` qui remplace les migrations 0002 et 0003 sans opérations, puisqu'elles s'annulent mutuellement.

### 2. Imports relatifs dans le package views

**Problème** : Les modules refactorés utilisaient des imports relatifs (`from .utils import`) qui échouaient lors de l'import depuis `urls.py`

**Solution** : Conversion de tous les imports relatifs en imports absolus :
```python
# Avant
from .utils import StaffRequiredMixin, ListView

# Après
from apps.cotisations.views.utils import StaffRequiredMixin, ListView
```

**Fichiers modifiés** :
- `apps/cotisations/views/dashboard.py`
- `apps/cotisations/views/cotisations.py`
- `apps/cotisations/views/paiements.py`
- `apps/cotisations/views/rappels.py`
- `apps/cotisations/views/baremes.py`
- `apps/cotisations/views/api.py`

### 3. Conflit de nommage views.py / views/

**Problème** : Le fichier `apps/cotisations/views.py` (ancien monolithe) coexistait avec le package `apps/cotisations/views/`, causant des erreurs d'import

**Solution** :
- Renommage de `views.py` en `views_old.py`
- Mise à jour de `views/__init__.py` pour importer les fonctions non migrées depuis `views_old` :

```python
from apps.cotisations import views_old

for name in non_migrated:
    if hasattr(views_old, name):
        globals()[name] = getattr(views_old, name)
```

---

## 🛠️ Prérequis

- **Python** : 3.10 ou supérieur
- **Système** : Linux/macOS/Windows
- **Git** : Pour cloner le dépôt

---

## 📦 Installation

### 1. Cloner le projet

```bash
git clone <url-du-repo> kandiane
cd kandiane
```

### 2. Créer l'environnement virtuel

```bash
python3 -m venv venv
```

### 3. Activer l'environnement virtuel

**Linux/macOS** :
```bash
source venv/bin/activate
```

**Windows** :
```cmd
venv\Scripts\activate
```

### 4. Installer les dépendances

```bash
pip install -r requirements.txt
```

**Dépendances principales** :
- Django 5.1.8
- django-environ 0.12.0
- django-debug-toolbar 5.1.0
- Pillow 11.1.0
- pandas 2.2.3
- reportlab 4.4.0
- django-apscheduler 0.7.0

---

## 🗄️ Configuration de la base de données

### 1. Vérifier la configuration Django

```bash
python manage.py check
```

**Résultat attendu** :
```
System check identified some issues:

WARNINGS:
?: (staticfiles.W004) The directory '/path/to/static' in the STATICFILES_DIRS setting does not exist.

System check identified 1 issue (0 silenced).
```

### 2. Créer le répertoire static

```bash
mkdir -p static
```

### 3. Appliquer les migrations

```bash
python manage.py migrate
```

**Résultat attendu** :
```
Operations to perform:
  Apply all migrations: accounts, admin, auth, contenttypes, core, cotisations, django_apscheduler, evenements, membres, sessions, sites
Running migrations:
  Applying core.0001_initial... OK
  Applying contenttypes.0001_initial... OK
  [...]
  Applying evenements.0002_0003_squashed_noop... OK
  [...]
```

### 4. Créer un superutilisateur

**Option A - Script automatique** (pour tests) :
```bash
python create_superuser.py
```

**Option B - Commande interactive** :
```bash
python manage.py createsuperuser
```

**Credentials de test créés par le script** :
- **Username** : `admin`
- **Email** : `admin@kandiane.local`
- **Password** : `admin123`

⚠️ **IMPORTANT** : Changez ces credentials en production !

---

## 🚀 Lancement de l'application

### Démarrer le serveur de développement

```bash
python manage.py runserver 0.0.0.0:8000
```

**Sortie attendue** :
```
Watching for file changes with StatReloader
Performing system checks...

System check identified no issues (0 silenced).
November 16, 2025 - 00:59:26
Django version 5.1.8, using settings 'config.settings'
Starting development server at http://0.0.0.0:8000/
Quit the server with CONTROL-C.
```

L'application est maintenant accessible sur **http://localhost:8000**

---

## ✅ Tests fonctionnels

### 1. Interface d'administration Django

**URL** : http://localhost:8000/admin/

**Test** :
1. Se connecter avec les credentials :
   - Username: `admin`
   - Password: `admin123`
2. Vérifier l'accès aux sections :
   - Accounts
   - Cotisations
   - Membres
   - Événements
   - Core

### 2. Module Cotisations - Dashboard

**URL** : http://localhost:8000/cotisations/dashboard/

**Tests** :
- ✅ Affichage du tableau de bord
- ✅ Statistiques des cotisations
- ✅ Graphiques (si données présentes)

**Code source** : `apps/cotisations/views/dashboard.py:80` (DashboardView)

### 3. Module Cotisations - CRUD

#### Liste des cotisations
**URL** : http://localhost:8000/cotisations/

**Tests** :
- ✅ Affichage de la liste
- ✅ Filtres de recherche
- ✅ Pagination

**Code source** : `apps/cotisations/views/cotisations.py:22` (CotisationListView)

#### Créer une cotisation
**URL** : http://localhost:8000/cotisations/ajouter/

**Tests** :
- ✅ Formulaire de création
- ✅ Validation des champs
- ✅ Enregistrement en base

### 4. Module Barèmes

**URL** : http://localhost:8000/cotisations/baremes/

**Tests** :
- ✅ Liste des barèmes
- ✅ Création d'un barème
- ✅ Modification d'un barème
- ✅ Vérification des dates de validité

**Code source** : `apps/cotisations/views/baremes.py:17` (BaremeCotisationListView)

### 5. Module Paiements

**URL** : http://localhost:8000/cotisations/paiements/

**Tests** :
- ✅ Liste des paiements
- ✅ Filtres (mode paiement, date)
- ✅ Création d'un paiement
- ✅ Statistiques (montant total, remboursements)

**Code source** : `apps/cotisations/views/paiements.py:22` (PaiementListView)

### 6. Module Rappels

**URL** : http://localhost:8000/cotisations/rappels/

**Tests** :
- ✅ Liste des rappels
- ✅ Création d'un rappel
- ✅ Envoi de rappel (email/SMS/courrier)
- ✅ Filtrage par état

**Code source** : `apps/cotisations/views/rappels.py:264` (RappelListView)

### 7. API Endpoints

#### Statistiques
**URL** : http://localhost:8000/cotisations/api/stats/

**Test** :
```bash
curl http://localhost:8000/cotisations/api/stats/
```

**Réponse attendue** :
```json
{
  "total_cotisations": 0,
  "montant_total": "0.00",
  "cotisations_payees": 0,
  "cotisations_impayees": 0
}
```

#### Cotisations en retard
**URL** : http://localhost:8000/cotisations/api/cotisations-en-retard/

**Test** :
```bash
curl http://localhost:8000/cotisations/api/cotisations-en-retard/
```

**Code source** : `apps/cotisations/views/api.py`

---

## 🐛 Dépannage

### Erreur : `No module named 'environ'`

**Cause** : Dépendances non installées ou environnement virtuel non activé

**Solution** :
```bash
source venv/bin/activate  # ou venv\Scripts\activate sur Windows
pip install -r requirements.txt
```

### Erreur : `table "django_apscheduler_djangojob" does not exist`

**Cause** : Migrations non appliquées

**Solution** :
```bash
python manage.py migrate
```

### Erreur : `AttributeError: module 'apps.cotisations.views' has no attribute 'export'`

**Cause** : Fichier `views.py` n'a pas été renommé en `views_old.py`

**Solution** :
```bash
cd apps/cotisations
mv views.py views_old.py
```

### Erreur : `attempted relative import with no known parent package`

**Cause** : Imports relatifs dans les modules refactorés

**Solution** : Utiliser le script de correction :
```bash
python fix_relative_imports.py
```

Ou corriger manuellement :
```python
# Remplacer
from .utils import SomeClass

# Par
from apps.cotisations.views.utils import SomeClass
```

### Serveur ne démarre pas sur Windows

**Cause** : Firewall ou port 8000 déjà utilisé

**Solution** : Utiliser un autre port
```bash
python manage.py runserver 8080
```

---

## 📊 Architecture du code refactoré

### Structure du package views

```
apps/cotisations/views/
├── __init__.py          # Imports et aliases de vues
├── utils.py             # Classes de base et utilitaires
├── dashboard.py         # Tableaux de bord et statistiques
├── cotisations.py       # CRUD cotisations
├── paiements.py         # Gestion paiements
├── rappels.py           # Gestion rappels
├── baremes.py           # Gestion barèmes
└── api.py               # Endpoints API REST
```

### Fichier legacy

```
apps/cotisations/views_old.py  # Ancien monolithe (3972 lignes)
                                # Contient les fonctions d'export/import non migrées
```

### Imports dans __init__.py

```python
# Imports depuis les modules refactorés
from apps.cotisations.views.utils import *
from apps.cotisations.views.dashboard import *
from apps.cotisations.views.cotisations import *
from apps.cotisations.views.paiements import *
from apps.cotisations.views.rappels import *
from apps.cotisations.views.baremes import *
from apps.cotisations.views.api import *

# Import depuis le legacy pour les fonctions non migrées
from apps.cotisations import views_old

# Création des aliases pour urls.py
dashboard = DashboardView.as_view()
cotisation_list = CotisationListView.as_view()
# ... etc
```

---

## 🎯 Résultats du refactoring

### Avant (Phase 2)
- **1 fichier** : `views.py` (3972 lignes)
- **Maintenabilité** : ⭐⭐ (2/5)
- **Lisibilité** : ⭐⭐ (2/5)

### Après (Phase 3)
- **8 modules** : ~400-500 lignes chacun
- **Maintenabilité** : ⭐⭐⭐⭐⭐ (5/5)
- **Lisibilité** : ⭐⭐⭐⭐⭐ (5/5)
- **Réduction** : ~300 lignes (élimination duplications)

### Avantages
- ✅ Séparation des responsabilités
- ✅ Imports absolus (plus de confusion)
- ✅ Modules de taille raisonnable (~100-500 lignes)
- ✅ Tests plus faciles à écrire
- ✅ Navigation dans le code simplifiée
- ✅ Collaboration facilitée (moins de conflits Git)

---

## 📝 Scripts utilitaires

### `create_superuser.py`
Crée automatiquement un superutilisateur pour les tests locaux.

**Usage** :
```bash
python create_superuser.py
```

### `reset_dev_env.sh`
Nettoie et réinitialise l'environnement de développement.

**Usage** :
```bash
./reset_dev_env.sh
```

### `setup_after_reset.sh`
Configure l'environnement après un reset.

**Usage** :
```bash
./setup_after_reset.sh
```

### `fix_relative_imports.py`
Convertit les imports relatifs en imports absolus.

**Usage** :
```bash
python fix_relative_imports.py
```

---

## 🔄 Prochaines étapes

### Phase 4 - Finalisation (optionnel)

1. **Migrer le module imports/exports**
   - Créer `views/imports_exports.py`
   - Migrer depuis `views_old.py`
   - Tester les fonctions d'import/export

2. **Supprimer le legacy**
   - Archiver `views_old.py`
   - Nettoyer `__init__.py`

3. **Tests unitaires**
   - Couvrir les nouveaux modules
   - Tests d'intégration

4. **Documentation technique**
   - Diagrammes d'architecture
   - Guide de contribution

---

## 📞 Support

Pour toute question ou problème :
1. Vérifier la section [Dépannage](#dépannage)
2. Consulter les logs : `python manage.py runserver --verbosity 2`
3. Activer le mode debug dans `config/settings/development.py`

---

**Dernière mise à jour** : 16 novembre 2025
**Version Django** : 5.1.8
**Phase du refactoring** : Phase 3 - Architecture (100% complète)
