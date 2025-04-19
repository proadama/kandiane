# apps/cotisations/tests/test_views.py
from decimal import Decimal
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


class CotisationViewsTest(TestCase):
    """Tests pour les vues de l'application Cotisations."""
    
    def setUp(self):
        # Créer un utilisateur pour les tests
        self.password = "test_password"
        self.user = User.objects.create_user(
            username="test_user",
            email="test_user@example.com",
            password=self.password,
            is_staff=True
        )
        
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

# Ajouter d'autres tests de vues...