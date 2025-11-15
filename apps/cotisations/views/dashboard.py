"""
Vues pour les tableaux de bord et statistiques des cotisations.

Ce module contient les vues pour:
- DashboardView: Tableau de bord principal avec graphiques
- StatistiquesView: Page de statistiques détaillées
"""

# Importations depuis utils.py
from apps.cotisations.views.utils import (
    StaffRequiredMixin, TemplateView,
    Q, Sum, Count, F, ExpressionWrapper, DecimalField,
    Decimal, timezone, logger, json, traceback, _,
    Cotisation, Paiement,
    ExtendedJSONEncoder
)
import datetime


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
