# apps/cotisations/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.http import JsonResponse, HttpResponse
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
        
        # Cotisations par mois (pour graphique)
        cotisations_par_mois = []
        paiements_par_mois = []
        
        if periode == 'year':
            for month in range(1, 13):
                month_name = datetime.date(2000, month, 1).strftime('%B')
                
                month_cotisations = Cotisation.objects.filter(
                    date_emission__year=annee,
                    date_emission__month=month
                )
                
                month_paiements = Paiement.objects.filter(
                    date_paiement__year=annee,
                    date_paiement__month=month,
                    type_transaction='paiement'
                )
                
                montant_cotisations = month_cotisations.aggregate(total=Sum('montant')).get('total') or Decimal('0.00')
                montant_paiements = month_paiements.aggregate(total=Sum('montant')).get('total') or Decimal('0.00')
                
                cotisations_par_mois.append({
                    'month': month_name,
                    'total': float(montant_cotisations)
                })
                
                paiements_par_mois.append({
                    'month': month_name,
                    'total': float(montant_paiements)
                })
        
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
            'cotisations_retard': cotisations_retard,
            'cotisations_echeance': cotisations_echeance,
            'nb_cotisations_retard': cotisations_retard.count(),
            'nb_cotisations_echeance': cotisations_echeance.count(),
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
            _("Le paiement a été enregistré avec succès.")
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
            
            form = PaiementForm(form_data, user=request.user, cotisation=cotisation)
            
            if form.is_valid():
                paiement = form.save()
                
                # Recharger la cotisation pour avoir les informations à jour
                cotisation.refresh_from_db()
                
                # Retourner les infos sur le paiement et la cotisation mise à jour
                return JsonResponse({
                    'success': True,
                    'paiement': {
                        'id': paiement.id,
                        'montant': float(paiement.montant),
                        'date_paiement': paiement.date_paiement.strftime('%Y-%m-%dT%H:%M:%S'),
                        'mode_paiement': paiement.mode_paiement.libelle if paiement.mode_paiement else '-',
                        'type_transaction': paiement.get_type_transaction_display(),
                        'reference_paiement': paiement.reference_paiement or ''
                    },
                    'cotisation': {
                        'montant_restant': float(cotisation.montant_restant),
                        'statut_paiement': cotisation.get_statut_paiement_display()
                    },
                    'message': _("Le paiement a été enregistré avec succès.")
                })
            else:
                return JsonResponse({
                    'success': False,
                    'errors': form.errors.as_json(),
                    'message': _("Erreur lors de l'enregistrement du paiement.")
                })
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'message': _("Format de données invalide.")
            }, status=400)
    
    # Pour les requêtes standard
    else:
        form = PaiementForm(request.POST, user=request.user, cotisation=cotisation)
        
        if form.is_valid():
            paiement = form.save()
            
            # Retourner les infos sur le paiement et la cotisation mise à jour
            cotisation.refresh_from_db()
            
            return JsonResponse({
                'success': True,
                'paiement': {
                    'id': paiement.id,
                    'montant': float(paiement.montant),
                    'date_paiement': paiement.date_paiement.strftime('%Y-%m-%dT%H:%M:%S'),
                    'mode_paiement': paiement.mode_paiement.libelle if paiement.mode_paiement else '-',
                    'type_transaction': paiement.get_type_transaction_display(),
                    'reference_paiement': paiement.reference_paiement or ''
                },
                'cotisation': {
                    'montant_restant': float(cotisation.montant_restant),
                    'statut_paiement': cotisation.get_statut_paiement_display()
                },
                'message': _("Le paiement a été enregistré avec succès.")
            })
        else:
            return JsonResponse({
                'success': False,
                'errors': form.errors.as_json(),
                'message': _("Erreur lors de l'enregistrement du paiement.")
            })


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
def rappel_create_ajax(request, cotisation_id):
    """
    Vue AJAX pour créer un rappel depuis la page de détail d'une cotisation.
    """
    cotisation = get_object_or_404(Cotisation, pk=cotisation_id)
    form = RappelForm(request.POST, user=request.user, cotisation=cotisation)
    
    if form.is_valid():
        rappel = form.save()
        
        return JsonResponse({
            'success': True,
            'rappel': {
                'id': rappel.id,
                'type_rappel': rappel.get_type_rappel_display(),
                'date_envoi': rappel.date_envoi.strftime('%d/%m/%Y %H:%M'),
                'etat': rappel.get_etat_display(),
                'niveau': rappel.niveau
            },
            'message': _("Le rappel a été créé avec succès.")
        })
    else:
        return JsonResponse({
            'success': False,
            'errors': form.errors.as_json(),
            'message': _("Erreur lors de la création du rappel.")
        })


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
            # (code similaire à CotisationListView.get_queryset)
            pass
        
        # Selon le format demandé
        if format_export == 'csv':
            return self._export_csv(queryset)
        elif format_export == 'excel':
            return self._export_excel(queryset)
        else:
            return HttpResponse(_("Format non supporté"), status=400)
    
    def _export_csv(self, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="cotisations_{timezone.now().strftime("%Y%m%d")}.csv"'
        
        writer = csv.writer(response)
        
        # En-tête
        writer.writerow([
            _('Référence'), _('Membre'), _('Email'), _('Montant'), 
            _('Montant restant'), _('Date émission'), _('Date échéance'),
            _('Statut paiement'), _('Type de membre')
        ])
        
        # Données
        for cotisation in queryset:
            writer.writerow([
                cotisation.reference,
                f"{cotisation.membre.prenom} {cotisation.membre.nom}",
                cotisation.membre.email,
                cotisation.montant,
                cotisation.montant_restant,
                cotisation.date_emission,
                cotisation.date_echeance,
                cotisation.get_statut_paiement_display(),
                cotisation.type_membre.libelle if cotisation.type_membre else ''
            ])
        
        return response
    
    def _export_excel(self, queryset):
        # Note: Cette fonction serait implémentée pour exporter en Excel
        # Nous renvoyons un message pour l'exemple
        response = HttpResponse(_("Export Excel - À implémenter"))
        return response


@login_required
def api_calculer_montant(request):
    """
    API pour calculer le montant d'une cotisation en fonction du barème sélectionné.
    """
    bareme_id = request.GET.get('bareme_id')
    
    if not bareme_id:
        return JsonResponse({'success': False, 'message': _("Barème non spécifié")})
    
    try:
        bareme = BaremeCotisation.objects.get(pk=bareme_id)
        return JsonResponse({
            'success': True,
            'montant': float(bareme.montant),
            'periodicite': bareme.get_periodicite_display()
        })
    except BaremeCotisation.DoesNotExist:
        return JsonResponse({'success': False, 'message': _("Barème non trouvé")})


@login_required
def api_generer_recu(request, paiement_id):
    """
    API pour générer un reçu PDF pour un paiement.
    """
    # Note: Cette fonction serait implémentée pour générer un PDF
    # Nous renvoyons un message pour l'exemple
    return HttpResponse(_("Génération de reçu - À implémenter"))

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
                    return JsonResponse({
                        'success': False,
                        'message': _("Format de date invalide")
                    }, status=400)
            else:
                # Si envoi immédiat, on marque comme envoyé
                etat = 'envoye'
                form_data['date_envoi'] = timezone.now()
            
            form_data['etat'] = etat
            
            form = RappelForm(form_data, user=request.user, cotisation=cotisation, membre=membre)
            
            if form.is_valid():
                rappel = form.save()
                
                # Pour les rappels à envoyer immédiatement, simuler l'envoi
                if etat == 'envoye':
                    # Ici, vous pouvez ajouter votre logique d'envoi de mail, SMS, etc.
                    pass
                
                # Retourner les infos sur le rappel créé
                return JsonResponse({
                    'success': True,
                    'rappel': {
                        'id': rappel.id,
                        'date_envoi': rappel.date_envoi.strftime('%Y-%m-%dT%H:%M:%S'),
                        'type_rappel': rappel.get_type_rappel_display(),
                        'niveau': rappel.niveau,
                        'etat': rappel.get_etat_display(),
                        'contenu': rappel.contenu
                    },
                    'message': _("Le rappel a été créé avec succès.")
                })
            else:
                return JsonResponse({
                    'success': False,
                    'errors': form.errors.as_json(),
                    'message': _("Erreur lors de la création du rappel.")
                })
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'message': _("Format de données invalide.")
            }, status=400)
    
    # Pour les requêtes standard
    else:
        form = RappelForm(request.POST, user=request.user, cotisation=cotisation, membre=membre)
        
        if form.is_valid():
            rappel = form.save()
            
            return JsonResponse({
                'success': True,
                'rappel': {
                    'id': rappel.id,
                    'date_envoi': rappel.date_envoi.strftime('%Y-%m-%dT%H:%M:%S'),
                    'type_rappel': rappel.get_type_rappel_display(),
                    'niveau': rappel.niveau,
                    'etat': rappel.get_etat_display(),
                    'contenu': rappel.contenu
                },
                'message': _("Le rappel a été créé avec succès.")
            })
        else:
            return JsonResponse({
                'success': False,
                'errors': form.errors.as_json(),
                'message': _("Erreur lors de la création du rappel.")
            })
        
# Vue de base pour maintenir la compatibilité avec urls.py
dashboard = DashboardView.as_view()
cotisation_list = CotisationListView.as_view()
cotisation_detail = CotisationDetailView.as_view()
cotisation_create = CotisationCreateView.as_view()
cotisation_update = CotisationUpdateView.as_view()
cotisation_delete = CotisationDeleteView.as_view()
paiement_list = lambda request: HttpResponse("Liste des paiements - Vue à implémenter")
paiement_detail = lambda request, pk: HttpResponse(f"Détail du paiement {pk} - Vue à implémenter")
paiement_create = PaiementCreateView.as_view()
paiement_update = PaiementUpdateView.as_view()
paiement_delete = PaiementDeleteView.as_view()
bareme_list = BaremeCotisationListView.as_view()
bareme_detail = lambda request, pk: HttpResponse(f"Détail du barème {pk} - Vue à implémenter")
bareme_create = BaremeCotisationCreateView.as_view()
bareme_update = BaremeCotisationUpdateView.as_view()
bareme_delete = BaremeCotisationDeleteView.as_view()
rappel_list = lambda request: HttpResponse("Liste des rappels - Vue à implémenter")
rappel_detail = lambda request, pk: HttpResponse(f"Détail du rappel {pk} - Vue à implémenter")
rappel_create = RappelCreateView.as_view()
corbeille = CotisationCorbeilleView.as_view()
statistiques = lambda request: HttpResponse("Statistiques - Vue à implémenter")
export = ExportCotisationsView.as_view()
import_cotisations = ImportCotisationsView.as_view()