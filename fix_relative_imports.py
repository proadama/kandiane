#!/usr/bin/env python3
"""
Script pour corriger les imports relatifs dans apps/cotisations/views/
et les remplacer par des imports absolus.
"""

import os
import re

# Répertoire contenant les modules
VIEWS_DIR = "apps/cotisations/views"

# Mapping des imports relatifs vers absolus
REPLACEMENTS = {
    "from .utils import": "from apps.cotisations.views.utils import",
}

def fix_imports_in_file(filepath):
    """Corrige les imports dans un fichier."""
    print(f"Traitement de {filepath}...")

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content
    modified = False

    for old_import, new_import in REPLACEMENTS.items():
        if old_import in content:
            content = content.replace(old_import, new_import)
            modified = True
            print(f"  ✓ Remplacé: {old_import} -> {new_import}")

    if modified:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  ✓ Fichier mis à jour")
        return True
    else:
        print(f"  ℹ Aucun changement nécessaire")
        return False

def main():
    """Point d'entrée principal."""
    print("=" * 70)
    print("Correction des imports relatifs dans apps/cotisations/views/")
    print("=" * 70)
    print()

    # Fichiers à traiter
    files_to_fix = [
        os.path.join(VIEWS_DIR, "dashboard.py"),
        os.path.join(VIEWS_DIR, "cotisations.py"),
        os.path.join(VIEWS_DIR, "paiements.py"),
        os.path.join(VIEWS_DIR, "rappels.py"),
        os.path.join(VIEWS_DIR, "baremes.py"),
        os.path.join(VIEWS_DIR, "api.py"),
    ]

    total_modified = 0

    for filepath in files_to_fix:
        if os.path.exists(filepath):
            if fix_imports_in_file(filepath):
                total_modified += 1
            print()
        else:
            print(f"⚠ Fichier non trouvé: {filepath}")
            print()

    print("=" * 70)
    print(f"✓ Terminé! {total_modified} fichier(s) modifié(s)")
    print("=" * 70)

if __name__ == "__main__":
    main()
