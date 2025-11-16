#!/bin/bash
  set -e

  GREEN='\033[0;32m'
  BLUE='\033[0;34m'
  NC='\033[0m'

  echo -e "${BLUE}Setup de l'application Kandiane${NC}\n"

  # Vérifier que venv est activé
  if [[ "$VIRTUAL_ENV" == "" ]]; then
      echo "⚠️  Activez d'abord l'environnement virtuel:"
      echo "   source venv/bin/activate"
      exit 1
  fi

  # Migrations
  echo -e "\n${GREEN}1. Application des migrations...${NC}"
  python manage.py migrate

  # Créer superuser
  echo -e "\n${GREEN}2. Création du superutilisateur...${NC}"
  python manage.py createsuperuser

  # Static files
  echo -e "\n${GREEN}3. Configuration des fichiers statiques...${NC}"
  mkdir -p static
  python manage.py collectstatic --noinput

  # Vérifications finales
  echo -e "\n${GREEN}4. Vérifications finales...${NC}"
  python manage.py check --deploy

  echo -e "\n${GREEN}✓ Setup terminé !${NC}"
  echo -e "\nDémarrez le serveur avec:"
  echo -e "  ${BLUE}python manage.py runserver 0.0.0.0:8000${NC}\n"
