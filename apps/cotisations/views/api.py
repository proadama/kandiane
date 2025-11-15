"""
API endpoints pour l'application cotisations.

Ce module contient tous les endpoints API JSON pour:
- Calcul de montants et barèmes
- Gestion des paiements et reçus
- Statistiques et rapports
- Rappels automatiques
"""

# Importations depuis utils.py
from .utils import (
    login_required, require_POST, get_object_or_404,
    JsonResponse, HttpResponse, HttpResponseForbidden,
    logger, timezone, Decimal, Sum, Count, F, Q, _,
    Cotisation, Paiement, BaremeCotisation, Rappel, TypeMembre,
    ExtendedJSONEncoder,
    RAPPEL_ETAT_PLANIFIE, RAPPEL_ETAT_ENVOYE, RAPPEL_ETAT_ECHOUE,
    Membre
)
import datetime
import traceback


# ============================================================================
# API pour les barèmes et calculs
# ============================================================================

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
        logger.error(f"Erreur lors du calcul du montant: {str(e)}")
        return JsonResponse({'success': False, 'message': str(e)})


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
            est_actif = (
                bareme.date_debut_validite <= today and
                (bareme.date_fin_validite is None or bareme.date_fin_validite >= today)
            )
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
        logger.error(f"Erreur lors de la récupération des barèmes: {str(e)}")
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
        logger.error(f"Erreur lors de la vérification du barème: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


# ============================================================================
# API pour les paiements et reçus
# ============================================================================

@login_required
def api_generer_recu(request, paiement_id):
    """
    API pour générer un reçu PDF pour un paiement.
    """
    # Vérifier les permissions
    if not request.user.is_staff:
        return HttpResponseForbidden(_("Vous n'avez pas les permissions pour générer ce reçu"))

    paiement = get_object_or_404(Paiement, pk=paiement_id)

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
        logger.error(f"Erreur lors de la génération du reçu: {str(e)}")
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


# ============================================================================
# API pour les statistiques et rapports
# ============================================================================

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
            logger.error(f"Erreur lors de la création du rappel: {str(e)}")
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


# ============================================================================
# API pour les rappels
# ============================================================================

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
    if rappel.etat != RAPPEL_ETAT_PLANIFIE:
        return JsonResponse({
            'success': False,
            'message': _("Ce rappel est déjà traité.")
        }, encoder=ExtendedJSONEncoder)

    try:
        # Marquer comme envoyé
        rappel.etat = RAPPEL_ETAT_ENVOYE
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
        logger.error(f"Erreur lors de l'envoi du rappel: {str(e)}")

        # En cas d'erreur, marquer comme échoué
        rappel.etat = RAPPEL_ETAT_ECHOUE
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
        logger.error(f"Erreur lors de la suppression du rappel: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': _("Erreur lors de la suppression du rappel: {0}").format(str(e))
        }, encoder=ExtendedJSONEncoder)


# ============================================================================
# API pour les types de membre
# ============================================================================

@login_required
def api_types_membre_par_membre(request):
    """
    API pour récupérer les types de membre associés à un membre spécifique.
    """
    membre_id = request.GET.get('membre_id')

    # Logs de débogage
    print(f"=== APPEL API TYPES MEMBRE ===")
    print(f"membre_id reçu: {membre_id}")

    if not membre_id:
        return JsonResponse({'success': False, 'message': _("Membre non spécifié")})

    try:
        # Récupérer le membre
        membre = Membre.objects.get(pk=membre_id)
        print(f"Membre trouvé: {membre.id} - {membre.prenom} {membre.nom}")

        # Date actuelle pour le débogage
        today = datetime.date.today()
        print(f"Date actuelle: {today}")

        # Utiliser la méthode intégrée get_types_actifs() du modèle Membre
        # Cette méthode est déjà définie pour récupérer les types actifs
        types_actifs = membre.get_types_actifs()

        print(f"Nombre de types actifs: {types_actifs.count()}")

        # Liste pour les logs de débogage
        for tm in types_actifs:
            print(f" - Type actif: {tm.id} - {tm.libelle}")

        # Préparer la réponse JSON
        types_membre = []
        for tm in types_actifs:
            types_membre.append({
                'id': tm.id,
                'libelle': tm.libelle,
            })

        # Message personnalisé si aucun type actif
        if not types_membre:
            print("ATTENTION: Aucun type de membre actif trouvé!")
            return JsonResponse({
                'success': True,
                'types_membre': [],
                'single_type': False,
                'membre_nom': f"{membre.prenom} {membre.nom}",
                'message': _("Ce membre n'a aucun type actif à la date d'aujourd'hui")
            })

        # Réponse normale
        return JsonResponse({
            'success': True,
            'types_membre': types_membre,
            'single_type': len(types_membre) == 1,
            'membre_nom': f"{membre.prenom} {membre.nom}"
        })

    except Membre.DoesNotExist:
        print(f"Erreur: Membre {membre_id} non trouvé")
        return JsonResponse({'success': False, 'message': _("Membre non trouvé")})
    except Exception as e:
        print(f"Exception dans api_types_membre_par_membre: {str(e)}")
        print(traceback.format_exc())
        return JsonResponse({'success': False, 'message': str(e)})


# ============================================================================
# Fonctions utilitaires
# ============================================================================

def get_duree_jours_par_periodicite(periodicite):
    """
    Fonction utilitaire pour obtenir la durée standard en jours pour une périodicité.
    """
    if periodicite == 'mensuelle':
        return 30
    elif periodicite == 'trimestrielle':
        return 91
    elif periodicite == 'semestrielle':
        return 182
    elif periodicite == 'annuelle':
        return 365
    else:
        return 365  # Par défaut
