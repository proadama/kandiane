# 🔧 Guide de Dépannage - Application Événements

## 📋 Vue d'ensemble

Ce guide aide à diagnostiquer et résoudre les problèmes courants de l'application événements. Il est organisé par symptôme avec des solutions étape par étape.

## 🚨 Problèmes Critiques

### **1. Événements non visibles**

#### **Symptômes**
- Les événements n'apparaissent pas dans la liste
- Dashboard affiche 0 événement
- Erreur 404 sur détail d'événement

#### **Diagnostic**
```bash
# Vérifier les événements en base
python manage.py shell
>>> from apps.evenements.models import Evenement
>>> Evenement.objects.count()  # Total avec supprimés
>>> Evenement.objects.all().count()  # Seulement actifs
>>> Evenement.objects.with_deleted().count()  # Avec supprimés logiques
```

#### **Causes et Solutions**

##### **Problème de permissions**
```python
# Vérifier les permissions utilisateur
>>> user = User.objects.get(username='probleme')
>>> user.is_staff
>>> user.has_perm('evenements.view_evenement')
```

**Solution :**
```python
# Donner les bonnes permissions
>>> from django.contrib.auth.models import Permission
>>> perm = Permission.objects.get(codename='view_evenement')
>>> user.user_permissions.add(perm)
```

##### **Événements en mauvais statut**
```python
# Vérifier les statuts
>>> Evenement.objects.values('statut').annotate(count=Count('id'))
```

**Solution :**
```python
# Publier les événements en brouillon
>>> Evenement.objects.filter(statut='brouillon').update(statut='publie')
```

##### **Suppression logique active**
```python
# Vérifier les suppressions logiques
>>> Evenement.objects.only_deleted().count()
```

**Solution :**
```python
# Restaurer les événements supprimés par erreur
>>> for evt in Evenement.objects.only_deleted():
>>>     evt.deleted_at = None
>>>     evt.save()
```

### **2. Inscriptions impossibles**

#### **Symptômes**
- Bouton d'inscription grisé
- Message "Vous ne pouvez pas vous inscrire"
- Erreur lors de la soumission du formulaire

#### **Diagnostic**
```python
# Tester l'éligibilité
>>> evenement = Evenement.objects.get(id=X)
>>> membre = Membre.objects.get(email='user@example.com')
>>> peut_inscrire, message = evenement.peut_s_inscrire(membre)
>>> print(f"Peut s'inscrire: {peut_inscrire}, Message: {message}")
```

#### **Solutions par Cause**

##### **Événement complet**
```python
# Vérifier les places
>>> evenement.places_disponibles
>>> evenement.est_complet
>>> evenement.inscriptions.filter(statut__in=['confirmee', 'presente']).count()
```

**Solution :**
```python
# Augmenter la capacité
>>> evenement.capacite_max = 50
>>> evenement.save()

# Ou nettoyer les inscriptions expirées
>>> from apps.evenements.tasks import nettoyer_inscriptions_expirees
>>> nettoyer_inscriptions_expirees.delay()
```

##### **Inscriptions fermées**
```python
# Vérifier les dates d'inscription
>>> evenement.inscriptions_ouvertes
>>> evenement.date_ouverture_inscriptions
>>> evenement.date_fermeture_inscriptions
```

**Solution :**
```python
# Rouvrir les inscriptions
>>> evenement.inscriptions_ouvertes = True
>>> evenement.date_fermeture_inscriptions = None
>>> evenement.save()
```

##### **Membre déjà inscrit**
```python
# Vérifier les inscriptions existantes
>>> InscriptionEvenement.objects.filter(
...     evenement=evenement, 
...     membre=membre,
...     statut__in=['en_attente', 'confirmee']
... ).exists()
```

**Solution :**
```python
# Permettre les inscriptions multiples ou annuler l'existante
>>> inscription_existante = InscriptionEvenement.objects.get(...)
>>> inscription_existante.annuler_inscription("Réinscription")
```

### **3. Notifications non envoyées**

#### **Symptômes**
- Pas d'email de confirmation
- Rappels non reçus
- Aucune notification d'annulation

#### **Diagnostic**
```bash
# Vérifier Celery
celery -A config inspect active
celery -A config inspect stats

# Vérifier la queue
celery -A config inspect reserved

# Logs
tail -f logs/celery.log
tail -f logs/evenements.log
```

#### **Solutions**

##### **Celery non démarré**
```bash
# Démarrer Celery worker
celery -A config worker -l info

# Démarrer Celery beat (pour tâches programmées)
celery -A config beat -l info

# En développement (mode eager)
export CELERY_TASK_ALWAYS_EAGER=True
```

##### **Configuration email incorrecte**
```python
# Tester la configuration email
>>> from django.core.mail import send_mail
>>> send_mail('Test', 'Message test', 'from@example.com', ['to@example.com'])
```

**Solution :**
```python
# Dans settings.py
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email@gmail.com'
EMAIL_HOST_PASSWORD = 'your-app-password'
```

##### **Préférences utilisateur**
```python
# Vérifier les préférences de notification
>>> membre.preferences_notifications.email_inscriptions
```

**Solution :**
```python
# Réactiver les notifications
>>> prefs = membre.preferences_notifications
>>> prefs.email_inscriptions = True
>>> prefs.save()
```

## 🐛 Problèmes Fréquents

### **4. Validation d'événements bloquée**

#### **Symptômes**
- Événements restent en "attente de validation"
- Notifications aux validateurs non envoyées
- Impossible d'approuver/refuser

#### **Diagnostic**
```python
# Vérifier les validations en attente
>>> ValidationEvenement.objects.en_attente().count()
>>> ValidationEvenement.objects.urgentes().count()

# Vérifier les permissions des validateurs
>>> User.objects.filter(is_staff=True, is_active=True).count()
```

#### **Solutions**

##### **Pas de validateurs actifs**
```python
# Créer un validateur
>>> admin = User.objects.create_user(
...     username='admin_val',
...     email='admin@example.com',
...     is_staff=True,
...     is_active=True
... )
>>> admin.set_password('secure_password')
>>> admin.save()
```

##### **Événements restent en attente**
```python
# Valider manuellement
>>> validation = ValidationEvenement.objects.get(evenement_id=X)
>>> validateur = User.objects.filter(is_staff=True).first()
>>> validation.approuver(validateur, "Validation manuelle")
```

### **5. Exports qui échouent**

#### **Symptômes**
- Erreur 500 lors d'export PDF/Excel
- Téléchargement interrompu
- Fichiers corrompus

#### **Diagnostic**
```python
# Tester les exports manuellement
>>> from apps.evenements.views import ExportInscriptionsView
>>> evenement = Evenement.objects.first()
# Vérifier les bibliothèques
>>> import openpyxl
>>> import reportlab
```

#### **Solutions**

##### **Bibliothèques manquantes**
```bash
# Installer les dépendances
pip install openpyxl reportlab Pillow

# Ou via requirements
echo "openpyxl>=3.1.0" >> requirements.txt
echo "reportlab>=4.0.0" >> requirements.txt
pip install -r requirements.txt
```

##### **Mémoire insuffisante**
```python
# Dans settings.py pour gros exports
DATA_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024  # 50MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024
```

##### **Timeout sur gros exports**
```python
# Augmenter les timeouts
import socket
socket.setdefaulttimeout(300)  # 5 minutes
```

### **6. Performance dégradée**

#### **Symptômes**
- Pages lentes à charger
- Timeout sur liste d'événements
- Dashboard très lent

#### **Diagnostic**
```python
# Analyser les requêtes SQL
>>> from django.db import connection
>>> from django.conf import settings
>>> settings.DEBUG = True  # Temporairement

# Après une action lente
>>> len(connection.queries)
>>> for query in connection.queries[-10:]:
...     print(query['sql'][:100])
```

#### **Solutions**

##### **Requêtes N+1**
```python
# Utiliser select_related/prefetch_related
>>> evenements = Evenement.objects.select_related(
...     'type_evenement', 'organisateur'
... ).prefetch_related('inscriptions__membre')
```

##### **Pas d'indexes**
```bash
# Vérifier les migrations d'index
python manage.py showmigrations evenements
python manage.py migrate
```

##### **Cache manquant**
```python
# Activer le cache
>>> from django.core.cache import cache
>>> cache.set('evenements_stats', stats, 3600)
```

### **7. Données incohérentes**

#### **Symptômes**
- Places disponibles incorrectes
- Montants calculés faux
- Statuts d'inscription incohérents

#### **Diagnostic**
```python
# Vérifier la cohérence des données
>>> for evenement in Evenement.objects.all():
...     inscriptions_count = evenement.inscriptions.filter(
...         statut__in=['confirmee', 'presente']
...     ).count()
...     if inscriptions_count > evenement.capacite_max:
...         print(f"Surbooking sur {evenement.id}: {inscriptions_count}/{evenement.capacite_max}")
```

#### **Solutions**

##### **Recalcul des places**
```python
# Script de correction
>>> for evenement in Evenement.objects.all():
...     # Recalculer les places correctement
...     evenement.save()  # Déclenche les signaux de recalcul
```

##### **Correction des montants**
```python
# Recalculer les montants d'inscription
>>> for inscription in InscriptionEvenement.objects.all():
...     montant_attendu = inscription.calculer_montant_total()
...     if inscription.montant_restant != (montant_attendu - inscription.montant_paye):
...         inscription.save()  # Déclenche le recalcul
```

## 🔍 Outils de Diagnostic

### **Commands de Management Django**

#### **Vérification de l'intégrité**
```python
# apps/evenements/management/commands/check_evenements_integrity.py
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Vérifie l\'intégrité des données événements'
    
    def handle(self, *args, **options):
        # Vérifications multiples
        self.check_places_coherence()
        self.check_dates_coherence()
        self.check_inscriptions_coherence()
    
    def check_places_coherence(self):
        problemes = []
        for evt in Evenement.objects.all():
            inscriptions = evt.inscriptions.filter(
                statut__in=['confirmee', 'presente']
            ).count()
            if inscriptions > evt.capacite_max:
                problemes.append(f"Surbooking {evt.id}: {inscriptions}/{evt.capacite_max}")
        
        if problemes:
            self.stdout.write(self.style.ERROR('Problèmes de places:'))
            for pb in problemes:
                self.stdout.write(f"  - {pb}")
        else:
            self.stdout.write(self.style.SUCCESS('✓ Places cohérentes'))
```

```bash
# Utilisation
python manage.py check_evenements_integrity
```

#### **Nettoyage des données**
```python
# apps/evenements/management/commands/cleanup_evenements.py
class Command(BaseCommand):
    help = 'Nettoie les données incohérentes'
    
    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--fix-places', action='store_true')
        parser.add_argument('--fix-dates', action='store_true')
    
    def handle(self, *args, **options):
        if options['fix_places']:
            self.fix_places_coherence(options['dry_run'])
```

```bash
# Utilisation
python manage.py cleanup_evenements --dry-run
python manage.py cleanup_evenements --fix-places
```

### **Logs et Monitoring**

#### **Configuration de logs détaillés**
```python
# settings.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'evenements_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/evenements.log',
            'maxBytes': 1024*1024*15,  # 15MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
        'notifications_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/notifications.log',
            'maxBytes': 1024*1024*15,
            'backupCount': 10,
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'apps.evenements': {
            'handlers': ['evenements_file'],
            'level': 'INFO',
            'propagate': True,
        },
        'apps.evenements.notifications': {
            'handlers': ['notifications_file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
```

#### **Monitoring avec des métriques**
```python
# apps/evenements/monitoring.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

def get_health_status():
    """Statut de santé de l'application événements"""
    now = timezone.now()
    
    # Vérifications critiques
    checks = {
        'evenements_actifs': Evenement.objects.publies().count() > 0,
        'inscriptions_recentes': InscriptionEvenement.objects.filter(
            date_inscription__gte=now - timedelta(days=7)
        ).count() > 0,
        'celery_workers': check_celery_workers(),
        'notifications_ok': check_recent_notifications(),
        'validations_en_attente': ValidationEvenement.objects.en_attente().count() < 10
    }
    
    return {
        'status': 'healthy' if all(checks.values()) else 'warning',
        'checks': checks,
        'timestamp': now.isoformat()
    }

def check_celery_workers():
    """Vérifie si les workers Celery sont actifs"""
    try:
        from celery import current_app
        inspect = current_app.control.inspect()
        active = inspect.active()
        return bool(active)
    except:
        return False
```

### **Scripts de Debug**

#### **Debug des inscriptions**
```python
# debug_inscriptions.py
def debug_inscription_probleme(inscription_id):
    """Debug approfondi d'une inscription problématique"""
    inscription = InscriptionEvenement.objects.get(id=inscription_id)
    
    print(f"=== DEBUG INSCRIPTION {inscription_id} ===")
    print(f"Membre: {inscription.membre}")
    print(f"Événement: {inscription.evenement}")
    print(f"Statut: {inscription.statut}")
    print(f"Date inscription: {inscription.date_inscription}")
    print(f"Date limite: {inscription.date_limite_confirmation}")
    print(f"Code confirmation: {inscription.code_confirmation}")
    
    # Vérifications
    peut_inscrire, message = inscription.evenement.peut_s_inscrire(inscription.membre)
    print(f"Peut s'inscrire: {peut_inscrire} - {message}")
    
    # Historique des modifications
    from django.contrib.admin.models import LogEntry
    logs = LogEntry.objects.filter(
        content_type__model='inscriptionevenement',
        object_id=str(inscription_id)
    ).order_by('-action_time')
    
    print(f"\n=== HISTORIQUE ===")
    for log in logs:
        print(f"{log.action_time}: {log.get_change_message()}")
```

#### **Debug des notifications**
```python
def debug_notifications_membre(membre_email):
    """Debug des notifications pour un membre"""
    membre = Membre.objects.get(email=membre_email)
    
    print(f"=== DEBUG NOTIFICATIONS {membre_email} ===")
    
    # Préférences
    try:
        prefs = membre.preferences_notifications
        print(f"Email inscriptions: {prefs.email_inscriptions}")
        print(f"Email rappels: {prefs.email_rappels}")
    except:
        print("Pas de préférences définies")
    
    # Logs récents
    logs = NotificationLog.objects.filter(
        destinataire=membre_email
    ).order_by('-date_envoi')[:10]
    
    print(f"\n=== LOGS RÉCENTS ===")
    for log in logs:
        print(f"{log.date_envoi}: {log.type_notification} - {log.statut}")
        if log.message_erreur:
            print(f"  Erreur: {log.message_erreur}")
```

## 📞 Escalade et Support

### **Niveaux de Support**

#### **Niveau 1 : Problèmes Utilisateur**
- Inscription impossible → Vérifier éligibilité
- Email non reçu → Vérifier spam, préférences
- Événement non visible → Vérifier statut, permissions

#### **Niveau 2 : Problèmes Technique**
- Performance dégradée → Analyser requêtes SQL
- Exports qui échouent → Vérifier bibliothèques
- Notifications en masse échouent → Vérifier Celery

#### **Niveau 3 : Problèmes Système**
- Corruption de données → Scripts de réparation
- Problèmes d'intégration → Vérifier signaux
- Performance critique → Optimisation base de données

### **Procédure d'Escalade**

```bash
# 1. Collecte d'informations
python manage.py check_evenements_integrity
python manage.py shell -c "from apps.evenements.monitoring import get_health_status; print(get_health_status())"

# 2. Logs détaillés
tail -f logs/evenements.log logs/celery.log logs/django.log

# 3. Sauvegarde avant intervention
python manage.py dumpdata apps.evenements > backup_evenements.json

# 4. Tests après correction
python manage.py test apps.evenements.tests.test_workflow_*
```

### **Contacts et Ressources**

#### **Documentation**
- [Documentation Django](https://docs.djangoproject.com/)
- [Celery Documentation](https://docs.celeryproject.org/)
- [Guide d'intégration](./INTEGRATION.md)

#### **Outils**
- **Monitoring** : Django Debug Toolbar, Sentry
- **Base de données** : pgAdmin, MySQL Workbench
- **Cache** : Redis CLI, Memcached stats
- **Logs** : ELK Stack, Grafana

---

**🔧 Guide de dépannage complet et pratique**  
**📊 Outils de diagnostic intégrés**  
**🚨 Procédures d'escalade structurées**  
**📞 Support multi-niveaux organisé**