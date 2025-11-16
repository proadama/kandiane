#!/bin/bash
  #
  # Script de réinitialisation de l'environnement de développement Kandiane
  #

  set -e  # Arrêter en cas d'erreur

  # Couleurs
  RED='\033[0;31m'
  GREEN='\033[0;32m'
  YELLOW='\033[1;33m'
  BLUE='\033[0;34m'
  NC='\033[0m'

  print_step() { echo -e "\n${BLUE}==>${NC} ${GREEN}$1${NC}"; }
  print_info() { echo -e "${YELLOW}ℹ${NC}  $1"; }
  print_success() { echo -e "${GREEN}✓${NC}  $1"; }
  print_error() { echo -e "${RED}✗${NC}  $1"; }

  # Vérifier qu'on est dans le bon répertoire
  if [ ! -f "manage.py" ]; then
      print_error "Erreur: manage.py non trouvé !"
      exit 1
  fi

  print_step "Réinitialisation de l'environnement Kandiane"

  # 1. Désactiver venv
  print_step "1/9 - Désactivation environnement virtuel"
  deactivate 2>/dev/null || true
  print_success "OK"

  # 2. Nettoyer cache Python
  print_step "2/9 - Nettoyage cache Python"
  find . -type f -name "*.pyc" -delete 2>/dev/null || true
  find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
  print_success "Cache nettoyé"

  # 3. Supprimer ancien venv
  print_step "3/9 - Suppression ancien venv"
  if [ -d "venv" ]; then
      rm -rf venv
      print_success "Ancien venv supprimé"
  else
      print_info "Aucun venv à supprimer"
  fi

  # 4. Nettoyer base de données
  print_step "4/9 - Nettoyage base de données"
  if [ -f "db.sqlite3" ]; then
      mv db.sqlite3 db.sqlite3.backup_$(date +%Y%m%d_%H%M%S)
      print_success "DB sauvegardée"
  else
      print_info "Aucune DB à nettoyer"
  fi

  # 5. Vérifier Python
  print_step "5/9 - Vérification Python"
  PYTHON_VERSION=$(python3 --version)
  print_success "Python: $PYTHON_VERSION"

  # 6. Créer nouveau venv
  print_step "6/9 - Création nouveau venv"
  python3 -m venv venv
  source venv/bin/activate
  print_success "Nouveau venv créé et activé"

  # 7. Mettre à jour pip
  print_step "7/9 - Mise à jour pip"
  pip install --upgrade pip --quiet
  print_success "pip mis à jour"

  # 8. Installer dépendances
  print_step "8/9 - Installation dépendances"
  pip install -r requirements.txt
  print_success "Dépendances installées"

  # 9. Vérifications
  print_step "9/9 - Vérifications"
  DJANGO_VERSION=$(python -c "import django; print(django.get_version())")
  python -c "from django.db import migrations" && print_success "Django $DJANGO_VERSION OK"
  python manage.py check && print_success "Configuration OK"

  echo ""
  echo -e "${GREEN}╔════════════════════════════════════════════════╗${NC}"
  echo -e "${GREEN}║   ✓ ENVIRONNEMENT RÉINITIALISÉ AVEC SUCCÈS !  ║${NC}"
  echo -e "${GREEN}╚════════════════════════════════════════════════╝${NC}"
  echo ""
  echo -e "${YELLOW}Prochaines étapes:${NC}"
  echo "  1. python manage.py migrate"
  echo "  2. python manage.py createsuperuser"
  echo "  3. mkdir -p static"
  echo "  4. python manage.py collectstatic --noinput"
  echo "  5. python manage.py runserver 0.0.0.0:8000"
  echo ""
