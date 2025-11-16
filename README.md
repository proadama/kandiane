# Kandiane - Système de Gestion Associative

Application Django complète pour la gestion d'une association : membres, cotisations, paiements, événements et comptabilité.

## 🚀 Démarrage rapide

### Installation

```bash
# Cloner le projet
git clone <url-du-repo> kandiane
cd kandiane

# Créer l'environnement virtuel
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# ou : venv\Scripts\activate  # Windows

# Installer les dépendances
pip install -r requirements.txt

# Créer le répertoire static
mkdir -p static

# Appliquer les migrations
python manage.py migrate

# Créer un superutilisateur (pour tests)
python create_superuser.py
# ou : python manage.py createsuperuser

# Démarrer le serveur
python manage.py runserver
```

**Accès** : http://localhost:8000

**Credentials de test** :
- Username: `admin`
- Password: `admin123`

---

## 📚 Documentation

### Pour commencer
- **[INSTALLATION_ET_TESTS.md](INSTALLATION_ET_TESTS.md)** - Guide complet d'installation et de test
  - Prérequis système
  - Procédure d'installation détaillée
  - Tests fonctionnels par module
  - Dépannage

### Documentation technique
- **[REFACTORING_PHASE3_NOTES.md](REFACTORING_PHASE3_NOTES.md)** - Notes techniques du refactoring
  - Architecture avant/après
  - Problèmes rencontrés et solutions
  - Description des modules
  - Métriques et leçons apprises

---

## 🏗️ Architecture

### Applications Django

```
apps/
├── accounts/           # Gestion des utilisateurs et authentification
├── core/              # Modèles et fonctionnalités de base (Statut, TypeMembre, etc.)
├── membres/           # Gestion des membres de l'association
├── cotisations/       # Gestion des cotisations et paiements (refactoré)
└── evenements/        # Gestion des événements
```

### Module cotisations (refactoré - Phase 3)

Le module cotisations a été refactoré d'un fichier monolithique de 3972 lignes en une architecture modulaire :

```
apps/cotisations/views/
├── __init__.py          # Imports et aliases de vues
├── utils.py             # Classes de base et utilitaires
├── dashboard.py         # Tableaux de bord et statistiques
├── cotisations.py       # CRUD cotisations
├── paiements.py         # Gestion des paiements
├── rappels.py           # Gestion des rappels
├── baremes.py           # Gestion des barèmes de cotisation
└── api.py               # Endpoints API REST
```

**Avantages** :
- ✅ Modules de taille raisonnable (~100-500 lignes)
- ✅ Séparation claire des responsabilités
- ✅ Maintenabilité +++++
- ✅ Tests plus faciles à écrire
- ✅ Moins de conflits Git

---

## 🎯 Fonctionnalités

### Gestion des membres
- Inscription et profils des membres
- Types de membres (adhérent, bienfaiteur, etc.)
- Historique d'activité
- Gestion de la corbeille (suppression logique)

### Gestion des cotisations
- **Dashboard** : Vue d'ensemble des cotisations et statistiques
- **Barèmes** : Gestion des tarifs par type de membre avec dates de validité
- **Cotisations** : Création, suivi, modification, suppression
- **Paiements** : Enregistrement des paiements (espèces, chèque, virement, carte)
- **Rappels** : Envoi de rappels automatiques (email, SMS, courrier)
- **Export/Import** : Export PDF, Excel / Import de cotisations en masse

### Gestion des événements
- Création et planification d'événements
- Suivi des participations
- Intégration avec les cotisations

### API REST
- Endpoints pour les statistiques
- Calcul de montants selon les barèmes
- Liste des cotisations en retard
- Envoi automatique de rappels

---

## 🔧 Technologies

### Backend
- **Django 5.1.8** - Framework web Python
- **Python 3.10+** - Langage de programmation
- **SQLite** - Base de données (développement)

### Packages principaux
- **django-environ** - Gestion des variables d'environnement
- **django-debug-toolbar** - Outils de débogage
- **Pillow** - Traitement d'images
- **pandas** - Manipulation de données
- **openpyxl** / **xlsxwriter** - Export Excel
- **reportlab** - Génération de PDF
- **django-apscheduler** - Tâches planifiées

Voir [requirements.txt](requirements.txt) pour la liste complète.

---

## 📂 Structure du projet

```
kandiane/
├── apps/                           # Applications Django
│   ├── accounts/                  # Utilisateurs et auth
│   ├── core/                      # Fonctionnalités de base
│   ├── membres/                   # Gestion membres
│   ├── cotisations/               # Gestion cotisations (refactoré)
│   └── evenements/                # Gestion événements
├── config/                         # Configuration Django
│   ├── settings/
│   │   ├── base.py               # Settings communs
│   │   ├── development.py        # Settings développement
│   │   └── production.py         # Settings production
│   ├── urls.py                    # URLs racine
│   └── wsgi.py                    # WSGI application
├── templates/                      # Templates globaux
├── static/                         # Fichiers statiques (CSS, JS, images)
├── media/                          # Fichiers uploadés
├── venv/                           # Environnement virtuel (non versionné)
├── db.sqlite3                      # Base de données SQLite (non versionné)
├── manage.py                       # Script de gestion Django
├── requirements.txt                # Dépendances Python
├── create_superuser.py             # Script création superuser
├── README.md                       # Ce fichier
├── INSTALLATION_ET_TESTS.md        # Guide d'installation détaillé
└── REFACTORING_PHASE3_NOTES.md     # Notes techniques refactoring
```

---

## 🧪 Tests

### Lancer les tests

```bash
# Tous les tests
python manage.py test

# Tests d'une application spécifique
python manage.py test apps.cotisations

# Avec pytest (recommandé)
pytest
```

### Vérification du code

```bash
# Vérifier la configuration Django
python manage.py check

# Vérifier les migrations
python manage.py makemigrations --dry-run --check
```

---

## 📊 Phases du refactoring

### ✅ Phase 1 - Sécurité (100%)
- Validation des entrées utilisateur
- Protection CSRF
- Sanitisation des données
- Gestion sécurisée des fichiers

### ✅ Phase 2 - Performance (100%)
- Optimisation des requêtes SQL (select_related, prefetch_related)
- Indexation des champs fréquemment filtrés
- Pagination efficace
- Cache des requêtes coûteuses

### ✅ Phase 3 - Architecture (100%)
- Refactoring du module cotisations (3972 lignes → 8 modules)
- Séparation des responsabilités
- Imports absolus
- Structure modulaire maintenable

### ⏳ Phase 4 - Finalisation (optionnel)
- [ ] Migration du module imports_exports
- [ ] Suppression de views_old.py
- [ ] Tests unitaires (80%+ couverture)
- [ ] Documentation API complète

---

## 🛠️ Scripts utilitaires

### create_superuser.py
Crée automatiquement un superutilisateur pour les tests :

```bash
python create_superuser.py
```

Credentials créés :
- Username: `admin`
- Email: `admin@kandiane.local`
- Password: `admin123`

### reset_dev_env.sh
Nettoie et réinitialise l'environnement de développement :

```bash
./reset_dev_env.sh
```

### setup_after_reset.sh
Configure l'environnement après un reset :

```bash
./setup_after_reset.sh
```

### fix_relative_imports.py
Convertit les imports relatifs en imports absolus :

```bash
python fix_relative_imports.py
```

---

## 🌐 URLs principales

### Interface d'administration
- http://localhost:8000/admin/

### Module Cotisations
- http://localhost:8000/cotisations/dashboard/ - Dashboard
- http://localhost:8000/cotisations/ - Liste des cotisations
- http://localhost:8000/cotisations/baremes/ - Gestion des barèmes
- http://localhost:8000/cotisations/paiements/ - Liste des paiements
- http://localhost:8000/cotisations/rappels/ - Liste des rappels

### API
- http://localhost:8000/cotisations/api/stats/ - Statistiques
- http://localhost:8000/cotisations/api/cotisations-en-retard/ - Cotisations en retard

---

## 📝 Contribuer

### Standards de code

- **PEP 8** : Style de code Python
- **Imports absolus** : Toujours utiliser `from apps.module import`
- **Docstrings** : Documenter les classes et fonctions
- **Type hints** : Utiliser les annotations de type (Python 3.10+)

### Workflow Git

1. Créer une branche pour chaque fonctionnalité
2. Commits atomiques avec messages descriptifs
3. Tests avant de pousser
4. Pull request pour review

---

## 🐛 Dépannage

Consultez [INSTALLATION_ET_TESTS.md](INSTALLATION_ET_TESTS.md#dépannage) pour les problèmes courants :

- ModuleNotFoundError
- Erreurs de migration
- Problèmes d'imports
- Serveur qui ne démarre pas

---

## 📄 Licence

[À définir]

---

## 👥 Auteurs

- Équipe de développement Kandiane
- Refactoring Phase 3 : Claude Code (Novembre 2025)

---

## 📞 Support

Pour toute question :
1. Consulter la [documentation](INSTALLATION_ET_TESTS.md)
2. Vérifier les [notes techniques](REFACTORING_PHASE3_NOTES.md)
3. Activer le mode debug et consulter les logs

---

**Dernière mise à jour** : 16 novembre 2025
**Version Django** : 5.1.8
**Statut** : Phase 3 Architecture - 100% complète ✅
