# apps/core/management/commands/create_default_statuts.py
from django.core.management.base import BaseCommand
from apps.core.models import Statut

class Command(BaseCommand):
    help = 'Crée les statuts par défaut pour l\'application'
    
    def handle(self, *args, **options):
        # Statuts pour les membres
        statuts_membres = [
            ('Actif', 'Membre à jour de ses cotisations'),
            ('En attente', 'Membre en attente de validation'),
            ('Suspendu', 'Membre temporairement suspendu'),
            ('Désactivé', 'Ancien membre'),
            ('Honoraire', 'Membre dispensé de cotisation')
        ]
        
        # Statuts pour les cotisations
        statuts_cotisations = [
            ('En attente de paiement', 'Cotisation émise mais non payée'),
            ('Payée', 'Cotisation entièrement payée'),
            ('En retard', 'Cotisation en retard de paiement'),
            ('Annulée', 'Cotisation annulée')
        ]
        
        # Statuts pour les paiements
        statuts_paiements = [
            ('Validé', 'Paiement validé'),
            ('En attente', 'Paiement en attente de traitement'),
            ('Annulé', 'Paiement annulé'),
            ('Rejeté', 'Paiement rejeté par la banque')
        ]
        
        # Création des statuts
        for nom, description in statuts_membres:
            Statut.objects.get_or_create(
                nom=nom,
                defaults={
                    'description': description,
                    'type_entite': 'membre'
                }
            )
            
        for nom, description in statuts_cotisations:
            Statut.objects.get_or_create(
                nom=nom,
                defaults={
                    'description': description,
                    'type_entite': 'cotisation'
                }
            )
            
        for nom, description in statuts_paiements:
            Statut.objects.get_or_create(
                nom=nom,
                defaults={
                    'description': description,
                    'type_entite': 'paiement'
                }
            )
            
        self.stdout.write(self.style.SUCCESS('Statuts par défaut créés avec succès'))