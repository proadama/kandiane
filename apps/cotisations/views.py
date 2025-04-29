# apps/cotisations/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.http import JsonResponse, HttpResponse, HttpResponseForbidden
from django.views.generic import (
    View, TemplateView, ListView, DetailView, 
    CreateView, UpdateView, DeleteView
)
from django.views.decorators.http import require_POST
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Sum, Count, F, ExpressionWrapper, DecimalField
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from decimal import Decimal
import json
import csv
import datetime
from django.core.serializers.json import DjangoJSONEncoder
from . import export_utils

from apps.core.mixins import StaffRequiredMixin, TrashViewMixin, RestoreViewMixin
from apps.membres.models import Membre, TypeMembre

from .models import (
    Cotisation, Paiement, ModePaiement, BaremeCotisation,
    Rappel, HistoriqueCotisation, ConfigurationCotisation
)
from .forms import (
    CotisationForm, PaiementForm, BaremeCotisationForm,
    RappelForm, CotisationSearchForm, ImportCotisationsForm,
    ConfigurationCotisationForm
)


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
        montant_total = Cotisation.objects.filter(cotisations_filter).aggregate(total=Sum('montant')).get('total') or Decimal('0.00')
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
            'cotisations_par_mois': json.dumps(cotisations_par_mois),
            'paiements_par_mois': json.dumps(paiements_par_mois),
            'cotisations_non_payees_par_mois': json.dumps(cotisations_non_payees_par_mois),
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
                pass
        
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
                'message': str(_("Format de données invalide."))  # Convertir explicitement en chaîne
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
            _("Le rappel a été créé avec succès.")
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
                success_message = "Le paiement a été enregistré avec succès."
                
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
                error_message = "Erreur lors de l'enregistrement du paiement."
                return JsonResponse({
                    'success': False,
                    'errors': form.errors.as_json(),
                    'message': error_message
                }, encoder=ExtendedJSONEncoder)
        except json.JSONDecodeError:
            error_message = "Format de données invalide."
            return JsonResponse({
                'success': False,
                'message': error_message
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
            
            success_message = "Le paiement a été enregistré avec succès."
            
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
            error_message = "Erreur lors de l'enregistrement du paiement."
            return JsonResponse({
                'success': False,
                'errors': form.errors.as_json(),
                'message': error_message
            }, encoder=ExtendedJSONEncoder)

@require_POST
def rappel_create_ajax(request, cotisation_id):
    """
    Vue AJAX pour créer un rappel depuis la page de détail d'une cotisation.
    """
    cotisation = get_object_or_404(Cotisation, pk=cotisation_id)
    membre = cotisation.membre
    
    # Pour les requêtes AJAX avec JSON
    if request.content_type == 'application/json':
        try:
            data = json.loads(request.body)
            
            # Créer un dictionnaire de données pour le formulaire
            form_data = {
                'type_rappel': data.get('type_rappel'),
                'niveau': data.get('niveau'),
                'contenu': data.get('contenu'),
            }
            
            # Traiter les options de planification
            if data.get('planifie') == 'true' and data.get('date_planifiee'):
                # Si l'envoi est planifié, on garde l'état 'planifie'
                etat = 'planifie'
                # Convertir la date planifiée en datetime
                try:
                    date_planifiee = datetime.datetime.fromisoformat(data.get('date_planifiee'))
                    form_data['date_envoi'] = date_planifiee
                except (ValueError, TypeError):
                    error_message = "Format de date invalide"
                    return JsonResponse({
                        'success': False,
                        'message': error_message
                    }, encoder=ExtendedJSONEncoder, status=400)
            else:
                # Si envoi immédiat, on marque comme envoyé
                etat = 'envoye'
                form_data['date_envoi'] = timezone.now()
            
            form_data['etat'] = etat
            
            # Utiliser None comme user si non authentifié
            user = request.user if request.user.is_authenticated else None
            form = RappelForm(form_data, user=user, cotisation=cotisation, membre=membre)
            
            if form.is_valid():
                rappel = form.save()
                
                # Pour les rappels à envoyer immédiatement, simuler l'envoi
                if etat == 'envoye':
                    # Ici, vous pouvez ajouter votre logique d'envoi de mail, SMS, etc.
                    pass
                
                success_message = "Le rappel a été créé avec succès."
                
                # Retourner les infos sur le rappel créé
                return JsonResponse({
                    'success': True,
                    'rappel': {
                        'id': rappel.id,
                        'date_envoi': rappel.date_envoi.strftime('%Y-%m-%dT%H:%M:%S'),
                        'type_rappel': str(rappel.get_type_rappel_display()),
                        'niveau': rappel.niveau,
                        'etat': str(rappel.get_etat_display()),
                        'contenu': rappel.contenu
                    },
                    'message': success_message
                }, encoder=ExtendedJSONEncoder)
            else:
                error_message = "Erreur lors de la création du rappel."
                return JsonResponse({
                    'success': False,
                    'errors': form.errors.as_json(),
                    'message': error_message
                }, encoder=ExtendedJSONEncoder)
        except json.JSONDecodeError:
            error_message = "Format de données invalide."
            return JsonResponse({
                'success': False,
                'message': error_message
            }, encoder=ExtendedJSONEncoder, status=400)
    
    # Pour les requêtes standard
    else:
        # Utiliser None comme user si non authentifié
        user = request.user if request.user.is_authenticated else None
        form = RappelForm(request.POST, user=user, cotisation=cotisation, membre=membre)
        
        if form.is_valid():
            rappel = form.save()
            
            success_message = "Le rappel a été créé avec succès."
            
            return JsonResponse({
                'success': True,
                'rappel': {
                    'id': rappel.id,
                    'date_envoi': rappel.date_envoi.strftime('%Y-%m-%dT%H:%M:%S'),
                    'type_rappel': str(rappel.get_type_rappel_display()),
                    'niveau': rappel.niveau,
                    'etat': str(rappel.get_etat_display()),
                    'contenu': rappel.contenu
                },
                'message': success_message
            }, encoder=ExtendedJSONEncoder)
        else:
            error_message = "Erreur lors de la création du rappel."
            return JsonResponse({
                'success': False,
                'errors': form.errors.as_json(),
                'message': error_message
            }, encoder=ExtendedJSONEncoder)


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
    # Note: cette partie serait remplacée par votre système d'envoi de mail
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
        # Ajouter cette méthode pour inclure current_date dans le contexte
        context = super().get_context_data(**kwargs)
        context['current_date'] = timezone.now().date()
        # Vous pouvez également ajouter "today" comme synonyme si nécessaire
        context['today'] = timezone.now().date()
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


class CotisationCorbeilleView(StaffRequiredMixin, TrashViewMixin, ListView):
    """
    Vue pour afficher les cotisations supprimées (corbeille).
    """
    model = Cotisation
    template_name = 'cotisations/corbeille.html'
    context_object_name = 'cotisations'
    paginate_by = 20
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _("Corbeille - Cotisations supprimées")
        return context


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


class ImportCotisationsView(StaffRequiredMixin, TemplateView):
    """
    Vue pour importer des cotisations depuis un fichier CSV ou Excel.
    """
    template_name = 'cotisations/import.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = ImportCotisationsForm()
        return context
    
    def post(self, request, *args, **kwargs):
        form = ImportCotisationsForm(request.POST, request.FILES)
        results = {
            'success': 0,
            'errors': 0,
            'details': []
        }
        
        if form.is_valid():
            fichier = form.cleaned_data['fichier']
            
            # Traiter selon le type de fichier
            extension = fichier.name.split('.')[-1].lower()
            
            if extension == 'csv':
                results = self._process_csv(fichier, form)
            elif extension in ['xlsx', 'xls']:
                results = self._process_excel(fichier, form)
        
        return render(request, self.template_name, {
            'form': form,
            'results': results
        })
    
    def _process_csv(self, fichier, form):
        """Traiter un fichier CSV"""
        # Note: Cette fonction serait implémentée pour traiter un fichier CSV
        # Nous la simulons ici pour l'exemple
        return {
            'success': 5,
            'errors': 1,
            'details': [
                {'row': 1, 'status': 'success', 'message': 'Cotisation créée pour jean.dupont@example.com'},
                {'row': 2, 'status': 'success', 'message': 'Cotisation créée pour marie.durand@example.com'},
                {'row': 3, 'status': 'success', 'message': 'Cotisation créée pour pierre.martin@example.com'},
                {'row': 4, 'status': 'error', 'message': 'Email inconnu: inconnu@example.com'},
                {'row': 5, 'status': 'success', 'message': 'Cotisation créée pour sophie.leroy@example.com'},
                {'row': 6, 'status': 'success', 'message': 'Cotisation créée pour paul.moreau@example.com'},
            ]
        }
    
    def _process_excel(self, fichier, form):
        """Traiter un fichier Excel"""
        # Note: Cette fonction serait implémentée pour traiter un fichier Excel
        # Nous la simulons ici pour l'exemple
        return {
            'success': 4,
            'errors': 0,
            'details': [
                {'row': 1, 'status': 'success', 'message': 'Cotisation créée pour jean.dupont@example.com'},
                {'row': 2, 'status': 'success', 'message': 'Cotisation créée pour marie.durand@example.com'},
                {'row': 3, 'status': 'success', 'message': 'Cotisation créée pour pierre.martin@example.com'},
                {'row': 4, 'status': 'success', 'message': 'Cotisation créée pour sophie.leroy@example.com'},
            ]
        }


from . import export_utils

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
        
        # Charger les relations pour optimiser les performances
        queryset = queryset.select_related('membre', 'type_membre')
        
        # Selon le format demandé
        if format_export == 'csv':
            return self._export_csv(queryset)
        elif format_export == 'excel':
            return self._export_excel(queryset)
        else:
            return HttpResponse(_("Format non supporté"), status=400)
    
    def _export_csv(self, queryset):
        return export_utils.export_cotisations_csv(queryset)
    
    def _export_excel(self, queryset):
        """
        Exporte les cotisations au format Excel.
        
        Args:
            queryset: QuerySet de cotisations à exporter
            
        Returns:
            HttpResponse: Fichier Excel à télécharger
        """
        from .export_utils import export_cotisations_excel
        return export_cotisations_excel(queryset)


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
            queryset = queryset.filter(date_paiement__gte=date_debut)
        
        date_fin = self.request.GET.get('date_fin')
        if date_fin:
            # Ajouter un jour pour inclure toute la journée de fin
            from datetime import datetime, timedelta
            try:
                date_fin_dt = datetime.strptime(date_fin, '%Y-%m-%d')
                date_fin_next = (date_fin_dt + timedelta(days=1)).strftime('%Y-%m-%d')
                queryset = queryset.filter(date_paiement__lt=date_fin_next)
            except ValueError:
                pass  # Si la date est mal formatée, ignorer ce filtre
        
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

# Dans le fichier views.py, ajoutez ce code avant la définition de PaiementDetailView
# pour gérer le cas où la classe HistoriqueTransaction n'existerait pas

# Import conditionnel pour historique des transactions
try:
    from .models import HistoriqueTransaction
except ImportError:
    # Fallback - utiliser la table historique_transactions directement si le modèle n'existe pas
    class HistoriqueTransaction:
        objects = None
        
        @staticmethod
        def get_empty_queryset():
            from django.db.models.query import EmptyQuerySet
            return EmptyQuerySet(model=None)

# Puis modifier la méthode get_context_data de PaiementDetailView:

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
        except Exception:
            # Si rien ne fonctionne, initialiser avec une liste vide
            context['historique'] = []
    
    return context

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
            # Utiliser une liste vide si la classe n'existe pas
            context['historique'] = []

        # NOUVEAU CODE: Calculer le montant payé sans utiliser le filtre sub
        if hasattr(paiement.cotisation, 'montant') and hasattr(paiement.cotisation, 'montant_restant'):
            context['montant_paye'] = paiement.cotisation.montant - paiement.cotisation.montant_restant
        else:
            context['montant_paye'] = 0
        
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
                pass
                
        if date_fin:
            try:
                date_fin = datetime.datetime.strptime(date_fin, '%Y-%m-%d').date()
                queryset = queryset.filter(date_envoi__lte=date_fin)
            except ValueError:
                pass
                
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


class RappelDetailView(StaffRequiredMixin, DetailView):
    """
    Vue détaillée d'un rappel.
    """
    model = Rappel
    template_name = 'cotisations/rappel_detail.html'
    context_object_name = 'rappel'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        rappel = self.object
        
        context.update({
            'cotisation': rappel.cotisation,
            'membre': rappel.membre,
            'autres_rappels': Rappel.objects.filter(
                cotisation=rappel.cotisation
            ).exclude(pk=rappel.pk).order_by('-date_envoi'),
        })
        
        return context


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
    
    if form.is_valid():
        # Appliquer les filtres (mêmes filtres que dans CotisationListView.get_queryset)
        if membre := form.cleaned_data.get('membre'):
            queryset = queryset.filter(membre=membre)
        # Autres filtres...
    
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
    
    if type_transaction:
        queryset = queryset.filter(type_transaction=type_transaction)
    
    if date_debut:
        try:
            date_debut = datetime.datetime.strptime(date_debut, '%Y-%m-%d').date()
            queryset = queryset.filter(date_paiement__gte=date_debut)
        except ValueError:
            pass
    
    if date_fin:
        try:
            date_fin = datetime.datetime.strptime(date_fin, '%Y-%m-%d').date()
            queryset = queryset.filter(date_paiement__lte=date_fin)
        except ValueError:
            pass
    
    if mode_paiement_id:
        queryset = queryset.filter(mode_paiement_id=mode_paiement_id)
    
    if membre_id:
        queryset = queryset.filter(cotisation__membre_id=membre_id)
    
    # Exporter selon le format demandé
    if format_export == 'csv':
        return export_utils.export_paiements_csv(queryset)
    elif format_export == 'excel':
        return export_utils.export_paiements_excel(queryset)
    else:
        return HttpResponse(_("Format non supporté"), status=400)


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
    if type_rappel:
        queryset = queryset.filter(type_rappel=type_rappel)
    
    if etat:
        queryset = queryset.filter(etat=etat)
    
    if date_debut:
        try:
            date_debut = datetime.datetime.strptime(date_debut, '%Y-%m-%d').date()
            queryset = queryset.filter(date_envoi__gte=date_debut)
        except ValueError:
            pass
    
    if date_fin:
        try:
            date_fin = datetime.datetime.strptime(date_fin, '%Y-%m-%d').date()
            queryset = queryset.filter(date_envoi__lte=date_fin)
        except ValueError:
            pass
    
    if membre_id:
        queryset = queryset.filter(membre_id=membre_id)
    
    # Exporter selon le format demandé
    if format_export == 'csv':
        return export_utils.export_rappels_csv(queryset)
    elif format_export == 'excel':
        return export_utils.export_rappels_excel(queryset)
    else:
        return HttpResponse(_("Format non supporté"), status=400)


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
        return JsonResponse({'success': False, 'message': str(e)})

# Pour api_baremes_par_type
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
            est_actif = (bareme.date_debut_validite <= today and 
                         (bareme.date_fin_validite is None or bareme.date_fin_validite >= today))
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
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)

@login_required
@require_POST
def bareme_reactive(request):
    """
    Vue pour réactiver un barème inactif.
    """
    bareme_id = request.POST.get('bareme_id')
    date_fin_validite = request.POST.get('date_fin_validite') or None
    
    if not bareme_id:
        messages.error(request, _("Barème non spécifié"))
        return redirect('cotisations:bareme_liste')
    
    try:
        bareme = BaremeCotisation.objects.get(pk=bareme_id)
        
        # Convertir la date de fin si elle est fournie
        if date_fin_validite:
            date_fin_validite = datetime.datetime.strptime(date_fin_validite, '%Y-%m-%d').date()
        
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
        messages.error(request, _("Erreur lors de la réactivation du barème: %(error)s") % {'error': str(e)})
    
    return redirect('cotisations:bareme_liste')

@login_required
def api_generer_recu(request, paiement_id):
    """
    API pour générer un reçu PDF pour un paiement.
    """
    paiement = get_object_or_404(Paiement, pk=paiement_id)
    
    # Vérifier les permissions
    if not request.user.is_staff:
        return HttpResponseForbidden(_("Vous n'avez pas les permissions pour générer ce reçu"))
    
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
    if rappel.etat != 'planifie':
        return JsonResponse({
            'success': False,
            'message': _("Ce rappel est déjà traité.")
        }, encoder=ExtendedJSONEncoder)
    
    try:
        # Marquer comme envoyé
        rappel.etat = 'envoye'
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
        # En cas d'erreur, marquer comme échoué
        rappel.etat = 'echoue'
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
        return JsonResponse({
            'success': False,
            'message': _("Erreur lors de la suppression du rappel: {0}").format(str(e))
        }, encoder=ExtendedJSONEncoder)


# Vue de base pour maintenir la compatibilité avec urls.py
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