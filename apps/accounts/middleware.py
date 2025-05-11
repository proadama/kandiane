# apps/accounts/middleware.py
from django.utils import timezone
from django.urls import resolve, reverse
from django.shortcuts import redirect
from django.conf import settings
from django.contrib.auth import logout
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
import re


class LastUserActivityMiddleware:
    """
    Middleware qui met à jour la dernière date d'activité d'un utilisateur.
    """
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        response = self.get_response(request)
        
        # Mettre à jour la dernière activité de l'utilisateur
        if request.user.is_authenticated:
            # Mettre à jour seulement si la dernière mise à jour date de plus de 15 minutes
            update_threshold = timezone.now() - timezone.timedelta(minutes=15)
            if not request.user.derniere_connexion or request.user.derniere_connexion < update_threshold:
                request.user.derniere_connexion = timezone.now()
                request.user.save(update_fields=['derniere_connexion'])
        
        return response


class RolePermissionMiddleware:
    """
    Middleware qui vérifie les permissions utilisateur basées sur les rôles.
    """
    def __init__(self, get_response):
        self.get_response = get_response
        self.exempt_urls = [
            re.compile(settings.LOGIN_URL.lstrip('/')),
            re.compile(r'^admin/.*'),
            re.compile(r'^accounts/login/.*'),
            re.compile(r'^accounts/logout/.*'),
            re.compile(r'^accounts/register/.*'),
            re.compile(r'^accounts/password/.*'),
            re.compile(r'^accounts/activate/.*'),
            re.compile(r'^static/.*'),
            re.compile(r'^media/.*'),
        ]
        
    def __call__(self, request):
        # Continuer si l'utilisateur n'est pas authentifié
        if not request.user.is_authenticated:
            return self.get_response(request)
        
        # Vérifier si l'URL est exemptée
        path = request.path_info.lstrip('/')
        for exempt_url in self.exempt_urls:
            if exempt_url.match(path):
                return self.get_response(request)
        
        # Obtenir la vue résolue pour cette URL
        resolver = resolve(request.path_info)
        view_name = resolver.view_name
        
        # Vérifier les permissions requises (stockées dans les attributs de la vue)
        view_func = resolver.func
        required_permission = getattr(view_func, 'required_permission', None)
        
        if required_permission:
            if not request.user.has_permission(required_permission):
                messages.error(request, _("Vous n'avez pas les permissions nécessaires pour accéder à cette page."))
                return redirect(settings.LOGIN_REDIRECT_URL)
        
        return self.get_response(request)


class SessionExpiryMiddleware:
    """
    Middleware qui gère l'expiration des sessions utilisateur.
    """
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        if request.user.is_authenticated:
            # Vérifier si l'utilisateur a été désactivé
            if not request.user.is_active or request.user.date_desactivation:
                logout(request)
                messages.error(request, _("Votre compte a été désactivé."))
                return redirect(settings.LOGIN_URL)
            
            # Vérifier l'âge de la session
            if 'last_activity' in request.session:
                last_activity = request.session['last_activity']
                session_age = timezone.now().timestamp() - last_activity
                
                # Déconnecter si la session est trop ancienne (par défaut: 30 minutes)
                session_timeout = getattr(settings, 'SESSION_IDLE_TIMEOUT', 1800)
                if session_age > session_timeout:
                    logout(request)
                    messages.info(request, _("Votre session a expiré pour des raisons de sécurité. Veuillez vous reconnecter."))
                    return redirect(settings.LOGIN_URL)
            
            # Mettre à jour l'horodatage de la dernière activité
            request.session['last_activity'] = timezone.now().timestamp()
        
        return self.get_response(request)

class TemporaryPasswordMiddleware:
    """
    Middleware qui vérifie si l'utilisateur a un mot de passe temporaire
    et le redirige vers la page de changement de mot de passe si nécessaire
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        # Vérifier si l'utilisateur est authentifié
        if request.user.is_authenticated:
            # Vérifier si l'utilisateur a un mot de passe temporaire
            if hasattr(request.user, 'password_temporary') and request.user.password_temporary:
                # Path actuel pour éviter les boucles infinies
                current_path = request.path
                
                # Liste des chemins à exclure
                excluded_paths = [
                    '/accounts/profile/change-password/',  # URL correcte selon urls.py
                    '/accounts/logout/',
                    '/admin/',
                    '/static/',
                    '/media/',
                ]
                
                # Vérifier si le chemin actuel doit être exclu
                should_redirect = True
                for path in excluded_paths:
                    if current_path.startswith(path):
                        should_redirect = False
                        break
                
                if should_redirect:
                    # Informer l'utilisateur qu'il doit changer son mot de passe
                    messages.info(
                        request, 
                        _("""
                        <div class="d-flex align-items-center">
                            <i class="fas fa-info-circle text-info me-3 fa-2x"></i>
                            <div>
                                <h5 class="mb-1">Action requise</h5>
                                <p class="mb-0">Votre mot de passe est temporaire. Veuillez le changer maintenant.</p>
                            </div>
                        </div>
                        """)
                    )
                    
                    # Rediriger vers la page de changement de mot de passe
                    return redirect('accounts:change_password')
        
        # Exécuter la vue et continuer
        response = self.get_response(request)
        
        return response