# apps/core/views.py
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render

class HomeView(TemplateView):
    """
    Vue de la page d'accueil.
    """
    template_name = 'core/home.html'

class DashboardView(LoginRequiredMixin, TemplateView):
    """
    Vue du tableau de bord, accessible uniquement aux utilisateurs connectés.
    """
    template_name = 'core/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Ajouter des données au contexte si nécessaire
        return context

def maintenance_view(request):
    """
    Vue affichée lorsque le site est en maintenance.
    """
    context = {
        'title': 'Site en maintenance',
        'message': 'Notre site est actuellement en maintenance. Merci de revenir plus tard.'
    }
    return render(request, 'core/maintenance.html', context, status=503)

def error_404(request, exception):
    """
    Vue pour les erreurs 404.
    """
    return render(request, 'core/errors/404.html', status=404)

def error_500(request):
    """
    Vue pour les erreurs 500.
    """
    return render(request, 'core/errors/500.html', status=500)