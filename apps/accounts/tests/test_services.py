"""
Tests pour le service de création d'utilisateurs (UserCreationService).

Execute les tests avec:
    python manage.py test apps.accounts.tests.test_services
"""

from django.test import TestCase, TransactionTestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from apps.accounts.services import UserCreationService
from apps.accounts.models import CustomUser
from apps.membres.models import Membre, TypeMembre
from apps.core.models import Statut


class UserCreationServiceTechniqueTest(TransactionTestCase):
    """Tests pour la méthode creer_utilisateur_technique()"""

    def test_creer_utilisateur_technique_minimal(self):
        """Test création avec données minimales"""
        user, password = UserCreationService.creer_utilisateur_technique(
            username='test.tech',
            email='test@example.com'
        )

        # Vérifications
        self.assertIsNotNone(user)
        self.assertEqual(user.username, 'test.tech')
        self.assertEqual(user.email, 'test@example.com')
        self.assertIsNotNone(password)
        self.assertEqual(len(password), 12)  # Password généré de 12 caractères
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertFalse(hasattr(user, 'membre'))

    def test_creer_utilisateur_technique_complet(self):
        """Test création avec toutes les données"""
        user, password = UserCreationService.creer_utilisateur_technique(
            username='admin.tech',
            email='admin@example.com',
            password='MyPassword123!',
            first_name='Admin',
            last_name='Tech',
            telephone='0612345678',
            is_staff=True,
            is_superuser=True
        )

        # Vérifications
        self.assertEqual(user.username, 'admin.tech')
        self.assertEqual(user.email, 'admin@example.com')
        self.assertEqual(user.first_name, 'Admin')
        self.assertEqual(user.last_name, 'Tech')
        self.assertEqual(user.telephone, '0612345678')
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertEqual(password, 'MyPassword123!')
        # Vérifier que l'utilisateur peut se connecter
        self.assertTrue(user.check_password('MyPassword123!'))

    def test_creer_utilisateur_technique_username_duplicate(self):
        """Test qu'un username dupliqué lève ValidationError"""
        # Créer un premier utilisateur
        UserCreationService.creer_utilisateur_technique(
            username='dupli',
            email='first@example.com'
        )

        # Tenter de créer avec le même username
        with self.assertRaises(ValidationError) as cm:
            UserCreationService.creer_utilisateur_technique(
                username='dupli',  # Même username
                email='second@example.com'
            )

        self.assertIn('username', cm.exception.message_dict)

    def test_creer_utilisateur_technique_email_duplicate(self):
        """Test qu'un email dupliqué lève ValidationError"""
        # Créer un premier utilisateur
        UserCreationService.creer_utilisateur_technique(
            username='user1',
            email='same@example.com'
        )

        # Tenter de créer avec le même email
        with self.assertRaises(ValidationError) as cm:
            UserCreationService.creer_utilisateur_technique(
                username='user2',
                email='same@example.com'  # Même email
            )

        self.assertIn('email', cm.exception.message_dict)

    def test_creer_utilisateur_technique_password_genere(self):
        """Test génération automatique du password"""
        user, password = UserCreationService.creer_utilisateur_technique(
            username='autopass',
            email='autopass@example.com'
            # Pas de password fourni
        )

        # Vérifications
        self.assertIsNotNone(password)
        self.assertEqual(len(password), 12)
        # Vérifier que l'utilisateur peut se connecter avec ce password
        self.assertTrue(user.check_password(password))
        # Vérifier que le password est marqué comme temporaire
        self.assertTrue(user.password_temporary)

    def test_creer_utilisateur_technique_pas_de_membre(self):
        """Test qu'aucun membre n'est créé"""
        user, password = UserCreationService.creer_utilisateur_technique(
            username='nomembre',
            email='nomembre@example.com'
        )

        # Vérifier qu'aucun membre n'est lié
        self.assertFalse(hasattr(user, 'membre'))
        # Vérifier qu'aucun membre avec cet email n'existe
        self.assertEqual(Membre.objects.filter(email='nomembre@example.com').count(), 0)


class UserCreationServiceMembreTest(TransactionTestCase):
    """Tests pour la méthode creer_membre_avec_compte()"""

    def setUp(self):
        """Préparation des données de test"""
        # Créer un statut de test
        self.statut = Statut.objects.create(
            nom='Actif',
            type_entite='membre'
        )

        # Créer des types de membre
        self.type_adherent = TypeMembre.objects.create(
            libelle='Adhérent',
            cotisation_requise=True
        )
        self.type_bienfaiteur = TypeMembre.objects.create(
            libelle='Bienfaiteur',
            cotisation_requise=False
        )

    def test_creer_membre_avec_compte_minimal(self):
        """Test création avec données minimales"""
        membre, user, password = UserCreationService.creer_membre_avec_compte(
            nom='Dupont',
            prenom='Jean',
            email='jean.dupont@example.com'
        )

        # Vérifications membre
        self.assertIsNotNone(membre)
        self.assertEqual(membre.nom, 'DUPONT')  # Le modèle convertit en majuscules
        self.assertEqual(membre.prenom, 'Jean')
        self.assertEqual(membre.email, 'jean.dupont@example.com')
        self.assertEqual(membre.pays, 'France')  # Défaut

        # Vérifications utilisateur
        self.assertIsNotNone(user)
        self.assertEqual(user.email, 'jean.dupont@example.com')
        self.assertEqual(user.first_name, 'Jean')
        self.assertEqual(user.last_name, 'Dupont')

        # Vérifier la relation OneToOne
        self.assertEqual(membre.utilisateur, user)
        self.assertEqual(user.membre, membre)

        # Vérifier password
        self.assertIsNotNone(password)
        self.assertTrue(user.check_password(password))

    def test_creer_membre_avec_compte_complet(self):
        """Test création avec toutes les données"""
        membre, user, password = UserCreationService.creer_membre_avec_compte(
            nom='Martin',
            prenom='Marie',
            email='marie.martin@example.com',
            telephone='0687654321',
            adresse='123 Rue de la Paix',
            code_postal='75001',
            ville='Paris',
            pays='France',
            date_naissance=timezone.now().date().replace(year=1990),
            langue='fr',
            statut=self.statut,
            types_membre=[self.type_adherent, self.type_bienfaiteur],
            accepte_mail=True,
            accepte_sms=True,
            commentaires='Membre fondateur',
            username='marie.m',
            password='SecurePass123!'
        )

        # Vérifications membre
        self.assertEqual(membre.nom, 'MARTIN')  # Le modèle convertit en majuscules
        self.assertEqual(membre.telephone, '0687654321')
        self.assertEqual(membre.adresse, '123 Rue de la Paix')
        self.assertEqual(membre.code_postal, '75001')
        self.assertEqual(membre.ville, 'Paris')
        self.assertEqual(membre.statut, self.statut)
        self.assertTrue(membre.accepte_mail)
        self.assertTrue(membre.accepte_sms)
        self.assertEqual(membre.commentaires, 'Membre fondateur')

        # Vérifications utilisateur
        self.assertEqual(user.username, 'marie.m')
        self.assertEqual(password, 'SecurePass123!')
        self.assertTrue(user.check_password('SecurePass123!'))

        # Vérifier les types de membre
        types_actifs = list(membre.get_types_actifs())
        self.assertEqual(len(types_actifs), 2)
        self.assertIn(self.type_adherent, types_actifs)
        self.assertIn(self.type_bienfaiteur, types_actifs)

    def test_creer_membre_avec_compte_email_duplicate(self):
        """Test qu'un email dupliqué lève ValidationError"""
        # Créer un premier membre
        UserCreationService.creer_membre_avec_compte(
            nom='Premier',
            prenom='Test',
            email='duplicate@example.com'
        )

        # Tenter de créer avec le même email
        with self.assertRaises(ValidationError) as cm:
            UserCreationService.creer_membre_avec_compte(
                nom='Deuxième',
                prenom='Test',
                email='duplicate@example.com'  # Même email
            )

        self.assertIn('email', cm.exception.message_dict)

    def test_creer_membre_avec_compte_username_genere(self):
        """Test génération automatique du username"""
        membre, user, password = UserCreationService.creer_membre_avec_compte(
            nom='Leroy',
            prenom='Pierre',
            email='pierre.leroy@example.com'
            # Pas de username fourni
        )

        # Vérifier que le username est généré depuis prenom.nom
        self.assertEqual(user.username, 'pierre.leroy')

    def test_creer_membre_avec_compte_username_collision(self):
        """Test gestion des collisions de username"""
        # Créer un premier membre avec jean.martin
        UserCreationService.creer_membre_avec_compte(
            nom='Martin',
            prenom='Jean',
            email='jean1@example.com'
        )

        # Créer un deuxième Jean Martin
        membre2, user2, password2 = UserCreationService.creer_membre_avec_compte(
            nom='Martin',
            prenom='Jean',
            email='jean2@example.com'
        )

        # Le username devrait être incrémenté
        self.assertEqual(user2.username, 'jean.martin1')

        # Créer un troisième
        membre3, user3, password3 = UserCreationService.creer_membre_avec_compte(
            nom='Martin',
            prenom='Jean',
            email='jean3@example.com'
        )

        self.assertEqual(user3.username, 'jean.martin2')

    def test_creer_membre_avec_compte_types_membre(self):
        """Test attribution des types de membre"""
        membre, user, password = UserCreationService.creer_membre_avec_compte(
            nom='Dubois',
            prenom='Sophie',
            email='sophie.dubois@example.com',
            types_membre=[self.type_adherent]
        )

        # Vérifier que le type a été attribué
        types_actifs = list(membre.get_types_actifs())
        self.assertEqual(len(types_actifs), 1)
        self.assertEqual(types_actifs[0], self.type_adherent)

        # Vérifier qu'il est bien actif
        self.assertTrue(membre.est_type_actif(self.type_adherent))

    def test_creer_membre_avec_compte_rollback_si_erreur(self):
        """Test rollback de la transaction si erreur"""
        # Compter les objets avant
        nb_users_avant = CustomUser.objects.count()
        nb_membres_avant = Membre.objects.count()

        # Tenter de créer avec un email déjà utilisé par un utilisateur
        CustomUser.objects.create_user(
            username='existing',
            email='existing@example.com',
            password='test123'
        )

        # Tenter de créer un membre avec le même email
        with self.assertRaises(ValidationError):
            UserCreationService.creer_membre_avec_compte(
                nom='Test',
                prenom='Rollback',
                email='existing@example.com'  # Email existant
            )

        # Vérifier qu'aucun objet n'a été créé (rollback)
        self.assertEqual(CustomUser.objects.count(), nb_users_avant + 1)  # +1 pour l'existing
        self.assertEqual(Membre.objects.count(), nb_membres_avant)

    def test_creer_membre_avec_compte_relation_onetoone(self):
        """Test la relation OneToOne entre Membre et CustomUser"""
        membre, user, password = UserCreationService.creer_membre_avec_compte(
            nom='Relation',
            prenom='Test',
            email='relation@example.com'
        )

        # Vérifier la relation dans les deux sens
        self.assertEqual(membre.utilisateur, user)
        self.assertEqual(user.membre, membre)

        # Vérifier qu'on peut accéder aux infos dans les deux sens
        self.assertEqual(user.membre.nom, 'RELATION')  # Le modèle convertit en majuscules
        self.assertEqual(membre.utilisateur.username, 'test.relation')
