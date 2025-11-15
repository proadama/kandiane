"""
Vues pour la gestion des cotisations.

Ce module contient toutes les vues CRUD pour les cotisations,
ainsi que les vues pour la corbeille et la restauration.
"""

# Importations depuis utils.py
from .utils import (
    StaffRequiredMixin, LoginRequiredMixin, TrashViewMixin, RestoreViewMixin, View,
    ListView, DetailView, CreateView, UpdateView, DeleteView,
    get_object_or_404, redirect, reverse, reverse_lazy, messages, timezone,
    logger, Q, Sum, ExpressionWrapper, DecimalField, Decimal, _,
    Cotisation, HistoriqueCotisation, Membre, BaremeCotisation,
    CotisationForm, CotisationSearchForm, PaiementForm, RappelForm
)


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

        # Optimiser les requêtes pour éviter N+1
        return queryset.select_related('membre', 'type_membre', 'statut', 'bareme')

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

    def get_queryset(self):
        """Optimiser la requête pour éviter N+1"""
        return Cotisation.objects.select_related('membre', 'type_membre', 'statut', 'bareme')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cotisation = self.object

        # Paiements liés à cette cotisation avec optimisation
        context['paiements'] = cotisation.paiements.select_related(
            'mode_paiement', 'statut'
        ).order_by('-date_paiement')

        # Rappels envoyés avec optimisation
        context['rappels'] = cotisation.rappels.select_related('membre').order_by('-date_envoi')

        # Historique des modifications avec optimisation
        context['historique'] = HistoriqueCotisation.objects.filter(
            cotisation=cotisation
        ).select_related('utilisateur').order_by('-date_action')

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


# ============================================================================
# Vues de corbeille et restauration
# ============================================================================

class CotisationCorbeilleView(StaffRequiredMixin, TrashViewMixin, ListView):
    """
    Vue pour afficher les cotisations supprimées (corbeille).
    """
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
    """
    Vue pour restaurer une cotisation individuelle.
    """
    def get(self, request, pk):
        cotisation = get_object_or_404(Cotisation.objects.only_deleted(), pk=pk)
        cotisation.restore()
        messages.success(request, _("La cotisation a été restaurée avec succès."))
        return redirect('cotisations:corbeille')


class SupprimerDefinitivementCotisationView(StaffRequiredMixin, LoginRequiredMixin, View):
    """
    Vue pour supprimer définitivement une cotisation.
    """
    def get(self, request, pk):
        cotisation = get_object_or_404(Cotisation.objects.only_deleted(), pk=pk)
        cotisation.delete(hard=True)
        messages.success(request, _("La cotisation a été supprimée définitivement."))
        return redirect('cotisations:corbeille')


class CotisationRestoreView(StaffRequiredMixin, RestoreViewMixin, View):
    """
    Vue pour restaurer une cotisation depuis la corbeille (alternative).
    """
    model = Cotisation
    success_url = reverse_lazy('cotisations:cotisation_liste')

    def get_success_message(self):
        return _("La cotisation a été restaurée avec succès.")
