# apps/cotisations/tests/test_views.py
from decimal import Decimal
import json
import datetime
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
    """Tests pour les vues de l'application Cotisations."""
    
    def setUp(self):
        import time
        timestamp = int(time.time())
        
        # Définir explicitement le mot de passe
        self.password = "password123"
        
        # Créer un utilisateur avec droits d'administration
        self.user = User.objects.create_user(
            username=f"test_user_{timestamp}",
            email=f"test_user_{timestamp}@example.com",
            password=self.password,
            is_staff=True
        )
        
        # Authentifier l'utilisateur
        self.client.force_login(self.user)
        
        # Créer un client et s'identifier
        self.client = Client()
        self.client.login(username="test_user", password=self.password)
        
        # Créer des données pour les tests
        self.type_membre = TypeMembre.objects.create(
            libelle="Membre standard"
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
        
        self.today = timezone.now().date()
        
        # Créer une cotisation
        self.cotisation = Cotisation.objects.create(
            membre=self.membre,
            type_membre=self.type_membre,
            montant=Decimal('120.00'),
            date_emission=self.today,
            date_echeance=self.today + timezone.timedelta(days=30),
            periode_debut=self.today,
            periode_fin=self.today.replace(year=self.today.year + 1),
            annee=self.today.year,
            statut=self.statut,
            montant_restant=Decimal('120.00')
        )
        
        # Créer un mode de paiement
        self.mode_paiement = ModePaiement.objects.create(
            libelle="Carte bancaire"
        )
    
    def test_dashboard_view(self):
        """Teste l'accès au tableau de bord."""
        response = self.client.get(reverse('cotisations:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'cotisations/dashboard.html')
    
    def test_cotisation_list_view(self):
        """Teste la vue de liste des cotisations."""
        response = self.client.get(reverse('cotisations:cotisation_liste'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'cotisations/cotisation_liste.html')
        self.assertContains(response, self.cotisation.reference)
    
    def test_cotisation_detail_view(self):
        """Teste la vue de détail d'une cotisation."""
        response = self.client.get(
            reverse('cotisations:cotisation_detail', kwargs={'pk': self.cotisation.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'cotisations/cotisation_detail.html')
        self.assertContains(response, self.cotisation.reference)
        self.assertContains(response, self.membre.prenom)
    
    def test_cotisation_create_view(self):
        """Teste la création d'une cotisation."""
        # Accéder au formulaire
        response = self.client.get(reverse('cotisations:cotisation_creer'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'cotisations/cotisation_form.html')
        
        # Données du formulaire
        form_data = {
            'membre': self.membre.pk,
            'type_membre': self.type_membre.pk,
            'montant': '150.00',
            'date_emission': self.today.strftime('%Y-%m-%d'),
            'date_echeance': (self.today + timezone.timedelta(days=30)).strftime('%Y-%m-%d'),
            'periode_debut': self.today.strftime('%Y-%m-%d'),
            'periode_fin': self.today.replace(year=self.today.year + 1).strftime('%Y-%m-%d'),
            'statut': self.statut.pk,
            'generer_reference': True,
            'utiliser_bareme': False
        }
        
        # Soumettre le formulaire
        response = self.client.post(
            reverse('cotisations:cotisation_creer'), 
            data=form_data,
            follow=True
        )
        
        # Vérifier le résultat
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Cotisation.objects.count(), 2)  # La cotisation dans setUp + celle-ci
    
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
        self.assertEqual(self.cotisation.montant_restant, Decimal('60.00'))
        self.assertEqual(self.cotisation.statut_paiement, 'partiellement_payee')

class TestDashboardView(TestCase):
    """
    Tests pour la vue DashboardView.
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
        self.client.login(username='testuser', password='testpass')
        
        # Créer un membre, un type, un statut
        self.membre = Membre.objects.create(
            nom="Dupont",
            prenom="Jean",
            email="jean.dupont@example.com"
        )
        self.type_membre = TypeMembre.objects.create(libelle="Standard")
        self.statut = Statut.objects.create(nom="Actif")
        
        # Créer quelques cotisations pour avoir des données dans le dashboard
        self.cotisation1 = Cotisation.objects.create(
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
        
        self.cotisation2 = Cotisation.objects.create(
            membre=self.membre,
            montant=Decimal("80.00"),
            date_emission=timezone.now().date(),
            date_echeance=timezone.now().date() - datetime.timedelta(days=10),  # En retard
            periode_debut=timezone.now().date(),
            periode_fin=timezone.now().date() + datetime.timedelta(days=365),
            annee=timezone.now().year,
            mois=timezone.now().month,
            statut=self.statut,
            statut_paiement="non_payee",
            montant_restant=Decimal("80.00"),
            type_membre=self.type_membre,
            reference="COT-2023-002"
        )
    
    def test_dashboard_access(self):
        """Vérifier que le dashboard est accessible pour un utilisateur staff."""
        response = self.client.get(reverse('cotisations:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'cotisations/dashboard.html')
    
    def test_dashboard_context(self):
        """Vérifier que le dashboard contient les données attendues."""
        response = self.client.get(reverse('cotisations:dashboard'))
        self.assertEqual(response.status_code, 200)
        
        # Vérifier les cotisations en retard
        self.assertIn('cotisations_retard', response.context)
        self.assertEqual(response.context['nb_cotisations_retard'], 1)
        
        # Vérifier les statistiques
        self.assertEqual(response.context['total_cotisations'], 2)
        self.assertEqual(response.context['montant_total'], Decimal("200.00"))
        self.assertEqual(response.context['montant_restant'], Decimal("200.00"))
    
    def test_dashboard_unauthorized(self):
        import time
        timestamp = int(time.time())
        
        user_non_staff = User.objects.create_user(
            username=f"user_dashboard_{timestamp}",
            email=f"user_dashboard_{timestamp}@example.com",
            password="password123",
            is_staff=False
        )
        
        # Déconnectez l'utilisateur actuel et connectez le nouveau
        self.client.logout()
        self.client.login(username=f"user_dashboard_{timestamp}", password="password123")
        
        # Se connecter avec l'utilisateur non staff
        self.client.logout()
        self.client.login(username='regular', password='regular')
        
        # Essayer d'accéder au dashboard
        response = self.client.get(reverse('cotisations:dashboard'))
        self.assertEqual(response.status_code, 302)  # Redirection vers la page de connexion


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
    """
    Tests pour la vue PaiementCreateView.
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
    
    def test_paiement_create_form_display(self):
        """Vérifier que le formulaire de création de paiement s'affiche correctement."""
        response = self.client.get(reverse('cotisations:paiement_creer', args=[self.cotisation.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'cotisations/paiement_form.html')
        
        # Vérifier que le contexte contient la cotisation
        self.assertIn('cotisation', response.context)
        self.assertEqual(response.context['cotisation'], self.cotisation)
    
    def test_paiement_create_success(self):
        """Vérifier que la création d'un paiement fonctionne."""
        response = self.client.post(
            reverse('cotisations:paiement_creer', args=[self.cotisation.id]),
            {
                'montant': '50.00',
                'mode_paiement': self.mode_paiement.id,
                'date_paiement': timezone.now().strftime('%Y-%m-%dT%H:%M'),
                'type_transaction': 'paiement',
                'reference_paiement': 'PAY-2023-001',
                'commentaire': 'Test de paiement'
            }
        )
        
        # Vérifier la redirection vers la page de détail de la cotisation
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('cotisations:cotisation_detail', args=[self.cotisation.id]))
        
        # Vérifier que le paiement a été créé
        self.assertTrue(Paiement.objects.filter(cotisation=self.cotisation, montant=50.00).exists())
        
        # Vérifier que la cotisation a été mise à jour
        self.cotisation.refresh_from_db()
        self.assertEqual(self.cotisation.montant_restant, Decimal('70.00'))
        self.assertEqual(self.cotisation.statut_paiement, 'partiellement_payee')
    
    def test_paiement_create_ajax(self):
        """Vérifier que la création d'un paiement via AJAX fonctionne."""
        response = self.client.post(
            reverse('cotisations:paiement_create_ajax', args=[self.cotisation.id]),
            json.dumps({
                'montant': 50.00,
                'mode_paiement': self.mode_paiement.id,
                'date_paiement': timezone.now().strftime('%Y-%m-%dT%H:%M'),
                'type_transaction': 'paiement',
                'reference_paiement': 'PAY-2023-001',
                'commentaire': 'Test de paiement AJAX'
            }),
            content_type='application/json'
        )
        
        # Vérifier que la réponse est correcte
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        
        # Vérifier que le paiement a été créé
        self.assertTrue(Paiement.objects.filter(cotisation=self.cotisation, montant=50.00).exists())
        
        # Vérifier que la cotisation a été mise à jour
        self.cotisation.refresh_from_db()
        self.assertEqual(self.cotisation.montant_restant, Decimal('70.00'))
        self.assertEqual(self.cotisation.statut_paiement, 'partiellement_payee')


class TestApiCalculerMontant(TestCase):
    """
    Tests pour la vue api_calculer_montant.
    """
    def setUp(self):
        # Créer un utilisateur
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass',
            email='testuser@example.com',
        )
        self.client = Client()
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
    
    def test_api_calculer_montant_par_bareme(self):
        """Vérifier que l'API renvoie le montant correct pour un barème spécifié."""
        response = self.client.get(reverse('cotisations:api_calculer_montant') + f'?bareme_id={self.bareme.id}')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(data['montant'], float(self.bareme.montant))
        self.assertEqual(data['periodicite'], self.bareme.get_periodicite_display())
    
    def test_api_calculer_montant_par_type_membre(self):
        """Vérifier que l'API renvoie le montant correct pour un type de membre spécifié."""
        response = self.client.get(reverse('cotisations:api_calculer_montant') + f'?type_membre_id={self.type_membre.id}')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(data['montant'], float(self.bareme.montant))
        self.assertEqual(data['periodicite'], self.bareme.get_periodicite_display())
    
    def test_api_calculer_montant_bareme_inexistant(self):
        """Vérifier que l'API renvoie une erreur pour un barème inexistant."""
        response = self.client.get(reverse('cotisations:api_calculer_montant') + '?bareme_id=999')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertFalse(data['success'])
        self.assertIn('message', data)