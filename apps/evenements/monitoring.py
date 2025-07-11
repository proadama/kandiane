# apps/evenements/monitoring.py
from django.utils import timezone
from datetime import timedelta
from apps.core.models import Log
import logging

logger = logging.getLogger(__name__)

class NotificationMonitoring:
    """Classe pour le monitoring des notifications"""
    
    @staticmethod
    def verifier_sante_notifications():
        """Vérifie l'état de santé du système de notifications"""
        now = timezone.now()
        derniere_heure = now - timedelta(hours=1)
        derniere_24h = now - timedelta(hours=24)
        
        # Vérifications
        logs_recents = Log.objects.filter(
            action__startswith='NOTIFICATION_',
            created_at__gte=derniere_heure
        )
        
        echecs_24h = Log.objects.filter(
            action__startswith='NOTIFICATION_',
            details__success=False,
            created_at__gte=derniere_24h
        ).count()
        
        succes_24h = Log.objects.filter(
            action__startswith='NOTIFICATION_',
            details__success=True,
            created_at__gte=derniere_24h
        ).count()
        
        # Calcul du taux de succès
        total_24h = echecs_24h + succes_24h
        taux_succes = (succes_24h / total_24h * 100) if total_24h > 0 else 100
        
        status = {
            'sante': 'OK' if taux_succes >= 95 else 'ATTENTION' if taux_succes >= 85 else 'CRITIQUE',
            'taux_succes': round(taux_succes, 2),
            'echecs_24h': echecs_24h,
            'succes_24h': succes_24h,
            'logs_derniere_heure': logs_recents.count(),
            'timestamp': now.isoformat()
        }
        
        # Logger si problème
        if status['sante'] != 'OK':
            logger.warning(f"Problème notifications détecté: {status}")
        
        return status
    
    @staticmethod
    def generer_rapport_quotidien():
        """Génère un rapport quotidien des notifications"""
        yesterday = timezone.now() - timedelta(days=1)
        today = timezone.now()
        
        logs_jour = Log.objects.filter(
            action__startswith='NOTIFICATION_',
            created_at__gte=yesterday,
            created_at__lt=today
        )
        
        rapport = {
            'date': yesterday.date(),
            'total_notifications': logs_jour.count(),
            'reussites': logs_jour.filter(details__success=True).count(),
            'echecs': logs_jour.filter(details__success=False).count(),
            'par_type': {}
        }
        
        # Détail par type
        types_actions = logs_jour.values_list('action', flat=True).distinct()
        for action in types_actions:
            count = logs_jour.filter(action=action).count()
            rapport['par_type'][action] = count
        
        return rapport