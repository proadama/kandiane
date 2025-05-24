# apps/cotisations/signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from datetime import datetime
import json

from .models import Cotisation, Paiement, HistoriqueCotisation


def format_date(date_value):
    """Convertit une date en format ISO, quel que soit son type."""
    if date_value is None:
        return None
    if isinstance(date_value, str):
        try:
            # Essayer de parser la chaîne en date
            return datetime.fromisoformat(date_value).isoformat()
        except ValueError:
            # Si c'est une date au format YYYY-MM-DD
            try:
                return datetime.strptime(date_value, '%Y-%m-%d').isoformat()
            except ValueError:
                return date_value  # Retourner tel quel si impossible à parser
    else:
        # Si c'est déjà un objet date ou datetime
        return date_value.isoformat()


@receiver(post_save, sender=Cotisation)
def post_save_cotisation(sender, instance, created, **kwargs):
    """
    Signal exécuté après la sauvegarde d'une cotisation.
    Crée une entrée dans l'historique des cotisations.
    """
    # Préparer les détails à enregistrer dans l'historique
    details = {
        'reference': instance.reference,
        'montant': float(instance.montant) if instance.montant else None,
        'montant_restant': float(instance.montant_restant) if instance.montant_restant else None,
        'statut_paiement': instance.statut_paiement,
        'date_emission': format_date(instance.date_emission),
        'date_echeance': format_date(instance.date_echeance),
        'periode_debut': format_date(instance.periode_debut),
        'periode_fin': format_date(instance.periode_fin),
    }
    
    # Créer l'entrée d'historique
    HistoriqueCotisation.objects.create(
        cotisation=instance,
        action='creation' if created else 'modification',
        details=json.dumps(details),
        utilisateur=instance.cree_par if created else instance.modifie_par,
        date_action=timezone.now()
    )


@receiver(post_save, sender=Paiement)
def post_save_paiement(sender, instance, created, **kwargs):
    """
    Signal exécuté après la sauvegarde d'un paiement.
    Met à jour le montant restant et le statut de la cotisation associée.
    """
    # Mettre à jour la cotisation
    cotisation = instance.cotisation
    cotisation.recalculer_montant_restant()
    cotisation.save(update_fields=['montant_restant', 'statut_paiement'])
    
    # Enregistrer dans l'historique
    details = {
        'paiement_id': instance.id,
        'montant': float(instance.montant) if instance.montant else None,
        'date_paiement': format_date(instance.date_paiement),
        'mode_paiement': instance.mode_paiement.libelle if instance.mode_paiement else None,
        'type_transaction': instance.type_transaction,
        'nouveau_montant_restant': float(cotisation.montant_restant) if cotisation.montant_restant else None,
        'nouveau_statut_paiement': cotisation.statut_paiement,
    }
    
    HistoriqueCotisation.objects.create(
        cotisation=cotisation,
        action='paiement_ajoute' if created else 'paiement_modifie',
        details=json.dumps(details),
        utilisateur=instance.cree_par if created else instance.modifie_par,
        date_action=timezone.now()
    )


@receiver(post_delete, sender=Paiement)
def post_delete_paiement(sender, instance, **kwargs):
    """
    Signal exécuté après la suppression d'un paiement.
    Met à jour le montant restant et le statut de la cotisation associée.
    """
    # Vérifier si la cotisation existe encore
    try:
        cotisation = instance.cotisation
        cotisation.recalculer_montant_restant()
        cotisation.save(update_fields=['montant_restant', 'statut_paiement'])
        
        # Enregistrer dans l'historique
        details = {
            'paiement_id': instance.id,
            'montant': float(instance.montant) if instance.montant else None,
            'date_paiement': format_date(instance.date_paiement),
            'mode_paiement': instance.mode_paiement.libelle if instance.mode_paiement else None,
            'type_transaction': instance.type_transaction,
            'nouveau_montant_restant': float(cotisation.montant_restant) if cotisation.montant_restant else None,
            'nouveau_statut_paiement': cotisation.statut_paiement,
        }
        
        HistoriqueCotisation.objects.create(
            cotisation=cotisation,
            action='paiement_supprime',
            details=json.dumps(details),
            date_action=timezone.now()
        )
    except Cotisation.DoesNotExist:
        # La cotisation a déjà été supprimée, rien à faire
        pass