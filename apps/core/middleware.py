# apps/core/middleware.py
import time
import json
import logging
from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings

logger = logging.getLogger('django')

class RequestLogMiddleware(MiddlewareMixin):
    """
    Middleware pour journaliser les requêtes HTTP.
    """
    def process_request(self, request):
        request.start_time = time.time()
        
    def process_response(self, request, response):
        if hasattr(request, 'start_time'):
            duration = time.time() - request.start_time
            
            # Construire le message de log
            log_data = {
                'path': request.path,
                'method': request.method,
                'duration': duration,
                'status': response.status_code,
                'user': request.user.username if hasattr(request, 'user') and request.user.is_authenticated else 'anonymous',
                'ip': self.get_client_ip(request),
            }
            
            # Journaliser la requête
            if response.status_code >= 500:
                logger.error(f"Request: {json.dumps(log_data)}")
            elif response.status_code >= 400:
                logger.warning(f"Request: {json.dumps(log_data)}")
            else:
                logger.info(f"Request: {json.dumps(log_data)}")
                
        return response
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

class MaintenanceModeMiddleware(MiddlewareMixin):
    """
    Middleware pour gérer le mode maintenance.
    """
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        # Vérifier si mode maintenance est activé
        if hasattr(settings, 'MAINTENANCE_MODE') and settings.MAINTENANCE_MODE:
            # Ignorer les requêtes vers l'administration
            if not request.path.startswith('/admin/'):
                from django.shortcuts import render
                context = getattr(settings, 'MAINTENANCE_CONTEXT', {
                    'title': 'Site en maintenance',
                    'message': 'Notre site est actuellement en maintenance. Merci de revenir plus tard.'
                })
                return render(request, 'core/maintenance.html', context, status=503)
        
        # Continuer avec la chaîne de middleware
        return self.get_response(request)
    
    def process_request(self, request):
        if hasattr(settings, 'MAINTENANCE_MODE') and settings.MAINTENANCE_MODE:
            if not request.path.startswith('/admin/'):
                from django.shortcuts import render
                context = getattr(settings, 'MAINTENANCE_CONTEXT', {
                    'title': 'Site en maintenance',
                    'message': 'Notre site est actuellement en maintenance. Merci de revenir plus tard.'
                })
                return render(request, 'core/maintenance.html', context, status=503)
        return None

    def process_response(self, request, response):
        if hasattr(request, 'start_time'):
            duration = time.time() - request.start_time
            
            # Vérifier si response est un objet de réponse valide
            # Si ce n'est pas un objet de réponse (par exemple dans les tests), 
            # initialiser des valeurs par défaut
            status_code = getattr(response, 'status_code', 200)
            
            # Construire le message de log
            log_data = {
                'path': request.path,
                'method': request.method,
                'duration': duration,
                'status': status_code,
                'user': request.user.username if hasattr(request, 'user') and request.user.is_authenticated else 'anonymous',
                'ip': self.get_client_ip(request),
            }
            
            # Journaliser la requête
            if status_code >= 500:
                logger.error(f"Request: {json.dumps(log_data)}")
            elif status_code >= 400:
                logger.warning(f"Request: {json.dumps(log_data)}")
            else:
                logger.info(f"Request: {json.dumps(log_data)}")
                
        return response