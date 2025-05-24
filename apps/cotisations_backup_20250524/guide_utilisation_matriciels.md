# Guide d'utilisation - Templates matriciels

## 🎯 Vue d'ensemble

Les templates matriciels organisent vos rappels selon une logique **3×3** :

| Type \ Niveau | **Standard** | **Urgent** | **Formel** |
|--------------|-------------|-----------|-----------|
| **📧 Email** | Rappel poli | Délai précis | Mise en demeure |
| **📱 SMS** | Court & amical | Direct & pressant | Avis officiel |
| **📮 Courrier** | Lettre cordiale | Recommandé AR | Document juridique |

## 🚀 Installation et première utilisation

### 1. Créer les templates matriciels

```bash
# Créer tous les templates (9 au total)
python manage.py create_rappel_templates

# Forcer la recréation (supprime les existants)
python manage.py create_rappel_templates --force

# Créer uniquement les templates Email
python manage.py create_rappel_templates --type=email

# Créer des templates en anglais
python manage.py create_rappel_templates --langue=en
```

### 2. Vérifier la création

```bash
# Via l'admin Django
http://localhost:8000/admin/cotisations/rappeltemplate/

# Via le shell Django
python manage.py shell
>>> from apps.cotisations.models import RappelTemplate
>>> RappelTemplate.objects.count()
9  # Devrait afficher 9 templates créés
```

## 📋 Caractéristiques de chaque type

### 📧 **TEMPLATES EMAIL**

#### **Email Standard** (Niveau 1-2)
- **Objectif** : Premier rappel amical
- **Ton** : Poli et compréhensif
- **Contenu** : ~800 caractères
- **Variables spéciales** : `{lien_paiement}`, `{signature_html}`
- **Usage** : Rappel classique, membre régulier

#### **Email Urgent** (Niveau 2-4)
- **Objectif** : Rappel avec délai strict
- **Ton** : Direct mais professionnel
- **Contenu** : ~1200 caractères
- **Éléments visuels** : Emojis d'alerte, délais en gras
- **Usage** : Cotisation en retard > 7 jours

#### **Email Formel** (Niveau 3-5)
- **Objectif** : Mise en demeure officielle
- **Ton** : Juridique et ferme
- **Contenu** : ~1800 caractères
- **Mentions légales** : Références Code Civil, conséquences
- **Usage** : Dernier rappel avant procédure

### 📱 **TEMPLATES SMS**

#### **SMS Standard** (Niveau 1-2)
- **Contrainte** : ≤ 160 caractères
- **Ton** : Amical avec emoji
- **Contenu type** : "Bonjour Jean ! 😊 Petit rappel..."
- **Usage** : Rappel rapide et discret

#### **SMS Urgent** (Niveau 2-4)
- **Contrainte** : ≤ 160 caractères
- **Ton** : Direct et pressant
- **Format** : "⚠️ URGENT Jean - Cotisation..."
- **Usage** : Alerte immédiate

#### **SMS Formel** (Niveau 3-5)
- **Contrainte** : ≤ 160 caractères
- **Ton** : Officiel, sans emoji
- **Format** : "AVIS OFFICIEL - M. Dupont..."
- **Usage** : Notification légale

### 📮 **TEMPLATES COURRIER**

#### **Courrier Standard** (Niveau 1-2)
- **Format** : Lettre classique avec en-tête
- **Ton** : Cordial et respectueux
- **Longueur** : 1 page
- **Usage** : Rappel traditionnel

#### **Courrier Urgent** (Niveau 2-4)
- **Format** : Lettre recommandée avec A.R.
- **Ton** : Ferme mais courtois
- **Mentions** : "RAPPEL URGENT", délais encadrés
- **Usage** : Escalade officielle

#### **Courrier Formel** (Niveau 3-5)
- **Format** : Document juridique complet
- **Ton** : Légal et procédural
- **Mentions** : Articles de loi, procédures, conséquences
- **Usage** : Mise en demeure préalable à procédure

## 🎨 Personnalisation des templates

### Variables disponibles dans tous les templates

| Variable | Description | Exemple |
|----------|-------------|---------|
| `{prenom}` | Prénom du membre | Jean |
| `{nom}` | Nom du membre | Dupont |
| `{reference}` | Référence cotisation | COT-2024-0001 |
| `{montant}` | Montant restant dû | 120.00 |
| `{date_echeance}` | Date d'échéance | 15/01/2024 |
| `{jours_retard}` | Jours de retard | 15 |
| `{date_limite}` | Date limite règlement | 31/01/2024 |
| `{association_nom}` | Nom de l'association | Mon Association |

### Variables spécialisées par type

#### Pour les emails
- `{lien_paiement}` : URL de paiement en ligne
- `{signature_html}` : Signature formatée HTML
- `{bouton_contact}` : Bouton de contact stylisé

#### Pour les SMS
- `{lien_court}` : URL raccourcie
- `{tel_urgence}` : Numéro d'urgence
- `{ref_courte}` : Référence abrégée

#### Pour les courriers
- `{adresse_complete}` : Adresse postale du membre
- `{mentions_legales}` : Mentions obligatoires
- `{cachet}` : Emplacement pour cachet/signature

## 🔧 Administration et gestion

### Interface d'administration

```
http://localhost:8000/admin/cotisations/rappeltemplate/
```

**Fonctionnalités disponibles :**
- ✅ Liste filtrée par type/niveau
- ✅ Recherche dans le contenu
- ✅ Prévisualisation des templates
- ✅ Duplication de templates
- ✅ Activation/désactivation en masse

### Actions en lot

```python
# Dans l'admin Django, sélectionner plusieurs templates et :
- "Activer les templates sélectionnés"
- "Désactiver les templates sélectionnés"
```

### Sauvegarde et restauration

```bash
# Exporter tous les templates
python manage.py dumpdata cotisations.RappelTemplate > templates_backup.json

# Restaurer les templates
python manage.py loaddata templates_backup.json
```

## 🎯 Utilisation dans l'interface

### Sélection automatique intelligente

L'interface propose automatiquement les templates selon :

1. **Type de rappel choisi** (Email/SMS/Courrier)
2. **Niveau de rappel saisi** (1-5)
3. **Disponibilité du template**

### Workflow utilisateur

```
1. Sélectionner le type : Email/SMS/Courrier
   ↓
2. Choisir le niveau : 1-5
   ↓
3. Templates compatibles affichés automatiquement
   ↓
4. Cliquer sur le template souhaité
   ↓
5. Contenu personnalisé généré avec les variables
   ↓
6. Modification possible avant envoi
```

### Interface visuelle

Les boutons de templates sont colorés selon leur niveau :
- 🟢 **Standard** : Vert (amical)
- 🟡 **Urgent** : Orange (attention)
- 🔴 **Formel** : Rouge (alerte)

## 📊 Monitoring et statistiques

### Utilisation des templates

```python
# Via le shell Django
from apps.cotisations.models import RappelTemplate, Rappel

# Templates les plus utilisés
templates_usage = Rappel.objects.values('template_utilise').annotate(
    count=Count('id')
).order_by('-count')

# Efficacité par type
taux_reponse = Rappel.objects.values('type_rappel').annotate(
    envoyes=Count('id'),
    repondus=Count('id', filter=Q(etat='lu'))
)
```

### Métriques importantes

- **Taux d'ouverture** des emails
- **Taux de réponse** par type
- **Temps de traitement** moyen
- **Escalade** : passage d'un niveau à l'autre

## 🔧 Maintenance et évolution

### Mise à jour des templates

```python
# Modifier un template existant
template = RappelTemplate.objects.get(nom="Email Standard - Premier rappel")
template.contenu = "Nouveau contenu..."
template.save()
```

### Création de nouveaux templates

```python
# Ajouter un template personnalisé
RappelTemplate.objects.create(
    nom="SMS Weekend",
    type_template="custom",
    type_rappel="sms",
    contenu="Message spécial weekend...",
    niveau_min=1,
    niveau_max=2
)
```

### Nettoyage périodique

```bash
# Supprimer les templates inactifs depuis plus de 6 mois
python manage.py shell
>>> from datetime import datetime, timedelta
>>> from apps.cotisations.models import RappelTemplate
>>> cutoff = datetime.now() - timedelta(days=180)
>>> RappelTemplate.objects.filter(actif=False, updated_at__lt=cutoff).delete()
```

## 🚀 Prochaines étapes

Avec les templates matriciels en place, vous pouvez maintenant :

1. **Tester chaque template** avec de vraies données
2. **Personnaliser le contenu** selon vos besoins
3. **Ajouter des contraintes** de validation (prochaine étape)
4. **Créer des templates** dans d'autres langues
5. **Analyser l'efficacité** de chaque type

## 🆘 Dépannage

### Problèmes courants

**Template non affiché :**
- Vérifier que `actif=True`
- Contrôler les niveaux min/max
- S'assurer de la bonne langue

**Variables non remplacées :**
- Vérifier l'orthographe : `{prenom}` pas `{prénom}`
- S'assurer que la cotisation a les données requises

**Longueur SMS dépassée :**
- Utiliser des abréviations
- Supprimer les emojis non essentiels
- Utiliser `{ref_courte}` au lieu de `{reference}`

---

Les templates matriciels sont maintenant prêts ! 🎉

**Prochaine étape recommandée :** Implémentation des contraintes intelligentes pour validation automatique selon le type.