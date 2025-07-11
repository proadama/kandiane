# apps/evenements/services.py - CRÉER CE FICHIER
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

class NotificationService:
    """Service de gestion des notifications pour les événements"""
    
    @staticmethod
    def envoyer_rappel_confirmation(inscription):
        """Envoie un rappel de confirmation d'inscription"""
        try:
            # Vérifier les préférences utilisateur
            if not inscription.membre.utilisateur.profile.get_notification_preference('evenement_rappel_confirmation'):
                logger.info(f"Rappel ignoré pour {inscription.membre.email} - préférence désactivée")
                return False
            
            # Envoyer l'email
            subject = f"Rappel : Confirmez votre inscription à {inscription.evenement.titre}"
            context = {
                'inscription': inscription,
                'evenement': inscription.evenement,
                'membre': inscription.membre,
                'url_confirmation': f"{settings.SITE_URL}/evenements/inscriptions/confirmer/{inscription.code_confirmation}/",
                'site_name': getattr(settings, 'SITE_NAME', 'Gestion Association'),
            }
            
            message = render_to_string('emails/evenements/rappel.html', context)
            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[inscription.membre.email],
                fail_silently=False,
            )
            
            # Logger le succès
            _log_notification(inscription.membre.utilisateur, 'RAPPEL_CONFIRMATION', {
                'evenement_id': inscription.evenement.id,
                'inscription_id': inscription.id,
                'success': True
            })
            
            return True
            
        except Exception as e:
            # Logger l'erreur
            _log_notification(inscription.membre.utilisateur, 'RAPPEL_CONFIRMATION', {
                'evenement_id': inscription.evenement.id,
                'inscription_id': inscription.id,
                'success': False,
                'error': str(e)
            })
            logger.error(f"Erreur envoi rappel pour inscription {inscription.id}: {str(e)}")
            return False
    
    @staticmethod
    def envoyer_promotion_liste_attente(inscription):
        """Notifie une promotion depuis la liste d'attente"""
        try:
            if not inscription.membre.utilisateur.profile.get_notification_preference('evenement_promotion_liste'):
                return False
            
            subject = f"Bonne nouvelle ! Place disponible pour {inscription.evenement.titre}"
            context = {
                'inscription': inscription,
                'evenement': inscription.evenement,
                'membre': inscription.membre,
                'url_confirmation': f"{settings.SITE_URL}/evenements/inscriptions/confirmer/{inscription.code_confirmation}/",
            }
            
            message = render_to_string('emails/evenements/promotion_liste_attente.html', context)
            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[inscription.membre.email],
                fail_silently=False,
            )
            
            _log_notification(inscription.membre.utilisateur, 'PROMOTION_LISTE_ATTENTE', {
                'evenement_id': inscription.evenement.id,
                'inscription_id': inscription.id,
                'success': True
            })
            
            return True
            
        except Exception as e:
            _log_notification(inscription.membre.utilisateur, 'PROMOTION_LISTE_ATTENTE', {
                'evenement_id': inscription.evenement.id,
                'inscription_id': inscription.id,
                'success': False,
                'error': str(e)
            })
            return False
    
    @staticmethod
    def envoyer_notification_expiration(inscription):
        """Notifie l'expiration d'une inscription"""
        try:
            if not inscription.membre.utilisateur.profile.get_notification_preference('evenement_rappel_confirmation'):
                return False
            
            subject = f"Inscription expirée : {inscription.evenement.titre}"
            context = {
                'inscription': inscription,
                'evenement': inscription.evenement,
                'membre': inscription.membre,
            }
            
            message = render_to_string('emails/evenements/expiration.html', context)
            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[inscription.membre.email],
                fail_silently=False,
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur notification expiration: {str(e)}")
            return False
    
    @staticmethod
    def envoyer_rappel_evenement(evenement, membres_inscrits):
        """Envoie un rappel avant un événement"""
        try:
            emails_envoyes = 0
            
            for membre in membres_inscrits:
                if membre.utilisateur.profile.get_notification_preference('evenement_rappel_confirmation'):
                    
                    subject = f"Rappel : {evenement.titre} bientôt !"
                    context = {
                        'evenement': evenement,
                        'membre': membre,
                    }
                    
                    message = render_to_string('emails/evenements/rappel_evenement.html', context)
                    
                    send_mail(
                        subject=subject,
                        message=message,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[membre.email],
                        fail_silently=False,
                    )
                    emails_envoyes += 1
            
            return emails_envoyes > 0
            
        except Exception as e:
            logger.error(f"Erreur rappel événement {evenement.id}: {str(e)}")
            return False
    
    @staticmethod
    def get_statistiques_envois(periode_jours=30):
        """Récupère les statistiques d'envois sur une période"""
        from django.utils import timezone
        from datetime import timedelta
        
        date_debut = timezone.now() - timedelta(days=periode_jours)
        
        logs_notifications = Log.objects.filter(
            action__startswith='NOTIFICATION_',
            created_at__gte=date_debut
        )
        
        stats = {
            'total_envois': logs_notifications.count(),
            'envois_reussis': logs_notifications.filter(
                details__success=True
            ).count(),
            'envois_echecs': logs_notifications.filter(
                details__success=False
            ).count(),
            'par_type': {}
        }
        
        # Statistiques par type de notification
        types_notifications = [
            'RAPPEL_CONFIRMATION',
            'PROMOTION_LISTE_ATTENTE', 
            'NOTIFICATION_EXPIRATION',
            'RAPPEL_EVENEMENT'
        ]
        
        for type_notif in types_notifications:
            count = logs_notifications.filter(
                action=f'NOTIFICATION_{type_notif}'
            ).count()
            stats['par_type'][type_notif] = count
        
        return stats
    
    @staticmethod
    def get_historique_membre(membre, limite=50):
        """Récupère l'historique des notifications pour un membre"""
        return Log.objects.filter(
            utilisateur=membre.utilisateur,
            action__startswith='NOTIFICATION_'
        ).order_by('-created_at')[:limite]
    
    @staticmethod
    def get_logs_echecs(periode_jours=7):
        """Récupère les logs d'échecs récents pour monitoring"""
        from django.utils import timezone
        from datetime import timedelta
        
        date_debut = timezone.now() - timedelta(days=periode_jours)
        
        return Log.objects.filter(
            action__startswith='NOTIFICATION_',
            details__success=False,
            created_at__gte=date_debut
        ).order_by('-created_at')
    

def _log_notification(utilisateur, action, details, request=None):
    """Fonction améliorée pour logger les notifications"""
    try:
        # Extraire l'IP si disponible
        adresse_ip = None
        if request:
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                adresse_ip = x_forwarded_for.split(',')[0]
            else:
                adresse_ip = request.META.get('REMOTE_ADDR')
        
        Log.objects.create(
            utilisateur=utilisateur,
            action=f"NOTIFICATION_{action}",
            details={
                'timestamp': timezone.now().isoformat(),
                'action_type': action,
                **details
            },
            adresse_ip=adresse_ip
        )
        
        logger.info(f"Log notification créé : {action} pour {utilisateur.email if utilisateur else 'Anonyme'}")
        
    except Exception as e:
        logger.error(f"Erreur logging notification: {str(e)}")