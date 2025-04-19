# apps/cotisations/signals.py
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.utils import timezone

from .models import Cotisation, Paiement, HistoriqueCotisation


@receiver(pre_save, sender=Cotisation)
def pre_save_cotisation(sender, instance, **kwargs):
    """
    Signal déclenché avant la sauvegarde d'une cotisation.
    Permet d'enregistrer l'état avant modification.
    """
    # Ne s'applique qu'aux mises à jour, pas aux créations
    if instance.pk:
        try:
            # Stocker l'ancienne instance pour comparaison
            instance._old_instance = Cotisation.objects.get(pk=instance.pk)
        except Cotisation.DoesNotExist:
            pass


@receiver(post_save, sender=Cotisation)
def post_save_cotisation(sender, instance, created, **kwargs):
    """
    Signal déclenché après la sauvegarde d'une cotisation.
    Permet de journaliser la création ou modification.
    """
    # Création d'une nouvelle cotisation
    if created:
        HistoriqueCotisation.objects.create(
            cotisation=instance,
            action='creation',
            details={
                'montant': str(instance.montant),
                'date_emission': str(instance.date_emission),
                'date_echeance': str(instance.date_echeance),
                'statut_paiement': instance.statut_paiement
            },
            utilisateur=instance.cree_par
        )
    # Modification d'une cotisation existante
    elif hasattr(instance, '_old_instance'):
        old = instance._old_instance
        changes = {}
        
        # Détecter les changements
        for field in ['montant', 'date_echeance', 'statut_paiement', 'montant_restant']:
            old_value = getattr(old, field)
            new_value = getattr(instance, field)
            
            # Convertir en string pour compatibilité JSON
            if isinstance(old_value, (int, float)):
                old_value = str(old_value)
            if isinstance(new_value, (int, float)):
                new_value = str(new_value)
                
            if old_value != new_value:
                changes[field] = {
                    'before': old_value,
                    'after': new_value
                }
        
        # Créer l'historique si des changements ont été détectés
        if changes:
            HistoriqueCotisation.objects.create(
                cotisation=instance,
                action='modification',
                details=changes,
                utilisateur=instance.modifie_par
            )


@receiver(post_delete, sender=Cotisation)
def post_delete_cotisation(sender, instance, **kwargs):
    """
    Signal déclenché après la suppression d'une cotisation.
    Permet de journaliser la suppression.
    """
    HistoriqueCotisation.objects.create(
        cotisation=instance,
        action='suppression',
        details={
            'montant': str(instance.montant),
            'date_emission': str(instance.date_emission),
            'date_echeance': str(instance.date_echeance),
            'statut_paiement': instance.statut_paiement
        },
        utilisateur=instance.modifie_par,
        date_action=timezone.now()
    )


@receiver(post_save, sender=Paiement)
def post_save_paiement(sender, instance, created, **kwargs):
    """
    Signal déclenché après la sauvegarde d'un paiement.
    Permet de mettre à jour la cotisation associée et de journaliser l'action.
    """
    # Journaliser l'action dans l'historique de la cotisation
    if created:
        HistoriqueCotisation.objects.create(
            cotisation=instance.cotisation,
            action='paiement_ajoute',
            details={
                'montant_paiement': str(instance.montant),
                'date_paiement': str(instance.date_paiement),
                'mode_paiement': str(instance.mode_paiement),
                'type_transaction': instance.type_transaction
            },
            utilisateur=instance.cree_par
        )


@receiver(post_delete, sender=Paiement)
def post_delete_paiement(sender, instance, **kwargs):
    """
    Signal déclenché après la suppression d'un paiement.
    Permet de mettre à jour la cotisation associée et de journaliser l'action.
    """
    HistoriqueCotisation.objects.create(
        cotisation=instance.cotisation,
        action='paiement_supprime',
        details={
            'montant_paiement': str(instance.montant),
            'date_paiement': str(instance.date_paiement),
            'mode_paiement': str(instance.mode_paiement) if instance.mode_paiement else None,
            'type_transaction': instance.type_transaction
        },
        utilisateur=instance.modifie_par
    )