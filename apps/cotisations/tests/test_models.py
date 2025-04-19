# apps/cotisations/tests/test_models.py
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from django.core.exceptions import ValidationError

from apps.membres.models import Membre, TypeMembre
from apps.core.models import Statut
from apps.cotisations.models import (
    Cotisation, Paiement, ModePaiement, BaremeCotisation,
    Rappel, HistoriqueCotisation
)


class CotisationModelTest(TestCase):
    """Tests pour le modèle Cotisation."""
    
    def setUp(self):
        # Créer les données de test
        self.type_membre = TypeMembre.objects.create(
            libelle="Membre standard",
            description="Membre standard de l'association"
        )
        
        self.statut = Statut.objects.create(
            nom="Actif",
            description="Statut actif"
        )
        
        self.membre = Membre.objects.create(
            nom="Dupont",
            prenom="Jean",
            email="jean.dupont@example.com",
            date_adhesion=timezone.now().date()
        )
        
        # Dates pour les tests
        today = timezone.now().date()
        self.date_emission = today
        self.date_echeance = today + timezone.timedelta(days=30)
        
        # Créer une cotisation
        self.cotisation = Cotisation.objects.create(
            membre=self.membre,
            montant=Decimal('120.00'),
            date_emission=self.date_emission,
            date_echeance=self.date_echeance,
            periode_debut=self.date_emission,
            periode_fin=self.date_emission.replace(year=self.date_emission.year + 1),
            annee=self.date_emission.year,
            statut=self.statut,
            type_membre=self.type_membre,
            montant_restant=Decimal('120.00')
        )
    
    def test_creation_cotisation(self):
        """Teste la création d'une cotisation avec tous les champs obligatoires."""
        self.assertEqual(Cotisation.objects.count(), 1)
        self.assertEqual(self.cotisation.montant, Decimal('120.00'))
        self.assertEqual(self.cotisation.membre, self.membre)
        self.assertEqual(self.cotisation.type_membre, self.type_membre)
        self.assertEqual(self.cotisation.montant_restant, Decimal('120.00'))
        
        # Vérifier que le statut de paiement est correct
        self.assertEqual(self.cotisation.statut_paiement, 'non_payee')
    
    def test_reference_generation(self):
        """Teste la génération automatique d'une référence unique."""
        self.assertTrue(self.cotisation.reference)
        self.assertTrue(self.cotisation.reference.startswith('COT-'))
        self.assertIn(str(self.cotisation.date_emission.year), self.cotisation.reference)
    
    def test_paiement_integration(self):
        """Teste l'intégration avec les paiements et la mise à jour du montant restant."""
        # Créer un mode de paiement
        mode_paiement = ModePaiement.objects.create(
            libelle="Carte bancaire",
            description="Paiement par carte bancaire"
        )
        
        # Ajouter un paiement partiel
        paiement = Paiement.objects.create(
            cotisation=self.cotisation,
            montant=Decimal('50.00'),
            date_paiement=timezone.now(),
            mode_paiement=mode_paiement,
            type_transaction='paiement'
        )
        
        # Recharger la cotisation
        self.cotisation.refresh_from_db()
        
        # Vérifier la mise à jour du montant restant
        self.assertEqual(self.cotisation.montant_restant, Decimal('70.00'))
        self.assertEqual(self.cotisation.statut_paiement, 'partiellement_payee')
        
        # Ajouter un second paiement pour completer
        paiement2 = Paiement.objects.create(
            cotisation=self.cotisation,
            montant=Decimal('70.00'),
            date_paiement=timezone.now(),
            mode_paiement=mode_paiement,
            type_transaction='paiement'
        )
        
        # Recharger la cotisation
        self.cotisation.refresh_from_db()
        
        # Vérifier que la cotisation est complètement payée
        self.assertEqual(self.cotisation.montant_restant, Decimal('0.00'))
        self.assertEqual(self.cotisation.statut_paiement, 'payee')
    
    def test_remboursement(self):
        """Teste le remboursement et son impact sur le montant restant."""
        # Créer un mode de paiement
        mode_paiement = ModePaiement.objects.create(
            libelle="Virement",
            description="Paiement par virement"
        )
        
        # Paiement complet
        Paiement.objects.create(
            cotisation=self.cotisation,
            montant=Decimal('120.00'),
            date_paiement=timezone.now(),
            mode_paiement=mode_paiement,
            type_transaction='paiement'
        )
        
        # Recharger la cotisation
        self.cotisation.refresh_from_db()
        self.assertEqual(self.cotisation.statut_paiement, 'payee')
        
        # Remboursement partiel
        Paiement.objects.create(
            cotisation=self.cotisation,
            montant=Decimal('20.00'),
            date_paiement=timezone.now(),
            mode_paiement=mode_paiement,
            type_transaction='remboursement'
        )
        
        # Recharger la cotisation
        self.cotisation.refresh_from_db()
        
        # Vérifier que le montant restant a augmenté et le statut a changé
        self.assertEqual(self.cotisation.montant_restant, Decimal('20.00'))
        self.assertEqual(self.cotisation.statut_paiement, 'partiellement_payee')


# Ajouter d'autres classes de test pour les autres modèles...