# Dans apps/cotisations/management/commands/traiter_rappels.py
from django.core.management.base import BaseCommand
from apps.cotisations.tasks import traiter_rappels_planifies

class Command(BaseCommand):
    help = 'Traite les rappels planifiés dont la date est passée'

    def handle(self, *args, **options):
        traiter_rappels_planifies()
        self.stdout.write(self.style.SUCCESS('Rappels traités avec succès'))