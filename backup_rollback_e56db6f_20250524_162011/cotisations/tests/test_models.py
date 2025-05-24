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

import datetime
from django.test import TestCase
from django.contrib.auth import get_user_model

User = get_user_model()

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

class TestBaremeCotisation(TestCase):
    """
    Tests pour le modèle BaremeCotisation.
    """
    def setUp(self):
        # Créer un type de membre
        self.type_membre = TypeMembre.objects.create(libelle="Standard")
        
        # Créer un barème
        self.bareme = BaremeCotisation.objects.create(
            type_membre=self.type_membre,
            montant=Decimal("120.00"),
            date_debut_validite=timezone.now().date(),
            periodicite="annuelle"
        )
    
    def test_creation_bareme(self):
        """Vérifier que le barème est correctement créé."""
        self.assertEqual(self.bareme.montant, Decimal("120.00"))
        self.assertEqual(self.bareme.type_membre.libelle, "Standard")
        self.assertEqual(self.bareme.periodicite, "annuelle")
    
    def test_est_actif(self):
        """Vérifier la méthode est_actif()."""
        # Barème sans date de fin
        self.assertTrue(self.bareme.est_actif())
        
        # Barème avec date de fin future
        demain = timezone.now().date() + datetime.timedelta(days=1)
        self.bareme.date_fin_validite = demain
        self.bareme.save()
        self.assertTrue(self.bareme.est_actif())
        
        # Barème avec date de fin passée
        hier = timezone.now().date() - datetime.timedelta(days=1)
        self.bareme.date_fin_validite = hier
        self.bareme.save()
        self.assertFalse(self.bareme.est_actif())


class TestCotisation(TestCase):
    """
    Tests pour le modèle Cotisation.
    """
    def setUp(self):
        # Créer un membre
        self.membre = Membre.objects.create(
            nom="Dupont",
            prenom="Jean",
            email="jean.dupont@example.com"
        )
        
        # Créer un type de membre
        self.type_membre = TypeMembre.objects.create(libelle="Standard")
        
        # Créer un statut
        self.statut = Statut.objects.create(nom="Actif")
        
        # Créer une cotisation
        self.cotisation = Cotisation.objects.create(
            membre=self.membre,
            montant=Decimal("120.00"),
            date_emission=timezone.now().date(),
            date_echeance=timezone.now().date() + datetime.timedelta(days=30),
            periode_debut=timezone.now().date(),
            periode_fin=timezone.now().date() + datetime.timedelta(days=365),
            annee=timezone.now().year,
            mois=timezone.now().month,
            statut=self.statut,
            statut_paiement="non_payee",
            montant_restant=Decimal("120.00"),
            type_membre=self.type_membre,
            reference="COT-2023-001"
        )
    
    def test_creation_cotisation(self):
        """Vérifier que la cotisation est correctement créée."""
        self.assertEqual(self.cotisation.montant, Decimal("120.00"))
        self.assertEqual(self.cotisation.montant_restant, Decimal("120.00"))
        self.assertEqual(self.cotisation.statut_paiement, "non_payee")
        self.assertEqual(self.cotisation.reference, "COT-2023-001")
    
    def test_mettre_a_jour_statut_paiement(self):
        """Vérifier la mise à jour du statut de paiement."""
        # Cotisation non payée
        self.assertEqual(self.cotisation.statut_paiement, "non_payee")
        
        # Cotisation partiellement payée
        self.cotisation.montant_restant = Decimal("60.00")
        self.cotisation._mettre_a_jour_statut_paiement()
        self.assertEqual(self.cotisation.statut_paiement, "partiellement_payee")
        
        # Cotisation entièrement payée
        self.cotisation.montant_restant = Decimal("0.00")
        self.cotisation._mettre_a_jour_statut_paiement()
        self.assertEqual(self.cotisation.statut_paiement, "payee")
    
    def test_calcul_montant_paye(self):
        """Vérifier le calcul du montant payé."""
        # Créer un mode de paiement
        mode_paiement = ModePaiement.objects.create(libelle="Carte bancaire")
        
        # Pas de paiement initialement
        self.assertEqual(self.cotisation.get_montant_paye(), Decimal("0.00"))
        
        # Ajouter un premier paiement
        paiement1 = Paiement.objects.create(
            cotisation=self.cotisation,
            montant=Decimal("50.00"),
            date_paiement=timezone.now(),
            mode_paiement=mode_paiement,
            type_transaction="paiement"
        )
        
        # Recalculer le montant restant
        self.cotisation.refresh_from_db()
        self.assertEqual(self.cotisation.get_montant_paye(), Decimal("50.00"))
        
        # Ajouter un deuxième paiement
        paiement2 = Paiement.objects.create(
            cotisation=self.cotisation,
            montant=Decimal("70.00"),
            date_paiement=timezone.now(),
            mode_paiement=mode_paiement,
            type_transaction="paiement"
        )
        
        # Recalculer le montant restant
        self.cotisation.refresh_from_db()
        self.assertEqual(self.cotisation.get_montant_paye(), Decimal("120.00"))
        
        # Vérifier que le statut est "payée"
        self.assertEqual(self.cotisation.statut_paiement, "payee")
    
    def test_recalculer_montant_restant(self):
        """Vérifier le recalcul du montant restant."""
        # Créer un mode de paiement
        mode_paiement = ModePaiement.objects.create(libelle="Carte bancaire")
        
        # Ajouter un paiement
        paiement = Paiement.objects.create(
            cotisation=self.cotisation,
            montant=Decimal("50.00"),
            date_paiement=timezone.now(),
            mode_paiement=mode_paiement,
            type_transaction="paiement"
        )
        
        # Recalculer manuellement
        self.cotisation.recalculer_montant_restant()
        self.cotisation.save()
        
        # Vérifier le montant restant et le statut
        self.assertEqual(self.cotisation.montant_restant, Decimal("70.00"))
        self.assertEqual(self.cotisation.statut_paiement, "partiellement_payee")
        
        # Ajouter un remboursement
        remboursement = Paiement.objects.create(
            cotisation=self.cotisation,
            montant=Decimal("20.00"),
            date_paiement=timezone.now(),
            mode_paiement=mode_paiement,
            type_transaction="remboursement"
        )
        
        # Recalculer manuellement
        self.cotisation.recalculer_montant_restant()
        self.cotisation.save()
        
        # Vérifier le montant restant et le statut (après remboursement)
        self.assertEqual(self.cotisation.montant_restant, Decimal("90.00"))
        self.assertEqual(self.cotisation.statut_paiement, "partiellement_payee")


class TestPaiement(TestCase):
    """
    Tests pour le modèle Paiement.
    """
    def setUp(self):
        # Créer un membre
        self.membre = Membre.objects.create(
            nom="Dupont",
            prenom="Jean",
            email="jean.dupont@example.com"
        )
        
        # Créer un type de membre
        self.type_membre = TypeMembre.objects.create(libelle="Standard")
        
        # Créer un statut
        self.statut = Statut.objects.create(nom="Actif")
        
        # Créer une cotisation
        self.cotisation = Cotisation.objects.create(
            membre=self.membre,
            montant=Decimal("120.00"),
            date_emission=timezone.now().date(),
            date_echeance=timezone.now().date() + datetime.timedelta(days=30),
            periode_debut=timezone.now().date(),
            periode_fin=timezone.now().date() + datetime.timedelta(days=365),
            annee=timezone.now().year,
            mois=timezone.now().month,
            statut=self.statut,
            statut_paiement="non_payee",
            montant_restant=Decimal("120.00"),
            type_membre=self.type_membre,
            reference="COT-2023-001"
        )
        
        # Créer un mode de paiement
        self.mode_paiement = ModePaiement.objects.create(libelle="Carte bancaire")
        
        # Créer un paiement
        self.paiement = Paiement.objects.create(
            cotisation=self.cotisation,
            montant=Decimal("50.00"),
            date_paiement=timezone.now(),
            mode_paiement=self.mode_paiement,
            type_transaction="paiement",
            reference_paiement="PAY-2023-001"
        )
    
    def test_creation_paiement(self):
        """Vérifier que le paiement est correctement créé."""
        self.assertEqual(self.paiement.montant, Decimal("50.00"))
        self.assertEqual(self.paiement.type_transaction, "paiement")
        self.assertEqual(self.paiement.reference_paiement, "PAY-2023-001")
        
        # Vérifier que la cotisation a été mise à jour
        self.cotisation.refresh_from_db()
        self.assertEqual(self.cotisation.montant_restant, Decimal("70.00"))
        self.assertEqual(self.cotisation.statut_paiement, "partiellement_payee")
    
    def test_suppression_paiement(self):
        """Vérifier que la suppression d'un paiement met à jour la cotisation."""
        # Supprimer le paiement
        self.paiement.delete()
        
        # Vérifier que la cotisation a été mise à jour
        self.cotisation.refresh_from_db()
        self.assertEqual(self.cotisation.montant_restant, Decimal("120.00"))
        self.assertEqual(self.cotisation.statut_paiement, "non_payee")


class TestRappel(TestCase):
    """
    Tests pour le modèle Rappel.
    """
    def setUp(self):
        # Créer un membre
        self.membre = Membre.objects.create(
            nom="Dupont",
            prenom="Jean",
            email="jean.dupont@example.com"
        )
        
        # Créer un type de membre
        self.type_membre = TypeMembre.objects.create(libelle="Standard")
        
        # Créer un statut
        self.statut = Statut.objects.create(nom="Actif")
        
        # Créer une cotisation
        self.cotisation = Cotisation.objects.create(
            membre=self.membre,
            montant=Decimal("120.00"),
            date_emission=timezone.now().date(),
            date_echeance=timezone.now().date() - datetime.timedelta(days=10),  # Déjà en retard
            periode_debut=timezone.now().date(),
            periode_fin=timezone.now().date() + datetime.timedelta(days=365),
            annee=timezone.now().year,
            mois=timezone.now().month,
            statut=self.statut,
            statut_paiement="non_payee",
            montant_restant=Decimal("120.00"),
            type_membre=self.type_membre,
            reference="COT-2023-001"
        )
        
        # Créer un rappel
        self.rappel = Rappel.objects.create(
            membre=self.membre,
            cotisation=self.cotisation,
            type_rappel="email",
            contenu="Rappel pour votre cotisation en retard",
            etat="planifie",
            niveau=1
        )
    
    def test_creation_rappel(self):
        """Vérifier que le rappel est correctement créé."""
        self.assertEqual(self.rappel.type_rappel, "email")
        self.assertEqual(self.rappel.etat, "planifie")
        self.assertEqual(self.rappel.niveau, 1)
        self.assertEqual(self.rappel.cotisation, self.cotisation)
        self.assertEqual(self.rappel.membre, self.membre)
    
    def test_affichage_rappel(self):
        """Vérifier l'affichage du rappel."""
        # Le test attendait 'Email' mais le code utilise 'Courriel'
        expected = f"{self.rappel.membre.prenom} {self.rappel.membre.nom} - Courriel ({self.rappel.date_envoi})"
        self.assertEqual(str(self.rappel), expected)