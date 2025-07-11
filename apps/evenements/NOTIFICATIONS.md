# 📧 Guide Système de Notifications - Application Événements

## 📋 Vue d'ensemble

Le système de notifications de l'application événements gère automatiquement toutes les communications avec les utilisateurs via emails, SMS et notifications in-app. Il est conçu pour être fiable, configurable et respectueux des préférences utilisateur.

## 🏗️ Architecture du Système

### **Composants Principaux**
```
┌─────────────────────────────────────────────────────────────┐
│                    SYSTÈME DE NOTIFICATIONS                 │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │  DÉCLENCHEURS   │  │   PROCESSEURS   │  │   CANAUX     │ │
│  │                 │  │                 │  │              │ │
│  │ • Signaux       │  │ • Templates     │  │ • Email      │ │
│  │ • Tâches Celery │  │ • Contexte      │  │ • SMS        │ │
│  │ • Actions users │  │ • Préférences   │  │ • In-App     │ │
│  │ • Cron Jobs     │  │ • Retry Logic   │  │ • Push       │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────▼─────────┐
                    │   AUDIT & LOGS    │
                    │ • Envois réussis  │
                    │ • Échecs & retry  │
                    │ • Métriques       │
                    └───────────────────┘
```

## 🎯 Types de Notifications

### **1. Notifications d'Inscription**
#### **Confirmation d'Inscription**
- **Déclencheur** : Création d'une nouvelle inscription
- **Destinataire** : Membre inscrit
- **Template** : `inscription_confirmation.html`
- **Données** : Code confirmation, détails événement, délai

```python
# Contexte du template
{
    'inscription': inscription,
    'evenement': evenement,
    'membre': membre,
    'code_confirmation': '12CHAR-CODE',
    'lien_confirmation': 'https://site.com/evenements/confirmer/CODE',
    'date_limite': datetime,
    'montant_total': Decimal,
    'accompagnants': QuerySet
}
```

#### **Rappel de Confirmation**
- **Déclencheur** : Tâche Celery (24h et 2h avant expiration)
- **Condition** : Statut 'en_attente' + dans le délai
- **Template** : `rappel_confirmation.html`

#### **Expiration d'Inscription**
- **Déclencheur** : Tâche de nettoyage quotidienne
- **Condition** : Date limite dépassée
- **Template** : `inscription_expiree.html`

### **2. Notifications de Liste d'Attente**
#### **Mise en Liste d'Attente**
- **Déclencheur** : Inscription sur événement complet
- **Template** : `liste_attente.html`

#### **Promotion depuis Liste d'Attente**
- **Déclencheur** : Libération de place
- **Template** : `promotion_liste_attente.html`
- **Urgence** : Délai de confirmation réduit

### **3. Notifications de Validation**
#### **Événement Soumis pour Validation**
- **Déclencheur** : Création événement nécessitant validation
- **Destinataire** : Équipe de validation
- **Template** : `evenement_a_valider.html`

#### **Événement Approuvé**
- **Déclencheur** : Validation approuvée
- **Destinataire** : Organisateur
- **Template** : `evenement_approuve.html`

#### **Événement Refusé**
- **Déclencheur** : Validation refusée
- **Destinataire** : Organisateur
- **Template** : `evenement_refuse.html`
- **Données** : Commentaires du validateur

#### **Modifications Demandées**
- **Déclencheur** : Demande de modifications
- **Template** : `modifications_demandees.html`
- **Données** : Liste des modifications requises

### **4. Notifications d'Événements**
#### **Annulation d'Événement**
- **Déclencheur** : Changement statut vers 'annule'
- **Destinataires** : Tous les inscrits
- **Template** : `evenement_annule.html`
- **Données** : Raison, remboursements

#### **Modification d'Événement**
- **Déclencheur** : Changements importants (date, lieu)
- **Destinataires** : Inscrits confirmés
- **Template** : `evenement_modifie.html`

#### **Rappel Avant Événement**
- **Déclencheur** : Tâche Celery (J-1, H-2)
- **Template** : `rappel_evenement.html`

### **5. Notifications d'Accompagnants**
#### **Invitation Accompagnant**
- **Déclencheur** : Ajout d'accompagnant avec email
- **Template** : `invitation_accompagnant.html`

#### **Confirmation Accompagnant**
- **Déclencheur** : Confirmation via lien
- **Template** : `accompagnant_confirme.html`

## 🔧 Service de Notifications

### **NotificationService Principal**
```python
# apps/evenements/services.py
class NotificationService:
    """Service centralisé de notifications"""
    
    def __init__(self):
        self.email_backend = get_connection()
        self.logger = logging.getLogger('apps.evenements.notifications')
    
    def envoyer_notification_inscription(self, inscription):
        """Notification d'inscription avec confirmation"""
        try:
            # Vérifier les préférences du membre
            if not self._peut_envoyer_notification(inscription.membre, 'inscription'):
                return False
            
            # Préparer le contexte
            context = self._get_context_inscription(inscription)
            
            # Envoyer l'email
            resultat = self._send_email(
                template_name='inscription_confirmation',
                to_email=inscription.membre.email,
                context=context,
                inscription=inscription
            )
            
            self._log_notification(inscription, 'inscription_confirmation', resultat)
            return resultat
            
        except Exception as e:
            self.logger.error(f"Erreur notification inscription {inscription.id}: {e}")
            return False
    
    def envoyer_rappel_confirmation(self, inscription):
        """Rappel de confirmation d'inscription"""
        # Vérifier si pas déjà confirmée
        if inscription.statut != 'en_attente':
            return False
        
        # Calculer urgence
        heures_restantes = (inscription.date_limite_confirmation - timezone.now()).total_seconds() / 3600
        
        context = self._get_context_inscription(inscription)
        context.update({
            'est_urgent': heures_restantes <= 6,
            'heures_restantes': int(heures_restantes),
            'est_dernier_rappel': heures_restantes <= 2
        })
        
        return self._send_email(
            template_name='rappel_confirmation',
            to_email=inscription.membre.email,
            context=context,
            priority='high' if context['est_urgent'] else 'normal'
        )
    
    def envoyer_notification_promotion(self, inscription):
        """Notification de promotion depuis liste d'attente"""
        context = self._get_context_inscription(inscription)
        context.update({
            'ancien_statut': 'liste_attente',
            'nouveau_statut': 'en_attente',
            'delai_confirmation_reduit': True
        })
        
        return self._send_email(
            template_name='promotion_liste_attente',
            to_email=inscription.membre.email,
            context=context,
            priority='high'  # Urgent car délai réduit
        )
```

### **Système de Templates**
```python
class TemplateManager:
    """Gestionnaire de templates de notifications"""
    
    TEMPLATES_CONFIG = {
        'inscription_confirmation': {
            'subject': '✅ Confirmation d\'inscription - {{ evenement.titre }}',
            'template_html': 'emails/evenements/inscription_confirmation.html',
            'template_text': 'emails/evenements/inscription_confirmation.txt',
            'from_email': settings.DEFAULT_FROM_EMAIL,
            'reply_to': None,
            'attachments': []
        },
        'rappel_confirmation': {
            'subject': '⏰ {{ "URGENT - " if est_urgent }}Confirmez votre inscription',
            'template_html': 'emails/evenements/rappel_confirmation.html',
            'priority': 'high'
        },
        'evenement_annule': {
            'subject': '❌ Annulation - {{ evenement.titre }}',
            'template_html': 'emails/evenements/evenement_annule.html',
            'priority': 'high'
        }
    }
    
    def render_template(self, template_name, context):
        """Rendu d'un template avec contexte"""
        config = self.TEMPLATES_CONFIG.get(template_name)
        if not config:
            raise ValueError(f"Template {template_name} non trouvé")
        
        # Rendu du sujet
        subject_template = Template(config['subject'])
        subject = subject_template.render(Context(context))
        
        # Rendu du corps HTML
        html_content = render_to_string(config['template_html'], context)
        
        # Rendu du corps texte (optionnel)
        text_content = None
        if 'template_text' in config:
            text_content = render_to_string(config['template_text'], context)
        
        return {
            'subject': subject,
            'html_content': html_content,
            'text_content': text_content,
            'config': config
        }
```

## 🕐 Tâches Automatisées (Celery)

### **Configuration des Tâches**
```python
# apps/evenements/tasks.py
from celery import shared_task
from django.utils import timezone
from datetime import timedelta

@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def envoyer_rappel_confirmation(self):
    """Envoie les rappels de confirmation"""
    try:
        service = NotificationService()
        
        # Rappels 24h avant expiration
        seuil_24h = timezone.now() + timedelta(hours=24)
        inscriptions_24h = InscriptionEvenement.objects.filter(
            statut='en_attente',
            date_limite_confirmation__lte=seuil_24h,
            date_limite_confirmation__gt=timezone.now(),
            rappel_24h_envoye=False
        )
        
        count_24h = 0
        for inscription in inscriptions_24h:
            if service.envoyer_rappel_confirmation(inscription):
                inscription.rappel_24h_envoye = True
                inscription.save()
                count_24h += 1
        
        # Rappels 2h avant expiration (urgents)
        seuil_2h = timezone.now() + timedelta(hours=2)
        inscriptions_2h = InscriptionEvenement.objects.filter(
            statut='en_attente',
            date_limite_confirmation__lte=seuil_2h,
            date_limite_confirmation__gt=timezone.now(),
            rappel_2h_envoye=False
        )
        
        count_2h = 0
        for inscription in inscriptions_2h:
            if service.envoyer_rappel_confirmation(inscription):
                inscription.rappel_2h_envoye = True
                inscription.save()
                count_2h += 1
        
        logger.info(f"Rappels envoyés: {count_24h} (24h), {count_2h} (2h)")
        return f"Rappels: {count_24h + count_2h} envoyés"
        
    except Exception as exc:
        logger.error(f"Erreur rappels confirmation: {exc}")
        # Retry avec backoff exponentiel
        raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))

@shared_task
def nettoyer_inscriptions_expirees():
    """Nettoie les inscriptions expirées et notifie"""
    service = NotificationService()
    
    # Trouver les inscriptions expirées
    inscriptions_expirees = InscriptionEvenement.objects.filter(
        statut='en_attente',
        date_limite_confirmation__lt=timezone.now()
    )
    
    count = 0
    for inscription in inscriptions_expirees:
        # Envoyer notification d'expiration
        service.envoyer_notification_expiration(inscription)
        
        # Marquer comme expirée
        inscription.statut = 'expiree'
        inscription.save()
        
        # Promouvoir depuis la liste d'attente
        inscription.evenement.promouvoir_liste_attente()
        count += 1
    
    logger.info(f"Inscriptions expirées nettoyées: {count}")
    return count

@shared_task
def envoyer_notifications_urgentes_validation():
    """Notifie les validateurs d'événements urgents"""
    service = NotificationService()
    
    # Événements nécessitant validation urgente (< 7 jours)
    validations_urgentes = ValidationEvenement.objects.urgentes(jours=7)
    
    if validations_urgentes.exists():
        # Grouper par validateur ou envoyer à tous les staff
        validateurs = User.objects.filter(is_staff=True, is_active=True)
        
        for validateur in validateurs:
            service.envoyer_notification_validations_urgentes(
                validateur, validations_urgentes
            )
    
    return validations_urgentes.count()

@shared_task
def envoyer_rappels_evenement():
    """Envoie les rappels avant événements"""
    service = NotificationService()
    
    # Événements demain
    demain = timezone.now() + timedelta(days=1)
    evenements_demain = Evenement.objects.filter(
        date_debut__date=demain.date(),
        statut='publie'
    )
    
    count = 0
    for evenement in evenements_demain:
        inscriptions = evenement.inscriptions.filter(statut='confirmee')
        for inscription in inscriptions:
            if service.envoyer_rappel_evenement(inscription):
                count += 1
    
    return count
```

### **Planification Celery**
```python
# settings.py
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    # Rappels de confirmation (toutes les heures)
    'evenements-rappels-confirmation': {
        'task': 'apps.evenements.tasks.envoyer_rappel_confirmation',
        'schedule': crontab(minute=0),
    },
    
    # Nettoyage inscriptions expirées (quotidien à 2h)
    'evenements-nettoyer-expires': {
        'task': 'apps.evenements.tasks.nettoyer_inscriptions_expirees',
        'schedule': crontab(hour=2, minute=0),
    },
    
    # Validations urgentes (quotidien à 9h)
    'evenements-validations-urgentes': {
        'task': 'apps.evenements.tasks.envoyer_notifications_urgentes_validation',
        'schedule': crontab(hour=9, minute=0),
    },
    
    # Rappels événements (quotidien à 18h)
    'evenements-rappels-evenement': {
        'task': 'apps.evenements.tasks.envoyer_rappels_evenement',
        'schedule': crontab(hour=18, minute=0),
    },
    
    # Promotion liste d'attente (toutes les 30 min)
    'evenements-promouvoir-liste-attente': {
        'task': 'apps.evenements.tasks.promouvoir_liste_attente',
        'schedule': crontab(minute='*/30'),
    }
}
```

## 📨 Templates d'Emails

### **Structure des Templates**
```
templates/emails/evenements/
├── base_email.html                 # Template de base
├── inscription_confirmation.html   # Confirmation d'inscription
├── rappel_confirmation.html       # Rappels de confirmation
├── inscription_expiree.html       # Inscription expirée
├── liste_attente.html             # Mise en liste d'attente
├── promotion_liste_attente.html   # Promotion liste d'attente
├── evenement_valide.html          # Événement approuvé
├── evenement_refuse.html          # Événement refusé
├── evenement_annule.html          # Événement annulé
├── evenement_modifie.html         # Événement modifié
├── rappel_evenement.html          # Rappel avant événement
└── accompagnant_invitation.html   # Invitation accompagnant
```

### **Template de Base**
```html
<!-- templates/emails/evenements/base_email.html -->
{% load static %}
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Notification - {{ evenement.titre }}{% endblock %}</title>
    <style>
        body { 
            font-family: Arial, sans-serif; 
            line-height: 1.6; 
            color: #333; 
            margin: 0; 
            padding: 0; 
        }
        .container { 
            max-width: 600px; 
            margin: 0 auto; 
            padding: 20px; 
        }
        .header { 
            background: #007bff; 
            color: white; 
            padding: 20px; 
            text-align: center; 
        }
        .content { 
            background: #f8f9fa; 
            padding: 30px; 
        }
        .btn { 
            display: inline-block; 
            padding: 12px 24px; 
            background: #28a745; 
            color: white; 
            text-decoration: none; 
            border-radius: 5px; 
            margin: 15px 0; 
        }
        .btn.urgent { background: #dc3545; }
        .footer { 
            background: #6c757d; 
            color: white; 
            padding: 15px; 
            text-align: center; 
            font-size: 12px; 
        }
        .details-box { 
            background: white; 
            border: 1px solid #dee2e6; 
            border-radius: 5px; 
            padding: 20px; 
            margin: 20px 0; 
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{% block header_title %}🎯 Association{% endblock %}</h1>
            <p>{% block header_subtitle %}Gestion d'Événements{% endblock %}</p>
        </div>
        
        <div class="content">
            {% block content %}{% endblock %}
        </div>
        
        <div class="footer">
            {% block footer %}
            <p>Cet email a été envoyé automatiquement. Ne pas répondre.</p>
            <p>© {{ "now"|date:"Y" }} Association - Tous droits réservés</p>
            {% endblock %}
        </div>
    </div>
</body>
</html>
```

### **Template Confirmation d'Inscription**
```html
<!-- templates/emails/evenements/inscription_confirmation.html -->
{% extends "emails/evenements/base_email.html" %}

{% block title %}Confirmation d'inscription - {{ evenement.titre }}{% endblock %}

{% block header_title %}✅ Inscription Enregistrée{% endblock %}
{% block header_subtitle %}{{ evenement.titre }}{% endblock %}

{% block content %}
<h2>Bonjour {{ membre.prenom }},</h2>

<p>Votre inscription à l'événement <strong>{{ evenement.titre }}</strong> a été enregistrée avec succès !</p>

<div class="details-box">
    <h3>📅 Détails de l'événement</h3>
    <ul>
        <li><strong>Date :</strong> {{ evenement.date_debut|date:"l d F Y à H:i" }}</li>
        {% if evenement.date_fin %}
        <li><strong>Fin :</strong> {{ evenement.date_fin|date:"l d F Y à H:i" }}</li>
        {% endif %}
        <li><strong>Lieu :</strong> {{ evenement.lieu }}</li>
        {% if evenement.adresse_complete %}
        <li><strong>Adresse :</strong> {{ evenement.adresse_complete }}</li>
        {% endif %}
        <li><strong>Organisateur :</strong> {{ evenement.organisateur.get_full_name }}</li>
    </ul>
</div>

<div class="details-box">
    <h3>👤 Votre inscription</h3>
    <ul>
        <li><strong>Statut :</strong> 
            {% if inscription.statut == 'en_attente' %}
                ⏳ En attente de confirmation
            {% elif inscription.statut == 'liste_attente' %}
                📋 Liste d'attente
            {% endif %}
        </li>
        {% if inscription.nombre_accompagnants > 0 %}
        <li><strong>Accompagnants :</strong> {{ inscription.nombre_accompagnants }}</li>
        {% endif %}
        {% if montant_total > 0 %}
        <li><strong>Montant total :</strong> {{ montant_total }}€</li>
        {% endif %}
        <li><strong>Référence :</strong> {{ inscription.code_confirmation }}</li>
    </ul>
</div>

{% if inscription.statut == 'en_attente' %}
<div style="text-align: center; margin: 30px 0;">
    <h3>⚠️ Action Requise</h3>
    <p>Vous devez <strong>confirmer votre inscription</strong> avant le :</p>
    <p style="font-size: 18px; color: #dc3545; font-weight: bold;">
        {{ inscription.date_limite_confirmation|date:"l d F Y à H:i" }}
    </p>
    
    <a href="{{ lien_confirmation }}" class="btn" style="font-size: 16px;">
        🔗 Confirmer mon inscription
    </a>
    
    <p style="font-size: 12px; color: #6c757d;">
        Vous pouvez aussi utiliser le code : <strong>{{ inscription.code_confirmation }}</strong>
    </p>
</div>
{% elif inscription.statut == 'liste_attente' %}
<div style="text-align: center; margin: 30px 0;">
    <h3>📋 Liste d'Attente</h3>
    <p>L'événement est actuellement complet. Vous avez été placé(e) en liste d'attente.</p>
    <p>Nous vous notifierons dès qu'une place se libère !</p>
</div>
{% endif %}

{% if evenement.instructions_particulieres %}
<div class="details-box">
    <h3>📝 Instructions Particulières</h3>
    <p>{{ evenement.instructions_particulieres|linebreaks }}</p>
</div>
{% endif %}

<p>À bientôt,<br>
L'équipe d'organisation</p>
{% endblock %}
```

## 🔔 Préférences Utilisateur

### **Modèle de Préférences**
```python
# Extension du modèle Membre
class PreferencesNotifications(models.Model):
    """Préférences de notifications d'un membre"""
    membre = models.OneToOneField(
        'membres.Membre',
        on_delete=models.CASCADE,
        related_name='preferences_notifications'
    )
    
    # Notifications par email
    email_inscriptions = models.BooleanField(default=True)
    email_confirmations = models.BooleanField(default=True)
    email_rappels = models.BooleanField(default=True)
    email_validations = models.BooleanField(default=True)
    email_modifications = models.BooleanField(default=True)
    email_annulations = models.BooleanField(default=True)
    
    # Notifications SMS
    sms_urgents = models.BooleanField(default=False)
    sms_rappels = models.BooleanField(default=False)
    
    # Notifications in-app
    app_toutes = models.BooleanField(default=True)
    
    # Fréquence des rappels
    rappels_frequence = models.CharField(
        max_length=20,
        choices=[
            ('standard', 'Standard (24h et 2h)'),
            ('reduit', 'Réduit (2h seulement)'),
            ('aucun', 'Aucun rappel')
        ],
        default='standard'
    )
    
    class Meta:
        db_table = 'preferences_notifications'
        verbose_name = "Préférences de notifications"
```

### **Vérification des Préférences**
```python
def _peut_envoyer_notification(self, membre, type_notification):
    """Vérifie si on peut envoyer une notification selon les préférences"""
    try:
        prefs = membre.preferences_notifications
    except PreferencesNotifications.DoesNotExist:
        # Créer des préférences par défaut
        prefs = PreferencesNotifications.objects.create(membre=membre)
    
    # Mapping type -> préférence
    mapping = {
        'inscription': prefs.email_inscriptions,
        'confirmation': prefs.email_confirmations,
        'rappel': prefs.email_rappels,
        'validation': prefs.email_validations,
        'modification': prefs.email_modifications,
        'annulation': prefs.email_annulations
    }
    
    return mapping.get(type_notification, True)
```

## 📊 Monitoring et Métriques

### **Logs des Notifications**
```python
class NotificationLog(models.Model):
    """Log des notifications envoyées"""
    inscription = models.ForeignKey(
        InscriptionEvenement,
        on_delete=models.CASCADE,
        null=True, blank=True
    )
    evenement = models.ForeignKey(
        Evenement,
        on_delete=models.CASCADE,
        null=True, blank=True
    )
    destinataire = models.EmailField()
    type_notification = models.CharField(max_length=50)
    canal = models.CharField(
        max_length=20,
        choices=[('email', 'Email'), ('sms', 'SMS'), ('app', 'In-App')]
    )
    statut = models.CharField(
        max_length=20,
        choices=[
            ('envoye', 'Envoyé'),
            ('echec', 'Échec'),
            ('retry', 'Nouvelle tentative'),
            ('abandonne', 'Abandonné')
        ]
    )
    date_envoi = models.DateTimeField(auto_now_add=True)
    message_erreur = models.TextField(blank=True)
    tentatives = models.PositiveIntegerField(default=1)
    
    class Meta:
        db_table = 'notifications_logs'
        indexes = [
            models.Index(fields=['type_notification', 'statut']),
            models.Index(fields=['date_envoi']),
        ]
```

### **Métriques Dashboard**
```python
def get_stats_notifications():
    """Statistiques des notifications pour dashboard admin"""
    from django.utils import timezone
    from datetime import timedelta
    
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    
    stats = NotificationLog.objects.filter(
        date_envoi__date__gte=week_ago
    ).aggregate(
        total_envoyes=Count('id'),
        total_reussites=Count('id', filter=Q(statut='envoye')),
        total_echecs=Count('id', filter=Q(statut='echec')),
        total_abandonne=Count('id', filter=Q(statut='abandonne'))
    )
    
    stats['taux_succes'] = (
        stats['total_reussites'] / stats['total_envoyes'] * 100 
        if stats['total_envoyes'] > 0 else 0
    )
    
    return stats
```

## 🛠️ Configuration et Déploiement

### **Variables d'Environnement**
```bash
# Configuration email
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=noreply@association.com
EMAIL_HOST_PASSWORD=app_password_gmail

# Configuration SMS (Twilio)
TWILIO_ACCOUNT_SID=AC123...
TWILIO_AUTH_TOKEN=abc123...
TWILIO_PHONE_NUMBER=+33123456789

# Configuration Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Configuration notifications
NOTIFICATIONS_DEFAULT_FROM_EMAIL=noreply@association.com
NOTIFICATIONS_RETRY_MAX=3
NOTIFICATIONS_RETRY_DELAY=300
```

### **Tests des Notifications**
```python
# Commande de test
python manage.py test apps.evenements.tests.test_workflow_notifications

# Test manuel d'envoi
python manage.py shell
>>> from apps.evenements.services import NotificationService
>>> from apps.evenements.models import InscriptionEvenement
>>> service = NotificationService()
>>> inscription = InscriptionEvenement.objects.first()
>>> service.envoyer_notification_inscription(inscription)
```

## 🔧 Dépannage

### **Problèmes Fréquents**
1. **Emails non reçus**
   - Vérifier configuration SMTP
   - Contrôler logs Django et Celery
   - Vérifier spam/courrier indésirable

2. **Tâches Celery non exécutées**
   - Vérifier Redis/broker actif
   - Contrôler celery worker et beat
   - Vérifier timezone configuration

3. **Templates non trouvés**
   - Vérifier TEMPLATES_DIRS dans settings
   - Contrôler noms de fichiers et chemins

### **Commandes de Debug**
```bash
# Statut Celery
celery -A config inspect active
celery -A config inspect scheduled

# Logs en temps réel
tail -f logs/evenements_notifications.log

# Purger la queue
celery -A config purge

# Test des templates
python manage.py shell
>>> from django.template.loader import render_to_string
>>> render_to_string('emails/evenements/inscription_confirmation.html', context)
```

---

**📧 Système de notifications complet et professionnel**  
**🔄 Automatisation Celery pour fiabilité**  
**📊 Monitoring et métriques intégrés**  
**⚙️ Configuration flexible et extensible**