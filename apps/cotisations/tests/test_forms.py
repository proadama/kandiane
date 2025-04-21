# apps/cotisations/tests/test_forms.py
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
import time

from apps.membres.models import Membre, TypeMembre
from apps.core.models import Statut
from apps.cotisations.models import Cotisation, ModePaiement, BaremeCotisation, Rappel
from apps.cotisations.forms import CotisationForm, PaiementForm, RappelForm, BaremeCotisationForm

from decimal import Decimal
import datetime
from django.contrib.auth import get_user_model

User = get_user_model()

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
        
        self.user = User.objects.create_user(username="test_user", email=f"test{int(time.time())}@example.com", password="password123", is_staff=True)
        self.membre = Membre.objects.create(nom="Dupont", prenom="Jean", email=f"test{int(time.time())}@example.com", utilisateur_id=self.user.id)

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
        form = CotisationForm(data=self.form_data)
        if not form.is_valid():
            print("Erreurs du formulaire:", form.errors)
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
        self.user = User.objects.create_user(username="test_user", email=f"test{int(time.time())}@example.com", password="password123", is_staff=True)
        self.membre = Membre.objects.create(nom="Dupont", prenom="Jean", email=f"test{int(time.time())}@example.com", utilisateur_id=self.user.id)
        
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

class TestBaremeCotisationForm(TestCase):
    """
    Tests pour le formulaire BaremeCotisationForm.
    """
    def setUp(self):
        # Créer un type de membre
        self.type_membre = TypeMembre.objects.create(libelle="Standard")
    
    def test_form_valid(self):
        """Vérifier que le formulaire est valide avec des données correctes."""
        form_data = {
            'type_membre': self.type_membre.id,
            'montant': Decimal("120.00"),
            'date_debut_validite': timezone.now().date(),
            'periodicite': 'annuelle',
            'description': 'Cotisation annuelle standard'
        }
        form = BaremeCotisationForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_form_date_fin_before_date_debut(self):
        """Vérifier que le formulaire est invalide si la date de fin est avant la date de début."""
        aujourd_hui = timezone.now().date()
        hier = aujourd_hui - datetime.timedelta(days=1)
        
        form_data = {
            'type_membre': self.type_membre.id,
            'montant': Decimal("120.00"),
            'date_debut_validite': aujourd_hui,
            'date_fin_validite': hier,
            'periodicite': 'annuelle'
        }
        form = BaremeCotisationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('date_fin_validite', form.errors)


class TestCotisationForm(TestCase):
    """
    Tests pour le formulaire CotisationForm.
    """
    def setUp(self):
        # Créer un utilisateur
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass',
            email='testuser@example.com',
            is_staff=True
        )
        
        # Créer un membre
        self.user = User.objects.create_user(username="test_user", email=f"test{int(time.time())}@example.com", password="password123", is_staff=True)
        self.membre = Membre.objects.create(nom="Dupont", prenom="Jean", email=f"test{int(time.time())}@example.com", utilisateur_id=self.user.id)
        
        # Créer un type de membre
        self.type_membre = TypeMembre.objects.create(libelle="Standard")
        
        # Créer un statut
        self.statut = Statut.objects.create(nom="Actif")
        
        # Créer un barème
        self.bareme = BaremeCotisation.objects.create(
            type_membre=self.type_membre,
            montant=Decimal("120.00"),
            date_debut_validite=timezone.now().date(),
            periodicite="annuelle"
        )
    
    def test_form_valid_creation_auto_reference(self):
        """Vérifier que le formulaire est valide avec génération automatique de référence."""
        today = timezone.now().date()
        form_data = {
            'membre': self.membre.id,
            'type_membre': self.type_membre.id,
            'bareme': self.bareme.id,
            'montant': Decimal("120.00"),
            'date_emission': today,
            'date_echeance': today + datetime.timedelta(days=30),
            'periode_debut': today,
            'periode_fin': today + datetime.timedelta(days=365),
            'statut': self.statut.id,
            'generer_reference': True,
            'utiliser_bareme': True
        }
        form = CotisationForm(data=form_data, user=self.user)
        self.assertTrue(form.is_valid())
    
    def test_form_invalid_date_echeance_before_emission(self):
        """Vérifier que le formulaire est invalide si la date d'échéance est avant la date d'émission."""
        today = timezone.now().date()
        yesterday = today - datetime.timedelta(days=1)
        
        form_data = {
            'membre': self.membre.id,
            'type_membre': self.type_membre.id,
            'bareme': self.bareme.id,
            'montant': Decimal("120.00"),
            'date_emission': today,
            'date_echeance': yesterday,  # Date d'échéance avant date d'émission
            'periode_debut': today,
            'periode_fin': today + datetime.timedelta(days=365),
            'statut': self.statut.id,
            'generer_reference': True,
            'utiliser_bareme': True
        }
        form = CotisationForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('date_echeance', form.errors)
    
    def test_form_invalid_montant_negatif(self):
        """Vérifier que le formulaire est invalide avec un montant négatif."""
        today = timezone.now().date()
        
        form_data = {
            'membre': self.membre.id,
            'type_membre': self.type_membre.id,
            'bareme': self.bareme.id,
            'montant': Decimal("-10.00"),  # Montant négatif
            'date_emission': today,
            'date_echeance': today + datetime.timedelta(days=30),
            'periode_debut': today,
            'periode_fin': today + datetime.timedelta(days=365),
            'statut': self.statut.id,
            'generer_reference': True,
            'utiliser_bareme': True
        }
        form = CotisationForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('montant', form.errors)


class TestPaiementForm(TestCase):
    """
    Tests pour le formulaire PaiementForm.
    """
    def setUp(self):
        # Créer un utilisateur
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass',
            email='testuser@example.com',
            is_staff=True
        )
        
        # Créer un membre
        self.user = User.objects.create_user(username="test_user", email=f"test{int(time.time())}@example.com", password="password123", is_staff=True)
        self.membre = Membre.objects.create(nom="Dupont", prenom="Jean", email=f"test{int(time.time())}@example.com", utilisateur_id=self.user.id)
        
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
    
    def test_form_valid(self):
        """Vérifier que le formulaire est valide avec des données correctes."""
        form_data = {
            'montant': Decimal("50.00"),
            'mode_paiement': self.mode_paiement.id,
            'date_paiement': timezone.now(),
            'type_transaction': 'paiement',
            'reference_paiement': 'PAY-2023-001',
            'commentaire': 'Paiement par carte bancaire'
        }
        form = PaiementForm(data=form_data, user=self.user, cotisation=self.cotisation)
        self.assertTrue(form.is_valid())
    
    def test_form_invalid_montant_trop_eleve(self):
        """Vérifier que le formulaire est invalide si le montant est supérieur au montant restant."""
        form_data = {
            'montant': Decimal("150.00"),  # Supérieur au montant restant (120.00)
            'mode_paiement': self.mode_paiement.id,
            'date_paiement': timezone.now(),
            'type_transaction': 'paiement',
            'reference_paiement': 'PAY-2023-001'
        }
        form = PaiementForm(data=form_data, user=self.user, cotisation=self.cotisation)
        self.assertFalse(form.is_valid())
        self.assertIn('montant', form.errors)
    
    def test_form_valid_remboursement(self):
        """Vérifier que le formulaire est valide pour un remboursement (pas de limite de montant)."""
        form_data = {
            'montant': Decimal("150.00"),  # Supérieur au montant restant, mais c'est un remboursement
            'mode_paiement': self.mode_paiement.id,
            'date_paiement': timezone.now(),
            'type_transaction': 'remboursement',
            'reference_paiement': 'REMB-2023-001'
        }
        form = PaiementForm(data=form_data, user=self.user, cotisation=self.cotisation)
        self.assertTrue(form.is_valid())


class TestRappelForm(TestCase):
    """
    Tests pour le formulaire RappelForm.
    """
    def setUp(self):
        # Créer un utilisateur
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass',
            email='testuser@example.com',
            is_staff=True
        )
        
        # Créer un membre
        self.user = User.objects.create_user(username="test_user", email=f"test{int(time.time())}@example.com", password="password123", is_staff=True)
        self.membre = Membre.objects.create(nom="Dupont", prenom="Jean", email=f"test{int(time.time())}@example.com", utilisateur_id=self.user.id)
        
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
    
    def test_form_valid(self):
        """Vérifier que le formulaire est valide avec des données correctes."""
        form_data = {
            'type_rappel': 'email',
            'contenu': 'Rappel pour votre cotisation en retard',
            'niveau': 1
        }
        form = RappelForm(data=form_data, user=self.user, cotisation=self.cotisation)
        self.assertTrue(form.is_valid())
    
    def test_form_save(self):
        """Vérifier que le formulaire sauvegarde correctement un rappel."""
        form_data = {
            'type_rappel': 'email',
            'contenu': 'Rappel pour votre cotisation en retard',
            'niveau': 1
        }
        form = RappelForm(data=form_data, user=self.user, cotisation=self.cotisation)
        self.assertTrue(form.is_valid())
        
        rappel = form.save()
        self.assertEqual(rappel.type_rappel, 'email')
        self.assertEqual(rappel.cotisation, self.cotisation)
        self.assertEqual(rappel.membre, self.membre)
        self.assertEqual(rappel.etat, 'planifie')
        self.assertEqual(rappel.niveau, 1)