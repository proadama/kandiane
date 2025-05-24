# apps/cotisations/managers.py
from django.db import models
from django.db.models import Sum, Q, F, ExpressionWrapper, DecimalField
from django.utils import timezone
from decimal import Decimal


class BaseManager(models.Manager):
    """
    Gestionnaire de base pour les modèles avec suppression logique.
    """
    def get_queryset(self):
        """Par défaut, on exclut les objets supprimés"""
        return super().get_queryset().filter(deleted_at__isnull=True)
    
    def with_deleted(self):
        """Inclut les objets supprimés"""
        return super().get_queryset()
    
    def only_deleted(self):
        """Ne retourne que les objets supprimés"""
        return super().get_queryset().filter(deleted_at__isnull=False)
    
    def hard_delete(self):
        """Suppression physique définitive"""
        return super().get_queryset().delete()


class CotisationManager(BaseManager):
    """
    Gestionnaire personnalisé pour les cotisations.
    """
    def en_retard(self):
        """Retourne les cotisations en retard de paiement"""
        return self.filter(
            date_echeance__lt=timezone.now().date(),
            statut_paiement__in=['non_payee', 'partiellement_payee']
        )
    
    def a_echeance(self, jours=30):
        """Retourne les cotisations qui arrivent à échéance dans X jours"""
        date_limite = timezone.now().date() + timezone.timedelta(days=jours)
        return self.filter(
            date_echeance__lte=date_limite,
            date_echeance__gte=timezone.now().date(),
            statut_paiement__in=['non_payee', 'partiellement_payee']
        )
    
    def pour_membre(self, membre_id):
        """Retourne les cotisations d'un membre spécifique"""
        return self.filter(membre_id=membre_id)
    
    def par_statut_paiement(self, statut):
        """Filtre par statut de paiement"""
        return self.filter(statut_paiement=statut)
    
    def pour_periode(self, debut, fin=None):
        """Retourne les cotisations pour une période donnée"""
        query = self.filter(date_emission__gte=debut)
        if fin:
            query = query.filter(date_emission__lte=fin)
        return query
    
    def pour_annee(self, annee):
        """Retourne les cotisations pour une année spécifique"""
        return self.filter(annee=annee)
    
    def pour_mois_annee(self, mois, annee):
        """Retourne les cotisations pour un mois et une année spécifiques"""
        return self.filter(mois=mois, annee=annee)
    
    def total_a_percevoir(self):
        """Retourne le montant total des cotisations"""
        return self.aggregate(total=Sum('montant')).get('total') or Decimal('0.00')
    
    def total_percu(self):
        """Retourne le montant total des cotisations payées"""
        # Calculer la différence entre montant total et montant restant
        expr = ExpressionWrapper(
            F('montant') - F('montant_restant'),
            output_field=DecimalField()
        )
        return self.aggregate(total=Sum(expr)).get('total') or Decimal('0.00')
    
    def taux_recouvrement(self):
        """Calcule le taux de recouvrement des cotisations en pourcentage"""
        total = self.total_a_percevoir()
        if total == 0:
            return Decimal('0.00')
        
        percu = self.total_percu()
        return (percu / total * 100).quantize(Decimal('0.01'))
    
    def cotisations_par_type_membre(self):
        """Retourne les statistiques de cotisations par type de membre"""
        return self.values('type_membre__libelle').annotate(
            total=Sum('montant'),
            count=models.Count('id')
        ).order_by('type_membre__libelle')
    
    def recherche(self, terme):
        """Recherche globale sur les cotisations"""
        if not terme:
            return self.all()
        
        # Recherche par référence, commentaire ou nom/prénom du membre
        return self.filter(
            Q(reference__icontains=terme) |
            Q(commentaire__icontains=terme) |
            Q(membre__nom__icontains=terme) |
            Q(membre__prenom__icontains=terme) |
            Q(membre__email__icontains=terme)
        )


class PaiementManager(BaseManager):
    """
    Gestionnaire personnalisé pour les paiements.
    """
    def pour_cotisation(self, cotisation_id):
        """Retourne les paiements pour une cotisation spécifique"""
        return self.filter(cotisation_id=cotisation_id)
    
    def pour_membre(self, membre_id):
        """Retourne les paiements d'un membre spécifique"""
        return self.filter(cotisation__membre_id=membre_id)
    
    def par_mode_paiement(self, mode_id):
        """Filtre par mode de paiement"""
        return self.filter(mode_paiement_id=mode_id)
    
    def par_type_transaction(self, type_transaction):
        """Filtre par type de transaction"""
        return self.filter(type_transaction=type_transaction)
    
    def pour_periode(self, debut, fin=None):
        """Retourne les paiements pour une période donnée"""
        query = self.filter(date_paiement__gte=debut)
        if fin:
            query = query.filter(date_paiement__lte=fin)
        return query
    
    def total_paiements(self):
        """Retourne le montant total des paiements positifs"""
        return self.filter(type_transaction='paiement').aggregate(
            total=Sum('montant')
        ).get('total') or Decimal('0.00')
    
    def total_remboursements(self):
        """Retourne le montant total des remboursements"""
        return self.filter(type_transaction='remboursement').aggregate(
            total=Sum('montant')
        ).get('total') or Decimal('0.00')
    
    def paiements(self):
        """Retourne uniquement les transactions de type 'paiement'"""
        return self.filter(type_transaction='paiement')

    def remboursements(self):
        """Retourne uniquement les transactions de type 'remboursement'"""
        return self.filter(type_transaction='remboursement')

    def rejets(self):
        """Retourne uniquement les transactions de type 'rejet'"""
        return self.filter(type_transaction='rejet')

    def recherche(self, terme):
        """Recherche globale sur les paiements"""
        if not terme:
            return self.all()
        
        # Recherche par référence, commentaire ou nom/prénom du membre
        return self.filter(
            Q(reference_paiement__icontains=terme) |
            Q(commentaire__icontains=terme) |
            Q(cotisation__reference__icontains=terme) |
            Q(cotisation__membre__nom__icontains=terme) |
            Q(cotisation__membre__prenom__icontains=terme)
        )