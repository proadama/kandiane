# Utilisation des barèmes de cotisation : exemples concrets

Les barèmes de cotisation permettent de standardiser et d'automatiser le calcul des montants selon le type de membre. Voici trois exemples concrets d'utilisation :

## Exemple 1 : Cotisation annuelle standard

**Scénario** : Marie vient de rejoindre l'association comme "Membre Actif"

1. L'administrateur va dans "Nouvelle cotisation"
2. Il sélectionne Marie dans la liste des membres
3. Le type de membre "Membre Actif" est automatiquement sélectionné (car c'est son type actuel)
4. L'option "Utiliser un barème pour calculer le montant" est cochée par défaut
5. Dans la liste déroulante des barèmes, il sélectionne "Barème annuel - Membre Actif (50€)"
6. **Le montant est automatiquement rempli avec 50€**
7. Les dates de début et fin de période sont automatiquement définies pour couvrir une année
8. L'administrateur n'a plus qu'à valider la cotisation

**Avantage** : Gain de temps et réduction des erreurs de saisie manuelle des montants.

## Exemple 2 : Cotisation avec prorata temporis

**Scénario** : Thomas rejoint l'association en milieu d'année comme "Membre Familial"

1. L'administrateur crée une nouvelle cotisation
2. Il sélectionne Thomas comme membre et "Membre Familial" comme type
3. Il coche "Utiliser un barème pour calculer le montant"
4. Il sélectionne "Barème annuel - Membre Familial (80€)"
5. Il modifie la période de validité : au lieu d'une année complète, il indique une période de 6 mois
6. **Le système calcule automatiquement un montant au prorata : 40€** (la moitié du barème annuel)
7. Ce calcul se fait via une requête AJAX qui appelle `api_calculer_montant` quand la période change

**Avantage** : Calcul équitable des cotisations partielles sans avoir à faire le calcul manuellement.

## Exemple 3 : Gestion des changements de tarifs

**Scénario** : L'association augmente ses tarifs pour l'année suivante

1. L'administrateur va dans "Barèmes" puis "Nouveau barème"
2. Il crée un nouveau barème pour "Membre Senior" à 45€ (au lieu de 40€)
3. Il définit une date de début de validité au 1er janvier de l'année suivante
4. À partir de cette date, lors de la création de cotisations :
   - Pour les membres de type "Senior", le nouveau barème apparaît en premier dans la liste
   - **En le sélectionnant, le montant s'actualise automatiquement à 45€**
   - Les anciens barèmes restent disponibles mais sont affichés plus bas dans la liste

**Avantage** : Transition facile entre différents tarifs avec historisation, sans avoir à modifier manuellement les anciens barèmes.

---

Dans tous ces cas, la logique est gérée par:
1. Un appel JavaScript qui réagit aux changements de type de membre ou de barème
2. Une requête à l'API interne `api_calculer_montant` 
3. L'affichage automatique du montant dans le formulaire

Cette automatisation garantit la cohérence des tarifs et simplifie considérablement le travail administratif, en particulier lors des renouvellements en masse.