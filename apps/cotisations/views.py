# apps/cotisations/views.py
"""
Vues pour la gestion des cotisations, paiements, rappels et barèmes.
"""
# Importations standard
import csv
import datetime
import io
import json
import logging
import os
import tempfile
import traceback
from decimal import Decimal, InvalidOperation
from django.db import connection
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from datetime import datetime

# Importations Django
from django.contrib import messages
from django import forms
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Q, Sum, Count, F, ExpressionWrapper, DecimalField
from django.http import JsonResponse, HttpResponse, HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST
from django.views.generic import (
    View, TemplateView, ListView, DetailView, 
    CreateView, UpdateView, DeleteView
)

# Importations conditionnelles
try:
    import pandas as pd
    import numpy as np
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

# Importations des applications
from apps.core.mixins import StaffRequiredMixin, TrashViewMixin, RestoreViewMixin
from apps.core.models import Statut
from apps.membres.models import Membre, TypeMembre, MembreTypeMembre
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import View
from apps.core.mixins import StaffRequiredMixin
# Importations locales
from . import export_utils
from .models import (
    Cotisation, Paiement, ModePaiement, BaremeCotisation,
    Rappel, HistoriqueCotisation, ConfigurationCotisation
)
from .forms import (
    CotisationForm, PaiementForm, BaremeCotisationForm,
    RappelForm, CotisationSearchForm, ImportCotisationsForm,
    ConfigurationCotisationForm
)

from apps.cotisations.models import Rappel, RAPPEL_ETAT_PLANIFIE, RAPPEL_ETAT_ENVOYE, RAPPEL_ETAT_ECHOUE, RAPPEL_ETAT_LU

# Configuration du logging
logger = logging.getLogger(__name__)


class ExtendedJSONEncoder(DjangoJSONEncoder):
    """
    Encodeur JSON personnalisé pour gérer les types Python spécifiques
    comme Decimal, date et datetime correctement.
    """
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, datetime.date):
            return obj.isoformat()
        elif isinstance(obj, datetime.datetime):
            return obj.isoformat()
        return super().default(obj)


#
# Vues pour le tableau de bord
#
class DashboardView(StaffRequiredMixin, TemplateView):
    """
    Vue du tableau de bord des cotisations avec statistiques et visualisations.
    """
    template_name = 'cotisations/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Récupérer les paramètres de filtre
        periode = self.request.GET.get('periode', 'year')
        annee = int(self.request.GET.get('annee', timezone.now().date().year))
        
        # Définir les dates de début et de fin selon la période
        today = timezone.now().date()
        
        if periode == 'month':
            # Mois en cours
            date_debut = today.replace(day=1)
            # Dernier jour du mois
            if today.month == 12:
                date_fin = today.replace(day=31)
            else:
                date_fin = today.replace(month=today.month+1, day=1) - datetime.timedelta(days=1)
        elif periode == 'quarter':
            # Trimestre en cours
            current_quarter = (today.month - 1) // 3 + 1
            date_debut = today.replace(month=((current_quarter - 1) * 3) + 1, day=1)
            if current_quarter == 4:
                date_fin = today.replace(month=12, day=31)
            else:
                date_fin = today.replace(month=current_quarter * 3 + 1, day=1) - datetime.timedelta(days=1)
        elif periode == 'year':
            # Année en cours ou sélectionnée
            date_debut = datetime.date(annee, 1, 1)
            date_fin = datetime.date(annee, 12, 31)
        else:  # all
            date_debut = None
            date_fin = None
        
        # Construire les filtres de base
        cotisations_filter = Q()
        if date_debut and date_fin:
            cotisations_filter &= Q(date_emission__gte=date_debut, date_emission__lte=date_fin)
        
        # Statistiques générales
        total_cotisations = Cotisation.objects.filter(cotisations_filter).count()
        montant_total = Cotisation.objects.filter(cotisations_filter).aggregate(
            total=Sum('montant')
        ).get('total') or Decimal('0.00')
        
        montant_paye = Cotisation.objects.filter(cotisations_filter).aggregate(
            total=Sum(ExpressionWrapper(
                F('montant') - F('montant_restant'),
                output_field=DecimalField()
            ))
        ).get('total') or Decimal('0.00')
        
        taux_recouvrement = 0
        if montant_total > 0:
            taux_recouvrement = (montant_paye / montant_total * 100).quantize(Decimal('0.01'))
        
        # Cotisations par statut
        cotisations_par_statut = Cotisation.objects.filter(cotisations_filter).values('statut_paiement').annotate(
            count=Count('id'),
            total=Sum('montant'),
            paid=Sum(ExpressionWrapper(
                F('montant') - F('montant_restant'),
                output_field=DecimalField()
            ))
        ).order_by('statut_paiement')
        
        # Cotisations par type de membre
        cotisations_par_type = Cotisation.objects.filter(cotisations_filter).values(
            'type_membre__libelle'
        ).annotate(
            count=Count('id'),
            total=Sum('montant')
        ).order_by('type_membre__libelle')
        
        # Préparation des données pour le JSON des types de membre
        cotisations_par_type_data = []
        for item in cotisations_par_type:
            libelle = item['type_membre__libelle']
            if libelle is None:
                libelle = 'Non défini'
            
            cotisations_par_type_data.append({
                'libelle': libelle,
                'total': float(item['total'] or 0)
            })
        
        # Définir les noms des mois en français
        mois_fr = [
            'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
            'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre'
        ]
        
        # Cotisations par mois (pour graphique)
        cotisations_par_mois = []
        paiements_par_mois = []
        cotisations_non_payees_par_mois = []
        
        if periode == 'year':
            for month_idx, month_name in enumerate(mois_fr, 1):
                # Cotisations émises ce mois
                month_cotisations = Cotisation.objects.filter(
                    date_emission__year=annee,
                    date_emission__month=month_idx
                )
                
                # Paiements reçus ce mois
                month_paiements = Paiement.objects.filter(
                    date_paiement__year=annee,
                    date_paiement__month=month_idx,
                    type_transaction='paiement'
                )
                
                # Cotisations non payées émises ce mois
                month_non_payees = month_cotisations.filter(
                    statut_paiement__in=['non_payee', 'partiellement_payee']
                )
                
                montant_cotisations = month_cotisations.aggregate(total=Sum('montant')).get('total') or Decimal('0.00')
                montant_paiements = month_paiements.aggregate(total=Sum('montant')).get('total') or Decimal('0.00')
                montant_non_payees = month_non_payees.aggregate(total=Sum('montant_restant')).get('total') or Decimal('0.00')
                
                cotisations_par_mois.append({
                    'month': month_name,
                    'total': float(montant_cotisations)
                })
                
                paiements_par_mois.append({
                    'month': month_name,
                    'total': float(montant_paiements)
                })
                
                cotisations_non_payees_par_mois.append({
                    'month': month_name,
                    'total': float(montant_non_payees)
                })
        
        # TOP 5 des membres avec le plus de cotisations impayées
        top_membres_impayes = Cotisation.objects.filter(
            statut_paiement__in=['non_payee', 'partiellement_payee']
        ).values(
            'membre__id', 
            'membre__nom', 
            'membre__prenom'
        ).annotate(
            total=Sum('montant_restant')
        ).order_by('-total')[:5]
        
        # Cotisations en retard et à échéance proche
        cotisations_retard = Cotisation.objects.en_retard()
        cotisations_echeance = Cotisation.objects.a_echeance(jours=30)
        
        # S'assurer que les données JSON sont bien formatées
        try:
            # Sérialiser toutes les données pour les graphiques
            cotisations_par_mois_json = json.dumps(cotisations_par_mois, cls=ExtendedJSONEncoder, ensure_ascii=False)
            paiements_par_mois_json = json.dumps(paiements_par_mois, cls=ExtendedJSONEncoder, ensure_ascii=False)
            cotisations_non_payees_par_mois_json = json.dumps(cotisations_non_payees_par_mois, cls=ExtendedJSONEncoder, ensure_ascii=False)
            
            # Sérialiser les données de statut
            statuts_data = {
                'non_payee': 0,
                'partiellement_payee': 0,
                'payee': 0
            }
            
            for statut in cotisations_par_statut:
                statut_key = statut['statut_paiement']
                if statut_key in statuts_data:
                    statuts_data[statut_key] = statut['count']
            
            statuts_json = json.dumps(statuts_data, cls=ExtendedJSONEncoder, ensure_ascii=False)
            
            # Sérialiser les données de type de membre
            types_json = json.dumps(cotisations_par_type_data, cls=ExtendedJSONEncoder, ensure_ascii=False)
            
        except Exception as e:
            logger.error(f"Erreur lors de la sérialisation JSON: {str(e)}")
            logger.error(traceback.format_exc())
            
            # En cas d'erreur, utiliser des tableaux vides
            cotisations_par_mois_json = "[]"
            paiements_par_mois_json = "[]"
            cotisations_non_payees_par_mois_json = "[]"
            statuts_json = '{"non_payee": 0, "partiellement_payee": 0, "payee": 0}'
            types_json = "[]"
        
        # Ajouter les données au contexte
        context.update({
            'periode': periode,
            'annee': annee,
            'annees_disponibles': range(today.year - 5, today.year + 1),
            'total_cotisations': total_cotisations,
            'montant_total': montant_total,
            'montant_paye': montant_paye,
            'montant_restant': montant_total - montant_paye,
            'taux_recouvrement': taux_recouvrement,
            'cotisations_par_statut': cotisations_par_statut,
            'cotisations_par_type': cotisations_par_type,
            'cotisations_par_mois': cotisations_par_mois_json,
            'paiements_par_mois': paiements_par_mois_json,
            'cotisations_non_payees_par_mois': cotisations_non_payees_par_mois_json,
            'statuts_json': statuts_json,
            'types_json': types_json,
            'cotisations_retard': cotisations_retard,
            'cotisations_echeance': cotisations_echeance,
            'nb_cotisations_retard': cotisations_retard.count(),
            'nb_cotisations_echeance': cotisations_echeance.count(),
            'top_membres_impayes': top_membres_impayes,
            'now': timezone.now(),
        })
        
        return context
    
class CotisationListView(StaffRequiredMixin, ListView):
    """
    Vue pour afficher la liste des cotisations avec filtres.
    """
    model = Cotisation
    template_name = 'cotisations/cotisation_liste.html'
    context_object_name = 'cotisations'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Cotisation.objects.all()
        form = CotisationSearchForm(self.request.GET)
        
        if form.is_valid():
            # Appliquer les filtres de recherche
            if membre := form.cleaned_data.get('membre'):
                queryset = queryset.filter(membre=membre)
            
            if type_membre := form.cleaned_data.get('type_membre'):
                queryset = queryset.filter(type_membre=type_membre)
            
            if statut_paiement := form.cleaned_data.get('statut_paiement'):
                queryset = queryset.filter(statut_paiement=statut_paiement)
            
            if date_emission_debut := form.cleaned_data.get('date_emission_debut'):
                queryset = queryset.filter(date_emission__gte=date_emission_debut)
            
            if date_emission_fin := form.cleaned_data.get('date_emission_fin'):
                queryset = queryset.filter(date_emission__lte=date_emission_fin)
            
            if date_echeance_debut := form.cleaned_data.get('date_echeance_debut'):
                queryset = queryset.filter(date_echeance__gte=date_echeance_debut)
            
            if date_echeance_fin := form.cleaned_data.get('date_echeance_fin'):
                queryset = queryset.filter(date_echeance__lte=date_echeance_fin)
            
            if montant_min := form.cleaned_data.get('montant_min'):
                queryset = queryset.filter(montant__gte=montant_min)
            
            if montant_max := form.cleaned_data.get('montant_max'):
                queryset = queryset.filter(montant__lte=montant_max)
            
            if annee := form.cleaned_data.get('annee'):
                queryset = queryset.filter(annee=annee)
            
            if mois := form.cleaned_data.get('mois'):
                queryset = queryset.filter(mois=int(mois))
            
            if reference := form.cleaned_data.get('reference'):
                queryset = queryset.filter(reference__icontains=reference)
            
            if en_retard := form.cleaned_data.get('en_retard'):
                queryset = queryset.filter(
                    date_echeance__lt=timezone.now().date(),
                    statut_paiement__in=['non_payee', 'partiellement_payee']
                )
            
            if terme := form.cleaned_data.get('terme'):
                queryset = queryset.filter(
                    Q(reference__icontains=terme) |
                    Q(commentaire__icontains=terme) |
                    Q(membre__nom__icontains=terme) |
                    Q(membre__prenom__icontains=terme) |
                    Q(membre__email__icontains=terme)
                )
        
        return queryset.select_related('membre', 'type_membre', 'statut')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_form'] = CotisationSearchForm(self.request.GET)
        
        # Ajouter des statistiques rapides
        total_cotisations = Cotisation.objects.count()
        montant_total = Cotisation.objects.aggregate(total=Sum('montant')).get('total') or Decimal('0.00')
        montant_paye = Cotisation.objects.aggregate(
            total=Sum(ExpressionWrapper(
                F('montant') - F('montant_restant'),
                output_field=DecimalField()
            ))
        ).get('total') or Decimal('0.00')
        
        context.update({
            'total_cotisations': total_cotisations,
            'montant_total': montant_total,
            'montant_paye': montant_paye,
            'taux_recouvrement': (montant_paye / montant_total * 100).quantize(Decimal('0.01')) if montant_total > 0 else 0
        })
        
        return context


class CotisationDetailView(StaffRequiredMixin, DetailView):
    """
    Vue détaillée d'une cotisation avec ses paiements et rappels.
    """
    model = Cotisation
    template_name = 'cotisations/cotisation_detail.html'
    context_object_name = 'cotisation'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cotisation = self.object
        
        # Paiements liés à cette cotisation
        context['paiements'] = cotisation.paiements.all().order_by('-date_paiement')
        
        # Rappels envoyés
        context['rappels'] = cotisation.rappels.all().order_by('-date_envoi')
        
        # Historique des modifications
        context['historique'] = HistoriqueCotisation.objects.filter(
            cotisation=cotisation
        ).order_by('-date_action')
        
        # Formulaire pour un nouveau paiement
        context['paiement_form'] = PaiementForm(cotisation=cotisation)
        
        # Formulaire pour un nouveau rappel
        context['rappel_form'] = RappelForm(cotisation=cotisation)
        
        # Calculer le montant déjà payé
        context['montant_paye'] = cotisation.montant - cotisation.montant_restant
        
        # Vérifier si la cotisation est en retard
        context['est_en_retard'] = cotisation.est_en_retard
        context['jours_retard'] = cotisation.jours_retard if cotisation.est_en_retard else 0
        
        return context


class CotisationCreateView(StaffRequiredMixin, CreateView):
    """
    Vue pour créer une nouvelle cotisation.
    """
    model = Cotisation
    form_class = CotisationForm
    template_name = 'cotisations/cotisation_form.html'
    
    def get_initial(self):
        initial = super().get_initial()
        
        # Pré-remplir le membre si spécifié dans l'URL
        membre_id = self.kwargs.get('membre_id')
        if membre_id:
            initial['membre'] = membre_id
            
            # Si le membre a un type, pré-remplir le type et récupérer le barème actif
            try:
                membre = Membre.objects.get(pk=membre_id)
                type_membre = membre.get_types_actifs().first()
                if type_membre:
                    initial['type_membre'] = type_membre.id
                    
                    # Trouver le barème actif pour ce type
                    bareme = BaremeCotisation.objects.filter(
                        type_membre=type_membre,
                        date_debut_validite__lte=timezone.now().date()
                    ).order_by('-date_debut_validite').first()
                    
                    if bareme:
                        initial['bareme'] = bareme.id
                        initial['montant'] = bareme.montant
            except Membre.DoesNotExist:
                logger.warning(f"Membre non trouvé avec l'ID {membre_id}")
        
        return initial
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request, 
            _("La cotisation a été créée avec succès.")
        )
        return response
    
    def get_success_url(self):
        return reverse('cotisations:cotisation_detail', kwargs={'pk': self.object.pk})


class CotisationUpdateView(StaffRequiredMixin, UpdateView):
    """
    Vue pour modifier une cotisation existante.
    """
    model = Cotisation
    form_class = CotisationForm
    template_name = 'cotisations/cotisation_form.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request, 
            _("La cotisation a été modifiée avec succès.")
        )
        return response
    
    def get_success_url(self):
        return reverse('cotisations:cotisation_detail', kwargs={'pk': self.object.pk})


class CotisationDeleteView(StaffRequiredMixin, DeleteView):
    """
    Vue pour supprimer une cotisation.
    """
    model = Cotisation
    template_name = 'cotisations/cotisation_confirm_delete.html'
    success_url = reverse_lazy('cotisations:cotisation_liste')
    
    def delete(self, request, *args, **kwargs):
        cotisation = self.get_object()
        cotisation.modifie_par = request.user
        cotisation.delete()  # Suppression logique
        
        messages.success(
            request, 
            _("La cotisation a été supprimée avec succès.")
        )
        return redirect(self.success_url)


#
# Vues pour les paiements
#
class PaiementListView(StaffRequiredMixin, ListView):
    """
    Vue pour afficher la liste des paiements avec filtres.
    """
    model = Paiement
    template_name = 'cotisations/paiement_liste.html'
    context_object_name = 'paiements'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Paiement.objects.all().select_related(
            'cotisation', 'cotisation__membre', 'mode_paiement', 'statut'
        )
        
        # Filtres par cotisation
        cotisation_id = self.request.GET.get('cotisation')
        if cotisation_id:
            queryset = queryset.filter(cotisation_id=cotisation_id)
        
        # Filtre par mode de paiement
        mode_paiement_id = self.request.GET.get('mode_paiement')
        if mode_paiement_id:
            queryset = queryset.filter(mode_paiement_id=mode_paiement_id)
        
        # Filtre par type de transaction
        type_transaction = self.request.GET.get('type_transaction')
        if type_transaction:
            queryset = queryset.filter(type_transaction=type_transaction)
        
        # Recherche textuelle
        recherche = self.request.GET.get('recherche')
        if recherche:
            queryset = queryset.filter(
                Q(reference_paiement__icontains=recherche) |
                Q(commentaire__icontains=recherche) |
                Q(cotisation__reference__icontains=recherche) |
                Q(cotisation__membre__nom__icontains=recherche) |
                Q(cotisation__membre__prenom__icontains=recherche)
            )
        
        # Filtre par date
        date_debut = self.request.GET.get('date_debut')
        if date_debut:
            try:
                queryset = queryset.filter(date_paiement__gte=date_debut)
            except (ValueError, TypeError):
                logger.warning(f"Format de date de début invalide: {date_debut}")
        
        date_fin = self.request.GET.get('date_fin')
        if date_fin:
            try:
                # Ajouter un jour pour inclure toute la journée de fin
                date_fin_dt = datetime.datetime.strptime(date_fin, '%Y-%m-%d')
                date_fin_next = (date_fin_dt + datetime.timedelta(days=1)).strftime('%Y-%m-%d')
                queryset = queryset.filter(date_paiement__lt=date_fin_next)
            except (ValueError, TypeError):
                logger.warning(f"Format de date de fin invalide: {date_fin}")
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Liste des cotisations pour le filtre
        context['cotisations_list'] = Cotisation.objects.all().order_by('-date_emission')[:100]
        
        # Liste des modes de paiement pour le filtre
        context['modes_paiement'] = ModePaiement.objects.filter(actif=True)
        
        # Calculer les statistiques
        paiements = Paiement.objects.all()
        
        # Total des paiements
        context['total_paiements'] = paiements.count()
        
        # Montant total des paiements (entrées d'argent)
        montant_paiements = paiements.filter(
            type_transaction='paiement'
        ).aggregate(total=Sum('montant')).get('total') or Decimal('0.00')
        
        context['montant_total'] = montant_paiements
        
        # Montant des remboursements
        montant_remboursements = paiements.filter(
            type_transaction='remboursement'
        ).aggregate(total=Sum('montant')).get('total') or Decimal('0.00')
        
        context['montant_remboursements'] = montant_remboursements
        
        # Montant des rejets
        montant_rejets = paiements.filter(
            type_transaction='rejet'
        ).aggregate(total=Sum('montant')).get('total') or Decimal('0.00')
        
        context['montant_rejets'] = montant_rejets
        
        # Total des déductions (remboursements + rejets)
        context['total_deductions'] = montant_remboursements + montant_rejets
        
        # Solde net
        context['solde_net'] = montant_paiements - (montant_remboursements + montant_rejets)
        
        return context


# Import conditionnel pour historique des transactions
try:
    from .models import HistoriqueTransaction
except ImportError:
    # Fallback - utiliser une classe abstraite si le modèle n'existe pas
    class HistoriqueTransaction:
        objects = None
        
        @staticmethod
        def get_empty_queryset():
            from django.db.models.query import EmptyQuerySet
            return EmptyQuerySet(model=None)


class PaiementDetailView(StaffRequiredMixin, DetailView):
    """
    Vue détaillée d'un paiement avec son historique.
    """
    model = Paiement
    template_name = 'cotisations/paiement_detail.html'
    context_object_name = 'paiement'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        paiement = self.object
        
        # Récupérer l'historique des actions liées à ce paiement
        if hasattr(HistoriqueTransaction, 'objects') and HistoriqueTransaction.objects:
            context['historique'] = HistoriqueTransaction.objects.filter(
                type='paiement',
                reference_id=paiement.id
            ).order_by('-date_creation')
        else:
            # Vérifier s'il existe une table directe historique_transactions
            try:
                from django.db import connection
                with connection.cursor() as cursor:
                    cursor.execute("""
                        SELECT * FROM historique_transactions 
                        WHERE type = 'paiement' AND reference_id = %s
                        ORDER BY date_creation DESC
                    """, [paiement.id])
                    columns = [col[0] for col in cursor.description]
                    context['historique'] = [
                        dict(zip(columns, row)) for row in cursor.fetchall()
                    ]
            except Exception as e:
                # Si rien ne fonctionne, initialiser avec une liste vide
                logger.error(f"Erreur lors de la récupération de l'historique: {str(e)}")
                context['historique'] = []
        
        # Calculer le montant payé
        if hasattr(paiement.cotisation, 'montant') and hasattr(paiement.cotisation, 'montant_restant'):
            context['montant_paye'] = paiement.cotisation.montant - paiement.cotisation.montant_restant
        else:
            context['montant_paye'] = Decimal('0.00')
        
        return context


class PaiementCreateView(StaffRequiredMixin, CreateView):
    """
    Vue pour créer un nouveau paiement.
    """
    model = Paiement
    form_class = PaiementForm
    template_name = 'cotisations/paiement_form.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        
        # Récupérer la cotisation associée
        cotisation_id = self.kwargs.get('cotisation_id')
        if cotisation_id:
            self.cotisation = get_object_or_404(Cotisation, pk=cotisation_id)
            kwargs['cotisation'] = self.cotisation
        
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if hasattr(self, 'cotisation'):
            context['cotisation'] = self.cotisation
        return context
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request, 
            _("Le paiement a été enregistré avec succès. Référence: {}").format(self.object.reference_paiement)
        )
        return response
    
    def get_success_url(self):
        if hasattr(self, 'cotisation'):
            return reverse('cotisations:cotisation_detail', kwargs={'pk': self.cotisation.pk})
        return reverse('cotisations:cotisation_liste')


@require_POST
def paiement_create_ajax(request, cotisation_id):
    """
    Vue AJAX pour créer un paiement depuis la page de détail d'une cotisation.
    """
    cotisation = get_object_or_404(Cotisation, pk=cotisation_id)
    
    # Pour les requêtes AJAX avec JSON
    if request.content_type == 'application/json':
        try:
            data = json.loads(request.body)
            
            # Créer un dictionnaire de données pour le formulaire
            form_data = {
                'montant': data.get('montant'),
                'mode_paiement': data.get('mode_paiement'),
                'date_paiement': data.get('date_paiement'),
                'type_transaction': data.get('type_transaction', 'paiement'),
                'reference_paiement': data.get('reference_paiement', ''),
                'commentaire': data.get('commentaire', '')
            }
            
            # Utiliser None comme user si non authentifié
            user = request.user if request.user.is_authenticated else None
            form = PaiementForm(form_data, user=user, cotisation=cotisation)
            
            if form.is_valid():
                paiement = form.save()
                
                # Recharger la cotisation pour avoir les informations à jour
                cotisation.refresh_from_db()
                
                # Préparer les données de réponse
                success_message = _("Le paiement a été enregistré avec succès.")
                
                # Retourner les infos sur le paiement et la cotisation mise à jour
                return JsonResponse({
                    'success': True,
                    'paiement': {
                        'id': paiement.id,
                        'montant': float(paiement.montant),
                        'date_paiement': paiement.date_paiement.strftime('%Y-%m-%dT%H:%M:%S'),
                        'mode_paiement': paiement.mode_paiement.libelle if paiement.mode_paiement else '-',
                        'type_transaction': str(paiement.get_type_transaction_display()),
                        'reference_paiement': paiement.reference_paiement or ''
                    },
                    'cotisation': {
                        'montant_restant': float(cotisation.montant_restant),
                        'statut_paiement': str(cotisation.get_statut_paiement_display())
                    },
                    'message': success_message
                }, encoder=ExtendedJSONEncoder)
            else:
                error_message = _("Erreur lors de l'enregistrement du paiement.")
                return JsonResponse({
                    'success': False,
                    'errors': form.errors.as_json(),
                    'message': error_message
                }, encoder=ExtendedJSONEncoder)
        except json.JSONDecodeError:
            error_message = _("Format de données invalide.")
            return JsonResponse({
                'success': False,
                'message': str(error_message)
            }, encoder=ExtendedJSONEncoder, status=400)
    
    # Pour les requêtes standard
    else:
        # Utiliser None comme user si non authentifié
        user = request.user if request.user.is_authenticated else None
        form = PaiementForm(request.POST, user=user, cotisation=cotisation)
        
        if form.is_valid():
            paiement = form.save()
            
            # Retourner les infos sur le paiement et la cotisation mise à jour
            cotisation.refresh_from_db()
            
            success_message = _("Le paiement a été enregistré avec succès.")
            
            return JsonResponse({
                'success': True,
                'paiement': {
                    'id': paiement.id,
                    'montant': float(paiement.montant),
                    'date_paiement': paiement.date_paiement.strftime('%Y-%m-%dT%H:%M:%S'),
                    'mode_paiement': paiement.mode_paiement.libelle if paiement.mode_paiement else '-',
                    'type_transaction': str(paiement.get_type_transaction_display()),
                    'reference_paiement': paiement.reference_paiement or ''
                },
                'cotisation': {
                    'montant_restant': float(cotisation.montant_restant),
                    'statut_paiement': str(cotisation.get_statut_paiement_display())
                },
                'message': success_message
            }, encoder=ExtendedJSONEncoder)
        else:
            error_message = _("Erreur lors de l'enregistrement du paiement.")
            return JsonResponse({
                'success': False,
                'errors': form.errors.as_json(),
                'message': error_message
            }, encoder=ExtendedJSONEncoder)

class PaiementUpdateView(StaffRequiredMixin, UpdateView):
    """
    Vue pour modifier un paiement existant.
    """
    model = Paiement
    form_class = PaiementForm
    template_name = 'cotisations/paiement_form.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        kwargs['cotisation'] = self.object.cotisation
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['cotisation'] = self.object.cotisation
        return context
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request, 
            _("Le paiement a été modifié avec succès.")
        )
        return response
    
    def get_success_url(self):
        return reverse('cotisations:cotisation_detail', kwargs={'pk': self.object.cotisation.pk})


class PaiementDeleteView(StaffRequiredMixin, DeleteView):
    """
    Vue pour supprimer un paiement.
    """
    model = Paiement
    template_name = 'cotisations/paiement_confirm_delete.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['cotisation'] = self.object.cotisation
        return context
    
    def delete(self, request, *args, **kwargs):
        paiement = self.get_object()
        cotisation = paiement.cotisation
        paiement.modifie_par = request.user
        paiement.delete()  # Suppression logique
        
        messages.success(
            request, 
            _("Le paiement a été supprimé avec succès.")
        )
        return redirect('cotisations:cotisation_detail', pk=cotisation.pk)

    def get_success_url(self):
        # Récupérer l'ID de la cotisation avant que le paiement ne soit supprimé
        cotisation_id = self.object.cotisation.id
        return reverse('cotisations:cotisation_detail', kwargs={'pk': cotisation_id})

class RappelCreateView(StaffRequiredMixin, CreateView):
    """
    Vue pour créer un nouveau rappel.
    """
    model = Rappel
    form_class = RappelForm
    template_name = 'cotisations/rappel_form.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        
        # Récupérer la cotisation associée
        cotisation_id = self.kwargs.get('cotisation_id')
        if cotisation_id:
            self.cotisation = get_object_or_404(Cotisation, pk=cotisation_id)
            kwargs['cotisation'] = self.cotisation
            kwargs['membre'] = self.cotisation.membre
        
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if hasattr(self, 'cotisation'):
            context['cotisation'] = self.cotisation
        # Ajouter la date courante pour le template
        context['today'] = timezone.now().date()
        return context
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request, 
            _("Le rappel a été créé avec succès.")
        )
        return response
        
    def get_success_url(self):
        if hasattr(self, 'cotisation'):
            return reverse('cotisations:cotisation_detail', kwargs={'pk': self.cotisation.pk})
        return reverse('cotisations:cotisation_liste')

@login_required
@require_http_methods(["POST"])
def rappel_create_ajax(request, cotisation_id):
    """
    Vue AJAX pour créer un rappel rapidement depuis le modal
    """
    try:
        # Récupérer la cotisation
        cotisation = get_object_or_404(Cotisation, pk=cotisation_id)
        
        # Vérifier les permissions
        if not request.user.is_staff:
            return JsonResponse({
                'success': False,
                'message': 'Permission refusée'
            }, status=403)
        
        # Récupérer les données JSON
        data = json.loads(request.body)
        
        # Validation des données requises
        required_fields = ['type_rappel', 'niveau', 'contenu']
        errors = {}
        
        for field in required_fields:
            if field not in data or not data[field]:
                errors[field] = [f"Le champ {field} est requis"]
        
        # Validation spécifique du niveau
        try:
            niveau = int(data.get('niveau', 0))
            if niveau < 1 or niveau > 5:
                errors['niveau'] = ["Le niveau doit être entre 1 et 5"]
        except (ValueError, TypeError):
            errors['niveau'] = ["Le niveau doit être un nombre entier"]
        
        # Validation du type de rappel
        types_valides = ['email', 'sms', 'courrier', 'appel']
        if data.get('type_rappel') not in types_valides:
            errors['type_rappel'] = ["Type de rappel invalide"]
        
        # Validation du contenu
        contenu = data.get('contenu', '').strip()
        if len(contenu) < 10:
            errors['contenu'] = ["Le contenu doit contenir au moins 10 caractères"]
        elif len(contenu) > 2000:
            errors['contenu'] = ["Le contenu ne peut pas dépasser 2000 caractères"]
        
        # Gestion de la date d'envoi
        date_envoi = timezone.now()
        planifie = data.get('planifie', 'false').lower() == 'true'
        
        if planifie:
            date_planifiee_str = data.get('date_planifiee')
            if date_planifiee_str:
                try:
                    # Parser la date au format ISO (YYYY-MM-DDTHH:MM)
                    date_envoi = datetime.fromisoformat(date_planifiee_str.replace('Z', '+00:00'))
                    if timezone.is_naive(date_envoi):
                        date_envoi = timezone.make_aware(date_envoi)
                    
                    # Vérifier que la date est dans le futur
                    if date_envoi <= timezone.now():
                        errors['date_planification'] = ["La date d'envoi doit être dans le futur"]
                except ValueError:
                    errors['date_planification'] = ["Format de date invalide"]
            else:
                errors['date_planification'] = ["Date de planification requise"]
        
        # Si des erreurs, retourner les erreurs
        if errors:
            return JsonResponse({
                'success': False,
                'message': 'Données invalides',
                'errors': json.dumps(errors)
            }, status=400)
        
        # Créer le rappel
        rappel = Rappel.objects.create(
            cotisation=cotisation,
            membre=cotisation.membre,
            type_rappel=data['type_rappel'],
            niveau=niveau,
            contenu=contenu,
            date_envoi=date_envoi,
            etat=RAPPEL_ETAT_PLANIFIE if planifie else RAPPEL_ETAT_PLANIFIE,
            cree_par=request.user
        )
        
        # Si envoi immédiat, tenter d'envoyer le rappel
        if not planifie:
            try:
                # Marquer comme envoyé immédiatement
                rappel.marquer_comme_envoye()
                rappel.etat = RAPPEL_ETAT_ENVOYE
                rappel.save()
                message_success = f"Rappel créé et envoyé avec succès à {cotisation.membre.prenom} {cotisation.membre.nom}"
            except Exception as e:
                # En cas d'erreur d'envoi, garder le rappel comme planifié
                rappel.etat = RAPPEL_ETAT_ECHOUE
                rappel.resultat = f"Erreur lors de l'envoi: {str(e)}"
                rappel.save()
                message_success = f"Rappel créé mais l'envoi a échoué: {str(e)}"
        else:
            message_success = f"Rappel planifié avec succès pour le {date_envoi.strftime('%d/%m/%Y à %H:%M')}"
        
        # Préparer les données du rappel pour la réponse
        rappel_data = {
            'id': rappel.id,
            'type_rappel': rappel.get_type_rappel_display(),
            'niveau': rappel.niveau,
            'etat': rappel.get_etat_display(),
            'contenu': rappel.contenu,
            'date_envoi': rappel.date_envoi.isoformat()
        }
        
        return JsonResponse({
            'success': True,
            'message': message_success,
            'rappel': rappel_data
        })
        
    except Cotisation.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Cotisation non trouvée'
        }, status=404)
    
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Données JSON invalides'
        }, status=400)
    
    except Exception as e:
        # Logger l'erreur pour le débogage
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Erreur lors de la création du rappel AJAX: {str(e)}", exc_info=True)
        
        return JsonResponse({
            'success': False,
            'message': f'Erreur interne du serveur: {str(e)}'
        }, status=500)


@login_required
def envoyer_rappel(request, rappel_id):
    """
    Vue pour marquer un rappel comme envoyé et envoyer l'email si nécessaire.
    """
    rappel = get_object_or_404(Rappel, pk=rappel_id)
    
    # Vérifier que le rappel est en état "planifié"
    if rappel.etat != 'planifie':
        messages.error(
            request, 
            _("Ce rappel a déjà été traité.")
        )
        return redirect('cotisations:cotisation_detail', pk=rappel.cotisation.pk)
    
    # Marquer comme envoyé
    rappel.etat = 'envoye'
    rappel.date_envoi = timezone.now()
    rappel.save()
    
    # Envoyer l'email si le type de rappel est 'email'
    if rappel.type_rappel == 'email':
        try:
            # Envoi d'email simulé ici
            # send_mail(...)
            
            messages.success(
                request, 
                _("Le rappel a été envoyé avec succès à %(email)s.") % {
                    'email': rappel.membre.email
                }
            )
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi du rappel: {str(e)}")
            rappel.etat = 'echoue'
            rappel.resultat = str(e)
            rappel.save()
            
            messages.error(
                request, 
                _("Erreur lors de l'envoi du rappel: %(error)s") % {
                    'error': str(e)
                }
            )
    else:
        messages.success(
            request, 
            _("Le rappel a été marqué comme envoyé.")
        )
    
    return redirect('cotisations:cotisation_detail', pk=rappel.cotisation.pk)


class RappelListView(StaffRequiredMixin, ListView):
    """
    Vue pour afficher la liste des rappels avec filtres.
    """
    model = Rappel
    template_name = 'cotisations/rappel_liste.html'
    context_object_name = 'rappels'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Rappel.objects.all()
        
        # Filtres disponibles
        type_rappel = self.request.GET.get('type_rappel')
        etat = self.request.GET.get('etat')
        date_debut = self.request.GET.get('date_debut')
        date_fin = self.request.GET.get('date_fin')
        membre_id = self.request.GET.get('membre_id')
        
        # Appliquer les filtres
        if type_rappel:
            queryset = queryset.filter(type_rappel=type_rappel)
            
        if etat:
            queryset = queryset.filter(etat=etat)
            
        if date_debut:
            try:
                date_debut = datetime.datetime.strptime(date_debut, '%Y-%m-%d').date()
                queryset = queryset.filter(date_envoi__gte=date_debut)
            except ValueError:
                logger.warning(f"Format de date de début invalide: {date_debut}")
                
        if date_fin:
            try:
                date_fin = datetime.datetime.strptime(date_fin, '%Y-%m-%d').date()
                queryset = queryset.filter(date_envoi__lte=date_fin)
            except ValueError:
                logger.warning(f"Format de date de fin invalide: {date_fin}")
                
        if membre_id:
            queryset = queryset.filter(membre_id=membre_id)
        
        return queryset.select_related('membre', 'cotisation')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Statistiques pour le tableau de bord
        rappels_par_etat = Rappel.objects.values('etat').annotate(count=Count('id'))
        rappels_par_type = Rappel.objects.values('type_rappel').annotate(count=Count('id'))
        
        context.update({
            'rappels_par_etat': rappels_par_etat,
            'rappels_par_type': rappels_par_type,
            'filtres': {
                'type_rappel': self.request.GET.get('type_rappel', ''),
                'etat': self.request.GET.get('etat', ''),
                'date_debut': self.request.GET.get('date_debut', ''),
                'date_fin': self.request.GET.get('date_fin', ''),
                'membre_id': self.request.GET.get('membre_id', '')
            }
        })
        
        return context


class RappelDetailView(LoginRequiredMixin, DetailView):
    """
    Vue détaillée d'un rappel.
    """
    model = Rappel
    template_name = 'cotisations/rappel_detail.html'
    context_object_name = 'rappel'
    
    def post(self, request, *args, **kwargs):
        rappel = self.get_object()
        action = request.POST.get('action')
        
        if action == 'envoyer':
            # Logique pour envoyer le rappel
            rappel.etat = RAPPEL_ETAT_ENVOYE
            rappel.date_envoi = timezone.now()
            rappel.save()
            messages.success(request, _("Le rappel a été envoyé avec succès."))
            
        elif action == 'reenvoyer':
            # Logique pour réessayer l'envoi d'un rappel échoué
            rappel.etat = RAPPEL_ETAT_ENVOYE
            rappel.date_envoi = timezone.now()
            rappel.save()
            messages.success(request, _("Le rappel a été renvoyé avec succès."))
        
        return redirect('cotisations:rappel_detail', pk=rappel.pk)


class RappelUpdateView(StaffRequiredMixin, UpdateView):
    """
    Vue pour modifier un rappel existant.
    """
    model = Rappel
    form_class = RappelForm
    template_name = 'cotisations/rappel_form.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        
        # S'assurer que self.object (le rappel) est chargé
        if not hasattr(self, 'object'):
            self.object = self.get_object()
        
        # Vérifier que la cotisation et le membre existent avant de les ajouter
        if self.object.cotisation:
            kwargs['cotisation'] = self.object.cotisation
        if self.object.membre:
            kwargs['membre'] = self.object.membre
        
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Ajouter explicitement la cotisation au contexte
        if self.object and self.object.cotisation:
            context['cotisation'] = self.object.cotisation
        return context
    
    def form_valid(self, form):
        # Vérifier que la date planifiée est dans le futur
        if form.cleaned_data.get('etat') == 'planifie':
            date_envoi = form.cleaned_data.get('date_envoi')
            if date_envoi and date_envoi <= timezone.now():
                form.add_error('date_envoi', _("La date d'envoi planifiée doit être dans le futur"))
                return self.form_invalid(form)
        
        messages.success(self.request, _("Le rappel a été modifié avec succès."))
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('cotisations:rappel_detail', kwargs={'pk': self.object.pk})


class RappelEnvoyerView(LoginRequiredMixin, View):
    """
    Vue pour envoyer un rappel (raccourci).
    """
    def get(self, request, pk):
        rappel = get_object_or_404(Rappel, pk=pk)
        
        # Vérifier si le rappel peut être envoyé
        if rappel.etat != 'planifie':
            messages.error(request, _("Ce rappel ne peut pas être envoyé car il n'est pas planifié."))
            return redirect('cotisations:rappel_detail', pk=pk)
            
        # Logique pour envoyer le rappel
        rappel.etat = 'envoye'
        rappel.date_envoi = timezone.now()
        rappel.save()
        
        # Ici, vous pourriez ajouter du code pour l'envoi réel (email, SMS, etc.)
        
        messages.success(request, _("Rappel envoyé avec succès"))
        return redirect('cotisations:rappel_detail', pk=pk)

class RappelDeleteView(StaffRequiredMixin, DeleteView):
    """
    Vue pour supprimer un rappel.
    """
    model = Rappel
    template_name = 'cotisations/rappel_confirm_delete.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['cotisation'] = self.object.cotisation
        return context
    
    def delete(self, request, *args, **kwargs):
        rappel = self.get_object()
        cotisation = rappel.cotisation
        rappel.delete()  # Suppression logique via BaseModel
        
        messages.success(
            request, 
            _("Le rappel a été supprimé avec succès.")
        )
        return redirect('cotisations:cotisation_detail', pk=cotisation.pk)

    def get_success_url(self):
        cotisation_id = self.object.cotisation.id
        return reverse('cotisations:cotisation_detail', kwargs={'pk': cotisation_id})
#
# Vues pour les barèmes de cotisation
#
class BaremeCotisationListView(StaffRequiredMixin, ListView):
    """
    Vue pour afficher la liste des barèmes de cotisation.
    """
    model = BaremeCotisation
    template_name = 'cotisations/bareme_liste.html'
    context_object_name = 'baremes'
    
    def get_queryset(self):
        return BaremeCotisation.objects.all().select_related('type_membre')
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_date'] = timezone.now().date()
        context['today'] = timezone.now().date()  # Alias pour compatibilité
        return context


class BaremeDetailView(StaffRequiredMixin, DetailView):
    """
    Vue détaillée d'un barème de cotisation.
    """
    model = BaremeCotisation
    template_name = 'cotisations/bareme_detail.html'
    context_object_name = 'bareme'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        bareme = self.object
        
        # Récupérer les cotisations utilisant ce barème
        context['cotisations'] = Cotisation.objects.filter(bareme=bareme).order_by('-date_emission')
        
        # Calculer des statistiques
        nb_cotisations = context['cotisations'].count()
        montant_total = context['cotisations'].aggregate(total=Sum('montant')).get('total') or Decimal('0.00')
        
        context.update({
            'nb_cotisations': nb_cotisations,
            'montant_total': montant_total,
            'est_actif': bareme.est_actif(),
            'type_membre': bareme.type_membre
        })
        
        return context


class BaremeCotisationCreateView(StaffRequiredMixin, CreateView):
    """
    Vue pour créer un nouveau barème de cotisation.
    """
    model = BaremeCotisation
    form_class = BaremeCotisationForm
    template_name = 'cotisations/bareme_form.html'
    success_url = reverse_lazy('cotisations:bareme_liste')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request, 
            _("Le barème de cotisation a été créé avec succès.")
        )
        return response


class BaremeCotisationUpdateView(StaffRequiredMixin, UpdateView):
    """
    Vue pour modifier un barème de cotisation existant.
    """
    model = BaremeCotisation
    form_class = BaremeCotisationForm
    template_name = 'cotisations/bareme_form.html'
    success_url = reverse_lazy('cotisations:bareme_liste')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request, 
            _("Le barème de cotisation a été modifié avec succès.")
        )
        return response


class BaremeCotisationDeleteView(StaffRequiredMixin, DeleteView):
    """
    Vue pour supprimer un barème de cotisation.
    """
    model = BaremeCotisation
    template_name = 'cotisations/bareme_confirm_delete.html'
    success_url = reverse_lazy('cotisations:bareme_liste')
    
    def delete(self, request, *args, **kwargs):
        messages.success(
            request, 
            _("Le barème de cotisation a été supprimé avec succès.")
        )
        return super().delete(request, *args, **kwargs)


@login_required
@require_POST
def bareme_reactive(request):
    """
    Vue pour réactiver un barème inactif.
    """
    if not request.user.is_staff:
        messages.error(request, _("Vous n'avez pas les permissions nécessaires."))
        return redirect('cotisations:bareme_liste')
        
    bareme_id = request.POST.get('bareme_id')
    date_fin_validite = request.POST.get('date_fin_validite') or None
    
    if not bareme_id:
        messages.error(request, _("Barème non spécifié"))
        return redirect('cotisations:bareme_liste')
    
    try:
        bareme = BaremeCotisation.objects.get(pk=bareme_id)
        
        # Convertir la date de fin si elle est fournie
        if date_fin_validite:
            try:
                date_fin_validite = datetime.datetime.strptime(date_fin_validite, '%Y-%m-%d').date()
            except ValueError:
                messages.error(request, _("Format de date invalide"))
                return redirect('cotisations:bareme_liste')
        
        # Mettre à jour la date de fin
        bareme.date_fin_validite = date_fin_validite
        bareme.save()
        
        messages.success(
            request, 
            _("Le barème pour %(type)s a été réactivé avec succès.") % {
                'type': bareme.type_membre.libelle
            }
        )
    except BaremeCotisation.DoesNotExist:
        messages.error(request, _("Barème introuvable"))
    except Exception as e:
        logger.error(f"Erreur lors de la réactivation du barème: {str(e)}")
        messages.error(request, _("Erreur lors de la réactivation du barème: %(error)s") % {'error': str(e)})
    
    return redirect('cotisations:bareme_liste')

class CotisationCorbeilleView(StaffRequiredMixin, TrashViewMixin, ListView):

    model = Cotisation
    template_name = 'cotisations/corbeille.html'
    context_object_name = 'cotisations_list'
    paginate_by = 10
    
    def get_queryset(self):
        return Cotisation.objects.only_deleted()
    
    def post(self, request, *args, **kwargs):
        selected_ids = request.POST.getlist('selected_ids')
        action = request.POST.get('action')
        
        if not selected_ids:
            messages.warning(request, _("Aucune cotisation n'a été sélectionnée."))
            return redirect('cotisations:corbeille')
        
        cotisations = Cotisation.objects.only_deleted().filter(id__in=selected_ids)
        count = cotisations.count()
        
        if action == 'restaurer':
            # Restaurer les cotisations sélectionnées
            for cotisation in cotisations:
                cotisation.restore()
            messages.success(request, _("{} cotisations ont été restaurées avec succès.").format(count))
        
        elif action == 'supprimer':
            # Supprimer définitivement les cotisations sélectionnées
            cotisations.delete(hard=True)
            messages.success(request, _("{} cotisations ont été supprimées définitivement.").format(count))
        
        return redirect('cotisations:corbeille')

class RestaurerCotisationView(StaffRequiredMixin, LoginRequiredMixin, View):
    def get(self, request, pk):
        cotisation = get_object_or_404(Cotisation.objects.only_deleted(), pk=pk)
        cotisation.restore()
        messages.success(request, _("La cotisation a été restaurée avec succès."))
        return redirect('cotisations:corbeille')

class SupprimerDefinitivementCotisationView(StaffRequiredMixin, LoginRequiredMixin, View):
    def get(self, request, pk):
        cotisation = get_object_or_404(Cotisation.objects.only_deleted(), pk=pk)
        cotisation.delete(hard=True)
        messages.success(request, _("La cotisation a été supprimée définitivement."))
        return redirect('cotisations:corbeille')

class CotisationRestoreView(StaffRequiredMixin, RestoreViewMixin, View):
    """
    Vue pour restaurer une cotisation depuis la corbeille.
    """
    model = Cotisation
    success_url = reverse_lazy('cotisations:cotisation_liste')
    
    def get_success_message(self):
        return _("La cotisation a été restaurée avec succès.")


class PaiementCorbeilleView(StaffRequiredMixin, TrashViewMixin, ListView):
    """
    Vue pour afficher les paiements supprimés (corbeille).
    """
    model = Paiement
    template_name = 'cotisations/paiement_corbeille.html'
    context_object_name = 'paiements'
    paginate_by = 20
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _("Corbeille - Paiements supprimés")
        return context


class PaiementRestoreView(StaffRequiredMixin, RestoreViewMixin, View):
    """
    Vue pour restaurer un paiement depuis la corbeille.
    """
    model = Paiement
    
    def get_success_url(self):
        return reverse('cotisations:cotisation_detail', kwargs={'pk': self.object.cotisation.pk})
    
    def get_success_message(self):
        return _("Le paiement a été restauré avec succès.")
	
#
# Vues pour l'importation des cotisations
#

class ImportCotisationsForm(forms.Form):
    """Formulaire pour l'importation de cotisations."""
    fichier = forms.FileField(
        label=_("Fichier"),
        help_text=_("Sélectionnez un fichier CSV ou Excel (.xlsx, .xls) contenant les cotisations à importer."),
        error_messages={
            'required': _("Veuillez sélectionner un fichier."),
            'invalid': _("Le fichier sélectionné n'est pas valide."),
        }
    )
    
    def clean_fichier(self):
        """Valide le fichier téléchargé."""
        fichier = self.cleaned_data.get('fichier')
        
        if fichier:
            # Vérifier l'extension du fichier
            extension = os.path.splitext(fichier.name)[1].lower()
            if extension not in ['.csv', '.xlsx', '.xls']:
                raise forms.ValidationError(
                    _("Le format du fichier n'est pas pris en charge. Utilisez CSV ou Excel (.xlsx, .xls).")
                )
            
            # Vérifier la taille du fichier (max 10 Mo)
            if fichier.size > 10 * 1024 * 1024:  # 10 Mo
                raise forms.ValidationError(
                    _("Le fichier est trop volumineux. La taille maximum est de 10 Mo.")
                )
        
        return fichier


class ImportCotisationsView(StaffRequiredMixin, TemplateView):
    """Vue pour l'importation des cotisations à partir d'un fichier CSV ou Excel."""
    template_name = 'cotisations/import.html'
    
    def get(self, request):
        """Affiche le formulaire d'importation."""
        form = ImportCotisationsForm()
        context = {
            'form': form,
        }
        return render(request, self.template_name, context)
    
    def post(self, request):
        """Traite le formulaire d'importation selon l'étape demandée."""
        # Récupérer l'étape actuelle
        step = request.POST.get('step', 'upload')
        
        if step == 'upload':
            # Étape 1: Traitement du fichier chargé
            return self._handle_file_upload(request)
        elif step == 'mapping':
            # Étape intermédiaire: Mise à jour du mappage des colonnes
            return self._handle_column_mapping(request)
        elif step == 'import':
            # Étape 2: Importation finale des données
            return self._handle_import(request)
        else:
            # Étape inconnue, rediriger vers le début
            messages.error(request, _("Étape inconnue. Veuillez recommencer."))
            return redirect('cotisations:import')
    
    def _handle_file_upload(self, request):
        """Traite le fichier chargé et prépare la prévisualisation."""
        form = ImportCotisationsForm(request.POST, request.FILES)
        
        context = {
            'form': form,
        }
        
        if not form.is_valid():
            # Formulaire invalide, réafficher avec les erreurs
            return render(request, self.template_name, context)
        
        temp_path = None  # Initialiser avant le bloc try pour pouvoir le nettoyer en cas d'erreur
        
        try:
            # Récupérer le fichier
            uploaded_file = request.FILES['fichier']
            file_name = uploaded_file.name
            
            # Créer un fichier temporaire pour stocker les données
            timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
            temp_path = f"temp_imports/{timestamp}_{file_name}"
            file_path = default_storage.save(temp_path, ContentFile(uploaded_file.read()))
            
            # Analyser le fichier pour la prévisualisation
            preview_data, total_rows, preview_headers, column_analysis, validation_issues, error = (
                self._parse_file_for_preview(file_path)
            )
            
            if error:
                # Erreur lors du parsing du fichier
                context['server_error'] = error
                context['debug_info'] = self._get_debug_info(file_path)
                
                # Nettoyer le fichier temporaire
                if default_storage.exists(file_path):
                    default_storage.delete(file_path)
                
                return render(request, self.template_name, context)
            
            # Stocker le chemin du fichier en session pour l'étape suivante
            request.session['import_file_path'] = file_path
            request.session['import_file_name'] = file_name
            
            # Déterminer le format du fichier
            file_format = "CSV" if file_name.lower().endswith('.csv') else "Excel"
            
            # Préparer les champs requis pour le mappage
            required_fields = self._prepare_required_fields(preview_headers)
            
            # Vérifier si des colonnes obligatoires sont manquantes
            column_missing = not column_analysis.get('email', False) or not column_analysis.get('montant', False)
            
            # Contexte pour le template de prévisualisation
            preview_context = {
                'preview_data': preview_data,
                'total_rows': total_rows,
                'preview_headers': preview_headers,
                'file_name': file_name,
                'file_format': file_format,
                'column_count': len(preview_headers),
                'file_id': file_path,
                'validation_issues': validation_issues,
                'detected_columns': preview_headers,
                'required_fields': required_fields,
                'column_analysis': column_analysis,
                'column_missing': column_missing,
            }
            
            # Ajouter le contexte de prévisualisation
            context.update(preview_context)
            
            return render(request, self.template_name, context)
            
        except Exception as e:
            # Erreur non prévue
            error_message = str(e)
            logger.error(f"Erreur lors de l'importation: {error_message}")
            logger.error(traceback.format_exc())
            
            # Afficher l'erreur
            context['server_error'] = _("Une erreur s'est produite lors du traitement du fichier: {}").format(error_message)
            context['debug_info'] = traceback.format_exc()
            
            # Supprimer le fichier temporaire en cas d'erreur
            if temp_path and default_storage.exists(temp_path):
                default_storage.delete(temp_path)
            
            return render(request, self.template_name, context)
    
    def _prepare_required_fields(self, preview_headers):
        """Prépare la liste des champs requis pour le mappage."""
        required_fields = [
            {'name': 'email', 'label': _('Email du membre'), 'required': True, 'mapped_to': 'email' if 'email' in preview_headers else ''},
            {'name': 'montant', 'label': _('Montant'), 'required': True, 'mapped_to': 'montant' if 'montant' in preview_headers else ''},
            {'name': 'date_emission', 'label': _('Date d\'émission'), 'required': False, 'mapped_to': 'date_emission' if 'date_emission' in preview_headers else ''},
            {'name': 'date_echeance', 'label': _('Date d\'échéance'), 'required': False, 'mapped_to': 'date_echeance' if 'date_echeance' in preview_headers else ''},
            {'name': 'type_membre', 'label': _('Type de membre'), 'required': False, 'mapped_to': 'type_membre' if 'type_membre' in preview_headers else ''},
        ]
        return required_fields
    
    def _handle_column_mapping(self, request):
        """Gère la mise à jour du mappage des colonnes."""
        file_path = request.POST.get('file_id') or request.session.get('import_file_path')
        
        if not file_path or not default_storage.exists(file_path):
            messages.error(request, _("Le fichier n'est plus disponible. Veuillez le charger à nouveau."))
            return redirect('cotisations:import')
        
        try:
            # Récupérer les mappings mis à jour
            mappings = {}
            for key, value in request.POST.items():
                if key.startswith('map_') and value:
                    field_name = key[4:]  # Supprimer 'map_'
                    mappings[field_name] = value
            
            # Stocker les mappings en session
            request.session['import_column_mappings'] = mappings
            
            # Refaire la prévisualisation avec les mappings mis à jour
            return self._refresh_preview(request, file_path, mappings)
            
        except Exception as e:
            # Erreur non prévue
            error_message = str(e)
            logger.error(f"Erreur lors du mappage: {error_message}")
            logger.error(traceback.format_exc())
            
            # Récupérer le contexte de base
            form = ImportCotisationsForm()
            context = {
                'form': form,
                'preview_error': _("Erreur lors du mappage des colonnes: {}").format(error_message),
                'debug_info': traceback.format_exc(),
            }
            
            return render(request, self.template_name, context)
    
    def _refresh_preview(self, request, file_path, mappings=None):
        """Rafraîchit la prévisualisation après mise à jour du mappage."""
        file_name = request.session.get('import_file_name', os.path.basename(file_path))
        
        try:
            # Analyser à nouveau le fichier avec les mappings mis à jour
            preview_data, total_rows, preview_headers, column_analysis, validation_issues, error = self._parse_file_for_preview(
                file_path, 
                mappings=mappings or request.session.get('import_column_mappings', {})
            )
            
            if error:
                # Erreur lors du parsing du fichier
                form = ImportCotisationsForm()
                context = {
                    'form': form,
                    'preview_error': error,
                    'debug_info': self._get_debug_info(file_path),
                }
                return render(request, self.template_name, context)
            
            # Déterminer le format du fichier
            file_format = "CSV" if file_name.lower().endswith('.csv') else "Excel"
            
            # Préparer les champs requis pour le mappage avec les mappings mis à jour
            required_fields = self._prepare_mapped_fields(preview_headers, mappings)
            
            # Vérifier si des colonnes obligatoires sont manquantes après mappage
            mapped_columns = [field['mapped_to'] for field in required_fields if field['required']]
            column_missing = any(not col for col in mapped_columns)
            
            # Contexte pour le template de prévisualisation
            form = ImportCotisationsForm()
            context = {
                'form': form,
                'preview_data': preview_data,
                'total_rows': total_rows,
                'preview_headers': preview_headers,
                'file_name': file_name,
                'file_format': file_format,
                'column_count': len(preview_headers),
                'file_id': file_path,
                'validation_issues': validation_issues,
                'detected_columns': preview_headers,
                'required_fields': required_fields,
                'column_analysis': column_analysis,
                'column_missing': column_missing,
            }
            
            return render(request, self.template_name, context)
            
        except Exception as e:
            # Erreur non prévue
            error_message = str(e)
            logger.error(f"Erreur lors du rafraîchissement de la prévisualisation: {error_message}")
            logger.error(traceback.format_exc())
            
            # Récupérer le contexte de base
            form = ImportCotisationsForm()
            context = {
                'form': form,
                'preview_error': _("Erreur lors du rafraîchissement de la prévisualisation: {}").format(error_message),
                'debug_info': traceback.format_exc(),
            }
            
            return render(request, self.template_name, context)
    
    def _prepare_mapped_fields(self, preview_headers, mappings=None):
        """Prépare les champs requis avec les mappings appliqués."""
        required_fields = [
            {'name': 'email', 'label': _('Email du membre'), 'required': True, 
             'mapped_to': mappings.get('email', 'email') if mappings else ('email' if 'email' in preview_headers else '')},
            {'name': 'montant', 'label': _('Montant'), 'required': True, 
             'mapped_to': mappings.get('montant', 'montant') if mappings else ('montant' if 'montant' in preview_headers else '')},
            {'name': 'date_emission', 'label': _('Date d\'émission'), 'required': False, 
             'mapped_to': mappings.get('date_emission', 'date_emission') if mappings else ('date_emission' if 'date_emission' in preview_headers else '')},
            {'name': 'date_echeance', 'label': _('Date d\'échéance'), 'required': False, 
             'mapped_to': mappings.get('date_echeance', 'date_echeance') if mappings else ('date_echeance' if 'date_echeance' in preview_headers else '')},
            {'name': 'type_membre', 'label': _('Type de membre'), 'required': False, 
             'mapped_to': mappings.get('type_membre', 'type_membre') if mappings else ('type_membre' if 'type_membre' in preview_headers else '')},
        ]
        return required_fields
    
    def _handle_import(self, request):
        """Importe les données du fichier dans la base de données."""
        file_path = request.POST.get('file_id') or request.session.get('import_file_path')
        force_import = request.POST.get('force_import') == '1'
        
        if not file_path or not default_storage.exists(file_path):
            messages.error(request, _("Le fichier n'est plus disponible. Veuillez le charger à nouveau."))
            return redirect('cotisations:import')
        
        try:
            # Récupérer les mappings
            mappings = request.session.get('import_column_mappings', {})
            
            # Importer les données
            results = self._import_data(file_path, mappings, force_import)
            
            # Supprimer le fichier temporaire après importation
            if default_storage.exists(file_path):
                default_storage.delete(file_path)
            
            # Nettoyer la session
            for key in ['import_file_path', 'import_file_name', 'import_column_mappings']:
                if key in request.session:
                    del request.session[key]
            
            # Préparer le contexte pour la page de résultats
            form = ImportCotisationsForm()
            context = {
                'form': form,
                'import_completed': True,
                'results': results,
            }
            
            return render(request, self.template_name, context)
            
        except Exception as e:
            # Erreur non prévue
            error_message = str(e)
            logger.error(f"Erreur lors de l'importation finale: {error_message}")
            logger.error(traceback.format_exc())
            
            # Récupérer le contexte de base
            form = ImportCotisationsForm()
            context = {
                'form': form,
                'import_completed': True,
                'import_error': _("Une erreur s'est produite lors de l'importation: {}").format(error_message),
                'debug_info': traceback.format_exc(),
                'results': {
                    'success': 0,
                    'errors': 0,
                    'total': 0,
                    'details': [],
                }
            }
            
            # S'assurer que le fichier temporaire est supprimé
            if file_path and default_storage.exists(file_path):
                default_storage.delete(file_path)
            
            return render(request, self.template_name, context)
    
    def _parse_file_for_preview(self, file_path, max_rows=50, mappings=None):
        """Parse le fichier pour la prévisualisation et la validation."""
        try:
            file_extension = os.path.splitext(file_path)[1].lower()
            
            if file_extension == '.csv':
                return self._parse_csv_for_preview(file_path, max_rows, mappings)
            elif file_extension in ['.xls', '.xlsx']:
                if not PANDAS_AVAILABLE:
                    return [], 0, [], {}, [], _("Le support des fichiers Excel nécessite pandas. Veuillez l'installer ou utiliser un fichier CSV.")
                return self._parse_excel_for_preview(file_path, max_rows, mappings)
            else:
                return [], 0, [], {}, [], _("Format de fichier non pris en charge.")
        except Exception as e:
            logger.error(f"Erreur lors du parsing du fichier: {str(e)}")
            logger.error(traceback.format_exc())
            return [], 0, [], {}, [], _("Erreur lors de l'analyse du fichier: {}").format(str(e))
    
    def _parse_csv_for_preview(self, file_path, max_rows=50, mappings=None):
        """Parse un fichier CSV pour la prévisualisation."""
        preview_data = []
        validation_issues = []
        
        try:
            # Ouvrir le fichier en mode binaire puis le décoder manuellement
            with default_storage.open(file_path, 'rb') as binary_file:
                # Wrapper pour décoder avec l'encodage approprié
                f = io.TextIOWrapper(binary_file, encoding='utf-8')
                
                # Essayer de détecter le délimiteur
                sample = f.read(4096)
                f.seek(0)
                
                # Compter les occurrences des délimiteurs courants
                delimiter_counts = {
                    ',': sample.count(','),
                    ';': sample.count(';'),
                    '\t': sample.count('\t'),
                }
                
                # Choisir le délimiteur avec le plus d'occurrences
                delimiter = max(delimiter_counts.items(), key=lambda x: x[1])[0]
                
                # Si aucun délimiteur n'a suffisamment d'occurrences, utiliser la virgule par défaut
                if delimiter_counts[delimiter] < 3:
                    delimiter = ','
                
                # Lire le CSV
                reader = csv.reader(f, delimiter=delimiter)
                headers = next(reader)  # Première ligne = en-têtes
                
                # Normaliser les en-têtes (supprimer espaces, minuscules)
                headers = [h.strip().lower() for h in headers]
                
                # Analyser les colonnes
                column_analysis = self._analyze_columns(headers)
                
                # Si des mappings sont fournis, remapper les en-têtes
                headers_mapping = {}
                if mappings:
                    for field, column in mappings.items():
                        if column in headers:
                            headers_mapping[column] = field
                
                # Compteur de lignes et liste pour les données de prévisualisation
                row_count = 0
                
                for i, row in enumerate(reader, start=2):  # Commencer à 2 car la ligne 1 est l'en-tête
                    row_count += 1
                    
                    # S'assurer que la ligne a le bon nombre de colonnes
                    if len(row) < len(headers):
                        row.extend([''] * (len(headers) - len(row)))
                    elif len(row) > len(headers):
                        row = row[:len(headers)]
                    
                    # Préparer les données pour la validation
                    row_data = dict(zip(headers, row))
                    
                    # Appliquer les mappings si présents
                    if mappings:
                        mapped_data = {}
                        for field, column in mappings.items():
                            if column in row_data:
                                mapped_data[field] = row_data[column]
                        row_data = mapped_data if mapped_data else row_data
                    
                    # Valider la ligne
                    row_issues = self._validate_row(row_data, i)
                    has_issue = len(row_issues) > 0
                    
                    # Ajouter les problèmes à la liste globale
                    validation_issues.extend(row_issues)
                    
                    # Ajouter à la prévisualisation si dans la limite
                    if i <= max_rows:
                        preview_data.append({
                            'row_num': i,
                            'data': row,
                            'has_issue': has_issue
                        })
                
                return preview_data, row_count + 1, headers, column_analysis, validation_issues, None
                
        except Exception as e:
            logger.error(f"Erreur lors du parsing CSV: {str(e)}")
            logger.error(traceback.format_exc())
            return [], 0, [], {}, [], _("Erreur lors de l'analyse du fichier CSV: {}").format(str(e))
    
    def _parse_excel_for_preview(self, file_path, max_rows=50, mappings=None):
        """Parse un fichier Excel pour la prévisualisation."""
        preview_data = []
        validation_issues = []
        
        try:
            # Ouvrir le fichier avec pandas
            df = pd.read_excel(default_storage.path(file_path), nrows=max_rows + 1)
            
            # Obtenir les en-têtes
            headers = [str(col).strip().lower() for col in df.columns]
            
            # Analyser les colonnes
            column_analysis = self._analyze_columns(headers)
            
            # Prévisualisation des données (jusqu'à max_rows)
            for i, (_, row) in enumerate(df.iterrows(), start=2):  # Commencer à 2 car la ligne 1 est l'en-tête
                # Convertir la ligne en liste
                row_data = [str(val) if not pd.isna(val) else '' for val in row]
                
                # Préparer les données pour la validation
                row_dict = dict(zip(headers, row_data))
                
                # Appliquer les mappings si présents
                if mappings:
                    mapped_data = {}
                    for field, column in mappings.items():
                        if column in row_dict:
                            mapped_data[field] = row_dict[column]
                    row_dict = mapped_data if mapped_data else row_dict
                
                # Valider la ligne
                row_issues = self._validate_row(row_dict, i)
                has_issue = len(row_issues) > 0
                
                # Ajouter les problèmes à la liste globale
                validation_issues.extend(row_issues)
                
                # Ajouter à la prévisualisation
                preview_data.append({
                    'row_num': i,
                    'data': row_data,
                    'has_issue': has_issue
                })
            
            # Obtenir le nombre total de lignes (en incluant l'en-tête)
            total_rows = len(df) + 1
            
            return preview_data, total_rows, headers, column_analysis, validation_issues, None
            
        except Exception as e:
            logger.error(f"Erreur lors du parsing Excel: {str(e)}")
            logger.error(traceback.format_exc())
            return [], 0, [], {}, [], _("Erreur lors de l'analyse du fichier Excel: {}").format(str(e))
    
    def _analyze_columns(self, headers):
        """Analyse les colonnes du fichier pour vérifier la présence des colonnes requises."""
        columns = {
            'email': False,
            'montant': False,
            'date_emission': False,
            'date_echeance': False,
            'type_membre': False,
        }
        
        # Normaliser les en-têtes et vérifier la présence des colonnes requises
        normalized_headers = [h.strip().lower() for h in headers]
        
        for col in columns.keys():
            if col in normalized_headers:
                columns[col] = True
        
        # Vérifier aussi des variantes courantes
        if not columns['email'] and any(h in normalized_headers for h in ['mail', 'courriel', 'e-mail', 'e_mail']):
            columns['email'] = True
        
        if not columns['montant'] and any(h in normalized_headers for h in ['amount', 'somme', 'prix', 'tarif']):
            columns['montant'] = True
        
        if not columns['date_emission'] and any(h in normalized_headers for h in ['emission', 'émission', 'date_creation', 'created_at']):
            columns['date_emission'] = True
        
        if not columns['date_echeance'] and any(h in normalized_headers for h in ['echeance', 'échéance', 'date_fin', 'expiration']):
            columns['date_echeance'] = True
        
        if not columns['type_membre'] and any(h in normalized_headers for h in ['type', 'categorie', 'catégorie', 'membership_type']):
            columns['type_membre'] = True
        
        return columns
    
    def _validate_row(self, row_data, row_num):
        """Valide une ligne de données et retourne les problèmes trouvés."""
        issues = []
        
        # Vérifier l'email
        email = row_data.get('email', '')
        if not email:
            issues.append({
                'row': row_num,
                'type': _("Email manquant"),
                'message': _("L'email est obligatoire.")
            })
        elif '@' not in email or '.' not in email:
            issues.append({
                'row': row_num,
                'type': _("Email invalide"),
                'message': _("L'email '{}' ne semble pas valide.").format(email)
            })
        else:
            # Vérifier si le membre existe
            try:
                membre = Membre.objects.filter(email=email).first()
                if not membre:
                    issues.append({
                        'row': row_num,
                        'type': _("Membre introuvable"),
                        'message': _("Aucun membre trouvé avec l'email '{}'.").format(email)
                    })
            except Exception:
                # Ignorer les erreurs de base de données lors de la validation préliminaire
                pass
        
        # Vérifier le montant
        montant = row_data.get('montant', '')
        if not montant:
            issues.append({
                'row': row_num,
                'type': _("Montant manquant"),
                'message': _("Le montant est obligatoire.")
            })
        else:
            # Nettoyer le montant (remplacer la virgule par un point)
            montant = str(montant).replace(',', '.')
            try:
                montant_decimal = Decimal(montant)
                if montant_decimal <= 0:
                    issues.append({
                        'row': row_num,
                        'type': _("Montant invalide"),
                        'message': _("Le montant doit être supérieur à zéro.")
                    })
            except (InvalidOperation, ValueError, TypeError):
                issues.append({
                    'row': row_num,
                    'type': _("Montant invalide"),
                    'message': _("Le montant '{}' n'est pas un nombre valide.").format(montant)
                })
        
        # Vérifier les dates si présentes
        date_emission = row_data.get('date_emission', '')
        if date_emission:
            try:
                self._parse_date(date_emission)
            except ValueError:
                issues.append({
                    'row': row_num,
                    'type': _("Date d'émission invalide"),
                    'message': _("La date d'émission '{}' n'est pas au format valide (YYYY-MM-DD ou DD/MM/YYYY).").format(date_emission)
                })
        
        date_echeance = row_data.get('date_echeance', '')
        if date_echeance:
            try:
                self._parse_date(date_echeance)
            except ValueError:
                issues.append({
                    'row': row_num,
                    'type': _("Date d'échéance invalide"),
                    'message': _("La date d'échéance '{}' n'est pas au format valide (YYYY-MM-DD ou DD/MM/YYYY).").format(date_echeance)
                })
        
        # Vérifier le type de membre si présent
        type_membre = row_data.get('type_membre', '')
        if type_membre:
            try:
                type_membre_obj = TypeMembre.objects.filter(libelle__iexact=type_membre).first()
                if not type_membre_obj:
                    issues.append({
                        'row': row_num,
                        'type': _("Type de membre invalide"),
                        'message': _("Le type de membre '{}' n'existe pas dans la base de données.").format(type_membre)
                    })
            except Exception:
                # Ignorer les erreurs de base de données lors de la validation préliminaire
                pass
        
        return issues
		
    def _import_data(self, file_path, mappings, force_import=False):
            """Importe les données du fichier dans la base de données."""
            results = {
                'success': 0,
                'errors': 0,
                'total': 0,
                'details': []
            }
            
            try:
                # Déterminer le type de fichier
                file_extension = os.path.splitext(file_path)[1].lower()
                
                # Statut par défaut pour les nouvelles cotisations
                default_status = Statut.objects.filter(nom__iexact='En attente').first()
                if not default_status:
                    default_status = Statut.objects.create(
                        nom='En attente', 
                        description='Statut par défaut pour les cotisations'
                    )
                
                # Parser le fichier selon son type
                if file_extension == '.csv':
                    self._import_from_csv(file_path, mappings, results, default_status, force_import)
                elif file_extension in ['.xls', '.xlsx']:
                    if not PANDAS_AVAILABLE:
                        raise ImportError(_("Le support des fichiers Excel nécessite pandas. Veuillez l'installer ou utiliser un fichier CSV."))
                    self._import_from_excel(file_path, mappings, results, default_status, force_import)
                else:
                    raise ValueError(_("Format de fichier non pris en charge."))
                
                # Mettre à jour le total
                results['total'] = results['success'] + results['errors']
                
                return results
                
            except Exception as e:
                logger.error(f"Erreur lors de l'importation des données: {str(e)}")
                logger.error(traceback.format_exc())
                raise
    
    def _import_from_csv(self, file_path, mappings, results, default_status, force_import):
        """Importe les données à partir d'un fichier CSV."""
        try:
            # Ouvrir le fichier en mode binaire puis le décoder manuellement
            with default_storage.open(file_path, 'rb') as binary_file:
                # Wrapper pour décoder avec l'encodage approprié
                f = io.TextIOWrapper(binary_file, encoding='utf-8')
                
                # Essayer de détecter le délimiteur
                sample = f.read(4096)
                f.seek(0)
                
                # Compter les occurrences des délimiteurs courants
                delimiter_counts = {
                    ',': sample.count(','),
                    ';': sample.count(';'),
                    '\t': sample.count('\t'),
                }
                
                # Choisir le délimiteur avec le plus d'occurrences
                delimiter = max(delimiter_counts.items(), key=lambda x: x[1])[0]
                
                # Si aucun délimiteur n'a suffisamment d'occurrences, utiliser la virgule par défaut
                if delimiter_counts[delimiter] < 3:
                    delimiter = ','
                
                # Lire le CSV
                reader = csv.reader(f, delimiter=delimiter)
                headers = next(reader)  # Première ligne = en-têtes
                
                # Normaliser les en-têtes (supprimer espaces, minuscules)
                headers = [h.strip().lower() for h in headers]
                
                # Traiter chaque ligne
                for i, row in enumerate(reader, start=2):  # Commencer à 2 car la ligne 1 est l'en-tête
                    # S'assurer que la ligne a le bon nombre de colonnes
                    if len(row) < len(headers):
                        row.extend([''] * (len(headers) - len(row)))
                    elif len(row) > len(headers):
                        row = row[:len(headers)]
                    
                    # Créer un dictionnaire pour la ligne
                    row_data = dict(zip(headers, row))
                    
                    # Appliquer les mappings
                    if mappings:
                        mapped_data = {}
                        for field, column in mappings.items():
                            if column in row_data:
                                mapped_data[field] = row_data[column]
                        
                        if mapped_data:
                            row_data = mapped_data
                    
                    # Traiter la ligne
                    self._process_row(row_data, i, results, default_status, force_import)
    
        except Exception as e:
            logger.error(f"Erreur lors de l'importation CSV: {str(e)}")
            logger.error(traceback.format_exc())
            raise
    
    def _import_from_excel(self, file_path, mappings, results, default_status, force_import):
        """Importe les données à partir d'un fichier Excel."""
        try:
            # Ouvrir le fichier avec pandas
            df = pd.read_excel(default_storage.path(file_path))
            
            # Obtenir les en-têtes
            headers = [str(col).strip().lower() for col in df.columns]
            
            # Traiter chaque ligne
            for i, (_, row) in enumerate(df.iterrows(), start=2):  # Commencer à 2 car la ligne 1 est l'en-tête
                # Convertir les valeurs nan en chaînes vides
                row_data = {headers[j]: ('' if pd.isna(val) else str(val)) for j, val in enumerate(row)}
                
                # Appliquer les mappings
                if mappings:
                    mapped_data = {}
                    for field, column in mappings.items():
                        if column in row_data:
                            mapped_data[field] = row_data[column]
                    
                    if mapped_data:
                        row_data = mapped_data
                
                # Traiter la ligne
                self._process_row(row_data, i, results, default_status, force_import)
        
        except Exception as e:
            logger.error(f"Erreur lors de l'importation Excel: {str(e)}")
            logger.error(traceback.format_exc())
            raise
    
    def _process_row(self, row_data, row_num, results, default_status, force_import):
        """Traite une ligne pour l'importation."""
        try:
            # Vérifier si toutes les données nécessaires sont présentes
            email = row_data.get('email', '').strip()
            montant_str = str(row_data.get('montant', '')).strip().replace(',', '.')
            
            # Vérifier les données obligatoires
            if not email:
                self._add_error_detail(results, row_num, _("Email manquant"))
                return
            
            if not montant_str:
                self._add_error_detail(results, row_num, _("Montant manquant"))
                return
            
            # Convertir le montant
            try:
                montant = Decimal(montant_str)
                if montant <= 0:
                    self._add_error_detail(results, row_num, _("Le montant doit être supérieur à zéro"))
                    return
            except (InvalidOperation, ValueError, TypeError):
                self._add_error_detail(results, row_num, _("Montant invalide: {}").format(montant_str))
                return
            
            # Trouver le membre
            membre = Membre.objects.filter(email=email).first()
            
            # Si le membre n'existe pas, essayer de le créer
            if not membre and force_import:
                membre = self._create_membre_from_row(row_data, email)
                if not membre:
                    self._add_error_detail(
                        results, row_num, 
                        _("Impossible de créer le membre avec l'email '{}'").format(email),
                        email=email, montant=montant
                    )
                    return
            
            # Si le membre n'existe toujours pas
            if not membre:
                self._add_error_detail(
                    results, row_num,
                    _("Membre introuvable avec l'email '{}'").format(email),
                    email=email, montant=montant
                )
                return
            
            # Traiter les dates
            date_emission, date_echeance = self._get_dates_from_row(row_data, force_import)
            if date_emission is None and not force_import:
                self._add_error_detail(
                    results, row_num,
                    _("Date d'émission invalide: {}").format(row_data.get('date_emission', '')),
                    membre=membre, montant=montant
                )
                return
            
            if date_echeance is None and 'date_echeance' in row_data and row_data['date_echeance'] and not force_import:
                self._add_error_detail(
                    results, row_num,
                    _("Date d'échéance invalide: {}").format(row_data['date_echeance']),
                    membre=membre, montant=montant
                )
                return
            
            # Trouver le type de membre
            type_membre = self._get_type_membre(row_data, membre, force_import)
            if type_membre is None and 'type_membre' in row_data and row_data['type_membre'] and not force_import:
                self._add_error_detail(
                    results, row_num,
                    _("Type de membre non trouvé: {}").format(row_data['type_membre']),
                    membre=membre, montant=montant
                )
                return
            
            # Récupérer le montant restant et déterminer le statut de paiement
            montant_restant, statut_paiement = self._get_payment_details(row_data, montant)
            
            # Créer la cotisation
            try:
                cotisation = self._create_cotisation(
                    membre, montant, montant_restant, statut_paiement,
                    default_status, date_emission, date_echeance, type_membre
                )
                
                # Succès !
                membre_info = f"{membre.prenom} {membre.nom} ({membre.email})"
                results['success'] += 1
                results['details'].append({
                    'row': row_num,
                    'status': 'success',
                    'membre': membre_info,
                    'montant': float(montant),
                    'message': _("Cotisation créée avec succès")
                })
                
            except Exception as e:
                logger.error(f"Erreur lors de la création de la cotisation: {str(e)}")
                logger.error(traceback.format_exc())
                
                membre_info = f"{membre.prenom} {membre.nom} ({membre.email})" if membre else email
                self._add_error_detail(
                    results, row_num,
                    _("Erreur lors de la création: {}").format(str(e)),
                    membre=membre_info, montant=montant
                )
        
        except Exception as e:
            logger.error(f"Erreur lors du traitement de la ligne {row_num}: {str(e)}")
            logger.error(traceback.format_exc())
            
            self._add_error_detail(results, row_num, _("Erreur inattendue: {}").format(str(e)))
    
    def _add_error_detail(self, results, row_num, message, **kwargs):
        """Ajoute une erreur détaillée aux résultats."""
        results['errors'] += 1
        
        # Créer un dictionnaire de détails
        detail = {
            'row': row_num,
            'status': 'error',
            'message': message
        }
        
        # Ajouter les kwargs comme informations supplémentaires
        for key, value in kwargs.items():
            if isinstance(value, Decimal):
                detail[key] = float(value)
            else:
                detail[key] = value
        
        results['details'].append(detail)
    
    def _create_membre_from_row(self, row_data, email):
        """Crée un nouveau membre à partir des données de la ligne."""
        try:
            # Extraire les informations du membre
            nom_prenom = row_data.get('membre', '').strip()
            
            # Diviser le nom complet en nom et prénom
            if nom_prenom:
                parts = nom_prenom.split(' ', 1)
                if len(parts) > 1:
                    prenom, nom = parts
                else:
                    nom = parts[0]
                    prenom = ""
            else:
                # Si le nom n'est pas fourni, utiliser l'email comme base
                nom = email.split('@')[0]
                prenom = ""
            
            # Créer le statut par défaut pour les membres si nécessaire
            membre_statut = Statut.objects.filter(nom__iexact='Actif').first()
            if not membre_statut:
                membre_statut = Statut.objects.create(
                    nom='Actif', 
                    description='Statut par défaut pour les membres'
                )
            
            # Créer le nouveau membre
            membre = Membre.objects.create(
                nom=nom.upper() if nom else "NOM",
                prenom=prenom.capitalize() if prenom else "Prénom",
                email=email,
                statut=membre_statut,
                date_adhesion=datetime.datetime.now().date()
            )
            
            # Récupérer et assigner le type de membre si disponible
            type_membre_nom = row_data.get('type_membre', '').strip()
            if type_membre_nom:
                type_membre = TypeMembre.objects.filter(libelle__iexact=type_membre_nom).first()
                if type_membre:
                    # Créer une association entre le membre et le type de membre
                    # Note: ceci dépend de la structure du modèle MembreTypeMembre
                    MembreTypeMembre.objects.create(
                        membre=membre,
                        type_membre=type_membre,
                        date_debut=datetime.datetime.now().date()
                    )
            
            logger.info(f"Membre créé automatiquement: {email}")
            return membre
            
        except Exception as e:
            # En cas d'erreur lors de la création du membre
            logger.error(f"Erreur lors de la création automatique du membre: {str(e)}")
            logger.error(traceback.format_exc())
            return None
    
    def _get_dates_from_row(self, row_data, force_import):
        """Extrait et valide les dates d'une ligne."""
        date_emission = None
        date_echeance = None
        
        # Traiter la date d'émission
        if 'date_emission' in row_data and row_data['date_emission']:
            try:
                date_emission = self._parse_date(row_data['date_emission'])
            except ValueError:
                if force_import:
                    # Utiliser la date actuelle si force_import est activé
                    date_emission = datetime.datetime.now().date()
                else:
                    return None, None
        else:
            # Par défaut, utiliser la date actuelle
            date_emission = datetime.datetime.now().date()
        
        # Traiter la date d'échéance
        if 'date_echeance' in row_data and row_data['date_echeance']:
            try:
                date_echeance = self._parse_date(row_data['date_echeance'])
            except ValueError:
                if force_import:
                    # Par défaut, la date d'échéance est à 1 an de la date d'émission
                    date_echeance = date_emission.replace(year=date_emission.year + 1)
                else:
                    return date_emission, None
        else:
            # Par défaut, la date d'échéance est à 1 an de la date d'émission
            date_echeance = date_emission.replace(year=date_emission.year + 1)
        
        return date_emission, date_echeance
    
    def _get_type_membre(self, row_data, membre, force_import):
        """Récupère le type de membre à partir des données de la ligne ou du membre."""
        # Essayer d'abord à partir des données de la ligne
        if 'type_membre' in row_data and row_data['type_membre']:
            type_membre = TypeMembre.objects.filter(libelle__iexact=row_data['type_membre'].strip()).first()
            if type_membre:
                return type_membre
        
        # Si pas dans les données ou pas trouvé, essayer à partir du membre
        if membre:
            # Approche 1: Relations type active via MembreTypeMembre
            membre_types = MembreTypeMembre.objects.filter(
                membre=membre,
                date_fin__isnull=True
            ).select_related('type_membre').first()
            
            if membre_types:
                return membre_types.type_membre
            
            # Approche 2: Types actifs via une méthode du modèle
            if hasattr(membre, 'get_types_actifs') and callable(membre.get_types_actifs):
                types_actifs = membre.get_types_actifs()
                if types_actifs.exists():
                    return types_actifs.first()
        
        # Si force_import est activé, utiliser le type de membre par défaut
        if force_import:
            # Trouver ou créer un type par défaut
            default_type = TypeMembre.objects.filter(libelle__iexact='Standard').first()
            if not default_type:
                default_type = TypeMembre.objects.first()  # Prendre le premier type disponible
            
            return default_type
        
        return None
    
    def _get_payment_details(self, row_data, montant):
        """Récupère les détails de paiement à partir des données de la ligne."""
        # Montant restant par défaut = montant total
        montant_restant = montant
        
        # Récupérer le montant restant s'il est spécifié
        if 'montant_restant' in row_data and row_data['montant_restant']:
            try:
                montant_restant_str = str(row_data['montant_restant']).strip().replace(',', '.')
                montant_restant = Decimal(montant_restant_str)
                # Valider le montant restant
                if montant_restant < 0:
                    montant_restant = Decimal('0.00')
                elif montant_restant > montant:
                    montant_restant = montant
            except (InvalidOperation, ValueError, TypeError):
                # En cas d'erreur dans le format, utiliser le montant total
                pass
        
        # Déterminer le statut de paiement
        statut_paiement = 'non_payee'  # Par défaut
        
        if 'statut_paiement' in row_data and row_data['statut_paiement']:
            statut_str = row_data['statut_paiement'].strip().lower()
            
            if 'payée' in statut_str or 'payee' in statut_str or 'pay' in statut_str:
                if 'partiel' in statut_str or 'partial' in statut_str:
                    statut_paiement = 'partiellement_payee'
                    # Si le montant restant n'a pas été explicitement défini
                    if montant_restant == montant:
                        montant_restant = montant * Decimal('0.5')  # 50% par défaut
                else:
                    statut_paiement = 'payee'
                    montant_restant = Decimal('0')
        
        # Si le montant restant est 0, la cotisation est payée
        if montant_restant == 0:
            statut_paiement = 'payee'
        # Si le montant restant est entre 0 et le montant total, partiellement payée
        elif montant_restant < montant:
            statut_paiement = 'partiellement_payee'
        
        return montant_restant, statut_paiement
    
    def _create_cotisation(self, membre, montant, montant_restant, statut_paiement, 
                         statut, date_emission, date_echeance, type_membre):
        """Crée une nouvelle cotisation avec les données fournies."""
        # Préparer les données pour la cotisation
        cotisation_data = {
            'membre': membre,
            'montant': montant,
            'montant_restant': montant_restant,
            'statut': statut,
            'statut_paiement': statut_paiement,
        }
        
        # Ajouter les champs optionnels si présents
        if date_emission:
            cotisation_data['date_emission'] = date_emission
        
        if date_echeance:
            cotisation_data['date_echeance'] = date_echeance
        
        # Ajouter les périodes
        if date_emission:
            cotisation_data['periode_debut'] = date_emission
            cotisation_data['mois'] = date_emission.month
            cotisation_data['annee'] = date_emission.year
        
        if date_echeance:
            cotisation_data['periode_fin'] = date_echeance
        
        # Ajouter le type de membre si présent
        if type_membre:
            cotisation_data['type_membre'] = type_membre
        
        # Créer la cotisation
        cotisation = Cotisation.objects.create(**cotisation_data)
        return cotisation
    
    def _parse_date(self, date_str):
        """Parse une date à partir d'une chaîne de caractères."""
        date_str = str(date_str).strip()
        
        # Essayer différents formats de date
        formats = [
            '%Y-%m-%d',       # YYYY-MM-DD
            '%d/%m/%Y',       # DD/MM/YYYY
            '%d-%m-%Y',       # DD-MM-YYYY
            '%m/%d/%Y',       # MM/DD/YYYY (format US)
            '%d.%m.%Y',       # DD.MM.YYYY
        ]
        
        for fmt in formats:
            try:
                return datetime.datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        
        # Si on arrive ici, aucun format n'a fonctionné
        raise ValueError(f"Format de date non reconnu: {date_str}")
    
    def _get_debug_info(self, file_path):
        """Récupère des informations de débogage sur le fichier."""
        try:
            info = []
            
            # Informations sur le fichier
            file_exists = default_storage.exists(file_path)
            info.append(f"Fichier existe: {file_exists}")
            
            if file_exists:
                file_size = default_storage.size(file_path)
                info.append(f"Taille du fichier: {file_size} octets")
                
                # Extension du fichier
                file_extension = os.path.splitext(file_path)[1].lower()
                info.append(f"Extension du fichier: {file_extension}")
                
                # Pour les fichiers CSV, essayer de lire les premières lignes
                if file_extension == '.csv':
                    try:
                        with default_storage.open(file_path, 'rb') as binary_file:
                            # Décoder le fichier
                            f = io.TextIOWrapper(binary_file, encoding='utf-8')
                            lines = [f.readline() for _ in range(5)]
                            info.append("Premières lignes du fichier:")
                            for i, line in enumerate(lines):
                                if line:
                                    info.append(f"Ligne {i+1}: {line.strip()}")
                    except Exception as e:
                        info.append(f"Erreur lors de la lecture des premières lignes: {str(e)}")
                
                # Pour les fichiers Excel, essayer de lire avec pandas
                elif file_extension in ['.xls', '.xlsx'] and PANDAS_AVAILABLE:
                    try:
                        df = pd.read_excel(default_storage.path(file_path), nrows=5)
                        info.append(f"En-têtes du fichier: {', '.join(map(str, df.columns))}")
                        info.append(f"Nombre de lignes lues: {len(df)}")
                    except Exception as e:
                        info.append(f"Erreur lors de la lecture avec pandas: {str(e)}")
            
            return "\n".join(info)
        
        except Exception as e:
            return f"Erreur lors de la récupération des informations de débogage: {str(e)}"


#
# Vues pour l'exportation des cotisations et paiements
#
class ExportCotisationsView(StaffRequiredMixin, View):
    """
    Vue pour exporter la liste des cotisations au format CSV ou Excel.
    """
    def get(self, request, *args, **kwargs):
        format_export = request.GET.get('format', 'csv')
        
        # Récupérer les filtres de recherche pour les appliquer à l'export
        form = CotisationSearchForm(request.GET)
        queryset = Cotisation.objects.all()
        
        if form.is_valid():
            # Appliquer les mêmes filtres que pour la vue liste
            queryset = self._apply_search_filters(form, queryset)
        
        # Charger les relations pour optimiser les performances
        queryset = queryset.select_related('membre', 'type_membre')
        
        # Selon le format demandé
        if format_export == 'csv':
            return self._export_csv(queryset)
        elif format_export == 'excel':
            return self._export_excel(queryset)
        else:
            return HttpResponse(_("Format non supporté"), status=400)
    
    def _apply_search_filters(self, form, queryset):
        """Applique les filtres de recherche au queryset."""
        if membre := form.cleaned_data.get('membre'):
            queryset = queryset.filter(membre=membre)
        
        if type_membre := form.cleaned_data.get('type_membre'):
            queryset = queryset.filter(type_membre=type_membre)
        
        if statut_paiement := form.cleaned_data.get('statut_paiement'):
            queryset = queryset.filter(statut_paiement=statut_paiement)
        
        if date_emission_debut := form.cleaned_data.get('date_emission_debut'):
            queryset = queryset.filter(date_emission__gte=date_emission_debut)
        
        if date_emission_fin := form.cleaned_data.get('date_emission_fin'):
            queryset = queryset.filter(date_emission__lte=date_emission_fin)
        
        if date_echeance_debut := form.cleaned_data.get('date_echeance_debut'):
            queryset = queryset.filter(date_echeance__gte=date_echeance_debut)
        
        if date_echeance_fin := form.cleaned_data.get('date_echeance_fin'):
            queryset = queryset.filter(date_echeance__lte=date_echeance_fin)
        
        if montant_min := form.cleaned_data.get('montant_min'):
            queryset = queryset.filter(montant__gte=montant_min)
        
        if montant_max := form.cleaned_data.get('montant_max'):
            queryset = queryset.filter(montant__lte=montant_max)
        
        if annee := form.cleaned_data.get('annee'):
            queryset = queryset.filter(annee=annee)
        
        if mois := form.cleaned_data.get('mois'):
            queryset = queryset.filter(mois=int(mois))
        
        if reference := form.cleaned_data.get('reference'):
            queryset = queryset.filter(reference__icontains=reference)
        
        if en_retard := form.cleaned_data.get('en_retard'):
            queryset = queryset.filter(
                date_echeance__lt=timezone.now().date(),
                statut_paiement__in=['non_payee', 'partiellement_payee']
            )
        
        if terme := form.cleaned_data.get('terme'):
            queryset = queryset.filter(
                Q(reference__icontains=terme) |
                Q(commentaire__icontains=terme) |
                Q(membre__nom__icontains=terme) |
                Q(membre__prenom__icontains=terme) |
                Q(membre__email__icontains=terme)
            )
        
        return queryset
    
    def _export_csv(self, queryset):
        """Exporte les cotisations au format CSV."""
        return export_utils.export_cotisations_csv(queryset)
    
    def _export_excel(self, queryset):
        """Exporte les cotisations au format Excel."""
        return export_utils.export_cotisations_excel(queryset)

class StatistiquesView(StaffRequiredMixin, TemplateView):
    """
    Vue pour afficher les statistiques financières des cotisations et paiements.
    """
    template_name = 'cotisations/statistiques.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Récupérer les paramètres de filtre
        annee = self.request.GET.get('annee', timezone.now().date().year)
        try:
            annee = int(annee)
        except (ValueError, TypeError):
            annee = timezone.now().date().year
        
        # Statistiques générales
        total_cotisations = Cotisation.objects.filter(annee=annee).count()
        montant_total = Cotisation.objects.filter(annee=annee).aggregate(
            total=Sum('montant')
        ).get('total') or Decimal('0.00')
        
        montant_paye = Paiement.objects.filter(
            cotisation__annee=annee,
            type_transaction='paiement'
        ).aggregate(total=Sum('montant')).get('total') or Decimal('0.00')
        
        montant_remboursement = Paiement.objects.filter(
            cotisation__annee=annee,
            type_transaction='remboursement'
        ).aggregate(total=Sum('montant')).get('total') or Decimal('0.00')
        
        # Calcul du taux de recouvrement
        taux_recouvrement = 0
        if montant_total > 0:
            taux_recouvrement = (montant_paye / montant_total * 100).quantize(Decimal('0.01'))
        
        # Statistiques par mois
        stats_par_mois = []
        for mois in range(1, 13):
            cotisations_mois = Cotisation.objects.filter(annee=annee, mois=mois)
            paiements_mois = Paiement.objects.filter(
                cotisation__annee=annee,
                cotisation__mois=mois,
                type_transaction='paiement'
            )
            
            montant_cotisations = cotisations_mois.aggregate(
                total=Sum('montant')
            ).get('total') or Decimal('0.00')
            
            montant_paiements = paiements_mois.aggregate(
                total=Sum('montant')
            ).get('total') or Decimal('0.00')
            
            stats_par_mois.append({
                'mois': mois,
                'mois_nom': datetime.date(2000, mois, 1).strftime('%B'),
                'montant_cotisations': montant_cotisations,
                'montant_paiements': montant_paiements,
                'difference': montant_paiements - montant_cotisations,
            })
        
        # Statistiques par type de membre
        stats_par_type = Cotisation.objects.filter(annee=annee).values(
            'type_membre__libelle'
        ).annotate(
            nb_cotisations=Count('id'),
            montant_total=Sum('montant'),
            montant_paye=Sum(F('montant') - F('montant_restant')),
        ).order_by('type_membre__libelle')
        
        # Statistiques par mode de paiement
        stats_par_mode = Paiement.objects.filter(
            cotisation__annee=annee,
            type_transaction='paiement'
        ).values(
            'mode_paiement__libelle'
        ).annotate(
            nb_paiements=Count('id'),
            montant_total=Sum('montant')
        ).order_by('-montant_total')
        
        context.update({
            'annee': annee,
            'annees_disponibles': range(datetime.date.today().year - 5, datetime.date.today().year + 1),
            'total_cotisations': total_cotisations,
            'montant_total': montant_total,
            'montant_paye': montant_paye,
            'montant_remboursement': montant_remboursement,
            'taux_recouvrement': taux_recouvrement,
            'stats_par_mois': stats_par_mois,
            'stats_par_type': stats_par_type,
            'stats_par_mode': stats_par_mode,
        })
        
        return context

@login_required
def export_cotisations_pdf(request):
    """
    Vue pour exporter les cotisations au format PDF.
    """
    if not request.user.is_staff:
        return HttpResponseForbidden(_("Vous n'avez pas les permissions nécessaires."))
    
    # Récupérer les filtres de recherche pour les appliquer à l'export
    form = CotisationSearchForm(request.GET)
    queryset = Cotisation.objects.all()
    
    # Appliquer les filtres comme dans ExportCotisationsView._apply_search_filters
    if form.is_valid():
        # Appliquer les filtres correspondants
        if membre := form.cleaned_data.get('membre'):
            queryset = queryset.filter(membre=membre)
        # Continuer avec les autres filtres...
    
    # Préparer les filtres pour le rapport
    filtres = {}
    for field in form.cleaned_data:
        if form.cleaned_data[field]:
            filtres[form.fields[field].label] = form.cleaned_data[field]
    
    # Générer le rapport PDF
    return export_utils.generer_rapport_cotisations_pdf(
        queryset,
        titre=_("Rapport des cotisations"),
        filtres=filtres
    )


@login_required
def export_paiements(request):
    """
    Vue pour exporter la liste des paiements au format CSV ou Excel.
    """
    if not request.user.is_staff:
        return HttpResponseForbidden(_("Vous n'avez pas les permissions nécessaires."))
    
    format_export = request.GET.get('format', 'csv')
    
    # Récupérer les filtres et les appliquer
    queryset = Paiement.objects.all()
    
    # Appliquer les filtres
    type_transaction = request.GET.get('type_transaction')
    date_debut = request.GET.get('date_debut')
    date_fin = request.GET.get('date_fin')
    mode_paiement_id = request.GET.get('mode_paiement')
    membre_id = request.GET.get('membre_id')
    
    # Appliquer les filtres de recherche au queryset
    queryset = _apply_paiement_filters(
        queryset, type_transaction, date_debut, date_fin, mode_paiement_id, membre_id
    )
    
    # Exporter selon le format demandé
    if format_export == 'csv':
        return export_utils.export_paiements_csv(queryset)
    elif format_export == 'excel':
        return export_utils.export_paiements_excel(queryset)
    else:
        return HttpResponse(_("Format non supporté"), status=400)


def _apply_paiement_filters(queryset, type_transaction, date_debut, date_fin, mode_paiement_id, membre_id):
    """
    Applique les filtres de recherche au queryset des paiements.
    Fonction utilitaire utilisée par plusieurs vues.
    """
    if type_transaction:
        queryset = queryset.filter(type_transaction=type_transaction)
    
    if date_debut:
        try:
            date_debut = datetime.datetime.strptime(date_debut, '%Y-%m-%d').date()
            queryset = queryset.filter(date_paiement__gte=date_debut)
        except ValueError:
            logger.warning(f"Format de date invalide pour date_debut: {date_debut}")
    
    if date_fin:
        try:
            date_fin = datetime.datetime.strptime(date_fin, '%Y-%m-%d').date()
            queryset = queryset.filter(date_paiement__lte=date_fin)
        except ValueError:
            logger.warning(f"Format de date invalide pour date_fin: {date_fin}")
    
    if mode_paiement_id:
        queryset = queryset.filter(mode_paiement_id=mode_paiement_id)
    
    if membre_id:
        queryset = queryset.filter(cotisation__membre_id=membre_id)
    
    return queryset


@login_required
def export_rappels(request):
    """
    Vue pour exporter la liste des rappels au format CSV ou Excel.
    """
    if not request.user.is_staff:
        return HttpResponseForbidden(_("Vous n'avez pas les permissions nécessaires."))
    
    format_export = request.GET.get('format', 'csv')
    
    # Récupérer les filtres et les appliquer
    queryset = Rappel.objects.all()
    
    # Filtres disponibles
    type_rappel = request.GET.get('type_rappel')
    etat = request.GET.get('etat')
    date_debut = request.GET.get('date_debut')
    date_fin = request.GET.get('date_fin')
    membre_id = request.GET.get('membre_id')
    
    # Appliquer les filtres
    queryset = _apply_rappel_filters(queryset, type_rappel, etat, date_debut, date_fin, membre_id)
    
    # Exporter selon le format demandé
    if format_export == 'csv':
        return export_utils.export_rappels_csv(queryset)
    elif format_export == 'excel':
        return export_utils.export_rappels_excel(queryset)
    else:
        return HttpResponse(_("Format non supporté"), status=400)


def _apply_rappel_filters(queryset, type_rappel, etat, date_debut, date_fin, membre_id):
    """
    Applique les filtres de recherche au queryset des rappels.
    Fonction utilitaire utilisée par plusieurs vues.
    """
    if type_rappel:
        queryset = queryset.filter(type_rappel=type_rappel)
    
    if etat:
        queryset = queryset.filter(etat=etat)
    
    if date_debut:
        try:
            date_debut = datetime.datetime.strptime(date_debut, '%Y-%m-%d').date()
            queryset = queryset.filter(date_envoi__gte=date_debut)
        except ValueError:
            logger.warning(f"Format de date invalide pour date_debut: {date_debut}")
    
    if date_fin:
        try:
            date_fin = datetime.datetime.strptime(date_fin, '%Y-%m-%d').date()
            queryset = queryset.filter(date_envoi__lte=date_fin)
        except ValueError:
            logger.warning(f"Format de date invalide pour date_fin: {date_fin}")
    
    if membre_id:
        queryset = queryset.filter(membre_id=membre_id)
    
    return queryset
	
	#
# API et fonctions pour les calculs de cotisations
#
@login_required
def api_calculer_montant(request):
    """
    API pour calculer le montant d'une cotisation en fonction du barème sélectionné.
    Peut calculer un montant au prorata si les dates sont fournies.
    """
    bareme_id = request.GET.get('bareme_id')
    type_membre_id = request.GET.get('type_membre_id')
    
    # Nouveaux paramètres pour le calcul au prorata
    date_debut = request.GET.get('date_debut')
    date_fin = request.GET.get('date_fin')
    
    # Convertir les dates si fournies
    periode_debut = None
    periode_fin = None
    
    if date_debut:
        try:
            periode_debut = datetime.datetime.strptime(date_debut, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({
                'success': False, 
                'message': str(_("Format de date de début invalide. Format attendu: YYYY-MM-DD"))
            })
            
    if date_fin:
        try:
            periode_fin = datetime.datetime.strptime(date_fin, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({
                'success': False, 
                'message': str(_("Format de date de fin invalide. Format attendu: YYYY-MM-DD"))
            })
    
    if not bareme_id and not type_membre_id:
        return JsonResponse({
            'success': False, 
            'message': str(_("Paramètre manquant. Veuillez spécifier bareme_id ou type_membre_id"))
        })
    
    try:
        # Récupérer le barème
        if bareme_id:
            bareme = BaremeCotisation.objects.get(pk=bareme_id)
        elif type_membre_id:
            # Trouver le barème actif pour ce type de membre
            bareme = BaremeCotisation.objects.filter(
                type_membre_id=type_membre_id,
                date_debut_validite__lte=timezone.now().date()
            ).order_by('-date_debut_validite').first()
            
            if not bareme:
                return JsonResponse({
                    'success': False, 
                    'message': str(_("Aucun barème trouvé pour ce type de membre"))
                })
        
        # Calculer le montant (au prorata si les dates sont fournies)
        if periode_debut and periode_fin:
            montant = bareme.calculer_montant_prorata(periode_debut, periode_fin)
            montant_original = bareme.montant
            
            # Pourcentage appliqué
            if montant_original > 0:
                pourcentage = (montant / montant_original * 100).quantize(Decimal('0.01'))
            else:
                pourcentage = Decimal('100.00')
            
            return JsonResponse({
                'success': True,
                'montant': float(montant),
                'montant_original': float(montant_original),
                'pourcentage': float(pourcentage),
                'periodicite': bareme.get_periodicite_display(),
                'calcul_prorata': True,
                'periode_debut': periode_debut.isoformat(),
                'periode_fin': periode_fin.isoformat()
            })
        else:
            # Comportement standard sans prorata
            return JsonResponse({
                'success': True,
                'montant': float(bareme.montant),
                'periodicite': bareme.get_periodicite_display(),
                'calcul_prorata': False
            })
    
    except BaremeCotisation.DoesNotExist:
        return JsonResponse({'success': False, 'message': str(_("Barème non trouvé"))})
    except Exception as e:
        logger.error(f"Erreur lors du calcul du montant: {str(e)}")
        return JsonResponse({'success': False, 'message': str(e)})


@login_required
def api_baremes_par_type(request):
    """
    API pour récupérer les barèmes disponibles pour un type de membre.
    """
    type_membre_id = request.GET.get('type_membre')
    
    if not type_membre_id:
        return JsonResponse({
            'success': False, 
            'message': _("Type de membre non spécifié")
        })
    
    try:
        today = timezone.now().date()
        
        # Récupérer tous les barèmes pour ce type de membre
        baremes = BaremeCotisation.objects.filter(
            type_membre_id=type_membre_id
        ).order_by('-date_debut_validite')
        
        # Formater les données pour l'API
        baremes_data = []
        for bareme in baremes:
            est_actif = (
                bareme.date_debut_validite <= today and 
                (bareme.date_fin_validite is None or bareme.date_fin_validite >= today)
            )
            est_futur = bareme.date_debut_validite > today
            
            baremes_data.append({
                'id': bareme.id,
                'montant': float(bareme.montant),
                'periodicite': bareme.periodicite,
                'periodicite_display': bareme.get_periodicite_display(),
                'date_debut_validite': bareme.date_debut_validite.isoformat(),
                'date_fin_validite': bareme.date_fin_validite.isoformat() if bareme.date_fin_validite else None,
                'est_actif': est_actif,
                'est_futur': est_futur
            })
        
        return JsonResponse({
            'success': True,
            'baremes': baremes_data
        })
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des barèmes: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)
    
@login_required
def api_verifier_bareme(request):
    """
    API pour vérifier si un barème existe déjà pour un type de membre à une date donnée.
    """
    type_membre_id = request.GET.get('type_membre')
    date = request.GET.get('date')
    exclude_id = request.GET.get('exclude')
    
    if not type_membre_id or not date:
        return JsonResponse({
            'success': False,
            'message': _("Paramètres manquants")
        })
    
    try:
        # Convertir la date en objet date
        date_obj = datetime.datetime.strptime(date, '%Y-%m-%d').date()
        
        # Construire la requête
        query = BaremeCotisation.objects.filter(
            type_membre_id=type_membre_id,
            date_debut_validite__lte=date_obj,
            deleted_at__isnull=True
        )
        
        # Ajouter la condition pour la date de fin (si elle existe)
        query = query.filter(
            Q(date_fin_validite__isnull=True) | Q(date_fin_validite__gte=date_obj)
        )
        
        # Exclure le barème en cours d'édition
        if exclude_id:
            query = query.exclude(pk=exclude_id)
        
        # Vérifier si un barème existe
        exists = query.exists()
        
        if exists:
            bareme = query.first()
            type_membre = TypeMembre.objects.get(pk=type_membre_id)
            
            return JsonResponse({
                'success': True,
                'exists': True,
                'message': _("Un barème existe déjà pour le type '%(type)s' à la date du %(date)s (%(montant)s € - %(periodicite)s)") % {
                    'type': type_membre.libelle,
                    'date': date_obj.strftime('%d/%m/%Y'),
                    'montant': bareme.montant,
                    'periodicite': bareme.get_periodicite_display()
                }
            })
        else:
            return JsonResponse({
                'success': True,
                'exists': False
            })
    except Exception as e:
        logger.error(f"Erreur lors de la vérification du barème: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


#
# API pour les paiements et reçus
#
@login_required
def api_generer_recu(request, paiement_id):
    """
    API pour générer un reçu PDF pour un paiement.
    """
    # Vérifier les permissions
    if not request.user.is_staff:
        return HttpResponseForbidden(_("Vous n'avez pas les permissions pour générer ce reçu"))
    
    paiement = get_object_or_404(Paiement, pk=paiement_id)
    
    try:
        # Créer un objet HttpResponse avec l'en-tête PDF approprié
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="recu_paiement_{paiement_id}.pdf"'
        
        # Créer le document PDF
        from reportlab.lib.pagesizes import letter
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        
        doc = SimpleDocTemplate(response, pagesize=letter)
        styles = getSampleStyleSheet()
        
        # Créer des styles personnalisés
        title_style = ParagraphStyle(
            'Title',
            parent=styles['Heading1'],
            alignment=1,  # Centré
            spaceAfter=12
        )
        
        subtitle_style = ParagraphStyle(
            'Subtitle',
            parent=styles['Heading2'],
            fontSize=12,
            alignment=1,
            spaceAfter=6
        )
        
        normal_style = styles["Normal"]
        
        # Contenu du document
        content = []
        
        # Titre
        content.append(Paragraph(_("REÇU DE PAIEMENT"), title_style))
        content.append(Spacer(1, 12))
        
        # Référence
        content.append(Paragraph(
            f"{_('Référence')}: {paiement.reference_paiement or paiement.id}",
            subtitle_style
        ))
        content.append(Spacer(1, 12))
        
        # Informations de base
        infos = [
            [_("Date de paiement:"), paiement.date_paiement.strftime('%d/%m/%Y %H:%M')],
            [_("Mode de paiement:"), paiement.mode_paiement.libelle if paiement.mode_paiement else '-'],
            [_("Montant:"), f"{paiement.montant} {paiement.devise}"],
            [_("Type de transaction:"), paiement.get_type_transaction_display()],
            [_("Cotisation associée:"), paiement.cotisation.reference]
        ]
        
        # Ajouter les informations du membre
        membre = paiement.cotisation.membre
        infos.extend([
            [_("Membre:"), f"{membre.prenom} {membre.nom}"],
            [_("Email:"), membre.email],
            [_("ID membre:"), str(membre.id)]
        ])
        
        # Créer un tableau avec ces informations
        table = Table(infos, colWidths=[150, 350])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey)
        ]))
        
        content.append(table)
        content.append(Spacer(1, 20))
        
        # Informations complémentaires
        if paiement.commentaire:
            content.append(Paragraph(_("Commentaire:"), styles['Heading3']))
            content.append(Paragraph(paiement.commentaire, normal_style))
            content.append(Spacer(1, 12))
        
        # Note légale
        content.append(Spacer(1, 30))
        content.append(Paragraph(
            _("Ce reçu fait office de justificatif de paiement. Conservez-le précieusement."),
            ParagraphStyle('Note', parent=normal_style, fontName='Helvetica-Oblique')
        ))
        
        # Générer le PDF
        doc.build(content)
        
        # Marquer le reçu comme envoyé
        paiement.recu_envoye = True
        paiement.save(update_fields=['recu_envoye'])
        
        return response
    
    except Exception as e:
        # En cas d'erreur, renvoyer une réponse JSON avec l'erreur
        logger.error(f"Erreur lors de la génération du reçu: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, encoder=ExtendedJSONEncoder, status=500)


@login_required
@require_POST
def api_marquer_paiement_recu(request, paiement_id):
    """
    API pour marquer un paiement comme ayant eu un reçu envoyé.
    Utile pour marquer les reçus envoyés manuellement.
    """
    if not request.user.is_staff:
        return JsonResponse({
            'success': False,
            'message': _("Vous n'avez pas les permissions nécessaires.")
        }, encoder=ExtendedJSONEncoder, status=403)
    
    paiement = get_object_or_404(Paiement, pk=paiement_id)
    paiement.recu_envoye = True
    paiement.save(update_fields=['recu_envoye'])
    
    return JsonResponse({
        'success': True,
        'message': _("Paiement marqué comme ayant reçu un reçu.")
    }, encoder=ExtendedJSONEncoder)


#
# API pour les statistiques et rapports
#
@login_required
def api_stats_cotisations(request):
    """
    API pour obtenir des statistiques sur les cotisations au format JSON.
    Utile pour les tableaux de bord dynamiques et les graphiques.
    """
    if not request.user.is_staff:
        return JsonResponse({
            'success': False,
            'message': _("Vous n'avez pas les permissions nécessaires.")
        }, encoder=ExtendedJSONEncoder, status=403)
    
    # Paramètres de filtrage
    annee = request.GET.get('annee', timezone.now().year)
    try:
        annee = int(annee)
    except (ValueError, TypeError):
        annee = timezone.now().year
    
    # Statistiques de base
    stats = {
        'total_cotisations': Cotisation.objects.filter(annee=annee).count(),
        'montant_total': float(Cotisation.objects.filter(annee=annee).aggregate(
            total=Sum('montant')).get('total') or 0),
        'montant_paye': float(Cotisation.objects.filter(annee=annee).aggregate(
            total=Sum(F('montant') - F('montant_restant'))).get('total') or 0),
        'taux_recouvrement': 0,
    }
    
    # Calcul du taux de recouvrement
    if stats['montant_total'] > 0:
        stats['taux_recouvrement'] = round((stats['montant_paye'] / stats['montant_total']) * 100, 2)
    
    # Distribution par statut de paiement
    status_counts = {status[0]: 0 for status in Cotisation._meta.get_field('statut_paiement').choices}
    for status_data in Cotisation.objects.filter(annee=annee).values('statut_paiement').annotate(count=Count('id')):
        status_counts[status_data['statut_paiement']] = status_data['count']
    
    stats['distribution_statut'] = status_counts
    
    # Données par mois
    monthly_data = []
    for month in range(1, 13):
        month_name = datetime.date(2000, month, 1).strftime('%B')
        
        cotisations_data = Cotisation.objects.filter(annee=annee, mois=month).aggregate(
            count=Count('id'),
            total=Sum('montant'),
            paid=Sum(F('montant') - F('montant_restant'))
        )
        
        paiements_data = Paiement.objects.filter(
            date_paiement__year=annee,
            date_paiement__month=month,
            type_transaction='paiement'
        ).aggregate(
            count=Count('id'),
            total=Sum('montant')
        )
        
        monthly_data.append({
            'month': month_name,
            'cotisations_count': cotisations_data['count'] or 0,
            'cotisations_total': float(cotisations_data['total'] or 0),
            'cotisations_paid': float(cotisations_data['paid'] or 0),
            'paiements_count': paiements_data['count'] or 0,
            'paiements_total': float(paiements_data['total'] or 0),
        })
    
    stats['monthly_data'] = monthly_data
    
    # Cotisations en retard
    cotisations_retard = Cotisation.objects.en_retard().filter(annee=annee)
    stats['cotisations_retard'] = {
        'count': cotisations_retard.count(),
        'total': float(cotisations_retard.aggregate(total=Sum('montant_restant')).get('total') or 0)
    }
    
    return JsonResponse({
        'success': True,
        'stats': stats
    }, encoder=ExtendedJSONEncoder)


@login_required
def api_cotisations_en_retard(request):
    """
    API pour récupérer la liste des cotisations en retard.
    Utile pour les tâches automatisées de rappel.
    """
    if not request.user.is_staff:
        return JsonResponse({
            'success': False,
            'message': _("Vous n'avez pas les permissions nécessaires.")
        }, encoder=ExtendedJSONEncoder, status=403)
    
    jours_retard = request.GET.get('jours_retard')
    try:
        jours_retard = int(jours_retard) if jours_retard else None
    except ValueError:
        jours_retard = None
    
    # Récupérer les cotisations en retard
    cotisations_retard = Cotisation.objects.en_retard()
    
    # Filtrer par nombre de jours de retard si spécifié
    if jours_retard is not None:
        date_limite = timezone.now().date() - datetime.timedelta(days=jours_retard)
        cotisations_retard = cotisations_retard.filter(date_echeance__lte=date_limite)
    
    # Préparer les données de réponse
    cotisations_data = []
    for cotisation in cotisations_retard.select_related('membre'):
        cotisations_data.append({
            'id': cotisation.id,
            'reference': cotisation.reference,
            'membre': {
                'id': cotisation.membre.id,
                'nom': cotisation.membre.nom,
                'prenom': cotisation.membre.prenom,
                'email': cotisation.membre.email
            },
            'montant_total': float(cotisation.montant),
            'montant_restant': float(cotisation.montant_restant),
            'date_echeance': cotisation.date_echeance.isoformat(),
            'jours_retard': cotisation.jours_retard
        })
    
    return JsonResponse({
        'success': True,
        'cotisations_retard': cotisations_data
    }, encoder=ExtendedJSONEncoder)


@login_required
@require_POST
def api_envoyer_rappels_automatiques(request):
    """
    API pour envoyer des rappels automatiques pour les cotisations en retard.
    Utile pour être appelée par une tâche cron.
    """
    if not request.user.is_staff:
        return JsonResponse({
            'success': False,
            'message': _("Vous n'avez pas les permissions nécessaires.")
        }, encoder=ExtendedJSONEncoder, status=403)
    
    # Paramètres
    jours_retard = request.POST.get('jours_retard')
    try:
        jours_retard = int(jours_retard) if jours_retard else 30  # Par défaut, 30 jours de retard
    except ValueError:
        jours_retard = 30
    
    type_rappel = request.POST.get('type_rappel', 'email')
    niveau_rappel = request.POST.get('niveau_rappel', 1)
    try:
        niveau_rappel = int(niveau_rappel)
    except ValueError:
        niveau_rappel = 1
    
    # Récupérer les cotisations en retard
    date_limite = timezone.now().date() - datetime.timedelta(days=jours_retard)
    cotisations_retard = Cotisation.objects.en_retard().filter(date_echeance__lte=date_limite)
    
    # Vérifier si des rappels ont déjà été envoyés récemment
    date_dernier_rappel = timezone.now() - datetime.timedelta(days=7)  # Ne pas envoyer plus d'un rappel par semaine
    
    # Statistiques pour le retour
    stats = {
        'total': cotisations_retard.count(),
        'rappels_crees': 0,
        'rappels_envoyes': 0,
        'erreurs': 0,
        'details': []
    }
    
    for cotisation in cotisations_retard:
        # Vérifier si un rappel récent existe déjà
        rappel_recent = Rappel.objects.filter(
            cotisation=cotisation,
            date_envoi__gte=date_dernier_rappel
        ).exists()
        
        if rappel_recent:
            stats['details'].append({
                'reference': cotisation.reference,
                'status': 'ignored',
                'message': _("Un rappel récent existe déjà")
            })
            continue
        
        # Créer un nouveau rappel
        try:
            # Générer le contenu du rappel
            membre = cotisation.membre
            montant = cotisation.montant_restant
            date_echeance = cotisation.date_echeance
            
            contenu = _(
                "Cher/Chère %(prenom)s %(nom)s,\n\n"
                "Nous vous rappelons que votre cotisation (réf. %(reference)s) "
                "d'un montant restant dû de %(montant)s € "
                "est arrivée à échéance le %(date)s.\n\n"
                "Nous vous remercions de bien vouloir procéder au règlement "
                "dans les meilleurs délais.\n\n"
                "Cordialement,\n"
                "L'équipe de l'association"
            ) % {
                'prenom': membre.prenom,
                'nom': membre.nom,
                'reference': cotisation.reference,
                'montant': montant,
                'date': date_echeance.strftime('%d/%m/%Y')
            }
            
            # Créer le rappel
            rappel = Rappel.objects.create(
                membre=membre,
                cotisation=cotisation,
                type_rappel=type_rappel,
                niveau=niveau_rappel,
                contenu=contenu,
                etat='planifie',
                cree_par=request.user
            )
            
            stats['rappels_crees'] += 1
            
            # Simuler l'envoi du rappel
            # Note: Dans une implémentation réelle, vous connecteriez ceci à votre système d'envoi d'emails
            rappel.etat = 'envoye'
            rappel.date_envoi = timezone.now()
            rappel.save()
            
            stats['rappels_envoyes'] += 1
            stats['details'].append({
                'reference': cotisation.reference,
                'status': 'success',
                'rappel_id': rappel.id,
                'message': _("Rappel créé et envoyé")
            })
            
        except Exception as e:
            logger.error(f"Erreur lors de la création du rappel: {str(e)}")
            stats['erreurs'] += 1
            stats['details'].append({
                'reference': cotisation.reference,
                'status': 'error',
                'message': str(e)
            })
    
    return JsonResponse({
        'success': True,
        'stats': stats
    }, encoder=ExtendedJSONEncoder)


#
# API pour les rappels
#
@login_required
def rappel_contenu_ajax(request, rappel_id):
    """
    Vue AJAX pour récupérer le contenu d'un rappel.
    """
    if not request.user.is_staff:
        return JsonResponse({
            'success': False,
            'message': _("Vous n'avez pas les permissions nécessaires.")
        }, encoder=ExtendedJSONEncoder, status=403)
    
    rappel = get_object_or_404(Rappel, pk=rappel_id)
    
    return JsonResponse({
        'success': True,
        'contenu': rappel.contenu,
        'rappel': {
            'id': rappel.id,
            'type_rappel': rappel.get_type_rappel_display(),
            'etat': rappel.get_etat_display(),
            'niveau': rappel.niveau
        }
    }, encoder=ExtendedJSONEncoder)


@login_required
@require_POST
def rappel_envoi_ajax(request, rappel_id):
    """
    Vue AJAX pour envoyer un rappel planifié.
    """
    if not request.user.is_staff:
        return JsonResponse({
            'success': False,
            'message': _("Vous n'avez pas les permissions nécessaires.")
        }, encoder=ExtendedJSONEncoder, status=403)
    
    rappel = get_object_or_404(Rappel, pk=rappel_id)
    
    # Vérifier que le rappel est en état 'planifié'
    if rappel.etat != RAPPEL_ETAT_PLANIFIE:
        return JsonResponse({
            'success': False,
            'message': _("Ce rappel est déjà traité.")
        }, encoder=ExtendedJSONEncoder)
    
    try:
        # Marquer comme envoyé
        rappel.etat = RAPPEL_ETAT_ENVOYE
        rappel.date_envoi = timezone.now()
        rappel.save()
        
        # Simuler l'envoi d'email ou SMS ici
        # Cette partie serait remplacée par votre système d'envoi réel
        
        return JsonResponse({
            'success': True,
            'message': _("Le rappel a été envoyé avec succès."),
            'rappel': {
                'id': rappel.id,
                'etat': rappel.get_etat_display(),
                'date_envoi': rappel.date_envoi.isoformat()
            }
        }, encoder=ExtendedJSONEncoder)
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi du rappel: {str(e)}")
        
        # En cas d'erreur, marquer comme échoué
        rappel.etat = RAPPEL_ETAT_ECHOUE
        rappel.resultat = str(e)
        rappel.save()
        
        return JsonResponse({
            'success': False,
            'message': _("Erreur lors de l'envoi du rappel: {0}").format(str(e))
        }, encoder=ExtendedJSONEncoder)


@login_required
@require_POST
def rappel_supprimer_ajax(request, rappel_id):
    """
    Vue AJAX pour supprimer un rappel.
    """
    if not request.user.is_staff:
        return JsonResponse({
            'success': False,
            'message': _("Vous n'avez pas les permissions nécessaires.")
        }, encoder=ExtendedJSONEncoder, status=403)
    
    rappel = get_object_or_404(Rappel, pk=rappel_id)
    
    try:
        # Suppression logique
        rappel.delete()
        
        return JsonResponse({
            'success': True,
            'message': _("Le rappel a été supprimé avec succès.")
        }, encoder=ExtendedJSONEncoder)
    except Exception as e:
        logger.error(f"Erreur lors de la suppression du rappel: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': _("Erreur lors de la suppression du rappel: {0}").format(str(e))
        }, encoder=ExtendedJSONEncoder)


"""
Solution finale pour api_types_membre_par_membre utilisant la méthode existante get_types_actifs()

Cette solution utilise directement la méthode intégrée au modèle Membre qui est déjà
conçue pour récupérer les types de membre actifs.
"""

@login_required
def api_types_membre_par_membre(request):
    """
    API pour récupérer les types de membre associés à un membre spécifique.
    """
    membre_id = request.GET.get('membre_id')
    
    # Logs de débogage
    print(f"=== APPEL API TYPES MEMBRE ===")
    print(f"membre_id reçu: {membre_id}")
    
    if not membre_id:
        return JsonResponse({'success': False, 'message': _("Membre non spécifié")})
    
    try:
        # Récupérer le membre
        membre = Membre.objects.get(pk=membre_id)
        print(f"Membre trouvé: {membre.id} - {membre.prenom} {membre.nom}")
        
        # Date actuelle pour le débogage
        today = datetime.date.today()
        print(f"Date actuelle: {today}")
        
        # Utiliser la méthode intégrée get_types_actifs() du modèle Membre
        # Cette méthode est déjà définie pour récupérer les types actifs
        types_actifs = membre.get_types_actifs()
        
        print(f"Nombre de types actifs: {types_actifs.count()}")
        
        # Liste pour les logs de débogage
        for tm in types_actifs:
            print(f" - Type actif: {tm.id} - {tm.libelle}")
        
        # Préparer la réponse JSON
        types_membre = []
        for tm in types_actifs:
            types_membre.append({
                'id': tm.id,
                'libelle': tm.libelle,
            })
        
        # Message personnalisé si aucun type actif
        if not types_membre:
            print("ATTENTION: Aucun type de membre actif trouvé!")
            return JsonResponse({
                'success': True,
                'types_membre': [],
                'single_type': False,
                'membre_nom': f"{membre.prenom} {membre.nom}",
                'message': _("Ce membre n'a aucun type actif à la date d'aujourd'hui")
            })
        
        # Réponse normale
        return JsonResponse({
            'success': True,
            'types_membre': types_membre,
            'single_type': len(types_membre) == 1,
            'membre_nom': f"{membre.prenom} {membre.nom}"
        })
        
    except Membre.DoesNotExist:
        print(f"Erreur: Membre {membre_id} non trouvé")
        return JsonResponse({'success': False, 'message': _("Membre non trouvé")})
    except Exception as e:
        import traceback
        print(f"Exception dans api_types_membre_par_membre: {str(e)}")
        print(traceback.format_exc())
        return JsonResponse({'success': False, 'message': str(e)})


def get_duree_jours_par_periodicite(periodicite):
    """
    Fonction utilitaire pour obtenir la durée standard en jours pour une périodicité.
    """
    if periodicite == 'mensuelle':
        return 30
    elif periodicite == 'trimestrielle':
        return 91
    elif periodicite == 'semestrielle':
        return 182
    elif periodicite == 'annuelle':
        return 365
    else:
        return 365  # Par défaut


#
# Aliases de vues pour l'intégration avec urls.py
#
dashboard = DashboardView.as_view()
cotisation_list = CotisationListView.as_view()
cotisation_detail = CotisationDetailView.as_view()
cotisation_create = CotisationCreateView.as_view()
cotisation_update = CotisationUpdateView.as_view()
cotisation_delete = CotisationDeleteView.as_view()
paiement_list = PaiementListView.as_view()
paiement_detail = PaiementDetailView.as_view()
paiement_create = PaiementCreateView.as_view()
paiement_update = PaiementUpdateView.as_view()
paiement_delete = PaiementDeleteView.as_view()
bareme_list = BaremeCotisationListView.as_view()
bareme_detail = BaremeDetailView.as_view()
bareme_create = BaremeCotisationCreateView.as_view()
bareme_update = BaremeCotisationUpdateView.as_view()
bareme_delete = BaremeCotisationDeleteView.as_view()
rappel_list = RappelListView.as_view()
rappel_detail = RappelDetailView.as_view()
rappel_create = RappelCreateView.as_view()
corbeille = CotisationCorbeilleView.as_view()
statistiques = StatistiquesView.as_view()
export = ExportCotisationsView.as_view()
import_cotisations = ImportCotisationsView.as_view()
rappel_update = RappelUpdateView.as_view()