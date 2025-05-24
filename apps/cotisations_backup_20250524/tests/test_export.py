# apps/cotisations/tests/test_export.py
import csv
import io
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.core.models import Statut
from apps.membres.models import Membre, TypeMembre
from apps.cotisations.models import Cotisation, ModePaiement, Paiement
from apps.cotisations.export_utils import (
    export_cotisations_csv, export_cotisations_excel, 
    export_paiements_csv, export_paiements_excel, 
    generer_rapport_cotisations_pdf, generer_recu_pdf
)

User = get_user_model()

class TestExportUtils(TestCase):
    """Tests pour les fonctions d'export."""
    
    def setUp(self):
        """Configuration initiale pour les tests."""
        # Créer un utilisateur staff
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword',
            is_staff=True
        )
        
        # Créer un statut
        self.statut = Statut.objects.create(nom='Actif')
        
        # Créer un type de membre
        self.type_membre = TypeMembre.objects.create(libelle='Standard')
        
        # Créer un membre
        self.membre = Membre.objects.create(
            nom='Dupont',
            prenom='Jean',
            email='jean.dupont@example.com',
            statut=self.statut
        )
        
        # Créer un mode de paiement
        self.mode_paiement = ModePaiement.objects.create(libelle='Carte bancaire')
        
        # Créer des cotisations
        today = timezone.now().date()
        
        self.cotisation1 = Cotisation.objects.create(
            membre=self.membre,
            montant=Decimal('100.00'),
            montant_restant=Decimal('0.00'),
            statut_paiement='payee',
            date_emission=today - timedelta(days=30),
            date_echeance=today + timedelta(days=30),
            periode_debut=today,
            periode_fin=today + timedelta(days=365),
            reference='COT-2023-001',
            type_membre=self.type_membre,
            statut=self.statut,
            annee=today.year,
            mois=today.month
        )
        
        self.cotisation2 = Cotisation.objects.create(
            membre=self.membre,
            montant=Decimal('150.00'),
            montant_restant=Decimal('75.00'),
            statut_paiement='partiellement_payee',
            date_emission=today - timedelta(days=15),
            date_echeance=today + timedelta(days=45),
            periode_debut=today,
            periode_fin=today + timedelta(days=365),
            reference='COT-2023-002',
            type_membre=self.type_membre,
            statut=self.statut,
            annee=today.year,
            mois=today.month
        )
        
        # Créer des paiements
        self.paiement1 = Paiement.objects.create(
            cotisation=self.cotisation1,
            montant=Decimal('100.00'),
            date_paiement=timezone.now() - timedelta(days=15),
            mode_paiement=self.mode_paiement,
            reference_paiement='PAY-2023-001',
            type_transaction='paiement'
        )
        
        self.paiement2 = Paiement.objects.create(
            cotisation=self.cotisation2,
            montant=Decimal('75.00'),
            date_paiement=timezone.now() - timedelta(days=10),
            mode_paiement=self.mode_paiement,
            reference_paiement='PAY-2023-002',
            type_transaction='paiement'
        )
    
    def test_export_cotisations_csv(self):
        """Vérifier que l'export CSV des cotisations fonctionne."""
        response = export_cotisations_csv(Cotisation.objects.all())
        
        # Vérifier le type de réponse
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertTrue('attachment; filename="cotisations_' in response['Content-Disposition'])
        
        # Lire le contenu CSV
        content = response.content.decode('utf-8')
        csv_reader = csv.reader(io.StringIO(content))
        rows = list(csv_reader)
        
        # Vérifier les en-têtes
        header = rows[0]
        self.assertIn('Référence', header)
        self.assertIn('Membre', header)
        self.assertIn('Courriel', header)
        self.assertIn('Montant', header)
        
        # Vérifier que le nombre de lignes est correct (en-tête + 2 cotisations)
        self.assertEqual(len(rows), 3)
        
        # Vérifier les données des cotisations
        references = [row[0] for row in rows[1:]]
        self.assertIn('COT-2023-001', references)
        self.assertIn('COT-2023-002', references)
    
    def test_export_cotisations_excel(self):
        """Vérifier que l'export Excel des cotisations fonctionne."""
        # Vérifier si xlsxwriter est disponible
        try:
            import xlsxwriter
        except ImportError:
            self.skipTest("xlsxwriter n'est pas installé, test ignoré")
        
        # Appeler la fonction d'export
        response = export_cotisations_excel(Cotisation.objects.all())
        
        # Vérifier la réponse
        self.assertEqual(
            response['Content-Type'], 
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        self.assertTrue('attachment; filename="cotisations_' in response['Content-Disposition'])
        
        # Vérifier que le contenu est un fichier Excel valide (présence de contenu)
        self.assertTrue(len(response.content) > 0)
    
    def test_export_paiements_csv(self):
        """Vérifier que l'export CSV des paiements fonctionne."""
        response = export_paiements_csv(Paiement.objects.all())
        
        # Vérifier le type de réponse
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertTrue('attachment; filename="paiements_' in response['Content-Disposition'])
        
        # Lire le contenu CSV
        content = response.content.decode('utf-8')
        csv_reader = csv.reader(io.StringIO(content))
        rows = list(csv_reader)
        
        # Vérifier que le nombre de lignes est correct (en-tête + 2 paiements)
        self.assertEqual(len(rows), 3)
    
    def test_export_paiements_excel(self):
        """Vérifier que l'export Excel des paiements fonctionne."""
        # Vérifier si xlsxwriter est disponible
        try:
            import xlsxwriter
        except ImportError:
            self.skipTest("xlsxwriter n'est pas installé, test ignoré")
        
        # Appeler la fonction d'export
        response = export_paiements_excel(Paiement.objects.all())
        
        # Vérifier la réponse
        self.assertEqual(
            response['Content-Type'], 
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        self.assertTrue('attachment; filename="paiements_' in response['Content-Disposition'])
        
        # Vérifier que le contenu est un fichier Excel valide
        self.assertTrue(len(response.content) > 0)
    
    def test_generer_rapport_cotisations_pdf(self):
        """Vérifier que la génération de rapport PDF fonctionne."""
        # Vérifier si reportlab est disponible
        try:
            import reportlab
        except ImportError:
            self.skipTest("reportlab n'est pas installé, test ignoré")
        
        # Appeler la fonction de génération de rapport
        response = generer_rapport_cotisations_pdf(Cotisation.objects.all())
        
        # Vérifier la réponse
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue('attachment; filename="rapport_cotisations_' in response['Content-Disposition'])
        
        # Vérifier que le contenu est un fichier PDF valide
        self.assertTrue(len(response.content) > 0)
    
    def test_generer_recu_pdf(self):
        """Vérifier que la génération de reçu PDF fonctionne."""
        # Vérifier si reportlab est disponible
        try:
            import reportlab
        except ImportError:
            self.skipTest("reportlab n'est pas installé, test ignoré")
        
        # Appeler la fonction de génération de reçu
        response = generer_recu_pdf(self.paiement1)
        
        # Vérifier la réponse
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue('attachment; filename="recu_paiement_' in response['Content-Disposition'])
        
        # Vérifier que le contenu est un fichier PDF valide
        self.assertTrue(len(response.content) > 0)


class TestExportViews(TestCase):
    """Tests pour les vues d'export."""
    
    def setUp(self):
        """Configuration initiale pour les tests."""
        # Créer un utilisateur staff
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword',
            is_staff=True
        )
        
        # Créer un statut
        self.statut = Statut.objects.create(nom='Actif')
        
        # Créer un type de membre
        self.type_membre = TypeMembre.objects.create(libelle='Standard')
        
        # Créer un membre
        self.membre = Membre.objects.create(
            nom='Dupont',
            prenom='Jean',
            email='jean.dupont@example.com',
            statut=self.statut
        )
        
        # Créer un mode de paiement
        self.mode_paiement = ModePaiement.objects.create(libelle='Carte bancaire')
        
        # Créer des cotisations
        today = timezone.now().date()
        
        self.cotisation1 = Cotisation.objects.create(
            membre=self.membre,
            montant=Decimal('100.00'),
            montant_restant=Decimal('0.00'),
            statut_paiement='payee',
            date_emission=today - timedelta(days=30),
            date_echeance=today + timedelta(days=30),
            periode_debut=today,
            periode_fin=today + timedelta(days=365),
            reference='COT-2023-001',
            type_membre=self.type_membre,
            statut=self.statut,
            annee=today.year,
            mois=today.month
        )
        
        self.cotisation2 = Cotisation.objects.create(
            membre=self.membre,
            montant=Decimal('150.00'),
            montant_restant=Decimal('75.00'),
            statut_paiement='partiellement_payee',
            date_emission=today - timedelta(days=15),
            date_echeance=today + timedelta(days=45),
            periode_debut=today,
            periode_fin=today + timedelta(days=365),
            reference='COT-2023-002',
            type_membre=self.type_membre,
            statut=self.statut,
            annee=today.year,
            mois=today.month
        )
        
        # Créer des paiements
        self.paiement1 = Paiement.objects.create(
            cotisation=self.cotisation1,
            montant=Decimal('100.00'),
            date_paiement=timezone.now() - timedelta(days=15),
            mode_paiement=self.mode_paiement,
            reference_paiement='PAY-2023-001',
            type_transaction='paiement'
        )
        
        self.paiement2 = Paiement.objects.create(
            cotisation=self.cotisation2,
            montant=Decimal('75.00'),
            date_paiement=timezone.now() - timedelta(days=10),
            mode_paiement=self.mode_paiement,
            reference_paiement='PAY-2023-002',
            type_transaction='paiement'
        )
        
        # Client authentifié
        self.client = Client()
        self.client.force_login(self.user)
    
    def test_export_cotisations_csv_view(self):
        """Vérifier que la vue d'export CSV des cotisations fonctionne."""
        # Appeler la vue d'export
        response = self.client.get(reverse('cotisations:export') + '?format=csv')
        
        # Vérifier la réponse
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertTrue('attachment; filename="cotisations_' in response['Content-Disposition'])
    
    def test_export_cotisations_excel_view(self):
        """Vérifier que la vue d'export Excel des cotisations fonctionne."""
        # Vérifier si xlsxwriter est disponible
        try:
            import xlsxwriter
        except ImportError:
            self.skipTest("xlsxwriter n'est pas installé, test ignoré")
        
        # Appeler la vue d'export
        response = self.client.get(reverse('cotisations:export') + '?format=excel')
        
        # Vérifier la réponse
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response['Content-Type'], 
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        self.assertTrue('attachment; filename="cotisations_' in response['Content-Disposition'])
    
    def test_export_with_filters(self):
        """Vérifier que les filtres sont appliqués lors de l'export."""
        # Appeler la vue d'export avec des filtres
        response = self.client.get(
            reverse('cotisations:export') + 
            '?format=csv&statut_paiement=partiellement_payee'
        )
        
        # Lire le contenu CSV
        content = response.content.decode('utf-8')
        csv_reader = csv.reader(io.StringIO(content))
        rows = list(csv_reader)
        
        # Vérifier que seule la cotisation partiellement payée est présente
        self.assertEqual(len(rows), 2)  # En-tête + 1 cotisation
        self.assertEqual(rows[1][0], 'COT-2023-002')
    
    def test_export_unauthorized(self):
        """Vérifier que l'export est restreint aux utilisateurs staff."""
        # Créer un utilisateur non-staff
        user = User.objects.create_user(
            username='regularuser',
            email='regular@example.com',
            password='password123'
        )
        
        # Se connecter avec l'utilisateur non-staff
        client = Client()
        client.force_login(user)
        
        # Essayer d'accéder à l'export
        response = client.get(reverse('cotisations:export') + '?format=csv')
        
        # Vérifier que l'accès est refusé
        self.assertNotEqual(response.status_code, 200)
    
    def test_export_invalid_format(self):
        """Vérifier que les formats d'export non supportés sont rejetés."""
        response = self.client.get(reverse('cotisations:export') + '?format=pdf')
        
        self.assertEqual(response.status_code, 400)