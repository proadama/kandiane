# apps/accounts/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.views import LoginView
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages
from django.views.generic import CreateView, ListView, UpdateView, DeleteView
from django.utils import timezone
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.utils.translation import gettext_lazy as _
from django.db.models import Q
from django.views.decorators.http import require_POST
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.views.generic import TemplateView, RedirectView
from django.contrib.auth.forms import PasswordResetForm
from django.core.exceptions import ValidationError
from django.contrib.auth.views import LoginView, PasswordResetView

from .models import Role, Permission, UserProfile, UserLoginHistory
from .forms import (
    CustomUserCreationForm, UserProfileForm, RoleForm,
    CustomAuthenticationForm
)
from .middleware import RolePermissionMiddleware
import logging
from django.urls import reverse
from apps.core.services import EmailService
from django.views.generic import FormView


logger = logging.getLogger(__name__)

User = get_user_model()


class CustomLoginView(LoginView):
    """
    Vue personnalisée pour la connexion des utilisateurs.
    Enregistre les tentatives de connexion et met à jour la dernière connexion.
    """
    form_class = CustomAuthenticationForm
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True

    


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

# Supprimer : Ajoutez cette fonction à votre fichier views.py existant

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
    
    user = User.objects.filter(email=email, is_active=False).first()
    
    if not user:
        messages.error(
            request, 
            _("Aucun compte inactif trouvé avec cette adresse email ou le compte est déjà activé.")
        )
        return redirect('accounts:login')
    
    # Générer une nouvelle clé d'activation
    activation_key = user.generate_activation_key()
    
    # Envoyer l'email d'activation
    activation_link = f"{settings.SITE_URL}/accounts/activate/{activation_key}/"
    send_mail(
        _('Activation de votre compte'),
        _(f'Bonjour {user.get_full_name() or user.username},\n\n'
          f'Voici un nouveau lien pour activer votre compte :\n'
          f'{activation_link}\n\n'
          f'Ce lien est valable pendant 24 heures.\n\n'
          f'Cordialement,\n'
          f'L\'équipe {settings.SITE_NAME}'),
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )
    
    messages.success(
        request, 
        _("Un nouveau lien d'activation a été envoyé à votre adresse email.")
    )
    logger.info(f"Nouveau lien d'activation envoyé à: {user.email}")
    
    return redirect('accounts:login')


@login_required
def profile_view(request):
    """
    Vue pour afficher le profil utilisateur.
    """
    user = request.user
    return render(request, 'accounts/profile.html', {'user': user})


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


@login_required
def change_password(request):
    """
    Vue pour changer le mot de passe.
    """
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            # Mettre à jour la session pour éviter la déconnexion
            update_session_auth_hash(request, user)
            messages.success(request, _("Votre mot de passe a été changé avec succès."))
            return redirect('accounts:profile')
    else:
        form = PasswordChangeForm(request.user)
    
    return render(request, 'accounts/change_password.html', {'form': form})


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
        user = get_object_or_404(CustomUser, email_verification_token=token)
        
        if user.verify_email(token):
            messages.success(self.request, _("Votre adresse email a été vérifiée avec succès. Vous pouvez maintenant vous connecter."))
            return reverse('login')
        else:
            messages.error(self.request, _("Le lien de vérification a expiré ou est invalide. Veuillez demander un nouveau lien."))
            return reverse('email_verification_required')

class EmailVerificationRequiredView(TemplateView):
    """
    Vue affichée lorsque la vérification d'email est nécessaire
    """
    template_name = 'accounts/email_verification_required.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Ajouter des infos au contexte si nécessaire
        return context
    
    def post(self, request, *args, **kwargs):
        """
        Gère la demande de renvoi du lien de vérification
        """
        email = request.POST.get('email')
        if email:
            try:
                user = CustomUser.objects.get(email=email)
                if not user.is_email_verified:
                    # Générer un nouveau token
                    token = user.generate_email_verification_token()
                    
                    # Préparer le lien de vérification
                    verification_url = request.build_absolute_uri(
                        reverse('email_verify', kwargs={'token': token})
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
                    
                    messages.success(request, _("Un nouveau lien de vérification a été envoyé à votre adresse email."))
                else:
                    messages.info(request, _("Votre adresse email est déjà vérifiée. Vous pouvez vous connecter."))
            except CustomUser.DoesNotExist:
                # Ne pas divulguer l'existence ou non de l'utilisateur
                messages.success(request, _("Si cette adresse est associée à un compte, un email de vérification sera envoyé."))
        
        return self.render_to_response(self.get_context_data())

class ChangePasswordView(LoginRequiredMixin, FormView):
    """Vue pour changer son mot de passe"""
    template_name = 'accounts/change_password.html'
    form_class = PasswordChangeForm
    success_url = reverse_lazy('dashboard')  # Rediriger vers le tableau de bord après changement

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        user = form.save()
        # Important : mettre à jour le hash de session pour éviter la déconnexion
        update_session_auth_hash(self.request, user)
        
        # Afficher un message de succès
        messages.success(
            self.request,
            _(f"""
            <div class="d-flex align-items-center">
                <i class="fas fa-check-circle text-success me-3 fa-2x"></i>
                <div>
                    <h5 class="mb-1">Mot de passe modifié !</h5>
                    <p class="mb-0">Votre mot de passe a été changé avec succès.</p>
                </div>
            </div>
            """)
        )
        
        return super().form_valid(form)

    def form_invalid(self, form):
        # Afficher des messages d'erreur
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(self.request, f"{error}")
        
        return super().form_invalid(form)
    
def change_password(request, initial_change=False):
    """
    Vue pour changer le mot de passe d'un utilisateur
    Si initial_change=True, cela signifie qu'il s'agit du premier changement après un mot de passe temporaire
    """
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            # Mise à jour du hash de session pour éviter la déconnexion
            update_session_auth_hash(request, user)
            
            # Message de succès formaté avec l'icône et le style
            success_message = f"""
            <div class="d-flex align-items-center">
                <i class="fas fa-check-circle text-success me-3 fa-2x"></i>
                <div>
                    <h5 class="mb-1">{_('Mot de passe modifié!')}</h5>
                    <p class="mb-0">{_('Votre mot de passe a été modifié avec succès.')}</p>
                </div>
            </div>
            """
            
            messages.success(request, success_message)
            
            # Redirection adaptée selon le contexte
            if initial_change:
                return redirect('dashboard')  # Rediriger vers le tableau de bord après le premier changement
            return redirect('accounts:profile')
    else:
        form = PasswordChangeForm(request.user)
        
        # Message supplémentaire pour un mot de passe temporaire
        if initial_change or getattr(request.user, 'password_temporary', False):
            info_message = f"""
            <div class="d-flex align-items-center">
                <i class="fas fa-info-circle text-info me-3 fa-2x"></i>
                <div>
                    <h5 class="mb-1">{_('Action requise')}</h5>
                    <p class="mb-0">{_('Veuillez changer votre mot de passe temporaire.')}</p>
                </div>
            </div>
            """
            messages.info(request, info_message)
    
    return render(request, 'accounts/change_password.html', {
        'form': form,
        'initial_change': initial_change
    })