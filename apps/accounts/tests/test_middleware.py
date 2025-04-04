# apps/accounts/tests/test_middleware.py
from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.auth.middleware import AuthenticationMiddleware
from django.contrib.messages.middleware import MessageMiddleware
from django.utils import timezone
from apps.accounts.middleware import LastUserActivityMiddleware, SessionExpiryMiddleware
import time

User = get_user_model()

class LastUserActivityMiddlewareTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpassword'
        )
        self.middleware = LastUserActivityMiddleware(get_response=lambda r: r)
        
    def test_middleware_updates_last_activity(self):
        # Créer une requête et ajouter un utilisateur authentifié
        request = self.factory.get('/')
        middleware = SessionMiddleware(get_response=lambda r: r)
        middleware.process_request(request)
        
        auth_middleware = AuthenticationMiddleware(get_response=lambda r: r)
        auth_middleware.process_request(request)
        
        request.user = self.user
        request.session.save()
        
        # Définir une dernière connexion passée
        self.user.derniere_connexion = timezone.now() - timezone.timedelta(hours=1)
        self.user.save()
        
        # Appliquer le middleware
        self.middleware(request)
        
        # Rafraîchir l'utilisateur depuis la base de données
        self.user.refresh_from_db()
        
        # Vérifier que la dernière activité a été mise à jour
        self.assertGreater(self.user.derniere_connexion, timezone.now() - timezone.timedelta(minutes=1))


class SessionExpiryMiddlewareTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpassword'
        )
        self.middleware = SessionExpiryMiddleware(get_response=lambda r: r)
        
    def test_middleware_updates_last_activity_timestamp(self):
        # Créer une requête et ajouter un utilisateur authentifié
        request = self.factory.get('/')
        middleware = SessionMiddleware(get_response=lambda r: r)
        middleware.process_request(request)
        
        auth_middleware = AuthenticationMiddleware(get_response=lambda r: r)
        auth_middleware.process_request(request)
        
        message_middleware = MessageMiddleware(get_response=lambda r: r)
        message_middleware.process_request(request)
        
        request.user = self.user
        request.session.save()
        
        # Appliquer le middleware
        self.middleware(request)
        
        # Vérifier que le timestamp de dernière activité est défini
        self.assertIn('last_activity', request.session)
        self.assertIsInstance(request.session['last_activity'], float)