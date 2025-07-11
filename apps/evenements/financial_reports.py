# apps/evenements/financial_reports.py - CRÉER CE FICHIER
from django.db.models import Sum, Count, Q, Avg
from django.utils import timezone
from datetime import datetime, timedelta
from apps.cotisations.models import Cotisation, Paiement
from .models import Evenement, InscriptionEvenement

class EvenementFinancialReports:
    """Classe pour les rapports financiers des événements"""
    
    @staticmethod
    def rapport_revenus_evenements(date_debut=None, date_fin=None):
        """Génère un rapport des revenus par événements"""
        
        if not date_debut:
            date_debut = timezone.now().date() - timedelta(days=365)
        if not date_fin:
            date_fin = timezone.now().date()
        
        # Cotisations d'événements sur la période
        cotisations_evenements = Cotisation.objects.filter(
            metadata__type_cotisation='EVENEMENT',
            date_echeance__range=[date_debut, date_fin]
        )
        
        rapport = {
            'periode': {'debut': date_debut, 'fin': date_fin},
            'total_cotisations': cotisations_evenements.count(),
            'montant_total_attendu': 0,
            'montant_total_percu': 0,
            'montant_total_restant': 0,
            'taux_recouvrement': 0,
            'evenements': [],
            'par_type_evenement': {},
            'par_statut_paiement': {
                'payee': 0,
                'partiellement_payee': 0,
                'non_payee': 0
            }
        }
        
        if cotisations_evenements.exists():
            # Statistiques globales
            totaux = cotisations_evenements.aggregate(
                total_attendu=Sum('montant'),
                total_restant=Sum('montant_restant')
            )
            
            rapport['montant_total_attendu'] = float(totaux['total_attendu'] or 0)
            rapport['montant_total_restant'] = float(totaux['total_restant'] or 0)
            rapport['montant_total_percu'] = rapport['montant_total_attendu'] - rapport['montant_total_restant']
            
            if rapport['montant_total_attendu'] > 0:
                rapport['taux_recouvrement'] = round(
                    (rapport['montant_total_percu'] / rapport['montant_total_attendu']) * 100, 2
                )
            
            # Par statut de paiement
            for statut in ['payee', 'partiellement_payee', 'non_payee']:
                count = cotisations_evenements.filter(statut_paiement=statut).count()
                rapport['par_statut_paiement'][statut] = count
            
            # Détail par événement
            evenements_ids = list(set([
                c.metadata.get('evenement_id') for c in cotisations_evenements 
                if c.metadata.get('evenement_id')
            ]))
            
            for evenement_id in evenements_ids:
                try:
                    evenement = Evenement.objects.get(id=evenement_id)
                    cotisations_evt = cotisations_evenements.filter(
                        metadata__evenement_id=evenement_id
                    )
                    
                    totaux_evt = cotisations_evt.aggregate(
                        total_attendu=Sum('montant'),
                        total_restant=Sum('montant_restant'),
                        nb_inscriptions=Count('id')
                    )
                    
                    montant_percu = (totaux_evt['total_attendu'] or 0) - (totaux_evt['total_restant'] or 0)
                    
                    rapport['evenements'].append({
                        'evenement': {
                            'id': evenement.id,
                            'titre': evenement.titre,
                            'date': evenement.date_debut,
                            'type': evenement.type_evenement.libelle
                        },
                        'nb_inscriptions': totaux_evt['nb_inscriptions'],
                        'montant_attendu': float(totaux_evt['total_attendu'] or 0),
                        'montant_percu': float(montant_percu),
                        'montant_restant': float(totaux_evt['total_restant'] or 0),
                        'taux_recouvrement': round(
                            (montant_percu / (totaux_evt['total_attendu'] or 1)) * 100, 2
                        )
                    })
                    
                except Evenement.DoesNotExist:
                    continue
        
        return rapport
    
    @staticmethod
    def rapport_remboursements(date_debut=None, date_fin=None):
        """Génère un rapport des remboursements"""
        
        if not date_debut:
            date_debut = timezone.now().date() - timedelta(days=30)
        if not date_fin:
            date_fin = timezone.now().date()
        
        # Paiements de remboursement sur la période
        remboursements = Paiement.objects.filter(
            type_transaction='remboursement',
            date_paiement__date__range=[date_debut, date_fin],
            cotisation__metadata__type_cotisation='EVENEMENT'
        ).select_related('cotisation')
        
        rapport = {
            'periode': {'debut': date_debut, 'fin': date_fin},
            'total_remboursements': remboursements.count(),
            'montant_total_rembourse': 0,
            'remboursements': [],
            'par_raison': {}
        }
        
        if remboursements.exists():
            # Montant total (attention : les remboursements sont en négatif)
            total = remboursements.aggregate(total=Sum('montant'))['total'] or 0
            rapport['montant_total_rembourse'] = abs(float(total))
            
            # Détail des remboursements
            for remboursement in remboursements:
                cotisation = remboursement.cotisation
                evenement_id = cotisation.metadata.get('evenement_id')
                
                try:
                    evenement = Evenement.objects.get(id=evenement_id) if evenement_id else None
                except Evenement.DoesNotExist:
                    evenement = None
                
                raison = remboursement.metadata.get('raison_remboursement', 'Non spécifiée')
                
                rapport['remboursements'].append({
                    'date': remboursement.date_paiement,
                    'montant': abs(float(remboursement.montant)),
                    'cotisation_reference': cotisation.reference,
                    'evenement': {
                        'titre': evenement.titre if evenement else 'Événement supprimé',
                        'date': evenement.date_debut if evenement else None
                    },
                    'raison': raison
                })
                
                # Grouper par raison
                if raison in rapport['par_raison']:
                    rapport['par_raison'][raison]['count'] += 1
                    rapport['par_raison'][raison]['montant'] += abs(float(remboursement.montant))
                else:
                    rapport['par_raison'][raison] = {
                        'count': 1,
                        'montant': abs(float(remboursement.montant))
                    }
        
        return rapport
    
    @staticmethod
    def tableau_bord_financier_evenements():
        """Tableau de bord financier synthétique pour les événements"""
        
        now = timezone.now()
        debut_mois = now.replace(day=1).date()
        fin_mois = (debut_mois.replace(month=debut_mois.month + 1) if debut_mois.month < 12 
                   else debut_mois.replace(year=debut_mois.year + 1, month=1)) - timedelta(days=1)
        
        # Données du mois en cours
        cotisations_mois = Cotisation.objects.filter(
            metadata__type_cotisation='EVENEMENT',
            date_echeance__range=[debut_mois, fin_mois]
        )
        
        # Événements du mois
        evenements_mois = Evenement.objects.filter(
            date_debut__date__range=[debut_mois, fin_mois]
        )
        
        dashboard = {
            'mois_courant': {
                'periode': {'debut': debut_mois, 'fin': fin_mois},
                'nb_evenements': evenements_mois.count(),
                'nb_evenements_payants': evenements_mois.filter(est_payant=True).count(),
                'nb_inscriptions_payantes': cotisations_mois.count(),
                'revenus_prevus': float(cotisations_mois.aggregate(
                    total=Sum('montant'))['total'] or 0),
                'revenus_percus': float(cotisations_mois.aggregate(
                    total=Sum('montant') - Sum('montant_restant'))['total'] or 0),
            },
            'a_venir': {
                'evenements_non_payes': 0,
                'montant_attendu': 0
            },
            'alertes': []
        }
        
        # Revenus restants
        dashboard['mois_courant']['revenus_restants'] = (
            dashboard['mois_courant']['revenus_prevus'] - 
            dashboard['mois_courant']['revenus_percus']
        )
        
        # Événements à venir avec impayés
        evenements_futurs = Evenement.objects.filter(
            date_debut__gte=now,
            est_payant=True
        )
        
        for evenement in evenements_futurs:
            cotisations_impayees = Cotisation.objects.filter(
                metadata__evenement_id=evenement.id,
                montant_restant__gt=0
            )
            
            if cotisations_impayees.exists():
                montant_impaye = cotisations_impayees.aggregate(
                    total=Sum('montant_restant'))['total'] or 0
                
                dashboard['a_venir']['evenements_non_payes'] += 1
                dashboard['a_venir']['montant_attendu'] += float(montant_impaye)
                
                # Alertes pour échéances proches
                jours_avant = (evenement.date_debut.date() - now.date()).days
                if jours_avant <= 7:
                    dashboard['alertes'].append({
                        'type': 'echeance_proche',
                        'message': f"Événement '{evenement.titre}' dans {jours_avant} jour(s) avec {cotisations_impayees.count()} impayé(s)",
                        'montant': float(montant_impaye)
                    })
        
        return dashboard