# apps/core/mixins.py
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.contrib import messages
from django.shortcuts import redirect
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy

class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Mixin pour limiter l'accès aux utilisateurs avec le statut staff.
    """
    def test_func(self):
        return self.request.user.is_staff
    
    def handle_no_permission(self):
        messages.error(self.request, "Vous n'avez pas les permissions nécessaires pour accéder à cette page.")
        return super().handle_no_permission()

class PermissionRequiredMixin(LoginRequiredMixin):
    """
    Mixin pour vérifier que l'utilisateur a une permission spécifique.
    """
    permission_required = None
    
    def dispatch(self, request, *args, **kwargs):
        if not self.has_permission():
            messages.error(request, "Vous n'avez pas les permissions nécessaires pour accéder à cette page.")
            return redirect('core:home')
        return super().dispatch(request, *args, **kwargs)
    
    def has_permission(self):
        if self.permission_required is None:
            return False
        
        if self.request.user.is_superuser:
            return True
        
        # Note: Cette implémentation sera complétée quand l'application accounts sera développée
        # Pour l'instant, seuls les superusers ont accès
        return False

class AjaxRequiredMixin:
    """
    Mixin pour limiter les vues aux requêtes AJAX.
    """
    def dispatch(self, request, *args, **kwargs):
        if not request.headers.get('x-requested-with') == 'XMLHttpRequest':
            raise PermissionDenied("Cette vue nécessite une requête AJAX.")
        return super().dispatch(request, *args, **kwargs)
    
class TrashViewMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Mixin pour les vues de corbeille."""
    
    trash_template_name = None  # À définir dans la classe enfant
    admin_required = True
    
    def test_func(self):
        """Vérifier les permissions pour accéder à la corbeille."""
        if self.admin_required:
            return self.request.user.is_staff
        return True
    
    def get_queryset(self):
        """Récupérer uniquement les objets supprimés."""
        return self.model.objects.only_deleted()

class RestoreViewMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Mixin pour les vues de restauration."""
    
    success_url = None  # À définir dans la classe enfant
    admin_required = True
    
    def test_func(self):
        """Vérifier les permissions pour restaurer des objets."""
        if self.admin_required:
            return self.request.user.is_staff
        return True
    
    def post(self, request, *args, **kwargs):
        """Restaurer l'objet et rediriger."""
        obj = self.get_object()
        obj.restore(user=request.user)
        return self.get_success_response()