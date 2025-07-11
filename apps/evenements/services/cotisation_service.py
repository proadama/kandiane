# apps/evenements/services/cotisation_service.py - CRÉER CE FICHIER
from django.utils import timezone
from django.db import transaction
from apps.cotisations.models import Cotisation, Paiement
import logging

logger = logging.getLogger(__name__)

class EvenementCotisationService:
    """Service d'intégration entre événements et cotisations"""
    
    @staticmethod
    def creer_cotisation_inscription(inscription_evenement, utilisateur=None):
        """Crée une cotisation pour une inscription à un événement payant"""
        try:
            if not inscription_evenement.evenement.est_payant:
                return None, "Événement gratuit"
            
            # Vérifier si une cotisation existe déjà
            cotisation_existante = Cotisation.objects.filter(
                inscription_evenement_id=inscription_evenement.id,
                type_cotisation='evenement'
            ).first()
            
            if cotisation_existante:
                return cotisation_existante, "Cotisation existante"
            
            # Créer la nouvelle cotisation
            cotisation, message = Cotisation.creer_pour_evenement(
                inscription_evenement, utilisateur
            )
            
            if cotisation:
                logger.info(f"Cotisation créée: {cotisation.reference} pour inscription {inscription_evenement.id}")
            
            return cotisation, message
            
        except Exception as e:
            logger.error(f"Erreur création cotisation inscription {inscription_evenement.id}: {str(e)}")
            return None, f"Erreur: {str(e)}"
    
    @staticmethod
    def synchroniser_paiement(inscription_evenement):
        """Synchronise les paiements entre inscription et cotisation"""
        try:
            cotisation = Cotisation.objects.filter(
                inscription_evenement_id=inscription_evenement.id,
                type_cotisation='evenement'
            ).first()
            
            if not cotisation:
                return False, "Aucune cotisation trouvée"
            
            # Vérifier si un paiement existe déjà
            if inscription_evenement.montant_paye > 0 and not cotisation.paiements.exists():
                # Créer le paiement dans le système cotisations
                Paiement.objects.create(
                    cotisation=cotisation,
                    montant=inscription_evenement.montant_paye,
                    mode_paiement=inscription_evenement.mode_paiement,
                    reference_paiement=inscription_evenement.reference_paiement or f"EVT-{inscription_evenement.id}",
                    commentaire=f"Paiement événement: {inscription_evenement.evenement.titre}",
                    metadata={
                        'inscription_id': inscription_evenement.id,
                        'synchronisation': True
                    }
                )
                
                logger.info(f"Paiement synchronisé pour cotisation {cotisation.reference}")
                return True, "Paiement synchronisé"
            
            return True, "Déjà synchronisé"
            
        except Exception as e:
            logger.error(f"Erreur synchronisation paiement: {str(e)}")
            return False, f"Erreur: {str(e)}"
    
    @staticmethod
    def gerer_remboursement_annulation(evenement, raison="Annulation événement"):
        """Gère les remboursements automatiques en cas d'annulation d'événement"""
        try:
            cotisations = Cotisation.objects.filter(
                evenement_id=evenement.id,
                type_cotisation='evenement',
                statut_paiement='payee'
            )
            
            remboursements_effectues = 0
            erreurs = []
            
            for cotisation in cotisations:
                # Force le remboursement en cas d'annulation d'événement
                try:
                    success, message = cotisation.effectuer_remboursement(
                        raison=raison, 
                        utilisateur=None
                    )
                    if success:
                        remboursements_effectues += 1
                    else:
                        erreurs.append(f"Cotisation {cotisation.reference}: {message}")
                except Exception as e:
                    erreurs.append(f"Cotisation {cotisation.reference}: {str(e)}")
            
            return remboursements_effectues, erreurs
            
        except Exception as e:
            logger.error(f"Erreur remboursements annulation événement {evenement.id}: {str(e)}")
            return 0, [f"Erreur générale: {str(e)}"]
    
    @staticmethod
    def obtenir_rapports_financiers_evenement(evenement):
        """Génère un rapport financier pour un événement"""
        try:
            cotisations = Cotisation.objects.filter(
                evenement_id=evenement.id,
                type_cotisation='evenement'
            )
            
            if not cotisations.exists():
                return {
                    'total_cotisations': 0,
                    'total_paye': 0,
                    'total_restant': 0,
                    'nombre_participants': 0,
                    'detail_paiements': []
                }
            
            from django.db.models import Sum, Count
            
            stats = cotisations.aggregate(
                total_montant=Sum('montant'),
                total_paye=Sum('montant') - Sum('montant_restant'),
                total_restant=Sum('montant_restant'),
                nombre_cotisations=Count('id')
            )
            
            return {
                'total_cotisations': float(stats['total_montant'] or 0),
                'total_paye': float(stats['total_paye'] or 0),
                'total_restant': float(stats['total_restant'] or 0),
                'nombre_participants': stats['nombre_cotisations'],
                'cotisations_detail': list(cotisations.values(
                    'reference', 'membre__nom', 'membre__prenom', 
                    'montant', 'montant_restant', 'statut_paiement'
                ))
            }
            
        except Exception as e:
            logger.error(f"Erreur rapport financier événement {evenement.id}: {str(e)}")
            return {}