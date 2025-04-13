# apps/membres/tests/test_trash.py
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model

from apps.membres.models import Membre, TypeMembre

User = get_user_model()

class TrashFunctionalityTest(TestCase):
    def setUp(self):
        # Créer un utilisateur admin
        self.admin = User.objects.create_superuser(
            username='admin', 
            email='admin@example.com', 
            password='adminpassword'
        )
        self.client.login(username='admin', password='adminpassword')
        
        # Créer un membre de test
        self.membre = Membre.objects.create(
            nom='Dupont',
            prenom='Jean',
            email='jean.dupont@example.com',
            date_adhesion=timezone.now().date()
        )
    
    def test_soft_delete(self):
        """Vérifier que la suppression logique fonctionne correctement."""
        # Supprimer le membre
        response = self.client.post(reverse('membres:membre_supprimer', args=[self.membre.pk]))
        self.assertEqual(response.status_code, 302)  # Redirection après suppression
        
        # Vérifier que le membre n'apparaît plus dans la liste standard
        response = self.client.get(reverse('membres:membre_liste'))
        self.assertNotContains(response, 'jean.dupont@example.com')
        
        # Vérifier que le membre est bien marqué comme supprimé en BDD
        membre_refresh = Membre.objects.with_deleted().get(pk=self.membre.pk)
        self.assertIsNotNone(membre_refresh.deleted_at)
    
    def test_trash_page(self):
        """Vérifier que la page corbeille fonctionne correctement."""
        # Supprimer le membre
        self.membre.delete()
        
        # Accéder à la corbeille
        response = self.client.get(reverse('membres:membre_corbeille'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'jean.dupont@example.com')
    
    def test_restore(self):
        """Vérifier que la restauration fonctionne correctement."""
        # Supprimer le membre
        self.membre.delete()
        
        # Restaurer le membre
        response = self.client.post(reverse('membres:membre_restaurer', args=[self.membre.pk]))
        self.assertEqual(response.status_code, 302)  # Redirection après restauration
        
        # Vérifier que le membre apparaît à nouveau dans la liste standard
        response = self.client.get(reverse('membres:membre_liste'))
        self.assertContains(response, 'jean.dupont@example.com')
        
        # Vérifier que le membre n'est plus marqué comme supprimé en BDD
        membre_refresh = Membre.objects.get(pk=self.membre.pk)
        self.assertIsNone(membre_refresh.deleted_at)
    
    def test_permanent_delete(self):
        """Vérifier que la suppression définitive fonctionne correctement."""
        # Supprimer le membre
        self.membre.delete()
        
        # Supprimer définitivement le membre
        response = self.client.post(reverse('membres:membre_supprimer_definitif', args=[self.membre.pk]))
        self.assertEqual(response.status_code, 302)  # Redirection après suppression
        
        # Vérifier que le membre n'existe plus du tout
        with self.assertRaises(Membre.DoesNotExist):
            Membre.objects.with_deleted().get(pk=self.membre.pk)