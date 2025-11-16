"""
Service centralisé pour la création d'utilisateurs et de membres.

Ce module fournit une interface unique pour créer des comptes utilisateur,
qu'ils soient des utilisateurs techniques (staff, services) ou des membres
de l'association avec leur profil complet.

Usage:
    # Créer un utilisateur technique
    from apps.accounts.services import UserCreationService
    user, password = UserCreationService.creer_utilisateur_technique(
        username='monitoring',
        email='monitoring@example.com',
        is_staff=True
    )

    # Créer un membre avec son compte
    membre, user, password = UserCreationService.creer_membre_avec_compte(
        nom='Dupont',
        prenom='Jean',
        email='jean.dupont@example.com',
        envoyer_email=True
    )
"""

from django.db import transaction
from django.utils.crypto import get_random_string
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


class UserCreationService:
    """
    Service centralisé pour la création d'utilisateurs.

    Gère la création d'utilisateurs techniques ET de membres avec validation,
    transactions atomiques, et logging.
    """

    @staticmethod
    @transaction.atomic
    def creer_utilisateur_technique(
        username,
        email,
        password=None,
        first_name='',
        last_name='',
        telephone='',
        is_staff=False,
        is_superuser=False,
        **kwargs
    ):
        """
        Crée un utilisateur technique (sans profil membre).

        Un utilisateur technique est un compte pour le staff, les services,
        ou les administrateurs qui n'ont pas besoin d'un profil membre complet.

        Args:
            username (str): Nom d'utilisateur unique
            email (str): Adresse email unique
            password (str, optional): Mot de passe. Si None, un mot de passe
                aléatoire de 12 caractères sera généré.
            first_name (str, optional): Prénom
            last_name (str, optional): Nom
            telephone (str, optional): Numéro de téléphone
            is_staff (bool, optional): L'utilisateur peut accéder à l'admin. Défaut: False
            is_superuser (bool, optional): L'utilisateur a tous les droits. Défaut: False
            **kwargs: Arguments supplémentaires passés à create_user()

        Returns:
            tuple: (user, password) où:
                - user: Instance de CustomUser créée
                - password: Le mot de passe en clair (à communiquer à l'utilisateur)

        Raises:
            ValidationError: Si le username ou l'email existe déjà

        Example:
            >>> user, pwd = UserCreationService.creer_utilisateur_technique(
            ...     username='admin.tech',
            ...     email='admin@example.com',
            ...     is_staff=True
            ... )
            >>> print(f"User: {user.username}, Password: {pwd}")
            User: admin.tech, Password: xYz123AbC456
        """
        # Validation de l'unicité
        if User.objects.filter(username=username).exists():
            raise ValidationError({
                'username': _("Ce nom d'utilisateur existe déjà.")
            })

        if User.objects.filter(email=email).exists():
            raise ValidationError({
                'email': _("Cette adresse email est déjà utilisée.")
            })

        # Générer mot de passe si nécessaire
        if not password:
            password = get_random_string(length=12)
            password_temporary = True
        else:
            password_temporary = kwargs.pop('password_temporary', False)

        # Créer l'utilisateur
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            is_staff=is_staff,
            is_superuser=is_superuser,
            password_temporary=password_temporary,
            **kwargs
        )

        # Ajouter le téléphone si fourni
        if telephone:
            user.telephone = telephone
            user.save(update_fields=['telephone'])

        logger.info(
            f"Utilisateur technique créé: {username} ({email}), "
            f"staff={is_staff}, superuser={is_superuser}"
        )

        return user, password

    @staticmethod
    @transaction.atomic
    def creer_membre_avec_compte(
        # Données membre (required)
        nom,
        prenom,
        email,
        # Données membre (optional)
        telephone='',
        adresse='',
        code_postal='',
        ville='',
        pays='France',
        date_adhesion=None,
        date_naissance=None,
        langue='fr',
        statut=None,
        types_membre=None,
        accepte_mail=True,
        accepte_sms=False,
        commentaires='',
        photo=None,
        # Données compte utilisateur
        username=None,
        password=None,
        envoyer_email=False,
        request=None,
        **kwargs
    ):
        """
        Crée un membre ET son compte utilisateur associé.

        Cette méthode crée de manière atomique un membre de l'association
        avec son compte utilisateur. Si une erreur se produit, toute la
        transaction est annulée (rollback).

        Args:
            nom (str): Nom du membre (requis)
            prenom (str): Prénom du membre (requis)
            email (str): Email unique (requis)
            telephone (str, optional): Téléphone
            adresse (str, optional): Adresse postale
            code_postal (str, optional): Code postal
            ville (str, optional): Ville
            pays (str, optional): Pays. Défaut: 'France'
            date_adhesion (date, optional): Date d'adhésion. Défaut: aujourd'hui
            date_naissance (date, optional): Date de naissance
            langue (str, optional): Langue préférée. Défaut: 'fr'
            statut (Statut, optional): Statut du membre
            types_membre (list, optional): Liste des TypeMembre à attribuer
            accepte_mail (bool, optional): Accepte les emails. Défaut: True
            accepte_sms (bool, optional): Accepte les SMS. Défaut: False
            commentaires (str, optional): Commentaires
            photo (File, optional): Photo du membre
            username (str, optional): Username. Si None, généré automatiquement
                depuis prenom.nom
            password (str, optional): Mot de passe. Si None, généré automatiquement
            envoyer_email (bool, optional): Envoyer email de bienvenue. Défaut: False
            request (HttpRequest, optional): Requête HTTP pour construire les URLs
            **kwargs: Arguments supplémentaires passés à Membre.objects.create()

        Returns:
            tuple: (membre, user, password) où:
                - membre: Instance de Membre créée
                - user: Instance de CustomUser créée
                - password: Le mot de passe en clair

        Raises:
            ValidationError: Si l'email existe déjà ou si les données sont invalides

        Example:
            >>> membre, user, pwd = UserCreationService.creer_membre_avec_compte(
            ...     nom='Dupont',
            ...     prenom='Jean',
            ...     email='jean.dupont@example.com',
            ...     telephone='0612345678',
            ...     envoyer_email=True,
            ...     request=request
            ... )
            >>> print(f"Membre: {membre.nom_complet}, User: {user.username}")
            Membre: Jean Dupont, User: jean.dupont
        """
        from django.utils import timezone
        from apps.membres.models import Membre

        # Validation de l'unicité de l'email
        if User.objects.filter(email=email).exists():
            raise ValidationError({
                'email': _("Un utilisateur avec cet email existe déjà.")
            })

        if Membre.objects.filter(email=email).exists():
            raise ValidationError({
                'email': _("Un membre avec cet email existe déjà.")
            })

        # Générer username si nécessaire
        if not username:
            # Nettoyer les caractères spéciaux
            username_base = f"{prenom.lower()}.{nom.lower()}"
            username = username_base.replace(' ', '_').replace("'", '').replace('-', '_')

            # Garantir l'unicité
            base_username = username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1

        # Générer password si nécessaire
        if not password:
            password = get_random_string(length=12)
            password_temporary = True
        else:
            password_temporary = False

        # Créer l'utilisateur
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=prenom,
            last_name=nom,
            password_temporary=password_temporary,
        )

        # Ajouter le téléphone
        if telephone:
            user.telephone = telephone
            user.save(update_fields=['telephone'])

        # Créer le membre
        membre = Membre.objects.create(
            utilisateur=user,
            nom=nom,
            prenom=prenom,
            email=email,
            telephone=telephone,
            adresse=adresse,
            code_postal=code_postal,
            ville=ville,
            pays=pays,
            date_adhesion=date_adhesion or timezone.now().date(),
            date_naissance=date_naissance,
            langue=langue,
            statut=statut,
            accepte_mail=accepte_mail,
            accepte_sms=accepte_sms,
            commentaires=commentaires,
            photo=photo,
            **kwargs
        )

        # Ajouter les types de membre
        if types_membre:
            for type_membre in types_membre:
                membre.ajouter_type(type_membre)

        # Envoyer email de bienvenue si demandé
        if envoyer_email:
            UserCreationService._envoyer_email_bienvenue(
                membre, user, username, password, request
            )

        logger.info(
            f"Membre créé avec compte: {prenom} {nom} ({email}), "
            f"username: {username}, "
            f"types: {[str(t) for t in types_membre] if types_membre else []}"
        )

        return membre, user, password

    @staticmethod
    def _envoyer_email_bienvenue(membre, user, username, password, request=None):
        """
        Envoie un email de bienvenue avec les identifiants de connexion.

        Méthode privée utilisée par creer_membre_avec_compte() pour envoyer
        un email contenant les informations de connexion au nouveau membre.

        Args:
            membre (Membre): Instance du membre
            user (CustomUser): Instance de l'utilisateur
            username (str): Nom d'utilisateur
            password (str): Mot de passe en clair
            request (HttpRequest, optional): Requête HTTP pour construire l'URL de connexion

        Note:
            Cette méthode ne lève pas d'exception en cas d'erreur d'envoi pour
            ne pas bloquer la création du compte. Les erreurs sont loggées.
        """
        try:
            from django.core.mail import EmailMultiAlternatives
            from django.template.loader import render_to_string
            from django.urls import reverse
            from django.conf import settings

            # URL de connexion
            if request:
                login_url = request.build_absolute_uri(reverse('accounts:login'))
            else:
                site_url = getattr(settings, 'SITE_URL', 'http://localhost:8000')
                login_url = f"{site_url}{reverse('accounts:login')}"

            # Contexte pour le template
            context = {
                'membre': membre,
                'user': user,
                'username': username,
                'password': password,
                'login_url': login_url,
            }

            # Rendre les templates
            html_message = render_to_string('emails/nouveau_compte.html', context)
            text_message = render_to_string('emails/nouveau_compte.txt', context)

            # Créer et envoyer l'email
            email = EmailMultiAlternatives(
                subject=_("Bienvenue - Vos identifiants de connexion"),
                body=text_message,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@kandiane.local'),
                to=[membre.email]
            )
            email.attach_alternative(html_message, "text/html")
            email.send()

            logger.info(f"Email de bienvenue envoyé à {membre.email}")

        except Exception as e:
            logger.error(
                f"Erreur lors de l'envoi de l'email de bienvenue à {membre.email}: {str(e)}",
                exc_info=True
            )
            # Ne pas lever d'exception pour ne pas bloquer la création du compte
