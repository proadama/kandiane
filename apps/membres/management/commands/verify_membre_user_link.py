"""
Commande pour vérifier que tous les membres ont un utilisateur lié.

Usage:
    python manage.py verify_membre_user_link
"""

from django.core.management.base import BaseCommand
from apps.membres.models import Membre


class Command(BaseCommand):
    help = 'Vérifie que tous les membres ont un utilisateur lié'

    def handle(self, *args, **options):
        # Compter tous les membres
        total_membres = Membre.objects.count()

        # Trouver les membres sans utilisateur
        membres_sans_user = Membre.objects.filter(utilisateur__isnull=True)

        self.stdout.write(self.style.SUCCESS(f"Total membres en base: {total_membres}"))

        if membres_sans_user.exists():
            count = membres_sans_user.count()
            self.stdout.write(self.style.ERROR(
                f"\n⚠️  ATTENTION: {count} membre(s) sans utilisateur lié!\n"
            ))

            self.stdout.write(self.style.WARNING("Liste des membres sans utilisateur:"))
            for membre in membres_sans_user:
                self.stdout.write(
                    f"  - ID: {membre.id} | {membre.nom} {membre.prenom} | Email: {membre.email}"
                )

            self.stdout.write(self.style.ERROR(
                f"\n⛔ MIGRATION BLOQUÉE: Vous devez d'abord lier ces membres à des utilisateurs."
            ))
            self.stdout.write(self.style.WARNING(
                "\nPour chaque membre, créer un utilisateur via:\n"
                "  CustomUser.objects.create_user(username='...', email='...')\n"
                "Puis lier: membre.utilisateur = user; membre.save()"
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                "\n✅ OK: Tous les membres ont un utilisateur lié.\n"
            ))
            self.stdout.write(self.style.SUCCESS(
                "Vous pouvez procéder à la migration en toute sécurité."
            ))
