# apps/core/context_processors.py
from apps.membres.models import Membre
from django.utils import timezone

def trash_counters(request):
    """Ajouter des compteurs d'éléments dans la corbeille au contexte."""
    context = {}
    
    # Uniquement pour les utilisateurs authentifiés avec droits admin
    if request.user.is_authenticated and request.user.is_staff:
        # Membres supprimés
        context['membres_trash_count'] = Membre.objects.only_deleted().count()
        
        # Ajouter d'autres compteurs lorsque de nouvelles applications seront implémentées
        # context['cotisations_trash_count'] = ...
        # context['evenements_trash_count'] = ...
        
        # Total pour badge global
        context['trash_count'] = context['membres_trash_count']  # + autres compteurs quand disponibles
    
    return context

def date_context(request):
    """
    Ajoute les dates courantes au contexte de tous les templates.
    """
    return {
        'current_date': timezone.now().date(),
        'today': timezone.now().date(),
        'now': timezone.now(),
    }