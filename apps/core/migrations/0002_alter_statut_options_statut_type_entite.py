from django.db import migrations, models

def classifier_statuts_existants(apps, schema_editor):
    Statut = apps.get_model('core', 'Statut')
    
    # Mapping des statuts selon leur usage prévu
    statuts_membres = ['Actif', 'En attente', 'Suspendu', 'Désactivé', 'Honoraire']
    statuts_cotisations = ['Non payé', 'Payée', 'En retard', 'Annulée']
    statuts_paiements = ['Validé', 'En attente', 'Annulé', 'Rejeté']
    
    # Mettre à jour par nom (case insensitive)
    for statut in Statut.objects.all():
        nom_lower = statut.nom.lower()
        if any(s.lower() in nom_lower for s in statuts_membres):
            statut.type_entite = 'membre'
        elif any(s.lower() in nom_lower for s in statuts_cotisations):
            statut.type_entite = 'cotisation'
        elif any(s.lower() in nom_lower for s in statuts_paiements):
            statut.type_entite = 'paiement'
        statut.save()

def reverse_classifier_statuts(apps, schema_editor):
    Statut = apps.get_model('core', 'Statut')
    Statut.objects.all().update(type_entite='global')

    
class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='statut',
            options={'ordering': ['type_entite', 'nom'], 'verbose_name': 'Statut', 'verbose_name_plural': 'Statuts'},
        ),
        migrations.AddField(
            model_name='statut',
            name='type_entite',
            field=models.CharField(choices=[('global', 'Global'), ('membre', 'Membre'), ('cotisation', 'Cotisation'), ('paiement', 'Paiement'), ('evenement', 'Événement')], default='global', max_length=20, verbose_name="Type d'entité"),
        ),
        # Ajoutez cette opération après l'ajout du champ
        migrations.RunPython(classifier_statuts_existants, migrations.RunPython.noop),
    ]