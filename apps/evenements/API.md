# 🔌 API et Vues - Application Événements

## 📋 Vue d'ensemble

Cette documentation détaille toutes les vues, endpoints et APIs disponibles dans l'application événements, incluant les paramètres, permissions et exemples d'utilisation.

## 🏠 URLs et Routage

### **Structure des URLs**
```python
# apps/evenements/urls.py
urlpatterns = [
    path('', DashboardEvenementView.as_view(), name='dashboard'),
    path('evenements/', include(evenements_patterns)),
    path('inscriptions/', include(inscriptions_patterns)),
    path('validation/', include(validation_patterns)),
    path('types/', include(types_patterns)),
    path('export/', include(export_patterns)),
    path('ajax/', include(ajax_patterns)),
    path('public/', include(public_patterns)),
]
```

## 🎯 Vues Principales

### **Dashboard**
```
GET /evenements/
```
**Vue :** `DashboardEvenementView`  
**Permission :** Connecté  
**Description :** Tableau de bord principal avec statistiques

**Contexte retourné :**
```python
{
    'total_evenements': int,
    'evenements_publies': int,
    'evenements_a_valider': int,
    'inscriptions_en_attente': int,
    'prochains_evenements': QuerySet,
    'mes_prochaines_inscriptions': QuerySet,
    'organisateur_stats': dict
}
```

## 📅 Gestion des Événements

### **Liste des Événements**
```
GET /evenements/evenements/
```
**Vue :** `EvenementListView`  
**Permission :** Connecté  
**Pagination :** 20 par page

**Paramètres de filtrage :**
- `recherche` : Recherche textuelle
- `type_evenement` : ID du type
- `statut` : publie, brouillon, annule
- `lieu` : Lieu ou adresse
- `organisateur` : ID de l'organisateur
- `places_disponibles` : boolean
- `inscriptions_ouvertes` : boolean
- `periode` : aujourd_hui, cette_semaine, ce_mois
- `date_debut` : YYYY-MM-DD
- `date_fin` : YYYY-MM-DD

**Exemple :**
```
GET /evenements/evenements/?type_evenement=1&places_disponibles=true&periode=prochains_30_jours
```

### **Détail d'un Événement**
```
GET /evenements/evenements/<int:pk>/
```
**Vue :** `EvenementDetailView`  
**Permission :** Connecté (publics si publié)

**Contexte spécial :**
```python
{
    'evenement': Evenement,
    'inscriptions_confirmees': QuerySet,
    'inscriptions_en_attente': QuerySet,
    'liste_attente': QuerySet,
    'sessions': QuerySet,
    'peut_s_inscrire': boolean,
    'message_inscription': str,
    'inscription_existante': InscriptionEvenement|None,
    'peut_modifier': boolean
}
```

### **Création d'Événement**
```
GET/POST /evenements/evenements/nouveau/
```
**Vue :** `EvenementCreateView`  
**Permission :** Staff ou organisateur

**Champs du formulaire :**
```python
{
    'titre': str,
    'description': text,
    'type_evenement': ForeignKey,
    'date_debut': datetime,
    'date_fin': datetime,
    'lieu': str,
    'capacite_max': int,
    'est_payant': boolean,
    'tarif_membre': decimal,
    'tarif_salarie': decimal,
    'tarif_invite': decimal,
    'permet_accompagnants': boolean,
    'nombre_max_accompagnants': int
}
```

### **Modification d'Événement**
```
GET/POST /evenements/evenements/<int:pk>/modifier/
```
**Vue :** `EvenementUpdateView`  
**Permission :** Staff ou organisateur propriétaire

### **Suppression d'Événement**
```
GET/POST /evenements/evenements/<int:pk>/supprimer/
```
**Vue :** `EvenementDeleteView`  
**Permission :** Staff

**Logique :** Suppression logique avec vérification des inscriptions

## 📝 Gestion des Inscriptions

### **Inscription à un Événement**
```
GET/POST /evenements/inscriptions/evenements/<int:evenement_pk>/inscription/
```
**Vue :** `InscriptionCreateView`  
**Permission :** Membre connecté

**Validation automatique :**
- Vérification éligibilité
- Contrôle places disponibles
- Validation accompagnants
- Calcul tarifs automatique

### **Détail d'une Inscription**
```
GET /evenements/inscriptions/<int:pk>/
```
**Vue :** `InscriptionDetailView`  
**Permission :** Propriétaire ou Staff

**Contexte :**
```python
{
    'inscription': InscriptionEvenement,
    'accompagnants': QuerySet,
    'montant_total': Decimal,
    'montant_restant': Decimal,
    'peut_confirmer': boolean,
    'peut_annuler': boolean
}
```

### **Confirmation d'Inscription**
```
POST /evenements/inscriptions/<int:pk>/confirmer/
```
**Vue :** `ConfirmerInscriptionView`  
**Permission :** Propriétaire ou Staff

### **Confirmation par Email (Public)**
```
GET/POST /evenements/inscriptions/confirmer/<str:code>/
```
**Vue :** `ConfirmerInscriptionEmailView`  
**Permission :** Public (avec code valide)

**Paramètres :**
- `code` : Code de confirmation unique (12 caractères)

### **Annulation d'Inscription**
```
POST /evenements/inscriptions/<int:pk>/annuler/
```
**Vue :** `AnnulerInscriptionView`  
**Permission :** Propriétaire ou Staff

**Paramètres POST :**
```python
{
    'raison': str  # Raison de l'annulation
}
```

## ✅ Système de Validation

### **Liste des Validations**
```
GET /evenements/validation/
```
**Vue :** `ValidationListView`  
**Permission :** Staff

**Contexte :**
```python
{
    'validations': QuerySet,
    'validations_urgentes': QuerySet  # Événements < 7 jours
}
```

### **Détail d'une Validation**
```
GET /evenements/validation/<int:pk>/
```
**Vue :** `ValidationDetailView`  
**Permission :** Staff

### **Approuver un Événement**
```
POST /evenements/validation/<int:pk>/approuver/
```
**Vue :** `ApprouverEvenementView`  
**Permission :** Staff

**Paramètres POST :**
```python
{
    'commentaire': str  # Commentaire optionnel
}
```

### **Refuser un Événement**
```
POST /evenements/validation/<int:pk>/refuser/
```
**Vue :** `RefuserEvenementView`  
**Permission :** Staff

**Paramètres POST :**
```python
{
    'commentaire': str  # Commentaire obligatoire
}
```

## 🏷️ Gestion des Types

### **Liste des Types d'Événements**
```
GET /evenements/types/
```
**Vue :** `TypeEvenementListView`  
**Permission :** Staff

### **Création de Type**
```
GET/POST /evenements/types/nouveau/
```
**Vue :** `TypeEvenementCreateView`  
**Permission :** Staff

**Champs :**
```python
{
    'libelle': str,
    'description': text,
    'couleur_affichage': str,  # Code couleur hex
    'necessite_validation': boolean,
    'permet_accompagnants': boolean,
    'ordre_affichage': int
}
```

## 📊 Exports et Rapports

### **Export Événements**
```
GET /evenements/export/evenements/?format=csv|excel|pdf
```
**Vue :** `ExportEvenementsView`  
**Permission :** Staff

**Paramètres :**
```python
{
    'format': 'csv|excel|pdf',
    'date_debut': 'YYYY-MM-DD',
    'date_fin': 'YYYY-MM-DD',
    'inclure_inscriptions': boolean,
    'inclure_accompagnants': boolean
}
```

### **Export Inscrits d'un Événement**
```
GET /evenements/export/evenements/<int:evenement_pk>/inscriptions/?format=csv|excel|pdf
```
**Vue :** `ExportInscritsView`  
**Permission :** Staff ou organisateur

### **Export Badges**
```
GET /evenements/export/evenements/<int:evenement_pk>/badges/
```
**Vue :** `ExportBadgesView`  
**Permission :** Staff ou organisateur  
**Format :** PDF avec badges 4 par page

### **Export Calendrier iCal**
```
GET /evenements/export/calendrier.ics
```
**Vue :** `ExportCalendrierView`  
**Permission :** Connecté  
**Format :** Fichier .ics pour calendriers

## ⚡ API AJAX

### **Vérifier Places Disponibles**
```
GET /evenements/ajax/evenements/<int:pk>/places-disponibles/
```
**Vue :** `CheckPlacesDisponiblesView`  
**Permission :** Connecté

**Réponse JSON :**
```json
{
    "places_disponibles": 15,
    "est_complet": false,
    "taux_occupation": 75.0
}
```

### **Calculer Tarif pour un Membre**
```
GET /evenements/ajax/evenements/<int:pk>/calculer-tarif/
```
**Vue :** `CalculerTarifView`  
**Permission :** Connecté

**Réponse JSON :**
```json
{
    "success": true,
    "tarif": 50.00,
    "tarif_formate": "50.00€",
    "est_payant": true
}
```

### **Vérifier Éligibilité Inscription**
```
GET /evenements/ajax/evenements/<int:pk>/peut-inscrire/
```
**Vue :** `CheckPeutInscrireView`  
**Permission :** Connecté

**Réponse JSON :**
```json
{
    "peut_inscrire": true,
    "message": "Inscription possible",
    "places_disponibles": 10,
    "est_complet": false
}
```

### **Autocomplétion Organisateurs**
```
GET /evenements/ajax/recherche/organisateurs/?q=<query>
```
**Vue :** `AutocompleteOrganisateursView`  
**Permission :** Staff

**Réponse JSON :**
```json
{
    "results": [
        {
            "id": 1,
            "text": "Jean Dupont (jean@example.com)",
            "nom_complet": "Jean Dupont",
            "email": "jean@example.com"
        }
    ]
}
```

### **Autocomplétion Lieux**
```
GET /evenements/ajax/recherche/lieux/?q=<query>
```
**Vue :** `AutocompleteLieuxView`  
**Permission :** Connecté

**Réponse JSON :**
```json
{
    "results": [
        {"id": "Salle de conférence", "text": "Salle de conférence"},
        {"id": "Centre de formation", "text": "Centre de formation"}
    ]
}
```

### **Promouvoir depuis Liste d'Attente**
```
POST /evenements/ajax/inscriptions/<int:pk>/promouvoir/
```
**Vue :** `PromouvoirListeAttenteView`  
**Permission :** Staff

**Réponse JSON :**
```json
{
    "success": true,
    "message": "Inscription promue avec succès",
    "nouveau_statut": "En attente de confirmation"
}
```

## 🌐 Vues Publiques

### **Événements Publics**
```
GET /evenements/public/evenements/
```
**Vue :** `EvenementsPublicsView`  
**Permission :** Public

**Filtres :** Seuls les événements publiés, à venir, avec inscriptions ouvertes

### **Détail Public d'un Événement**
```
GET /evenements/public/evenements/<int:pk>/
```
**Vue :** `EvenementPublicDetailView`  
**Permission :** Public

### **Calendrier Public**
```
GET /evenements/public/calendrier/
```
**Vue :** `CalendrierPublicView`  
**Permission :** Public  
**Format :** Interface calendrier JavaScript

## 📈 Rapports et Statistiques

### **Rapport d'Événements**
```
GET /evenements/rapports/evenements/?date_debut=<date>&date_fin=<date>
```
**Vue :** `RapportEvenementsView`  
**Permission :** Staff

**Contexte :**
```python
{
    'stats_generales': {
        'total_evenements': int,
        'evenements_publies': int,
        'evenements_annules': int,
        'total_inscriptions': int,
        'participants_total': int,
        'revenus_total': Decimal
    },
    'stats_par_type': QuerySet,
    'evolution_mensuelle': list
}
```

### **Mes Inscriptions**
```
GET /evenements/inscriptions/mes-inscriptions/
```
**Vue :** `MesInscriptionsView`  
**Permission :** Membre connecté

## 🔧 Utilitaires et Maintenance

### **Nettoyer Inscriptions Expirées**
```
POST /evenements/maintenance/nettoyer-inscriptions/
```
**Vue :** `NettoyerInscriptionsView`  
**Permission :** Staff

### **Validation en Masse**
```
POST /evenements/validation/validation-masse/
```
**Vue :** `ValidationMasseView`  
**Permission :** Staff

**Paramètres POST :**
```python
{
    'action': 'approuver|refuser',
    'evenements': [1, 2, 3],  # IDs des événements
    'commentaire': str
}
```

## 🗂️ Corbeille

### **Événements Supprimés**
```
GET /evenements/corbeille/evenements/
```
**Vue :** `CorbeilleEvenementsView`  
**Permission :** Staff

### **Restaurer un Événement**
```
POST /evenements/corbeille/evenements/<int:pk>/restaurer/
```
**Vue :** `RestaurerEvenementView`  
**Permission :** Staff

## 🔒 Gestion des Permissions

### **Matrice des Permissions**

| Action | Public | Membre | Organisateur | Staff | Admin |
|--------|--------|---------|--------------|-------|-------|
| Voir événements publics | ✅ | ✅ | ✅ | ✅ | ✅ |
| S'inscrire | ❌ | ✅ | ✅ | ✅ | ✅ |
| Créer événement | ❌ | ❌ | ✅ | ✅ | ✅ |
| Modifier événement | ❌ | ❌ | ✅* | ✅ | ✅ |
| Valider événement | ❌ | ❌ | ❌ | ✅ | ✅ |
| Exports | ❌ | ❌ | ✅* | ✅ | ✅ |
| Administration | ❌ | ❌ | ❌ | ✅ | ✅ |

*Uniquement pour ses propres événements

### **Décorateurs de Permission**
```python
# Utilisés dans les vues
@login_required
@staff_member_required
@permission_required('evenements.add_evenement')

# Mixins utilisés
LoginRequiredMixin
StaffRequiredMixin
PermissionRequiredMixin
```

## 📱 Codes de Réponse HTTP

### **Codes de Succès**
- `200 OK` : Requête réussie
- `201 Created` : Ressource créée
- `302 Found` : Redirection après action

### **Codes d'Erreur**
- `400 Bad Request` : Données invalides
- `401 Unauthorized` : Non authentifié
- `403 Forbidden` : Pas d'autorisation
- `404 Not Found` : Ressource inexistante
- `500 Internal Server Error` : Erreur serveur

## 🔍 Exemples d'Utilisation

### **Inscription via JavaScript**
```javascript
// Vérifier éligibilité
fetch('/evenements/ajax/evenements/1/peut-inscrire/')
    .then(response => response.json())
    .then(data => {
        if (data.peut_inscrire) {
            // Afficher formulaire d'inscription
            document.getElementById('form-inscription').style.display = 'block';
        } else {
            // Afficher message d'erreur
            alert(data.message);
        }
    });

// Calculer tarif en temps réel
fetch('/evenements/ajax/evenements/1/calculer-tarif/')
    .then(response => response.json())
    .then(data => {
        document.getElementById('tarif-display').textContent = data.tarif_formate;
    });
```

### **Export via curl**
```bash
# Export CSV des événements
curl -H "Cookie: sessionid=xxx" \
     "/evenements/export/evenements/?format=csv&date_debut=2024-01-01" \
     -o evenements.csv

# Export badges PDF
curl -H "Cookie: sessionid=xxx" \
     "/evenements/export/evenements/1/badges/" \
     -o badges.pdf
```

## 🚀 Performance et Optimisation

### **Mise en Cache**
```python
# Vues avec cache automatique
@cache_page(60 * 15)  # 15 minutes
def evenements_publics():
    pass

# Cache manuel
from django.core.cache import cache
stats = cache.get_or_set('evenements_stats', calcul_stats, 3600)
```

### **Optimisations SQL**
```python
# Requêtes optimisées utilisées
evenements = Evenement.objects.select_related(
    'type_evenement', 'organisateur'
).prefetch_related(
    'inscriptions__membre'
).avec_statistiques()
```

---

**📝 Documentation API complète**  
**🔄 Mise à jour** : Automatique avec le code  
**🧪 Tests** : Tous les endpoints testés  
**📊 Version** : 1.0.0