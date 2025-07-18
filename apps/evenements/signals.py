# apps/evenements/signals.py - CRÉER CE FICHIER
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from .models import InscriptionEvenement, Evenement, ValidationEvenement
from .services.cotisation_service import EvenementCotisationService
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=InscriptionEvenement)
def gerer_cotisation_inscription(sender, instance, created, **kwargs):
    """Gère la création/mise à jour de cotisation lors de l'inscription"""
    try:
        # Créer une cotisation si l'inscription est confirmée et l'événement payant
        if instance.statut == 'confirmee' and instance.evenement.est_payant:
            cotisation, message = EvenementCotisationService.creer_cotisation_inscription(
                instance, getattr(instance, '_user', None)
            )
            
            if cotisation:
                # Synchroniser le paiement si montant déjà payé
                if instance.montant_paye > 0:
                    EvenementCotisationService.synchroniser_paiement(instance)
                    
                logger.info(f"Cotisation gérée pour inscription {instance.id}: {message}")
    
    except Exception as e:
        logger.error(f"Erreur signal cotisation inscription {instance.id}: {str(e)}")

@receiver(post_save, sender=Evenement)
def gerer_changement_statut_evenement(sender, instance, created, **kwargs):
    """Gère les changements de statut d'événement (notamment annulation)"""
    try:
        if not created and instance.statut == 'annule':
            # Gérer les remboursements automatiques
            nb_remboursements, erreurs = EvenementCotisationService.gerer_remboursement_annulation(
                instance, f"Annulation de l'événement {instance.titre}"
            )
            
            if nb_remboursements > 0:
                logger.info(f"Remboursements automatiques effectués: {nb_remboursements} pour événement {instance.id}")
            
            if erreurs:
                logger.warning(f"Erreurs remboursements événement {instance.id}: {erreurs}")
    
    except Exception as e:
        logger.error(f"Erreur signal changement statut événement {instance.id}: {str(e)}")

@receiver(post_save, sender=Evenement)
def creer_validation_evenement(sender, instance, created, **kwargs):
    """
    SIGNAL CORRIGÉ : Crée automatiquement une ValidationEvenement 
    si le type d'événement nécessite validation
    """
    try:
        # Vérifier si l'événement nécessite validation
        if (instance.type_evenement and 
            instance.type_evenement.necessite_validation and 
            not ValidationEvenement.objects.filter(evenement=instance).exists()):
            
            # CORRECTION : Utiliser les bons noms de champs
            validation = ValidationEvenement.objects.create(
                evenement=instance,
                statut_validation='en_attente',
                # CORRECTION : Utiliser commentaire_validation au lieu de commentaire_organisateur
                commentaire_validation=f"Demande de validation automatique pour {instance.titre}"
            )
            
            # Mettre à jour le statut de l'événement
            if instance.statut == 'brouillon':
                instance.statut = 'en_attente_validation'
                instance.save(update_fields=['statut'])
            
            logger.info(f"ValidationEvenement créée pour l'événement {instance.id}: {instance.titre}")
            
    except Exception as e:
        logger.error(f"Erreur création ValidationEvenement pour {instance.id}: {e}")

@receiver(post_save, sender=Evenement)
def publier_evenement_sans_validation(sender, instance, created, **kwargs):
    """
    SIGNAL : Publie automatiquement les événements ne nécessitant pas de validation
    """
    try:
        # Si l'événement ne nécessite pas de validation et est en brouillon
        if (instance.type_evenement and 
            not instance.type_evenement.necessite_validation and 
            instance.statut == 'brouillon' and
            created):  # Seulement à la création
            
            instance.statut = 'publie'
            instance.save(update_fields=['statut'])
            
            logger.info(f"Événement {instance.id} publié automatiquement (pas de validation requise)")
            
    except Exception as e:
        logger.error(f"Erreur publication automatique événement {instance.id}: {e}")