# apps/accounts/signals.py
from django.db.models.signals import post_save, pre_save, pre_delete
from django.dispatch import receiver
from django.core.mail import send_mail
from django.utils import timezone
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.utils.translation import gettext_lazy as _
from .models import Role, UserLoginHistory, CustomUser, RolePermission
import uuid
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


@receiver(pre_save, sender=Role)
def ensure_single_default_role(sender, instance, **kwargs):
    """
    S'assure qu'il n'y a qu'un seul rôle par défaut.
    Si un rôle est défini comme défaut, les autres sont désactivés.
    """
    if instance.is_default:
        # Désactiver le flag par défaut pour tous les autres rôles
        Role.objects.filter(is_default=True).exclude(pk=instance.pk).update(is_default=False)


@receiver(post_save, sender=Role)
def assign_default_role_to_new_users(sender, instance, created, **kwargs):
    """
    Assigne le rôle par défaut aux utilisateurs qui n'ont pas de rôle.
    """
    if instance.is_default:
        # Assigner ce rôle comme défaut pour tous les utilisateurs sans rôle
        User.objects.filter(role__isnull=True).update(role=instance)


@receiver(post_save, sender=CustomUser)
def send_activation_email(sender, instance, created, **kwargs):
    """
    Envoie un email d'activation lorsqu'un nouvel utilisateur est créé.
    """
    if created and instance.cle_activation and not instance.is_active:
        try:
            activation_link = f"{settings.SITE_URL}/accounts/activate/{instance.cle_activation}/"
            send_mail(
                _('Activation de votre compte'),
                _(f'Bonjour {instance.get_full_name() or instance.username},\n\n'
                  f'Merci de vous être inscrit. Pour activer votre compte, veuillez cliquer sur le lien suivant :\n'
                  f'{activation_link}\n\n'
                  f'Ce lien est valable pendant 24 heures.\n\n'
                  f'Cordialement,\n'
                  f'L\'équipe {settings.SITE_NAME}'),
                settings.DEFAULT_FROM_EMAIL,
                [instance.email],
                fail_silently=False,
            )
            logger.info(f"Email d'activation envoyé à {instance.email}")
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi de l'email d'activation à {instance.email}: {str(e)}")


@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    """
    Enregistre les connexions réussies.
    """
    # Mise à jour de la dernière connexion
    user.derniere_connexion = timezone.now()
    user.save(update_fields=['derniere_connexion'])
    
    # Création d'une entrée dans l'historique
    UserLoginHistory.objects.create(
        user=user,
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', ''),
        session_key=request.session.session_key,
        status='success'
    )
    
    logger.info(f"Connexion réussie: {user.email} depuis {get_client_ip(request)}")


@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    """
    Enregistre les déconnexions.
    """
    if user:
        # Vérifier si session existe et a un session_key
        session_key = None
        if hasattr(request, 'session'):
            session_key = getattr(request.session, 'session_key', None)
        
        UserLoginHistory.objects.create(
            user=user,
            ip_address=get_client_ip(request) if hasattr(request, 'META') else None,
            user_agent=request.META.get('HTTP_USER_AGENT', '') if hasattr(request, 'META') else None,
            session_key=session_key,
            status='logout'
        )
        
        logger.info(f"Déconnexion: {user.email}")


@receiver(user_login_failed)
def log_user_login_failed(sender, credentials, request, **kwargs):
    """
    Enregistre les tentatives de connexion échouées.
    """
    email = credentials.get('username', '')
    user = None
    
    if email:
        user = User.objects.filter(email=email).first()
    
    if user:
        UserLoginHistory.objects.create(
            user=user,
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            status='failed'
        )
        
        logger.warning(f"Tentative de connexion échouée pour {email} depuis {get_client_ip(request)}")


@receiver(pre_delete, sender=RolePermission)
def log_permission_removal(sender, instance, **kwargs):
    """
    Enregistre la suppression d'une permission d'un rôle.
    """
    logger.info(f"Permission {instance.permission.code} supprimée du rôle {instance.role.nom}")


def get_client_ip(request):
    """
    Récupère l'adresse IP du client, en tenant compte des proxys.
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip