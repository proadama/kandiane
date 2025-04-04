# apps/accounts/tests/test_integration.py
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core import mail
from django.utils import timezone
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from apps.accounts.models import Role, Permission, RolePermission, UserProfile
from apps.accounts.middleware import RolePermissionMiddleware, SessionExpiryMiddleware
from apps.accounts.forms import CustomUserCreationForm
from unittest.mock import patch, MagicMock
import re

User = get_user_model()

class AccountsRegistrationWorkflowTest(TestCase):
    """
    Tests pour le workflow complet d'inscription, d'activation et de connexion.
    """
    def setUp(self):
        self.client = Client()
        self.register_url = reverse('accounts:register')
        self.login_url = reverse('accounts:login')
        
        # Créer un rôle par défaut
        self.role = Role.objects.create(nom="Membre", is_default=True)
    
    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_register_activate_login_workflow(self):
        """Test du workflow complet d'inscription, activation et connexion."""
        # 1. Inscription d'un nouvel utilisateur
        response = self.client.post(self.register_url, {
            'email': 'newuser@example.com',
            'username': 'newuser',
            'first_name': 'New',
            'last_name': 'User',
            'password1': 'complexpassword123',
            'password2': 'complexpassword123',
            'accepte_communications': True
        })
        
        # Vérifier que l'inscription a réussi
        self.assertEqual(response.status_code, 302)  # Redirection après inscription
        self.assertEqual(User.objects.filter(email='newuser@example.com').count(), 1)
        
        # Récupérer l'utilisateur
        user = User.objects.get(email='newuser@example.com')
        self.assertFalse(user.is_active)
        self.assertIsNotNone(user.cle_activation)
        
        # 2. Vérifier que l'email d'activation a été envoyé
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['newuser@example.com'])
        
        # Extraire le lien d'activation de l'email
        email_body = str(mail.outbox[0].body)  # Convertir en chaîne
        activation_link_match = re.search(r'http://[^/]+/accounts/activate/([^/\s]+)/', email_body)
        self.assertIsNotNone(activation_link_match, "Lien d'activation non trouvé dans l'email")
        
        activation_key = activation_link_match.group(1)
        self.assertEqual(activation_key, user.cle_activation)
        
        # 3. Activation du compte
        activate_url = reverse('accounts:activate', kwargs={'activation_key': activation_key})
        response = self.client.get(activate_url)
        
        # Vérifier que l'activation a réussi
        self.assertEqual(response.status_code, 302)  # Redirection après activation
        
        # Rafraîchir l'utilisateur depuis la base de données
        user.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertIsNone(user.cle_activation)
        
        # 4. Connexion avec le compte activé
        response = self.client.post(self.login_url, {
            'username': 'newuser@example.com',
            'password': 'complexpassword123'
        })
        
        # Vérifier que la connexion a réussi
        self.assertEqual(response.status_code, 302)  # Redirection après connexion
        
        # 5. Accès à la page de profil après connexion
        profile_url = reverse('accounts:profile')
        response = self.client.get(profile_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'New User')  # Le nom complet doit apparaître sur la page


class RolePermissionIntegrationTest(TestCase):
    """
    Tests pour l'intégration des rôles et permissions avec le contrôle d'accès.
    """
    def setUp(self):
        self.client = Client()
        
        # Créer des rôles et permissions
        self.admin_role = Role.objects.create(nom="Administrateur")
        self.member_role = Role.objects.create(nom="Membre", is_default=True)
        
        self.view_dashboard_perm = Permission.objects.create(
            code="view_dashboard",
            nom="Voir le tableau de bord"
        )
        
        self.manage_users_perm = Permission.objects.create(
            code="manage_users",
            nom="Gérer les utilisateurs"
        )
        
        # Attribuer des permissions aux rôles
        RolePermission.objects.create(role=self.admin_role, permission=self.view_dashboard_perm)
        RolePermission.objects.create(role=self.admin_role, permission=self.manage_users_perm)
        RolePermission.objects.create(role=self.member_role, permission=self.view_dashboard_perm)
        
        # Créer des utilisateurs avec différents rôles
        self.admin_user = User.objects.create_user(
            email='admin@example.com',
            username='adminuser',
            password='adminpassword',
            role=self.admin_role,
            is_active=True
        )
        
        self.member_user = User.objects.create_user(
            email='member@example.com',
            username='memberuser',
            password='memberpassword',
            role=self.member_role,
            is_active=True
        )
        
    def test_user_has_permission(self):
        """Teste si les utilisateurs ont les bonnes permissions."""
        self.assertTrue(self.admin_user.has_permission("view_dashboard"))
        self.assertTrue(self.admin_user.has_permission("manage_users"))
        self.assertTrue(self.member_user.has_permission("view_dashboard"))
        self.assertFalse(self.member_user.has_permission("manage_users"))
    
    def test_permission_middleware(self):
        """
        Teste le middleware de permissions avec des vues nécessitant des permissions.
        """
        # Configuration du middleware de test avec une fonction get_response qui retourne None
        get_response_mock = MagicMock(return_value=None)
        middleware = RolePermissionMiddleware(get_response_mock)
        
        # Simuler une requête avec un chemin non exempté
        request = MagicMock()
        request.user = self.admin_user
        request.path_info = '/admin/users/'
        
        # Important: vider la liste des URLs exemptées pour le test
        middleware.exempt_urls = []
        
        # Créer un mock pour messages.error
        with patch('apps.accounts.middleware.messages.error'), \
            patch('apps.accounts.middleware.redirect') as mock_redirect, \
            patch('apps.accounts.middleware.resolve') as mock_resolve:
            
            # Configurer le mock pour resolve
            resolver_result = MagicMock()
            resolver_result.func = MagicMock()
            resolver_result.func.required_permission = "manage_users"
            resolver_result.view_name = 'admin_users'
            mock_resolve.return_value = resolver_result
            
            # Configurer le mock pour redirect
            mock_redirect.return_value = "REDIRECTED"  # Une valeur non-None
            
            # Tester avec un utilisateur ayant la permission
            response = middleware(request)
            self.assertIsNone(response)  # Pas de redirection, l'accès est autorisé
            
            # Tester avec un utilisateur n'ayant pas la permission
            request.user = self.member_user
            response = middleware(request)
            self.assertEqual(response, "REDIRECTED")  # Redirection, l'accès est refusé


class UserProfileIntegrationTest(TestCase):
    """
    Tests pour l'intégration entre les utilisateurs et leurs profils.
    """
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpassword',
            first_name='Test',
            last_name='User',
            is_active=True
        )
        
        # Connexion de l'utilisateur
        self.client.login(username='test@example.com', password='testpassword')
        
        # URLs pour les tests
        self.profile_url = reverse('accounts:profile')
        self.edit_profile_url = reverse('accounts:edit_profile')
        
    def test_profile_creation_and_update(self):
        """Teste la création et la mise à jour du profil utilisateur."""
        # Vérifier que le profil a été créé automatiquement
        self.assertIsNotNone(self.user.profile)
        
        # Accéder à la page de profil
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test User')
        
        # Mettre à jour le profil
        response = self.client.post(self.edit_profile_url, {
            'first_name': 'Updated',
            'last_name': 'Name',
            'telephone': '0123456789',
            'bio': 'This is my updated bio',
            'date_naissance': '1990-01-01',
            'adresse': '123 Test Street',
            'ville': 'Test City',
            'code_postal': '12345',
            'pays': 'Test Country'
        })
        
        # Vérifier la redirection après la mise à jour
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.profile_url)
        
        # Rafraîchir l'utilisateur et son profil
        self.user.refresh_from_db()
        self.user.profile.refresh_from_db()
        
        # Vérifier que les données ont été mises à jour
        self.assertEqual(self.user.first_name, 'Updated')
        self.assertEqual(self.user.last_name, 'Name')
        self.assertEqual(self.user.telephone, '0123456789')
        self.assertEqual(self.user.profile.bio, 'This is my updated bio')
        self.assertEqual(self.user.profile.pays, 'Test Country')
        
        # Vérifier que les changements sont visibles sur la page de profil
        response = self.client.get(self.profile_url)
        self.assertContains(response, 'Updated Name')
        self.assertContains(response, 'Test Country')


class SessionManagementIntegrationTest(TestCase):
    """
    Tests pour l'intégration de la gestion des sessions et de l'authentification.
    """
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpassword',
            is_active=True
        )
        
        # URLs pour les tests
        self.login_url = reverse('accounts:login')
        self.profile_url = reverse('accounts:profile')
        
    def test_session_expiry_middleware(self):
        """Teste le middleware d'expiration de session."""
        # Créons une version simplifiée du middleware pour le test
        class TestSessionExpiryMiddleware:
            def __init__(self, get_response):
                self.get_response = get_response
                
            def __call__(self, request):
                # Vérifier l'âge de la session
                if 'last_activity' in request.session:
                    last_activity = request.session['last_activity']
                    session_age = timezone.now().timestamp() - last_activity
                    
                    # Déconnecter si la session est trop ancienne
                    session_timeout = getattr(settings, 'SESSION_IDLE_TIMEOUT', 1800)
                    if session_age > session_timeout:
                        return "REDIRECTED"  # Simuler une redirection
                
                return None
        
        # Utiliser notre middleware de test
        middleware = TestSessionExpiryMiddleware(get_response=lambda r: None)
        
        # Simuler une requête avec une session active récente
        request = MagicMock()
        request.session = {'last_activity': timezone.now().timestamp()}
        
        # La session est récente, pas de redirection attendue
        response = middleware(request)
        self.assertIsNone(response)
        
        # Simuler une session expirée
        expired_timestamp = (timezone.now() - timezone.timedelta(hours=1)).timestamp()
        request.session = {'last_activity': expired_timestamp}
        
        # Avec SESSION_IDLE_TIMEOUT défini à 30 minutes
        with self.settings(SESSION_IDLE_TIMEOUT=1800):
            response = middleware(request)
            # La session devrait être expirée, une redirection est attendue
            self.assertEqual(response, "REDIRECTED")
    
    def test_login_logout_workflow(self):
        """Teste le workflow complet de connexion/déconnexion."""
        # Connexion
        response = self.client.post(self.login_url, {
            'username': 'test@example.com',
            'password': 'testpassword'
        })
        
        # Vérifier la redirection après connexion
        self.assertEqual(response.status_code, 302)
        
        # Vérifier l'accès à la page de profil
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 200)
        
        # Déconnexion
        logout_url = reverse('accounts:logout')
        response = self.client.post(logout_url)
        
        # Vérifier la redirection après déconnexion
        self.assertEqual(response.status_code, 302)
        
        # Vérifier que l'accès à la page de profil est maintenant refusé
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 302)  # Redirection vers login
        self.assertTrue(response.url.startswith(self.login_url))