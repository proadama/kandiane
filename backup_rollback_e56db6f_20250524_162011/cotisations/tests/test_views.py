# apps/cotisations/tests/test_views.py
from decimal import Decimal
import json
import datetime
from datetime import date, timedelta
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


class CotisationViewsTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Créer un utilisateur staff pour les tests
        cls.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword',
            is_staff=True  # Important: attribuer le statut staff
        )
        
        # Créer les données nécessaires
        cls.statut = Statut.objects.create(nom='Actif')
        cls.type_membre = TypeMembre.objects.create(libelle='Membre standard')
        cls.membre = Membre.objects.create(
            nom='Dupont',
            prenom='Jean',
            email='jean.dupont@example.com',
            statut=cls.statut
        )
        
        # Utiliser des objets date au lieu de chaînes
        today = timezone.now().date()
        
        cls.cotisation = Cotisation.objects.create(
            membre=cls.membre,
            montant=Decimal('100.00'),
            date_emission=today,
            date_echeance=today + timedelta(days=30),
            periode_debut=today,
            periode_fin=date(today.year + 1, today.month, today.day) - timedelta(days=1),
            annee=today.year,
            mois=today.month,
            type_membre=cls.type_membre,
            reference='COT-TEST-001',
            montant_restant=Decimal('100.00')
        )
        
        # Créer un mode de paiement pour le test paiement_ajax_create
        cls.mode_paiement = ModePaiement.objects.create(libelle='Virement')
    
    def setUp(self):
        # Se connecter avant chaque test
        self.client.force_login(self.user)
    
    def test_dashboard_view(self):
        response = self.client.get(reverse('cotisations:dashboard'))
        self.assertEqual(response.status_code, 200)
    
    def test_cotisation_list_view(self):
        response = self.client.get(reverse('cotisations:cotisation_liste'))
        self.assertEqual(response.status_code, 200)
        
    def test_cotisation_detail_view(self):
        response = self.client.get(reverse('cotisations:cotisation_detail', args=[self.cotisation.id]))
        self.assertEqual(response.status_code, 200)
        
    def test_cotisation_create_view(self):
        response = self.client.get(reverse('cotisations:cotisation_creer'))
        self.assertEqual(response.status_code, 200)
    
    def test_paiement_ajax_create(self):
        """Teste la création d'un paiement via AJAX."""
        # Données du paiement
        payment_data = {
            'montant': '60.00',
            'mode_paiement': self.mode_paiement.pk,
            'date_paiement': timezone.now().strftime('%Y-%m-%dT%H:%M:%S'),
            'type_transaction': 'paiement',
            'reference_paiement': 'TEST-123'
        }
        
        # Envoyer la requête AJAX
        response = self.client.post(
            reverse('cotisations:paiement_create_ajax', kwargs={'cotisation_id': self.cotisation.pk}),
            data=json.dumps(payment_data),
            content_type='application/json'
        )
        
        # Vérifier la réponse
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        
        # Vérifier que le paiement a été créé
        self.assertEqual(Paiement.objects.count(), 1)
        paiement = Paiement.objects.first()
        self.assertEqual(paiement.montant, Decimal('60.00'))
        
        # Vérifier que la cotisation a été mise à jour
        self.cotisation.refresh_from_db()
        self.assertEqual(self.cotisation.montant_restant, Decimal('40.00'))
        self.assertEqual(self.cotisation.statut_paiement, 'partiellement_payee')


class TestDashboardView(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Créer un utilisateur staff pour les tests
        cls.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword',
            is_staff=True
        )
    
    def setUp(self):
        # Se connecter avant chaque test
        self.client.force_login(self.user)
    
    def test_dashboard_access(self):
        response = self.client.get(reverse('cotisations:dashboard'))
        self.assertEqual(response.status_code, 200)
        
    def test_dashboard_context(self):
        response = self.client.get(reverse('cotisations:dashboard'))
        self.assertEqual(response.status_code, 200)
        # Vérifier la présence des variables de contexte clés
        self.assertIn('total_cotisations', response.context)
        self.assertIn('montant_total', response.context)
        self.assertIn('taux_recouvrement', response.context)


class TestCotisationListView(TestCase):
    """
    Tests pour la vue CotisationListView.
    """
    def setUp(self):
        # Créer un utilisateur staff
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass',
            email='testuser@example.com',
            is_staff=True
        )
        self.client = Client()
        self.client.force_login(self.user)
        
        # Créer un membre, un type, un statut
        self.membre = Membre.objects.create(
            nom="Dupont",
            prenom="Jean",
            email="jean.dupont@example.com"
        )
        self.type_membre = TypeMembre.objects.create(libelle="Standard")
        self.statut = Statut.objects.create(nom="Actif")
        
        # Créer quelques cotisations
        for i in range(5):
            Cotisation.objects.create(
                membre=self.membre,
                montant=Decimal("100.00"),
                date_emission=timezone.now().date(),
                date_echeance=timezone.now().date() + datetime.timedelta(days=30),
                periode_debut=timezone.now().date(),
                periode_fin=timezone.now().date() + datetime.timedelta(days=365),
                annee=timezone.now().year,
                mois=timezone.now().month,
                statut=self.statut,
                statut_paiement="non_payee",
                montant_restant=Decimal("100.00"),
                type_membre=self.type_membre,
                reference=f"COT-2023-00{i+1}"
            )
    
    def test_cotisation_list_access(self):
        """Vérifier que la liste des cotisations est accessible pour un utilisateur staff."""
        response = self.client.get(reverse('cotisations:cotisation_liste'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'cotisations/cotisation_liste.html')
    
    def test_cotisation_list_content(self):
        """Vérifier que la liste contient les cotisations."""
        response = self.client.get(reverse('cotisations:cotisation_liste'))
        self.assertEqual(response.status_code, 200)
        
        self.assertIn('cotisations', response.context)
        self.assertEqual(len(response.context['cotisations']), 5)
    
    def test_cotisation_list_search(self):
        """Vérifier que la recherche fonctionne."""
        # Recherche par référence
        response = self.client.get(reverse('cotisations:cotisation_liste') + '?reference=COT-2023-001')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['cotisations']), 1)
        
        # Recherche par nom de membre
        response = self.client.get(reverse('cotisations:cotisation_liste') + '?terme=Dupont')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['cotisations']), 5)
        
        # Recherche sans résultat
        response = self.client.get(reverse('cotisations:cotisation_liste') + '?terme=Inexistant')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['cotisations']), 0)


class TestPaiementCreateView(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Créer un utilisateur staff pour les tests
        cls.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword',
            is_staff=True
        )
        
        # Créer les données nécessaires
        cls.statut = Statut.objects.create(nom='Actif')
        cls.type_membre = TypeMembre.objects.create(libelle='Membre standard')
        cls.membre = Membre.objects.create(
            nom='Dupont',
            prenom='Jean',
            email='jean.dupont@example.com',
            statut=cls.statut
        )
        
        # Utiliser des objets date au lieu de chaînes
        today = date.today()
        
        cls.cotisation = Cotisation.objects.create(
            membre=cls.membre,
            montant=Decimal('100.00'),
            date_emission=today,
            date_echeance=today + timedelta(days=30),
            periode_debut=today,
            periode_fin=date(today.year + 1, today.month, today.day) - timedelta(days=1),
            annee=today.year,
            mois=today.month,
            type_membre=cls.type_membre,
            reference='COT-TEST-001',
            montant_restant=Decimal('100.00')
        )
        
        cls.mode_paiement = ModePaiement.objects.create(libelle='Virement')
    
    def setUp(self):
        # Se connecter avant chaque test
        self.client.force_login(self.user)
    
    def test_paiement_create_form_display(self):
        response = self.client.get(reverse('cotisations:paiement_creer', args=[self.cotisation.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'cotisations/paiement_form.html')
        
    def test_paiement_create_success(self):
        data = {
            'montant': '50.00',
            'mode_paiement': self.mode_paiement.id,
            'date_paiement': timezone.now().strftime('%Y-%m-%dT%H:%M:%S'),
            'type_transaction': 'paiement',
            'reference_paiement': 'REF-TEST-001',
            'commentaire': 'Test paiement'
        }
        
        response = self.client.post(
            reverse('cotisations:paiement_creer', args=[self.cotisation.id]),
            data
        )
        
        # Vérifier la redirection
        self.assertRedirects(response, reverse('cotisations:cotisation_detail', args=[self.cotisation.id]))
        
        # Vérifier que le paiement est créé
        paiement = Paiement.objects.filter(cotisation=self.cotisation).first()
        self.assertIsNotNone(paiement)
        self.assertEqual(paiement.montant, Decimal('50.00'))
        
        # Vérifier que la cotisation est mise à jour
        self.cotisation.refresh_from_db()
        self.assertEqual(self.cotisation.montant_restant, Decimal('50.00'))
        self.assertEqual(self.cotisation.statut_paiement, 'partiellement_payee')


class TestApiCalculerMontant(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Créer un utilisateur staff pour les tests
        cls.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword',
            is_staff=True
        )
        
        # Créer un type de membre
        cls.type_membre = TypeMembre.objects.create(libelle='Membre standard')
        
        # Créer un barème
        cls.bareme = BaremeCotisation.objects.create(
            type_membre=cls.type_membre,
            montant=Decimal('150.00'),
            date_debut_validite=timezone.now().date(),
            periodicite='annuelle'
        )
    
    def setUp(self):
        # Force authentication for each test
        self.client.force_login(self.user)
    
    def test_api_calculer_montant_par_bareme(self):
        url = f"{reverse('cotisations:api_calculer_montant')}?bareme_id={self.bareme.id}"
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(data['montant'], float(self.bareme.montant))
    
    def test_api_calculer_montant_par_type_membre(self):
        url = f"{reverse('cotisations:api_calculer_montant')}?type_membre_id={self.type_membre.id}"
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(data['montant'], float(self.bareme.montant))
    
    def test_api_calculer_montant_bareme_inexistant(self):
        # Utiliser un ID qui n'existe probablement pas
        url = f"{reverse('cotisations:api_calculer_montant')}?bareme_id=999"
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertFalse(data['success'])