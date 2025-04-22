# apps/cotisations/signals.py
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.utils import timezone

from .models import Cotisation, Paiement, HistoriqueCotisation
from .utils import DecimalJSONEncoder
import json

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
    Signal pour journaliser les modifications de cotisations.
    """
    # Déterminer le type d'action
    action = 'creation' if created else 'modification'
    
    # Préparer les détails de l'action
    details = {
        'montant': instance.montant,
        'montant_restant': instance.montant_restant,
        'statut_paiement': instance.statut_paiement,
        'date_emission': instance.date_emission.isoformat() if instance.date_emission else None,
        'date_echeance': instance.date_echeance.isoformat() if instance.date_echeance else None,
    }
    
    # Convertir les détails en JSON avec l'encodeur personnalisé
    details_json = json.loads(json.dumps(details, cls=DecimalJSONEncoder))
    
    # Créer une entrée d'historique
    HistoriqueCotisation.objects.create(
        cotisation=instance,
        action=action,
        details=details_json,
        utilisateur=instance.cree_par if created else instance.modifie_par
    )

@receiver(post_delete, sender=Cotisation)
def post_delete_cotisation(sender, instance, **kwargs):
    """
    Signal pour journaliser la suppression d'une cotisation.
    """
    # Préparer les détails de l'action
    details = {
        'montant': instance.montant,
        'statut_paiement': instance.statut_paiement,
        'date_suppression': instance.deleted_at.isoformat() if instance.deleted_at else None,
    }
    
    # Convertir les détails en JSON avec l'encodeur personnalisé
    details_json = json.loads(json.dumps(details, cls=DecimalJSONEncoder))
    
    # Créer une entrée d'historique
    HistoriqueCotisation.objects.create(
        cotisation=instance,
        action='suppression',
        details=details_json,
        utilisateur=instance.modifie_par
    )

@receiver(post_save, sender=Paiement)
def post_save_paiement(sender, instance, created, **kwargs):
    """
    Signal pour journaliser les modifications de paiements.
    """
    # Déterminer le type d'action
    action = 'creation' if created else 'modification'
    
    # Mettre à jour la cotisation associée
    if created:
        instance.cotisation.recalculer_montant_restant()
        instance.cotisation.save(update_fields=['montant_restant', 'statut_paiement'])
    
    # Journaliser la modification de la cotisation
    details = {
        'montant': instance.montant,
        'date_paiement': instance.date_paiement.isoformat() if instance.date_paiement else None,
        'mode_paiement': instance.mode_paiement.libelle if instance.mode_paiement else None,
        'type_transaction': instance.type_transaction,
    }
    
    # Convertir les détails en JSON avec l'encodeur personnalisé
    details_json = json.loads(json.dumps(details, cls=DecimalJSONEncoder))
    
    # Créer une entrée d'historique pour la cotisation
    HistoriqueCotisation.objects.create(
        cotisation=instance.cotisation,
        action=f'paiement_{action}',
        details=details_json,
        utilisateur=instance.cree_par if created else instance.modifie_par
    )

@receiver(post_delete, sender=Paiement)
def post_delete_paiement(sender, instance, **kwargs):
    """
    Signal pour journaliser la suppression d'un paiement.
    """
    # Mettre à jour la cotisation associée si elle existe encore
    if instance.cotisation:
        instance.cotisation.recalculer_montant_restant()
        instance.cotisation.save(update_fields=['montant_restant', 'statut_paiement'])
        
        # Journaliser la suppression
        details = {
            'montant': instance.montant,
            'date_paiement': instance.date_paiement.isoformat() if instance.date_paiement else None,
            'type_transaction': instance.type_transaction,
        }
        
        # Convertir les détails en JSON avec l'encodeur personnalisé
        details_json = json.loads(json.dumps(details, cls=DecimalJSONEncoder))
        
        # Créer une entrée d'historique
        HistoriqueCotisation.objects.create(
            cotisation=instance.cotisation,
            action='paiement_suppression',
            details=details_json,
            utilisateur=instance.modifie_par
        )