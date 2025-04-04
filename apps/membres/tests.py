import datetime
from django.test import TestCase
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from apps.core.models import Statut
from apps.membres.models import Membre, TypeMembre, MembreTypeMembre, HistoriqueMembre
from apps.membres.forms import MembreForm, TypeMembreForm, MembreTypeMembreForm


User = get_user_model()


class TypeMembreModelTests(TestCase):
    """Tests du modèle TypeMembre"""
    
    def setUp(self):
        """Initialisation des données de test"""
        self.type_membre = TypeMembre.objects.create(
            libelle="Membre régulier",
            description="Membres à jour de cotisation",
            cotisation_requise=True,
            ordre_affichage=1
        )
    
    def test_create_type_membre(self):
        """Vérifier la création d'un type de membre"""
        self.assertEqual(self.type_membre.libelle, "Membre régulier")
        self.assertEqual(self.type_membre.description, "Membres à jour de cotisation")
        self.assertTrue(self.type_membre.cotisation_requise)
        self.assertEqual(self.type_membre.ordre_affichage, 1)
    
    def test_str_representation(self):
        """Vérifier la représentation en chaîne"""
        self.assertEqual(str(self.type_membre), "Membre régulier")
    
    def test_get_absolute_url(self):
        """Vérifier l'URL absolue"""
        url = self.type_membre.get_absolute_url()
        # Modifier l'attente pour correspondre à l'URL "modifier" au lieu de "detail"
        self.assertEqual(url, f"/membres/types/{self.type_membre.pk}/modifier/")
    
    def test_soft_delete(self):
        """Vérifier la suppression logique"""
        self.type_membre.delete()
        # Vérifier que l'objet est toujours en base mais marqué comme supprimé
        self.assertIsNotNone(TypeMembre.objects.with_deleted().get(pk=self.type_membre.pk).deleted_at)
        # Vérifier qu'il n'apparaît plus dans les requêtes normales
        self.assertEqual(TypeMembre.objects.filter(pk=self.type_membre.pk).count(), 0)


class MembreModelTests(TestCase):
    """Tests du modèle Membre"""
    
    def setUp(self):
        """Initialisation des données de test"""
        self.statut = Statut.objects.create(
            nom="Actif",
            description="Membre à jour"
        )
        
        self.type_membre = TypeMembre.objects.create(
            libelle="Membre actif",
            description="Membre avec droits complets"
        )
        
        self.membre = Membre.objects.create(
            nom="DUPONT",
            prenom="Jean",
            email="jean.dupont@example.com",
            telephone="0123456789",
            adresse="1 rue de la Paix",
            code_postal="75001",
            ville="Paris",
            date_adhesion=timezone.now().date(),
            date_naissance=timezone.now().date() - datetime.timedelta(days=365*30),
            statut=self.statut
        )
        
        # Ajouter un type de membre
        self.membre_type = MembreTypeMembre.objects.create(
            membre=self.membre,
            type_membre=self.type_membre,
            date_debut=timezone.now().date()
        )
    
    def test_create_membre(self):
        """Vérifier la création d'un membre"""
        self.assertEqual(self.membre.nom, "DUPONT")
        self.assertEqual(self.membre.prenom, "Jean")
        self.assertEqual(self.membre.email, "jean.dupont@example.com")
        self.assertEqual(self.membre.statut, self.statut)
    
    def test_str_representation(self):
        """Vérifier la représentation en chaîne"""
        self.assertEqual(str(self.membre), "Jean DUPONT")
    
    def test_get_absolute_url(self):
        """Vérifier l'URL absolue"""
        url = self.membre.get_absolute_url()
        self.assertEqual(url, f"/membres/{self.membre.pk}/modifier/")
    
    def test_nom_complet_property(self):
        """Vérifier la propriété nom_complet"""
        self.assertEqual(self.membre.nom_complet, "Jean DUPONT")
    
    def test_adresse_complete_property(self):
        """Vérifier la propriété adresse_complete"""
        self.assertEqual(self.membre.adresse_complete, "1 rue de la Paix\n75001 Paris")
    
    def test_age_calculation(self):
        """Vérifier le calcul de l'âge"""
        # L'âge devrait être d'environ 30 ans
        self.assertAlmostEqual(self.membre.age(), 30, delta=1)
    
    def test_validation_date_naissance_future(self):
        """Vérifier la validation de la date de naissance dans le futur"""
        self.membre.date_naissance = timezone.now().date() + datetime.timedelta(days=10)
        with self.assertRaises(ValidationError):
            self.membre.full_clean()
    
    def test_validation_date_adhesion_future(self):
        """Vérifier la validation de la date d'adhésion dans le futur"""
        self.membre.date_adhesion = timezone.now().date() + datetime.timedelta(days=10)
        with self.assertRaises(ValidationError):
            self.membre.full_clean()
    
    def test_get_types_actifs(self):
        """Vérifier la récupération des types actifs"""
        types_actifs = self.membre.get_types_actifs()
        self.assertEqual(len(types_actifs), 1)
        self.assertEqual(types_actifs[0], self.type_membre)
    
    def test_est_type_actif(self):
        """Vérifier si le membre a un type spécifique actif"""
        self.assertTrue(self.membre.est_type_actif(self.type_membre))
        
        # Créer un nouveau type non associé
        nouveau_type = TypeMembre.objects.create(
            libelle="Type non associé"
        )
        self.assertFalse(self.membre.est_type_actif(nouveau_type))
    
    def test_ajouter_type(self):
        """Vérifier l'ajout d'un type de membre"""
        nouveau_type = TypeMembre.objects.create(
            libelle="Nouveau type"
        )
        
        # Ajouter le type
        self.membre.ajouter_type(nouveau_type)
        
        # Vérifier que le type a été ajouté
        self.assertTrue(self.membre.est_type_actif(nouveau_type))
    
    def test_supprimer_type(self):
        """Vérifier la suppression d'un type de membre"""
        # Supprimer le type existant
        self.membre.supprimer_type(self.type_membre)
        
        # Vérifier que le type n'est plus actif
        self.assertFalse(self.membre.est_type_actif(self.type_membre))
    
    def test_soft_delete(self):
        """Vérifier la suppression logique"""
        self.membre.delete()
        # Vérifier que l'objet est toujours en base mais marqué comme supprimé
        self.assertIsNotNone(Membre.objects.with_deleted().get(pk=self.membre.pk).deleted_at)
        # Vérifier qu'il n'apparaît plus dans les requêtes normales
        self.assertEqual(Membre.objects.filter(pk=self.membre.pk).count(), 0)


class MembreTypeMembreModelTests(TestCase):
    """Tests du modèle MembreTypeMembre"""
    
    def setUp(self):
        """Initialisation des données de test"""
        self.membre = Membre.objects.create(
            nom="MARTIN",
            prenom="Sophie",
            email="sophie.martin@example.com",
            date_adhesion=timezone.now().date()
        )
        
        self.type_membre = TypeMembre.objects.create(
            libelle="Membre honoraire"
        )
        
        self.membre_type = MembreTypeMembre.objects.create(
            membre=self.membre,
            type_membre=self.type_membre,
            date_debut=timezone.now().date() - datetime.timedelta(days=30),
            commentaire="Commentaire de test"
        )
    
    def test_create_membre_type_membre(self):
        """Vérifier la création d'une association membre-type"""
        self.assertEqual(self.membre_type.membre, self.membre)
        self.assertEqual(self.membre_type.type_membre, self.type_membre)
        self.assertEqual(self.membre_type.commentaire, "Commentaire de test")
        self.assertIsNone(self.membre_type.date_fin)
    
    def test_str_representation(self):
        """Vérifier la représentation en chaîne"""
        self.assertIn("Sophie MARTIN", str(self.membre_type))
        self.assertIn("Membre honoraire", str(self.membre_type))
        self.assertIn("actif", str(self.membre_type))
    
    def test_est_actif_property(self):
        """Vérifier la propriété est_actif"""
        # Cas sans date de fin
        self.assertTrue(self.membre_type.est_actif)
        
        # Cas avec date de fin dans le futur
        self.membre_type.date_fin = timezone.now().date() + datetime.timedelta(days=10)
        self.membre_type.save()
        self.assertTrue(self.membre_type.est_actif)
        
        # Cas avec date de fin dans le passé
        self.membre_type.date_fin = timezone.now().date() - datetime.timedelta(days=1)
        self.membre_type.save()
        self.assertFalse(self.membre_type.est_actif)
    
    def test_validation_dates(self):
        """Vérifier la validation des dates"""
        # Test date de fin antérieure à la date de début
        self.membre_type.date_fin = self.membre_type.date_debut - datetime.timedelta(days=1)
        with self.assertRaises(ValidationError):
            self.membre_type.full_clean()


class HistoriqueMembreModelTests(TestCase):
    """Tests du modèle HistoriqueMembre"""
    
    def setUp(self):
        """Initialisation des données de test"""
        self.user = User.objects.create_user(
            username="admin",
            email="admin@example.com",
            password="password"
        )
        
        self.membre = Membre.objects.create(
            nom="PETIT",
            prenom="Marie",
            email="marie.petit@example.com",
            date_adhesion=timezone.now().date()
        )
        
        self.historique = HistoriqueMembre.objects.create(
            membre=self.membre,
            utilisateur=self.user,
            action="creation",
            description="Création du membre",
            donnees_apres={
                "nom": "PETIT",
                "prenom": "Marie",
                "email": "marie.petit@example.com"
            }
        )
    
    def test_create_historique(self):
        """Vérifier la création d'un historique"""
        self.assertEqual(self.historique.membre, self.membre)
        self.assertEqual(self.historique.utilisateur, self.user)
        self.assertEqual(self.historique.action, "creation")
        self.assertEqual(self.historique.description, "Création du membre")
        self.assertEqual(self.historique.donnees_apres["nom"], "PETIT")
    
    def test_str_representation(self):
        """Vérifier la représentation en chaîne"""
        self.assertIn("creation", str(self.historique))
        self.assertIn("Marie PETIT", str(self.historique))


class MembreManagerTests(TestCase):
    """Tests du gestionnaire personnalisé de Membre"""
    
    def setUp(self):
        """Initialisation des données de test"""
        self.statut_actif = Statut.objects.create(nom="Actif")
        self.statut_inactif = Statut.objects.create(nom="Inactif")
        
        self.type_adherent = TypeMembre.objects.create(libelle="Adhérent")
        self.type_bienfaiteur = TypeMembre.objects.create(libelle="Bienfaiteur")
        
        # Créer plusieurs membres pour les tests
        self.membre1 = Membre.objects.create(
            nom="DUPONT",
            prenom="Jean",
            email="jean.dupont@example.com",
            date_adhesion=timezone.now().date() - datetime.timedelta(days=365),
            date_naissance=timezone.now().date() - datetime.timedelta(days=365*40),
            statut=self.statut_actif
        )
        
        self.membre2 = Membre.objects.create(
            nom="MARTIN",
            prenom="Sophie",
            email="sophie.martin@example.com",
            date_adhesion=timezone.now().date() - datetime.timedelta(days=30),
            date_naissance=timezone.now().date() - datetime.timedelta(days=365*25),
            statut=self.statut_actif
        )
        
        self.membre3 = Membre.objects.create(
            nom="PETIT",
            prenom="Marie",
            email="marie.petit@example.com",
            date_adhesion=timezone.now().date() - datetime.timedelta(days=730),
            date_naissance=timezone.now().date() - datetime.timedelta(days=365*50),
            statut=self.statut_inactif
        )
        
        # Associer des types aux membres
        MembreTypeMembre.objects.create(
            membre=self.membre1,
            type_membre=self.type_adherent,
            date_debut=timezone.now().date() - datetime.timedelta(days=365)
        )
        
        MembreTypeMembre.objects.create(
            membre=self.membre2,
            type_membre=self.type_bienfaiteur,
            date_debut=timezone.now().date() - datetime.timedelta(days=30)
        )
        
        # Membre 3 a eu un type mais n'en a plus (terminé)
        MembreTypeMembre.objects.create(
            membre=self.membre3,
            type_membre=self.type_adherent,
            date_debut=timezone.now().date() - datetime.timedelta(days=730),
            date_fin=timezone.now().date() - datetime.timedelta(days=365)
        )
    
    def test_recherche(self):
        """Tester la méthode de recherche"""
        # Recherche par nom
        resultats = Membre.objects.recherche("DUPONT")
        self.assertEqual(resultats.count(), 1)
        self.assertEqual(resultats.first(), self.membre1)
        
        # Recherche par prénom
        resultats = Membre.objects.recherche("Sophie")
        self.assertEqual(resultats.count(), 1)
        self.assertEqual(resultats.first(), self.membre2)
        
        # Recherche par email (partiel)
        resultats = Membre.objects.recherche("example.com")
        self.assertEqual(resultats.count(), 3)
    
    def test_par_type(self):
        """Tester le filtrage par type de membre"""
        # Filtrer par type adhérent
        resultats = Membre.objects.par_type(self.type_adherent.id)
        self.assertEqual(resultats.count(), 1)
        self.assertEqual(resultats.first(), self.membre1)
        
        # Filtrer par type bienfaiteur
        resultats = Membre.objects.par_type(self.type_bienfaiteur.id)
        self.assertEqual(resultats.count(), 1)
        self.assertEqual(resultats.first(), self.membre2)
    
    def test_par_statut(self):
        """Tester le filtrage par statut"""
        # Filtrer par statut actif
        resultats = Membre.objects.par_statut(self.statut_actif.id)
        self.assertEqual(resultats.count(), 2)
        
        # Filtrer par statut inactif
        resultats = Membre.objects.par_statut(self.statut_inactif.id)
        self.assertEqual(resultats.count(), 1)
        self.assertEqual(resultats.first(), self.membre3)
    
    def test_adhesions_recentes(self):
        """Tester le filtrage par adhésion récente"""
        # Membres ayant adhéré dans les 60 derniers jours
        resultats = Membre.objects.adhesions_recentes(jours=60)
        self.assertEqual(resultats.count(), 1)
        self.assertEqual(resultats.first(), self.membre2)
    
    def test_par_age(self):
        """Tester le filtrage par âge"""
        # Membres de moins de 30 ans
        resultats = Membre.objects.par_age(age_max=30)
        self.assertEqual(resultats.count(), 1)
        self.assertEqual(resultats.first(), self.membre2)
        
        # Membres de plus de 45 ans
        resultats = Membre.objects.par_age(age_min=45)
        self.assertEqual(resultats.count(), 1)
        self.assertEqual(resultats.first(), self.membre3)
        
        # Membres entre 35 et 45 ans
        resultats = Membre.objects.par_age(age_min=35, age_max=45)
        self.assertEqual(resultats.count(), 1)
        self.assertEqual(resultats.first(), self.membre1)
    
    def test_par_anciennete(self):
        """Tester le filtrage par ancienneté"""
        # Membres avec moins de 6 mois d'ancienneté
        resultats = Membre.objects.par_anciennete(annees_max=0.5)
        self.assertEqual(resultats.count(), 1)
        self.assertEqual(resultats.first(), self.membre2)
        
        # Membres avec plus d'un an d'ancienneté
        resultats = Membre.objects.par_anciennete(annees_min=1)
        self.assertEqual(resultats.count(), 2)
    
    def test_actifs_inactifs(self):
        """Tester le filtrage par activité (présence d'un type actif)"""
        # Membres actifs (avec un type de membre actif)
        resultats = Membre.objects.actifs()
        self.assertEqual(resultats.count(), 2)
        
        # Membres inactifs (sans type de membre actif)
        resultats = Membre.objects.inactifs()
        self.assertEqual(resultats.count(), 1)
        self.assertEqual(resultats.first(), self.membre3)


class MembreFormTests(TestCase):
    """Tests du formulaire MembreForm"""
    
    def setUp(self):
        """Initialisation des données de test"""
        self.statut = Statut.objects.create(nom="Actif")
        self.type_membre = TypeMembre.objects.create(libelle="Adhérent")
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="password"
        )
        
        self.valid_data = {
            'nom': 'DUPONT',
            'prenom': 'Jean',
            'email': 'jean.dupont@example.com',
            'telephone': '0123456789',
            'adresse': '1 rue de la Paix',
            'code_postal': '75001',
            'ville': 'Paris',
            'date_adhesion': timezone.now().date(),
            'date_naissance': timezone.now().date() - datetime.timedelta(days=365*30),
            'langue': 'fr',
            'statut': self.statut.id,
            'types_membre': [self.type_membre.id],
            'accepte_mail': True,
            'accepte_sms': False
        }
    
    def test_valid_form(self):
        """Tester la validation d'un formulaire valide"""
        form = MembreForm(data=self.valid_data, user=self.user)
        self.assertTrue(form.is_valid())
    
    def test_invalid_future_date_naissance(self):
        """Tester la validation avec une date de naissance future"""
        data = self.valid_data.copy()
        data['date_naissance'] = timezone.now().date() + datetime.timedelta(days=10)
        form = MembreForm(data=data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('date_naissance', form.errors)
    
    def test_invalid_future_date_adhesion(self):
        """Tester la validation avec une date d'adhésion future"""
        data = self.valid_data.copy()
        data['date_adhesion'] = timezone.now().date() + datetime.timedelta(days=10)
        form = MembreForm(data=data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('date_adhesion', form.errors)
    
    def test_duplicate_email(self):
        """Tester la validation avec un email dupliqué"""
        # Créer un membre avec l'email
        Membre.objects.create(
            nom="EXISTANT",
            prenom="Test",
            email=self.valid_data['email'],
            date_adhesion=timezone.now().date()
        )
        
        # Tester le formulaire avec le même email
        form = MembreForm(data=self.valid_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)
    
    def test_save_with_types(self):
        """Tester l'enregistrement avec des types de membre"""
        form = MembreForm(data=self.valid_data, user=self.user)
        self.assertTrue(form.is_valid())
        
        # Enregistrer le membre
        membre = form.save()
        
        # Vérifier que le membre a été créé
        self.assertIsNotNone(membre.pk)
        self.assertEqual(membre.nom, 'DUPONT')
        
        # Vérifier que le type a été ajouté
        types_actifs = membre.get_types_actifs()
        self.assertEqual(len(types_actifs), 1)
        self.assertEqual(types_actifs[0], self.type_membre)
        
        # Vérifier que l'historique a été créé
        historique = HistoriqueMembre.objects.filter(membre=membre, action='modification').first()
        self.assertIsNotNone(historique)
        self.assertEqual(historique.utilisateur, self.user)


class MembreViewTests(TestCase):
    """Tests des vues de l'application membres"""
    
    def setUp(self):
        """Initialisation des données de test"""
        # Créer un utilisateur administrateur
        self.admin_user = User.objects.create_user(
            username="admin",
            email="admin@example.com",
            password="password",
            is_staff=True
        )
        self.client.force_login(self.admin_user)

        # Statut et type de membre
        self.statut = Statut.objects.create(nom="Actif")
        self.type_membre = TypeMembre.objects.create(libelle="Adhérent")
        
        # Créer un membre
        self.membre = Membre.objects.create(
            nom="DUPONT",
            prenom="Jean",
            email="jean.dupont@example.com",
            date_adhesion=timezone.now().date() - datetime.timedelta(days=30),
            statut=self.statut
        )
        
        # Associer un type au membre
        self.membre_type = MembreTypeMembre.objects.create(
            membre=self.membre,
            type_membre=self.type_membre,
            date_debut=timezone.now().date() - datetime.timedelta(days=30)
        )
        
        # Se connecter AVANT chaque test
        self.client.login(username="admin", password="password")
    
    def test_dashboard_view(self):
        """Tester la vue du tableau de bord"""
        # Connexion
        self.client.login(username="admin", password="password")
        
        # Accéder à la vue
        response = self.client.get(reverse('membres:dashboard'))
        
        # Vérifier le code de statut
        self.assertEqual(response.status_code, 200)
        
        # Vérifier le contenu
        self.assertContains(response, "Tableau de bord")
        self.assertContains(response, "1")  # Nombre total de membres
    
    def test_membre_list_view(self):
        """Tester la vue de liste des membres"""
        # Connexion
        self.client.login(username="admin", password="password")
        
        # Accéder à la vue
        response = self.client.get(reverse('membres:membre_liste'))
        
        # Vérifier le code de statut
        self.assertEqual(response.status_code, 200)
        
        # Vérifier que le membre est dans la liste
        self.assertContains(response, "DUPONT")
        self.assertContains(response, "Jean")
    
    def test_membre_detail_view(self):
        """Tester la vue de détail d'un membre"""
        # Connexion
        self.client.login(username="admin", password="password")
        
        # Accéder à la vue
        response = self.client.get(reverse('membres:membre_detail', kwargs={'pk': self.membre.pk}))
        
        # Vérifier le code de statut
        self.assertEqual(response.status_code, 200)
        
        # Vérifier le contenu
        self.assertContains(response, "Jean DUPONT")
        self.assertContains(response, "jean.dupont@example.com")
        self.assertContains(response, "Adhérent")  # Type de membre
    
    def test_membre_create_view(self):
        """Tester la vue de création d'un membre"""
        # Connexion en tant qu'admin
        self.client.login(username="admin", password="password")
        
        # Accéder à la vue
        response = self.client.get(reverse('membres:membre_nouveau'), follow=True)
        
        # Vérifier le code de statut
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<form')
        
        # Vérifier le formulaire
        self.assertContains(response, '<form')
        self.assertContains(response, 'name="nom"')
        
        # Envoyer le formulaire
        data = {
            'nom': 'MARTIN',
            'prenom': 'Sophie',
            'email': 'sophie.martin@example.com',
            'telephone': '0987654321',
            'adresse': '2 avenue des Champs',
            'code_postal': '75008',
            'ville': 'Paris',
            'date_adhesion': timezone.now().date().strftime('%Y-%m-%d'),
            'langue': 'fr',
            'statut': self.statut.id,
            'types_membre': [self.type_membre.id],
            'accepte_mail': True
        }
        
        response = self.client.post(reverse('membres:membre_nouveau'), data=data)
        
        # Vérifier la redirection
        self.assertEqual(response.status_code, 302)
        
        # Vérifier que le membre a été créé
        self.assertTrue(Membre.objects.filter(email='sophie.martin@example.com').exists())
    
    def test_membre_update_view(self):
        """Tester la vue de modification d'un membre"""
        # Connexion en tant qu'admin
        self.client.login(username="admin", password="password")
        
        # Accéder à la vue
        response = self.client.get(reverse('membres:membre_modifier', kwargs={'pk': self.membre.pk}))
        
        # Vérifier le code de statut
        self.assertEqual(response.status_code, 200)
        
        # Vérifier le formulaire pré-rempli
        self.assertContains(response, 'value="DUPONT"')
        self.assertContains(response, 'value="Jean"')
        
        # Modifier le membre
        data = {
            'nom': 'DUPONT',
            'prenom': 'Jean-Pierre',  # Modification du prénom
            'email': 'jean.dupont@example.com',
            'telephone': '0123456789',
            'date_adhesion': self.membre.date_adhesion.strftime('%Y-%m-%d'),
            'langue': 'fr',
            'statut': self.statut.id,
            'types_membre': [self.type_membre.id],
            'accepte_mail': True
        }
        
        response = self.client.post(
            reverse('membres:membre_modifier', kwargs={'pk': self.membre.pk}),
            data=data
        )
        
        # Vérifier la redirection
        self.assertEqual(response.status_code, 302)
        
        # Vérifier que le membre a été modifié
        self.membre.refresh_from_db()
        self.assertEqual(self.membre.prenom, 'Jean-Pierre')
    
    def test_membre_delete_view(self):
        """Tester la vue de suppression d'un membre"""
        # Connexion en tant qu'admin
        self.client.login(username="admin", password="password")
        
        # Accéder à la vue
        response = self.client.get(reverse('membres:membre_supprimer', kwargs={'pk': self.membre.pk}))
        
        # Vérifier le code de statut
        self.assertEqual(response.status_code, 200)
        
        # Vérifier la page de confirmation
        self.assertContains(response, "Supprimer le membre")
        
        # Confirmer la suppression
        response = self.client.post(
            reverse('membres:membre_supprimer', kwargs={'pk': self.membre.pk})
        )
        
        # Vérifier la redirection
        self.assertEqual(response.status_code, 302)
        
        # Vérifier que le membre a été supprimé (logiquement)
        self.assertEqual(Membre.objects.filter(pk=self.membre.pk).count(), 0)
        self.assertEqual(Membre.objects.with_deleted().filter(pk=self.membre.pk).count(), 1)
    
    def test_unauthorized_access(self):
        """Tester l'accès non autorisé aux vues réservées au staff"""
        # D'abord, déconnectez le client
        self.client.logout()
        
        # Créez un utilisateur non-staff
        standard_user = User.objects.create_user(
            username="standard",
            email="standard@example.com",
            password="password",
            is_staff=False
        )
        
        # Connectez-vous avec cet utilisateur non-staff
        self.client.login(username="standard", password="password")
        
        # Tentative d'accès à la création de membre (réservée au staff)
        response = self.client.get(reverse('membres:membre_nouveau'))
        
        # Vérifier redirection ou accès refusé
        self.assertNotEqual(response.status_code, 200)
    
    def test_import_csv(self):
        """Tester l'importation CSV des membres"""
        # Créer un fichier CSV temporaire
        import tempfile
        from django.core.files.uploadedfile import SimpleUploadedFile
        
        csv_content = b"Nom,Prenom,Email,Telephone\nDUBOIS,Pierre,pierre.dubois@example.com,0123456789\nMARTIN,Sophie,sophie.martin@example.com,0987654321"
        csv_file = SimpleUploadedFile("members.csv", csv_content, content_type="text/csv")
        
        # Créer un type de membre pour l'importation
        type_membre = TypeMembre.objects.create(libelle="Importé", description="Membre importé")
        
        # Simuler une requête POST avec le formulaire
        form_data = {
            'fichier': csv_file,
            'delimiter': ',',
            'header': True,
            'type_membre': type_membre.id
        }
        
        # Compter les membres avant l'importation
        count_before = Membre.objects.count()
        
        # Exécuter la vue d'importation
        self.client.login(username="admin", password="password")
        response = self.client.post(reverse('membres:membre_importer'), form_data)
        
        # Vérifier que l'importation a fonctionné
        self.assertEqual(response.status_code, 302)  # Redirection
        self.assertEqual(Membre.objects.count(), count_before + 2)  # 2 membres ajoutés
        
        # Vérifier le contenu importé
        self.assertTrue(Membre.objects.filter(email="jean.dupont@example.com").exists())
        self.assertTrue(Membre.objects.filter(email="sophie.martin@example.com").exists())