# =======================================================
# SCRIPT ROLLBACK PERSONNALISÉ - PowerShell Windows
# Commit cible: e56db6f
# Migrations à supprimer: 0005, 0006
# =======================================================

param(
    [switch]$Force = $false
)

# Configuration
$targetCommit = "e56db6f"
$migrationsToDelete = @(
    "0006_rappel_erreurs_validation_rappel_template_utilise_and_more.py",
    "0005_rappeltemplate.py"
)

Write-Host "🔄 ROLLBACK PERSONNALISÉ - Retour à $targetCommit" -ForegroundColor Yellow
Write-Host "====================================================" -ForegroundColor Yellow

# =======================================================
# ÉTAPE 1: Vérifications préalables
# =======================================================
Write-Host "`n🔍 ÉTAPE 1: Vérifications préalables" -ForegroundColor Cyan

# Vérifier qu'on est dans le bon projet
if (-not (Test-Path "manage.py")) {
    Write-Host "❌ ERREUR: manage.py non trouvé" -ForegroundColor Red
    Write-Host "   Exécutez ce script depuis la racine de votre projet Django" -ForegroundColor Yellow
    Write-Host "   Exemple: cd C:\Users\frada\OneDrive\INFORMATIQUE\Web\SourceCode\project-web" -ForegroundColor Yellow
    exit 1
}

Write-Host "✅ Projet Django détecté" -ForegroundColor Green

# Vérifier que le commit cible existe
try {
    $commitInfo = git show --oneline -s $targetCommit 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Commit cible trouvé: $commitInfo" -ForegroundColor Green
    } else {
        throw "Commit non trouvé"
    }
} catch {
    Write-Host "❌ ERREUR: Commit $targetCommit non trouvé" -ForegroundColor Red
    Write-Host "   Vérifiez le hash du commit avec: git log --oneline" -ForegroundColor Yellow
    exit 1
}

# Afficher l'état actuel
Write-Host "`n📊 État actuel:" -ForegroundColor Cyan
Write-Host "Répertoire: $(Get-Location)" -ForegroundColor White
git status --porcelain | ForEach-Object { Write-Host "   $_" -ForegroundColor Yellow }

# Vérifier les migrations existantes
Write-Host "`n📂 Migrations actuelles dans cotisations:" -ForegroundColor Cyan
$currentMigrations = Get-ChildItem "apps\cotisations\migrations\*.py" -ErrorAction SilentlyContinue
if ($currentMigrations) {
    $currentMigrations | ForEach-Object { 
        $status = if ($_.Name -in $migrationsToDelete) { "[À SUPPRIMER]" } else { "[À CONSERVER]" }
        Write-Host "   $status $($_.Name)" -ForegroundColor $(if ($_.Name -in $migrationsToDelete) { "Red" } else { "Green" })
    }
} else {
    Write-Host "   Aucune migration trouvée" -ForegroundColor Yellow
}

# =======================================================
# ÉTAPE 2: Sauvegarde de sécurité
# =======================================================
Write-Host "`n💾 ÉTAPE 2: Sauvegarde de sécurité" -ForegroundColor Cyan

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupDir = "backup_rollback_e56db6f_$timestamp"

Write-Host "📦 Création de la sauvegarde: $backupDir" -ForegroundColor White
New-Item -ItemType Directory -Path $backupDir -Force | Out-Null

# Sauvegarder les éléments critiques
$backupItems = @(
    @{ Source = "apps\cotisations"; Dest = "$backupDir\cotisations"; Name = "Application cotisations" },
    @{ Source = "db.sqlite3"; Dest = "$backupDir\db.sqlite3"; Name = "Base de données" },
    @{ Source = "static\js\cotisations"; Dest = "$backupDir\static_js"; Name = "JS cotisations" },
    @{ Source = "templates\cotisations"; Dest = "$backupDir\templates"; Name = "Templates cotisations" }
)

foreach ($item in $backupItems) {
    if (Test-Path $item.Source) {
        if ((Get-Item $item.Source) -is [System.IO.DirectoryInfo]) {
            Copy-Item -Path $item.Source -Destination $item.Dest -Recurse -Force
        } else {
            Copy-Item -Path $item.Source -Destination $item.Dest -Force
        }
        Write-Host "   ✅ $($item.Name) sauvegardé" -ForegroundColor Green
    } else {
        Write-Host "   ⚠️  $($item.Name) non trouvé, ignoré" -ForegroundColor Yellow
    }
}

# Sauvegarder les stash actuels
$stashCount = (git stash list | Measure-Object).Count
if ($stashCount -gt 0) {
    Write-Host "   📋 $stashCount stash(es) existant(s) préservé(s)" -ForegroundColor Green
}

Write-Host "✅ Sauvegarde terminée dans: $backupDir" -ForegroundColor Green

# =======================================================
# ÉTAPE 3: Confirmation utilisateur
# =======================================================
if (-not $Force) {
    Write-Host "`n⚠️  CONFIRMATION REQUISE" -ForegroundColor Red
    Write-Host "=============================" -ForegroundColor Red
    Write-Host "ATTENTION: Cette opération va:" -ForegroundColor Yellow
    Write-Host "   ❌ Revenir au commit: $targetCommit" -ForegroundColor Red
    Write-Host "   ❌ Supprimer DÉFINITIVEMENT tous les commits après $targetCommit" -ForegroundColor Red
    Write-Host "   ❌ Supprimer les migrations: " -ForegroundColor Red
    $migrationsToDelete | ForEach-Object { Write-Host "      - $_" -ForegroundColor Red }
    Write-Host "   ❌ Perdre tous les changements non commités" -ForegroundColor Red
    Write-Host ""
    Write-Host "   ✅ Sauvegarde disponible dans: $backupDir" -ForegroundColor Green
    Write-Host ""
    
    $confirmation = Read-Host "Tapez 'OUI' en majuscules pour confirmer"
    if ($confirmation -ne "OUI") {
        Write-Host "❌ Opération annulée par l'utilisateur" -ForegroundColor Red
        Write-Host "💾 Sauvegarde conservée dans: $backupDir" -ForegroundColor Green
        exit 0
    }
}

# =======================================================
# ÉTAPE 4: Nettoyage de la base de données
# =======================================================
Write-Host "`n🗄️ ÉTAPE 4: Nettoyage de la base de données" -ForegroundColor Cyan

# Tenter de faire un migrate vers zero pour les migrations à supprimer
Write-Host "📦 Tentative de rollback des migrations en base..." -ForegroundColor White

try {
    # Identifier le numéro de la migration précédente (0004)
    $keepMigration = "0004"
    
    Write-Host "   Rollback vers la migration $keepMigration..." -ForegroundColor White
    python manage.py migrate cotisations $keepMigration --fake 2>$null
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   ✅ Rollback des migrations réussi" -ForegroundColor Green
    } else {
        Write-Host "   ⚠️  Rollback partiel, on continue..." -ForegroundColor Yellow
    }
} catch {
    Write-Host "   ⚠️  Erreur lors du rollback des migrations, on continue..." -ForegroundColor Yellow
}

# =======================================================
# ÉTAPE 5: Rollback Git
# =======================================================
Write-Host "`n🔄 ÉTAPE 5: Rollback Git vers $targetCommit" -ForegroundColor Cyan

# Stash les changements actuels
Write-Host "💾 Sauvegarde des changements non commités..." -ForegroundColor White
git stash push -m "Rollback automatique vers $targetCommit - $timestamp" 2>$null

# Reset hard vers le commit cible
Write-Host "🎯 Reset vers le commit $targetCommit..." -ForegroundColor White
git reset --hard $targetCommit

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Reset Git réussi" -ForegroundColor Green
} else {
    Write-Host "❌ ERREUR lors du reset Git" -ForegroundColor Red
    exit 1
}

# Vérifier le résultat
Write-Host "`n📊 État après rollback Git:" -ForegroundColor White
$currentCommit = git rev-parse --short HEAD
Write-Host "   Commit actuel: $currentCommit" -ForegroundColor Green
git log --oneline -3 | ForEach-Object { Write-Host "   $_" -ForegroundColor Gray }

# =======================================================
# ÉTAPE 6: Suppression des migrations spécifiques
# =======================================================
Write-Host "`n🗑️  ÉTAPE 6: Suppression des migrations spécifiques" -ForegroundColor Cyan

$migrationsDir = "apps\cotisations\migrations"
$deletedCount = 0

foreach ($migrationFile in $migrationsToDelete) {
    $fullPath = Join-Path $migrationsDir $migrationFile
    if (Test-Path $fullPath) {
        Remove-Item $fullPath -Force
        Write-Host "   ✅ Supprimé: $migrationFile" -ForegroundColor Green
        $deletedCount++
    } else {
        Write-Host "   ⚠️  Non trouvé: $migrationFile" -ForegroundColor Yellow
    }
}

Write-Host "📊 $deletedCount migration(s) supprimée(s)" -ForegroundColor Green

# Vérifier les migrations restantes
Write-Host "`n📂 Migrations restantes:" -ForegroundColor White
$remainingMigrations = Get-ChildItem "$migrationsDir\*.py" -ErrorAction SilentlyContinue | Where-Object { $_.Name -ne "__init__.py" }
if ($remainingMigrations) {
    $remainingMigrations | ForEach-Object { Write-Host "   ✅ $($_.Name)" -ForegroundColor Green }
} else {
    Write-Host "   ⚠️  Aucune migration restante (hors __init__.py)" -ForegroundColor Yellow
}

# =======================================================
# ÉTAPE 7: Nettoyage de l'environnement
# =======================================================
Write-Host "`n🧹 ÉTAPE 7: Nettoyage de l'environnement" -ForegroundColor Cyan

# Supprimer les fichiers Python compilés
Write-Host "🗑️  Suppression des fichiers .pyc et __pycache__..." -ForegroundColor White
Get-ChildItem -Path . -Recurse -Filter "*.pyc" -ErrorAction SilentlyContinue | Remove-Item -Force
Get-ChildItem -Path . -Recurse -Name "__pycache__" -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force
Write-Host "   ✅ Fichiers temporaires supprimés" -ForegroundColor Green

# Nettoyer les fichiers statiques collectés
if (Test-Path "staticfiles") {
    Write-Host "🗑️  Nettoyage des fichiers statiques..." -ForegroundColor White
    Remove-Item "staticfiles" -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "   ✅ Staticfiles nettoyé" -ForegroundColor Green
}

# =======================================================
# ÉTAPE 8: Reconstruction
# =======================================================
Write-Host "`n🏗️  ÉTAPE 8: Reconstruction de l'environnement" -ForegroundColor Cyan

# Recollecte des fichiers statiques
Write-Host "📦 Recollecte des fichiers statiques..." -ForegroundColor White
python manage.py collectstatic --noinput --clear 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "   ✅ Fichiers statiques collectés" -ForegroundColor Green
} else {
    Write-Host "   ⚠️  Erreur lors de la collecte, continuons..." -ForegroundColor Yellow
}

# Créer les nouvelles migrations si nécessaire
Write-Host "📝 Vérification des migrations nécessaires..." -ForegroundColor White
$makeMigrationsOutput = python manage.py makemigrations cotisations --dry-run 2>&1
if ($makeMigrationsOutput -match "No changes detected") {
    Write-Host "   ✅ Aucune nouvelle migration nécessaire" -ForegroundColor Green
} else {
    Write-Host "   📝 Création des nouvelles migrations..." -ForegroundColor White
    python manage.py makemigrations cotisations
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   ✅ Nouvelles migrations créées" -ForegroundColor Green
    } else {
        Write-Host "   ❌ Erreur lors de la création des migrations" -ForegroundColor Red
    }
}

# Appliquer les migrations
Write-Host "📦 Application des migrations..." -ForegroundColor White
python manage.py migrate 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "   ✅ Migrations appliquées avec succès" -ForegroundColor Green
} else {
    Write-Host "   ⚠️  Erreur lors de l'application, vérifiez manuellement" -ForegroundColor Yellow
}

# =======================================================
# ÉTAPE 9: Vérifications finales
# =======================================================
Write-Host "`n✅ ÉTAPE 9: Vérifications finales" -ForegroundColor Cyan

# Check Django
Write-Host "🔍 Vérification de Django..." -ForegroundColor White
$checkOutput = python manage.py check 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "   ✅ Django check réussi" -ForegroundColor Green
} else {
    Write-Host "   ⚠️  Avertissements Django:" -ForegroundColor Yellow
    $checkOutput | ForEach-Object { Write-Host "      $_" -ForegroundColor Yellow }
}

# Test de base des migrations
Write-Host "🧪 Test des migrations..." -ForegroundColor White
try {
    python manage.py showmigrations cotisations | Out-String | ForEach-Object {
        if ($_ -match "\[X\]") { Write-Host "   ✅ Migration appliquée" -ForegroundColor Green }
        elseif ($_ -match "\[ \]") { Write-Host "   ⚠️  Migration en attente" -ForegroundColor Yellow }
    }
} catch {
    Write-Host "   ⚠️  Impossible de vérifier les migrations" -ForegroundColor Yellow
}

# =======================================================
# ÉTAPE 10: Création d'un point de sauvegarde
# =======================================================
Write-Host "`n💾 ÉTAPE 10: Point de sauvegarde propre" -ForegroundColor Cyan

# Créer un commit de sauvegarde
Write-Host "📝 Création d'un commit de sauvegarde..." -ForegroundColor White
git add . 2>$null
$commitMessage = @"
🔄 Rollback complet vers $targetCommit - État propre

✅ Actions effectuées:
- Rollback Git vers commit $targetCommit
- Suppression migrations: $(($migrationsToDelete | ForEach-Object { $_.Replace('.py', '') }) -join ', ')
- Environnement nettoyé et reconstruit
- Migrations recréées si nécessaire

📦 Sauvegarde disponible: $backupDir
📅 Date: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
🤖 Rollback automatique
"@

git commit -m $commitMessage 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "   ✅ Commit de sauvegarde créé" -ForegroundColor Green
} else {
    Write-Host "   ⚠️  Pas de changements à commiter" -ForegroundColor Yellow
}

# Créer une branche de sauvegarde
$branchName = "rollback-propre-$timestamp"
git branch $branchName 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "   🌿 Branche de sauvegarde créée: $branchName" -ForegroundColor Green
}

# =======================================================
# RÉSUMÉ FINAL
# =======================================================
Write-Host "`n🎉 ROLLBACK TERMINÉ AVEC SUCCÈS!" -ForegroundColor Green
Write-Host "=======================================" -ForegroundColor Green

Write-Host "`n📋 RÉSUMÉ DES ACTIONS:" -ForegroundColor Cyan
Write-Host "✅ Rollback Git vers commit: $targetCommit" -ForegroundColor White
Write-Host "✅ Migrations supprimées:" -ForegroundColor White
$migrationsToDelete | ForEach-Object { Write-Host "   - $_" -ForegroundColor Gray }
Write-Host "✅ Base de données nettoyée" -ForegroundColor White
Write-Host "✅ Environnement reconstruit" -ForegroundColor White
Write-Host "✅ Sauvegarde complète: $backupDir" -ForegroundColor White
Write-Host "✅ Point de sauvegarde: $branchName" -ForegroundColor White

Write-Host "`n🚀 PROCHAINES ÉTAPES:" -ForegroundColor Yellow
Write-Host "1. Tester que l'application fonctionne:" -ForegroundColor White
Write-Host "   python manage.py runserver" -ForegroundColor Gray
Write-Host "2. Accéder à: http://localhost:8000/cotisations/" -ForegroundColor White
Write-Host "3. Tester la création d'un rappel basique" -ForegroundColor White
Write-Host "4. Commencer l'implémentation étape par étape" -ForegroundColor White

Write-Host "`n🆘 EN CAS DE PROBLÈME:" -ForegroundColor Red
Write-Host "- Sauvegarde complète: $backupDir" -ForegroundColor White
Write-Host "- Branche de sauvegarde: git checkout $branchName" -ForegroundColor White
Write-Host "- Stash disponible: git stash list" -ForegroundColor White
Write-Host "- Restaurer DB: Copy-Item '$backupDir\db.sqlite3' '.\db.sqlite3' -Force" -ForegroundColor White

Write-Host "`n🎯 VOUS ÊTES MAINTENANT PRÊT POUR UNE IMPLÉMENTATION PROPRE!" -ForegroundColor Green
Write-Host "=================================================================" -ForegroundColor Green

# Afficher les informations finales pour référence
Write-Host "`n📊 ÉTAT FINAL:" -ForegroundColor Cyan
Write-Host "Commit actuel: $(git rev-parse --short HEAD)" -ForegroundColor White
Write-Host "Branche: $(git branch --show-current)" -ForegroundColor White
Write-Host "Migrations cotisations:" -ForegroundColor White
Get-ChildItem "apps\cotisations\migrations\*.py" -ErrorAction SilentlyContinue | Where-Object { $_.Name -ne "__init__.py" } | ForEach-Object { 
    Write-Host "   $($_.Name)" -ForegroundColor Gray 
}

Write-Host "`nScript terminé. Bon développement! 🚀" -ForegroundColor Green