# apps/cotisations/tests/test_api.py
from decimal import Decimal
import datetime
import json

from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model

from apps.membres.models import Membre, TypeMembre
from apps.core.models import Statut
from apps.cotisations.models import (
    Cotisation, Paiement, ModePaiement, BaremeCotisation, Rappel
)

User = get_user_model()

class TestApiCalculerMontant(TestCase):
    """Tests pour l'API api_calculer_montant."""
    def setUp(self):
        import time
        timestamp = int(time.time())
        
        # Créer un utilisateur staff
        self.user = User.objects.create_user(
            username=f"test_{self.__class__.__name__}_{timestamp}",
            email=f"test_{self.__class__.__name__}_{timestamp}@example.com",
            password="password123",
            is_staff=True
        )
        
        # Force l'authentification sans passer par login()
        self.client.force_login(self.user)
        
        # Créer un type de membre
        self.type_membre = TypeMembre.objects.create(libelle="Standard")
        
        # Créer un barème
        self.bareme = BaremeCotisation.objects.create(
            type_membre=self.type_membre,
            montant=Decimal("120.00"),
            date_debut_validite=timezone.now().date() - datetime.timedelta(days=10),
            periodicite="annuelle"
        )
    
    def test_api_calculer_montant_bareme(self):
        """Vérifier que l'API renvoie le montant correct pour un barème."""
        response = self.client.get(reverse('cotisations:api_calculer_montant') + f'?bareme_id={self.bareme.id}')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(data['montant'], float(self.bareme.montant))
        self.assertEqual(data['periodicite'], self.bareme.get_periodicite_display())
    
    def test_api_calculer_montant_type_membre(self):
        """Vérifier que l'API renvoie le montant correct pour un type de membre."""
        response = self.client.get(reverse('cotisations:api_calculer_montant') + f'?type_membre_id={self.type_membre.id}')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(data['montant'], float(self.bareme.montant))
        self.assertEqual(data['periodicite'], self.bareme.get_periodicite_display())
    
    def test_api_calculer_montant_no_params(self):
        """Vérifier que l'API renvoie une erreur si aucun paramètre n'est spécifié."""
        response = self.client.get(reverse('cotisations:api_calculer_montant'))
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertFalse(data['success'])
        self.assertIn('message', data)


class TestPaiementCreateAjax(TestCase):
    """Tests pour l'API paiement_create_ajax."""
    def setUp(self):
        import time
        timestamp = int(time.time())
        
        # Créer un utilisateur staff
        self.user = User.objects.create_user(
            username=f"test_{self.__class__.__name__}_{timestamp}",
            email=f"test_{self.__class__.__name__}_{timestamp}@example.com",
            password="password123",
            is_staff=True
        )
        
        # Force l'authentification sans passer par login()
        self.client.force_login(self.user)

        
        # Créer un membre, un type, un statut
        self.user = User.objects.create_user(username="test_user", email="test@example.com", password="password123", is_staff=True)
        self.membre = Membre.objects.create(nom="Dupont", prenom="Jean", email="test@example.com", utilisateur_id=self.user.id)
        self.type_membre = TypeMembre.objects.create(libelle="Standard")
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
    
    def test_paiement_create_ajax_json(self):
        """Vérifier que la création de paiement via AJAX avec JSON fonctionne."""
        data = {
            'montant': 50.00,
            'mode_paiement': self.mode_paiement.id,
            'date_paiement': timezone.now().strftime('%Y-%m-%dT%H:%M'),
            'type_transaction': 'paiement',
            'reference_paiement': 'PAY-2023-001',
            'commentaire': 'Test de paiement AJAX'
        }
        
        response = self.client.post(
            reverse('cotisations:paiement_create_ajax', args=[self.cotisation.id]),
            json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        self.assertIn('paiement', response_data)
        self.assertIn('cotisation', response_data)
        
        # Vérifier que le paiement a été créé
        self.assertTrue(Paiement.objects.filter(cotisation=self.cotisation, montant=50.00).exists())
        
        # Vérifier que la cotisation a été mise à jour
        self.cotisation.refresh_from_db()
        self.assertEqual(self.cotisation.montant_restant, Decimal('70.00'))
        self.assertEqual(self.cotisation.statut_paiement, 'partiellement_payee')
    
    def test_paiement_create_ajax_form(self):
        """Vérifier que la création de paiement via AJAX avec form-data fonctionne."""
        data = {
            'montant': '50.00',
            'mode_paiement': self.mode_paiement.id,
            'date_paiement': timezone.now().strftime('%Y-%m-%dT%H:%M'),
            'type_transaction': 'paiement',
            'reference_paiement': 'PAY-2023-001',
            'commentaire': 'Test de paiement AJAX'
        }
        
        response = self.client.post(
            reverse('cotisations:paiement_create_ajax', args=[self.cotisation.id]),
            data
        )
        
        self.assertEqual(response.status_code, 200)
        
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        self.assertIn('paiement', response_data)
        self.assertIn('cotisation', response_data)
        
        # Vérifier que le paiement a été créé
        self.assertTrue(Paiement.objects.filter(cotisation=self.cotisation, montant=50.00).exists())
        
        # Vérifier que la cotisation a été mise à jour
        self.cotisation.refresh_from_db()
        self.assertEqual(self.cotisation.montant_restant, Decimal('70.00'))
        self.assertEqual(self.cotisation.statut_paiement, 'partiellement_payee')
    
    def test_paiement_create_ajax_invalid(self):
        """Vérifier que l'API renvoie une erreur si les données sont invalides."""
        data = {
            'montant': -50.00,  # Montant négatif invalide
            'mode_paiement': self.mode_paiement.id,
            'date_paiement': timezone.now().strftime('%Y-%m-%dT%H:%M'),
            'type_transaction': 'paiement'
        }
        
        response = self.client.post(
            reverse('cotisations:paiement_create_ajax', args=[self.cotisation.id]),
            json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        
        response_data = json.loads(response.content)
        self.assertFalse(response_data['success'])
        self.assertIn('errors', response_data)


class TestRappelCreateAjax(TestCase):
    """Tests pour l'API rappel_create_ajax."""
    def setUp(self):
        import time
        timestamp = int(time.time())
        
        # Créer un utilisateur staff
        self.user = User.objects.create_user(
            username=f"test_{self.__class__.__name__}_{timestamp}",
            email=f"test_{self.__class__.__name__}_{timestamp}@example.com",
            password="password123",
            is_staff=True
        )
        
        # Force l'authentification sans passer par login()
        self.client.force_login(self.user)
        
        # Créer un membre, un type, un statut
        self.user = User.objects.create_user(username="test_user", email="test@example.com", password="password123", is_staff=True)
        self.membre = Membre.objects.create(nom="Dupont", prenom="Jean", email="test@example.com", utilisateur_id=self.user.id)
        self.type_membre = TypeMembre.objects.create(libelle="Standard")
        self.statut = Statut.objects.create(nom="Actif")
        
        # Créer une cotisation
        self.cotisation = Cotisation.objects.create(
            membre=self.membre,
            montant=Decimal("120.00"),
            date_emission=timezone.now().date(),
            date_echeance=timezone.now().date() - datetime.timedelta(days=10),  # En retard
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
    
    def test_rappel_create_ajax_json(self):
        """Vérifier que la création de rappel via AJAX avec JSON fonctionne."""
        data = {
            'type_rappel': 'email',
            'niveau': 1,
            'contenu': 'Rappel pour votre cotisation en retard',
            'planifie': 'false'
        }
        
        response = self.client.post(
            reverse('cotisations:rappel_create_ajax', args=[self.cotisation.id]),
            json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        self.assertIn('rappel', response_data)
        
        # Vérifier que le rappel a été créé
        self.assertTrue(Rappel.objects.filter(cotisation=self.cotisation, type_rappel='email').exists())
    
    def test_rappel_create_ajax_form(self):
        """Vérifier que la création de rappel via AJAX avec form-data fonctionne."""
        data = {
            'type_rappel': 'email',
            'niveau': 1,
            'contenu': 'Rappel pour votre cotisation en retard'
        }
        
        response = self.client.post(
            reverse('cotisations:rappel_create_ajax', args=[self.cotisation.id]),
            data
        )
        
        self.assertEqual(response.status_code, 200)
        
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        self.assertIn('rappel', response_data)
        
        # Vérifier que le rappel a été créé
        self.assertTrue(Rappel.objects.filter(cotisation=self.cotisation, type_rappel='email').exists())
    
    def test_rappel_create_ajax_invalid(self):
        """Vérifier que l'API renvoie une erreur si les données sont invalides."""
        data = {
            'niveau': 1,  # Type de rappel manquant
            'contenu': 'Rappel pour votre cotisation en retard'
        }
        
        response = self.client.post(
            reverse('cotisations:rappel_create_ajax', args=[self.cotisation.id]),
            json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        
        response_data = json.loads(response.content)
        self.assertFalse(response_data['success'])
        self.assertIn('errors', response_data)