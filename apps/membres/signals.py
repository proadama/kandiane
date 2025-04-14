import logging
from django.db.models.signals import pre_save, post_save, pre_delete, post_delete
from django.dispatch import receiver
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from django.utils.crypto import get_random_string
from apps.membres.models import Membre
from apps.accounts.models import CustomUser
from apps.membres.models import Membre, TypeMembre, MembreTypeMembre, HistoriqueMembre

logger = logging.getLogger(__name__)
User = get_user_model()


@receiver(pre_save, sender=Membre)
def validate_membre_data(sender, instance, **kwargs):
    """
    Valider les données du membre avant l'enregistrement
    """
    # Vérifier que la date de naissance n'est pas dans le futur
    if instance.date_naissance:
        # Convertir en date si c'est un datetime
        date_naissance = instance.date_naissance
        if hasattr(date_naissance, 'date'):
            date_naissance = date_naissance.date()
        
        if date_naissance > timezone.now().date():
            raise ValidationError({
                'date_naissance': _("La date de naissance ne peut pas être dans le futur")
            })
    
    # Vérifier que la date d'adhésion n'est pas dans le futur
    if instance.date_adhesion:
        # Convertir en date si c'est un datetime
        date_adhesion = instance.date_adhesion
        if hasattr(date_adhesion, 'date'):
            date_adhesion = date_adhesion.date()
            
        if date_adhesion > timezone.now().date():
            raise ValidationError({
                'date_adhesion': _("La date d'adhésion ne peut pas être dans le futur")
            })
    
    # Le reste du code reste inchangé
    if instance.nom:
        instance.nom = instance.nom.strip().upper()
    if instance.prenom:
        instance.prenom = instance.prenom.strip().title()
    
    if instance.email:
        instance.email = instance.email.strip().lower()


@receiver(post_save, sender=Membre)
def create_membre_historique(sender, instance, created, **kwargs):
    """
    Créer une entrée dans l'historique lors de la création d'un membre
    """
    if created:
        try:
            HistoriqueMembre.objects.create(
                membre=instance,
                action='creation',
                description=_("Création du membre"),
                donnees_apres={
                    'id': instance.id,
                    'nom': instance.nom,
                    'prenom': instance.prenom,
                    'email': instance.email,
                    'date_adhesion': str(instance.date_adhesion)
                }
            )
            logger.info(f"Historique créé pour nouveau membre: {instance}")
        except Exception as e:
            logger.error(f"Erreur lors de la création de l'historique pour {instance}: {e}")


@receiver(pre_save, sender=MembreTypeMembre)
def validate_membre_type_membre(sender, instance, **kwargs):
    """
    Valider les données de l'association membre-type avant l'enregistrement
    """
    # Vérifier que la date de fin est postérieure à la date de début
    if instance.date_fin and instance.date_debut:
        # Convertir en date si nécessaire
        date_fin = instance.date_fin
        date_debut = instance.date_debut
        
        if hasattr(date_fin, 'date'):
            date_fin = date_fin.date()
        if hasattr(date_debut, 'date'):
            date_debut = date_debut.date()
            
        if date_fin < date_debut:
            raise ValidationError({
                'date_fin': _("La date de fin doit être postérieure à la date de début")
            })
    
    # Vérifier que la date de début n'est pas dans le futur
    if instance.date_debut:
        # Convertir en date si c'est un datetime
        date_debut = instance.date_debut
        if hasattr(date_debut, 'date'):
            date_debut = date_debut.date()
            
        if date_debut > timezone.now().date():
            raise ValidationError({
                'date_debut': _("La date de début ne peut pas être dans le futur")
            })


@receiver(post_save, sender=MembreTypeMembre)
def create_membre_type_historique(sender, instance, created, **kwargs):
    """
    Créer une entrée dans l'historique lors de la modification d'une association membre-type
    """
    try:
        # Déterminer l'action et la description
        if created:
            action = 'ajout_type'
            description = _(f"Ajout du type de membre: {instance.type_membre.libelle}")
        else:
            # Vérifier si la date de fin a été ajoutée (association terminée)
            if instance.date_fin:
                action = 'fin_type'
                description = _(f"Fin de l'association avec le type: {instance.type_membre.libelle}")
            else:
                action = 'modification_type'
                description = _(f"Modification de l'association avec le type: {instance.type_membre.libelle}")
        
        # Créer l'entrée d'historique
        HistoriqueMembre.objects.create(
            membre=instance.membre,
            utilisateur=instance.modifie_par,
            action=action,
            description=description,
            donnees_apres={
                'type_membre': instance.type_membre.libelle,
                'date_debut': str(instance.date_debut),
                'date_fin': str(instance.date_fin) if instance.date_fin else None,
                'commentaire': instance.commentaire
            }
        )
        logger.info(f"Historique créé pour association membre-type: {instance}")
    except Exception as e:
        logger.error(f"Erreur lors de la création de l'historique pour {instance}: {e}")


@receiver(pre_delete, sender=Membre)
def handle_membre_delete(sender, instance, **kwargs):
    """
    Gérer la suppression d'un membre (soft delete pour l'historique)
    """
    # Créer une entrée dans l'historique
    try:
        HistoriqueMembre.objects.create(
            membre=instance,
            action='suppression',
            description=_("Suppression du membre"),
            donnees_avant={
                'id': instance.id,
                'nom': instance.nom,
                'prenom': instance.prenom,
                'email': instance.email,
                'date_adhesion': str(instance.date_adhesion)
            }
        )
        logger.info(f"Historique créé pour suppression du membre: {instance}")
    except Exception as e:
        logger.error(f"Erreur lors de la création de l'historique pour la suppression de {instance}: {e}")


@receiver(post_delete, sender=User)
def handle_user_delete(sender, instance, **kwargs):
    """
    Gérer la suppression d'un utilisateur lié à un membre
    """
    try:
        # Vérifier si l'utilisateur est lié à un membre
        membre = Membre.objects.filter(utilisateur_id=instance.id).first()
        if membre:
            # Dissocier l'utilisateur supprimé du membre
            membre.utilisateur = None
            membre.save(update_fields=['utilisateur'])
            
            # Créer une entrée d'historique
            HistoriqueMembre.objects.create(
                membre=membre,
                action='dissociation_compte',
                description=_("Dissociation du compte utilisateur suite à sa suppression"),
                donnees_avant={
                    'utilisateur_id': instance.id,
                    'utilisateur_username': instance.username,
                }
            )
            logger.info(f"Compte utilisateur dissocié du membre: {membre}")
    except Exception as e:
        logger.error(f"Erreur lors de la dissociation du compte utilisateur: {e}")


@receiver(post_save, sender=User)
def handle_user_create(sender, instance, created, **kwargs):
    """
    Gérer la création d'un utilisateur et tenter de l'associer à un membre existant
    """
    if created and instance.email:
        try:
            # Rechercher un membre avec la même adresse email
            membre = Membre.objects.filter(
                email=instance.email,
                utilisateur__isnull=True
            ).first()
            
            # Si un membre correspondant est trouvé, associer l'utilisateur
            if membre:
                membre.utilisateur = instance
                membre.save(update_fields=['utilisateur'])
                
                # Créer une entrée d'historique
                HistoriqueMembre.objects.create(
                    membre=membre,
                    utilisateur=instance,
                    action='association_compte',
                    description=_("Association automatique d'un compte utilisateur"),
                    donnees_apres={
                        'utilisateur_id': instance.id,
                        'utilisateur_username': instance.username,
                    }
                )
                logger.info(f"Compte utilisateur {instance} associé automatiquement au membre {membre}")
        except Exception as e:
            logger.error(f"Erreur lors de l'association automatique du compte utilisateur: {e}")
"""
@receiver(post_save, sender=Membre)
def create_user_for_membre(sender, instance, created, **kwargs):
    Crée automatiquement un utilisateur pour un membre si nécessaire
    # Éviter les boucles infinies
    if hasattr(instance, '_creating_user'):
        return
        
    if not instance.utilisateur and instance.email:
        try:
            # Vérifier si un utilisateur avec cet email existe déjà
            user = User.objects.get(email=instance.email)
            # Lier l'utilisateur existant au membre
            instance._creating_user = True
            instance.utilisateur = user
            instance.save(update_fields=['utilisateur'])
            logger.info(f"Utilisateur existant associé au membre {instance.nom_complet}")
        except User.DoesNotExist:
            # Créer un nouvel utilisateur si c'est une création automatique
            username = f"{instance.prenom.lower()}.{instance.nom.lower()}"
            username = username.replace(' ', '_')
            base_username = username
            counter = 1
            
            # Éviter les doublons
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1
            
            # Créer l'utilisateur avec un mot de passe aléatoire
            from django.utils.crypto import get_random_string
            password = get_random_string(length=12)
            
            user = User.objects.create_user(
                username=username,
                email=instance.email,
                password=password,
                first_name=instance.prenom,
                last_name=instance.nom
            )
            
            # Lier à ce membre
            instance._creating_user = True
            instance.utilisateur = user
            instance.save(update_fields=['utilisateur'])
            
            # Enregistrer dans les logs pour que l'admin puisse récupérer les infos
            logger.info(f"Utilisateur créé automatiquement pour {instance.nom_complet}. "
                        f"Username: {username}, Password: {password}")
"""