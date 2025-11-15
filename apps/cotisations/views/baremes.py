"""
Vues pour la gestion des barèmes de cotisation.

Ce module contient toutes les vues CRUD pour les barèmes de cotisation.
"""

# Importations depuis utils.py
from apps.cotisations.views.utils import (
    StaffRequiredMixin, ListView, DetailView, CreateView, UpdateView, DeleteView,
    login_required, require_POST, redirect, messages, reverse_lazy, timezone,
    logger, Decimal, Sum, _,
    BaremeCotisation, Cotisation, BaremeCotisationForm
)
import datetime


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
