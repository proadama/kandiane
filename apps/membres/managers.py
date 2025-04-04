from django.db import models
from django.db.models import Q, Count, Max, F, Subquery, OuterRef
from django.utils import timezone
from apps.core.managers import BaseManager
import datetime

class TypeMembreManager(BaseManager):
    """
    Gestionnaire personnalisé pour le modèle TypeMembre
    """
    def actifs(self):
        """Retourne les types de membres qui ont au moins un membre actif"""
        from apps.membres.models import MembreTypeMembre
        
        types_ids = MembreTypeMembre.objects.filter(
            date_debut__lte=timezone.now().date(),
            date_fin__isnull=True
        ).values_list('type_membre_id', flat=True).distinct()
        
        return self.filter(id__in=types_ids)
    
    def avec_nombre_membres(self):
        """Retourne les types de membres avec le nombre de membres actifs"""
        from apps.membres.models import MembreTypeMembre
        
        subquery = MembreTypeMembre.objects.filter(
            type_membre=OuterRef('pk'),
            date_debut__lte=timezone.now().date(),
            date_fin__isnull=True
        ).values('type_membre').annotate(
            count=Count('membre', distinct=True)
        ).values('count')
        
        return self.annotate(nombre_membres=Subquery(subquery))
    
    def par_ordre_affichage(self):
        """Retourne les types de membres triés par ordre d'affichage"""
        return self.order_by('ordre_affichage', 'libelle')


class MembreManager(BaseManager):
    """
    Gestionnaire personnalisé pour le modèle Membre
    """
    def recherche(self, query):
        """Recherche de membres par différents critères"""
        if not query:
            return self.all()
        
        return self.filter(
            Q(nom__icontains=query) | 
            Q(prenom__icontains=query) | 
            Q(email__icontains=query) | 
            Q(telephone__icontains=query) |
            Q(code_postal__icontains=query) |
            Q(ville__icontains=query)
        )
    
    def par_type(self, type_membre_id):
        """Filtre les membres par type de membre actif"""
        if not type_membre_id:
            return self.all()
            
        return self.filter(
            types_historique__type_membre_id=type_membre_id,
            types_historique__date_debut__lte=timezone.now().date(),
            types_historique__date_fin__isnull=True
        ).distinct()
    
    def par_statut(self, statut_id):
        """Filtre les membres par statut"""
        if not statut_id:
            return self.all()
            
        return self.filter(statut_id=statut_id)
    
    def adhesions_recentes(self, jours=30):
        """Retourne les membres ayant adhéré récemment"""
        date_limite = timezone.now().date() - timezone.timedelta(days=jours)
        return self.filter(date_adhesion__gte=date_limite)
    
    def avec_cotisations_impayees(self):
        """Retourne les membres ayant des cotisations impayées"""
        from apps.cotisations.models import Cotisation
        
        membres_ids = Cotisation.objects.filter(
            statut_paiement__in=['non_payée', 'partiellement_payée']
        ).values_list('membre_id', flat=True).distinct()
        
        return self.filter(id__in=membres_ids)
    
    def avec_statistiques(self):
        """Ajoute des statistiques aux membres (cotisations, événements, etc.)"""
        from apps.cotisations.models import Cotisation
        from apps.evenements.models import Inscription
        
        return self.annotate(
            nb_cotisations=Count('cotisation', distinct=True),
            nb_evenements=Count('inscriptions', distinct=True),
            derniere_cotisation=Max('cotisation__date_creation')
        )
    
    def sans_compte_utilisateur(self):
        """Retourne les membres sans compte utilisateur associé"""
        return self.filter(utilisateur__isnull=True)
    
    def avec_compte_utilisateur(self):
        """Retourne les membres avec compte utilisateur associé"""
        return self.filter(utilisateur__isnull=False)
    
    def actifs(self):
        """Retourne les membres actifs (avec au moins un type de membre actif)"""
        from apps.membres.models import MembreTypeMembre
        
        membres_ids = MembreTypeMembre.objects.filter(
            date_debut__lte=timezone.now().date(),
            date_fin__isnull=True
        ).values_list('membre_id', flat=True).distinct()
        
        return self.filter(id__in=membres_ids)
        
    def inactifs(self):
        """Retourne les membres inactifs (sans type de membre actif)"""
        from apps.membres.models import MembreTypeMembre
        
        membres_ids = MembreTypeMembre.objects.filter(
            date_debut__lte=timezone.now().date(),
            date_fin__isnull=True
        ).values_list('membre_id', flat=True).distinct()
        
        return self.exclude(id__in=membres_ids)
    
    def par_age(self, age_min=None, age_max=None):
        """Filtre les membres par tranche d'âge"""
        today = timezone.now().date()
        queryset = self.all()
        
        if age_min is not None:
            date_naissance_max = today.replace(year=today.year - age_min)
            queryset = queryset.filter(date_naissance__lte=date_naissance_max)
            
        if age_max is not None:
            date_naissance_min = today.replace(year=today.year - age_max - 1)
            date_naissance_min = date_naissance_min.replace(day=date_naissance_min.day + 1)
            queryset = queryset.filter(date_naissance__gt=date_naissance_min)
            
        return queryset
    
    def par_anciennete(self, annees_min=None, annees_max=None):
        """Filtre les membres par ancienneté (en années)"""
        today = timezone.now().date()
        queryset = self.all()
        
        if annees_min is not None:
            # Calculer la date limite en jours plutôt qu'en utilisant replace()
            days_min = int(annees_min * 365)
            date_adhesion_max = today - datetime.timedelta(days=days_min)
            queryset = queryset.filter(date_adhesion__lte=date_adhesion_max)
            
        if annees_max is not None:
            # Calculer la date limite en jours
            days_max = int(annees_max * 365)
            date_adhesion_min = today - datetime.timedelta(days=days_max)
            queryset = queryset.filter(date_adhesion__gt=date_adhesion_min)
            
        return queryset


class MembreTypeMembreManager(models.Manager):
    """
    Gestionnaire personnalisé pour le modèle MembreTypeMembre
    """
    def actifs(self):
        """Retourne les associations membre-type actives"""
        today = timezone.now().date()
        return self.filter(
            date_debut__lte=today,
            date_fin__isnull=True
        )
    
    def par_type(self, type_membre_id):
        """Filtre les associations par type de membre"""
        return self.filter(type_membre_id=type_membre_id)
    
    def par_membre(self, membre_id):
        """Filtre les associations par membre"""
        return self.filter(membre_id=membre_id)
    
    def historique(self, membre_id=None, type_membre_id=None):
        """Retourne l'historique complet des associations"""
        queryset = self.all()
        
        if membre_id:
            queryset = queryset.filter(membre_id=membre_id)
            
        if type_membre_id:
            queryset = queryset.filter(type_membre_id=type_membre_id)
            
        return queryset.order_by('membre', 'type_membre', '-date_debut')