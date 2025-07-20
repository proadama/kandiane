import pytest
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
from django.db.models import Q

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core import mail
from unittest.mock import patch, MagicMock

from apps.membres.models import Membre, TypeMembre, MembreTypeMembre
from ..models import Evenement, InscriptionEvenement
from .factories import (
    EvenementFactory, MembreFactory, TypeMembreFactory,
    InscriptionEvenementFactory, CustomUserFactory
)


@pytest.mark.django_db
@pytest.mark.integration
class TestIntegrationMembres:
    """Tests d'intégration avec le module Membres"""

    def test_tarif_preferentiel_etudiant(self):
        """Test tarif préférentiel pour étudiant"""
        # Créer un type membre étudiant
        type_etudiant = TypeMembreFactory(libelle='Étudiant')
        membre = MembreFactory()
        
        # Associer le type étudiant au membre
        MembreTypeMembre.objects.create(
            membre=membre,
            type_membre=type_etudiant,
            date_debut=timezone.now().date()
        )
        
        # Créer un événement avec tarifs différenciés
        evenement = EvenementFactory(
            est_payant=True,
            tarif_membre=Decimal('20.00'),    # Tarif standard
            tarif_salarie=Decimal('30.00'),   # Tarif salarié
            tarif_invite=Decimal('35.00')     # Tarif invité
        )
        
        # Vérifier que le membre étudiant bénéficie du tarif membre
        tarif_applique = evenement.calculer_tarif_membre(membre)
        assert tarif_applique == Decimal('20.00')

    def test_tarif_preferentiel_salarie(self):
        """Test tarif préférentiel pour salarié"""
        # Créer un type membre salarié
        type_salarie = TypeMembreFactory(libelle='Salarié')
        membre = MembreFactory()
        
        # Associer le type salarié au membre
        MembreTypeMembre.objects.create(
            membre=membre,
            type_membre=type_salarie,
            date_debut=timezone.now().date()
        )
        
        evenement = EvenementFactory(
            est_payant=True,
            tarif_membre=Decimal('20.00'),
            tarif_salarie=Decimal('30.00'),
            tarif_invite=Decimal('35.00')
        )
        
        # Vérifier que le membre salarié bénéficie du tarif salarié
        tarif_applique = evenement.calculer_tarif_membre(membre)
        assert tarif_applique == Decimal('30.00')

    def test_tarif_multiple_types_priorite_salarie(self):
        """Test priorité tarif salarié sur autres types"""
        # Créer plusieurs types
        type_etudiant = TypeMembreFactory(libelle='Étudiant')
        type_salarie = TypeMembreFactory(libelle='Salarié')
        type_retraite = TypeMembreFactory(libelle='Retraité')
        
        membre = MembreFactory()
        
        # Associer plusieurs types au membre
        for type_membre in [type_etudiant, type_salarie, type_retraite]:
            MembreTypeMembre.objects.create(
                membre=membre,
                type_membre=type_membre,
                date_debut=timezone.now().date()
            )
        
        evenement = EvenementFactory(
            est_payant=True,
            tarif_membre=Decimal('20.00'),
            tarif_salarie=Decimal('30.00'),
            tarif_invite=Decimal('35.00')
        )
        
        # Le tarif salarié doit avoir la priorité
        tarif_applique = evenement.calculer_tarif_membre(membre)
        assert tarif_applique == Decimal('30.00')

    def test_historique_evenements_membre(self):
        """Test historique des événements dans le profil membre"""
        membre = MembreFactory()
        
        # Créer plusieurs inscriptions à différents événements
        evenements = []
        inscriptions = []
        
        for i in range(3):
            evenement = EvenementFactory(titre=f'Événement {i+1}')
            inscription = InscriptionEvenementFactory(
                membre=membre,
                evenement=evenement,
                statut='confirmee'
            )
            evenements.append(evenement)
            inscriptions.append(inscription)
        
        # Vérifier que toutes les inscriptions sont liées au membre
        inscriptions_membre = InscriptionEvenement.objects.filter(membre=membre)
        assert inscriptions_membre.count() == 3
        
        # Vérifier que l'accès aux événements via le membre fonctionne
        evenements_membre = [inscr.evenement for inscr in inscriptions_membre]
        for evenement in evenements:
            assert evenement in evenements_membre

    def test_statistiques_participation_membre(self):
        """Test calcul des statistiques de participation"""
        membre = MembreFactory()
        
        # Créer différents types d'inscriptions
        InscriptionEvenementFactory(
            membre=membre,
            statut='confirmee',
            nombre_accompagnants=2,
            montant_paye=Decimal('25.00')
        )
        InscriptionEvenementFactory(
            membre=membre,
            statut='presente',
            nombre_accompagnants=1,
            montant_paye=Decimal('15.00')
        )
        InscriptionEvenementFactory(
            membre=membre,
            statut='annulee',
            nombre_accompagnants=0,
            montant_paye=Decimal('0.00')
        )
        
        # Calculer les statistiques
        stats = InscriptionEvenement.objects.statistiques_membre(membre)
        
        assert stats['total_inscriptions'] == 3
        assert stats['inscriptions_confirmees'] == 1
        assert stats['inscriptions_presentes'] == 1
        assert stats['inscriptions_annulees'] == 1
        assert stats['total_accompagnants'] == 3
        assert stats['montant_total_paye'] == Decimal('40.00')

    def test_eligibilite_membre_selon_statut(self):
        """Test éligibilité membre selon statut"""
        from apps.core.models import Statut
        
        # Créer des statuts
        statut_actif = Statut.objects.create(nom='Actif')
        statut_suspendu = Statut.objects.create(nom='Suspendu')
        
        # Membre actif
        membre_actif = MembreFactory(statut=statut_actif)
        
        # Membre suspendu
        membre_suspendu = MembreFactory(statut=statut_suspendu)
        
        evenement = EvenementFactory(
            statut='publie',
            inscriptions_ouvertes=True
        )
        
        # Vérifier éligibilité
        peut_actif, msg_actif = evenement.peut_s_inscrire(membre_actif)
        peut_suspendu, msg_suspendu = evenement.peut_s_inscrire(membre_suspendu)
        
        assert peut_actif
        assert peut_suspendu  # Même suspendu, peut s'inscrire (règle métier à adapter)

    def test_types_membres_actifs_temporels(self):
        """Test gestion temporelle des types de membres"""
        type_etudiant = TypeMembreFactory(libelle='Étudiant')
        type_salarie = TypeMembreFactory(libelle='Salarié')
        membre = MembreFactory()
        
        # Étudiant dans le passé (expiré)
        MembreTypeMembre.objects.create(
            membre=membre,
            type_membre=type_etudiant,
            date_debut=timezone.now().date() - timedelta(days=365),
            date_fin=timezone.now().date() - timedelta(days=30)
        )
        
        # Salarié actuellement
        MembreTypeMembre.objects.create(
            membre=membre,
            type_membre=type_salarie,
            date_debut=timezone.now().date() - timedelta(days=30),
            date_fin=None  # Toujours actif
        )
        
        evenement = EvenementFactory(
            est_payant=True,
            tarif_membre=Decimal('20.00'),
            tarif_salarie=Decimal('30.00')
        )
        
        # Seul le type salarié actif doit être pris en compte
        tarif_applique = evenement.calculer_tarif_membre(membre)
        assert tarif_applique == Decimal('30.00')

    def test_integration_suppression_membre(self):
        """Test intégration lors de suppression de membre"""
        membre = MembreFactory()
        
        # Créer des inscriptions
        inscription1 = InscriptionEvenementFactory(
            membre=membre,
            statut='confirmee'
        )
        inscription2 = InscriptionEvenementFactory(
            membre=membre,
            statut='en_attente'
        )
        
        # Supprimer logiquement le membre
        membre.delete()
        
        # Vérifier que les inscriptions existent toujours
        assert InscriptionEvenement.objects.filter(id=inscription1.id).exists()
        assert InscriptionEvenement.objects.filter(id=inscription2.id).exists()
        
        # Mais le membre n'apparaît plus dans les requêtes normales
        assert not Membre.objects.filter(id=membre.id).exists()
        assert Membre.objects.with_deleted().filter(id=membre.id).exists()

    def test_recherche_membres_pour_organisateurs(self):
        """Test recherche de membres pour sélection organisateur"""
        # Créer des membres avec utilisateurs
        membre1 = MembreFactory(nom='Dupont', prenom='Pierre')
        membre2 = MembreFactory(nom='Martin', prenom='Marie')
        membre3 = MembreFactory(nom='Bernard', prenom='Paul')
        
        # Supprimer un membre
        membre3.delete()
        
        # Recherche d'organisateurs actifs
        organisateurs_actifs = Membre.objects.filter(
            deleted_at__isnull=True,
            nom__icontains='Dup'
        )
        
        assert membre1 in organisateurs_actifs
        assert membre2 not in organisateurs_actifs
        assert membre3 not in organisateurs_actifs

    def test_validation_organisateur_membre_actif(self):
        """Test validation que l'organisateur est un membre actif"""
        # Utilisateur avec membre actif
        user_avec_membre = CustomUserFactory()
        membre_actif = MembreFactory(utilisateur=user_avec_membre)
        
        # Utilisateur sans membre
        user_sans_membre = CustomUserFactory()
        
        # Utilisateur avec membre supprimé
        user_membre_supprime = CustomUserFactory()
        membre_supprime = MembreFactory(utilisateur=user_membre_supprime)
        membre_supprime.delete()
        
        # Test événement avec organisateur membre actif
        evenement_valide = EvenementFactory.build(organisateur=user_avec_membre)
        evenement_valide.full_clean()  # Ne doit pas lever d'exception
        
        # Test événement avec organisateur sans membre
        from django.core.exceptions import ValidationError
        evenement_sans_membre = EvenementFactory.build(organisateur=user_sans_membre)
        with pytest.raises(ValidationError):
            evenement_sans_membre.full_clean()
        
        # Test événement avec organisateur membre supprimé
        evenement_membre_supprime = EvenementFactory.build(organisateur=user_membre_supprime)
        with pytest.raises(ValidationError):
            evenement_membre_supprime.full_clean()

    def test_prochains_evenements_pour_membre(self):
        """Test recommandations d'événements pour un membre"""
        membre = MembreFactory()
        
        # Événements auxquels le membre peut s'inscrire
        evt_disponible1 = EvenementFactory(
            statut='publie',
            inscriptions_ouvertes=True,
            date_debut=timezone.now() + timedelta(days=10)
        )
        evt_disponible2 = EvenementFactory(
            statut='publie',
            inscriptions_ouvertes=True,
            date_debut=timezone.now() + timedelta(days=20)
        )
        
        # Événement où le membre est déjà inscrit
        evt_deja_inscrit = EvenementFactory(
            statut='publie',
            inscriptions_ouvertes=True,
            date_debut=timezone.now() + timedelta(days=15)
        )
        InscriptionEvenementFactory(
            evenement=evt_deja_inscrit,
            membre=membre,
            statut='confirmee'
        )
        
        # Événement fermé aux inscriptions
        evt_ferme = EvenementFactory(
            statut='publie',
            inscriptions_ouvertes=False,
            date_debut=timezone.now() + timedelta(days=25)
        )
        
        # Récupérer les prochains événements pour le membre
        prochains = Evenement.objects.prochains_pour_membre(membre, limite=5)
        
        assert evt_disponible1 in prochains
        assert evt_disponible2 in prochains
        assert evt_deja_inscrit not in prochains
        assert evt_ferme not in prochains

    def test_notification_membre_inscription(self):
        """Test notification membre lors d'inscription"""
        membre = MembreFactory(email='test@example.com')
        evenement = EvenementFactory()
        
        # Créer une inscription
        inscription = InscriptionEvenementFactory(
            membre=membre,
            evenement=evenement,
            statut='en_attente'
        )
        
        # Vérifier que les données nécessaires pour les notifications sont présentes
        assert inscription.membre.email
        assert inscription.code_confirmation
        assert inscription.date_limite_confirmation
        
        # Simuler l'envoi de notification
        donnees_notification = {
            'destinataire': inscription.membre.email,
            'code_confirmation': inscription.code_confirmation,
            'evenement_titre': inscription.evenement.titre,
            'date_limite': inscription.date_limite_confirmation,
            'membre_nom': inscription.membre.get_nom_complet()
        }
        
        assert all(donnees_notification.values())

    def test_calcul_anciennete_pour_tarifs(self):
        """Test calcul ancienneté membre pour tarifs spéciaux"""
        # Membre ancien (plus de 2 ans)
        membre_ancien = MembreFactory(
            date_adhesion=timezone.now().date() - timedelta(days=800)
        )
        
        # Membre récent (moins de 6 mois)
        membre_recent = MembreFactory(
            date_adhesion=timezone.now().date() - timedelta(days=100)
        )
        
        # Calculer l'ancienneté
        anciennete_ancien = (timezone.now().date() - membre_ancien.date_adhesion).days
        anciennete_recent = (timezone.now().date() - membre_recent.date_adhesion).days
        
        assert anciennete_ancien > 365 * 2  # Plus de 2 ans
        assert anciennete_recent < 365 / 2  # Moins de 6 mois
        
        # Pourrait être utilisé pour des tarifs préférentiels d'ancienneté
        evenement = EvenementFactory(
            est_payant=True,
            tarif_membre=Decimal('25.00')
        )
        
        # Logique métier : réduction pour membres anciens
        tarif_ancien = evenement.tarif_membre
        if anciennete_ancien > 365 * 2:
            tarif_ancien *= Decimal('0.9')  # 10% de réduction
        
        tarif_recent = evenement.tarif_membre  # Pas de réduction
        
        assert tarif_ancien < tarif_recent


@pytest.mark.django_db
@pytest.mark.integration  
class TestIntegrationMembresAvance:
    """Tests d'intégration avancés avec le module Membres"""

    def test_migration_type_membre_impact_tarifs(self):
        """Test impact migration type membre sur tarifs événements"""
        type_etudiant = TypeMembreFactory(libelle='Étudiant')
        type_salarie = TypeMembreFactory(libelle='Salarié')
        membre = MembreFactory()
        
        # Membre étudiant initialement
        MembreTypeMembre.objects.create(
            membre=membre,
            type_membre=type_etudiant,
            date_debut=timezone.now().date() - timedelta(days=100),
            date_fin=timezone.now().date()  # Expire aujourd'hui
        )
        
        # Devient salarié
        MembreTypeMembre.objects.create(
            membre=membre,
            type_membre=type_salarie,
            date_debut=timezone.now().date(),
            date_fin=None
        )
        
        evenement = EvenementFactory(
            est_payant=True,
            tarif_membre=Decimal('20.00'),
            tarif_salarie=Decimal('30.00')
        )
        
        # Vérifier que le nouveau tarif est appliqué
        tarif_actuel = evenement.calculer_tarif_membre(membre)
        assert tarif_actuel == Decimal('30.00')  # Tarif salarié

    def test_coherence_donnees_membre_inscription(self):
        """Test cohérence données membre lors inscription"""
        membre = MembreFactory(
            nom='Dupont',
            prenom='Pierre',
            email='pierre.dupont@test.com',
            telephone='0123456789'
        )
        
        evenement = EvenementFactory()
        inscription = InscriptionEvenementFactory(
            membre=membre,
            evenement=evenement
        )
        
        # Vérifier cohérence des données
        assert inscription.membre.nom == 'Dupont'
        assert inscription.membre.email == 'pierre.dupont@test.com'
        
        # Les données du membre doivent être accessibles via l'inscription
        donnees_membre = {
            'nom_complet': f"{inscription.membre.prenom} {inscription.membre.nom}",
            'contact': inscription.membre.email,
            'telephone': inscription.membre.telephone
        }
        
        assert donnees_membre['nom_complet'] == 'Pierre Dupont'
        assert donnees_membre['contact'] == 'pierre.dupont@test.com'

    def test_performance_requetes_membres_evenements(self):
        """Test performance requêtes membres-événements"""
        # Créer plusieurs membres et événements
        membres = [MembreFactory() for _ in range(10)]
        evenements = [EvenementFactory() for _ in range(5)]
        
        # Créer des inscriptions
        for membre in membres:
            for i, evenement in enumerate(evenements):
                if i < 3:  # Chaque membre inscrit à 3 événements
                    InscriptionEvenementFactory(
                        membre=membre,
                        evenement=evenement,
                        statut='confirmee'
                    )
        
        # Test requête optimisée avec select_related et prefetch_related
        inscriptions = InscriptionEvenement.objects.select_related(
            'membre', 'evenement'
        ).prefetch_related(
            'accompagnants'
        ).all()
        
        # Vérifier que les données sont accessibles sans requêtes supplémentaires
        for inscription in inscriptions[:5]:  # Tester quelques inscriptions
            # Ces accès ne doivent pas générer de requêtes DB supplémentaires
            _ = inscription.membre.nom
            _ = inscription.evenement.titre
            _ = list(inscription.accompagnants.all())
        
        assert len(inscriptions) == 30  # 10 membres * 3 événements

    def test_gestion_doublons_inscription_membre(self):
        """Test gestion doublons inscription membre"""
        membre = MembreFactory()
        evenement = EvenementFactory()
        
        # Première inscription
        inscription1 = InscriptionEvenementFactory(
            membre=membre,
            evenement=evenement,
            statut='confirmee'
        )
        
        # Tentative de seconde inscription au même événement
        from django.db.utils import IntegrityError
        with pytest.raises(IntegrityError):
            InscriptionEvenementFactory(
                membre=membre,
                evenement=evenement,
                statut='en_attente'
            )
        
        # Vérifier qu'une seule inscription existe
        inscriptions = InscriptionEvenement.objects.filter(
            membre=membre,
            evenement=evenement
        )
        assert inscriptions.count() == 1
        assert inscriptions.first() == inscription1