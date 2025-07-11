# apps/core/views.py
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.utils import timezone
from django.db.models import Count, Sum, Q, F, ExpressionWrapper, fields
from decimal import Decimal
import datetime
import json
import logging
from django.urls import reverse
from apps.evenements.models import Evenement, InscriptionEvenement, TypeEvenement
from datetime import timedelta

logger = logging.getLogger(__name__)

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
            
            # Cotisations en attente de paiement (non payées ou partiellement payées)
            cotisations_attente = Cotisation.objects.filter(
                Q(statut_paiement='non_payee') | 
                Q(statut_paiement='partiellement_payee') |
                Q(statut_paiement='non_payée') |  # Avec accent
                Q(statut_paiement='partiellement_payée')  # Avec accent
            ).count()
            
            # Membres avec cotisations à jour - CORRECTION
            try:
                # Méthode 1: Utiliser une requête plus simple et directe
                # Une cotisation est "à jour" si elle est payée et a une date d'échéance future
                membres_cotisations_jour = Membre.objects.filter(
                    cotisations__statut_paiement__in=['payee', 'payée'],  # Essayer les 2 possibilités (avec/sans accent)
                    cotisations__date_echeance__gte=today
                ).distinct().count()
                
                # Si le calcul renvoie 0 mais que nous savons qu'il devrait y avoir des membres à jour,
                # essayons une méthode alternative
                if membres_cotisations_jour == 0:
                    logger.info("Première méthode a retourné 0, essai d'une méthode alternative")
                    
                    # Méthode 2: Compter manuellement
                    membres_ids = set()
                    
                    # Récupérer les cotisations payées
                    cotisations_payees = Cotisation.objects.filter(
                        Q(statut_paiement='payee') | Q(statut_paiement='payée')
                    )
                    
                    # Parcourir chaque cotisation et vérifier la date d'échéance
                    for cotisation in cotisations_payees:
                        try:
                            # Récupérer et normaliser la date d'échéance
                            echeance = cotisation.date_echeance
                            
                            # Convertir en date si c'est un datetime
                            if isinstance(echeance, datetime.datetime):
                                echeance = echeance.date()
                                
                            # Ajouter le membre si la cotisation est à jour
                            if echeance >= today and cotisation.membre_id:
                                membres_ids.add(cotisation.membre_id)
                                
                        except Exception as e:
                            logger.warning(f"Erreur lors du traitement de la cotisation {cotisation.id}: {str(e)}")
                    
                    membres_cotisations_jour = len(membres_ids)
                    
                    # Si toujours 0, essayons une troisième méthode
                    if membres_cotisations_jour == 0:
                        logger.info("Deuxième méthode a retourné 0, essai d'une troisième méthode")
                        
                        # Méthode 3: Ignorer complètement la date et juste compter les membres qui ont au moins une cotisation payée
                        membres_cotisations_jour = Membre.objects.filter(
                            Q(cotisations__statut_paiement='payee') | 
                            Q(cotisations__statut_paiement='payée')
                        ).distinct().count()
                
            except Exception as e:
                logger.error(f"Erreur lors du calcul des membres avec cotisations à jour: {str(e)}")
                # Logger les détails pour le débogage
                logger.error(f"Détails de l'erreur: {traceback.format_exc()}")
                membres_cotisations_jour = 0
            
            # Mettre à jour le contexte avec les données des cotisations
            context.update({
                'cotisations_total': montant_total,
                'cotisations_mois': cotisations_mois,
                'cotisations_attente': cotisations_attente,
                'membres_cotisations_jour': membres_cotisations_jour,
            })
            
            # Préparer les données pour le graphique des cotisations par statut
            cotisations_par_statut = []
            status_counts = Cotisation.objects.values('statut_paiement').annotate(
                count=Count('id')
            ).order_by('statut_paiement')
            
            # Dictionnaire de mapping pour les noms conviviaux des statuts
            status_labels = {
                'non_payee': 'Non payée',
                'non_payée': 'Non payée',
                'partiellement_payee': 'Partiellement payée',
                'partiellement_payée': 'Partiellement payée',
                'payee': 'Payée',
                'payée': 'Payée'
            }
            
            for status in status_counts:
                status_code = status['statut_paiement']
                status_name = status_labels.get(status_code, status_code)
                cotisations_par_statut.append({
                    'label': status_name,
                    'value': status['count']
                })
            
            context['cotisations_par_statut_json'] = json.dumps(cotisations_par_statut)
            
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
                            
                            # Utiliser reverse() pour générer l'URL correcte
                            paiement_url = reverse('cotisations:paiement_detail', kwargs={'pk': paiement.id})
                            
                            context['activites_recentes'].append({
                                'type': 'paiement',
                                'date': date_paiement,
                                'date_timestamp': date_timestamp,  # Pour le tri
                                'description': f"Paiement de {paiement.montant}€ par {membre.prenom} {membre.nom}",
                                'lien': paiement_url
                            })
                except Exception as e:
                    # Ignorer les paiements avec des données incorrectes
                    logger.warning(f"Erreur avec le paiement {paiement.id}: {str(e)}")
                    continue
                
        except (ImportError, ModuleNotFoundError):
            # L'application Cotisations n'est pas disponible ou configurée
            pass
        except Exception as e:
            # Capturer toute autre erreur pour éviter de bloquer le tableau de bord
            logger.error(f"Erreur lors de la récupération des données de cotisations: {str(e)}")
            import traceback
            logger.error(f"Détails de l'erreur: {traceback.format_exc()}")
        

        # Récupérer les données de l'application Événements - AMÉLIORATION
        try:
            from apps.evenements.models import Evenement, InscriptionEvenement, ValidationEvenement
            
            # Statistiques générales des événements
            evenements_total = Evenement.objects.count()
            evenements_venir = Evenement.objects.filter(date_debut__gte=today).count()
            evenements_publies = Evenement.objects.filter(statut='publie').count()
            
            # Mettre à jour le contexte avec les données des événements
            context.update({
                'evenements_total': evenements_total,
                'evenements_venir': evenements_venir,
                'evenements_publies': evenements_publies,
            })
            
            # === NOUVEAUX WIDGETS ÉVÉNEMENTS ===
            
            # 1. PROCHAINS ÉVÉNEMENTS PUBLICS (pour tous)
            prochains_evenements = Evenement.objects.filter(
                statut='publie',
                date_debut__gte=timezone.now(),
                inscriptions_ouvertes=True
            ).order_by('date_debut')[:5]
            
            context['prochains_evenements'] = prochains_evenements
            
            # 2. MES INSCRIPTIONS (si membre)
            mes_inscriptions = []
            try:
                membre = Membre.objects.get(utilisateur=user)
                mes_inscriptions = InscriptionEvenement.objects.filter(
                    membre=membre,
                    statut__in=['confirmee', 'en_attente'],
                    evenement__date_debut__gte=timezone.now()
                ).select_related('evenement').order_by('evenement__date_debut')[:5]
                
                context['mes_inscriptions'] = mes_inscriptions
                
                # Statistiques personnelles
                context['mes_stats_evenements'] = {
                    'total_inscriptions': InscriptionEvenement.objects.filter(membre=membre).count(),
                    'inscriptions_confirmees': InscriptionEvenement.objects.filter(
                        membre=membre, statut='confirmee'
                    ).count(),
                    'prochaines_inscriptions': mes_inscriptions.count()
                }
                
            except Membre.DoesNotExist:
                context['mes_inscriptions'] = []
                context['mes_stats_evenements'] = {}
            
            # 3. DONNÉES ORGANISATEUR (si staff ou organisateur)
            if user.is_staff:
                # Mes événements organisés
                mes_evenements = Evenement.objects.filter(organisateur=user)
                context['mes_evenements'] = mes_evenements[:5]
                
                # Statistiques organisateur
                from django.db.models import Count, Sum
                stats_organisateur = mes_evenements.aggregate(
                    total_organise=Count('id'),
                    evenements_venir=Count('id', filter=Q(date_debut__gte=timezone.now())),
                    total_inscriptions=Count('inscriptions'),
                    total_participants=Sum('inscriptions__nombre_accompagnants')
                )
                context['stats_organisateur'] = stats_organisateur
                
                # 4. ALERTES VALIDATION (si staff)
                validations_attente = ValidationEvenement.objects.filter(
                    statut_validation='en_attente'
                ).select_related('evenement').order_by('evenement__date_debut')[:5]
                
                context['validations_attente'] = validations_attente
                context['nb_validations_attente'] = validations_attente.count()
                
                # Alertes urgentes (événements dans moins de 7 jours)
                from datetime import timedelta
                date_limite_urgente = timezone.now() + timedelta(days=7)
                validations_urgentes = validations_attente.filter(
                    evenement__date_debut__lte=date_limite_urgente
                )
                context['validations_urgentes'] = validations_urgentes.count()
            
            # 5. MÉTRIQUES DU MOIS
            # Événements du mois
            evenements_mois = Evenement.objects.filter(
                date_debut__gte=first_day_of_month,
                date_debut__lt=timezone.now().replace(day=1) + timedelta(days=32)
            ).count()
            
            # Inscriptions du mois
            inscriptions_mois = InscriptionEvenement.objects.filter(
                date_inscription__gte=first_day_of_month
            ).count()
            
            # Revenus événements du mois (si système cotisations intégré)
            revenus_evenements_mois = 0
            try:
                from apps.cotisations.models import Cotisation
                revenus_evenements = Cotisation.objects.filter(
                    type_cotisation='evenement',
                    date_creation__gte=first_day_of_month,
                    statut_paiement='payee'
                ).aggregate(total=Sum('montant'))
                revenus_evenements_mois = revenus_evenements['total'] or 0
            except (ImportError, AttributeError):
                pass
            
            context.update({
                'evenements_mois': evenements_mois,
                'inscriptions_mois': inscriptions_mois,
                'revenus_evenements_mois': revenus_evenements_mois,
            })
            
            # 6. DONNÉES POUR GRAPHIQUES
            # Évolution des inscriptions par mois (6 derniers mois)
            inscriptions_par_mois = []
            for i in range(6):
                date_mois = (timezone.now().replace(day=1) - timedelta(days=32*i)).replace(day=1)
                date_mois_suivant = (date_mois + timedelta(days=32)).replace(day=1)
                
                count = InscriptionEvenement.objects.filter(
                    date_inscription__gte=date_mois,
                    date_inscription__lt=date_mois_suivant
                ).count()
                
                inscriptions_par_mois.append({
                    'label': date_mois.strftime('%B %Y'),
                    'value': count
                })
            
            inscriptions_par_mois.reverse()  # Ordre chronologique
            context['inscriptions_par_mois_json'] = json.dumps(inscriptions_par_mois)
            
            # Récupérer également quelques événements récents pour les activités
            evenements_recents = Evenement.objects.order_by('-created_at')[:3]
            for evenement in evenements_recents:
                try:
                    date_creation = evenement.created_at
                    date_timestamp = date_creation.timestamp() if isinstance(date_creation, datetime.datetime) else 0
                    
                    # Utiliser reverse() pour l'URL si disponible
                    try:
                        from django.urls import reverse
                        evenement_url = reverse('evenements:detail', kwargs={'pk': evenement.id})
                    except:
                        evenement_url = f"/evenements/{evenement.id}/"
                    
                    context['activites_recentes'].append({
                        'type': 'evenement',
                        'date': date_creation,
                        'date_timestamp': date_timestamp,
                        'description': f"Nouvel événement : {evenement.titre}",
                        'lien': evenement_url
                    })
                except Exception:
                    continue
                    
        except (ImportError, ModuleNotFoundError):
            # L'application Événements n'est pas disponible
            context.update({
                'evenements_total': 0,
                'evenements_venir': 0,
                'prochains_evenements': [],
                'mes_inscriptions': [],
                'mes_evenements': [],
                'validations_attente': [],
                'nb_validations_attente': 0,
                'validations_urgentes': 0,
                'inscriptions_par_mois_json': json.dumps([]),
            })
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des données d'événements: {str(e)}")
            # Valeurs par défaut en cas d'erreur
            context.update({
                'evenements_total': 0,
                'evenements_venir': 0,
                'prochains_evenements': [],
                'mes_inscriptions': [],
                'mes_evenements': [],
                'validations_attente': [],
                'nb_validations_attente': 0,
                'validations_urgentes': 0,
            })
        
        # Trier les activités récentes par timestamp (valeur numérique sûre pour le tri)
        try:
            context['activites_recentes'].sort(key=lambda x: x.get('date_timestamp', 0), reverse=True)
        except Exception as e:
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