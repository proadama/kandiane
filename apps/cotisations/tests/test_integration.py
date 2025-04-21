# apps/cotisations/tests/test_integration.py
from decimal import Decimal
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


class CotisationWorkflowTest(TestCase):
    """Tests d'intégration du workflow complet des cotisations."""
    
    def setUp(self):
        import time
        timestamp = int(time.time())
        
        # Créer un utilisateur pour les tests
        self.password = "test_password"
        self.user = User.objects.create_user(
            username=f"test_user_{timestamp}",
            email=f"test_user_{timestamp}@example.com",
            password=self.password,
            is_staff=True
        )
        
        # Créer un client et s'identifier
        self.client = Client()
        self.client.force_login(self.user)
        
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
            email=f"jean.dupont_{timestamp}@example.com",
            date_adhesion=timezone.now().date()
        )
        
        self.mode_paiement = ModePaiement.objects.create(
            libelle="Carte bancaire"
        )
    
    def test_workflow_complet(self):
        # Créer les données préalables
        self.type_membre = TypeMembre.objects.create(libelle="Standard")
        
        # Créer le barème explicitement
        self.bareme = BaremeCotisation.objects.create(
            type_membre=self.type_membre,
            montant=Decimal('100.00'),
            periodicite='annuelle',
            date_debut_validite=timezone.now().date()
        )
        
        # Vérifier qu'il existe bien
        self.assertEqual(BaremeCotisation.objects.count(), 1)
        
        response = self.client.post(
            reverse('cotisations:bareme_creer'),
            data=bareme_data,
            follow=True
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(BaremeCotisation.objects.count(), 1)
        
        bareme = BaremeCotisation.objects.first()
        
        # 2. Créer une cotisation basée sur le barème
        cotisation_data = {
            'membre': self.membre.pk,
            'type_membre': self.type_membre.pk,
            'bareme': bareme.pk,
            'montant': '120.00',
            'date_emission': today.strftime('%Y-%m-%d'),
            'date_echeance': (today + timezone.timedelta(days=30)).strftime('%Y-%m-%d'),
            'periode_debut': today.strftime('%Y-%m-%d'),
            'periode_fin': today.replace(year=today.year + 1).strftime('%Y-%m-%d'),
            'statut': self.statut.pk,
            'generer_reference': True,
            'utiliser_bareme': True
        }
        
        response = self.client.post(
            reverse('cotisations:cotisation_creer'),
            data=cotisation_data,
            follow=True
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Cotisation.objects.count(), 1)
        
        cotisation = Cotisation.objects.first()
        
        # 3. Ajouter un paiement partiel
        paiement_data = {
            'montant': '50.00',
            'mode_paiement': self.mode_paiement.pk,
            'date_paiement': timezone.now().strftime('%Y-%m-%dT%H:%M'),
            'type_transaction': 'paiement',
            'reference_paiement': 'CB-123456'
        }
        
        response = self.client.post(
            reverse('cotisations:paiement_creer', kwargs={'cotisation_id': cotisation.pk}),
            data=paiement_data,
            follow=True
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Paiement.objects.count(), 1)
        
        # Vérifier la mise à jour de la cotisation
        cotisation.refresh_from_db()
        self.assertEqual(cotisation.montant_restant, Decimal('70.00'))
        self.assertEqual(cotisation.statut_paiement, 'partiellement_payee')
        
        # 4. Créer un rappel
        rappel_data = {
            'type_rappel': 'email',
            'contenu': 'Ceci est un rappel de test pour votre cotisation en retard.',
            'niveau': 1
        }
        
        response = self.client.post(
            reverse('cotisations:rappel_creer', kwargs={'cotisation_id': cotisation.pk}),
            data=rappel_data,
            follow=True
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Rappel.objects.count(), 1)
        
        # 5. Compléter le paiement
        paiement_final_data = {
            'montant': '70.00',
            'mode_paiement': self.mode_paiement.pk,
            'date_paiement': timezone.now().strftime('%Y-%m-%dT%H:%M'),
            'type_transaction': 'paiement',
            'reference_paiement': 'CB-654321'
        }
        
        response = self.client.post(
            reverse('cotisations:paiement_creer', kwargs={'cotisation_id': cotisation.pk}),
            data=paiement_final_data,
            follow=True
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Paiement.objects.count(), 2)
        
        # Vérifier que la cotisation est entièrement payée
        cotisation.refresh_from_db()
        self.assertEqual(cotisation.montant_restant, Decimal('0.00'))
        self.assertEqual(cotisation.statut_paiement, 'payee')