# apps/core/migrations/XXXX_add_log_model.py
# CRÉER cette migration après avoir ajouté le modèle Log

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('core', '0001_initial'),  # Adapter selon la dernière migration existante
    ]

    operations = [
        migrations.CreateModel(
            name='Log',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(max_length=100, verbose_name='Action')),
                ('details', models.JSONField(blank=True, default=dict, verbose_name='Détails')),
                ('adresse_ip', models.GenericIPAddressField(blank=True, null=True, verbose_name='Adresse IP')),
                ('timestamp', models.DateTimeField(default=django.utils.timezone.now, verbose_name='Horodatage')),
                ('utilisateur', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, verbose_name='Utilisateur')),
            ],
            options={
                'verbose_name': 'Log',
                'verbose_name_plural': 'Logs',
                'ordering': ['-timestamp'],
            },
        ),
        migrations.AddIndex(
            model_name='log',
            index=models.Index(fields=['action'], name='core_log_action_idx'),
        ),
        migrations.AddIndex(
            model_name='log',
            index=models.Index(fields=['timestamp'], name='core_log_timestamp_idx'),
        ),
        migrations.AddIndex(
            model_name='log',
            index=models.Index(fields=['utilisateur'], name='core_log_utilisateur_idx'),
        ),
    ]