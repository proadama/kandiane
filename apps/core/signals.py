# apps/core/signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
import logging

logger = logging.getLogger('django')

@receiver(post_save)
def log_model_save(sender, instance, created, **kwargs):
    """
    Log les créations et mises à jour d'objets.
    """
    # Ignorer les modèles internes de Django
    if sender._meta.app_label in ('auth', 'admin', 'sessions', 'contenttypes'):
        return
    
    # Log l'événement
    action = 'créé' if created else 'modifié'
    model_name = sender._meta.verbose_name
    logger.info(f"{model_name} {instance} {action}")

@receiver(post_delete)
def log_model_delete(sender, instance, **kwargs):
    """
    Log les suppressions d'objets.
    """
    # Ignorer les modèles internes de Django
    if sender._meta.app_label in ('auth', 'admin', 'sessions', 'contenttypes'):
        return
    
    # Log l'événement
    model_name = sender._meta.verbose_name
    logger.info(f"{model_name} {instance} supprimé")