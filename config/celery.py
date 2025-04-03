# config/celery.py
import os
from celery import Celery

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