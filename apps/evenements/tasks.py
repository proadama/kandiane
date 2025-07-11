# apps/evenements/tasks.py
from celery import shared_task
from celery.schedules import crontab
from django.utils import timezone
from django.db.models import Q
from datetime import datetime, timedelta
from django.core.mail import send_mail
from django.conf import settings
import logging
from .services import NotificationService
from apps.core.models import Log
from .monitoring import NotificationMonitoring

from .models import (
    Evenement, InscriptionEvenement, EvenementRecurrence, 
    ValidationEvenement, AccompagnantInvite
)
from apps.core.notifications import NotificationService
from apps.membres.models import Membre

logger = logging.getLogger(__name__)

# Configuration des tâches périodiques
CELERY_BEAT_SCHEDULE = {
    'envoyer-rappels-confirmation': {
        'task': 'apps.evenements.tasks.envoyer_rappels_confirmation',
        'schedule': crontab(minute=0, hour='*/2'),  # Toutes les 2 heures
    },
    'nettoyer-inscriptions-expirees': {
        'task': 'apps.evenements.tasks.nettoyer_inscriptions_expirees',
        'schedule': crontab(minute=0, hour=9),  # Tous les jours à 9h
    },
    'generer-occurrences-recurrentes': {
        'task': 'apps.evenements.tasks.generer_occurrences_recurrentes',
        'schedule': crontab(minute=0, hour=0, day_of_week=1),  # Tous les lundis à minuit
    },
    'envoyer-rappels-evenements': {
        'task': 'apps.evenements.tasks.envoyer_rappels_evenements',
        'schedule': crontab(minute=0, hour=10),  # Tous les jours à 10h
    },
    'notifier-validations-urgentes': {
        'task': 'apps.evenements.tasks.notifier_validations_urgentes',
        'schedule': crontab(minute=0, hour=8),  # Tous les jours à 8h
    },
    'nettoyer-anciennes-donnees': {
        'task': 'apps.evenements.tasks.nettoyer_anciennes_donnees',
        'schedule': crontab(minute=0, hour=2, day_of_week=0),  # Tous les dimanches à 2h
    },
}

@shared_task(bind=True, max_retries=3)
def envoyer_rappels_confirmation(self):
    """
    Envoie des rappels de confirmation pour les inscriptions en attente
    """
    try:
        now = timezone.now()
        rappels_envoyes = 0
        erreurs = 0
        
        # Inscriptions à confirmer dans les 24 heures
        inscriptions_24h = InscriptionEvenement.objects.filter(
            statut='en_attente',
            date_limite_confirmation__lte=now + timedelta(hours=24),
            date_limite_confirmation__gt=now
        ).select_related('membre', 'evenement')
        
        # Inscriptions à confirmer dans les 2 heures
        inscriptions_2h = InscriptionEvenement.objects.filter(
            statut='en_attente',
            date_limite_confirmation__lte=now + timedelta(hours=2),
            date_limite_confirmation__gt=now
        ).select_related('membre', 'evenement')
        
        # Envoyer rappels 24h
        for inscription in inscriptions_24h:
            try:
                # Vérifier si un rappel 24h n'a pas déjà été envoyé
                if not hasattr(inscription, '_rappel_24h_envoye'):
                    if NotificationService.envoyer_rappel_confirmation(inscription):
                        rappels_envoyes += 1
                        # Marquer comme envoyé (vous pouvez utiliser un champ dans le modèle)
                        logger.info(f"Rappel 24h envoyé pour inscription {inscription.id}")
                    else:
                        erreurs += 1
            except Exception as e:
                erreurs += 1
                logger.error(f"Erreur rappel 24h pour inscription {inscription.id}: {str(e)}")
        
        # Envoyer rappels 2h (plus urgents)
        for inscription in inscriptions_2h:
            try:
                if NotificationService.envoyer_rappel_confirmation(inscription):
                    rappels_envoyes += 1
                    logger.info(f"Rappel 2h envoyé pour inscription {inscription.id}")
                else:
                    erreurs += 1
            except Exception as e:
                erreurs += 1
                logger.error(f"Erreur rappel 2h pour inscription {inscription.id}: {str(e)}")
        
        logger.info(f"Rappels de confirmation: {rappels_envoyes} envoyés, {erreurs} erreurs")
        
        return {
            'rappels_envoyes': rappels_envoyes,
            'erreurs': erreurs,
            'total_24h': inscriptions_24h.count(),
            'total_2h': inscriptions_2h.count()
        }
        
    except Exception as e:
        logger.error(f"Erreur dans envoyer_rappels_confirmation: {str(e)}")
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60, exc=e)
        raise

@shared_task(bind=True, max_retries=3)
def nettoyer_inscriptions_expirees(self):
    """
    Nettoie les inscriptions expirées et promeut les membres en liste d'attente
    """
    try:
        now = timezone.now()
        inscriptions_expirees = 0
        promotions = 0
        
        # Trouver les inscriptions expirées
        inscriptions_a_expirer = InscriptionEvenement.objects.filter(
            statut='en_attente',
            date_limite_confirmation__lt=now
        ).select_related('evenement', 'membre')
        
        for inscription in inscriptions_a_expirer:
            try:
                # Marquer comme expirée
                inscription.statut = 'expiree'
                inscription.save()
                inscriptions_expirees += 1
                
                # Notifier le membre
                try:
                    NotificationService.envoyer_notification_expiration(inscription)
                except Exception as e:
                    logger.error(f"Erreur notification expiration: {str(e)}")
                
                # Promouvoir depuis la liste d'attente
                evenement = inscription.evenement
                inscription_attente = InscriptionEvenement.objects.filter(
                    evenement=evenement,
                    statut='liste_attente'
                ).order_by('date_inscription').first()
                
                if inscription_attente:
                    inscription_attente.statut = 'en_attente'
                    inscription_attente.date_limite_confirmation = now + timedelta(
                        hours=evenement.delai_confirmation
                    )
                    inscription_attente.save()
                    promotions += 1
                    
                    # Notifier la promotion
                    try:
                        NotificationService.envoyer_promotion_liste_attente(inscription_attente)
                    except Exception as e:
                        logger.error(f"Erreur notification promotion: {str(e)}")
                
                logger.info(f"Inscription {inscription.id} expirée et traitée")
                
            except Exception as e:
                logger.error(f"Erreur traitement inscription {inscription.id}: {str(e)}")
        
        logger.info(f"Nettoyage terminé: {inscriptions_expirees} expirées, {promotions} promotions")
        
        return {
            'inscriptions_expirees': inscriptions_expirees,
            'promotions': promotions
        }
        
    except Exception as e:
        logger.error(f"Erreur dans nettoyer_inscriptions_expirees: {str(e)}")
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60, exc=e)
        raise

@shared_task(bind=True, max_retries=3)
def generer_occurrences_recurrentes(self):
    """
    Génère les occurrences futures pour les événements récurrents
    """
    try:
        occurrences_creees = 0
        erreurs = 0
        
        # Trouver les événements récurrents actifs
        recurrences = EvenementRecurrence.objects.filter(
            Q(date_fin_recurrence__isnull=True) | Q(date_fin_recurrence__gte=timezone.now().date())
        ).select_related('evenement_parent')
        
        for recurrence in recurrences:
            try:
                # Créer les occurrences pour les 3 prochains mois
                date_limite = timezone.now() + timedelta(days=90)
                
                # Logique de génération selon la fréquence
                if recurrence.frequence == 'hebdomadaire':
                    nouvelles_occurrences = _generer_occurrences_hebdomadaires(
                        recurrence, date_limite
                    )
                elif recurrence.frequence == 'mensuelle':
                    nouvelles_occurrences = _generer_occurrences_mensuelles(
                        recurrence, date_limite
                    )
                elif recurrence.frequence == 'annuelle':
                    nouvelles_occurrences = _generer_occurrences_annuelles(
                        recurrence, date_limite
                    )
                else:
                    continue
                
                occurrences_creees += nouvelles_occurrences
                logger.info(f"Récurrence {recurrence.id}: {nouvelles_occurrences} occurrences créées")
                
            except Exception as e:
                erreurs += 1
                logger.error(f"Erreur génération récurrence {recurrence.id}: {str(e)}")
        
        logger.info(f"Génération récurrences terminée: {occurrences_creees} créées, {erreurs} erreurs")
        
        return {
            'occurrences_creees': occurrences_creees,
            'erreurs': erreurs
        }
        
    except Exception as e:
        logger.error(f"Erreur dans generer_occurrences_recurrentes: {str(e)}")
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60, exc=e)
        raise

def _generer_occurrences_hebdomadaires(recurrence, date_limite):
    """
    Génère les occurrences hebdomadaires
    """
    occurrences_creees = 0
    evenement_parent = recurrence.evenement_parent
    
    # Trouver la dernière occurrence créée
    derniere_occurrence = Evenement.objects.filter(
        evenement_parent=evenement_parent
    ).order_by('-date_debut').first()
    
    if derniere_occurrence:
        prochaine_date = derniere_occurrence.date_debut + timedelta(
            weeks=recurrence.intervalle_recurrence
        )
    else:
        prochaine_date = evenement_parent.date_debut + timedelta(
            weeks=recurrence.intervalle_recurrence
        )
    
    while prochaine_date <= date_limite:
        # Vérifier si cette occurrence existe déjà
        if not Evenement.objects.filter(
            evenement_parent=evenement_parent,
            date_debut=prochaine_date
        ).exists():
            
            # Créer la nouvelle occurrence
            nouvelle_occurrence = Evenement.objects.create(
                titre=evenement_parent.titre,
                description=evenement_parent.description,
                date_debut=prochaine_date,
                date_fin=prochaine_date + (evenement_parent.date_fin - evenement_parent.date_debut) if evenement_parent.date_fin else None,
                lieu=evenement_parent.lieu,
                adresse_complete=evenement_parent.adresse_complete,
                capacite_max=evenement_parent.capacite_max,
                type_evenement=evenement_parent.type_evenement,
                organisateur=evenement_parent.organisateur,
                statut='publie',
                est_payant=evenement_parent.est_payant,
                tarif_membre=evenement_parent.tarif_membre,
                tarif_salarie=evenement_parent.tarif_salarie,
                tarif_invite=evenement_parent.tarif_invite,
                permet_accompagnants=evenement_parent.permet_accompagnants,
                nombre_max_accompagnants=evenement_parent.nombre_max_accompagnants,
                delai_confirmation=evenement_parent.delai_confirmation,
                evenement_parent=evenement_parent
            )
            
            occurrences_creees += 1
            logger.info(f"Occurrence hebdomadaire créée: {nouvelle_occurrence.id}")
        
        prochaine_date += timedelta(weeks=recurrence.intervalle_recurrence)
    
    return occurrences_creees

def _generer_occurrences_mensuelles(recurrence, date_limite):
    """
    Génère les occurrences mensuelles
    """
    occurrences_creees = 0
    evenement_parent = recurrence.evenement_parent
    
    # Logique similaire pour les occurrences mensuelles
    derniere_occurrence = Evenement.objects.filter(
        evenement_parent=evenement_parent
    ).order_by('-date_debut').first()
    
    if derniere_occurrence:
        prochaine_date = derniere_occurrence.date_debut
    else:
        prochaine_date = evenement_parent.date_debut
    
    # Calculer la prochaine date mensuelle
    while prochaine_date <= date_limite:
        # Ajouter les mois
        if prochaine_date.month + recurrence.intervalle_recurrence <= 12:
            prochaine_date = prochaine_date.replace(
                month=prochaine_date.month + recurrence.intervalle_recurrence
            )
        else:
            mois_suivant = (prochaine_date.month + recurrence.intervalle_recurrence - 1) % 12 + 1
            annee_suivante = prochaine_date.year + (prochaine_date.month + recurrence.intervalle_recurrence - 1) // 12
            prochaine_date = prochaine_date.replace(year=annee_suivante, month=mois_suivant)
        
        # Vérifier si cette occurrence existe déjà
        if not Evenement.objects.filter(
            evenement_parent=evenement_parent,
            date_debut=prochaine_date
        ).exists():
            
            # Créer la nouvelle occurrence
            nouvelle_occurrence = Evenement.objects.create(
                titre=evenement_parent.titre,
                description=evenement_parent.description,
                date_debut=prochaine_date,
                date_fin=prochaine_date + (evenement_parent.date_fin - evenement_parent.date_debut) if evenement_parent.date_fin else None,
                lieu=evenement_parent.lieu,
                adresse_complete=evenement_parent.adresse_complete,
                capacite_max=evenement_parent.capacite_max,
                type_evenement=evenement_parent.type_evenement,
                organisateur=evenement_parent.organisateur,
                statut='publie',
                est_payant=evenement_parent.est_payant,
                tarif_membre=evenement_parent.tarif_membre,
                tarif_salarie=evenement_parent.tarif_salarie,
                tarif_invite=evenement_parent.tarif_invite,
                permet_accompagnants=evenement_parent.permet_accompagnants,
                nombre_max_accompagnants=evenement_parent.nombre_max_accompagnants,
                delai_confirmation=evenement_parent.delai_confirmation,
                evenement_parent=evenement_parent
            )
            
            occurrences_creees += 1
            logger.info(f"Occurrence mensuelle créée: {nouvelle_occurrence.id}")
    
    return occurrences_creees

def _generer_occurrences_annuelles(recurrence, date_limite):
    """
    Génère les occurrences annuelles
    """
    occurrences_creees = 0
    evenement_parent = recurrence.evenement_parent
    
    # Logique similaire pour les occurrences annuelles
    derniere_occurrence = Evenement.objects.filter(
        evenement_parent=evenement_parent
    ).order_by('-date_debut').first()
    
    if derniere_occurrence:
        prochaine_date = derniere_occurrence.date_debut.replace(
            year=derniere_occurrence.date_debut.year + recurrence.intervalle_recurrence
        )
    else:
        prochaine_date = evenement_parent.date_debut.replace(
            year=evenement_parent.date_debut.year + recurrence.intervalle_recurrence
        )
    
    while prochaine_date <= date_limite:
        # Vérifier si cette occurrence existe déjà
        if not Evenement.objects.filter(
            evenement_parent=evenement_parent,
            date_debut=prochaine_date
        ).exists():
            
            # Créer la nouvelle occurrence
            nouvelle_occurrence = Evenement.objects.create(
                titre=evenement_parent.titre,
                description=evenement_parent.description,
                date_debut=prochaine_date,
                date_fin=prochaine_date + (evenement_parent.date_fin - evenement_parent.date_debut) if evenement_parent.date_fin else None,
                lieu=evenement_parent.lieu,
                adresse_complete=evenement_parent.adresse_complete,
                capacite_max=evenement_parent.capacite_max,
                type_evenement=evenement_parent.type_evenement,
                organisateur=evenement_parent.organisateur,
                statut='publie',
                est_payant=evenement_parent.est_payant,
                tarif_membre=evenement_parent.tarif_membre,
                tarif_salarie=evenement_parent.tarif_salarie,
                tarif_invite=evenement_parent.tarif_invite,
                permet_accompagnants=evenement_parent.permet_accompagnants,
                nombre_max_accompagnants=evenement_parent.nombre_max_accompagnants,
                delai_confirmation=evenement_parent.delai_confirmation,
                evenement_parent=evenement_parent
            )
            
            occurrences_creees += 1
            logger.info(f"Occurrence annuelle créée: {nouvelle_occurrence.id}")
        
        prochaine_date = prochaine_date.replace(year=prochaine_date.year + recurrence.intervalle_recurrence)
    
    return occurrences_creees

@shared_task(bind=True, max_retries=3)
def envoyer_rappels_evenements(self):
    """
    Envoie des rappels avant les événements
    """
    try:
        now = timezone.now()
        rappels_envoyes = 0
        erreurs = 0
        
        # Événements dans 24h
        evenements_24h = Evenement.objects.filter(
            date_debut__gte=now + timedelta(hours=23),
            date_debut__lte=now + timedelta(hours=25),
            statut='publie'
        ).select_related('type_evenement', 'organisateur')
        
        # Événements dans 2h
        evenements_2h = Evenement.objects.filter(
            date_debut__gte=now + timedelta(hours=1),
            date_debut__lte=now + timedelta(hours=3),
            statut='publie'
        ).select_related('type_evenement', 'organisateur')
        
        # Traiter les rappels 24h
        for evenement in evenements_24h:
            try:
                # Récupérer les membres inscrits confirmés
                membres_inscrits = Membre.objects.filter(
                    inscriptions_evenements__evenement=evenement,
                    inscriptions_evenements__statut__in=['confirmee', 'presente']
                ).distinct()
                
                if NotificationService.envoyer_rappel_evenement(evenement, membres_inscrits):
                    rappels_envoyes += 1
                    logger.info(f"Rappel 24h envoyé pour événement {evenement.id}")
                else:
                    erreurs += 1
                    
            except Exception as e:
                erreurs += 1
                logger.error(f"Erreur rappel 24h événement {evenement.id}: {str(e)}")
        
        # Traiter les rappels 2h
        for evenement in evenements_2h:
            try:
                # Récupérer les membres inscrits confirmés
                membres_inscrits = Membre.objects.filter(
                    inscriptions_evenements__evenement=evenement,
                    inscriptions_evenements__statut__in=['confirmee', 'presente']
                ).distinct()
                
                if NotificationService.envoyer_rappel_evenement(evenement, membres_inscrits):
                    rappels_envoyes += 1
                    logger.info(f"Rappel 2h envoyé pour événement {evenement.id}")
                else:
                    erreurs += 1
                    
            except Exception as e:
                erreurs += 1
                logger.error(f"Erreur rappel 2h événement {evenement.id}: {str(e)}")
        
        logger.info(f"Rappels d'événements: {rappels_envoyes} envoyés, {erreurs} erreurs")
        
        return {
            'rappels_envoyes': rappels_envoyes,
            'erreurs': erreurs,
            'evenements_24h': evenements_24h.count(),
            'evenements_2h': evenements_2h.count()
        }
        
    except Exception as e:
        logger.error(f"Erreur dans envoyer_rappels_evenements: {str(e)}")
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60, exc=e)
        raise

@shared_task(bind=True, max_retries=3)
def notifier_validations_urgentes(self):
    """
    Notifie les validations urgentes (événements dans moins de 7 jours)
    """
    try:
        now = timezone.now()
        notifications_envoyees = 0
        erreurs = 0
        
        # Validations urgentes
        validations_urgentes = ValidationEvenement.objects.filter(
            statut_validation='en_attente',
            evenement__date_debut__lte=now + timedelta(days=7)
        ).select_related('evenement', 'evenement__organisateur')
        
        # Récupérer les validateurs (admins)
        from django.contrib.auth import get_user_model
        User = get_user_model()
        validateurs = User.objects.filter(is_staff=True, is_active=True)
        
        for validation in validations_urgentes:
            try:
                jours_restants = (validation.evenement.date_debut.date() - now.date()).days
                
                for validateur in validateurs:
                    try:
                        # Créer le contexte de notification
                        context = {
                            'validation': validation,
                            'evenement': validation.evenement,
                            'jours_restants': jours_restants,
                            'url_validation': f"{settings.SITE_URL}/evenements/validation/{validation.id}/",
                            'site_name': getattr(settings, 'SITE_NAME', 'Gestion Association'),
                        }
                        
                        # Envoyer la notification
                        send_mail(
                            subject=f"URGENT: Validation requise - {validation.evenement.titre}",
                            message=f"L'événement '{validation.evenement.titre}' nécessite une validation urgente. Il reste {jours_restants} jour(s) avant l'événement.",
                            from_email=settings.DEFAULT_FROM_EMAIL,
                            recipient_list=[validateur.email],
                            fail_silently=False,
                        )
                        
                        notifications_envoyees += 1
                        
                    except Exception as e:
                        erreurs += 1
                        logger.error(f"Erreur notification validateur {validateur.email}: {str(e)}")
                        
            except Exception as e:
                erreurs += 1
                logger.error(f"Erreur traitement validation {validation.id}: {str(e)}")
        
        logger.info(f"Notifications urgentes: {notifications_envoyees} envoyées, {erreurs} erreurs")
        
        return {
            'notifications_envoyees': notifications_envoyees,
            'erreurs': erreurs,
            'validations_urgentes': validations_urgentes.count()
        }
        
    except Exception as e:
        logger.error(f"Erreur dans notifier_validations_urgentes: {str(e)}")
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60, exc=e)
        raise

@shared_task(bind=True, max_retries=3)
def nettoyer_anciennes_donnees(self):
    """
    Nettoie les anciennes données (événements terminés depuis longtemps, etc.)
    """
    try:
        now = timezone.now()
        donnees_nettoyees = 0
        
        # Supprimer les événements terminés depuis plus de 2 ans
        evenements_anciens = Evenement.objects.filter(
            date_debut__lt=now - timedelta(days=730),
            statut='termine'
        )
        
        count_evenements = evenements_anciens.count()
        evenements_anciens.delete()
        donnees_nettoyees += count_evenements
        
        # Supprimer les inscriptions expirées depuis plus de 6 mois
        inscriptions_anciennes = InscriptionEvenement.objects.filter(
            statut='expiree',
            date_inscription__lt=now - timedelta(days=180)
        )
        
        count_inscriptions = inscriptions_anciennes.count()
        inscriptions_anciennes.delete()
        donnees_nettoyees += count_inscriptions
        
        # Supprimer les accompagnants sans inscription
        accompagnants_orphelins = AccompagnantInvite.objects.filter(
            inscription__isnull=True
        )
        
        count_accompagnants = accompagnants_orphelins.count()
        accompagnants_orphelins.delete()
        donnees_nettoyees += count_accompagnants
        
        logger.info(f"Nettoyage terminé: {donnees_nettoyees} entrées supprimées")
        
        return {
            'donnees_nettoyees': donnees_nettoyees,
            'evenements_supprimes': count_evenements,
            'inscriptions_supprimees': count_inscriptions,
            'accompagnants_supprimes': count_accompagnants
        }
        
    except Exception as e:
        logger.error(f"Erreur dans nettoyer_anciennes_donnees: {str(e)}")
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60, exc=e)
        raise

@shared_task(bind=True, max_retries=3)
def generer_rapport_activite(self):
    """
    Génère un rapport d'activité hebdomadaire
    """
    try:
        now = timezone.now()
        semaine_passee = now - timedelta(days=7)
        
        # Statistiques de la semaine
        stats = {
            'evenements_crees': Evenement.objects.filter(
                created_at__gte=semaine_passee
            ).count(),
            'inscriptions_total': InscriptionEvenement.objects.filter(
                date_inscription__gte=semaine_passee
            ).count(),
            'inscriptions_confirmees': InscriptionEvenement.objects.filter(
                date_inscription__gte=semaine_passee,
                statut='confirmee'
            ).count(),
            'evenements_tenus': Evenement.objects.filter(
                date_debut__gte=semaine_passee,
                date_debut__lt=now,
                statut='termine'
            ).count(),
            'validations_traitees': ValidationEvenement.objects.filter(
                date_validation__gte=semaine_passee
            ).count(),
        }
        
        # Envoyer le rapport aux administrateurs
        from django.contrib.auth import get_user_model
        User = get_user_model()
        administrateurs = User.objects.filter(is_staff=True, is_active=True)
        
        for admin in administrateurs:
            try:
                send_mail(
                    subject=f"Rapport d'activité hebdomadaire - {settings.SITE_NAME}",
                    message=f"""
                    Bonjour {admin.get_full_name()},
                    
                    Voici le rapport d'activité de la semaine passée :
                    
                    📊 Statistiques :
                    - Événements créés : {stats['evenements_crees']}
                    - Inscriptions totales : {stats['inscriptions_total']}
                    - Inscriptions confirmées : {stats['inscriptions_confirmees']}
                    - Événements tenus : {stats['evenements_tenus']}
                    - Validations traitées : {stats['validations_traitees']}
                    
                    Cordialement,
                    L'équipe {settings.SITE_NAME}
                    """,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[admin.email],
                    fail_silently=False,
                )
                
                logger.info(f"Rapport envoyé à {admin.email}")
                
            except Exception as e:
                logger.error(f"Erreur envoi rapport à {admin.email}: {str(e)}")
        
        logger.info("Rapport d'activité généré et envoyé")
        
        return stats
        
    except Exception as e:
        logger.error(f"Erreur dans generer_rapport_activite: {str(e)}")
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60, exc=e)
        raise

# Tâches ponctuelles utiles

@shared_task
def envoyer_notification_personnalisee(evenement_id, message, destinataires_ids):
    """
    Envoie une notification personnalisée pour un événement
    """
    try:
        evenement = Evenement.objects.get(id=evenement_id)
        destinataires = Membre.objects.filter(id__in=destinataires_ids)
        
        notifications_envoyees = 0
        
        for membre in destinataires:
            try:
                send_mail(
                    subject=f"Notification : {evenement.titre}",
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[membre.email],
                    fail_silently=False,
                )
                notifications_envoyees += 1
                
            except Exception as e:
                logger.error(f"Erreur envoi notification à {membre.email}: {str(e)}")
        
        logger.info(f"Notification personnalisée envoyée à {notifications_envoyees} membres")
        
        return {
            'notifications_envoyees': notifications_envoyees,
            'total_destinataires': len(destinataires_ids)
        }
        
    except Exception as e:
        logger.error(f"Erreur dans envoyer_notification_personnalisee: {str(e)}")
        raise

@shared_task
def synchroniser_evenements_externes(self):
    """
    Synchronise avec des calendriers externes (Google Calendar, etc.)
    """
    try:
        # Implémenter la logique de synchronisation si nécessaire
        # Cette fonction pourrait être utilisée pour importer/exporter
        # des événements depuis/vers des calendriers externes
        
        logger.info("Synchronisation avec calendriers externes terminée")
        
        return {
            'synchronisation_reussie': True,
            'evenements_synchronises': 0
        }
        
    except Exception as e:
        logger.error(f"Erreur dans synchroniser_evenements_externes: {str(e)}")
        raise

# Fonction utilitaire pour tester les tâches
@shared_task
def test_celery_task():
    """
    Tâche de test pour vérifier que Celery fonctionne
    """
    logger.info("Tâche de test Celery exécutée avec succès")
    return "Test réussi"

# Configuration pour le monitoring
@shared_task
def health_check():
    """
    Vérification de l'état de santé des tâches
    """
    try:
        # Vérifier la connexion à la base de données
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        
        # Vérifier l'état des tâches importantes
        now = timezone.now()
        
        # Vérifier s'il y a des inscriptions bloquées
        inscriptions_problematiques = InscriptionEvenement.objects.filter(
            statut='en_attente',
            date_limite_confirmation__lt=now - timedelta(hours=1)
        ).count()
        
        # Vérifier s'il y a des validations en retard
        validations_en_retard = ValidationEvenement.objects.filter(
            statut_validation='en_attente',
            evenement__date_debut__lte=now + timedelta(days=1)
        ).count()
        
        status = {
            'database_ok': True,
            'inscriptions_problematiques': inscriptions_problematiques,
            'validations_en_retard': validations_en_retard,
            'timestamp': now.isoformat()
        }
        
        logger.info(f"Health check terminé: {status}")
        
        return status
        
    except Exception as e:
        logger.error(f"Erreur dans health_check: {str(e)}")
        return {
            'database_ok': False,
            'error': str(e),
            'timestamp': timezone.now().isoformat()
        }


@shared_task
def verifier_sante_notifications():
    """Vérification quotidienne de l'état des notifications"""
    try:
        status = NotificationMonitoring.verifier_sante_notifications()
        
        if status['sante'] != 'OK':
            # Alerter les administrateurs si problème
            from django.contrib.auth import get_user_model
            from django.core.mail import send_mail
            
            User = get_user_model()
            admins = User.objects.filter(is_staff=True, is_active=True)
            
            for admin in admins:
                send_mail(
                    subject=f"[ALERTE] Problème système notifications - {status['sante']}",
                    message=f"""
                    Problème détecté dans le système de notifications :
                    
                    - État : {status['sante']}
                    - Taux de succès : {status['taux_succes']}%
                    - Échecs 24h : {status['echecs_24h']}
                    - Succès 24h : {status['succes_24h']}
                    
                    Vérifiez les logs pour plus de détails.
                    """,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[admin.email],
                    fail_silently=True,
                )
        
        logger.info(f"Vérification santé notifications: {status}")
        return status
        
    except Exception as e:
        logger.error(f"Erreur vérification santé notifications: {str(e)}")
        raise

# AJOUTER dans CELERY_BEAT_SCHEDULE
'verifier-sante-notifications': {
    'task': 'apps.evenements.tasks.verifier_sante_notifications',
    'schedule': crontab(minute=0, hour=6),  # Tous les jours à 6h
},