# Dans apps/cotisations/scheduler.py
from apscheduler.schedulers.background import BackgroundScheduler
from django_apscheduler.jobstores import DjangoJobStore
from django.utils import timezone
from apps.cotisations.tasks import traiter_rappels_planifies
import logging
import time

logger = logging.getLogger(__name__)

def start():
    try:
        scheduler = BackgroundScheduler()
        scheduler.add_jobstore(DjangoJobStore(), "default")
        
        # Vérifier si le job existe déjà pour éviter les doublons
        scheduler.add_job(
            traiter_rappels_planifies_avec_retry,  # Fonction modifiée avec retry
            'interval',
            minutes=10,
            # hours=1
            name='traiter_rappels_planifies',
            id='traiter_rappels_planifies',
            replace_existing=True,
            jobstore='default'
        )
        
        scheduler.start()
        logger.info("Scheduler démarré avec succès")
        print("Scheduler démarré avec succès")
    except Exception as e:
        logger.error(f"Erreur lors du démarrage du scheduler: {e}")
        print(f"Erreur lors du démarrage du scheduler: {e}")

def traiter_rappels_planifies_avec_retry():
    """Wrapper avec retry pour le traitement des rappels planifiés"""
    from apps.cotisations.tasks import traiter_rappels_planifies
    
    max_retries = 3
    retry_delay = 2  # secondes
    
    for attempt in range(max_retries):
        try:
            return traiter_rappels_planifies()
        except Exception as e:
            if 'database is locked' in str(e):
                logger.warning(f"Base de données verrouillée, tentative {attempt+1}/{max_retries}... attente de {retry_delay}s")
                time.sleep(retry_delay)
                retry_delay *= 2  # augmentation exponentielle du délai
            else:
                logger.error(f"Erreur lors du traitement des rappels: {e}")
                raise
    
    logger.error(f"Échec du traitement des rappels après {max_retries} tentatives")
    return 0