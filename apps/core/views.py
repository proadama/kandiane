# apps/core/views.py
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.utils import timezone
from django.db.models import Count, Sum, Q
from decimal import Decimal
import datetime
import json

class HomeView(TemplateView):
    """
    Vue de la page d'accueil.
    """
    template_name = 'core/home.html'

class DashboardView(LoginRequiredMixin, TemplateView):
    """
    Vue du tableau de bord, accessible uniquement aux utilisateurs connectés.
    """
    template_name = 'core/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Initialiser les données par défaut
        context.update({
            'membres_total': 0,
            'membres_nouveaux': 0,
            'membres_cotisations_jour': 0,
            'cotisations_total': 0,
            'cotisations_mois': 0,
            'cotisations_attente': 0,
            'evenements_total': 0,
            'evenements_venir': 0,
            'inscriptions_attente': 0,
            'activites_recentes': [],
            # Données pour les graphiques (vides par défaut)
            'adhesions_par_mois_json': json.dumps([]),
            'cotisations_par_statut_json': json.dumps([]),
        })
        
        # Date actuelle pour éviter de la récupérer plusieurs fois
        today = timezone.now().date()
        first_day_of_month = today.replace(day=1)
        
        # Récupérer les données de l'application Membres
        try:
            from apps.membres.models import Membre, TypeMembre
            
            # Statistiques des membres
            membres_total = Membre.objects.count()
            membres_nouveaux = Membre.objects.filter(date_adhesion__gte=first_day_of_month).count()
            
            # Mettre à jour le contexte avec les données des membres
            context.update({
                'membres_total': membres_total,
                'membres_nouveaux': membres_nouveaux,
            })
            
            # Préparer les données pour le graphique des adhésions par mois
            adhesions_par_mois = []
            month_names = [
                'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin', 
                'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre'
            ]
            
            for i in range(1, 13):
                # Compter les membres ayant adhéré ce mois (quel que soit l'année)
                count = Membre.objects.filter(date_adhesion__month=i).count()
                adhesions_par_mois.append({
                    'label': month_names[i-1],
                    'value': count
                })
            
            context['adhesions_par_mois_json'] = json.dumps(adhesions_par_mois)
            
            # Récupérer également quelques membres récents pour les activités
            membres_recents = Membre.objects.order_by('-date_adhesion')[:5]
            for membre in membres_recents:
                # S'assurer que la date est bien un objet date
                date_adhesion = membre.date_adhesion
                if isinstance(date_adhesion, datetime.datetime):
                    date_adhesion = date_adhesion.date()
                
                context['activites_recentes'].append({
                    'type': 'membre',
                    'date': date_adhesion,  # Utilisez un objet date
                    'date_timestamp': datetime.datetime.combine(date_adhesion, datetime.time.min).timestamp(),  # Pour le tri
                    'description': f"Nouveau membre : {membre.prenom} {membre.nom}",
                    'lien': f"/membres/{membre.id}/"
                })
                
        except (ImportError, ModuleNotFoundError):
            # L'application Membres n'est pas disponible ou configurée
            pass
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Erreur lors de la récupération des données de membres: {str(e)}")
        
        # Récupérer les données de l'application Cotisations
        try:
            from apps.cotisations.models import Cotisation, Paiement
            
            # Statistiques des cotisations
            cotisations_total = Cotisation.objects.count()
            
            # Montant total des cotisations
            montant_total = Cotisation.objects.aggregate(total=Sum('montant')).get('total') or Decimal('0.00')
            
            # Cotisations du mois courant
            cotisations_mois = Cotisation.objects.filter(
                date_emission__gte=first_day_of_month
            ).aggregate(total=Sum('montant')).get('total') or Decimal('0.00')
            
            # Cotisations en attente de paiement
            cotisations_attente = Cotisation.objects.filter(
                statut_paiement__in=['non_payee', 'partiellement_payee']
            ).count()
            
            # Membres avec cotisations à jour
            try:
                # Approche sécurisée pour compter les membres avec cotisations à jour
                membres_ids = set()
                cotisations_a_jour = Cotisation.objects.filter(
                    statut_paiement='payee'
                ).select_related('membre')
                
                for cotisation in cotisations_a_jour:
                    # Extraire la date d'échéance, convertir si c'est un datetime
                    echeance = cotisation.date_echeance
                    if isinstance(echeance, datetime.datetime):
                        echeance = echeance.date()
                    
                    # Comparer uniquement si c'est un objet date
                    if isinstance(echeance, datetime.date) and echeance >= today and cotisation.membre_id:
                        membres_ids.add(cotisation.membre_id)
                
                membres_cotisations_jour = len(membres_ids)
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Erreur lors du calcul des membres avec cotisations à jour: {str(e)}")
                membres_cotisations_jour = 0
            
            # Préparer les données pour le graphique des cotisations par statut
            cotisations_par_statut = []
            status_counts = Cotisation.objects.values('statut_paiement').annotate(
                count=Count('id')
            ).order_by('statut_paiement')
            
            # Dictionnaire de mapping pour les noms conviviaux des statuts
            status_labels = {
                'non_payee': 'Non payée',
                'partiellement_payee': 'Partiellement payée',
                'payee': 'Payée'
            }
            
            for status in status_counts:
                status_code = status['statut_paiement']
                status_name = status_labels.get(status_code, status_code)
                cotisations_par_statut.append({
                    'label': status_name,
                    'value': status['count']
                })
            
            # Mettre à jour le contexte avec les données des cotisations
            context.update({
                'cotisations_total': montant_total,
                'cotisations_mois': cotisations_mois,
                'cotisations_attente': cotisations_attente,
                'membres_cotisations_jour': membres_cotisations_jour,
                'cotisations_par_statut_json': json.dumps(cotisations_par_statut),
            })
            
            # Récupérer également quelques paiements récents pour les activités
            paiements_recents = Paiement.objects.select_related('cotisation__membre').order_by('-date_paiement')[:5]
            for paiement in paiements_recents:
                try:
                    # S'assurer que le paiement et la cotisation associée existent
                    if hasattr(paiement, 'cotisation') and paiement.cotisation:
                        membre = paiement.cotisation.membre
                        if membre:
                            # Convertir datetime en date pour la comparaison
                            date_paiement = paiement.date_paiement
                            # Créer un timestamp pour le tri
                            date_timestamp = date_paiement.timestamp() if isinstance(date_paiement, datetime.datetime) else 0
                            
                            context['activites_recentes'].append({
                                'type': 'paiement',
                                'date': date_paiement,
                                'date_timestamp': date_timestamp,  # Pour le tri
                                'description': f"Paiement de {paiement.montant}€ par {membre.prenom} {membre.nom}",
                                'lien': f"/cotisations/paiement/{paiement.id}/"
                            })
                except Exception as e:
                    # Ignorer les paiements avec des données incorrectes
                    continue
                
        except (ImportError, ModuleNotFoundError):
            # L'application Cotisations n'est pas disponible ou configurée
            pass
        except Exception as e:
            # Capturer toute autre erreur pour éviter de bloquer le tableau de bord
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Erreur lors de la récupération des données de cotisations: {str(e)}")
        
        # Essayer de récupérer les données de l'application Événements si elle existe
        try:
            from apps.evenements.models import Evenement, Inscription
            
            # Statistiques des événements
            evenements_total = Evenement.objects.count()
            evenements_venir = Evenement.objects.filter(date_debut__gte=today).count()
            inscriptions_attente = Inscription.objects.filter(statut='en_attente').count()
            
            # Mettre à jour le contexte avec les données des événements
            context.update({
                'evenements_total': evenements_total,
                'evenements_venir': evenements_venir,
                'inscriptions_attente': inscriptions_attente,
            })
            
            # Récupérer également quelques événements récents pour les activités
            evenements_recents = Evenement.objects.order_by('-date_creation')[:5]
            for evenement in evenements_recents:
                try:
                    # Convertir datetime en date pour la comparaison
                    date_creation = evenement.date_creation
                    # Créer un timestamp pour le tri
                    date_timestamp = date_creation.timestamp() if isinstance(date_creation, datetime.datetime) else 0
                    
                    context['activites_recentes'].append({
                        'type': 'evenement',
                        'date': date_creation,
                        'date_timestamp': date_timestamp,  # Pour le tri
                        'description': f"Nouvel événement : {evenement.titre}",
                        'lien': f"/evenements/{evenement.id}/"
                    })
                except Exception:
                    continue
                
        except (ImportError, ModuleNotFoundError):
            # L'application Événements n'est pas disponible ou configurée
            pass
        
        # Trier les activités récentes par timestamp (valeur numérique sûre pour le tri)
        try:
            context['activites_recentes'].sort(key=lambda x: x.get('date_timestamp', 0), reverse=True)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Erreur lors du tri des activités récentes: {str(e)}")
        
        # Limiter à 10 activités max
        context['activites_recentes'] = context['activites_recentes'][:10]
        
        return context

def maintenance_view(request):
    """
    Vue affichée lorsque le site est en maintenance.
    """
    context = {
        'title': 'Site en maintenance',
        'message': 'Notre site est actuellement en maintenance. Merci de revenir plus tard.'
    }
    return render(request, 'core/maintenance.html', context, status=503)

def error_404(request, exception):
    """
    Vue pour les erreurs 404.
    """
    return render(request, 'core/errors/404.html', status=404)

def error_500(request):
    """
    Vue pour les erreurs 500.
    """
    return render(request, 'core/errors/500.html', status=500)


def test_filters(request):
    """
    Vue pour tester les filtres personnalisés.
    """
    context = {
        'current_date': timezone.now().date(),
    }
    return render(request, 'core/test_filters.html', context)