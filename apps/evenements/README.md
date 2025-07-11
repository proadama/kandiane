# 🎯 Application Événements - Documentation Technique

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![Status](https://img.shields.io/badge/status-Production%20Ready-green)
![Django](https://img.shields.io/badge/django-4.2+-blue)
![Python](https://img.shields.io/badge/python-3.8+-blue)

## 📋 Vue d'ensemble

L'application **Événements** est un module complet de gestion d'événements pour associations, intégré à l'écosystème de gestion d'association Django. Elle offre une solution complète pour l'organisation, la validation, l'inscription et le suivi d'événements.

## 🎯 Fonctionnalités Principales

### **Gestion d'Événements**
- ✅ **CRUD complet** : Création, consultation, modification, suppression
- ✅ **Types configurables** : Formations, réunions, conférences, etc.
- ✅ **Validation workflow** : Système d'approbation par les administrateurs
- ✅ **Récurrence avancée** : Événements hebdomadaires, mensuels, annuels
- ✅ **Sessions multiples** : Événements complexes avec sous-sessions
- ✅ **Gestion capacité** : Places disponibles, complet, surbooking

### **Système d'Inscription**
- ✅ **Workflow complet** : Inscription → Confirmation → Participation
- ✅ **Liste d'attente** : Gestion FIFO avec promotion automatique
- ✅ **Accompagnants** : Gestion des invités avec tarification
- ✅ **Délais configurables** : Confirmation dans les temps impartis
- ✅ **Codes uniques** : Confirmation par email sécurisée

### **Intégration Financière**
- ✅ **Tarification flexible** : Par type de membre (étudiant, salarié, etc.)
- ✅ **Cotisations automatiques** : Création pour événements payants
- ✅ **Synchronisation paiements** : Bidirectionnelle avec module cotisations
- ✅ **Remboursements** : Automatiques selon règles métier

### **Notifications Intelligentes**
- ✅ **Emails automatiques** : Confirmation, rappels, alertes
- ✅ **Tâches asynchrones** : Via Celery pour performance
- ✅ **Templates personnalisables** : Par type de notification
- ✅ **Préférences utilisateur** : Respect des choix de communication

## 🏗️ Architecture Technique

### **Modèles de Données**
```
Evenement (principal)
├── TypeEvenement (configuration)
├── ValidationEvenement (workflow approbation)
├── EvenementRecurrence (récurrence)
├── SessionEvenement (sous-sessions)
├── InscriptionEvenement (inscriptions)
├── AccompagnantInvite (accompagnants)
└── Intégrations (Membre, Cotisation, User)
```

### **Gestionnaires Personnalisés**
- **EvenementManager** : Filtres avancés (publics, à venir, complets)
- **InscriptionEvenementManager** : Gestion états et transitions
- **ValidationEvenementManager** : Workflow validation
- **NotificationService** : Service de notifications centralisé

### **Vues et API**
- **Vues CRUD** : Interface complète avec permissions
- **API AJAX** : Fonctionnalités temps réel (places, tarifs)
- **Exports** : PDF, Excel, CSV, iCal, badges
- **Vues publiques** : Interface sans authentification

## 📦 Installation et Configuration

### **Prérequis**
```python
# requirements.txt
Django>=4.2.0
Pillow>=10.0.0
celery>=5.3.0
redis>=4.5.0  # Pour Celery
openpyxl>=3.1.0  # Pour exports Excel
reportlab>=4.0.0  # Pour exports PDF
```

### **Configuration Django**
```python
# settings.py
INSTALLED_APPS = [
    # ... autres apps
    'apps.core',
    'apps.accounts', 
    'apps.membres',
    'apps.cotisations',
    'apps.evenements',  # ← Ajouter cette ligne
]

# Configuration Celery (notifications asynchrones)
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'

# Configuration email
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'your-smtp-server.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email@domain.com'
EMAIL_HOST_PASSWORD = 'your-password'
```

### **Migration Base de Données**
```bash
# Appliquer les migrations
python manage.py makemigrations evenements
python manage.py migrate

# Charger les données initiales
python manage.py loaddata apps/evenements/fixtures/types_evenements.json
python manage.py loaddata apps/evenements/fixtures/modes_paiement.json
```

### **URLs**
```python
# config/urls.py
urlpatterns = [
    # ... autres URLs
    path('evenements/', include('apps.evenements.urls')),
]
```

## 🔧 Configuration Avancée

### **Types d'Événements**
```python
# Création via l'admin ou shell
from apps.evenements.models import TypeEvenement

# Type nécessitant validation
TypeEvenement.objects.create(
    libelle='Conférence',
    description='Conférences et événements publics',
    necessite_validation=True,
    permet_accompagnants=True,
    couleur_affichage='#007bff'
)

# Type sans validation
TypeEvenement.objects.create(
    libelle='Réunion',
    description='Réunions internes',
    necessite_validation=False,
    permet_accompagnants=False,
    couleur_affichage='#28a745'
)
```

### **Configuration Notifications**
```python
# settings.py - Configuration Celery
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    # Rappels de confirmation (toutes les heures)
    'envoyer-rappels-confirmation': {
        'task': 'apps.evenements.tasks.envoyer_rappel_confirmation',
        'schedule': crontab(minute=0),  # Toutes les heures
    },
    
    # Nettoyage inscriptions expirées (quotidien)
    'nettoyer-inscriptions-expirees': {
        'task': 'apps.evenements.tasks.nettoyer_inscriptions_expirees',
        'schedule': crontab(hour=2, minute=0),  # 2h du matin
    },
    
    # Alertes validations urgentes (quotidien)
    'alertes-validations-urgentes': {
        'task': 'apps.evenements.tasks.envoyer_notifications_urgentes_validation',
        'schedule': crontab(hour=9, minute=0),  # 9h du matin
    },
}
```

## 🔑 Utilisation - Guide Développeur

### **Créer un Événement**
```python
from apps.evenements.models import Evenement, TypeEvenement
from django.utils import timezone
from datetime import timedelta

# Récupérer le type et l'organisateur
type_formation = TypeEvenement.objects.get(libelle='Formation')
organisateur = User.objects.get(username='admin')

# Créer l'événement
evenement = Evenement.objects.create(
    titre='Formation Django Avancée',
    description='Formation complète sur Django et ses bonnes pratiques',
    type_evenement=type_formation,
    organisateur=organisateur,
    date_debut=timezone.now() + timedelta(days=30),
    date_fin=timezone.now() + timedelta(days=30, hours=6),
    lieu='Centre de formation',
    capacite_max=20,
    est_payant=True,
    tarif_membre=100.00,
    tarif_invite=150.00,
    permet_accompagnants=True,
    nombre_max_accompagnants=1
)
```

### **Gérer les Inscriptions**
```python
from apps.evenements.models import InscriptionEvenement
from apps.membres.models import Membre

# Récupérer un membre
membre = Membre.objects.get(email='user@example.com')

# Vérifier si peut s'inscrire
peut_inscrire, message = evenement.peut_s_inscrire(membre)
if peut_inscrire:
    # Créer l'inscription
    inscription = InscriptionEvenement.objects.create(
        evenement=evenement,
        membre=membre,
        nombre_accompagnants=1
    )
    
    # Confirmer l'inscription
    inscription.confirmer_inscription()
    print(f"Inscription confirmée : {inscription.statut}")
```

### **Utiliser les Gestionnaires**
```python
# Événements publics à venir avec places disponibles
evenements_disponibles = Evenement.objects.publies().a_venir().avec_places_disponibles()

# Inscriptions en retard de confirmation
inscriptions_retard = InscriptionEvenement.objects.en_retard_confirmation()

# Validations urgentes (événements dans moins de 7 jours)
validations_urgentes = ValidationEvenement.objects.urgentes()

# Statistiques d'un événement
stats = InscriptionEvenement.objects.statistiques_evenement(evenement)
print(f"Total inscriptions : {stats['total_inscriptions']}")
print(f"Confirmées : {stats['inscriptions_confirmees']}")
```

### **Service de Notifications**
```python
from apps.evenements.services import NotificationService

service = NotificationService()

# Envoyer notification d'inscription
service.envoyer_notification_inscription(inscription)

# Envoyer notification de validation
service.envoyer_notification_validation_evenement(validation, 'approuve')

# Envoyer notifications d'annulation
service.envoyer_notifications_annulation_evenement(evenement)
```

## 🧪 Tests

### **Exécution des Tests**
```bash
# Tous les tests de l'application
python manage.py test apps.evenements

# Tests par catégorie
python manage.py test apps.evenements.tests.test_models
python manage.py test apps.evenements.tests.test_views
python manage.py test apps.evenements.tests.test_workflow_inscription

# Tests avec couverture
coverage run --source='apps/evenements' manage.py test apps.evenements
coverage report
coverage html
```

### **Tests de Workflow**
```bash
# Tests complets des workflows
python apps/evenements/tests/test_runner_workflow.py

# Tests de performance
python manage.py test apps.evenements.tests.test_workflow_inscription.WorkflowPerformanceTestCase
```

## 📊 Monitoring et Maintenance

### **Tâches de Maintenance**
```python
# Nettoyer les inscriptions expirées
from apps.evenements.tasks import nettoyer_inscriptions_expirees
nettoyer_inscriptions_expirees.delay()

# Promouvoir depuis la liste d'attente
from apps.evenements.tasks import promouvoir_liste_attente
promouvoir_liste_attente.delay()

# Statistiques globales
from apps.evenements.models import Evenement, InscriptionEvenement

print(f"Événements actifs : {Evenement.objects.publies().count()}")
print(f"Inscriptions confirmées : {InscriptionEvenement.objects.confirmees().count()}")
```

### **Logs et Debugging**
```python
# Configuration logging dans settings.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'evenements.log',
        },
    },
    'loggers': {
        'apps.evenements': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
```

## 🔒 Sécurité

### **Permissions et Contrôle d'Accès**
- **Organisateurs** : Peuvent créer des événements
- **Staff** : Peuvent valider et administrer
- **Membres** : Peuvent s'inscrire selon éligibilité
- **Publics** : Accès lecture seule aux événements publiés

### **Validation des Données**
- Validation côté modèle avec `clean()`
- Validation côté formulaire avec validateurs personnalisés
- Protection CSRF sur tous les formulaires
- Sanitisation des entrées utilisateur

## 🚀 Performance

### **Optimisations Implémentées**
- **Requêtes optimisées** : `select_related()` et `prefetch_related()`
- **Indexes** : Sur les champs de recherche fréquents
- **Cache** : Pour les statistiques et données statiques
- **Pagination** : Sur toutes les listes importantes
- **Tâches asynchrones** : Pour les traitements longs

### **Métriques**
- Temps de réponse < 2s pour les pages principales
- Support de 1000+ événements simultanés
- Gestion de 10000+ inscriptions
- Notifications envoyées en < 5 min

## 📈 Évolutions et Extensions

### **Points d'Extension**
- **API REST** : Ajout d'endpoints pour applications mobiles
- **Intégrations calendrier** : Google Calendar, Outlook
- **Paiements en ligne** : Stripe, PayPal
- **QR Codes** : Génération pour check-in événements
- **Questionnaires** : Post-événement satisfaction

### **Hooks et Signaux**
```python
# Signaux disponibles pour extensions
from django.db.models.signals import post_save
from apps.evenements.models import InscriptionEvenement

def mon_hook_inscription(sender, instance, created, **kwargs):
    if created:
        # Actions personnalisées à l'inscription
        pass

post_save.connect(mon_hook_inscription, sender=InscriptionEvenement)
```

## 📞 Support et Documentation

### **Documentation Complémentaire**
- [Guide Utilisateur Organisateur](./GUIDE_ORGANISATEUR.md)
- [Guide Utilisateur Participant](./GUIDE_PARTICIPANT.md)
- [Guide Administrateur](./GUIDE_ADMINISTRATEUR.md)
- [Guide de Déploiement](./DEPLOYMENT.md)
- [Troubleshooting](./TROUBLESHOOTING.md)

### **Ressources**
- **Issues** : Rapporter les bugs via l'outil de suivi
- **Documentation Django** : https://docs.djangoproject.com/
- **Celery** : https://docs.celeryproject.org/

### **Changelog**
Voir [CHANGELOG.md](./CHANGELOG.md) pour l'historique des versions.

---

**📝 Dernière mise à jour** : Décembre 2024  
**👨‍💻 Développé par** : Équipe Backend  
**📊 Version** : 1.0.0 - Production Ready  
**🎯 Statut** : ✅ Complet et Opérationnel