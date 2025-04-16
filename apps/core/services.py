# Créer un nouveau fichier: apps/core/services.py

import logging
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings

logger = logging.getLogger(__name__)

class EmailService:
    """
    Service pour l'envoi d'emails avec contenu HTML et texte
    """
    
    @staticmethod
    def send_template_email(template_name, context, subject, to_email, from_email=None):
        """
        Envoie un email basé sur un template HTML avec une version texte automatique
        
        Args:
            template_name (str): Chemin vers le template HTML (sans extension)
            context (dict): Contexte à passer au template
            subject (str): Sujet de l'email
            to_email (str or list): Destinataire(s) de l'email
            from_email (str, optional): Email d'expéditeur. Par défaut utilise DEFAULT_FROM_EMAIL
            
        Returns:
            bool: True si l'email a été envoyé avec succès, False sinon
        """
        try:
            # Utiliser l'email d'expéditeur par défaut si non spécifié
            if from_email is None:
                from_email = settings.DEFAULT_FROM_EMAIL
                
            # Convertir to_email en liste s'il s'agit d'une chaîne
            if isinstance(to_email, str):
                to_email = [to_email]
                
            # Générer le contenu HTML à partir du template
            html_content = render_to_string(f"{template_name}.html", context)
            
            # Créer une version texte à partir du HTML
            text_content = strip_tags(html_content)
            
            # Créer l'email
            msg = EmailMultiAlternatives(subject, text_content, from_email, to_email)
            msg.attach_alternative(html_content, "text/html")
            
            # Envoyer l'email
            return msg.send() > 0
            
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi de l'email: {str(e)}")
            return False