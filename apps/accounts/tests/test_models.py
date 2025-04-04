# apps/accounts/tests/test_models.py
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from apps.accounts.models import Role, Permission, RolePermission, UserProfile

User = get_user_model()

class RoleModelTest(TestCase):
    def setUp(self):
        self.role = Role.objects.create(
            nom="Testeur",
            description="Rôle pour les testeurs",
            is_default=True
        )
    
    def test_role_creation(self):
        self.assertEqual(self.role.nom, "Testeur")
        self.assertEqual(self.role.description, "Rôle pour les testeurs")
        self.assertTrue(self.role.is_default)
        
    def test_string_representation(self):
        self.assertEqual(str(self.role), "Testeur")


class PermissionModelTest(TestCase):
    def setUp(self):
        self.permission = Permission.objects.create(
            code="test_permission",
            nom="Permission de test",
            description="Permission pour tester"
        )
    
    def test_permission_creation(self):
        self.assertEqual(self.permission.code, "test_permission")
        self.assertEqual(self.permission.nom, "Permission de test")
        
    def test_string_representation(self):
        self.assertEqual(str(self.permission), "Permission de test (test_permission)")


class CustomUserModelTest(TestCase):
    def setUp(self):
        self.role = Role.objects.create(nom="Testeur")
        self.user = User.objects.create_user(
            email="test@example.com",
            username="testuser",
            password="testpassword",
            first_name="Test",
            last_name="User",
            role=self.role
        )
    
    def test_user_creation(self):
        self.assertEqual(self.user.email, "test@example.com")
        self.assertEqual(self.user.username, "testuser")
        self.assertEqual(self.user.get_full_name(), "Test User")
        self.assertEqual(self.user.role, self.role)
        
    def test_user_profile_auto_creation(self):
        self.assertIsNotNone(self.user.profile)
        
    def test_has_permission(self):
        # Créer une permission et l'attribuer au rôle
        permission = Permission.objects.create(code="can_test")
        RolePermission.objects.create(role=self.role, permission=permission)
        
        # Tester que l'utilisateur a cette permission
        self.assertTrue(self.user.has_permission("can_test"))
        
        # Tester que l'utilisateur n'a pas une permission inexistante
        self.assertFalse(self.user.has_permission("cannot_test"))
        
    def test_generate_activation_key(self):
        key = self.user.generate_activation_key()
        self.assertIsNotNone(key)
        self.assertEqual(key, self.user.cle_activation)