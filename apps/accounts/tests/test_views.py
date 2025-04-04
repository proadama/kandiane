# apps/accounts/tests/test_views.py
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.accounts.models import Role, Permission, RolePermission

User = get_user_model()

class AccountsViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.role = Role.objects.create(nom="Testeur", is_default=True)
        
        # Créer un utilisateur actif
        self.active_user = User.objects.create_user(
            email='active@example.com',
            username='activeuser',
            password='testpassword',
            role=self.role,
            is_active=True
        )
        
        # Créer un utilisateur inactif avec clé d'activation
        self.inactive_user = User.objects.create_user(
            email='inactive@example.com',
            username='inactiveuser',
            password='testpassword',
            role=self.role,
            is_active=False
        )
        self.inactive_user.cle_activation = 'testactivationkey'
        self.inactive_user.save()
        
        # Créer un superutilisateur
        self.admin_user = User.objects.create_superuser(
            email='admin@example.com',
            username='adminuser',
            password='adminpassword'
        )
        
        # URLs pour les tests
        self.login_url = reverse('accounts:login')
        self.register_url = reverse('accounts:register')
        self.profile_url = reverse('accounts:profile')
        self.edit_profile_url = reverse('accounts:edit_profile')
        self.change_password_url = reverse('accounts:change_password')
        self.activate_url = reverse('accounts:activate', kwargs={'activation_key': 'testactivationkey'})
        
    def test_login_view_get(self):
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/login.html')
        
    def test_login_view_post_valid(self):
        response = self.client.post(self.login_url, {
            'username': 'active@example.com',
            'password': 'testpassword'
        })
        self.assertEqual(response.status_code, 302)  # Redirection après connexion
        self.assertTrue(response.url.startswith('/'))  # Redirection vers la page d'accueil
        
    def test_login_view_post_invalid(self):
        response = self.client.post(self.login_url, {
            'username': 'active@example.com',
            'password': 'wrongpassword'
        })
        self.assertEqual(response.status_code, 200)  # Retour au formulaire
        self.assertTemplateUsed(response, 'accounts/login.html')
        self.assertContains(response, "Veuillez saisir une adresse email et un mot de passe valides")
        
    def test_register_view_get(self):
        response = self.client.get(self.register_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/register.html')
        
    def test_register_view_post_valid(self):
        response = self.client.post(self.register_url, {
            'email': 'newuser@example.com',
            'username': 'newuser',
            'first_name': 'New',
            'last_name': 'User',
            'password1': 'newpassword123',
            'password2': 'newpassword123',
            'accepte_communications': True
        })
        self.assertEqual(response.status_code, 302)  # Redirection après inscription
        self.assertEqual(User.objects.filter(email='newuser@example.com').count(), 1)
        
        # Vérifier que l'utilisateur est inactif et a une clé d'activation
        new_user = User.objects.get(email='newuser@example.com')
        self.assertFalse(new_user.is_active)
        self.assertIsNotNone(new_user.cle_activation)
        
    def test_activate_account_valid(self):
        response = self.client.get(self.activate_url)
        self.assertEqual(response.status_code, 302)  # Redirection après activation
        
        # Vérifier que l'utilisateur est maintenant actif
        self.inactive_user.refresh_from_db()
        self.assertTrue(self.inactive_user.is_active)
        self.assertIsNone(self.inactive_user.cle_activation)
        
    def test_profile_view_authenticated(self):
        self.client.login(username='active@example.com', password='testpassword')
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/profile.html')
        
    def test_profile_view_unauthenticated(self):
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 302)  # Redirection vers la page de connexion
        
    def test_edit_profile_authenticated(self):
        self.client.login(username='active@example.com', password='testpassword')
        response = self.client.get(self.edit_profile_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/edit_profile.html')
        
        # Test de la mise à jour du profil
        response = self.client.post(self.edit_profile_url, {
            'first_name': 'Updated',
            'last_name': 'User',
            'telephone': '0123456789',
            'bio': 'Updated bio',
            'adresse': 'Updated address',
            'ville': 'Updated City',
            'code_postal': '12345',
            'pays': 'Updated Country'
        })
        self.assertEqual(response.status_code, 302)  # Redirection après mise à jour
        
        # Vérifier que le profil a été mis à jour
        self.active_user.refresh_from_db()
        self.assertEqual(self.active_user.first_name, 'Updated')
        self.assertEqual(self.active_user.profile.adresse, 'Updated address')