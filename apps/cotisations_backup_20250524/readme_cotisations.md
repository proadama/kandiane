# Application Cotisations

## Présentation
L'application **Cotisations** est un module central du système de gestion d'association permettant de gérer l'ensemble du cycle de vie des cotisations des membres, depuis leur émission jusqu'à leur paiement, en passant par les rappels et le suivi financier. Elle s'intègre avec les applications Core et Membres pour offrir une gestion complète des aspects financiers de l'association.

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![Status](https://img.shields.io/badge/status-en_développement-orange)

## Fonctionnalités principales

- 📋 **Gestion complète des cotisations** avec suivi des statuts et échéances
- 💰 **Système de paiement multimodal** permettant des paiements partiels ou complets
- 📊 **Tableau de bord analytique** avec visualisations financières et statistiques
- 📥 **Import/Export de données** au format CSV et Excel
- 📅 **Barèmes de cotisation configurables** par type de membre
- 📬 **Système de rappels automatiques** pour les cotisations en retard
- 🔍 **Recherche avancée** avec filtres multiples
- 🗄️ **Historisation complète** pour l'audit et le suivi

## Prérequis

- Python 3.8+
- Django 4.2+
- Les applications Core et Membres installées
- Bibliothèques: django-environ, Pillow, openpyxl

## Installation et configuration

1. Assurez-vous que l'application est incluse dans `INSTALLED_APPS` :
   ```python
   INSTALLED_APPS = [
       # ...
       'apps.core',
       'apps.membres',
       'apps.cotisations',
       # ...
   ]
   ```

2. Ajoutez les URLs dans votre fichier `urls.py` principal :
   ```python
   urlpatterns = [
       # ...
       path('cotisations/', include('apps.cotisations.urls')),
       # ...
   ]
   ```

3. Exécutez les migrations pour créer les tables nécessaires :
   ```bash
   python manage.py makemigrations cotisations
   python manage.py migrate
   ```

4. Créez les statuts et modes de paiement de base :
   ```bash
   python manage.py loaddata cotisations_initial_data
   ```

## Structure de l'application

```
apps/cotisations/
├── __init__.py
├── admin.py              # Configuration de l'interface d'administration
├── apps.py               # Configuration de l'application
├── forms.py              # Formulaires pour la gestion des cotisations
├── managers.py           # Gestionnaires personnalisés pour les modèles
├── migrations/           # Migrations de base de données
├── models.py             # Modèles de données (Cotisation, Paiement, etc.)
├── static/               # Fichiers statiques (CSS, JS, images)
│   └── js/
│       └── cotisations/  # Scripts spécifiques aux cotisations
├── templates/            # Templates HTML de l'interface utilisateur
│   └── cotisations/
│       ├── dashboard.html
│       ├── cotisation_form.html
│       ├── cotisation_detail.html
│       └── ...
├── templatetags/         # Filtres et tags de templates personnalisés
│   ├── __init__.py
│   ├── custom_filters.py
│   └── cotisations_extras.py
├── tests/                # Tests unitaires et d'intégration
│   ├── __init__.py
│   ├── test_models.py
│   ├── test_views.py
│   └── test_integration.py
├── urls.py               # Configuration des URLs
└── views.py              # Vues pour les fonctionnalités
```

## Modèles principaux

### Cotisation
Représente une cotisation émise à un membre :
- Informations de base (montant, référence, dates)
- Périodicité (année, mois) et durée de validité
- Suivi de paiement (montant restant, statut)
- Association avec un membre et un type de membre

### Paiement
Enregistre un paiement lié à une cotisation :
- Montant et date du paiement
- Mode de paiement (carte, virement, chèque, etc.)
- Type de transaction (paiement, remboursement, rejet)
- Référence externe et métadonnées

### BaremeCotisation
Définit les tarifs par type de membre :
- Montant et périodicité (annuelle, mensuelle, etc.)
- Période de validité du barème
- Association avec un type de membre

### Rappel
Gère les rappels pour les cotisations non-payées :
- Type de rappel (email, SMS, courrier)
- Contenu et niveau du rappel
- Suivi d'envoi et état

### ModePaiement
Modes de paiement acceptés par l'association :
- Libellé et description
- Statut d'activation

## Workflows et processus

### Cycle de vie d'une cotisation

1. **Création** : La cotisation est créée avec un statut "non payée"
2. **Paiement** : Des paiements peuvent être enregistrés (partiels ou complets)
3. **Suivi** : Le statut évolue automatiquement ("partiellement payée", "payée")
4. **Rappels** : En cas de retard, des rappels peuvent être générés et envoyés

### Processus de paiement

1. Accès à la page de détail d'une cotisation
2. Enregistrement d'un paiement (montant, mode, date, référence)
3. Mise à jour automatique du montant restant et du statut
4. Possibilité d'annuler ou de modifier un paiement

### Système de rappels

1. Détection des cotisations en retard via le tableau de bord
2. Génération de rappels personnalisés (contenu, niveau)
3. Envoi manuel ou automatique selon la configuration
4. Suivi de l'état des rappels (envoyé, lu, etc.)

## Filtres de template personnalisés

L'application utilise des filtres personnalisés pour simplifier l'affichage des données dans les templates :

### Filtres disponibles
- `split` : Divise une chaîne en utilisant un séparateur
- `sub` : Soustrait un nombre d'un autre
- `add_days` : Ajoute un nombre de jours à une date

### Configuration
Ces filtres sont disponibles via deux modules :
- `custom_filters.py` : Module principal contenant les définitions des filtres
- `cotisations_extras.py` : Alias pour assurer la compatibilité avec les templates existants

### Utilisation
```django
{% load custom_filters %}

<!-- Exemple 1: Soustraire deux valeurs -->
{{ cotisation.montant|sub:cotisation.montant_restant|floatformat:2 }} €

<!-- Exemple 2: Diviser une chaîne -->
{% with parties=texte|split:"," %}
    {{ parties.0 }}
{% endwith %}

<!-- Exemple 3: Ajouter des jours à une date -->
{{ date_actuelle|add_days:30|date:"d/m/Y" }}
```

## Vues principales

### Dashboard (Tableau de bord)
- URL: `/cotisations/`
- Affiche des statistiques et graphiques sur les cotisations
- Permet de filtrer par période (mois, trimestre, année)
- Présente les cotisations en retard et celles à échéance

### Liste des cotisations
- URL: `/cotisations/liste/`
- Affiche toutes les cotisations avec filtres avancés
- Permet de trier et rechercher par différents critères

### Détail d'une cotisation
- URL: `/cotisations/<id>/`
- Affiche les informations complètes d'une cotisation
- Permet d'enregistrer des paiements et des rappels
- Présente l'historique des paiements et modifications

### Gestion des barèmes
- URL: `/cotisations/baremes/`
- Permet de configurer les tarifs par type de membre
- Gère les périodes de validité des barèmes

## Tests

L'application dispose d'une suite de tests complète :

### Tests unitaires
- Tests des modèles (Cotisation, Paiement, etc.)
- Tests des formulaires et leur validation
- Tests des vues et de leurs permissions

### Tests d'intégration
Le fichier `test_integration.py` contient des tests qui vérifient le workflow complet :
1. Création d'une cotisation
2. Enregistrement d'un paiement partiel
3. Création d'un rappel
4. Finalisation du paiement
5. Vérification de l'état final

### Exécution des tests
```bash
# Tous les tests de l'application
python manage.py test apps.cotisations

# Tests d'intégration spécifiques
python manage.py test apps.cotisations.tests.test_integration
```

## Intégration avec d'autres modules

### Application Core
- Utilisation du `BaseModel` pour la suppression logique
- Mixins de sécurité pour le contrôle d'accès
- Utilisation du modèle `Statut` pour le statut des cotisations

### Application Membres
- Lien avec les membres pour l'attribution des cotisations
- Utilisation des `TypeMembre` pour déterminer les barèmes
- Accès aux informations de contact pour les rappels

## Corrections et ajustements récents

### Filtres de template
- Ajout des filtres `split`, `sub` et `add_days` dans `custom_filters.py`
- Création de `cotisations_extras.py` comme alias pour la compatibilité
- Mise en place de la structure de dossier `templatetags`

### Tests d'intégration
- Correction du test `test_workflow_complet` pour éviter les duplications de `TypeMembre`
- Utilisation de l'ORM direct pour simplifier la création des objets de test
- Ajout de l'initialisation de `today` dans les tests

### URL manquantes
- Ajout de l'URL pour la fonction `envoyer_rappel` :
  ```python
  path('rappels/<int:rappel_id>/envoyer/', views.envoyer_rappel, name='envoyer_rappel')
  ```

## Dépannage courant

### Problème d'affichage dans les templates
- Vérifier que les filtres personnalisés sont correctement chargés avec `{% load custom_filters %}`
- S'assurer que tous les modèles référencés dans les templates existent

### Erreurs dans les tests
- Vérifier que toutes les URLs utilisées dans les tests sont bien définies
- S'assurer que les données de test sont cohérentes (types, références, etc.)

### Problèmes de filtres
- Si vous rencontrez l'erreur `Invalid filter`, vérifier que le filtre est bien défini et importé
- Si un filtre ne fonctionne pas comme prévu, vérifier sa définition dans `custom_filters.py`

## Évolutions futures

### Améliorations prévues
- 🔲 **Système de reçus automatiques** pour les paiements
- 🔲 **Interface d'export avancée** avec options de filtrage
- 🔲 **Tableau de bord interactif** avec filtres dynamiques
- 🔲 **Intégration de passerelles de paiement** en ligne
- 🔲 **Système de prélèvement automatique** pour les abonnements

### Intégrations futures
- 🔲 **Module Comptabilité** pour le reporting financier
- 🔲 **Module API REST** pour l'accès externe aux données
- 🔲 **Module PDF** pour la génération de documents officiels

---

Développé dans le cadre du projet de gestion d'association.  
Version: 1.0.0 | Dernière mise à jour: Avril 2025
