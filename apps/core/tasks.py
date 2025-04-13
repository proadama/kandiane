# apps/core/tasks.py
from celery import shared_task
from django.utils import timezone
from django.apps import apps
from django.conf import settings

@shared_task
def purge_deleted_items(days=90):
    """
    Supprime définitivement les éléments qui sont dans la corbeille 
    depuis plus de X jours.
    """
    purge_date = timezone.now() - timezone.timedelta(days=days)
    
    # Modèles à purger
    models_to_purge = [
        'membres.Membre',
        # Ajouter ici les autres modèles au fur et à mesure
    ]
    
    results = {}
    
    for model_path in models_to_purge:
        app_label, model_name = model_path.split('.')
        Model = apps.get_model(app_label, model_name)
        
        # Récupérer les éléments à purger
        items = Model.objects.only_deleted().filter(deleted_at__lt=purge_date)
        count = items.count()
        
        # Supprimer définitivement
        if count > 0:
            for item in items:
                item.delete(hard=True)
        
        results[model_path] = count
    
    return results