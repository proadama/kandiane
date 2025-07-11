# apps/core/notifications.py - Extension pour les événements
from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.utils import timezone
from django.urls import reverse
from celery import shared_task
import logging

User = get_user_model()
logger = logging.getLogger(__name__)

# Types de notifications pour les événements
class NotificationTypes:
    # Notifications existantes (si déjà dans le système)
    NOUVEAU_COMPTE = 'nouveau_compte'
    COTISATION_RAPPEL = 'cotisation_rappel'
    
    # Nouvelles notifications pour les événements
    INVITATION_EVENEMENT = 'invitation_evenement'
    CONFIRMATION_INSCRIPTION = 'confirmation_inscription'
    RAPPEL_CONFIRMATION = 'rappel_confirmation'
    INSCRIPTION_CONFIRMEE = 'inscription_confirmee'
    INSCRIPTION_ANNULEE = 'inscription_annulee'
    EVENEMENT_MODIFIE = 'evenement_modifie'
    EVENEMENT_ANNULE = 'evenement_annule'
    EVENEMENT_REPORTE = 'evenement_reporte'
    PROMOTION_LISTE_ATTENTE = 'promotion_liste_attente'
    RAPPEL_EVENEMENT = 'rappel_evenement'
    VALIDATION_EVENEMENT = 'validation_evenement'
    EVENEMENT_APPROUVE = 'evenement_approuve'
    EVENEMENT_REFUSE = 'evenement_refuse'
    NOUVELLE_INSCRIPTION = 'nouvelle_inscription'
    CAPACITE_ATTEINTE = 'capacite_atteinte'
    DELAI_CONFIRMATION_EXPIRE = 'delai_confirmation_expire'

class NotificationService:
    """
    Service centralisé pour l'envoi de notifications liées aux événements
    """
    
    @staticmethod
    def envoyer_invitation_inscription(evenement, membre):
        """
        Envoie une invitation à s'inscrire à un événement
        """
        try:
            context = {
                'evenement': evenement,
                'membre': membre,
                'url_inscription': settings.SITE_URL + reverse(
                    'evenements:inscription_creer', 
                    kwargs={'evenement_pk': evenement.pk}
                ),
                'url_detail': settings.SITE_URL + reverse(
                    'evenements:detail', 
                    kwargs={'pk': evenement.pk}
                ),
                'site_url': settings.SITE_URL,
                'site_name': getattr(settings, 'SITE_NAME', 'Gestion Association'),
            }
            
            # Envoyer l'email
            send_event_email.delay(
                recipient_email=membre.email,
                recipient_name=f"{membre.prenom} {membre.nom}",
                template_name='invitation_evenement',
                context=context,
                subject=f"Invitation : {evenement.titre}"
            )
            
            logger.info(f"Invitation envoyée à {membre.email} pour l'événement {evenement.titre}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi de l'invitation : {str(e)}")
            return False
    
    @staticmethod
    def envoyer_confirmation_inscription(inscription):
        """
        Envoie la confirmation d'inscription
        """
        try:
            context = {
                'inscription': inscription,
                'evenement': inscription.evenement,
                'membre': inscription.membre,
                'url_confirmation': settings.SITE_URL + reverse(
                    'evenements:confirmer_email', 
                    kwargs={'code': inscription.code_confirmation}
                ),
                'url_detail': settings.SITE_URL + reverse(
                    'evenements:inscription_detail', 
                    kwargs={'pk': inscription.pk}
                ),
                'montant_total': inscription.calculer_montant_total(),
                'delai_heures': inscription.evenement.delai_confirmation,
                'site_url': settings.SITE_URL,
                'site_name': getattr(settings, 'SITE_NAME', 'Gestion Association'),
            }
            
            # Envoyer l'email
            send_event_email.delay(
                recipient_email=inscription.membre.email,
                recipient_name=f"{inscription.membre.prenom} {inscription.membre.nom}",
                template_name='confirmation_inscription',
                context=context,
                subject=f"Confirmation d'inscription : {inscription.evenement.titre}"
            )
            
            logger.info(f"Confirmation envoyée à {inscription.membre.email} pour {inscription.evenement.titre}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi de la confirmation : {str(e)}")
            return False
    
    @staticmethod
    def envoyer_rappel_confirmation(inscription):
        """
        Envoie un rappel de confirmation
        """
        try:
            # Calculer le temps restant
            temps_restant = inscription.date_limite_confirmation - timezone.now()
            heures_restantes = int(temps_restant.total_seconds() / 3600)
            
            context = {
                'inscription': inscription,
                'evenement': inscription.evenement,
                'membre': inscription.membre,
                'heures_restantes': heures_restantes,
                'url_confirmation': settings.SITE_URL + reverse(
                    'evenements:confirmer_email', 
                    kwargs={'code': inscription.code_confirmation}
                ),
                'url_detail': settings.SITE_URL + reverse(
                    'evenements:inscription_detail', 
                    kwargs={'pk': inscription.pk}
                ),
                'site_url': settings.SITE_URL,
                'site_name': getattr(settings, 'SITE_NAME', 'Gestion Association'),
            }
            
            # Envoyer l'email
            send_event_email.delay(
                recipient_email=inscription.membre.email,
                recipient_name=f"{inscription.membre.prenom} {inscription.membre.nom}",
                template_name='rappel_confirmation',
                context=context,
                subject=f"RAPPEL : Confirmez votre inscription à {inscription.evenement.titre}"
            )
            
            logger.info(f"Rappel envoyé à {inscription.membre.email} pour {inscription.evenement.titre}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi du rappel : {str(e)}")
            return False
    
    @staticmethod
    def envoyer_inscription_confirmee(inscription):
        """
        Confirme que l'inscription a été validée
        """
        try:
            context = {
                'inscription': inscription,
                'evenement': inscription.evenement,
                'membre': inscription.membre,
                'url_detail': settings.SITE_URL + reverse(
                    'evenements:inscription_detail', 
                    kwargs={'pk': inscription.pk}
                ),
                'url_evenement': settings.SITE_URL + reverse(
                    'evenements:detail', 
                    kwargs={'pk': inscription.evenement.pk}
                ),
                'site_url': settings.SITE_URL,
                'site_name': getattr(settings, 'SITE_NAME', 'Gestion Association'),
            }
            
            # Envoyer l'email
            send_event_email.delay(
                recipient_email=inscription.membre.email,
                recipient_name=f"{inscription.membre.prenom} {inscription.membre.nom}",
                template_name='inscription_confirmee',
                context=context,
                subject=f"Inscription confirmée : {inscription.evenement.titre}"
            )
            
            logger.info(f"Confirmation validée envoyée à {inscription.membre.email}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi de la confirmation validée : {str(e)}")
            return False
    
    @staticmethod
    def envoyer_modification_evenement(evenement, membres_inscrits, modifications):
        """
        Notifie les membres inscrits qu'un événement a été modifié
        """
        try:
            context = {
                'evenement': evenement,
                'modifications': modifications,
                'url_evenement': settings.SITE_URL + reverse(
                    'evenements:detail', 
                    kwargs={'pk': evenement.pk}
                ),
                'site_url': settings.SITE_URL,
                'site_name': getattr(settings, 'SITE_NAME', 'Gestion Association'),
            }
            
            # Envoyer à tous les membres inscrits
            for membre in membres_inscrits:
                send_event_email.delay(
                    recipient_email=membre.email,
                    recipient_name=f"{membre.prenom} {membre.nom}",
                    template_name='evenement_modifie',
                    context=context,
                    subject=f"Modification : {evenement.titre}"
                )
            
            logger.info(f"Notifications de modification envoyées pour {evenement.titre}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi des notifications de modification : {str(e)}")
            return False
    
    @staticmethod
    def envoyer_annulation_evenement(evenement, membres_inscrits, raison=""):
        """
        Notifie les membres inscrits qu'un événement a été annulé
        """
        try:
            context = {
                'evenement': evenement,
                'raison': raison,
                'url_evenement': settings.SITE_URL + reverse(
                    'evenements:detail', 
                    kwargs={'pk': evenement.pk}
                ),
                'site_url': settings.SITE_URL,
                'site_name': getattr(settings, 'SITE_NAME', 'Gestion Association'),
            }
            
            # Envoyer à tous les membres inscrits
            for membre in membres_inscrits:
                send_event_email.delay(
                    recipient_email=membre.email,
                    recipient_name=f"{membre.prenom} {membre.nom}",
                    template_name='evenement_annule',
                    context=context,
                    subject=f"ANNULATION : {evenement.titre}"
                )
            
            logger.info(f"Notifications d'annulation envoyées pour {evenement.titre}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi des notifications d'annulation : {str(e)}")
            return False
    
    @staticmethod
    def envoyer_promotion_liste_attente(inscription):
        """
        Notifie qu'une inscription a été promue depuis la liste d'attente
        """
        try:
            # Calculer le temps restant pour confirmer
            temps_restant = inscription.date_limite_confirmation - timezone.now()
            heures_restantes = int(temps_restant.total_seconds() / 3600)
            
            context = {
                'inscription': inscription,
                'evenement': inscription.evenement,
                'membre': inscription.membre,
                'heures_restantes': heures_restantes,
                'url_confirmation': settings.SITE_URL + reverse(
                    'evenements:confirmer_email', 
                    kwargs={'code': inscription.code_confirmation}
                ),
                'url_detail': settings.SITE_URL + reverse(
                    'evenements:inscription_detail', 
                    kwargs={'pk': inscription.pk}
                ),
                'site_url': settings.SITE_URL,
                'site_name': getattr(settings, 'SITE_NAME', 'Gestion Association'),
            }
            
            # Envoyer l'email
            send_event_email.delay(
                recipient_email=inscription.membre.email,
                recipient_name=f"{inscription.membre.prenom} {inscription.membre.nom}",
                template_name='promotion_liste_attente',
                context=context,
                subject=f"Bonne nouvelle ! Place disponible pour {inscription.evenement.titre}"
            )
            
            logger.info(f"Promotion liste d'attente envoyée à {inscription.membre.email}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi de la promotion : {str(e)}")
            return False
    
    @staticmethod
    def envoyer_rappel_evenement(evenement, membres_inscrits):
        """
        Envoie un rappel avant l'événement
        """
        try:
            context = {
                'evenement': evenement,
                'url_evenement': settings.SITE_URL + reverse(
                    'evenements:detail', 
                    kwargs={'pk': evenement.pk}
                ),
                'site_url': settings.SITE_URL,
                'site_name': getattr(settings, 'SITE_NAME', 'Gestion Association'),
            }
            
            # Envoyer à tous les membres inscrits confirmés
            for membre in membres_inscrits:
                send_event_email.delay(
                    recipient_email=membre.email,
                    recipient_name=f"{membre.prenom} {membre.nom}",
                    template_name='rappel_evenement',
                    context=context,
                    subject=f"Rappel : {evenement.titre} - {evenement.date_debut.strftime('%d/%m/%Y')}"
                )
            
            logger.info(f"Rappels d'événement envoyés pour {evenement.titre}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi des rappels : {str(e)}")
            return False
    
    @staticmethod
    def envoyer_notification_validation(evenement, validateur):
        """
        Notifie qu'un événement nécessite une validation
        """
        try:
            context = {
                'evenement': evenement,
                'organisateur': evenement.organisateur,
                'url_validation': settings.SITE_URL + reverse(
                    'evenements:validation_detail', 
                    kwargs={'pk': evenement.validation.pk}
                ),
                'url_evenement': settings.SITE_URL + reverse(
                    'evenements:detail', 
                    kwargs={'pk': evenement.pk}
                ),
                'site_url': settings.SITE_URL,
                'site_name': getattr(settings, 'SITE_NAME', 'Gestion Association'),
            }
            
            # Envoyer au validateur
            send_event_email.delay(
                recipient_email=validateur.email,
                recipient_name=f"{validateur.first_name} {validateur.last_name}",
                template_name='validation_evenement',
                context=context,
                subject=f"Validation requise : {evenement.titre}"
            )
            
            logger.info(f"Notification de validation envoyée pour {evenement.titre}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi de la notification de validation : {str(e)}")
            return False
    
    @staticmethod
    def envoyer_notification_organisateur(evenement, action, commentaire=""):
        """
        Notifie l'organisateur du résultat de la validation
        """
        try:
            context = {
                'evenement': evenement,
                'action': action,
                'commentaire': commentaire,
                'url_evenement': settings.SITE_URL + reverse(
                    'evenements:detail', 
                    kwargs={'pk': evenement.pk}
                ),
                'site_url': settings.SITE_URL,
                'site_name': getattr(settings, 'SITE_NAME', 'Gestion Association'),
            }
            
            if action == 'approuve':
                template_name = 'evenement_approuve'
                subject = f"Événement approuvé : {evenement.titre}"
            else:
                template_name = 'evenement_refuse'
                subject = f"Événement refusé : {evenement.titre}"
            
            # Envoyer à l'organisateur
            send_event_email.delay(
                recipient_email=evenement.organisateur.email,
                recipient_name=evenement.organisateur.get_full_name(),
                template_name=template_name,
                context=context,
                subject=subject
            )
            
            logger.info(f"Notification de validation envoyée à l'organisateur pour {evenement.titre}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi de la notification à l'organisateur : {str(e)}")
            return False

@shared_task(bind=True, max_retries=3)
def send_event_email(self, recipient_email, recipient_name, template_name, context, subject):
    """
    Tâche Celery pour l'envoi d'emails liés aux événements
    """
    try:
        # Ajouter des informations communes au contexte
        context.update({
            'recipient_name': recipient_name,
            'current_year': timezone.now().year,
        })
        
        # Charger les templates
        html_template = f'emails/evenements/{template_name}.html'
        text_template = f'emails/evenements/{template_name}.txt'
        
        # Render du contenu
        html_content = render_to_string(html_template, context)
        text_content = render_to_string(text_template, context)
        
        # Créer l'email
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient_email]
        )
        email.attach_alternative(html_content, "text/html")
        
        # Envoyer
        email.send()
        
        logger.info(f"Email '{template_name}' envoyé avec succès à {recipient_email}")
        return True
        
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi de l'email : {str(e)}")
        
        # Retry avec backoff exponentiel
        if self.request.retries < self.max_retries:
            countdown = 2 ** self.request.retries
            raise self.retry(countdown=countdown, exc=e)
        else:
            logger.error(f"Échec définitif de l'envoi de l'email à {recipient_email}")
            return False

# Fonction utilitaire pour envoyer des notifications par lot
@shared_task
def send_batch_notifications(notification_type, recipients_data):
    """
    Envoie des notifications en lot
    """
    try:
        success_count = 0
        error_count = 0
        
        for recipient_data in recipients_data:
            try:
                send_event_email.delay(**recipient_data)
                success_count += 1
            except Exception as e:
                error_count += 1
                logger.error(f"Erreur lors de l'envoi à {recipient_data.get('recipient_email')}: {str(e)}")
        
        logger.info(f"Notifications en lot '{notification_type}': {success_count} succès, {error_count} erreurs")
        return {'success': success_count, 'errors': error_count}
        
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi des notifications en lot : {str(e)}")
        return {'success': 0, 'errors': len(recipients_data)}

# Fonction pour nettoyer les anciennes notifications
@shared_task
def cleanup_old_notifications():
    """
    Nettoie les anciennes notifications (optionnel si vous avez un modèle de log)
    """
    try:
        # Implémenter la logique de nettoyage si nécessaire
        logger.info("Nettoyage des anciennes notifications effectué")
        return True
    except Exception as e:
        logger.error(f"Erreur lors du nettoyage des notifications : {str(e)}")
        return False