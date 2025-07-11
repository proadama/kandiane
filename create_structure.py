#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script pour créer la structure de templates de l'app événements Django
"""

import os
from pathlib import Path

def create_html_file(filepath, content=""):
    """Créer un fichier HTML avec du contenu de base"""
    filename = os.path.basename(filepath)
    template_name = filename.replace('.html', '').replace('_', ' ').title()
    
    default_content = f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{template_name} - Événements</title>
</head>
<body>
    <h1>{template_name}</h1>
    <!-- TODO: Ajouter le contenu du template -->
</body>
</html>
"""
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content if content else default_content)
    print(f"✓ Créé: {filepath}")

def create_evenements_structure():
    """Créer la structure complète des templates événements"""
    
    # Chemin de base
    base_path = Path("apps/evenements/templates/evenements")
    
    # Structure des dossiers et fichiers
    structure = {
        # Fichiers à la racine
        "": [
            "base_evenement.html",
            "dashboard.html", 
            "liste.html",
            "detail.html",
            "form.html",
            "calendrier.html",
            "recherche.html"
        ],
        
        # Sous-dossiers avec leurs fichiers
        "inscription": [
            "form.html",
            "detail.html", 
            "confirmation.html",
            "confirmation_erreur.html",
            "confirmation_succes.html",
            "mes_inscriptions.html"
        ],
        
        "validation": [
            "liste.html",
            "detail.html",
            "masse.html"
        ],
        
        "sessions": [
            "liste.html",
            "form.html"
        ],
        
        "types": [
            "liste.html",
            "form.html"
        ],
        
        "rapports": [
            "evenements.html"
        ],
        
        "public": [
            "liste.html",
            "detail.html",
            "calendrier.html"
        ],
        
        "errors": [
            "404.html",
            "500.html"
        ]
    }
    
    print("🚀 Création de la structure des templates événements...")
    print(f"📁 Dossier de base: {base_path}")
    print("-" * 60)
    
    # Créer le dossier de base
    base_path.mkdir(parents=True, exist_ok=True)
    print(f"✓ Dossier créé: {base_path}")
    
    # Parcourir la structure
    for folder, files in structure.items():
        # Déterminer le chemin du dossier
        if folder == "":
            current_path = base_path
        else:
            current_path = base_path / folder
            current_path.mkdir(exist_ok=True)
            print(f"✓ Dossier créé: {current_path}")
        
        # Créer les fichiers dans ce dossier
        for file in files:
            file_path = current_path / file
            
            # Contenu spécial pour certains fichiers
            special_content = get_special_content(file, folder)
            create_html_file(file_path, special_content)
    
    print("-" * 60)
    print("✅ Structure créée avec succès!")
    print(f"📊 Total: {count_files(structure)} fichiers créés")
    print("\n🔍 Vérification de la structure:")
    display_tree(base_path)

def get_special_content(filename, folder):
    """Retourner du contenu spécialisé pour certains fichiers"""
    
    special_templates = {
        "base_evenement.html": """{% load static %}
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Événements{% endblock %}</title>
    <link rel="stylesheet" href="{% static 'css/evenements.css' %}">
</head>
<body>
    <header>
        <nav>
            <!-- Navigation principale -->
        </nav>
    </header>
    
    <main>
        {% block content %}
        {% endblock %}
    </main>
    
    <footer>
        <!-- Footer -->
    </footer>
    
    <script src="{% static 'js/evenements.js' %}"></script>
</body>
</html>""",
        
        "404.html": """{% extends "evenements/base_evenement.html" %}

{% block title %}Page non trouvée - Événements{% endblock %}

{% block content %}
<div class="error-page">
    <h1>404 - Page non trouvée</h1>
    <p>La page que vous recherchez n'existe pas.</p>
    <a href="{% url 'evenements:liste' %}">Retour à la liste des événements</a>
</div>
{% endblock %}""",
        
        "500.html": """{% extends "evenements/base_evenement.html" %}

{% block title %}Erreur serveur - Événements{% endblock %}

{% block content %}
<div class="error-page">
    <h1>500 - Erreur serveur</h1>
    <p>Une erreur interne s'est produite.</p>
    <a href="{% url 'evenements:liste' %}">Retour à la liste des événements</a>
</div>
{% endblock %}"""
    }
    
    return special_templates.get(filename, "")

def count_files(structure):
    """Compter le nombre total de fichiers"""
    return sum(len(files) for files in structure.values())

def display_tree(path, prefix="", is_last=True):
    """Afficher l'arborescence des fichiers créés"""
    items = sorted(path.iterdir())
    for i, item in enumerate(items):
        is_last_item = i == len(items) - 1
        current_prefix = "└── " if is_last_item else "├── "
        print(f"{prefix}{current_prefix}{item.name}")
        
        if item.is_dir():
            extension = "    " if is_last_item else "│   "
            display_tree(item, prefix + extension, is_last_item)

if __name__ == "__main__":
    try:
        create_evenements_structure()
    except Exception as e:
        print(f"❌ Erreur: {e}")
        print("Assurez-vous d'avoir les permissions d'écriture dans le répertoire courant.")