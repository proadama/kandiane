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