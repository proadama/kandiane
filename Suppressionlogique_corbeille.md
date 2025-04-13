# Guide d'utilisation: Suppression Logique & Corbeille

## Principes fondamentaux

1. **Suppression logique** - Tous les modèles qui héritent de `BaseModel` bénéficient d'une suppression logique par défaut.
2. **Corbeille** - Interface utilisateur permettant de voir, restaurer ou supprimer définitivement les éléments supprimés.

## API disponible sur les modèles

- `model.delete(hard=False, user=None)` - Supprime logiquement (ou physiquement si `hard=True`)
- `model.restore(user=None)` - Restaure un élément supprimé logiquement
- `model.is_deleted()` - Vérifie si l'élément est supprimé

## API disponible sur les gestionnaires

- `Model.objects.all()` - Retourne uniquement les éléments non supprimés
- `Model.objects.with_deleted()` - Retourne tous les éléments
- `Model.objects.only_deleted()` - Retourne uniquement les éléments supprimés
- `Model.objects.recent_deleted(days=30)` - Retourne les éléments supprimés récemment

## Comment implémenter la corbeille dans une nouvelle application

1. **Vues nécessaires**:
   - `XxxCorbeillePage` - Liste des éléments dans la corbeille
   - `XxxRestaurerView` - Restauration d'un élément
   - `XxxSuppressionDefinitiveView` - Suppression définitive

2. **Journalisation spécifique**:
   - Surcharger `_log_deletion` et `_log_restoration` dans le modèle

3. **Templates à créer**:
   - `templates/xxx/corbeille.html` - Interface de la corbeille

4. **URLs à ajouter**:
   - `corbeille/` - Vue de la corbeille
   - `<int:pk>/restaurer/` - Restauration d'un élément
   - `<int:pk>/supprimer-definitivement/` - Suppression définitive

## Bonnes pratiques

1. **Toujours utiliser `delete(hard=False)`** - Ne jamais appeler directement `super().delete()` 
2. **Privilégier la suppression logique** - La suppression définitive doit être une action consciente
3. **Journaliser toutes les actions** - Garder une trace complète des suppressions/restaurations
4. **Ajouter une politique de rétention** - Nettoyer périodiquement les éléments supprimés depuis longtemps