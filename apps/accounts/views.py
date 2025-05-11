# apps/accounts/views.py
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import get_user_model, update_session_auth_hash, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import LoginView
from django.contrib import messages
from django.views.generic import (
    CreateView, ListView, UpdateView, DeleteView,
    TemplateView, RedirectView, FormView
)
from django.utils import timezone
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse
from django.utils.translation import gettext_lazy as _
from django.db.models import Q
from django.views.decorators.http import require_POST
from django.core.mail import send_mail
from django.conf import settings

from .models import Role, Permission, UserProfile, UserLoginHistory
from .forms import (
    CustomUserCreationForm, UserProfileForm, RoleForm,
    CustomAuthenticationForm
)
from apps.core.services import EmailService


logger = logging.getLogger(__name__)

User = get_user_model()


class CustomLoginView(LoginView):
    """
    Vue personnalisée pour la connexion des utilisateurs.
    Enregistre les tentatives de connexion et met à jour la dernière connexion.
    Redirige immédiatement vers la page de changement de mot de passe si le mot de passe est temporaire.
    """
    form_class = CustomAuthenticationForm
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True

    def form_valid(self, form):
        """Enregistre la connexion réussie et met à jour la dernière connexion"""
        # Obtenir l'utilisateur avant le super() pour accéder à l'utilisateur authentifié
        user = form.get_user()
        
        # Vérifier si le mot de passe est temporaire et rediriger si nécessaire
        if hasattr(user, 'password_temporary') and user.password_temporary:
            # Connecter l'utilisateur d'abord
            super().form_valid(form)
            
            # Enregistrement de l'historique de connexion pour un utilisateur avec mot de passe temporaire
            UserLoginHistory.objects.create(
                user=user,
                ip_address=self.request.META.get('REMOTE_ADDR', ''),
                user_agent=self.request.META.get('HTTP_USER_AGENT', ''),
                session_key=self.request.session.session_key,
                status='success'
            )
            
            # Mise à jour de la dernière connexion
            user.derniere_connexion = timezone.now()
            user.save(update_fields=['derniere_connexion'])
            
            # Ajouter un message pour informer l'utilisateur
            messages.info(
                self.request, 
                _("Votre mot de passe est temporaire. Veuillez le changer maintenant.")
            )
            
            # Rediriger vers la page de changement de mot de passe
            return redirect('accounts:change_password')
        
        # Si le mot de passe n'est pas temporaire, continuer normalement
        response = super().form_valid(form)
        
        # Enregistrement de l'historique de connexion
        UserLoginHistory.objects.create(
            user=user,
            ip_address=self.request.META.get('REMOTE_ADDR', ''),
            user_agent=self.request.META.get('HTTP_USER_AGENT', ''),
            session_key=self.request.session.session_key,
            status='success'
        )
        
        # Mise à jour de la dernière connexion
        user.derniere_connexion = timezone.now()
        user.save(update_fields=['derniere_connexion'])
        
        return response
    
    def form_invalid(self, form):
        """Enregistre les tentatives de connexion échouées"""
        # Pour les échecs de connexion, on ne peut pas enregistrer l'utilisateur directement
        # car l'authentification a échoué
        email = form.cleaned_data.get('username', '')  # Dans votre cas, 'username' contient l'email
        
        # Essayer de trouver l'utilisateur correspondant à cet email
        try:
            user = User.objects.get(email=email)
            # Enregistrer l'échec avec l'utilisateur trouvé
            UserLoginHistory.objects.create(
                user=user,
                ip_address=self.request.META.get('REMOTE_ADDR', ''),
                user_agent=self.request.META.get('HTTP_USER_AGENT', ''),
                status='failed'
            )
        except User.DoesNotExist:
            # L'utilisateur n'existe pas, on ne peut pas enregistrer l'historique
            pass
        
        return super().form_invalid(form)


class RegisterView(CreateView):
    """
    Vue pour l'inscription d'un nouvel utilisateur.
    Envoie un email d'activation après l'inscription.
    """
    model = User
    form_class = CustomUserCreationForm
    template_name = 'accounts/register.html'
    success_url = reverse_lazy('accounts:login')
    
    def get(self, request, *args, **kwargs):
        # Rediriger si l'utilisateur est déjà connecté
        if request.user.is_authenticated:
            return redirect('home')
        return super().get(request, *args, **kwargs)
    
    def form_valid(self, form):
        response = super().form_valid(form)
        
        # Assigner le rôle par défaut si disponible
        default_role = Role.objects.filter(is_default=True).first()
        if default_role:
            self.object.role = default_role
            self.object.save(update_fields=['role'])
        
        # Message de succès
        messages.success(
            self.request, 
            _("Votre compte a été créé avec succès. Veuillez vérifier votre email pour l'activer.")
        )
        
        logger.info(f"Nouvel utilisateur inscrit: {self.object.email}")
        
        return response


def activate_account(request, activation_key):
    """
    Vue pour activer un compte utilisateur à partir du lien d'activation.
    """
    user = User.objects.filter(cle_activation=activation_key, is_active=False).first()
    
    if user:
        # Vérifier si la clé n'a pas expiré (24h)
        expiration_time = timezone.now() - timezone.timedelta(days=1)
        if user.date_joined > expiration_time:
            user.is_active = True
            user.cle_activation = None
            user.save(update_fields=['is_active', 'cle_activation'])
            
            messages.success(
                request, 
                _("Votre compte a été activé avec succès. Vous pouvez maintenant vous connecter.")
            )
            logger.info(f"Compte activé: {user.email}")
            
            return redirect('accounts:login')
        else:
            messages.error(
                request, 
                _("Le lien d'activation a expiré. Veuillez demander un nouveau lien.")
            )
            return redirect('accounts:resend_activation')
    else:
        messages.error(
            request, 
            _("Le lien d'activation est invalide.")
        )
        return redirect('accounts:login')


def custom_logout(request):
    """
    Vue personnalisée pour la déconnexion qui s'assure que la session est 
    complètement invalidée et que les cookies sont supprimés.
    """
    # Déconnecter l'utilisateur (invalidation de session)
    logout(request)
    
    # Créer une réponse de redirection
    response = redirect('accounts:login')
    
    # Supprimer explicitement le cookie de session
    response.delete_cookie('sessionid')
    
    # Éventuellement, supprimer d'autres cookies si nécessaire
    response.delete_cookie('csrftoken')
    
    # Ajouter des en-têtes pour éviter la mise en cache
    response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    
    return response


@require_POST
def resend_activation(request):
    """
    Vue pour renvoyer un email d'activation.
    """
    email = request.POST.get('email')
    
    if not email:
        messages.error(request, _("Veuillez fournir une adresse email."))
        return redirect('accounts:login')
    
    # Pour des raisons de sécurité, ne pas divulguer si le compte existe
    user = User.objects.filter(email=email, is_active=False).first()
    
    if user:
        # Générer une nouvelle clé d'activation
        activation_key = user.generate_activation_key()
        
        # Envoyer l'email d'activation
        activation_link = f"{settings.SITE_URL}/accounts/activate/{activation_key}/"
        
        # Utiliser EmailService pour envoyer un email formaté
        EmailService.send_template_email(
            'emails/account_activation',
            {
                'user': user,
                'activation_link': activation_link,
                'site_name': settings.SITE_NAME,
            },
            _('Activation de votre compte'),
            user.email
        )
        
        logger.info(f"Nouveau lien d'activation envoyé à: {user.email}")
    
    # Message générique qui ne révèle pas si l'email existe
    messages.success(
        request, 
        _("Si un compte inactif existe avec cette adresse email, un nouveau lien d'activation a été envoyé.")
    )
    
    return redirect('accounts:login')


@login_required
def profile_view(request):
    """
    Vue pour afficher le profil utilisateur.
    """
    return render(request, 'accounts/profile.html', {'user': request.user})


@login_required
def edit_profile(request):
    """
    Vue pour modifier le profil utilisateur.
    """
    user = request.user
    profile = user.profile
    
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=profile, user=user)
        
        if form.is_valid():
            form.save(user=user)
            messages.success(request, _("Votre profil a été mis à jour avec succès."))
            return redirect('accounts:profile')
    else:
        form = UserProfileForm(instance=profile, user=user)
    
    return render(request, 'accounts/edit_profile.html', {'form': form})


class ChangePasswordView(LoginRequiredMixin, FormView):
    """Vue pour changer son mot de passe"""
    template_name = 'accounts/change_password.html'
    form_class = PasswordChangeForm
    success_url = reverse_lazy('accounts:profile')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_temporary'] = getattr(self.request.user, 'password_temporary', False)
        
        # Si c'est un mot de passe temporaire, ajouter un message d'information
        if context['is_temporary']:
            messages.info(
                self.request, 
                _("Pour des raisons de sécurité, vous devez changer votre mot de passe temporaire.")
            )
        
        return context

    def form_valid(self, form):
        user = form.save()
        
        # Si c'était un mot de passe temporaire, le marquer comme permanent
        if hasattr(user, 'password_temporary') and user.password_temporary:
            user.password_temporary = False
            user.save(update_fields=['password_temporary'])
        
        # Mettre à jour le hash de session pour éviter la déconnexion
        update_session_auth_hash(self.request, user)
        
        # Message de succès
        messages.success(
            self.request,
            _("Votre mot de passe a été modifié avec succès.")
        )
        
        return super().form_valid(form)

    def form_invalid(self, form):
        # Afficher des messages d'erreur explicites pour chaque champ
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(self.request, f"{error}")
        
        return super().form_invalid(form)


class SuperUserRequiredMixin(UserPassesTestMixin):
    """
    Mixin pour restreindre l'accès aux superutilisateurs.
    """
    def test_func(self):
        return self.request.user.is_superuser


class RoleListView(LoginRequiredMixin, SuperUserRequiredMixin, ListView):
    """
    Vue pour lister les rôles (accessible uniquement aux superutilisateurs).
    """
    model = Role
    template_name = 'accounts/role_list.html'
    context_object_name = 'roles'
    
    def get_queryset(self):
        return Role.objects.all().prefetch_related('permissions')


class RoleCreateView(LoginRequiredMixin, SuperUserRequiredMixin, CreateView):
    """
    Vue pour créer un nouveau rôle.
    """
    model = Role
    form_class = RoleForm
    template_name = 'accounts/role_form.html'
    success_url = reverse_lazy('accounts:role_list')
    
    def form_valid(self, form):
        messages.success(self.request, _("Le rôle a été créé avec succès."))
        return super().form_valid(form)


class RoleUpdateView(LoginRequiredMixin, SuperUserRequiredMixin, UpdateView):
    """
    Vue pour modifier un rôle existant.
    """
    model = Role
    form_class = RoleForm
    template_name = 'accounts/role_form.html'
    success_url = reverse_lazy('accounts:role_list')
    
    def form_valid(self, form):
        messages.success(self.request, _("Le rôle a été modifié avec succès."))
        return super().form_valid(form)


class RoleDeleteView(LoginRequiredMixin, SuperUserRequiredMixin, DeleteView):
    """
    Vue pour supprimer un rôle.
    """
    model = Role
    template_name = 'accounts/role_confirm_delete.html'
    success_url = reverse_lazy('accounts:role_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, _("Le rôle a été supprimé avec succès."))
        return super().delete(request, *args, **kwargs)


@login_required
def check_session(request):
    """
    API interne pour vérifier l'état de la session utilisateur.
    Utilisée par le middleware de session et les scripts frontend.
    """
    return JsonResponse({
        'authenticated': request.user.is_authenticated,
        'user_id': request.user.id if request.user.is_authenticated else None,
        'session_valid': True,
        'timestamp': timezone.now().timestamp()
    })


def required_permission(permission_code):
    """
    Décorateur pour restreindre l'accès à une vue basée sur une permission.
    """
    def decorator(view_func):
        view_func.required_permission = permission_code
        return view_func
    return decorator


class ProtectedPageView(LoginRequiredMixin, ListView):
    """
    Vue protégée pour afficher une liste d'utilisateurs.
    Combine les fonctionnalités de TemplateView avec celles de ListView.
    """
    model = User
    template_name = 'accounts/protected_page.html'
    context_object_name = 'users'
    login_url = '/accounts/login/'
    redirect_field_name = 'next'
    
    def get_queryset(self):
        # Limiter la liste pour des raisons de performance
        return User.objects.filter(is_active=True)[:5]
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['now'] = timezone.now()
        return context


class TermsView(TemplateView):
    """
    Vue pour afficher les termes et conditions d'utilisation.
    """
    template_name = 'accounts/terms.html'


class EmailVerificationView(RedirectView):
    """
    Vue pour vérifier l'email d'un utilisateur via un token
    """
    def get_redirect_url(self, *args, **kwargs):
        token = kwargs.get('token')
        user = get_object_or_404(User, email_verification_token=token)
        
        if user.verify_email(token):
            messages.success(self.request, _("Votre adresse email a été vérifiée avec succès. Vous pouvez maintenant vous connecter."))
            return reverse('accounts:login')
        else:
            messages.error(self.request, _("Le lien de vérification a expiré ou est invalide. Veuillez demander un nouveau lien."))
            return reverse('accounts:email_verification_required')


class EmailVerificationRequiredView(TemplateView):
    """
    Vue affichée lorsque la vérification d'email est nécessaire
    """
    template_name = 'accounts/email_verification_required.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context
    
    def post(self, request, *args, **kwargs):
        """
        Gère la demande de renvoi du lien de vérification
        """
        email = request.POST.get('email')
        if email:
            self._send_verification_email(email)
        
        return self.render_to_response(self.get_context_data())
    
    def _send_verification_email(self, email):
        """
        Méthode auxiliaire pour envoyer l'email de vérification
        """
        try:
            user = User.objects.get(email=email)
            if not user.is_email_verified:
                # Générer un nouveau token
                token = user.generate_email_verification_token()
                
                # Préparer le lien de vérification
                verification_url = self.request.build_absolute_uri(
                    reverse('accounts:email_verify', kwargs={'token': token})
                )
                
                # Envoyer l'email de vérification
                context = {
                    'user': user,
                    'verification_url': verification_url
                }
                
                EmailService.send_template_email(
                    'emails/email_verification',
                    context,
                    _("Vérification de votre adresse email"),
                    user.email
                )
                
                logger.info(f"Email de vérification envoyé à {user.email}")
            
        except User.DoesNotExist:
            logger.info(f"Tentative de vérification pour une adresse email inexistante: {email}")
        
        # Toujours afficher le même message pour éviter les fuites d'information
        messages.success(self.request, _("Si cette adresse est associée à un compte, un email de vérification sera envoyé."))