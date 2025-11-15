# 🔧 Kandiane - Plan de Refactoring et Corrections

**Date de début** : 2025-11-15
**Date dernière mise à jour** : 2025-11-15
**Statut global** : 🟡 En cours - Phase 2 terminée
**Problèmes identifiés** : 60+

---

## 📊 Vue d'ensemble

| Catégorie | Total | Complétés | En cours | À faire |
|-----------|-------|-----------|----------|---------|
| 🚨 Critique | 8 | 8 | 0 | 0 |
| 🟠 Haute priorité | 10 | 5 | 0 | 5 |
| 🟡 Moyenne priorité | 15 | 3 | 0 | 12 |
| 🟢 Maintenance | 20+ | 0 | 0 | 20+ |
| **TOTAL** | **53+** | **16** | **0** | **37+** |

---

## ✅ **PHASES COMPLÉTÉES**

### 🎯 Phase 1 : Sécurité critique et nettoyage (TERMINÉE)
- Date : 2025-11-15
- Commit : 96e6d43
- Statut : ✅ 100% complété

### 🎯 Phase 2 : Performance et qualité du code (TERMINÉE)
- Date : 2025-11-15
- Statut : ✅ 100% complété

---

## 🚨 CRITIQUE - À corriger immédiatement

### ✅ SEC-01: Secrets hardcodés dans settings.py
- **Fichier** : `config/settings.py:23, 137` (supprimé)
- **Problème** : SECRET_KEY et EMAIL_HOST_PASSWORD exposés en clair
- **Solution appliquée** :
  - ✅ Créé `.env` et `.env.example`
  - ✅ Migré vers django-environ
  - ✅ Supprimé secrets du code
  - ✅ Généré nouvelle SECRET_KEY
  - ✅ Supprimé ancien config/settings.py
- **Statut** : ✅ **CORRIGÉ**

### ✅ SEC-02: DEBUG activé en production
- **Fichier** : `config/settings/base.py`, `development.py`, `production.py`
- **Solution appliquée** :
  - ✅ DEBUG configurable via environnement
  - ✅ DEBUG=False par défaut en production.py
  - ✅ Logging configuré par environnement
- **Statut** : ✅ **CORRIGÉ**

### ✅ SEC-03: ALLOWED_HOSTS vide
- **Fichier** : `config/settings/development.py:11`, `production.py:10`
- **Solution appliquée** :
  - ✅ ALLOWED_HOSTS configurable via .env
  - ✅ Valeurs par défaut sécurisées
- **Statut** : ✅ **CORRIGÉ**

### ✅ SEC-04: Base de données en production dans Git
- **Fichier** : `db.sqlite3.old` (SUPPRIMÉ)
- **Solution appliquée** :
  - ✅ Fichier supprimé du repository
  - ✅ Ajouté à .gitignore
- **Statut** : ✅ **CORRIGÉ**

### ✅ CONF-01: Système de settings dupliqué
- **Fichiers** : `config/settings.py` (SUPPRIMÉ) ET `config/settings/`
- **Solution appliquée** :
  - ✅ Choisi système modulaire (settings/)
  - ✅ Migré toute config vers settings/
  - ✅ Supprimé settings.py racine → settings.py.deprecated
  - ✅ DJANGO_SETTINGS_MODULE configuré
- **Statut** : ✅ **CORRIGÉ**

### ✅ CODE-01: Répertoires backup dans le code
- **Fichiers** : (TOUS SUPPRIMÉS - 200+ fichiers)
  - ✅ `apps/cotisations_backup_20250524/`
  - ✅ `backup_rollback_e56db6f_20250524_162011/`
  - ✅ `sauvegarde_avant_rollback_20250524_160059/`
- **Solution appliquée** :
  - ✅ Supprimé tous les backups du repository
  - ✅ Ajouté pattern *_backup_* à .gitignore
- **Statut** : ✅ **CORRIGÉ**

### ✅ CODE-02: Fichiers .backup/.old/.copy dispersés
- **Fichiers** : 17 fichiers supprimés
- **Solution appliquée** :
  - ✅ Tous les fichiers .backup/.old/.copy supprimés
  - ✅ Patterns ajoutés à .gitignore
- **Statut** : ✅ **CORRIGÉ**

### ✅ CONF-02: .env.example manquant
- **Fichier** : `.env.example` (CRÉÉ)
- **Problème** : Impossible pour nouveaux devs de savoir quelles variables sont nécessaires
- **Risque** : Setup difficile, erreurs de config
- **Solution** :
  - Créer .env.example complet
  - Documenter chaque variable
  - Ajouter instructions dans README
- **Statut** : ⏳ À faire

---

## 🟠 HAUTE PRIORITÉ

### ARCH-01: Fichier views.py gigantesque (cotisations)
- **Fichier** : `apps/cotisations/views.py` (3,970 lignes)
- **Problème** : Violation du principe de responsabilité unique
- **Impact** : Maintenance difficile, tests complexes
- **Solution** :
  - Diviser en modules : dashboard.py, crud.py, api.py, exports.py, imports.py
  - Créer package views/
  - Maintenir rétrocompatibilité imports
- **Statut** : ⏳ À faire

### ARCH-02: Fichier views.py gigantesque (membres)
- **Fichier** : `apps/membres/views.py` (1,737 lignes)
- **Problème** : Violation du principe de responsabilité unique
- **Impact** : Maintenance difficile, tests complexes
- **Solution** :
  - Diviser en modules : dashboard.py, crud.py, exports.py, imports.py, trash.py
  - Créer package views/
  - Maintenir rétrocompatibilité imports
- **Statut** : ⏳ À faire

### PERF-01: Index de base de données manquants
- **Fichier** : `apps/membres/models.py`, `apps/cotisations/models.py`, etc.
- **Problème** : Requêtes lentes sur foreign keys et champs filtrés
- **Impact** : Performance dégradée avec croissance des données
- **Solution** :
  - Ajouter index sur : statut, utilisateur, deleted_at, created_at, updated_at
  - Générer migrations
  - Tester performance avant/après
- **Statut** : ⏳ À faire

### PERF-02: Requêtes N+1
- **Fichier** : `apps/membres/views.py`, `apps/cotisations/views.py`
- **Problème** : Manque select_related() et prefetch_related()
- **Impact** : Centaines de requêtes DB au lieu de quelques-unes
- **Solution** :
  - Auditer toutes les vues
  - Ajouter select_related() pour FK
  - Ajouter prefetch_related() pour M2M
  - Utiliser django-debug-toolbar pour vérifier
- **Statut** : ⏳ À faire

### PERF-03: Écritures DB excessives (derniere_connexion)
- **Fichier** : `apps/accounts/middleware.py:26-28`
- **Problème** : Update user à CHAQUE requête
- **Impact** : Milliers d'écritures DB inutiles
- **Solution** :
  - Throttler à max 1 update par session
  - Ou utiliser cache Redis/Memcached
  - Ou batch updates périodiques
- **Statut** : ⏳ À faire

### PERF-04: Requêtes inefficaces dupliquées
- **Fichier** : `apps/membres/views.py:213-222, 1169-1177`
- **Problème** : Même requête complexe exécutée plusieurs fois
- **Impact** : CPU/DB surchargés
- **Solution** :
  - Mettre en cache le résultat
  - Ou créer vue matérialisée DB
  - Ou utiliser Redis pour cache
- **Statut** : ⏳ À faire

### CODE-03: Imports dupliqués
- **Fichier** : `apps/cotisations/views.py`, autres
- **Problème** : Même import multiple fois dans un fichier
- **Impact** : Code non professionnel, lint fails
- **Solution** :
  - Utiliser isort pour organiser imports
  - Configurer pre-commit hook
  - Nettoyer tous les fichiers
- **Statut** : ⏳ À faire

### CODE-04: URL patterns dupliquées
- **Fichier** : `config/urls.py:33-34`
- **Problème** : Même URLconf inclus deux fois
- **Impact** : Confusion, potentiels conflits
- **Solution** :
  - Garder uniquement version avec namespace
  - Vérifier que tout fonctionne
  - Supprimer duplicate
- **Statut** : ⏳ À faire

### CONF-03: Settings contradictoires
- **Fichier** : `config/settings/base.py`
- **Problème** : LOGIN_URL et SESSION_COOKIE_AGE définis deux fois
- **Impact** : Comportement imprévisible
- **Solution** :
  - Garder une seule définition
  - Vérifier toutes les settings
  - Documenter choix
- **Statut** : ⏳ À faire

### DB-01: SQLite pour production
- **Fichier** : `config/settings.py:78-86`
- **Problème** : SQLite inadapté pour production multi-utilisateurs
- **Impact** : Locking issues, pas de concurrence
- **Solution** :
  - Configurer PostgreSQL pour production
  - Garder SQLite pour dev/tests
  - Documenter migration
- **Statut** : ⏳ À faire

---

## 🟡 PRIORITÉ MOYENNE

### SEC-05: CSRF_COOKIE_HTTPONLY manquant
- **Fichier** : Settings
- **Problème** : Cookie CSRF accessible en JavaScript
- **Risque** : Réduction protection XSS
- **Solution** : Ajouter CSRF_COOKIE_HTTPONLY = True
- **Statut** : ⏳ À faire

### SEC-06: SECURE_REFERRER_POLICY manquant
- **Fichier** : Settings
- **Problème** : Pas de politique de referrer
- **Risque** : Fuite d'informations
- **Solution** : Configurer SECURE_REFERRER_POLICY
- **Statut** : ⏳ À faire

### SEC-07: Gestion d'erreurs silencieuse
- **Fichier** : `apps/membres/views.py:234-239`, autres
- **Problème** : Exceptions catchées sans logging
- **Impact** : Bugs cachés, debugging difficile
- **Solution** :
  - Ajouter logging approprié
  - Ou propager exceptions
  - Configurer Sentry/monitoring
- **Statut** : ⏳ À faire

### SEC-08: HTML dans messages sans escaping
- **Fichier** : `apps/accounts/middleware.py:147-156`
- **Problème** : HTML marqué safe
- **Risque** : Potentiel XSS si input utilisateur
- **Solution** :
  - Utiliser templates pour messages
  - Ou vérifier que jamais d'input utilisateur
  - Ou échapper proprement
- **Statut** : ⏳ À faire

### ARCH-03: Anti-pattern binding dynamique
- **Fichier** : `apps/membres/views.py:659-664, 715-719, 1493-1497`
- **Problème** : Méthodes bindées dynamiquement
- **Impact** : Code difficile à comprendre, non testable
- **Solution** :
  - Utiliser @property dans modèle
  - Ou @cached_property
  - Refactorer logique dans modèle
- **Statut** : ⏳ À faire

### ARCH-04: Couplage fort avec try/except
- **Fichier** : `apps/membres/views.py:204-236, 360-389`
- **Problème** : Import conditionnel avec try/except
- **Impact** : Logique métier dispersée
- **Solution** :
  - Utiliser signals Django
  - Ou service layer
  - Centraliser logique métier
- **Statut** : ⏳ À faire

### CODE-05: Nommage incohérent français/anglais
- **Fichier** : Partout dans le code
- **Problème** : Mélange français (membre, cotisation) et anglais (views, models)
- **Impact** : Cohérence du code
- **Solution** :
  - Standardiser sur anglais pour code
  - Garder français pour UI/templates
  - Documenter convention
- **Statut** : ⏳ À faire

### CODE-06: Nommage incohérent pk vs id
- **Fichier** : URL patterns variés
- **Problème** : Tantôt <pk>, tantôt <id>
- **Impact** : Confusion
- **Solution** :
  - Standardiser sur <pk> (convention Django)
  - Refactorer URLs
  - Mettre à jour vues
- **Statut** : ⏳ À faire

### CODE-07: Documentation manquante
- **Fichier** : La plupart des vues et méthodes
- **Problème** : Pas de docstrings
- **Impact** : Onboarding difficile, maintenance
- **Solution** :
  - Ajouter docstrings Google style
  - Documenter paramètres et retours
  - Générer documentation avec Sphinx
- **Statut** : ⏳ À faire

### CODE-08: Magic numbers
- **Fichier** : `apps/accounts/middleware.py:25, 99`
- **Problème** : Valeurs hardcodées (15, 1800)
- **Impact** : Difficile à maintenir et tester
- **Solution** :
  - Extraire vers settings
  - Nommer les constantes
  - Documenter
- **Statut** : ⏳ À faire

### CONF-04: Ordre middlewares incorrect
- **Fichier** : `config/settings.py:50`
- **Problème** : Custom middleware avant Django core
- **Impact** : Comportement imprévisible
- **Solution** :
  - Réorganiser selon best practices Django
  - TemporaryPasswordMiddleware après AuthenticationMiddleware
  - Tester exhaustivement
- **Statut** : ⏳ À faire

### CONF-05: Logging configurations multiples
- **Fichier** : `base.py`, `development.py`, `production.py`
- **Problème** : 3 configs différentes, priorité incertaine
- **Impact** : Logs imprévisibles
- **Solution** :
  - Consolider config logging
  - Utiliser dictConfig proprement
  - Tester chaque environnement
- **Statut** : ⏳ À faire

### CONF-06: STATIC_ROOT/STATICFILES_DIRS
- **Fichier** : `config/settings/base.py:150-152`
- **Problème** : Référence à répertoire qui peut ne pas exister
- **Impact** : collectstatic échoue
- **Solution** :
  - Créer répertoire static/ s'il manque
  - Ou ajuster configuration
  - Documenter structure
- **Statut** : ⏳ À faire

### DB-02: Soft delete incohérent
- **Fichier** : Modèles variés
- **Problème** : Implémentation varie entre apps
- **Impact** : Comportement imprévisible
- **Solution** :
  - Créer AbstractSoftDeleteModel dans core
  - Migrer tous les modèles
  - Standardiser managers
- **Statut** : ⏳ À faire

### DB-03: Migrations dans backups
- **Fichier** : `apps/cotisations_backup_20250524/migrations/`
- **Problème** : Migrations en conflit potentiel
- **Impact** : Problèmes de migration
- **Solution** :
  - Supprimer avec répertoires backup
  - Vérifier état migrations
- **Statut** : ⏳ À faire

---

## 🟢 MAINTENANCE

### MAINT-01: Requirements non versionnés
- **Fichier** : `requirements.txt`
- **Problème** : pytest-django sans version
- **Impact** : Builds non reproductibles
- **Solution** :
  - Versionner tous les packages
  - Utiliser pip-tools ou poetry
  - Générer requirements.txt depuis .in
- **Statut** : ⏳ À faire

### MAINT-02: Packages de sécurité manquants
- **Fichier** : `requirements.txt`
- **Problème** : Pas de django-ratelimit, django-cors-headers
- **Impact** : Protection limitée
- **Solution** :
  - Ajouter packages recommandés
  - Configurer proprement
  - Documenter usage
- **Statut** : ⏳ À faire

### MAINT-03: Pas de serveur WSGI/ASGI pour production
- **Fichier** : `requirements.txt`
- **Problème** : Pas de gunicorn/uwsgi
- **Impact** : Impossible de déployer en production
- **Solution** :
  - Ajouter gunicorn
  - Créer configuration
  - Documenter déploiement
- **Statut** : ⏳ À faire

### MAINT-04: .coverage dans Git
- **Fichier** : `.coverage`
- **Problème** : Fichier de test coverage versionné
- **Impact** : Pollution repository
- **Solution** :
  - Supprimer du repository
  - Ajouter à .gitignore
- **Statut** : ⏳ À faire

### MAINT-05: Pas de pre-commit hooks
- **Fichier** : `.pre-commit-config.yaml` (n'existe pas)
- **Problème** : Pas de validation automatique
- **Impact** : Code non uniforme
- **Solution** :
  - Configurer pre-commit
  - Ajouter : black, isort, flake8, mypy
  - Documenter pour équipe
- **Statut** : ⏳ À faire

### MAINT-06: Pas de CI/CD
- **Fichier** : `.github/workflows/` (n'existe pas)
- **Problème** : Pas de pipeline automatisé
- **Impact** : Tests manuels, déploiements risqués
- **Solution** :
  - Créer GitHub Actions workflow
  - Tests, linting, sécurité, déploiement
  - Badge dans README
- **Statut** : ⏳ À faire

### MAINT-07: Documentation API manquante
- **Fichier** : N/A
- **Problème** : Endpoints API non documentés
- **Impact** : Intégration difficile
- **Solution** :
  - Utiliser drf-spectacular pour OpenAPI
  - Ou swagger
  - Documenter tous les endpoints
- **Statut** : ⏳ À faire

### MAINT-08: README incomplet
- **Fichier** : `README.md` (probablement)
- **Problème** : Setup, config, déploiement non documentés
- **Impact** : Onboarding difficile
- **Solution** :
  - Compléter README
  - Ajouter : setup, config, tests, déploiement
  - Badges de statut
- **Statut** : ⏳ À faire

### MAINT-09: Tests unitaires incomplets
- **Fichier** : Varie
- **Problème** : Coverage non uniforme
- **Impact** : Bugs non détectés
- **Solution** :
  - Viser 90%+ coverage
  - Tests pour nouveaux modèles
  - Tests d'intégration
- **Statut** : ⏳ À faire

### MAINT-10: Monitoring/Observabilité manquant
- **Fichier** : N/A
- **Problème** : Pas de Sentry, APM, logs centralisés
- **Impact** : Debugging production difficile
- **Solution** :
  - Intégrer Sentry pour erreurs
  - Configurer structured logging
  - Metrics (Prometheus?)
- **Statut** : ⏳ À faire

### MAINT-11: Pas de Makefile/scripts utilitaires
- **Fichier** : `Makefile` (n'existe pas)
- **Problème** : Commandes communes non scriptées
- **Impact** : Productivité réduite
- **Solution** :
  - Créer Makefile
  - Commands : test, lint, migrate, run, etc.
  - Documenter
- **Statut** : ⏳ À faire

### MAINT-12: Pas de Docker pour développement
- **Fichier** : `docker-compose.yml` (n'existe pas)
- **Problème** : Setup dev non standardisé
- **Impact** : "Works on my machine"
- **Solution** :
  - Créer Dockerfile
  - docker-compose.yml avec PostgreSQL, Redis
  - Documentation
- **Statut** : ⏳ À faire

### MAINT-13: Validation des contraintes métier
- **Fichier** : `apps/membres/models.py:546` (MembreTypeMembre)
- **Problème** : Pas de validation des chevauchements de dates
- **Impact** : Données incohérentes possibles
- **Solution** :
  - Ajouter clean() method
  - Valider pas de overlap
  - Tests
- **Statut** : ⏳ À faire

### MAINT-14: Gestion des fichiers uploadés
- **Fichier** : Varie
- **Problème** : Pas de validation taille/type fichiers
- **Impact** : Sécurité, espace disque
- **Solution** :
  - Validators pour upload
  - Limites de taille
  - Types MIME autorisés
- **Statut** : ⏳ À faire

### MAINT-15: Pas de rate limiting
- **Fichier** : N/A
- **Problème** : Pas de protection contre abus
- **Impact** : Vulnérable à DoS
- **Solution** :
  - django-ratelimit
  - Limites sur login, API, etc.
  - Configuration par endpoint
- **Statut** : ⏳ À faire

### MAINT-16: Backup automatique manquant
- **Fichier** : N/A
- **Problème** : Pas de stratégie backup
- **Impact** : Perte de données possible
- **Solution** :
  - Script backup PostgreSQL
  - Cron job ou Celery task
  - Rotation et stockage sécurisé
- **Statut** : ⏳ À faire

### MAINT-17: Timezone handling
- **Fichier** : Settings
- **Problème** : TIME_ZONE = 'UTC' mais app en français
- **Impact** : Confusion sur les dates
- **Solution** :
  - Vérifier si UTC approprié
  - Ou configurer Europe/Paris
  - Documenter choix
- **Statut** : ⏳ À faire

### MAINT-18: Translations manquantes
- **Fichier** : Varie
- **Problème** : LANGUAGE_CODE = 'en-us' mais UI en français
- **Impact** : Incohérence
- **Solution** :
  - Configurer i18n proprement
  - Utiliser gettext
  - Ou choisir une langue
- **Statut** : ⏳ À faire

### MAINT-19: Template tag sécurité
- **Fichier** : `apps/evenements/templatetags/evenements_extras.py:2`
- **Problème** : Utilise mark_safe
- **Impact** : Potentiel XSS
- **Solution** :
  - Auditer tous les usages
  - Escape proprement
  - Tests de sécurité
- **Statut** : ⏳ À faire

### MAINT-20: Celery configuré mais pas utilisé
- **Fichier** : `config/celery.py`
- **Problème** : Celery configuré mais pas dans requirements
- **Impact** : Configuration morte
- **Solution** :
  - Finaliser intégration Celery
  - Ou supprimer si non nécessaire
  - Tasks async pour emails, etc.
- **Statut** : ⏳ À faire

---

## 📋 NOTES DE MISE EN ŒUVRE

### Ordre de correction recommandé

**Phase 1 : Sécurité critique (Semaine 1)**
- SEC-01 à SEC-04 : Secrets, DEBUG, ALLOWED_HOSTS, DB
- CONF-01 : Consolider settings
- CODE-01, CODE-02 : Nettoyer backups

**Phase 2 : Fondations (Semaine 2)**
- CONF-02 : .env.example
- DB-01 : PostgreSQL pour production
- CONF-03 : Settings contradictoires
- CODE-03 : Imports dupliqués

**Phase 3 : Performance (Semaine 3)**
- PERF-01 : Index DB
- PERF-02 : Requêtes N+1
- PERF-03 : Throttle derniere_connexion
- PERF-04 : Cache requêtes

**Phase 4 : Architecture (Semaine 4-5)**
- ARCH-01, ARCH-02 : Diviser gros fichiers views
- ARCH-03, ARCH-04 : Refactor patterns
- DB-02 : Soft delete cohérent

**Phase 5 : Qualité de code (Semaine 6)**
- CODE-04 à CODE-08 : URLs, nommage, docs, magic numbers
- SEC-05 à SEC-08 : Sécurité moyenne priorité
- CONF-04 à CONF-06 : Configurations

**Phase 6 : Outillage (Semaine 7)**
- MAINT-01 à MAINT-05 : Requirements, pre-commit
- MAINT-06 : CI/CD
- MAINT-11, MAINT-12 : Makefile, Docker

**Phase 7 : Production-ready (Semaine 8)**
- MAINT-03 : WSGI/ASGI
- MAINT-10 : Monitoring
- MAINT-15, MAINT-16 : Rate limiting, backups
- MAINT-07, MAINT-08 : Documentation

**Phase 8 : Polish (Semaine 9)**
- MAINT-09 : Tests complets
- MAINT-13, MAINT-14 : Validations
- MAINT-17 à MAINT-20 : Derniers détails

### Principes directeurs

1. **Sécurité d'abord** : Aucun compromis
2. **Tests exhaustifs** : Chaque changement testé
3. **Backward compatibility** : Minimiser breaking changes
4. **Documentation** : Chaque décision documentée
5. **Commits atomiques** : Un problème = un commit
6. **Code review** : Peer review pour changements majeurs

### Métriques de succès

- ✅ 100% secrets hors du code
- ✅ Coverage tests > 90%
- ✅ Temps réponse < 200ms (p95)
- ✅ 0 vulnérabilités critiques
- ✅ Code quality A (SonarQube)
- ✅ Documentation complète

---

**Dernière mise à jour** : 2025-11-15
**Prochaine révision** : À chaque problème corrigé
