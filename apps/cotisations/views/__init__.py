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

# TODO: Migrer progressivement depuis views.py vers les modules
# Pour l'instant, importer depuis l'ancien fichier pour compatibilité
import sys
import os

# Importer depuis l'ancien views.py (un niveau au-dessus)
# Cette approche temporaire maintient la compatibilité durant la migration
try:
    # Chemin vers l'ancien views.py
    current_dir = os.path.dirname(__file__)
    parent_dir = os.path.dirname(current_dir)
    old_views_path = os.path.join(parent_dir, 'views.py')

    if os.path.exists(old_views_path):
        # Importer tout depuis l'ancien fichier
        import importlib.util
        spec = importlib.util.spec_from_file_location("cotisations_views_old", old_views_path)
        old_views = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(old_views)

        # Réexporter tout
        for name in dir(old_views):
            if not name.startswith('_'):
                globals()[name] = getattr(old_views, name)
    else:
        # Si views.py n'existe plus, utiliser les nouveaux modules
        from .utils import *
        # TODO: from .dashboard import *
        # TODO: from .cotisations import *
        # TODO: from .paiements import *
        # TODO: from .rappels import *
        # TODO: from .baremes import *
        # TODO: from .imports_exports import *
        # TODO: from .api import *

except Exception as e:
    # Fallback : au moins importer utils
    from .utils import *
    import logging
    logger = logging.getLogger(__name__)
    logger.warning(f"Erreur lors de l'import depuis views.py: {e}")


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
