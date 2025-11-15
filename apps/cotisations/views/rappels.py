"""
Vues pour la gestion des rappels de cotisation.

Ce module contient toutes les vues CRUD pour les rappels de cotisation,
ainsi que les fonctions pour l'envoi de rappels (email, SMS, courrier).
"""

# Importations depuis utils.py
from apps.cotisations.views.utils import (
    StaffRequiredMixin, LoginRequiredMixin, View,
    CreateView, ListView, DetailView, UpdateView, DeleteView,
    login_required, require_http_methods, get_object_or_404,
    JsonResponse, messages, redirect, reverse, timezone,
    logger, json, _,
    Rappel, Cotisation, Count,
    RAPPEL_ETAT_PLANIFIE, RAPPEL_ETAT_ENVOYE, RAPPEL_ETAT_ECHOUE,
    RappelForm, dt
)
import datetime


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
                    date_envoi = dt.fromisoformat(date_planifiee_str.replace('Z', '+00:00'))
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
