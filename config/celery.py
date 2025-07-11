# config/celery.py
import os
from celery import Celery
from celery.schedules import crontab

# Définir les paramètres par défaut de Django pour celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('project-web')

# Utiliser les settings de Django pour configurer Celery
app.config_from_object('django.conf:settings', namespace='CELERY')

# Charger automatiquement les tâches depuis les applications Django
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')


app.conf.beat_schedule = {
    'traiter-rappels-planifies': {
        'task': 'apps.cotisations.tasks.traiter_rappels_planifies_task',
        'schedule': crontab(minute='0', hour='*'),  # Toutes les heures
    },
}

# config/celery.py - Configuration Celery avec tâches événements
import os
from celery import Celery
from django.conf import settings
from celery.schedules import crontab

# Configuration de l'environnement Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('config')

# Configuration depuis les settings Django
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-découverte des tâches
app.autodiscover_tasks()

# Configuration des tâches périodiques pour les événements
app.conf.beat_schedule = {
    # Tâches de rappels et notifications
    'envoyer-rappels-confirmation': {
        'task': 'apps.evenements.tasks.envoyer_rappels_confirmation',
        'schedule': crontab(minute=0, hour='*/2'),  # Toutes les 2 heures
        'options': {
            'expires': 7200,  # 2 heures
            'retry': True,
            'retry_policy': {
                'max_retries': 3,
                'interval_start': 0,
                'interval_step': 0.2,
                'interval_max': 0.2,
            }
        }
    },
    
    'nettoyer-inscriptions-expirees': {
        'task': 'apps.evenements.tasks.nettoyer_inscriptions_expirees',
        'schedule': crontab(minute=0, hour=9),  # Tous les jours à 9h
        'options': {
            'expires': 3600,  # 1 heure
            'retry': True,
            'retry_policy': {
                'max_retries': 3,
                'interval_start': 0,
                'interval_step': 0.2,
                'interval_max': 0.2,
            }
        }
    },
    
    'generer-occurrences-recurrentes': {
        'task': 'apps.evenements.tasks.generer_occurrences_recurrentes',
        'schedule': crontab(minute=0, hour=0, day_of_week=1),  # Tous les lundis à minuit
        'options': {
            'expires': 86400,  # 24 heures
            'retry': True,
            'retry_policy': {
                'max_retries': 2,
                'interval_start': 0,
                'interval_step': 0.2,
                'interval_max': 0.2,
            }
        }
    },
    
    'envoyer-rappels-evenements': {
        'task': 'apps.evenements.tasks.envoyer_rappels_evenements',
        'schedule': crontab(minute=0, hour=10),  # Tous les jours à 10h
        'options': {
            'expires': 3600,  # 1 heure
            'retry': True,
            'retry_policy': {
                'max_retries': 3,
                'interval_start': 0,
                'interval_step': 0.2,
                'interval_max': 0.2,
            }
        }
    },
    
    'notifier-validations-urgentes': {
        'task': 'apps.evenements.tasks.notifier_validations_urgentes',
        'schedule': crontab(minute=0, hour=8),  # Tous les jours à 8h
        'options': {
            'expires': 3600,  # 1 heure
            'retry': True,
            'retry_policy': {
                'max_retries': 3,
                'interval_start': 0,
                'interval_step': 0.2,
                'interval_max': 0.2,
            }
        }
    },
    
    # Tâches de maintenance
    'nettoyer-anciennes-donnees': {
        'task': 'apps.evenements.tasks.nettoyer_anciennes_donnees',
        'schedule': crontab(minute=0, hour=2, day_of_week=0),  # Tous les dimanches à 2h
        'options': {
            'expires': 86400,  # 24 heures
            'retry': True,
            'retry_policy': {
                'max_retries': 2,
                'interval_start': 0,
                'interval_step': 0.2,
                'interval_max': 0.2,
            }
        }
    },
    
    'generer-rapport-activite': {
        'task': 'apps.evenements.tasks.generer_rapport_activite',
        'schedule': crontab(minute=0, hour=9, day_of_week=1),  # Tous les lundis à 9h
        'options': {
            'expires': 3600,  # 1 heure
            'retry': True,
            'retry_policy': {
                'max_retries': 2,
                'interval_start': 0,
                'interval_step': 0.2,
                'interval_max': 0.2,
            }
        }
    },
    
    # Tâches de monitoring
    'health-check': {
        'task': 'apps.evenements.tasks.health_check',
        'schedule': crontab(minute='*/15'),  # Toutes les 15 minutes
        'options': {
            'expires': 900,  # 15 minutes
            'retry': False,  # Pas de retry pour le monitoring
        }
    },
    
    # Tâches de synchronisation (optionnel)
    'synchroniser-evenements-externes': {
        'task': 'apps.evenements.tasks.synchroniser_evenements_externes',
        'schedule': crontab(minute=0, hour=6),  # Tous les jours à 6h
        'options': {
            'expires': 7200,  # 2 heures
            'retry': True,
            'retry_policy': {
                'max_retries': 2,
                'interval_start': 0,
                'interval_step': 0.2,
                'interval_max': 0.2,
            }
        }
    },
}

# Configuration générale des tâches
app.conf.update(
    # Fuseau horaire
    timezone='Europe/Paris',
    
    # Sérialisation
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    
    # Résultats des tâches
    result_expires=3600,  # 1 heure
    result_backend='django-db',
    
    # Configuration des workers
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    
    # Gestion des erreurs
    task_reject_on_worker_lost=True,
    
    # Compression
    task_compression='gzip',
    result_compression='gzip',
    
    # Monitoring
    worker_send_task_events=True,
    task_send_sent_event=True,
    
    # Limites de tâches
    task_soft_time_limit=300,  # 5 minutes
    task_time_limit=600,  # 10 minutes
    
    # Configuration des queues
    task_default_queue='default',
    task_default_exchange='default',
    task_default_routing_key='default',
    
    # Queues spécifiques
    task_routes={
        'apps.evenements.tasks.envoyer_rappels_confirmation': {'queue': 'notifications'},
        'apps.evenements.tasks.nettoyer_inscriptions_expirees': {'queue': 'maintenance'},
        'apps.evenements.tasks.generer_occurrences_recurrentes': {'queue': 'maintenance'},
        'apps.evenements.tasks.envoyer_rappels_evenements': {'queue': 'notifications'},
        'apps.evenements.tasks.notifier_validations_urgentes': {'queue': 'notifications'},
        'apps.evenements.tasks.nettoyer_anciennes_donnees': {'queue': 'maintenance'},
        'apps.evenements.tasks.generer_rapport_activite': {'queue': 'reports'},
        'apps.evenements.tasks.health_check': {'queue': 'monitoring'},
        'apps.core.notifications.send_event_email': {'queue': 'emails'},
        'apps.core.notifications.send_batch_notifications': {'queue': 'emails'},
    },
    
    # Configuration des queues
    task_queues={
        'default': {
            'exchange': 'default',
            'routing_key': 'default',
        },
        'notifications': {
            'exchange': 'notifications',
            'routing_key': 'notifications',
        },
        'emails': {
            'exchange': 'emails',
            'routing_key': 'emails',
        },
        'maintenance': {
            'exchange': 'maintenance',
            'routing_key': 'maintenance',
        },
        'reports': {
            'exchange': 'reports',
            'routing_key': 'reports',
        },
        'monitoring': {
            'exchange': 'monitoring',
            'routing_key': 'monitoring',
        },
    },
)

# Configuration spécifique pour les emails
app.conf.update(
    # Limitation du débit pour les emails
    task_annotations={
        'apps.core.notifications.send_event_email': {'rate_limit': '30/m'},
        'apps.core.notifications.send_batch_notifications': {'rate_limit': '10/m'},
    },
)

# Handlers pour les signaux Celery
@app.task(bind=True)
def debug_task(self):
    """Tâche de debug pour tester Celery"""
    print(f'Request: {self.request!r}')
    return 'Debug task completed'

# Configuration des logs
import logging
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)

# Handler pour les erreurs de tâches
@app.task(bind=True, base=app.Task)
def error_handler(self, task_id, error, traceback):
    """
    Gestionnaire d'erreurs pour les tâches Celery
    """
    logger.error(f'Task {task_id} raised error: {error}')
    logger.error(f'Traceback: {traceback}')
    
    # Optionnel : envoyer une notification d'erreur aux admins
    if hasattr(settings, 'ADMINS') and settings.ADMINS:
        from django.core.mail import mail_admins
        mail_admins(
            subject=f'Erreur Celery - Task {task_id}',
            message=f'La tâche {task_id} a échoué avec l\'erreur: {error}\n\nTraceback:\n{traceback}',
            fail_silently=True,
        )

# Configuration des hooks
@app.task(bind=True)
def on_task_failure(self, task_id, error, traceback):
    """Hook appelé lors de l'échec d'une tâche"""
    logger.error(f'Task {task_id} failed: {error}')

@app.task(bind=True)
def on_task_success(self, task_id, result):
    """Hook appelé lors du succès d'une tâche"""
    logger.info(f'Task {task_id} succeeded with result: {result}')

# Configuration du worker
if __name__ == '__main__':
    app.start()