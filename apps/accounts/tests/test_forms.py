# apps/accounts/tests/test_forms.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.accounts.forms import (
    CustomUserCreationForm, CustomAuthenticationForm,
    UserProfileForm, RoleForm
)
from apps.accounts.models import Role, Permission, UserProfile

User = get_user_model()

class CustomUserCreationFormTest(TestCase):
    def test_form_with_valid_data(self):
        form_data = {
            'email': 'test@example.com',
            'username': 'testuser',
            'first_name': 'Test',
            'last_name': 'User',
            'password1': 'testpassword123',
            'password2': 'testpassword123',
            'accepte_communications': True
        }
        form = CustomUserCreationForm(data=form_data)
        self.assertTrue(form.is_valid())
        
    def test_form_with_mismatched_passwords(self):
        form_data = {
            'email': 'test@example.com',
            'username': 'testuser',
            'first_name': 'Test',
            'last_name': 'User',
            'password1': 'testpassword123',
            'password2': 'differentpassword',
            'accepte_communications': True
        }
        form = CustomUserCreationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('password2', form.errors)
        
    def test_form_with_existing_email(self):
        User.objects.create_user(
            email='existing@example.com',
            username='existinguser',
            password='testpassword'
        )
        
        form_data = {
            'email': 'existing@example.com',  # Email déjà utilisé
            'username': 'testuser',
            'first_name': 'Test',
            'last_name': 'User',
            'password1': 'testpassword123',
            'password2': 'testpassword123',
            'accepte_communications': True
        }
        form = CustomUserCreationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)


class UserProfileFormTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpassword'
        )
        self.profile = UserProfile.objects.get(user=self.user)
        
    def test_form_with_valid_data(self):
        form_data = {
            'first_name': 'Test',
            'last_name': 'User',
            'telephone': '0123456789',
            'bio': 'Test bio',
            'date_naissance': '1990-01-01',
            'adresse': '123 Test Street',
            'ville': 'Test City',
            'code_postal': '12345',
            'pays': 'Test Country'
        }
        form = UserProfileForm(data=form_data, instance=self.profile, user=self.user)
        self.assertTrue(form.is_valid())
        
    def test_form_save_updates_user_data(self):
        form_data = {
            'first_name': 'Updated',
            'last_name': 'Name',
            'telephone': '9876543210',
            'bio': 'Updated bio',
            'adresse': 'Updated address'
        }
        form = UserProfileForm(data=form_data, instance=self.profile, user=self.user)
        self.assertTrue(form.is_valid())
        form.save(user=self.user)
        
        # Rafraîchir l'utilisateur depuis la base de données
        self.user.refresh_from_db()
        self.profile.refresh_from_db()
        
        # Vérifier que les données de l'utilisateur ont été mises à jour
        self.assertEqual(self.user.first_name, 'Updated')
        self.assertEqual(self.user.last_name, 'Name')
        self.assertEqual(self.user.telephone, '9876543210')
        self.assertEqual(self.profile.bio, 'Updated bio')
        self.assertEqual(self.profile.adresse, 'Updated address')