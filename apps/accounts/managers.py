# apps/accounts/managers.py
from django.db import models
from django.contrib.auth.models import BaseUserManager
from django.utils.translation import gettext_lazy as _
from django.utils import timezone


class CustomUserQuerySet(models.QuerySet):
    def active(self):
        """Retourne uniquement les utilisateurs actifs."""
        return self.filter(is_active=True, deleted_at__isnull=True)
    
    def inactive(self):
        """Retourne uniquement les utilisateurs inactifs."""
        return self.filter(is_active=False, deleted_at__isnull=True)
    
    def deleted(self):
        """Retourne uniquement les utilisateurs supprimés."""
        return self.filter(deleted_at__isnull=False)
    
    def staff(self):
        """Retourne uniquement les utilisateurs du staff."""
        return self.filter(is_staff=True, is_active=True, deleted_at__isnull=True)
    
    def with_role(self, role_name):
        """Retourne les utilisateurs ayant un rôle spécifique."""
        return self.filter(
            role__nom=role_name, 
            is_active=True, 
            deleted_at__isnull=True
        )
    
    def recently_active(self, days=30):
        """Retourne les utilisateurs actifs récemment."""
        threshold = timezone.now() - timezone.timedelta(days=days)
        return self.filter(
            derniere_connexion__gte=threshold,
            is_active=True,
            deleted_at__isnull=True
        )


class ExtendedUserManager(BaseUserManager):
    """
    Gestionnaire personnalisé pour le modèle utilisateur CustomUser.
    Étend le gestionnaire de base en ajoutant des méthodes utiles.
    """
    def get_queryset(self):
        return CustomUserQuerySet(self.model, using=self._db)
    
    def create_user(self, email, password=None, **extra_fields):
        """
        Crée et sauvegarde un utilisateur avec l'email et le mot de passe donnés.
        """
        if not email:
            raise ValueError(_("L'adresse email est obligatoire"))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        """
        Crée et sauvegarde un superutilisateur avec l'email et le mot de passe donnés.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError(_("Le superutilisateur doit avoir is_staff=True"))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_("Le superutilisateur doit avoir is_superuser=True"))
        
        return self.create_user(email, password, **extra_fields)
    
    # Méthodes héritées du QuerySet
    def active(self):
        return self.get_queryset().active()
    
    def inactive(self):
        return self.get_queryset().inactive()
    
    def deleted(self):
        return self.get_queryset().deleted()
    
    def staff(self):
        return self.get_queryset().staff()
    
    def with_role(self, role_name):
        return self.get_queryset().with_role(role_name)
    
    def recently_active(self, days=30):
        return self.get_queryset().recently_active(days)
    
    def get_by_email(self, email):
        """
        Obtenir un utilisateur par son email.
        """
        return self.get_queryset().filter(email=email).first()
    
    def get_by_activation_key(self, key):
        """
        Obtenir un utilisateur par sa clé d'activation.
        """
        return self.get_queryset().filter(cle_activation=key, is_active=False).first()


class RoleQuerySet(models.QuerySet):
    def default(self):
        """Retourne le rôle par défaut."""
        return self.filter(is_default=True).first()
    
    def active(self):
        """Retourne uniquement les rôles actifs."""
        return self.filter(deleted_at__isnull=True)


class RoleManager(models.Manager):
    def get_queryset(self):
        return RoleQuerySet(self.model, using=self._db)
    
    def default(self):
        """Retourne le rôle par défaut."""
        return self.get_queryset().default()
    
    def active(self):
        """Retourne uniquement les rôles actifs."""
        return self.get_queryset().active()