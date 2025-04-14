# apps/membres/views.py
import csv
import io
import json
import logging
from datetime import datetime
import traceback
import sys
from django.http import HttpResponseRedirect

from django.db.models.functions import ExtractMonth
from django.contrib import messages
from django.db import transaction
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import (
    CreateView, DeleteView, DetailView, FormView, ListView, TemplateView, UpdateView, View
)

from openpyxl import Workbook
from openpyxl import load_workbook

from apps.core.mixins import StaffRequiredMixin, TrashViewMixin, RestoreViewMixin
from apps.core.models import Statut
from apps.membres.forms import (
    MembreForm, TypeMembreForm, MembreTypeMembreForm, 
    MembreImportForm, MembreSearchForm
)
from apps.membres.models import Membre, TypeMembre, MembreTypeMembre, HistoriqueMembre
from django.db.models import F, IntegerField
from django.db.models.functions import ExtractMonth
from django.utils.crypto import get_random_string
from apps.accounts.models import CustomUser


logger = logging.getLogger(__name__)


class DashboardView(TemplateView):
    """
    Vue du tableau de bord pour les statistiques sur les membres
    """
    template_name = 'membres/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Récupérer la date actuelle et les statistiques de base
        today = timezone.now().date()
        total_membres = Membre.objects.count()
        membres_actifs = Membre.objects.actifs().count()
        
        # Types de membres avec leur nombre
        types_membres = TypeMembre.objects.annotate(
            count=Count('membres_historique__membre', 
                          filter=Q(membres_historique__date_debut__lte=today, 
                                 membres_historique__date_fin__isnull=True),
                          distinct=True)
        ).order_by('-count')
        
        # Adhésions récentes
        adhesions_recentes = Membre.objects.order_by('-date_adhesion')[:10]
        
        # Statistiques sur les membres
        membres_par_mois = Membre.objects.annotate(
        month=ExtractMonth('date_adhesion', output_field=IntegerField())
        ).values('month').annotate(count=Count('id')).order_by('month')
        
        # Membres par statut
        membres_par_statut = Membre.objects.filter(
            statut__isnull=False
        ).values('statut__nom').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Membres avec/sans compte utilisateur
        avec_compte = Membre.objects.filter(utilisateur__isnull=False).count()
        sans_compte = total_membres - avec_compte
        
        # Construire les données pour les graphiques
        chart_types = [
            {'name': t.libelle, 'value': t.count} for t in types_membres
        ]
        
        chart_monthly = []
        for i in range(1, 13):
            month_name = datetime(2000, i, 1).strftime('%B')
            count = next((item['count'] for item in membres_par_mois if item['month'] == i), 0)
            chart_monthly.append({'month': month_name, 'count': count})
        
        chart_statuts = [
            {'name': s['statut__nom'] or 'Sans statut', 'value': s['count']} 
            for s in membres_par_statut
        ]
        
        chart_comptes = [
            {'name': 'Avec compte', 'value': avec_compte},
            {'name': 'Sans compte', 'value': sans_compte}
        ]
        
        context.update({
            'total_membres': total_membres,
            'membres_actifs': membres_actifs,
            'types_membres': types_membres,
            'adhesions_recentes': adhesions_recentes,
            'chart_types': json.dumps(chart_types),
            'chart_monthly': json.dumps(chart_monthly),
            'chart_statuts': json.dumps(chart_statuts),
            'chart_comptes': json.dumps(chart_comptes),
        })
        
        return context


class MembreListView(ListView):
    """
    Vue pour afficher la liste des membres avec recherche et filtrage
    """
    model = Membre
    template_name = 'membres/liste.html'
    context_object_name = 'membres'
    paginate_by = 20
    
    def get_queryset(self):
        # On commence avec un queryset vide mais qui sera rempli par les filtres
        queryset = Membre.objects.all()
        form = MembreSearchForm(self.request.GET)
        
        if form.is_valid():
            # Variables pour stocker les différents critères de filtrage
            filters = {}
            term = form.cleaned_data.get('terme')
            type_membre_id = form.cleaned_data.get('type_membre').id if form.cleaned_data.get('type_membre') else None
            statut_id = form.cleaned_data.get('statut').id if form.cleaned_data.get('statut') else None
            date_adhesion_min = form.cleaned_data.get('date_adhesion_min')
            date_adhesion_max = form.cleaned_data.get('date_adhesion_max')
            age_min = form.cleaned_data.get('age_min')
            age_max = form.cleaned_data.get('age_max')
            cotisations_impayees = form.cleaned_data.get('cotisations_impayees')
            avec_compte = form.cleaned_data.get('avec_compte')
            actif = form.cleaned_data.get('actif')
            
            # Appliquer les filtres standards Django (qui fonctionnent sur n'importe quel QuerySet)
            if date_adhesion_min:
                queryset = queryset.filter(date_adhesion__gte=date_adhesion_min)
            if date_adhesion_max:
                queryset = queryset.filter(date_adhesion__lte=date_adhesion_max)
                
            # Construire un filtre Q complexe pour gérer tous les critères
            q_objects = Q()
            
            # Ajouter les filtres manuellement avec des expressions Q
            if term:
                q_objects &= (
                    Q(nom__icontains=term) | 
                    Q(prenom__icontains=term) | 
                    Q(email__icontains=term) | 
                    Q(telephone__icontains=term) |
                    Q(code_postal__icontains=term) |
                    Q(ville__icontains=term)
                )
            
            if type_membre_id:
                q_objects &= Q(
                    types_historique__type_membre_id=type_membre_id,
                    types_historique__date_debut__lte=timezone.now().date(),
                    types_historique__date_fin__isnull=True
                )
            
            if statut_id:
                q_objects &= Q(statut_id=statut_id)
                
            # Applique tous les filtres Q construits
            if q_objects:
                queryset = queryset.filter(q_objects).distinct()
                
            # Appliquer les filtres spéciaux qui ne peuvent pas être facilement exprimés avec Q
            if age_min is not None or age_max is not None:
                queryset = Membre.objects.par_age(age_min=age_min, age_max=age_max)
                
            if cotisations_impayees:
                queryset = Membre.objects.avec_cotisations_impayees()
                
            if avec_compte == 'avec':
                queryset = queryset.filter(utilisateur__isnull=False)
            elif avec_compte == 'sans':
                queryset = queryset.filter(utilisateur__isnull=True)
                
            if actif == 'actif':
                queryset = Membre.objects.actifs()
            elif actif == 'inactif':
                queryset = Membre.objects.inactifs()
        
        # Précharger les relations pour optimiser les performances
        return queryset.select_related('statut').prefetch_related('types')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Ajouter le formulaire de recherche
        context['search_form'] = MembreSearchForm(self.request.GET)
        
        # Statistiques rapides
        context['total_membres'] = Membre.objects.count()
        context['membres_actifs'] = Membre.objects.actifs().count()
        
        return context


class MembreDetailView(DetailView):
    """
    Vue pour afficher les détails d'un membre
    """
    model = Membre
    template_name = 'membres/detail.html'
    context_object_name = 'membre'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        membre = self.object
        
        # Types de membre actuels et historiques
        context['types_actifs'] = membre.get_types_actifs()
        context['historique_types'] = MembreTypeMembre.objects.filter(
            membre=membre
        ).select_related('type_membre', 'modifie_par').order_by('-date_debut')
        
        # Formulaire pour ajouter un nouveau type
        context['type_form'] = MembreTypeMembreForm(membre=membre, user=self.request.user)
        
        # Historique des modifications
        context['historique'] = HistoriqueMembre.objects.filter(
            membre=membre
        ).select_related('utilisateur').order_by('-created_at')[:10]
        
        # Informations supplémentaires calculées
        context['age'] = membre.age()
        context['anciennete'] = (timezone.now().date() - membre.date_adhesion).days // 365
        
        # Cotisations (si l'application est disponible)
        try:
            from apps.cotisations.models import Cotisation
            context['cotisations'] = Cotisation.objects.filter(
                membre=membre
            ).order_by('-annee', '-mois')[:5]
            context['nb_cotisations_impayees'] = Cotisation.objects.filter(
                membre=membre, 
                statut_paiement__in=['non_payée', 'partiellement_payée']
            ).count()
        except ImportError:
            context['cotisations'] = None
        
        # Événements (si l'application est disponible)
        try:
            from apps.evenements.models import Inscription
            context['inscriptions'] = Inscription.objects.filter(
                membre=membre
            ).select_related('evenement').order_by('-date_inscription')[:5]
        except ImportError:
            context['inscriptions'] = None
        
        # Documents (si l'application est disponible)
        try:
            from apps.documents.models import Document
            context['documents'] = Document.objects.filter(
                reference_id=membre.id,
                type_document__nom='membre'
            ).order_by('-date_upload')
        except ImportError:
            context['documents'] = None
        
        return context


class MembreCreateView(StaffRequiredMixin, CreateView):
    """
    Vue pour créer un nouveau membre
    """
    model = Membre
    form_class = MembreForm
    template_name = 'membres/form.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        try:
            # Enregistrer le membre
            membre = form.save()
            
            # Créer un compte utilisateur si demandé
            if form.cleaned_data.get('creer_compte'):
                username = f"{membre.prenom.lower()}.{membre.nom.lower()}"
                username = username.replace(' ', '_')
                base_username = username
                counter = 1
                
                # Éviter les doublons
                while CustomUser.objects.filter(username=username).exists():
                    username = f"{base_username}{counter}"
                    counter += 1
                
                # Utiliser le mot de passe fourni ou en générer un
                password = form.cleaned_data.get('password')
                if not password:
                    password = get_random_string(length=12)
                
                # Créer l'utilisateur
                user = CustomUser.objects.create_user(
                    username=username,
                    email=membre.email,
                    password=password,
                    first_name=membre.prenom,
                    last_name=membre.nom
                )
                
                # Lier à ce membre
                membre.utilisateur = user
                membre.save(update_fields=['utilisateur'])
                
                # Message avec identifiants
                messages.success(
                    self.request,
                    _("Le membre %(name)s a été créé avec succès. Un compte utilisateur a été créé avec les identifiants:\nNom d'utilisateur: %(username)s\nMot de passe: %(password)s") % {
                        'name': membre.nom_complet,
                        'username': username,
                        'password': password
                    }
                )
            else:
                messages.success(
                    self.request, 
                    _("Le membre %(name)s a été créé avec succès.") % {'name': membre.nom_complet}
                )
            
            # Ajouter un enregistrement dans l'historique
            HistoriqueMembre.objects.create(
                membre=membre,
                utilisateur=self.request.user,
                action='creation',
                description=_("Création du membre"),
                donnees_apres={
                    field: str(value) for field, value in form.cleaned_data.items() 
                    if field not in ['types_membre', 'photo', 'creer_compte', 'password']
                }
            )
            
            return redirect(membre.get_absolute_url())
        except Exception as e:
            # Journaliser l'erreur
            logger.error(f"Erreur lors de la création d'un membre: {str(e)}")
            # Afficher un message d'erreur à l'utilisateur
            messages.error(self.request, f"Une erreur s'est produite: {str(e)}")
            # Re-afficher le formulaire avec les données
            return self.form_invalid(form)

class MembreCreateView(StaffRequiredMixin, CreateView):
    """
    Vue pour créer un nouveau membre
    """
    model = Membre
    form_class = MembreForm
    template_name = 'membres/form.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def post(self, request, *args, **kwargs):
        """Surcharge pour diagnostiquer les problèmes"""
        print("*** POST reçu dans MembreCreateView ***")
        print(f"Données du formulaire: {request.POST}")
        return super().post(request, *args, **kwargs)
    
    def form_invalid(self, form):
        """Surcharge pour mieux détecter les erreurs de validation"""
        print("*** FORM INVALID appelé ***")
        print(f"Erreurs du formulaire: {form.errors}")
        print(f"Non-field errors: {form.non_field_errors()}")
        
        # Affichage détaillé des erreurs pour l'utilisateur
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(self.request, f"Erreur dans {field}: {error}")
        
        return super().form_invalid(form)
    
    def form_valid(self, form):
        """Surcharge pour diagnostiquer les problèmes de traitement"""
        print("*** FORM VALID appelé ***")
        print(f"Données validées: {form.cleaned_data}")
        
        try:
            # Enregistrer le membre avec la méthode la plus simple possible
            membre = form.save()
            print(f"Membre créé avec ID: {membre.id}")
            
            # Essayer de créer un utilisateur séparément pour éviter les problèmes
            if form.cleaned_data.get('creer_compte'):
                print("Tentative de création de compte utilisateur")
                username = f"{membre.prenom.lower()}.{membre.nom.lower()}".replace(' ', '_')
                base_username = username
                counter = 1
                
                # Éviter les doublons
                while CustomUser.objects.filter(username=username).exists():
                    username = f"{base_username}{counter}"
                    counter += 1
                
                # Mot de passe
                password = form.cleaned_data.get('password')
                if not password:
                    password = get_random_string(length=12)
                
                # Créer l'utilisateur manuellement
                user = CustomUser.objects.create_user(
                    username=username,
                    email=membre.email,
                    password=password,
                    first_name=membre.prenom,
                    last_name=membre.nom
                )
                print(f"Utilisateur créé avec ID: {user.id}")
                
                # Lier à ce membre
                membre.utilisateur = user
                membre.save(update_fields=['utilisateur'])
                print("Membre mis à jour avec utilisateur")
                
                # Message avec identifiants
                messages.success(
                    self.request,
                    _(f"Le membre {membre.nom_complet} a été créé avec succès. Un compte utilisateur a été créé avec les identifiants:\nNom d'utilisateur: {username}\nMot de passe: {password}")
                )
            else:
                messages.success(
                    self.request, 
                    _(f"Le membre {membre.nom_complet} a été créé avec succès.")
                )
            
            # Redirection explicite sans passer par les méthodes standards
            print("Redirection vers le détail du membre")
            return HttpResponseRedirect(reverse('membres:membre_detail', kwargs={'pk': membre.pk}))
            
        except Exception as e:
            # Capturer et afficher les erreurs en détail
            print("*** EXCEPTION dans form_valid ***")
            print(f"Erreur: {str(e)}")
            print("Traceback:")
            traceback.print_exc(file=sys.stdout)
            
            # Informer l'utilisateur
            messages.error(self.request, f"Erreur lors de la création du membre: {str(e)}")
            return self.form_invalid(form)


class MembreDeleteView(StaffRequiredMixin, DeleteView):
    """
    Vue pour supprimer un membre
    """
    model = Membre
    template_name = 'membres/confirmer_suppression.html'
    success_url = reverse_lazy('membres:membre_liste')
    
    def delete(self, request, *args, **kwargs):
        membre = self.get_object()
        
        # Enregistrer l'action dans l'historique
        HistoriqueMembre.objects.create(
            membre=membre,
            utilisateur=request.user,
            action='suppression',
            description=_("Suppression du membre"),
            donnees_avant={
                'nom': membre.nom,
                'prenom': membre.prenom,
                'email': membre.email,
                'date_adhesion': str(membre.date_adhesion)
            }
        )
        
        # Suppression logique explicite
        membre.deleted_at = timezone.now()
        membre.save(update_fields=['deleted_at'])
        
        messages.success(
            request, 
            _("Le membre %(name)s a été supprimé avec succès.") % {'name': membre.nom_complet}
        )
        return redirect(self.success_url)


class TypeMembreListView(ListView):
    """
    Vue pour afficher la liste des types de membres
    """
    model = TypeMembre
    template_name = 'membres/type_membre_liste.html'
    context_object_name = 'types_membres'
    
    def get_queryset(self):
        return TypeMembre.objects.avec_nombre_membres().par_ordre_affichage()


class TypeMembreCreateView(StaffRequiredMixin, CreateView):
    """
    Vue pour créer un nouveau type de membre
    """
    model = TypeMembre
    form_class = TypeMembreForm
    template_name = 'membres/type_membre_form.html'
    success_url = reverse_lazy('membres:type_membre_liste')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request, 
            _("Le type de membre %(name)s a été créé avec succès.") % {'name': form.instance.libelle}
        )
        return response


class TypeMembreUpdateView(StaffRequiredMixin, UpdateView):
    """
    Vue pour modifier un type de membre existant
    """
    model = TypeMembre
    form_class = TypeMembreForm
    template_name = 'membres/type_membre_form.html'
    success_url = reverse_lazy('membres:type_membre_liste')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request, 
            _("Le type de membre %(name)s a été modifié avec succès.") % {'name': form.instance.libelle}
        )
        return response


class TypeMembreDeleteView(StaffRequiredMixin, DeleteView):
    """
    Vue pour supprimer un type de membre
    """
    model = TypeMembre
    template_name = 'membres/type_membre_confirmer_suppression.html'
    success_url = reverse_lazy('membres:type_membre_liste')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Nombre de membres actifs de ce type
        context['nb_membres_actifs'] = self.object.nb_membres_actifs()
        return context
    
    def delete(self, request, *args, **kwargs):
        type_membre = self.get_object()
        
        # Suppression logique (soft delete)
        type_membre.delete()
        
        messages.success(
            request, 
            _("Le type de membre %(name)s a été supprimé avec succès.") % {'name': type_membre.libelle}
        )
        return redirect(self.success_url)


class MembreTypeMembreCreateView(StaffRequiredMixin, CreateView):
    """
    Vue pour ajouter un type de membre à un membre
    """
    model = MembreTypeMembre
    form_class = MembreTypeMembreForm
    template_name = 'membres/membre_type_membre_form.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        self.membre = get_object_or_404(Membre, pk=self.kwargs['membre_id'])
        kwargs['membre'] = self.membre
        kwargs['user'] = self.request.user
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['membre'] = self.membre
        return context
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request, 
            _("Le type de membre %(type)s a été ajouté avec succès à %(name)s.") % {
                'type': form.instance.type_membre.libelle,
                'name': form.instance.membre.nom_complet
            }
        )
        return response
    
    def get_success_url(self):
        return reverse('membres:membre_detail', kwargs={'pk': self.membre.pk})


class MembreTypeMembreUpdateView(StaffRequiredMixin, UpdateView):
    """
    Vue pour modifier l'association entre un membre et un type de membre
    """
    model = MembreTypeMembre
    form_class = MembreTypeMembreForm
    template_name = 'membres/membre_type_membre_form.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['membre'] = self.object.membre
        kwargs['user'] = self.request.user
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['membre'] = self.object.membre
        context['is_update'] = True
        return context
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request, 
            _("L'association de type de membre a été modifiée avec succès.")
        )
        return response
    
    def get_success_url(self):
        return reverse('membres:membre_detail', kwargs={'pk': self.object.membre.pk})


class MembreTypeMembreTerminerView(StaffRequiredMixin, View):
    """
    Vue pour terminer l'association entre un membre et un type de membre
    """
    def post(self, request, pk):
        association = get_object_or_404(MembreTypeMembre, pk=pk)
        membre = association.membre
        
        # Date de fin par défaut aujourd'hui
        date_fin = timezone.now().date()
        commentaire = request.POST.get('commentaire', '')
        
        # Mettre à jour l'association
        association.date_fin = date_fin
        association.commentaire = commentaire
        association.modifie_par = request.user
        association.save()
        
        messages.success(
            request, 
            _("L'association avec le type %(type)s a été terminée.") % {
                'type': association.type_membre.libelle
            }
        )
        
        return redirect('membres:membre_detail', pk=membre.pk)


class MembreImportView(StaffRequiredMixin, FormView):
    """
    Vue pour importer des membres depuis un fichier CSV ou Excel
    """
    form_class = MembreImportForm
    template_name = 'membres/import.html'
    success_url = reverse_lazy('membres:membre_liste')
    
    def form_valid(self, form):
        fichier = form.cleaned_data['fichier']
        extension = fichier.name.split('.')[-1].lower()
        
        type_membre = form.cleaned_data['type_membre']
        statut = form.cleaned_data['statut']
        
        # Préparer les résultats
        resultats = {
            'importes': 0,
            'erreurs': 0,
            'maj': 0,
            'messages': []
        }
        
        try:
            if extension == 'csv':
                self._process_csv(fichier, form, type_membre, statut, resultats)
            else:  # xlsx ou xls
                self._process_excel(fichier, type_membre, statut, resultats)
                
            # Message de succès
            message = _("Importation terminée: %(importes)s membres importés, %(maj)s mis à jour, %(erreurs)s erreurs.") % {
                'importes': resultats['importes'],
                'maj': resultats['maj'],
                'erreurs': resultats['erreurs']
            }
            messages.success(self.request, message)
            
            # Ajouter des messages détaillés si nécessaire
            for msg in resultats['messages']:
                messages.info(self.request, msg)
            
        except Exception as e:
            logger.error(f"Erreur lors de l'importation: {str(e)}")
            messages.error(self.request, _("Une erreur s'est produite lors de l'importation: %(error)s") % {'error': str(e)})
        
        return super().form_valid(form)
    
    def _process_csv(self, fichier, form, type_membre, statut, resultats):
        """Traiter un fichier CSV"""
        delimiter = form.cleaned_data['delimiter']
        has_header = form.cleaned_data['header']
        
        # Lire le fichier CSV
        decoded_file = fichier.read().decode('utf-8')
        io_string = io.StringIO(decoded_file)
        
        reader = csv.reader(io_string, delimiter=delimiter)
        
        # Ignorer la première ligne si c'est un en-tête
        if has_header:
            next(reader)
        
        with transaction.atomic():
            for i, row in enumerate(reader, start=1):
                try:
                    # Vérifier que les données sont valides
                    if len(row) < 3:  # Au minimum: nom, prénom, email
                        resultats['messages'].append(_("Ligne %(line)d: Données insuffisantes") % {'line': i})
                        resultats['erreurs'] += 1
                        continue
                    
                    # Récupérer les données de base
                    nom = row[0].strip()
                    prenom = row[1].strip()
                    email = row[2].strip()
                    
                    if not nom or not prenom or not email:
                        resultats['messages'].append(_("Ligne %(line)d: Données incomplètes") % {'line': i})
                        resultats['erreurs'] += 1
                        continue
                    
                    # Vérifier si le membre existe déjà
                    membre_existant = Membre.objects.filter(email=email).first()
                    
                    if membre_existant:
                        # Mettre à jour le membre existant si nécessaire
                        if membre_existant.nom != nom or membre_existant.prenom != prenom:
                            membre_existant.nom = nom
                            membre_existant.prenom = prenom
                            membre_existant.save(update_fields=['nom', 'prenom'])
                            resultats['maj'] += 1
                        
                        # Ajouter le type de membre s'il n'existe pas déjà
                        if not membre_existant.est_type_actif(type_membre):
                            membre_existant.ajouter_type(type_membre)
                    else:
                        # Créer un nouveau membre
                        date_adhesion = timezone.now().date()
                        
                        # Données optionnelles (si disponibles)
                        telephone = row[3].strip() if len(row) > 3 else None
                        adresse = row[4].strip() if len(row) > 4 else None
                        
                        # Créer le membre
                        membre = Membre.objects.create(
                            nom=nom,
                            prenom=prenom,
                            email=email,
                            telephone=telephone,
                            adresse=adresse,
                            date_adhesion=date_adhesion,
                            statut=statut
                        )
                        
                        # Ajouter le type de membre
                        membre.ajouter_type(type_membre)
                        
                        resultats['importes'] += 1
                    
                except Exception as e:
                    resultats['messages'].append(_("Ligne %(line)d: %(error)s") % {'line': i, 'error': str(e)})
                    resultats['erreurs'] += 1
    
    def _process_excel(self, fichier, type_membre, statut, resultats):
        """Traiter un fichier Excel"""
        wb = load_workbook(fichier)
        sheet = wb.active
        
        # Déterminer si la première ligne est un en-tête (on suppose que oui)
        has_header = True
        
        with transaction.atomic():
            rows = list(sheet.rows)
            start_idx = 1 if has_header else 0
            
            for i, row in enumerate(rows[start_idx:], start=start_idx+1):
                try:
                    # Récupérer les valeurs des cellules
                    nom = row[0].value.strip() if row[0].value else ""
                    prenom = row[1].value.strip() if row[1].value else ""
                    email = row[2].value.strip() if row[2].value else ""
                    
                    if not nom or not prenom or not email:
                        resultats['messages'].append(_("Ligne %(line)d: Données incomplètes") % {'line': i})
                        resultats['erreurs'] += 1
                        continue
                    
                    # Vérifier si le membre existe déjà
                    membre_existant = Membre.objects.filter(email=email).first()
                    
                    if membre_existant:
                        # Mettre à jour le membre existant si nécessaire
                        if membre_existant.nom != nom or membre_existant.prenom != prenom:
                            membre_existant.nom = nom
                            membre_existant.prenom = prenom
                            membre_existant.save(update_fields=['nom', 'prenom'])
                            resultats['maj'] += 1
                        
                        # Ajouter le type de membre s'il n'existe pas déjà
                        if not membre_existant.est_type_actif(type_membre):
                            membre_existant.ajouter_type(type_membre)
                    else:
                        # Créer un nouveau membre
                        date_adhesion = timezone.now().date()
                        
                        # Données optionnelles (si disponibles)
                        telephone = row[3].value if len(row) > 3 and row[3].value else None
                        adresse = row[4].value if len(row) > 4 and row[4].value else None
                        
                        # Créer le membre
                        membre = Membre.objects.create(
                            nom=nom,
                            prenom=prenom,
                            email=email,
                            telephone=telephone,
                            adresse=adresse,
                            date_adhesion=date_adhesion,
                            statut=statut
                        )
                        
                        # Ajouter le type de membre
                        membre.ajouter_type(type_membre)
                        
                        resultats['importes'] += 1
                
                except Exception as e:
                    logger.error(f"Erreur ligne {i}: {str(e)}")
                    resultats['messages'].append(_("Ligne %(line)d: %(error)s") % {'line': i, 'error': str(e)})
                    resultats['erreurs'] += 1


class MembreExportView(StaffRequiredMixin, View):
    """
    Vue pour exporter la liste des membres au format CSV ou Excel
    """
    def get(self, request):
        format_export = request.GET.get('format', 'csv')
        
        # Récupérer les filtres de recherche pour les appliquer à l'export
        form = MembreSearchForm(request.GET)
        queryset = Membre.objects.all()
        
        if form.is_valid():
            # Appliquer les mêmes filtres que la vue liste
            if term := form.cleaned_data.get('terme'):
                queryset = queryset.recherche(term)
            
            if type_membre := form.cleaned_data.get('type_membre'):
                queryset = queryset.par_type(type_membre.id)
            
            if statut := form.cleaned_data.get('statut'):
                queryset = queryset.par_statut(statut.id)
            
            if date_min := form.cleaned_data.get('date_adhesion_min'):
                queryset = queryset.filter(date_adhesion__gte=date_min)
                
            if date_max := form.cleaned_data.get('date_adhesion_max'):
                queryset = queryset.filter(date_adhesion__lte=date_max)
            
            if age_min := form.cleaned_data.get('age_min'):
                queryset = queryset.par_age(age_min=age_min)
                
            if age_max := form.cleaned_data.get('age_max'):
                queryset = queryset.par_age(age_max=age_max)
            
            if form.cleaned_data.get('cotisations_impayees'):
                queryset = queryset.avec_cotisations_impayees()
            
            if compte := form.cleaned_data.get('avec_compte'):
                if compte == 'avec':
                    queryset = queryset.avec_compte_utilisateur()
                elif compte == 'sans':
                    queryset = queryset.sans_compte_utilisateur()
            
            if actif := form.cleaned_data.get('actif'):
                if actif == 'actif':
                    queryset = queryset.actifs()
                elif actif == 'inactif':
                    queryset = queryset.inactifs()
        
        # Précharger les relations pour optimiser
        membres = queryset.select_related('statut').prefetch_related('types')
        
        # Définir les champs à exporter
        champs = [
            'id', 'nom', 'prenom', 'email', 'telephone', 'adresse', 
            'code_postal', 'ville', 'pays', 'date_adhesion', 'date_naissance',
            'statut', 'types_actifs'
        ]
        
        # Générer le nom du fichier avec la date
        date_str = timezone.now().strftime('%Y%m%d')
        
        if format_export == 'excel':
            return self._export_excel(membres, champs, date_str)
        else:  # csv par défaut
            return self._export_csv(membres, champs, date_str)
    
    def _export_csv(self, membres, champs, date_str):
        """Exporter au format CSV"""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="membres_{date_str}.csv"'
        
        writer = csv.writer(response)
        
        # Écrire l'en-tête
        header = [
            _('ID'), _('Nom'), _('Prénom'), _('Email'), _('Téléphone'), 
            _('Adresse'), _('Code postal'), _('Ville'), _('Pays'),
            _('Date d\'adhésion'), _('Date de naissance'),
            _('Statut'), _('Types de membre')
        ]
        writer.writerow(header)
        
        # Écrire les données
        for membre in membres:
            row = []
            for champ in champs:
                if champ == 'statut':
                    row.append(membre.statut.nom if membre.statut else '')
                elif champ == 'types_actifs':
                    types = ", ".join([t.libelle for t in membre.get_types_actifs()])
                    row.append(types)
                else:
                    row.append(getattr(membre, champ, ''))
            writer.writerow(row)
        
        return response
    
    def _export_excel(self, membres, champs, date_str):
        """Exporter au format Excel"""
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="membres_{date_str}.xlsx"'
        
        # Créer un nouveau classeur Excel
        wb = Workbook()
        ws = wb.active
        ws.title = _("Membres")
        
        # Écrire l'en-tête
        header = [
            _('ID'), _('Nom'), _('Prénom'), _('Email'), _('Téléphone'), 
            _('Adresse'), _('Code postal'), _('Ville'), _('Pays'),
            _('Date d\'adhésion'), _('Date de naissance'),
            _('Statut'), _('Types de membre')
        ]
        ws.append(header)
        
        # Écrire les données
        for membre in membres:
            row = []
            for champ in champs:
                if champ == 'statut':
                    row.append(membre.statut.nom if membre.statut else '')
                elif champ == 'types_actifs':
                    types = ", ".join([t.libelle for t in membre.get_types_actifs()])
                    row.append(types)
                else:
                    row.append(getattr(membre, champ, ''))
            ws.append(row)
        
        # Style de l'en-tête
        for cell in ws[1]:
            cell.font = cell.font.copy(bold=True)
        
        # Ajuster la largeur des colonnes
        for column in ws.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                if cell.value:
                    max_length = max(max_length, len(str(cell.value)))
            ws.column_dimensions[column_letter].width = max_length + 2
        
        # Enregistrer le classeur dans la réponse
        wb.save(response)
        
        return response


class MembreHistoriqueView(DetailView):
    """
    Vue pour afficher l'historique complet des modifications d'un membre
    """
    model = Membre
    template_name = 'membres/historique.html'
    context_object_name = 'membre'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Historique des modifications
        context['historique'] = HistoriqueMembre.objects.filter(
            membre=self.object
        ).select_related('utilisateur').order_by('-created_at')
        
        # Historique des types de membre
        context['historique_types'] = MembreTypeMembre.objects.filter(
            membre=self.object
        ).select_related('type_membre', 'modifie_par').order_by('-date_debut')
        
        return context


class MembreStatistiquesView(StaffRequiredMixin, TemplateView):
    """
    Vue pour afficher des statistiques détaillées sur les membres
    """
    template_name = 'membres/statistiques.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now().date()
        
        # Statistiques générales
        total_membres = Membre.objects.count()
        membres_actifs = Membre.objects.actifs().count()
        
        # Répartition par type de membre
        types_stats = TypeMembre.objects.annotate(
            count=Count('membres_historique__membre', 
                          filter=Q(membres_historique__date_debut__lte=today, 
                                 membres_historique__date_fin__isnull=True),
                          distinct=True)
        ).order_by('-count')
        
        # Répartition par statut
        statuts_stats = Statut.objects.filter(
            membre__isnull=False
        ).annotate(
            count=Count('membre', distinct=True)
        ).order_by('-count')
        
        # Répartition par mois d'adhésion
        membres_par_mois = []
        for i in range(1, 13):
            month_name = datetime(2000, i, 1).strftime('%B')
            count = Membre.objects.filter(date_adhesion__month=i).count()
            membres_par_mois.append({'month': month_name, 'count': count})
        
        # Répartition par année d'adhésion
        annee_actuelle = today.year
        membres_par_annee = []
        for i in range(annee_actuelle - 9, annee_actuelle + 1):
            count = Membre.objects.filter(date_adhesion__year=i).count()
            membres_par_annee.append({'year': i, 'count': count})
        
        # Répartition par tranche d'âge
        membres_avec_age = Membre.objects.filter(date_naissance__isnull=False)
        tranches_age = [
            {'label': '< 18 ans', 'count': membres_avec_age.par_age(age_max=17).count()},
            {'label': '18-30 ans', 'count': membres_avec_age.par_age(age_min=18, age_max=30).count()},
            {'label': '31-45 ans', 'count': membres_avec_age.par_age(age_min=31, age_max=45).count()},
            {'label': '46-60 ans', 'count': membres_avec_age.par_age(age_min=46, age_max=60).count()},
            {'label': '61-75 ans', 'count': membres_avec_age.par_age(age_min=61, age_max=75).count()},
            {'label': '> 75 ans', 'count': membres_avec_age.par_age(age_min=76).count()},
        ]
        
        # Adhésions par année
        adhesions_par_annee = []
        for i in range(annee_actuelle - 9, annee_actuelle + 1):
            count = Membre.objects.filter(date_adhesion__year=i).count()
            adhesions_par_annee.append({'year': i, 'count': count})
        
        # Membres avec/sans compte utilisateur
        with_account = Membre.objects.filter(utilisateur__isnull=False).count()
        without_account = total_membres - with_account
        
        # Mettre à jour le contexte
        context.update({
            'total_membres': total_membres,
            'membres_actifs': membres_actifs,
            'pourcentage_actifs': round(membres_actifs / total_membres * 100 if total_membres else 0, 1),
            'types_stats': types_stats,
            'statuts_stats': statuts_stats,
            'membres_par_mois': membres_par_mois,
            'membres_par_annee': membres_par_annee,
            'tranches_age': tranches_age,
            'adhesions_par_annee': adhesions_par_annee,
            'with_account': with_account,
            'without_account': without_account,
            # Convertir en JSON pour les graphiques JavaScript
            'chart_types': json.dumps([{'name': t.libelle, 'value': t.count} for t in types_stats]),
            'chart_statuts': json.dumps([{'name': s.nom, 'value': s.count} for s in statuts_stats]),
            'chart_mois': json.dumps(membres_par_mois),
            'chart_annees': json.dumps(membres_par_annee),
            'chart_ages': json.dumps(tranches_age),
            'chart_adhesions': json.dumps(adhesions_par_annee),
            'chart_comptes': json.dumps([
                {'name': _('Avec compte'), 'value': with_account},
                {'name': _('Sans compte'), 'value': without_account}
            ]),
        })
        
        return context

class TypeMembreDetailView(StaffRequiredMixin, DetailView):
    """
    Vue pour afficher les détails d'un type de membre
    """
    model = TypeMembre
    template_name = 'membres/type_membre_detail.html'
    context_object_name = 'type_membre'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['membres_actifs'] = self.object.get_membres_actifs()
        return context
    
class MembreCorbeillePage(StaffRequiredMixin, ListView):
    """
    Vue pour afficher les membres supprimés logiquement
    """
    model = Membre
    template_name = 'membres/corbeille.html'
    context_object_name = 'membres'
    
    def get_queryset(self):
        # N'afficher que les membres supprimés
        return Membre.objects.only_deleted()
    
class MembreRestaurerView(StaffRequiredMixin, View):
    """
    Vue pour restaurer un membre supprimé
    """
    def post(self, request, pk):
        membre = get_object_or_404(Membre.objects.only_deleted(), pk=pk)
        membre.deleted_at = None
        membre.save(update_fields=['deleted_at'])
        
        # Ajouter à l'historique
        HistoriqueMembre.objects.create(
            membre=membre,
            utilisateur=request.user,
            action='restauration',
            description=_("Restauration du membre"),
            donnees_avant={'deleted_at': str(membre.deleted_at)},
            donnees_apres={'deleted_at': None}
        )
        
        messages.success(
            request, 
            _("Le membre %(name)s a été restauré avec succès.") % {'name': membre.nom_complet}
        )
        return redirect('membres:membre_detail', pk=membre.pk)
    
class MembreCorbeillePage(TrashViewMixin, ListView):
    """Vue pour la corbeille des membres."""
    model = Membre
    template_name = 'membres/corbeille.html'
    context_object_name = 'membres'
    paginate_by = 20
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _("Corbeille - Membres supprimés")
        return context

class MembreRestaurerView(RestoreViewMixin, View):
    """Vue pour restaurer un membre depuis la corbeille."""
    model = Membre
    success_url = reverse_lazy('membres:membre_liste')
    
    def get_object(self):
        """Récupérer le membre à restaurer."""
        return get_object_or_404(Membre.objects.only_deleted(), pk=self.kwargs['pk'])
    
    def get_success_response(self):
        """Response après restauration réussie."""
        messages.success(
            self.request, 
            _("Le membre a été restauré avec succès.")
        )
        return redirect(self.success_url)

class MembreSuppressionDefinitiveView(RestoreViewMixin, View):
    """Vue pour supprimer définitivement un membre."""
    model = Membre
    success_url = reverse_lazy('membres:membre_corbeille')
    
    def get_object(self):
        """Récupérer le membre à supprimer définitivement."""
        return get_object_or_404(Membre.objects.only_deleted(), pk=self.kwargs['pk'])
    
    def post(self, request, *args, **kwargs):
        """Supprimer définitivement le membre."""
        membre = self.get_object()
        
        # Journaliser l'action avant suppression définitive
        HistoriqueMembre.objects.create(
            membre=membre,
            utilisateur=request.user,
            action='suppression_definitive',
            description=_("Suppression définitive du membre"),
            donnees_avant={
                'nom': membre.nom,
                'prenom': membre.prenom,
                'email': membre.email,
                'deleted_at': str(membre.deleted_at)
            }
        )
        
        # Suppression physique
        membre.delete(hard=True)
        
        messages.success(
            request, 
            _("Le membre a été définitivement supprimé.")
        )
        return redirect(self.success_url)

# Dans apps/membres/views.py, ajoutez cette classe:

class MembreUpdateView(StaffRequiredMixin, UpdateView):
    """
    Vue pour modifier un membre existant
    """
    model = Membre
    form_class = MembreForm
    template_name = 'membres/form.html'
    success_url = reverse_lazy('membres:membre_liste')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        membre = form.save()
        messages.success(
            self.request, 
            _("Le membre %(name)s a été modifié avec succès.") % {'name': membre.nom_complet}
        )
        return super().form_valid(form)