"""
Vues pour la gestion des paiements de cotisation.

Ce module contient toutes les vues CRUD pour les paiements,
ainsi que les vues pour la corbeille et la restauration.
"""

# Importations depuis utils.py
from .utils import (
    StaffRequiredMixin, TrashViewMixin, RestoreViewMixin, View,
    ListView, DetailView, CreateView, UpdateView, DeleteView,
    require_POST, get_object_or_404,
    JsonResponse, messages, redirect, reverse, timezone,
    logger, json, Q, Sum, Decimal, _,
    Cotisation, Paiement, ModePaiement,
    PaiementForm, ExtendedJSONEncoder,
    connection
)
import datetime


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
    from ..models import HistoriqueTransaction
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
    success_url = 'cotisations:paiement_liste'
