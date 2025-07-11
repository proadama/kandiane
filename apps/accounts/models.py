# apps/accounts/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from apps.core.models import BaseModel, Statut
from django.db.models.signals import post_save
from django.dispatch import receiver
import uuid


class Role(BaseModel):
    """
    Modèle pour gérer les rôles des utilisateurs.
    Chaque rôle peut avoir plusieurs permissions.
    """
    nom = models.CharField(max_length=50, unique=True, verbose_name=_("Nom"))
    description = models.TextField(null=True, blank=True, verbose_name=_("Description"))
    is_default = models.BooleanField(default=False, verbose_name=_("Rôle par défaut"))
    
    class Meta:
        verbose_name = _("Rôle")
        verbose_name_plural = _("Rôles")
        
    def __str__(self):
        return self.nom


class Permission(BaseModel):
    """
    Modèle pour définir les permissions spécifiques à l'application.
    """
    code = models.CharField(max_length=100, unique=True, verbose_name=_("Code"))
    nom = models.CharField(max_length=100, verbose_name=_("Nom"))
    description = models.TextField(null=True, blank=True, verbose_name=_("Description"))
    
    class Meta:
        verbose_name = _("Permission")
        verbose_name_plural = _("Permissions")
        ordering = ['code']
        
    def __str__(self):
        return f"{self.nom} ({self.code})"


class RolePermission(models.Model):
    """
    Table d'association entre les rôles et les permissions.
    """
    role = models.ForeignKey(
        Role, 
        on_delete=models.CASCADE, 
        related_name='permissions',
        verbose_name=_("Rôle")
    )
    permission = models.ForeignKey(
        Permission, 
        on_delete=models.CASCADE,
        related_name='roles',
        verbose_name=_("Permission")
    )
    
    class Meta:
        verbose_name = _("Permission de rôle")
        verbose_name_plural = _("Permissions de rôle")
        unique_together = ('role', 'permission')
        
    def __str__(self):
        return f"{self.role} - {self.permission}"


class CustomUserManager(BaseUserManager):
    """
    Gestionnaire personnalisé pour le modèle utilisateur CustomUser.
    """
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError(_("L'adresse email est obligatoire"))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError(_("Le superutilisateur doit avoir is_staff=True"))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_("Le superutilisateur doit avoir is_superuser=True"))
        
        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractUser):
    """
    Modèle utilisateur personnalisé avec email comme identifiant.
    """
    
    # Champ pour marquer un mot de passe comme temporaire
    password_temporary = models.BooleanField(
        default=False,
        verbose_name=_("Mot de passe temporaire"),
        help_text=_("Indique si le mot de passe est temporaire et doit être changé")
    )
    email = models.EmailField(_("Adresse email"), unique=True)
    role = models.ForeignKey(
        Role, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='users',
        verbose_name=_("Rôle")
    )
    cle_activation = models.CharField(
        max_length=100, 
        null=True, 
        blank=True,
        verbose_name=_("Clé d'activation")
    )
    derniere_connexion = models.DateTimeField(
        null=True, 
        blank=True,
        verbose_name=_("Dernière connexion")
    )
    date_desactivation = models.DateTimeField(
        null=True, 
        blank=True,
        verbose_name=_("Date de désactivation")
    )
    deleted_at = models.DateTimeField(
        null=True, 
        blank=True,
        verbose_name=_("Date de suppression")
    )
    avatar = models.ImageField(
        upload_to='avatars/', 
        null=True, 
        blank=True,
        verbose_name=_("Avatar")
    )
    telephone = models.CharField(
        max_length=20, 
        null=True, 
        blank=True,
        verbose_name=_("Téléphone")
    )
    statut = models.ForeignKey(
        Statut,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Statut")
    )
    accepte_communications = models.BooleanField(
        default=True,
        verbose_name=_("Accepte les communications")
    )
    
    # Modification des champs par défaut
    username = models.CharField(
        _("Nom d'utilisateur"),
        max_length=150,
        unique=True,
        help_text=_("150 caractères maximum. Lettres, chiffres et @/./+/-/_ uniquement."),
        validators=[AbstractUser.username_validator],
        error_messages={
            "unique": _("Un utilisateur avec ce nom d'utilisateur existe déjà."),
        },
    )
    first_name = models.CharField(_("Prénom"), max_length=150, blank=True)
    last_name = models.CharField(_("Nom"), max_length=150, blank=True)
    
    objects = CustomUserManager()
    
    USERNAME_FIELD = 'email'  # L'email est utilisé comme identifiant
    REQUIRED_FIELDS = ['username']  # Le nom d'utilisateur reste obligatoire

    # Ajoutez ces champs à la classe CustomUser:
    is_email_verified = models.BooleanField(
        default=False,
        verbose_name=_("Email vérifié")
    )
    email_verification_token = models.CharField(
        max_length=100, 
        null=True, 
        blank=True,
        verbose_name=_("Token de vérification d'email")
    )
    email_verification_sent_at = models.DateTimeField(
        null=True, 
        blank=True,
        verbose_name=_("Date d'envoi de vérification")
    )
    
    class Meta:
        verbose_name = _("Utilisateur")
        verbose_name_plural = _("Utilisateurs")
        
    def __str__(self):
        return self.email
    
    def get_full_name(self):
        """
        Retourne le prénom et le nom complet.
        """
        full_name = f"{self.first_name} {self.last_name}"
        return full_name.strip()
    
    def has_permission(self, permission_code):
        """
        Vérifie si l'utilisateur a une permission spécifique.
        """
        if self.is_superuser:
            return True
        if not self.role:
            return False
        try:
            permission = Permission.objects.get(code=permission_code)
            return RolePermission.objects.filter(
                role=self.role, 
                permission=permission
            ).exists()
        except Permission.DoesNotExist:
            return False
    
    def generate_activation_key(self):
        """
        Génère une clé d'activation unique pour l'utilisateur.
        """
        self.cle_activation = uuid.uuid4().hex
        if self.pk:  # Seulement si l'objet a déjà une clé primaire
            self.save(update_fields=['cle_activation'])
        return self.cle_activation
    
    # Puis ajoutez ces méthodes à la classe CustomUser:
    def generate_email_verification_token(self):
        """
        Génère un token unique pour la vérification d'email
        """
        import uuid
        token = uuid.uuid4().hex
        self.email_verification_token = token
        self.email_verification_sent_at = timezone.now()
        self.save(update_fields=['email_verification_token', 'email_verification_sent_at'])
        return token
    
    def verify_email(self, token):
        """
        Vérifie si le token correspond et active l'email
        """
        if not self.is_email_verified and self.email_verification_token == token:
            # Vérifier que le token n'a pas expiré (24h)
            from django.conf import settings
            expiry_duration = getattr(settings, 'ACCOUNT_EMAIL_VERIFICATION_EXPIRY', 86400)  # 24h par défaut
            
            if self.email_verification_sent_at and (
                timezone.now() - self.email_verification_sent_at
            ).total_seconds() < expiry_duration:
                self.is_email_verified = True
                self.email_verification_token = None
                self.save(update_fields=['is_email_verified', 'email_verification_token'])
                return True
        return False


class UserProfile(BaseModel):
    """
    Profil supplémentaire pour les utilisateurs.
    """
    user = models.OneToOneField(
        CustomUser, 
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name=_("Utilisateur")
    )
    bio = models.TextField(
        blank=True, 
        null=True,
        verbose_name=_("Biographie")
    )
    date_naissance = models.DateField(
        blank=True, 
        null=True,
        verbose_name=_("Date de naissance")
    )
    adresse = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name=_("Adresse")
    )
    ville = models.CharField(
        max_length=100, 
        blank=True, 
        null=True,
        verbose_name=_("Ville")
    )
    code_postal = models.CharField(
        max_length=20, 
        blank=True, 
        null=True,
        verbose_name=_("Code postal")
    )
    pays = models.CharField(
        max_length=50, 
        blank=True, 
        null=True,
        verbose_name=_("Pays")
    )
    preferences = models.JSONField(
        default=dict, 
        blank=True,
        verbose_name=_("Préférences")
    )
    
     # AJOUTER ces constantes de classe
    NOTIFICATION_TYPES = {
        'evenement_invitation': 'Invitations aux événements',
        'evenement_rappel_confirmation': 'Rappels de confirmation',
        'evenement_modification': 'Modifications d\'événements',
        'evenement_annulation': 'Annulations d\'événements',
        'evenement_promotion_liste': 'Promotions depuis liste d\'attente',
        'evenement_nouveau_type': 'Nouveaux types d\'événements'
    }
    
    # AJOUTER ces méthodes après la méthode __str__
    def get_notification_preference(self, type_notification):
        """Récupère une préférence de notification"""
        notifications = self.preferences.get('notifications', {})
        return notifications.get(type_notification, True)  # Activé par défaut
    
    def set_notification_preference(self, type_notification, enabled):
        """Définit une préférence de notification"""
        if 'notifications' not in self.preferences:
            self.preferences['notifications'] = {}
        self.preferences['notifications'][type_notification] = enabled
        self.save(update_fields=['preferences'])
    
    def get_all_notification_preferences(self):
        """Retourne toutes les préférences de notification"""
        notifications = self.preferences.get('notifications', {})
        return {
            notif_type: notifications.get(notif_type, True)
            for notif_type in self.NOTIFICATION_TYPES.keys()
        }
    
    class Meta:
        verbose_name = _("Profil utilisateur")
        verbose_name_plural = _("Profils utilisateurs")
        
    def __str__(self):
        return f"Profil de {self.user.email}"


@receiver(post_save, sender=CustomUser)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Signal pour créer automatiquement un profil quand un utilisateur est créé.
    """
    if created:
        UserProfile.objects.create(user=instance)


class UserLoginHistory(BaseModel):
    """
    Historique des connexions des utilisateurs.
    """
    user = models.ForeignKey(
        CustomUser, 
        on_delete=models.CASCADE,
        related_name='login_history',
        verbose_name=_("Utilisateur")
    )
    ip_address = models.GenericIPAddressField(
        null=True, 
        blank=True,
        verbose_name=_("Adresse IP")
    )
    user_agent = models.TextField(
        null=True, 
        blank=True,
        verbose_name=_("User Agent")
    )
    session_key = models.CharField(
        max_length=40, 
        null=True, 
        blank=True,
        verbose_name=_("Clé de session")
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ('success', _('Succès')),
            ('failed', _('Échec')),
            ('logout', _('Déconnexion')),
        ],
        default='success',
        verbose_name=_("Statut")
    )
    
    class Meta:
        verbose_name = _("Historique de connexion")
        verbose_name_plural = _("Historique des connexions")
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.user.email} - {self.created_at}"
    
class Log(BaseModel):
    """Modèle pour la journalisation des actions"""
    utilisateur = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Utilisateur"
    )
    action = models.CharField(
        max_length=255,
        verbose_name="Action"
    )
    details = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Détails"
    )
    adresse_ip = models.GenericIPAddressField(
        blank=True,
        null=True,
        verbose_name="Adresse IP"
    )
    
    class Meta:
        db_table = 'logs'
        verbose_name = "Log"
        verbose_name_plural = "Logs"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.action} - {self.created_at}"