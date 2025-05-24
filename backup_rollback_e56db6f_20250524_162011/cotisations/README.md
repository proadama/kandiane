# Application Cotisations

## Présentation
L'application **Cotisations** fournit un système complet de gestion des cotisations pour les associations. Elle permet de suivre les paiements, gérer les barèmes de cotisation et envoyer des rappels automatiques.

## Fonctionnalités principales

- 💰 **Gestion complète des cotisations** avec suivi des statuts de paiement
- 💳 **Suivi des paiements** avec support pour paiements partiels et multiples
- 📊 **Barèmes de cotisations** par type de membre
- 📧 **Rappels automatiques** pour les cotisations en retard
- 📃 **Historique complet** des modifications et paiements
- 🔍 **Recherche avancée** avec filtres multiples

## Modèles principaux

### Cotisation
Enregistre une cotisation associée à un membre.
- Référence unique
- Montant et montant restant
- Dates d'émission et d'échéance
- Statut de paiement (non payée, partiellement payée, payée)
- Liens vers membre et type de membre

### Paiement
Enregistre un paiement associé à une cotisation.
- Montant
- Date de paiement
- Mode de paiement
- Type de transaction (paiement, remboursement, rejet)

### BaremeCotisation
Définit les montants de cotisation par type de membre.
- Montant
- Périodicité (mensuelle, trimestrielle, semestrielle, annuelle)
- Dates de validité

### Rappel
Gère les rappels envoyés pour les cotisations en retard.
- Type de rappel (email, SMS, courrier, appel)
- Niveau de rappel
- Suivi de l'état (planifié, envoyé, échoué, lu)

## Intégration

L'application s'intègre avec:
- **Application Membres**: Accès aux informations des membres
- **Application Accounts**: Gestion des utilisateurs et permissions
- **Application Core**: Utilisation des modèles de base et statuts

## Développement futur

- Interface complète de tableau de bord
- Génération automatique de reçus PDF
- Système avancé de rappels automatiques
- Statistiques et reporting détaillés