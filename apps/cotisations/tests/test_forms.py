# apps/cotisations/tests/test_forms.py
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone

from apps.membres.models import Membre, TypeMembre
from apps.core.models import Statut
from apps.cotisations.models import Cotisation, ModePaiement, BaremeCotisation
from apps.cotisations.forms import CotisationForm, PaiementForm, RappelForm, BaremeCotisationForm


class CotisationFormTest(TestCase):
    """Tests pour le formulaire CotisationForm."""
    
    def setUp(self):
        # Créer les données de base pour les tests
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
        
        self.bareme = BaremeCotisation.objects.create(
            type_membre=self.type_membre,
            montant=Decimal('120.00'),
            date_debut_validite=timezone.now().date(),
            periodicite='annuelle'
        )
        
        # Dates pour les tests
        self.today = timezone.now().date()
        self.date_echeance = self.today + timezone.timedelta(days=30)
        
        # Données de formulaire valides
        self.valid_data = {
            'membre': self.membre.pk,
            'type_membre': self.type_membre.pk,
            'montant': Decimal('120.00'),
            'date_emission': self.today,
            'date_echeance': self.date_echeance,
            'periode_debut': self.today,
            'periode_fin': self.today.replace(year=self.today.year + 1),
            'statut': self.statut.pk,
            'generer_reference': True,
            'utiliser_bareme': False
        }
    
    def test_valid_form(self):
        """Teste la validation d'un formulaire avec des données valides."""
        form = CotisationForm(data=self.valid_data)
        self.assertTrue(form.is_valid())
    
    def test_date_validation(self):
        """Teste la validation des dates."""
        # Date d'échéance antérieure à la date d'émission
        invalid_data = self.valid_data.copy()
        invalid_data['date_echeance'] = self.today - timezone.timedelta(days=1)
        
        form = CotisationForm(data=invalid_data)
        self.assertFalse(form.is_valid())
        self.assertIn('date_echeance', form.errors)
    
    def test_montant_validation(self):
        """Teste la validation du montant."""
        # Montant négatif
        invalid_data = self.valid_data.copy()
        invalid_data['montant'] = Decimal('-10.00')
        
        form = CotisationForm(data=invalid_data)
        self.assertFalse(form.is_valid())
        self.assertIn('montant', form.errors)
        
        # Montant nul
        invalid_data['montant'] = Decimal('0.00')
        form = CotisationForm(data=invalid_data)
        self.assertFalse(form.is_valid())
        self.assertIn('montant', form.errors)
    
    def test_reference_validation(self):
        """Teste la validation de la référence."""
        # Sans génération automatique et sans référence
        invalid_data = self.valid_data.copy()
        invalid_data['generer_reference'] = False
        invalid_data['reference'] = ''
        
        form = CotisationForm(data=invalid_data)
        self.assertFalse(form.is_valid())
        self.assertIn('reference', form.errors)
        
        # Sans génération automatique mais avec référence
        valid_data = self.valid_data.copy()
        valid_data['generer_reference'] = False
        valid_data['reference'] = 'COT-2025-TEST'
        
        form = CotisationForm(data=valid_data)
        self.assertTrue(form.is_valid())


class PaiementFormTest(TestCase):
    """Tests pour le formulaire PaiementForm."""
    
    def setUp(self):
        # Créer les données nécessaires
        self.membre = Membre.objects.create(
            nom="Dupont",
            prenom="Jean",
            email="jean.dupont@example.com",
            date_adhesion=timezone.now().date()
        )
        
        self.type_membre = TypeMembre.objects.create(
            libelle="Membre standard"
        )
        
        self.cotisation = Cotisation.objects.create(
            membre=self.membre,
            type_membre=self.type_membre,
            montant=Decimal('120.00'),
            date_emission=timezone.now().date(),
            date_echeance=timezone.now().date() + timezone.timedelta(days=30),
            periode_debut=timezone.now().date(),
            periode_fin=timezone.now().date().replace(year=timezone.now().date().year + 1),
            annee=timezone.now().date().year,
            montant_restant=Decimal('120.00')
        )
        
        self.mode_paiement = ModePaiement.objects.create(
            libelle="Carte bancaire"
        )
        
        # Données valides
        self.valid_data = {
            'montant': Decimal('50.00'),
            'mode_paiement': self.mode_paiement.pk,
            'date_paiement': timezone.now(),
            'type_transaction': 'paiement',
            'reference_paiement': 'CB-123456'
        }
    
    def test_valid_form(self):
        """Teste la validation avec des données valides."""
        form = PaiementForm(data=self.valid_data, cotisation=self.cotisation)
        self.assertTrue(form.is_valid())
    
    def test_montant_validation(self):
        """Teste la validation du montant."""
        # Montant négatif
        invalid_data = self.valid_data.copy()
        invalid_data['montant'] = Decimal('-10.00')
        
        form = PaiementForm(data=invalid_data, cotisation=self.cotisation)
        self.assertFalse(form.is_valid())
        self.assertIn('montant', form.errors)
        
        # Montant supérieur au montant restant pour un paiement
        invalid_data = self.valid_data.copy()
        invalid_data['montant'] = Decimal('150.00')  # > 120.00
        
        form = PaiementForm(data=invalid_data, cotisation=self.cotisation)
        self.assertFalse(form.is_valid())
        self.assertIn('montant', form.errors)
        
        # Montant supérieur au montant restant mais pour un remboursement (devrait être valide)
        valid_data = self.valid_data.copy()
        valid_data['montant'] = Decimal('150.00')
        valid_data['type_transaction'] = 'remboursement'
        
        form = PaiementForm(data=valid_data, cotisation=self.cotisation)
        self.assertTrue(form.is_valid())

# Ajouter des tests pour les autres formulaires...