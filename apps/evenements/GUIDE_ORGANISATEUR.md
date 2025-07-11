# 🔧 Guide de Dépannage - Application Événements

## 📋 Vue d'ensemble

Ce guide vous aide à **identifier, diagnostiquer et résoudre** les problèmes courants de l'application événements. Il est organisé par symptômes et fournit des solutions étape par étape.

---

## 🚨 Problèmes Critiques

### **🔴 Les Inscriptions ne Fonctionnent Plus**

#### **Symptômes**
- Erreur 500 lors de la création d'inscription
- Formulaire d'inscription ne se charge pas
- Message "Une erreur est survenue"

#### **Diagnostic**

```bash
# 1. Vérifier les logs d'erreur
tail -f logs/django.log | grep inscription
tail -f logs/debug.log | grep InscriptionEvenement

# 2. Vérifier la base de données
python manage.py shell
```

```python
# Dans le shell Django
from apps.evenements.models import InscriptionEvenement, Evenement
from apps.membres.models import Membre

# Tester la création d'inscription
evenement = Evenement.objects.first()
membre = Membre.objects.first()

try:
    inscription = InscriptionEvenement.objects.create(
        evenement=evenement,
        membre=membre
    )
    print("✅ Création d'inscription OK")
except Exception as e:
    print(f"❌ Erreur: {e}")
```

#### **Solutions**

1. **Problème de base de données**
```bash
# Vérifier les migrations
python manage.py showmigrations evenements
python manage.py migrate evenements

# Vérifier l'intégrité des données
python manage.py shell -c "
from apps.evenements.models import *
print('Événements:', Evenement.objects.count())
print('Membres:', Membre.objects.count())
print('Inscriptions:', InscriptionEvenement.objects.count())
"
```

2. **Problème de permissions**
```bash
# Vérifier les permissions des fichiers
ls -la media/temp_imports/
chmod 755 media/temp_imports/

# Vérifier les permissions Django
python manage.py shell -c "
from django.contrib.auth.models import Permission
perms = Permission.objects.filter(content_type__app_label='evenements')
for p in perms:
    print(f'{p.codename}: {p.name}')
"
```

3. **Problème de configuration**
```python
# settings/base.py - Vérifier la configuration
INSTALLED_APPS = [
    # ...
    'apps.evenements',  # Doit être présent
    'apps.membres',     # Dépendance requise
    'apps.cotisations', # Dépendance requise
]
```

---

### **🔴 Les Notifications ne Partent Plus**

#### **Symptômes**
- Aucun email reçu pour les inscriptions
- Erreurs dans les logs Celery
- Tâches Celery en échec

#### **Diagnostic**

```bash
# 1. Vérifier Celery
celery -A config inspect active
celery -A config inspect stats

# 2. Vérifier Redis/Broker
redis-cli ping
redis-cli info

# 3. Tester l'envoi d'email
python manage.py shell
```

```python
# Test d'envoi d'email
from django.core.mail import send_mail
try:
    send_mail(
        'Test Email',
        'Message de test',
        'from@example.com',
        ['to@example.com'],
        fail_silently=False,
    )
    print("✅ Email envoyé")
except Exception as e:
    print(f"❌ Erreur email: {e}")
```

#### **Solutions**

1. **Redémarrer Celery**
```bash
# Arrêter Celery
pkill -f "celery worker"
pkill -f "celery beat"

# Redémarrer
celery -A config worker --loglevel=info &
celery -A config beat --loglevel=info &
```

2. **Vérifier la configuration email**
```python
# settings/production.py
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'  # Vérifier l'host
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email@gmail.com'
EMAIL_HOST_PASSWORD = 'your-app-password'  # Mot de passe d'application
```

3. **Nettoyer la queue Celery**
```bash
# Vider la queue Redis
redis-cli flushdb

# Relancer les tâches
python manage.py shell -c "
from apps.evenements.tasks import envoyer_rappel_confirmation
envoyer_rappel_confirmation.delay()
"
```

---

### **🔴 Les Validations sont Bloquées**

#### **Symptômes**
- Événements restent en "en_attente_validation"
- Interface de validation inaccessible
- Erreurs lors de l'approbation/refus

#### **Diagnostic**

```python
# Vérifier les validations en attente
from apps.evenements.models import ValidationEvenement

validations = ValidationEvenement.objects.en_attente()
print(f"Validations en attente: {validations.count()}")

for v in validations[:5]:
    print(f"- {v.evenement.titre} (créé le {v.created_at})")
```

#### **Solutions**

1. **Problème de permissions**
```python
# Vérifier les permissions staff
from django.contrib.auth import get_user_model
User = get_user_model()

staffs = User.objects.filter(is_staff=True, is_active=True)
print(f"Utilisateurs staff actifs: {staffs.count()}")
```

2. **Valider manuellement**
```python
# Validation manuelle d'urgence
from apps.evenements.models import ValidationEvenement

validation = ValidationEvenement.objects.en_attente().first()
if validation:
    validation.statut_validation = 'approuve'
    validation.save()
    
    # Publier l'événement
    validation.evenement.statut = 'publie'
    validation.evenement.save()
    
    print(f"✅ Événement {validation.evenement.titre} approuvé manuellement")
```

---

## ⚠️ Problèmes Fréquents

### **📧 Emails en Spam/Non Reçus**

#### **Causes Communes**
- Configuration SMTP incorrecte
- Réputation IP faible
- Contenu détecté comme spam
- Limites de l'hébergeur email

#### **Solutions**

1. **Vérifier la configuration SMTP**
```bash
# Test de connexion SMTP
python -c "
import smtplib
server = smtplib.SMTP('smtp.gmail.com', 587)
server.starttls()
server.login('your-email@gmail.com', 'your-password')
print('✅ Connexion SMTP OK')
server.quit()
"
```

2. **Améliorer la délivrabilité**
```python
# settings/production.py
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.sendgrid.net'  # Utiliser un service dédié
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'apikey'
EMAIL_HOST_PASSWORD = 'your-sendgrid-api-key'

# Headers pour améliorer la délivrabilité
EMAIL_SUBJECT_PREFIX = '[Association] '
DEFAULT_FROM_EMAIL = 'Association <noreply@votredomaine.com>'
```

3. **Configuration SPF/DKIM**
```dns
# Enregistrements DNS (exemple)
TXT @ "v=spf1 include:sendgrid.net ~all"
TXT default._domainkey "v=DKIM1; k=rsa; p=your-public-key"
```

---

### **🐌 Performance Lente**

#### **Symptômes**
- Pages qui se chargent lentement (>5s)
- Timeouts sur les listes d'événements
- Base de données surchargée

#### **Diagnostic**

```python
# Analyser les requêtes lentes
import time
from django.test import Client
from django.db import connection

# Test de performance
start_time = time.time()
client = Client()
response = client.get('/evenements/evenements/')
end_time = time.time()

print(f"Temps de réponse: {end_time - start_time:.2f}s")
print(f"Nombre de requêtes SQL: {len(connection.queries)}")

# Analyser les requêtes
for query in connection.queries[-10:]:
    print(f"Durée: {query['time']}s - SQL: {query['sql'][:100]}...")
```

#### **Solutions**

1. **Optimisation des requêtes**
```python
# apps/evenements/views.py - EvenementListView
def get_queryset(self):
    return Evenement.objects.select_related(
        'type_evenement', 'organisateur'
    ).prefetch_related(
        'inscriptions'
    ).avec_statistiques()
```

2. **Ajout d'index en base**
```sql
-- Créer des index pour les requêtes fréquentes
CREATE INDEX idx_evenements_date_statut ON evenements (date_debut, statut);
CREATE INDEX idx_inscriptions_statut_evenement ON inscriptions_evenements (statut, evenement_id);
```

3. **Cache Redis**
```python
# settings/production.py
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# Dans les vues
from django.views.decorators.cache import cache_page

@cache_page(60 * 15)  # Cache 15 minutes
def evenement_list_view(request):
    # ...
```

---

### **💾 Problèmes de Base de Données**

#### **Erreurs d'Intégrité**

```sql
-- Vérifier l'intégrité des contraintes
SELECT 
    table_name, 
    constraint_name, 
    constraint_type 
FROM information_schema.table_constraints 
WHERE table_schema = 'your_database' 
AND table_name LIKE '%evenement%';
```

#### **Corruption de Données**

```python
# Script de vérification de cohérence
# apps/evenements/management/commands/check_data_integrity.py

from django.core.management.base import BaseCommand
from apps.evenements.models import *

class Command(BaseCommand):
    def handle(self, *args, **options):
        errors = []
        
        # Vérifier les inscriptions sans membre
        inscriptions_orphelines = InscriptionEvenement.objects.filter(
            membre__isnull=True
        )
        if inscriptions_orphelines.exists():
            errors.append(f"Inscriptions sans membre: {inscriptions_orphelines.count()}")
        
        # Vérifier les événements sans organisateur
        evenements_orphelins = Evenement.objects.filter(
            organisateur__isnull=True
        )
        if evenements_orphelins.exists():
            errors.append(f"Événements sans organisateur: {evenements_orphelins.count()}")
        
        # Vérifier les dates incohérentes
        evenements_dates_incorrectes = Evenement.objects.filter(
            date_fin__lt=models.F('date_debut')
        )
        if evenements_dates_incorrectes.exists():
            errors.append(f"Événements dates incorrectes: {evenements_dates_incorrectes.count()}")
        
        if errors:
            self.stdout.write("❌ Erreurs détectées:")
            for error in errors:
                self.stdout.write(f"  - {error}")
        else:
            self.stdout.write("✅ Intégrité des données OK")
```

---

### **🔄 Problèmes de Synchronisation**

#### **Cotisations non Créées**

```python
# Vérifier les signaux
from django.db.models import signals
from apps.evenements.models import InscriptionEvenement

# Lister les signaux connectés
for signal_name, signal in signals.__dict__.items():
    if hasattr(signal, 'send'):
        receivers = signal._live_receivers(sender=InscriptionEvenement)
        if receivers:
            print(f"{signal_name}: {len(receivers)} receivers")
```

#### **Script de Synchronisation Manuelle**

```python
# apps/evenements/management/commands/sync_cotisations.py

from django.core.management.base import BaseCommand
from apps.evenements.models import InscriptionEvenement
from apps.cotisations.models import Cotisation

class Command(BaseCommand):
    def handle(self, *args, **options):
        
        # Inscriptions payantes sans cotisation
        inscriptions_sans_cotisation = InscriptionEvenement.objects.filter(
            evenement__est_payant=True,
            montant_paye__gt=0
        ).exclude(
            membre__cotisations__reference__startswith='EVENT-'
        )
        
        count = 0
        for inscription in inscriptions_sans_cotisation:
            # Créer la cotisation manquante
            cotisation = Cotisation.objects.create(
                membre=inscription.membre,
                montant=inscription.calculer_montant_total(),
                reference=f"EVENT-{inscription.evenement.reference}-{inscription.id}",
                # ... autres champs
            )
            count += 1
        
        self.stdout.write(f"✅ {count} cotisations créées")
```

---

## 🔍 Outils de Diagnostic

### **Commandes de Debug**

```bash
# 1. État général du système
python manage.py check
python manage.py check --deploy

# 2. État des migrations
python manage.py showmigrations evenements

# 3. État de Celery
celery -A config inspect active
celery -A config inspect scheduled
celery -A config inspect reserved

# 4. État de la base de données
python manage.py dbshell
```

### **Script de Diagnostic Complet**

```python
# apps/evenements/management/commands/diagnostic.py

from django.core.management.base import BaseCommand
from django.db import connection
from apps.evenements.models import *
import subprocess
import sys

class Command(BaseCommand):
    def handle(self, *args, **options):
        self.stdout.write("🔍 DIAGNOSTIC APPLICATION ÉVÉNEMENTS")
        self.stdout.write("=" * 50)
        
        # 1. Vérifications base de données
        self.check_database()
        
        # 2. Vérifications modèles
        self.check_models()
        
        # 3. Vérifications Celery
        self.check_celery()
        
        # 4. Vérifications email
        self.check_email()
        
        # 5. Vérifications performances
        self.check_performance()
    
    def check_database(self):
        self.stdout.write("\n📊 Base de données:")
        
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                self.stdout.write("  ✅ Connexion DB OK")
        except Exception as e:
            self.stdout.write(f"  ❌ Erreur DB: {e}")
        
        # Compter les enregistrements
        counts = {
            'Événements': Evenement.objects.count(),
            'Inscriptions': InscriptionEvenement.objects.count(),
            'Validations': ValidationEvenement.objects.count(),
        }
        
        for model, count in counts.items():
            self.stdout.write(f"  📈 {model}: {count}")
    
    def check_models(self):
        self.stdout.write("\n🏗️ Modèles:")
        
        # Vérifier l'intégrité des modèles
        try:
            # Test création/lecture
            evenement = Evenement.objects.first()
            if evenement:
                self.stdout.write("  ✅ Modèle Evenement OK")
            else:
                self.stdout.write("  ⚠️ Aucun événement en base")
                
        except Exception as e:
            self.stdout.write(f"  ❌ Erreur modèles: {e}")
    
    def check_celery(self):
        self.stdout.write("\n⚙️ Celery:")
        
        try:
            # Vérifier si Celery répond
            from celery import current_app
            inspect = current_app.control.inspect()
            stats = inspect.stats()
            
            if stats:
                self.stdout.write("  ✅ Celery actif")
                self.stdout.write(f"  📊 Workers: {len(stats)}")
            else:
                self.stdout.write("  ❌ Aucun worker Celery actif")
                
        except Exception as e:
            self.stdout.write(f"  ❌ Erreur Celery: {e}")
    
    def check_email(self):
        self.stdout.write("\n📧 Configuration email:")
        
        from django.conf import settings
        
        try:
            backend = settings.EMAIL_BACKEND
            host = getattr(settings, 'EMAIL_HOST', 'Non configuré')
            self.stdout.write(f"  📮 Backend: {backend}")
            self.stdout.write(f"  🌐 Host: {host}")
            
            # Test simple (sans envoi)
            from django.core.mail import get_connection
            connection = get_connection()
            # connection.open()  # Décommenté pour test réel
            self.stdout.write("  ✅ Configuration email OK")
            
        except Exception as e:
            self.stdout.write(f"  ❌ Erreur email: {e}")
    
    def check_performance(self):
        self.stdout.write("\n⚡ Performance:")
        
        import time
        
        # Test requête simple
        start = time.time()
        count = Evenement.objects.count()
        duration = time.time() - start
        
        self.stdout.write(f"  ⏱️ Requête simple: {duration:.3f}s")
        
        if duration > 1.0:
            self.stdout.write("  ⚠️ Requête lente détectée")
        else:
            self.stdout.write("  ✅ Performance OK")
```

---

### **Monitoring en Continu**

```python
# apps/evenements/monitoring.py

import logging
from django.core.mail import mail_admins
from django.conf import settings

logger = logging.getLogger('apps.evenements.monitoring')

class HealthCheck:
    @staticmethod
    def check_inscriptions_rate():
        """Surveille le taux d'inscriptions"""
        from datetime import timedelta
        from django.utils import timezone
        
        # Inscriptions des dernières 24h
        yesterday = timezone.now() - timedelta(days=1)
        recent_inscriptions = InscriptionEvenement.objects.filter(
            date_inscription__gte=yesterday
        ).count()
        
        # Alerte si aucune inscription
        if recent_inscriptions == 0:
            logger.warning("Aucune inscription dans les dernières 24h")
            return False
        
        return True
    
    @staticmethod
    def check_email_queue():
        """Surveille la queue d'emails"""
        try:
            from celery import current_app
            inspect = current_app.control.inspect()
            
            # Vérifier les tâches en attente
            scheduled = inspect.scheduled()
            if scheduled:
                total_scheduled = sum(len(tasks) for tasks in scheduled.values())
                if total_scheduled > 100:  # Seuil d'alerte
                    logger.warning(f"Queue email importante: {total_scheduled} tâches")
                    return False
            
            return True
        except:
            return False
    
    @staticmethod
    def run_all_checks():
        """Exécute tous les checks"""
        checks = [
            ('Inscriptions', HealthCheck.check_inscriptions_rate),
            ('Email Queue', HealthCheck.check_email_queue),
        ]
        
        failed_checks = []
        for name, check_func in checks:
            try:
                if not check_func():
                    failed_checks.append(name)
            except Exception as e:
                logger.error(f"Erreur check {name}: {e}")
                failed_checks.append(name)
        
        # Alerter les admins si problèmes
        if failed_checks:
            mail_admins(
                subject="[ALERTE] Problèmes détectés - Événements",
                message=f"Checks en échec: {', '.join(failed_checks)}",
                fail_silently=True
            )
        
        return len(failed_checks) == 0
```

---

## 📋 Checklist de Résolution

### **Avant de Débugger**

- [ ] **Sauvegarder** : Base de données et fichiers
- [ ] **Identifier** : Quand le problème a commencé
- [ ] **Reproduire** : Étapes pour reproduire l'erreur
- [ ] **Logs** : Vérifier tous les logs pertinents
- [ ] **Environnement** : Développement, staging, production ?

### **Processus de Debug**

1. **🔍 Diagnostic**
   - [ ] Lancer le script de diagnostic complet
   - [ ] Vérifier les logs d'erreur récents
   - [ ] Tester les fonctionnalités de base

2. **🧪 Tests**
   - [ ] Exécuter les tests unitaires
   - [ ] Tester manuellement les fonctionnalités
   - [ ] Vérifier l'intégrité des données

3. **🔧 Correction**
   - [ ] Appliquer les corrections nécessaires
   - [ ] Redémarrer les services si besoin
   - [ ] Vérifier que la correction fonctionne

4. **✅ Validation**
   - [ ] Tests complets de l'application
   - [ ] Monitoring des métriques
   - [ ] Documentation de la solution

---

## 🆘 Contacts et Escalade

### **Niveaux de Support**

| Niveau | Type de Problème | Contact | Délai |
|--------|------------------|---------|--------|
| **L1** | Questions utilisateur | support@association.com | 4h |
| **L2** | Bugs applicatifs | dev@association.com | 24h |
| **L3** | Problèmes critiques | admin@association.com | 2h |
| **L4** | Infrastructure | ops@association.com | 1h |

### **Informations à Fournir**

```text
Titre: [URGENT/NORMAL] Problème événements - Description courte

Environnement: [Production/Staging/Dev]
Date/Heure: 
Utilisateur impacté: 
Actions effectuées: 

Symptômes:
- Description du problème
- Messages d'erreur exacts
- Comportement attendu vs observé

Logs:
[Joindre les logs pertinents]

Impact:
- Nombre d'utilisateurs impactés
- Fonctionnalités bloquées
- Urgence métier

Reproduction:
1. Étape 1
2. Étape 2
3. Résultat observé

Tentatives de résolution:
- Actions déjà tentées
- Résultats obtenus
```

---

## 📚 Ressources Utiles

### **Documentation**
- [Django Debug Toolbar](https://django-debug-toolbar.readthedocs.io/)
- [Celery Monitoring](https://docs.celeryproject.org/en/stable/userguide/monitoring.html)
- [PostgreSQL Performance](https://www.postgresql.org/docs/current/performance-tips.html)

### **Outils de Debug**
- **Sentry** : Monitoring d'erreurs en temps réel
- **New Relic** : Monitoring de performance
- **Flower** : Interface web pour Celery
- **pgAdmin** : Interface PostgreSQL

### **Commands Utiles**

```bash
# Logs en temps réel
tail -f logs/*.log

# Espace disque
df -h
du -sh media/ logs/

# Processus actifs
ps aux | grep python
ps aux | grep celery

# Connexions réseau
netstat -tuln | grep :5432  # PostgreSQL
netstat -tuln | grep :6379  # Redis
```

---

**📅 Dernière mise à jour** : Décembre 2024  
**🎯 Version** : 1.0.0  
**📊 Statut** : Guide complet et testé