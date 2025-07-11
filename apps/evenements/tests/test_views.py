import pytest
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
from django.urls import reverse
from django.test import Client
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.core import mail
from unittest.mock import patch, Mock
import json

from ..models import (
    Evenement, InscriptionEvenement, ValidationEvenement,
    AccompagnantInvite, TypeEvenement
)
from .factories import (
    EvenementFactory, InscriptionEvenementFactory, MembreFactory,
    TypeEvenementFactory, ValidationEvenementFactory, CustomUserFactory,
    AccompagnantInviteFactory, EvenementCompletFactory
)

User = get_user_model()


@pytest.mark.django_db
@pytest.mark.unit
class TestDashboardEvenementView:
    """Tests pour la vue Dashboard"""

    def test_dashboard_staff_access(self, client):
        """Test accès dashboard pour staff"""
        user = CustomUserFactory(is_staff=True)
        membre = MembreFactory(utilisateur=user)
        
        client.force_login(user)
        response = client.get(reverse('evenements:dashboard'))
        
        assert response.status_code == 200
        assert 'total_evenements' in response.context
        assert 'evenements_publies' in response.context

    def test_dashboard_membre_access(self, client):
        """Test accès dashboard pour membre simple"""
        user = CustomUserFactory(is_staff=False)
        membre = MembreFactory(utilisateur=user)
        
        client.force_login(user)
        response = client.get(reverse('evenements:dashboard'))
        
        assert response.status_code == 200
        assert 'mes_prochaines_inscriptions' in response.context

    def test_dashboard_non_membre_access(self, client):
        """Test accès dashboard pour non-membre"""
        user = CustomUserFactory(is_staff=False)
        # Pas de membre associé
        
        client.force_login(user)
        response = client.get(reverse('evenements:dashboard'))
        
        assert response.status_code == 200
        # Les données spécifiques aux membres ne doivent pas être présentes

    def test_dashboard_anonyme(self, client):
        """Test accès dashboard anonyme"""
        response = client.get(reverse('evenements:dashboard'))
        assert response.status_code == 302  # Redirection vers login


@pytest.mark.django_db
@pytest.mark.unit
class TestEvenementListView:
    """Tests pour la vue Liste des événements"""

    def test_liste_evenements_public(self, client):
        """Test liste événements publics"""
        user = CustomUserFactory()
        client.force_login(user)
        
        # Créer des événements avec différents statuts
        evt_publie = EvenementFactory(statut='publie')
        evt_brouillon = EvenementFactory(statut='brouillon')
        
        response = client.get(reverse('evenements:liste'))
        
        assert response.status_code == 200
        assert evt_publie in response.context['evenements']
        assert evt_brouillon not in response.context['evenements']

    def test_liste_evenements_staff(self, client):
        """Test liste pour staff (voit tous les événements)"""
        user = CustomUserFactory(is_staff=True)
        MembreFactory(utilisateur=user)
        client.force_login(user)
        
        evt_publie = EvenementFactory(statut='publie')
        evt_brouillon = EvenementFactory(statut='brouillon')
        
        response = client.get(reverse('evenements:liste'))
        
        assert response.status_code == 200
        # Staff voit tous les événements
        evenements = response.context['evenements']
        assert evt_publie in evenements
        assert evt_brouillon in evenements

    def test_liste_avec_filtres(self, client):
        """Test liste avec filtres de recherche"""
        user = CustomUserFactory()
        client.force_login(user)
        
        type_formation = TypeEvenementFactory(libelle='Formation')
        evt_formation = EvenementFactory(
            type_evenement=type_formation,
            titre='Formation Python',
            statut='publie'
        )
        evt_autre = EvenementFactory(titre='Réunion', statut='publie')
        
        response = client.get(reverse('evenements:liste'), {
            'recherche': 'Python',
            'type_evenement': type_formation.id
        })
        
        assert response.status_code == 200
        evenements = response.context['evenements']
        assert evt_formation in evenements
        assert evt_autre not in evenements

    def test_pagination(self, client):
        """Test pagination de la liste"""
        user = CustomUserFactory()
        client.force_login(user)
        
        # Créer plus d'événements que la limite par page
        for i in range(25):
            EvenementFactory(statut='publie')
        
        response = client.get(reverse('evenements:liste'))
        
        assert response.status_code == 200
        assert response.context['is_paginated']
        assert len(response.context['evenements']) == 20  # Limite par page


@pytest.mark.django_db
@pytest.mark.unit
class TestEvenementDetailView:
    """Tests pour la vue Détail d'événement"""

    def test_detail_evenement_publie(self, client):
        """Test détail événement publié"""
        user = CustomUserFactory()
        client.force_login(user)
        
        evenement = EvenementFactory(statut='publie')
        
        response = client.get(reverse('evenements:detail', kwargs={'pk': evenement.pk}))
        
        assert response.status_code == 200
        assert response.context['evenement'] == evenement

    def test_detail_evenement_brouillon_non_staff(self, client):
        """Test détail événement brouillon pour non-staff"""
        user = CustomUserFactory(is_staff=False)
        client.force_login(user)
        
        evenement = EvenementFactory(statut='brouillon')
        
        response = client.get(reverse('evenements:detail', kwargs={'pk': evenement.pk}))
        
        assert response.status_code == 404

    def test_detail_evenement_brouillon_staff(self, client):
        """Test détail événement brouillon pour staff"""
        user = CustomUserFactory(is_staff=True)
        MembreFactory(utilisateur=user)
        client.force_login(user)
        
        evenement = EvenementFactory(statut='brouillon')
        
        response = client.get(reverse('evenements:detail', kwargs={'pk': evenement.pk}))
        
        assert response.status_code == 200

    def test_detail_avec_inscriptions(self, client):
        """Test détail avec informations d'inscription"""
        user = CustomUserFactory()
        membre = MembreFactory(utilisateur=user)
        client.force_login(user)
        
        evenement = EvenementFactory(statut='publie')
        
        response = client.get(reverse('evenements:detail', kwargs={'pk': evenement.pk}))
        
        assert response.status_code == 200
        assert 'peut_s_inscrire' in response.context
        assert 'inscription_existante' in response.context

    def test_detail_avec_inscription_existante(self, client):
        """Test détail avec inscription existante"""
        user = CustomUserFactory()
        membre = MembreFactory(utilisateur=user)
        client.force_login(user)
        
        evenement = EvenementFactory(statut='publie')
        inscription = InscriptionEvenementFactory(
            evenement=evenement,
            membre=membre,
            statut='confirmee'
        )
        
        response = client.get(reverse('evenements:detail', kwargs={'pk': evenement.pk}))
        
        assert response.status_code == 200
        assert response.context['inscription_existante'] == inscription


@pytest.mark.django_db
@pytest.mark.unit
class TestEvenementCreateView:
    """Tests pour la vue Création d'événement"""

    def test_create_access_staff(self, client):
        """Test accès création pour staff"""
        user = CustomUserFactory(is_staff=True)
        MembreFactory(utilisateur=user)
        client.force_login(user)
        
        response = client.get(reverse('evenements:creer'))
        
        assert response.status_code == 200
        assert 'form' in response.context

    def test_create_access_non_staff(self, client):
        """Test accès création pour non-staff"""
        user = CustomUserFactory(is_staff=False)
        client.force_login(user)
        
        response = client.get(reverse('evenements:creer'))
        
        assert response.status_code == 403  # Forbidden

    def test_create_evenement_valid(self, client):
        """Test création événement valide"""
        user = CustomUserFactory(is_staff=True)
        MembreFactory(utilisateur=user)
        client.force_login(user)
        
        type_evenement = TypeEvenementFactory(necessite_validation=False)
        date_debut = timezone.now() + timedelta(days=30)
        
        form_data = {
            'titre': 'Test Formation',
            'description': 'Description test',
            'type_evenement': type_evenement.id,
            'date_debut': date_debut.strftime('%Y-%m-%dT%H:%M'),
            'lieu': 'Paris',
            'capacite_max': 50,
            'inscriptions_ouvertes': True,
            'est_payant': False,
            'permet_accompagnants': True,
            'nombre_max_accompagnants': 2,
            'delai_confirmation': 48
        }
        
        response = client.post(reverse('evenements:creer'), data=form_data)
        
        assert response.status_code == 302  # Redirection après succès
        assert Evenement.objects.filter(titre='Test Formation').exists()
        
        # Vérifier le message de succès
        messages = list(get_messages(response.wsgi_request))
        assert any('créé' in str(message) for message in messages)

    def test_create_evenement_avec_validation(self, client):
        """Test création événement nécessitant validation"""
        user = CustomUserFactory(is_staff=True)
        MembreFactory(utilisateur=user)
        client.force_login(user)
        
        type_evenement = TypeEvenementFactory(necessite_validation=True)
        date_debut = timezone.now() + timedelta(days=30)
        
        form_data = {
            'titre': 'Test Formation',
            'description': 'Description test',
            'type_evenement': type_evenement.id,
            'date_debut': date_debut.strftime('%Y-%m-%dT%H:%M'),
            'lieu': 'Paris',
            'capacite_max': 50,
        }
        
        response = client.post(reverse('evenements:creer'), data=form_data)
        
        evenement = Evenement.objects.get(titre='Test Formation')
        assert evenement.statut == 'en_attente_validation'
        assert ValidationEvenement.objects.filter(evenement=evenement).exists()


@pytest.mark.django_db
@pytest.mark.unit
class TestInscriptionCreateView:
    """Tests pour la vue Inscription à un événement"""

    def test_inscription_access_membre(self, client):
        """Test accès inscription pour membre"""
        user = CustomUserFactory()
        membre = MembreFactory(utilisateur=user)
        client.force_login(user)
        
        evenement = EvenementFactory(statut='publie', inscriptions_ouvertes=True)
        
        response = client.get(reverse('evenements:inscription_creer', 
                                   kwargs={'evenement_pk': evenement.pk}))
        
        assert response.status_code == 200
        assert 'form' in response.context

    def test_inscription_access_non_membre(self, client):
        """Test accès inscription pour non-membre"""
        user = CustomUserFactory()
        # Pas de membre associé
        client.force_login(user)
        
        evenement = EvenementFactory(statut='publie')
        
        response = client.get(reverse('evenements:inscription_creer', 
                                   kwargs={'evenement_pk': evenement.pk}))
        
        assert response.status_code == 302  # Redirection
        
        # Vérifier le message d'erreur
        messages = list(get_messages(response.wsgi_request))
        assert any('membre' in str(message) for message in messages)

    def test_inscription_evenement_ferme(self, client):
        """Test inscription à événement fermé"""
        user = CustomUserFactory()
        membre = MembreFactory(utilisateur=user)
        client.force_login(user)
        
        evenement = EvenementFactory(
            statut='publie',
            inscriptions_ouvertes=False
        )
        
        response = client.get(reverse('evenements:inscription_creer', 
                                   kwargs={'evenement_pk': evenement.pk}))
        
        assert response.status_code == 302  # Redirection
        
        messages = list(get_messages(response.wsgi_request))
        assert any('fermées' in str(message) for message in messages)

    def test_inscription_valide(self, client):
        """Test inscription valide"""
        user = CustomUserFactory()
        membre = MembreFactory(utilisateur=user)
        client.force_login(user)
        
        evenement = EvenementFactory(
            statut='publie',
            inscriptions_ouvertes=True,
            permet_accompagnants=True,
            nombre_max_accompagnants=2
        )
        
        form_data = {
            'nombre_accompagnants': 1,
            'commentaire': 'Test inscription',
            'accepter_conditions': True,
            'accompagnants_data': '[{"nom": "Dupont", "prenom": "Marie", "email": "marie@test.com"}]'
        }
        
        response = client.post(
            reverse('evenements:inscription_creer', kwargs={'evenement_pk': evenement.pk}),
            data=form_data
        )
        
        assert response.status_code == 302  # Redirection après succès
        assert InscriptionEvenement.objects.filter(
            evenement=evenement,
            membre=membre
        ).exists()
        
        inscription = InscriptionEvenement.objects.get(evenement=evenement, membre=membre)
        assert inscription.accompagnants.count() == 1

    def test_inscription_evenement_complet(self, client):
        """Test inscription à événement complet"""
        user = CustomUserFactory()
        membre = MembreFactory(utilisateur=user)
        client.force_login(user)
        
        evenement = EvenementFactory(
            statut='publie',
            inscriptions_ouvertes=True,
            capacite_max=1
        )
        
        # Remplir l'événement
        InscriptionEvenementFactory(evenement=evenement, statut='confirmee')
        
        form_data = {
            'nombre_accompagnants': 0,
            'accepter_conditions': True,
        }
        
        response = client.post(
            reverse('evenements:inscription_creer', kwargs={'evenement_pk': evenement.pk}),
            data=form_data
        )
        
        inscription = InscriptionEvenement.objects.get(evenement=evenement, membre=membre)
        assert inscription.statut == 'liste_attente'


@pytest.mark.django_db
@pytest.mark.unit
class TestConfirmerInscriptionView:
    """Tests pour la confirmation d'inscription"""

    def test_confirmer_inscription_valide(self, client):
        """Test confirmation inscription valide"""
        user = CustomUserFactory()
        membre = MembreFactory(utilisateur=user)
        client.force_login(user)
        
        inscription = InscriptionEvenementFactory(
            membre=membre,
            statut='en_attente'
        )
        
        response = client.post(reverse('evenements:confirmer', 
                                     kwargs={'pk': inscription.pk}))
        
        assert response.status_code == 302
        
        inscription.refresh_from_db()
        assert inscription.statut == 'confirmee'
        assert inscription.date_confirmation is not None

    def test_confirmer_inscription_autre_membre(self, client):
        """Test confirmation inscription d'un autre membre"""
        user = CustomUserFactory()
        MembreFactory(utilisateur=user)
        client.force_login(user)
        
        autre_membre = MembreFactory()
        inscription = InscriptionEvenementFactory(
            membre=autre_membre,
            statut='en_attente'
        )
        
        response = client.post(reverse('evenements:confirmer', 
                                     kwargs={'pk': inscription.pk}))
        
        assert response.status_code == 302
        
        messages = list(get_messages(response.wsgi_request))
        assert any('autorisation' in str(message) for message in messages)


@pytest.mark.django_db
@pytest.mark.unit
class TestValidationListView:
    """Tests pour la liste des validations"""

    def test_validation_liste_staff(self, client):
        """Test accès liste validation pour staff"""
        user = CustomUserFactory(is_staff=True)
        MembreFactory(utilisateur=user)
        client.force_login(user)
        
        validation = ValidationEvenementFactory(statut_validation='en_attente')
        
        response = client.get(reverse('evenements:validation_liste'))
        
        assert response.status_code == 200
        assert validation in response.context['validations']

    def test_validation_liste_non_staff(self, client):
        """Test accès liste validation pour non-staff"""
        user = CustomUserFactory(is_staff=False)
        client.force_login(user)
        
        response = client.get(reverse('evenements:validation_liste'))
        
        assert response.status_code == 403

    def test_approuver_evenement(self, client):
        """Test approbation d'événement"""
        user = CustomUserFactory(is_staff=True)
        MembreFactory(utilisateur=user)
        client.force_login(user)
        
        validation = ValidationEvenementFactory(statut_validation='en_attente')
        
        response = client.post(
            reverse('evenements:approuver', kwargs={'pk': validation.pk}),
            data={'commentaire': 'Événement approuvé'}
        )
        
        assert response.status_code == 302
        
        validation.refresh_from_db()
        assert validation.statut_validation == 'approuve'
        assert validation.evenement.statut == 'publie'

    def test_refuser_evenement(self, client):
        """Test refus d'événement"""
        user = CustomUserFactory(is_staff=True)
        MembreFactory(utilisateur=user)
        client.force_login(user)
        
        validation = ValidationEvenementFactory(statut_validation='en_attente')
        
        response = client.post(
            reverse('evenements:refuser', kwargs={'pk': validation.pk}),
            data={'commentaire': 'Événement non conforme'}
        )
        
        assert response.status_code == 302
        
        validation.refresh_from_db()
        assert validation.statut_validation == 'refuse'
        assert validation.evenement.statut == 'brouillon'


@pytest.mark.django_db
@pytest.mark.unit
class TestAjaxViews:
    """Tests pour les vues AJAX"""

    def test_check_places_disponibles(self, client):
        """Test vérification places disponibles AJAX"""
        user = CustomUserFactory()
        client.force_login(user)
        
        evenement = EvenementFactory(capacite_max=10)
        # Créer 3 inscriptions confirmées
        for _ in range(3):
            InscriptionEvenementFactory(
                evenement=evenement,
                statut='confirmee'
            )
        
        response = client.get(
            reverse('evenements:places_disponibles', kwargs={'pk': evenement.pk}),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['places_disponibles'] == 7
        assert not data['est_complet']

    def test_calculer_tarif_ajax(self, client):
        """Test calcul tarif AJAX"""
        user = CustomUserFactory()
        membre = MembreFactory(utilisateur=user)
        client.force_login(user)
        
        evenement = EvenementFactory(
            est_payant=True,
            tarif_membre=Decimal('25.00')
        )
        
        response = client.get(
            reverse('evenements:calculer_tarif', kwargs={'pk': evenement.pk}),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['success']
        assert data['tarif'] == 25.0

    def test_autocomplete_organisateurs(self, client):
        """Test autocomplétion organisateurs"""
        user = CustomUserFactory(is_staff=True)
        MembreFactory(utilisateur=user)
        client.force_login(user)
        
        # Créer des membres pour l'autocomplétion
        membre1 = MembreFactory(nom='Dupont', prenom='Pierre')
        membre2 = MembreFactory(nom='Martin', prenom='Marie')
        
        response = client.get(
            reverse('evenements:autocomplete_organisateurs'),
            {'q': 'Dupont'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        assert response.status_code == 200
        data = json.loads(response.content)
        assert len(data['results']) >= 1
        assert any('Dupont' in result['text'] for result in data['results'])


@pytest.mark.django_db
@pytest.mark.unit
class TestExportViews:
    """Tests pour les vues d'export"""

    def test_export_inscrits_csv(self, client):
        """Test export CSV des inscrits"""
        user = CustomUserFactory(is_staff=True)
        MembreFactory(utilisateur=user)
        client.force_login(user)
        
        evenement = EvenementFactory()
        inscription = InscriptionEvenementFactory(
            evenement=evenement,
            statut='confirmee'
        )
        
        response = client.get(
            reverse('evenements:export_inscrits', kwargs={'evenement_pk': evenement.pk}),
            {'format': 'csv'}
        )
        
        assert response.status_code == 200
        assert response['Content-Type'] == 'text/csv; charset=utf-8'
        assert inscription.membre.nom.encode() in response.content

    def test_export_inscrits_excel(self, client):
        """Test export Excel des inscrits"""
        user = CustomUserFactory(is_staff=True)
        MembreFactory(utilisateur=user)
        client.force_login(user)
        
        evenement = EvenementFactory()
        InscriptionEvenementFactory(
            evenement=evenement,
            statut='confirmee'
        )
        
        response = client.get(
            reverse('evenements:export_inscrits', kwargs={'evenement_pk': evenement.pk}),
            {'format': 'excel'}
        )
        
        assert response.status_code == 200
        assert 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' in response['Content-Type']

    def test_export_calendrier_ical(self, client):
        """Test export calendrier iCal"""
        user = CustomUserFactory()
        membre = MembreFactory(utilisateur=user)
        client.force_login(user)
        
        evenement = EvenementFactory()
        InscriptionEvenementFactory(
            evenement=evenement,
            membre=membre,
            statut='confirmee'
        )
        
        response = client.get(reverse('evenements:export_calendrier'))
        
        assert response.status_code == 200
        assert response['Content-Type'] == 'text/calendar; charset=utf-8'
        assert b'BEGIN:VCALENDAR' in response.content
        assert evenement.titre.encode() in response.content


@pytest.mark.django_db
@pytest.mark.unit
class TestRapportViews:
    """Tests pour les vues de rapports"""

    def test_rapport_evenements(self, client):
        """Test rapport événements"""
        user = CustomUserFactory(is_staff=True)
        MembreFactory(utilisateur=user)
        client.force_login(user)
        
        # Créer des événements pour les statistiques
        EvenementFactory(statut='publie')
        EvenementFactory(statut='annule')
        
        response = client.get(reverse('evenements:rapport_evenements'))
        
        assert response.status_code == 200
        assert 'stats_generales' in response.context
        assert 'evolution_mensuelle' in response.context

    def test_rapport_avec_periode(self, client):
        """Test rapport avec période spécifique"""
        user = CustomUserFactory(is_staff=True)
        MembreFactory(utilisateur=user)
        client.force_login(user)
        
        response = client.get(
            reverse('evenements:rapport_evenements'),
            {
                'date_debut': '2024-01-01',
                'date_fin': '2024-12-31'
            }
        )
        
        assert response.status_code == 200
        assert response.context['date_debut'].year == 2024


@pytest.mark.django_db
@pytest.mark.unit
class TestPublicViews:
    """Tests pour les vues publiques"""

    def test_evenements_publics(self, client):
        """Test vue publique des événements"""
        # Pas besoin de connexion pour la vue publique
        
        evt_publie = EvenementFactory(
            statut='publie',
            inscriptions_ouvertes=True
        )
        evt_brouillon = EvenementFactory(statut='brouillon')
        
        response = client.get(reverse('evenements:evenements_publics'))
        
        assert response.status_code == 200
        evenements = response.context['evenements']
        assert evt_publie in evenements
        assert evt_brouillon not in evenements

    def test_evenement_public_detail(self, client):
        """Test détail public d'événement"""
        evenement = EvenementFactory(statut='publie')
        
        response = client.get(
            reverse('evenements:evenement_public_detail', kwargs={'pk': evenement.pk})
        )
        
        assert response.status_code == 200
        assert response.context['evenement'] == evenement

    def test_calendrier_public(self, client):
        """Test calendrier public"""
        EvenementFactory(statut='publie')
        
        response = client.get(reverse('evenements:calendrier_public'))
        
        assert response.status_code == 200
        assert 'evenements_json' in response.context


@pytest.mark.django_db
@pytest.mark.unit
class TestCorbeilleViews:
    """Tests pour les vues de corbeille"""

    def test_corbeille_evenements(self, client):
        """Test vue corbeille événements"""
        user = CustomUserFactory(is_staff=True)
        MembreFactory(utilisateur=user)
        client.force_login(user)
        
        # Créer et supprimer un événement
        evenement = EvenementFactory()
        evenement.delete()  # Suppression logique
        
        response = client.get(reverse('evenements:corbeille_evenements'))
        
        assert response.status_code == 200
        assert evenement in response.context['evenements']

    def test_restaurer_evenement(self, client):
        """Test restauration d'événement"""
        user = CustomUserFactory(is_staff=True)
        MembreFactory(utilisateur=user)
        client.force_login(user)
        
        evenement = EvenementFactory()
        evenement.delete()  # Suppression logique
        
        response = client.post(
            reverse('evenements:restaurer_evenement', kwargs={'pk': evenement.pk})
        )
        
        assert response.status_code == 302
        
        evenement.refresh_from_db()
        assert evenement.deleted_at is None
        
        messages = list(get_messages(response.wsgi_request))
        assert any('restauré' in str(message) for message in messages)


@pytest.mark.django_db
@pytest.mark.unit
class TestPermissions:
    """Tests pour les permissions"""

    def test_creation_staff_required(self, client):
        """Test création nécessite staff"""
        user = CustomUserFactory(is_staff=False)
        client.force_login(user)
        
        response = client.get(reverse('evenements:creer'))
        assert response.status_code == 403

    def test_validation_staff_required(self, client):
        """Test validation nécessite staff"""
        user = CustomUserFactory(is_staff=False)
        client.force_login(user)
        
        response = client.get(reverse('evenements:validation_liste'))
        assert response.status_code == 403

    def test_modification_organisateur(self, client):
        """Test modification par organisateur"""
        user = CustomUserFactory(is_staff=False)
        membre = MembreFactory(utilisateur=user)
        client.force_login(user)
        
        evenement = EvenementFactory(organisateur=user)
        
        response = client.get(
            reverse('evenements:modifier', kwargs={'pk': evenement.pk})
        )
        
        assert response.status_code == 200

    def test_modification_non_organisateur(self, client):
        """Test modification par non-organisateur"""
        user = CustomUserFactory(is_staff=False)
        MembreFactory(utilisateur=user)
        client.force_login(user)
        
        autre_user = CustomUserFactory()
        evenement = EvenementFactory(organisateur=autre_user)
        
        response = client.get(
            reverse('evenements:modifier', kwargs={'pk': evenement.pk})
        )
        
        assert response.status_code == 404  # Ne voit pas l'événement


@pytest.mark.django_db
@pytest.mark.unit
class TestEmailConfirmation:
    """Tests pour la confirmation par email"""

    def test_confirmation_email_valide(self, client):
        """Test confirmation par email valide"""
        inscription = InscriptionEvenementFactory(
            statut='en_attente',
            date_limite_confirmation=timezone.now() + timedelta(hours=24)
        )
        
        response = client.get(
            reverse('evenements:confirmer_email', 
                   kwargs={'code': inscription.code_confirmation})
        )
        
        assert response.status_code == 200
        assert inscription in response.context

    def test_confirmation_email_code_invalide(self, client):
        """Test confirmation avec code invalide"""
        response = client.get(
            reverse('evenements:confirmer_email', kwargs={'code': 'INVALID'})
        )
        
        assert response.status_code == 200
        assert 'erreur' in response.context

    def test_confirmation_email_expiree(self, client):
        """Test confirmation expirée"""
        inscription = InscriptionEvenementFactory(
            statut='en_attente',
            date_limite_confirmation=timezone.now() - timedelta(hours=1)
        )
        
        response = client.get(
            reverse('evenements:confirmer_email', 
                   kwargs={'code': inscription.code_confirmation})
        )
        
        assert response.status_code == 200
        assert 'délai' in response.context['erreur']

    def test_confirmation_post_confirmer(self, client):
        """Test POST confirmation"""
        inscription = InscriptionEvenementFactory(
            statut='en_attente',
            date_limite_confirmation=timezone.now() + timedelta(hours=24)
        )
        
        response = client.post(
            reverse('evenements:confirmer_email', 
                   kwargs={'code': inscription.code_confirmation}),
            {'action': 'confirmer'}
        )
        
        assert response.status_code == 200
        inscription.refresh_from_db()
        assert inscription.statut == 'confirmee'

    def test_confirmation_post_refuser(self, client):
        """Test POST refus"""
        inscription = InscriptionEvenementFactory(
            statut='en_attente',
            date_limite_confirmation=timezone.now() + timedelta(hours=24)
        )
        
        response = client.post(
            reverse('evenements:confirmer_email', 
                   kwargs={'code': inscription.code_confirmation}),
            {'action': 'refuser'}
        )
        
        assert response.status_code == 200
        inscription.refresh_from_db()
        assert inscription.statut == 'annulee'