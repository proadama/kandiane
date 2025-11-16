#!/usr/bin/env python
"""Script pour créer un superutilisateur pour les tests."""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.accounts.models import CustomUser

# Credentials par défaut pour les tests
username = 'admin'
email = 'admin@kandiane.local'
password = 'admin123'

# Vérifier si le superuser existe déjà
if CustomUser.objects.filter(username=username).exists():
    print(f"✅ Le superutilisateur '{username}' existe déjà.")
else:
    # Créer le superuser
    user = CustomUser.objects.create_superuser(
        username=username,
        email=email,
        password=password
    )
    print(f"✅ Superutilisateur créé avec succès!")
    print(f"   Username: {username}")
    print(f"   Email: {email}")
    print(f"   Password: {password}")
    print(f"\n⚠️  IMPORTANT: Changez ce mot de passe en production!")
