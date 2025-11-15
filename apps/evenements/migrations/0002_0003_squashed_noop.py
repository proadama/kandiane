# Generated manually to resolve migration conflict
# This migration replaces 0002_log.py and 0003_delete_log.py
# which created and immediately deleted a Log model that conflicted with core.Log

from django.db import migrations


class Migration(migrations.Migration):
    """
    Migration vide pour remplacer 0002_log et 0003_delete_log.
    Ces migrations créaient et supprimaient un modèle Log qui était en conflit
    avec le modèle Log de l'app core (table core_log).
    """

    replaces = [
        ('evenements', '0002_log'),
        ('evenements', '0003_delete_log'),
    ]

    dependencies = [
        ('evenements', '0001_initial'),
    ]

    operations = [
        # Aucune opération - les migrations 0002 et 0003 s'annulent mutuellement
    ]
