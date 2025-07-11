# 🔗 Guide d'Intégration - Application Événements

## 📋 Vue d'ensemble

Ce guide détaille comment l'application événements s'intègre avec les autres modules du système et comment étendre ses fonctionnalités avec des systèmes externes.

## 🏗️ Architecture d'Intégration

### **Modules Connectés**
```
                    ┌─────────────────┐
                    │   ÉVÉNEMENTS   │
                    │   (Principal)   │
                    └─────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
┌───────▼────────┐ ┌────────▼────────┐ ┌────────▼────────┐
│    MEMBRES     │ │   COTISATIONS   │ │    ACCOUNTS     │
│  (Utilisateurs)│ │   (Financier)   │ │ (Authentification)│
└────────────────┘ └─────────────────┘ └─────────────────┘
        │                   │                   │
        └───────────────────┼───────────────────┘
                            │
                    ┌───────▼────────┐
                    │      CORE      │
                    │ (Base commune) │
                    └────────────────┘
```

## 🧑‍🤝‍🧑 Intégration Module Membres

### **Relations de Données**
```python
# apps/evenements/models.py
class InscriptionEvenement(BaseModel):
    membre = models.ForeignKey(
        'membres.Membre',
        on_delete=models.CASCADE,
        related_name='inscriptions_evenements'
    )
```

### **Tarification par Type de Membre**
```python
# Logique de calcul automatique des tarifs
def calculer_tarif_membre(self, membre):
    """Calcule le tarif selon le type de membre"""
    types_actifs = membre.get_types_actifs()
    
    # Priorité tarif étudiant
    if types_actifs.filter(libelle__icontains='étudiant').exists():
        return self.tarif_etudiant or self.tarif_membre
    
    # Priorité tarif salarié
    elif types_actifs.filter(libelle__icontains='salarié').exists():
        return self.tarif_salarie
    
    # Tarif membre standard
    return self.tarif_membre
```

### **Vérification d'Éligibilité**
```python
def peut_s_inscrire(self, membre):
    """Vérifie si un membre peut s'inscrire"""
    # Vérifications de base
    if not self.inscriptions_ouvertes:
        return False, "Les inscriptions sont fermées"
    
    # Vérification du statut membre
    if membre.deleted_at:
        return False, "Compte membre inactif"
    
    # Vérification cotisations si requises
    if self.type_evenement.necessite_cotisation_jour:
        if not membre.has_cotisation_valide():
            return False, "Cotisation non à jour"
    
    return True, "Inscription possible"
```

### **Historique et Statistiques**
```python
# Ajout automatique dans le profil membre
class Membre(BaseModel):
    def get_historique_evenements(self):
        """Retourne l'historique des événements du membre"""
        return self.inscriptions_evenements.select_related(
            'evenement'
        ).order_by('-date_inscription')
    
    def get_stats_participation(self):
        """Statistiques de participation"""
        inscriptions = self.inscriptions_evenements
        return {
            'total_inscriptions': inscriptions.count(),
            'confirmees': inscriptions.filter(statut='confirmee').count(),
            'participations': inscriptions.filter(statut='presente').count(),
            'taux_participation': self._calcul_taux_participation()
        }
```

### **Signaux d'Intégration**
```python
# apps/evenements/signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

@receiver(post_save, sender=InscriptionEvenement)
def update_membre_stats(sender, instance, created, **kwargs):
    """Met à jour les stats du membre après inscription"""
    if created:
        # Recalculer les statistiques du membre
        instance.membre.update_stats_evenements()

@receiver(post_delete, sender=InscriptionEvenement)
def cleanup_membre_stats(sender, instance, **kwargs):
    """Nettoie les stats après suppression inscription"""
    instance.membre.update_stats_evenements()
```

## 💰 Intégration Module Cotisations

### **Création Automatique de Cotisations**
```python
# apps/evenements/services.py
class CotisationService:
    @staticmethod
    def creer_cotisation_evenement(inscription):
        """Crée une cotisation pour un événement payant"""
        if not inscription.evenement.est_payant:
            return None
        
        from apps.cotisations.models import Cotisation
        
        # Générer référence unique
        reference = f"EVENT-{inscription.evenement.reference}-{inscription.id}"
        
        # Calculer échéance (2 jours avant événement)
        echeance = inscription.evenement.date_debut.date() - timedelta(days=2)
        
        cotisation = Cotisation.objects.create(
            membre=inscription.membre,
            montant=inscription.calculer_montant_total(),
            date_echeance=echeance,
            type_cotisation='evenement',
            reference=reference,
            description=f"Participation : {inscription.evenement.titre}",
            metadata={
                'inscription_id': inscription.id,
                'evenement_id': inscription.evenement.id,
                'type': 'inscription_evenement'
            }
        )
        
        # Lier l'inscription à la cotisation
        inscription.cotisation_associee = cotisation
        inscription.save()
        
        return cotisation
```

### **Synchronisation des Paiements**
```python
# Signal bidirectionnel
@receiver(post_save, sender='cotisations.Paiement')
def sync_paiement_inscription(sender, instance, created, **kwargs):
    """Synchronise les paiements avec les inscriptions"""
    if instance.cotisation.metadata.get('type') == 'inscription_evenement':
        inscription_id = instance.cotisation.metadata.get('inscription_id')
        
        try:
            inscription = InscriptionEvenement.objects.get(id=inscription_id)
            
            # Mettre à jour le montant payé
            total_paye = instance.cotisation.paiements.aggregate(
                total=Sum('montant')
            )['total'] or Decimal('0.00')
            
            inscription.montant_paye = total_paye
            inscription.mode_paiement = instance.mode_paiement
            inscription.reference_paiement = instance.reference_paiement
            inscription.save()
            
        except InscriptionEvenement.DoesNotExist:
            pass
```

### **Remboursements Automatiques**
```python
def gerer_remboursement_annulation(inscription):
    """Gère les remboursements en cas d'annulation"""
    if inscription.cotisation_associee and inscription.montant_paye > 0:
        
        # Calculer le montant remboursable selon les règles
        jours_avant = (inscription.evenement.date_debut.date() - timezone.now().date()).days
        
        if jours_avant >= 7:
            # Remboursement intégral
            montant_remboursement = inscription.montant_paye
            frais = Decimal('0.00')
        elif jours_avant >= 3:
            # Remboursement avec frais
            frais = inscription.montant_paye * Decimal('0.10')  # 10%
            montant_remboursement = inscription.montant_paye - frais
        else:
            # Pas de remboursement
            return False, "Délai de remboursement dépassé"
        
        # Créer le remboursement
        from apps.cotisations.models import Paiement
        
        Paiement.objects.create(
            cotisation=inscription.cotisation_associee,
            montant=-montant_remboursement,  # Montant négatif = remboursement
            date_paiement=timezone.now(),
            type_transaction='remboursement',
            reference_paiement=f"REMB-{inscription.id}",
            commentaire=f"Remboursement annulation - Frais: {frais}€"
        )
        
        return True, f"Remboursement de {montant_remboursement}€ effectué"
```

## 🔐 Intégration Module Accounts

### **Gestion des Permissions**
```python
# apps/evenements/permissions.py
from django.contrib.auth.decorators import user_passes_test

def est_organisateur_evenement(user, evenement):
    """Vérifie si l'user peut organiser l'événement"""
    if user.is_staff:
        return True
    
    if hasattr(user, 'membre'):
        # Vérifier les permissions selon le rôle
        return user.membre.peut_organiser_evenements()
    
    return False

def peut_valider_evenements(user):
    """Vérifie si l'user peut valider des événements"""
    return user.is_staff and user.has_perm('evenements.validate_evenement')
```

### **Rôles et Responsabilités**
```python
# Extension du modèle User via le profil
class MembreProfile:
    def peut_organiser_evenements(self):
        """Détermine si le membre peut créer des événements"""
        # Logique selon le type de membre
        return self.type_membre.peut_organiser or self.utilisateur.is_staff
    
    def peut_voir_evenements_prives(self):
        """Accès aux événements non publiés"""
        return self.utilisateur.is_staff or self.est_organisateur_actif()
```

### **Historique et Audit**
```python
# apps/evenements/models.py
class EvenementAudit(models.Model):
    """Audit trail pour les événements"""
    evenement = models.ForeignKey(Evenement, on_delete=models.CASCADE)
    action = models.CharField(max_length=50)
    utilisateur = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    details = models.JSONField(default=dict)
    adresse_ip = models.GenericIPAddressField(null=True)

# Signal automatique
@receiver(post_save, sender=Evenement)
def log_evenement_change(sender, instance, created, **kwargs):
    """Log automatique des changements"""
    action = 'created' if created else 'updated'
    
    # Récupérer l'utilisateur actuel depuis le middleware
    user = getattr(instance, '_current_user', None)
    
    EvenementAudit.objects.create(
        evenement=instance,
        action=action,
        utilisateur=user,
        details={
            'titre': instance.titre,
            'statut': instance.statut,
            'date_debut': instance.date_debut.isoformat()
        }
    )
```

## 📊 Intégration Dashboard Principal

### **Widgets pour le Dashboard**
```python
# apps/core/views.py - Extension du dashboard
class DashboardView(LoginRequiredMixin, TemplateView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Ajouter les données événements
        if 'apps.evenements' in settings.INSTALLED_APPS:
            context.update(self.get_evenements_data())
        
        return context
    
    def get_evenements_data(self):
        """Données événements pour le dashboard"""
        from apps.evenements.models import Evenement, InscriptionEvenement, ValidationEvenement
        
        user = self.request.user
        data = {}
        
        # Pour tous les utilisateurs connectés
        data.update({
            'evenements_total': Evenement.objects.publies().count(),
            'evenements_venir': Evenement.objects.publies().a_venir().count(),
        })
        
        # Pour les membres
        if hasattr(user, 'membre'):
            mes_inscriptions = InscriptionEvenement.objects.filter(
                membre=user.membre,
                statut__in=['confirmee', 'en_attente']
            ).count()
            data['mes_inscriptions'] = mes_inscriptions
        
        # Pour les organisateurs
        if user.is_staff or self.peut_organiser():
            mes_evenements = Evenement.objects.filter(organisateur=user)
            data.update({
                'mes_evenements_total': mes_evenements.count(),
                'mes_evenements_a_valider': mes_evenements.filter(
                    statut='en_attente_validation'
                ).count()
            })
        
        # Pour les validateurs
        if user.is_staff:
            data.update({
                'validations_en_attente': ValidationEvenement.objects.en_attente().count(),
                'validations_urgentes': ValidationEvenement.objects.urgentes().count()
            })
        
        return data
```

### **Templates de Dashboard**
```html
<!-- templates/core/dashboard.html - Widgets événements -->
{% if evenements_total > 0 %}
<div class="col-md-4">
    <div class="card mb-4 box-shadow">
        <div class="card-header bg-info text-white">
            <div class="d-flex justify-content-between align-items-center">
                <h4 class="my-0 font-weight-normal">Événements</h4>
                <i class="fas fa-calendar-alt fa-2x"></i>
            </div>
        </div>
        <div class="card-body">
            <h1 class="card-title">{{ evenements_total }}</h1>
            <ul class="list-unstyled mt-3 mb-4">
                <li><i class="fas fa-calendar-day me-2"></i> {{ evenements_venir }} à venir</li>
                {% if mes_inscriptions %}
                    <li><i class="fas fa-user-check me-2"></i> {{ mes_inscriptions }} mes inscriptions</li>
                {% endif %}
                {% if validations_en_attente %}
                    <li><i class="fas fa-hourglass-half me-2"></i> {{ validations_en_attente }} à valider</li>
                {% endif %}
            </ul>
            <a href="{% url 'evenements:liste' %}" class="btn btn-lg btn-block btn-outline-info w-100">
                Voir les événements
            </a>
        </div>
    </div>
</div>
{% endif %}
```

## 🔔 Intégration Système de Notifications

### **Service Centralisé**
```python
# apps/evenements/services.py
class NotificationService:
    def __init__(self):
        self.email_backend = self._get_email_backend()
        self.sms_backend = self._get_sms_backend()
    
    def envoyer_notification_inscription(self, inscription):
        """Notification d'inscription avec choix du canal"""
        membre = inscription.membre
        
        # Respecter les préférences du membre
        preferences = self._get_preferences_notification(membre)
        
        if preferences.get('email_inscriptions', True):
            self._send_email_inscription(inscription)
        
        if preferences.get('sms_inscriptions', False) and membre.telephone:
            self._send_sms_inscription(inscription)
    
    def _get_preferences_notification(self, membre):
        """Récupère les préférences de notification du membre"""
        # Intégration avec le système de préférences
        defaults = {
            'email_inscriptions': True,
            'email_rappels': True,
            'sms_urgents': False
        }
        
        if hasattr(membre, 'preferences_notifications'):
            defaults.update(membre.preferences_notifications.to_dict())
        
        return defaults
```

### **Templates d'Emails Contextuels**
```python
# Structure des templates
templates_evenements = {
    'inscription_confirmation': {
        'subject': 'Confirmation d\'inscription - {{ evenement.titre }}',
        'template': 'emails/evenements/inscription_confirmation.html',
        'context_processor': 'get_context_inscription'
    },
    'evenement_valide': {
        'subject': 'Votre événement a été approuvé',
        'template': 'emails/evenements/evenement_valide.html',
        'context_processor': 'get_context_validation'
    }
}

def get_context_inscription(inscription):
    """Contexte pour email d'inscription"""
    return {
        'inscription': inscription,
        'evenement': inscription.evenement,
        'membre': inscription.membre,
        'code_confirmation': inscription.code_confirmation,
        'lien_confirmation': inscription.get_lien_confirmation(),
        'date_limite': inscription.date_limite_confirmation,
        'montant_total': inscription.calculer_montant_total()
    }
```

## 🔗 Intégrations Externes

### **Calendriers Externes (Google, Outlook)**
```python
# apps/evenements/integrations/calendrier.py
class GoogleCalendarIntegration:
    def __init__(self, credentials):
        self.service = self._build_service(credentials)
    
    def exporter_evenement(self, evenement):
        """Exporte un événement vers Google Calendar"""
        event = {
            'summary': evenement.titre,
            'description': evenement.description,
            'location': f"{evenement.lieu}\n{evenement.adresse_complete}",
            'start': {
                'dateTime': evenement.date_debut.isoformat(),
                'timeZone': 'Europe/Paris',
            },
            'end': {
                'dateTime': evenement.date_fin.isoformat(),
                'timeZone': 'Europe/Paris',
            },
            'attendees': self._get_attendees(evenement)
        }
        
        return self.service.events().insert(
            calendarId='primary',
            body=event
        ).execute()
    
    def _get_attendees(self, evenement):
        """Liste des participants pour Google Calendar"""
        attendees = []
        
        for inscription in evenement.inscriptions.filter(statut='confirmee'):
            attendees.append({
                'email': inscription.membre.email,
                'displayName': f"{inscription.membre.prenom} {inscription.membre.nom}"
            })
        
        return attendees
```

### **Paiements en Ligne (Stripe)**
```python
# apps/evenements/integrations/paiement.py
import stripe

class StripePaymentIntegration:
    def __init__(self):
        stripe.api_key = settings.STRIPE_SECRET_KEY
    
    def creer_session_paiement(self, inscription):
        """Crée une session de paiement Stripe"""
        line_items = [{
            'price_data': {
                'currency': 'eur',
                'product_data': {
                    'name': inscription.evenement.titre,
                    'description': f"Inscription événement du {inscription.evenement.date_debut.strftime('%d/%m/%Y')}"
                },
                'unit_amount': int(inscription.calculer_montant_total() * 100),  # Centimes
            },
            'quantity': 1,
        }]
        
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=line_items,
            mode='payment',
            success_url=f"{settings.BASE_URL}/evenements/inscriptions/{inscription.id}/paiement-success/",
            cancel_url=f"{settings.BASE_URL}/evenements/inscriptions/{inscription.id}/",
            metadata={
                'inscription_id': inscription.id,
                'evenement_id': inscription.evenement.id
            }
        )
        
        return session
```

### **QR Codes pour Check-in**
```python
# apps/evenements/integrations/qrcode.py
import qrcode
from io import BytesIO

class QRCodeService:
    @staticmethod
    def generer_qr_inscription(inscription):
        """Génère un QR Code pour l'inscription"""
        # Données encodées
        data = {
            'type': 'inscription_evenement',
            'inscription_id': inscription.id,
            'code': inscription.code_confirmation,
            'evenement': inscription.evenement.reference
        }
        
        # Générer le QR Code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(json.dumps(data))
        qr.make(fit=True)
        
        # Convertir en image
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Sauvegarder en bytes
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        return buffer.getvalue()
    
    @staticmethod
    def verifier_qr_checkin(qr_data):
        """Vérifie un QR Code pour le check-in"""
        try:
            data = json.loads(qr_data)
            
            if data.get('type') != 'inscription_evenement':
                return False, "QR Code invalide"
            
            inscription = InscriptionEvenement.objects.get(
                id=data['inscription_id'],
                code_confirmation=data['code']
            )
            
            if inscription.statut != 'confirmee':
                return False, "Inscription non confirmée"
            
            # Marquer comme présent
            inscription.statut = 'presente'
            inscription.save()
            
            return True, f"Check-in réussi pour {inscription.membre.nom_complet}"
            
        except (json.JSONDecodeError, InscriptionEvenement.DoesNotExist):
            return False, "QR Code invalide ou expiré"
```

## 📱 API REST pour Applications Mobiles

### **Endpoints REST**
```python
# apps/evenements/api/views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

class EvenementViewSet(viewsets.ReadOnlyModelViewSet):
    """API REST pour les événements"""
    serializer_class = EvenementSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Evenement.objects.publies().avec_statistiques()
    
    @action(detail=True, methods=['post'])
    def s_inscrire(self, request, pk=None):
        """Inscription via API"""
        evenement = self.get_object()
        
        try:
            membre = request.user.membre
        except Membre.DoesNotExist:
            return Response(
                {'error': 'Utilisateur non membre'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Vérifier éligibilité
        peut_inscrire, message = evenement.peut_s_inscrire(membre)
        if not peut_inscrire:
            return Response(
                {'error': message}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Créer l'inscription
        inscription = InscriptionEvenement.objects.create(
            evenement=evenement,
            membre=membre,
            nombre_accompagnants=request.data.get('accompagnants', 0)
        )
        
        return Response({
            'inscription_id': inscription.id,
            'statut': inscription.statut,
            'code_confirmation': inscription.code_confirmation
        })
```

### **Serializers API**
```python
# apps/evenements/api/serializers.py
from rest_framework import serializers

class EvenementSerializer(serializers.ModelSerializer):
    """Serializer pour les événements"""
    places_disponibles = serializers.ReadOnlyField()
    est_complet = serializers.ReadOnlyField()
    peut_s_inscrire = serializers.SerializerMethodField()
    
    class Meta:
        model = Evenement
        fields = [
            'id', 'titre', 'description', 'date_debut', 'date_fin',
            'lieu', 'capacite_max', 'places_disponibles', 'est_complet',
            'est_payant', 'tarif_membre', 'peut_s_inscrire'
        ]
    
    def get_peut_s_inscrire(self, obj):
        """Vérifie si l'utilisateur peut s'inscrire"""
        request = self.context.get('request')
        if request and hasattr(request.user, 'membre'):
            peut, message = obj.peut_s_inscrire(request.user.membre)
            return {'possible': peut, 'message': message}
        return {'possible': False, 'message': 'Non connecté'}
```

## 🔧 Configuration des Intégrations

### **Settings d'Intégration**
```python
# settings.py
EVENEMENTS_CONFIG = {
    # Notifications
    'NOTIFICATIONS_ENABLED': True,
    'EMAIL_BACKEND': 'django.core.mail.backends.smtp.EmailBackend',
    'SMS_BACKEND': 'apps.evenements.backends.TwilioSMSBackend',
    
    # Intégrations externes
    'GOOGLE_CALENDAR_ENABLED': env.bool('GOOGLE_CALENDAR_ENABLED', False),
    'STRIPE_ENABLED': env.bool('STRIPE_ENABLED', False),
    'QR_CODE_ENABLED': True,
    
    # Règles métier
    'DELAI_CONFIRMATION_DEFAULT': 48,  # heures
    'REMBOURSEMENT_FRAIS_PERCENT': 10,  # %
    'VALIDATION_AUTOMATIQUE_TYPES': ['reunion', 'formation_interne'],
    
    # Performance
    'CACHE_TIMEOUT_STATS': 3600,  # 1 heure
    'PAGINATION_SIZE': 20,
}

# Celery pour tâches asynchrones
CELERY_BEAT_SCHEDULE.update({
    'evenements-rappels-confirmation': {
        'task': 'apps.evenements.tasks.envoyer_rappel_confirmation',
        'schedule': crontab(minute=0, hour='*/2'),  # Toutes les 2h
    },
    'evenements-nettoyer-expires': {
        'task': 'apps.evenements.tasks.nettoyer_inscriptions_expirees',
        'schedule': crontab(minute=0, hour=2),  # 2h du matin
    }
})
```

### **Variables d'Environnement**
```bash
# .env
# Configuration emails
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=noreply@association.com
EMAIL_HOST_PASSWORD=mot_de_passe_app

# Intégrations externes
GOOGLE_CALENDAR_ENABLED=True
GOOGLE_CALENDAR_CREDENTIALS_FILE=/path/to/credentials.json

STRIPE_ENABLED=True
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_SECRET_KEY=sk_test_...

# Redis pour Celery
REDIS_URL=redis://localhost:6379/0
```

---

**🔗 Guide d'intégration complet**  
**📱 Support API REST et mobile**  
**🔔 Notifications intelligentes**  
**💰 Intégration financière complète**