"""
Package views pour l'application cotisations.

Ce package est en cours de refactoring pour diviser le fichier monolithique views.py (3972 lignes)
en modules logiques plus maintenables.

Structure cible :
-----------------
    views/
    ├── __init__.py          # Ce fichier - Imports de compatibilité
    ├── utils.py             # ✅ Utilitaires et classes de base
    ├── dashboard.py         # 📋 Tableaux de bord et statistiques
    ├── cotisations.py       # 💰 CRUD cotisations
    ├── paiements.py         # 💳 Gestion paiements
    ├── rappels.py           # 📧 Gestion rappels
    ├── baremes.py           # 📊 Gestion barèmes
    ├── imports_exports.py   # 📥 Import/Export de données
    └── api.py               # 🔌 Endpoints API

État actuel :
-------------
    ✅ utils.py - Créé avec imports communs et ExtendedJSONEncoder
    ⏳ Autres modules - À créer (voir plan de migration ci-dessous)

Pour maintenir la compatibilité pendant la migration, ce fichier __init__.py
importe temporairement depuis l'ancien views.py.

Une fois tous les modules créés, ce fichier importera depuis chaque module.
"""

# Importer depuis les nouveaux modules avec imports absolus
from apps.cotisations.views.utils import *
from apps.cotisations.views.dashboard import *
from apps.cotisations.views.cotisations import *
from apps.cotisations.views.paiements import *
from apps.cotisations.views.rappels import *
from apps.cotisations.views.baremes import *
from apps.cotisations.views.api import *

# Import conditionnel depuis l'ancien views.py pour les modules non migrés
# (imports_exports.py reste dans views.py pour l'instant)
import sys
import os
import importlib.util

try:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    old_views_path = os.path.join(parent_dir, 'views.py')

    if os.path.exists(old_views_path):
        spec = importlib.util.spec_from_file_location("cotisations_views_old", old_views_path)
        old_views = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(old_views)

        # Importer uniquement les classes/fonctions non encore migrées
        # (ImportCotisationsForm, ImportCotisationsView, ExportCotisationsView, etc.)
        non_migrated = [
            'ImportCotisationsForm',
            'ImportCotisationsView',
            'ExportCotisationsView',
            'export_cotisations_pdf',
            'export_paiements',
            'export_rappels',
            '_apply_paiement_filters',
            '_apply_rappel_filters',
        ]

        for name in non_migrated:
            if hasattr(old_views, name):
                globals()[name] = getattr(old_views, name)

except Exception as e:
    import logging
    logger = logging.getLogger(__name__)
    logger.warning(f"Erreur lors de l'import des modules non migrés: {e}")

# Créer les aliases de vues pour urls.py
# Ces aliases pointent vers les vues des modules refactorés
dashboard = DashboardView.as_view()
statistiques = StatistiquesView.as_view()

cotisation_list = CotisationListView.as_view()
cotisation_detail = CotisationDetailView.as_view()
cotisation_create = CotisationCreateView.as_view()
cotisation_update = CotisationUpdateView.as_view()
cotisation_delete = CotisationDeleteView.as_view()
corbeille = CotisationCorbeilleView.as_view()

paiement_list = PaiementListView.as_view()
paiement_detail = PaiementDetailView.as_view()
paiement_create = PaiementCreateView.as_view()
paiement_update = PaiementUpdateView.as_view()
paiement_delete = PaiementDeleteView.as_view()

bareme_list = BaremeCotisationListView.as_view()
bareme_detail = BaremeDetailView.as_view()
bareme_create = BaremeCotisationCreateView.as_view()
bareme_update = BaremeCotisationUpdateView.as_view()
bareme_delete = BaremeCotisationDeleteView.as_view()

rappel_list = RappelListView.as_view()
rappel_detail = RappelDetailView.as_view()
rappel_create = RappelCreateView.as_view()
rappel_update = RappelUpdateView.as_view()

# Créer les aliases pour les vues d'export/import (depuis old_views)
# Ces vues ne sont pas encore migrées, elles viennent de views.py
try:
    if 'ExportCotisationsView' in globals():
        export = ExportCotisationsView.as_view()
    if 'ImportCotisationsView' in globals():
        import_cotisations = ImportCotisationsView.as_view()
except Exception:
    pass  # Les vues ne sont pas encore migrées


# ============================================================================
# PLAN DE MIGRATION DÉTAILLÉ
# ============================================================================
"""
Étape 1 : Créer utils.py ✅
    - Imports communs
    - ExtendedJSONEncoder
    - Configuration logger

Étape 2 : Créer dashboard.py
    - DashboardView (~220 lignes)
    - StatistiquesView (~100 lignes)
    - Graphiques et statistiques

Étape 3 : Créer api.py
    - api_calculer_montant
    - api_baremes_par_type
    - api_verifier_bareme
    - api_generer_recu
    - api_marquer_paiement_recu
    - api_stats_cotisations
    - api_cotisations_en_retard
    - api_envoyer_rappels_automatiques
    (~500 lignes)

Étape 4 : Créer baremes.py
    - BaremeCotisationListView
    - BaremeDetailView
    - BaremeCotisationCreateView
    - BaremeCotisationUpdateView
    - BaremeCotisationDeleteView
    - bareme_reactive
    (~200 lignes)

Étape 5 : Créer rappels.py
    - RappelCreateView
    - RappelListView
    - RappelDetailView
    - RappelUpdateView
    - RappelEnvoyerView
    - RappelDeleteView
    - rappel_create_ajax
    - envoyer_rappel
    (~400 lignes)

Étape 6 : Créer paiements.py
    - PaiementListView
    - PaiementDetailView
    - PaiementCreateView
    - PaiementUpdateView
    - PaiementDeleteView
    - PaiementCorbeilleView
    - PaiementRestoreView
    - paiement_create_ajax
    (~500 lignes)

Étape 7 : Créer cotisations.py
    - CotisationListView
    - CotisationDetailView
    - CotisationCreateView
    - CotisationUpdateView
    - CotisationDeleteView
    - CotisationCorbeilleView
    - RestaurerCotisationView
    - SupprimerDefinitivementCotisationView
    - CotisationRestoreView
    (~400 lignes)

Étape 8 : Créer imports_exports.py
    - ImportCotisationsForm
    - ImportCotisationsView
    - ExportCotisationsView
    - export_cotisations_pdf
    - export_paiements
    - export_rappels
    - _apply_paiement_filters
    - _apply_rappel_filters
    (~1200 lignes - le plus gros module)

Étape 9 : Mettre à jour __init__.py
    - Importer depuis tous les nouveaux modules
    - Supprimer l'import depuis views.py

Étape 10 : Renommer/Archiver views.py
    - Renommer en views.py.old
    - Ajouter à .gitignore

Étape 11 : Tests
    - Vérifier que toutes les URLs fonctionnent
    - Vérifier les imports dans urls.py
    - Tests unitaires

Total estimé après division :
    utils.py            ~100 lignes
    dashboard.py        ~320 lignes
    api.py              ~500 lignes
    baremes.py          ~200 lignes
    rappels.py          ~400 lignes
    paiements.py        ~500 lignes
    cotisations.py      ~400 lignes
    imports_exports.py  ~1200 lignes
    __init__.py         ~50 lignes
    ===========================
    TOTAL               ~3670 lignes (vs 3972 originales)

    Réduction nette : ~300 lignes (élimination de duplications)
    Maintenabilité : +++++ (8 fichiers de 100-500 lignes vs 1 fichier de 4000)
"""
