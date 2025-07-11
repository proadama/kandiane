import pytest
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
from django.db.models import Q

from ..models import (
    TypeEvenement, Evenement, InscriptionEvenement,
    ValidationEvenement, EvenementRecurrence
)
from .factories import (
    TypeEvenementFactory, EvenementFactory, MembreFactory,
    InscriptionEvenementFactory, ValidationEvenementFactory,
    CustomUserFactory, EvenementCompletFactory
)


@pytest.mark.django_db
@pytest.mark.unit
class TestTypeEvenementManager:
    """Tests unitaires pour TypeEvenementManager"""

    def test_actifs(self):
        """Test récupération types actifs"""
        # Créer des types actifs
        type1 = TypeEvenementFactory()
        type2 = TypeEvenementFactory()
        
        # Créer un type supprimé
        type_supprime = TypeEvenementFactory()
        type_supprime.delete()
        
        actifs = TypeEvenement.objects.actifs()
        
        assert type1 in actifs
        assert type2 in actifs
        assert type_supprime not in actifs

    def test_necessitant_validation(self):
        """Test types nécessitant validation"""
        type_avec_validation = TypeEvenementFactory(necessite_validation=True)
        type_sans_validation = TypeEvenementFactory(necessite_validation=False)
        
        types_validation = TypeEvenement.objects.necessitant_validation()
        
        assert type_avec_validation in types_validation
        assert type_sans_validation not in types_validation

    def test_permettant_accompagnants(self):
        """Test types permettant accompagnants"""
        type_avec_accomp = TypeEvenementFactory(permet_accompagnants=True)
        type_sans_accomp = TypeEvenementFactory(permet_accompagnants=False)
        
        types_accompagnants = TypeEvenement.objects.permettant_accompagnants()
        
        assert type_avec_accomp in types_accompagnants
        assert type_sans_accomp not in types_accompagnants

    def test_par_ordre_affichage(self):
        """Test tri par ordre d'affichage"""
        type1 = TypeEvenementFactory(ordre_affichage=3, libelle="C")
        type2 = TypeEvenementFactory(ordre_affichage=1, libelle="A")
        type3 = TypeEvenementFactory(ordre_affichage=2, libelle="B")
        
        types_ordonnes = list(TypeEvenement.objects.par_ordre_affichage())
        
        assert types_ordonnes[0] == type2  # ordre 1
        assert types_ordonnes[1] == type3  # ordre 2
        assert types_ordonnes[2] == type1  # ordre 3


@pytest.mark.django_db
@pytest.mark.unit
class TestEvenementManager:
    """Tests unitaires pour EvenementManager"""

    def test_publies(self):
        """Test événements publiés"""
        evt_publie = EvenementFactory(statut='publie')
        evt_brouillon = EvenementFactory(statut='brouillon')
        evt_annule = EvenementFactory(statut='annule')
        
        publies = Evenement.objects.publies()
        
        assert evt_publie in publies
        assert evt_brouillon not in publies
        assert evt_annule not in publies

    def test_a_venir(self):
        """Test événements à venir"""
        # Événement futur
        evt_futur = EvenementFactory(
            date_debut=timezone.now() + timedelta(days=10)
        )
        
        # Événement passé
        evt_passe = EvenementFactory(
            date_debut=timezone.now() - timedelta(days=10),
            date_fin=timezone.now() - timedelta(days=9)
        )
        
        a_venir = Evenement.objects.a_venir()
        
        assert evt_futur in a_venir
        assert evt_passe not in a_venir

    def test_en_cours(self):
        """Test événements en cours"""
        maintenant = timezone.now()
        
        # Événement en cours
        evt_en_cours = EvenementFactory(
            date_debut=maintenant - timedelta(hours=1),
            date_fin=maintenant + timedelta(hours=1)
        )
        
        # Événement futur
        evt_futur = EvenementFactory(
            date_debut=maintenant + timedelta(hours=1)
        )
        
        en_cours = Evenement.objects.en_cours()
        
        assert evt_en_cours in en_cours
        assert evt_futur not in en_cours

    def test_passes(self):
        """Test événements passés"""
        maintenant = timezone.now()
        
        # Événement passé
        evt_passe = EvenementFactory(
            date_debut=maintenant - timedelta(days=2),
            date_fin=maintenant - timedelta(days=1)
        )
        
        # Événement futur
        evt_futur = EvenementFactory(
            date_debut=maintenant + timedelta(days=1)
        )
        
        passes = Evenement.objects.passes()
        
        assert evt_passe in passes
        assert evt_futur not in passes

    def test_inscriptions_ouvertes(self):
        """Test événements avec inscriptions ouvertes"""
        maintenant = timezone.now()
        
        # Inscriptions ouvertes
        evt_ouvert = EvenementFactory(
            statut='publie',
            inscriptions_ouvertes=True,
            date_ouverture_inscriptions=maintenant - timedelta(days=1),
            date_fermeture_inscriptions=maintenant + timedelta(days=1)
        )
        
        # Inscriptions fermées
        evt_ferme = EvenementFactory(
            inscriptions_ouvertes=False
        )
        
        # Pas encore ouvert
        evt_pas_ouvert = EvenementFactory(
            statut='publie',
            inscriptions_ouvertes=True,
            date_ouverture_inscriptions=maintenant + timedelta(days=1)
        )
        
        ouverts = Evenement.objects.inscriptions_ouvertes()
        
        assert evt_ouvert in ouverts
        assert evt_ferme not in ouverts
        assert evt_pas_ouvert not in ouverts

    def test_avec_places_disponibles(self):
        """Test événements avec places disponibles"""
        # Événement avec places
        evt_places = EvenementFactory(capacite_max=10)
        for _ in range(3):
            InscriptionEvenementFactory(
                evenement=evt_places,
                statut='confirmee'
            )
        
        # Événement complet
        evt_complet = EvenementFactory(capacite_max=2)
        for _ in range(2):
            InscriptionEvenementFactory(
                evenement=evt_complet,
                statut='confirmee'
            )
        
        avec_places = Evenement.objects.avec_places_disponibles()
        
        assert evt_places in avec_places
        assert evt_complet not in avec_places

    def test_complets(self):
        """Test événements complets"""
        # Événement complet
        evt_complet = EvenementFactory(capacite_max=2)
        for _ in range(2):
            InscriptionEvenementFactory(
                evenement=evt_complet,
                statut='confirmee'
            )
        
        # Événement avec places
        evt_places = EvenementFactory(capacite_max=10)
        InscriptionEvenementFactory(
            evenement=evt_places,
            statut='confirmee'
        )
        
        complets = Evenement.objects.complets()
        
        assert evt_complet in complets
        assert evt_places not in complets

    def test_par_type_string(self):
        """Test filtrage par type (string)"""
        type_formation = TypeEvenementFactory(libelle="Formation Python")
        type_reunion = TypeEvenementFactory(libelle="Réunion")
        
        evt_formation = EvenementFactory(type_evenement=type_formation)
        evt_reunion = EvenementFactory(type_evenement=type_reunion)
        
        formations = Evenement.objects.par_type("Formation")
        
        assert evt_formation in formations
        assert evt_reunion not in formations

    def test_par_type_objet(self):
        """Test filtrage par type (objet)"""
        type_formation = TypeEvenementFactory(libelle="Formation")
        type_reunion = TypeEvenementFactory(libelle="Réunion")
        
        evt_formation = EvenementFactory(type_evenement=type_formation)
        evt_reunion = EvenementFactory(type_evenement=type_reunion)
        
        formations = Evenement.objects.par_type(type_formation)
        
        assert evt_formation in formations
        assert evt_reunion not in formations

    def test_par_organisateur(self):
        """Test filtrage par organisateur"""
        org1 = CustomUserFactory()
        org2 = CustomUserFactory()
        
        evt1 = EvenementFactory(organisateur=org1)
        evt2 = EvenementFactory(organisateur=org2)
        
        evt_org1 = Evenement.objects.par_organisateur(org1)
        
        assert evt1 in evt_org1
        assert evt2 not in evt_org1

    def test_par_lieu(self):
        """Test filtrage par lieu"""
        evt_paris = EvenementFactory(lieu="Paris", adresse_complete="75001 Paris")
        evt_lyon = EvenementFactory(lieu="Lyon", adresse_complete="69001 Lyon")
        
        evt_avec_paris = Evenement.objects.par_lieu("Paris")
        
        assert evt_paris in evt_avec_paris
        assert evt_lyon not in evt_avec_paris

    def test_par_periode(self):
        """Test filtrage par période"""
        date_debut = timezone.now().date()
        date_fin = date_debut + timedelta(days=10)
        
        # Événement dans la période
        evt_dans_periode = EvenementFactory(
            date_debut=timezone.make_aware(
                timezone.datetime.combine(date_debut + timedelta(days=5), timezone.datetime.min.time())
            )
        )
        
        # Événement hors période
        evt_hors_periode = EvenementFactory(
            date_debut=timezone.make_aware(
                timezone.datetime.combine(date_debut + timedelta(days=15), timezone.datetime.min.time())
            )
        )
        
        evt_periode = Evenement.objects.par_periode(date_debut, date_fin)
        
        assert evt_dans_periode in evt_periode
        assert evt_hors_periode not in evt_periode

    def test_payants_gratuits(self):
        """Test filtrage payants/gratuits"""
        evt_payant = EvenementFactory(est_payant=True)
        evt_gratuit = EvenementFactory(est_payant=False)
        
        payants = Evenement.objects.payants()
        gratuits = Evenement.objects.gratuits()
        
        assert evt_payant in payants
        assert evt_payant not in gratuits
        assert evt_gratuit in gratuits
        assert evt_gratuit not in payants

    def test_recurrents(self):
        """Test filtrage récurrents"""
        evt_recurrent = EvenementFactory(est_recurrent=True)
        evt_simple = EvenementFactory(est_recurrent=False)
        
        recurrents = Evenement.objects.recurrents()
        non_recurrents = Evenement.objects.non_recurrents()
        
        assert evt_recurrent in recurrents
        assert evt_recurrent not in non_recurrents
        assert evt_simple in non_recurrents
        assert evt_simple not in recurrents

    def test_recherche(self):
        """Test recherche textuelle"""
        evt1 = EvenementFactory(
            titre="Formation Python",
            description="Apprendre le langage Python",
            lieu="Paris"
        )
        evt2 = EvenementFactory(
            titre="Réunion Java",
            description="Discussion sur Java",
            lieu="Lyon"
        )
        
        # Recherche par titre
        resultats_python = Evenement.objects.recherche("Python")
        assert evt1 in resultats_python
        assert evt2 not in resultats_python
        
        # Recherche par lieu
        resultats_paris = Evenement.objects.recherche("Paris")
        assert evt1 in resultats_paris
        assert evt2 not in resultats_paris

    def test_avec_statistiques(self):
        """Test ajout statistiques"""
        evenement = EvenementFactory()
        
        # Créer diverses inscriptions
        InscriptionEvenementFactory(evenement=evenement, statut='confirmee')
        InscriptionEvenementFactory(evenement=evenement, statut='en_attente')
        InscriptionEvenementFactory(evenement=evenement, statut='liste_attente')
        InscriptionEvenementFactory(evenement=evenement, statut='annulee')
        
        evt_avec_stats = Evenement.objects.avec_statistiques().get(id=evenement.id)
        
        assert hasattr(evt_avec_stats, 'total_inscriptions')
        assert hasattr(evt_avec_stats, 'inscriptions_confirmees')
        assert hasattr(evt_avec_stats, 'inscriptions_en_attente')
        assert hasattr(evt_avec_stats, 'taux_occupation')
        
        assert evt_avec_stats.total_inscriptions == 4
        assert evt_avec_stats.inscriptions_confirmees == 1
        assert evt_avec_stats.inscriptions_en_attente == 1

    def test_necessitant_validation(self):
        """Test événements nécessitant validation"""
        type_avec_validation = TypeEvenementFactory(necessite_validation=True)
        type_sans_validation = TypeEvenementFactory(necessite_validation=False)
        
        evt_a_valider = EvenementFactory(
            type_evenement=type_avec_validation,
            statut='en_attente_validation'
        )
        evt_sans_validation = EvenementFactory(
            type_evenement=type_sans_validation,
            statut='publie'
        )
        
        a_valider = Evenement.objects.necessitant_validation()
        
        assert evt_a_valider in a_valider
        assert evt_sans_validation not in a_valider

    def test_prochains_pour_membre(self):
        """Test prochains événements pour un membre"""
        membre = MembreFactory()
        
        # Événement disponible
        evt_disponible = EvenementFactory(
            statut='publie',
            inscriptions_ouvertes=True,
            date_debut=timezone.now() + timedelta(days=10)
        )
        
        # Événement où le membre est déjà inscrit
        evt_inscrit = EvenementFactory(
            statut='publie',
            inscriptions_ouvertes=True,
            date_debut=timezone.now() + timedelta(days=5)
        )
        InscriptionEvenementFactory(
            evenement=evt_inscrit,
            membre=membre,
            statut='confirmee'
        )
        
        prochains = Evenement.objects.prochains_pour_membre(membre, limite=5)
        
        assert evt_disponible in prochains
        assert evt_inscrit not in prochains

    def test_statistiques_periode(self):
        """Test statistiques sur une période"""
        date_debut = timezone.now().date()
        date_fin = date_debut + timedelta(days=30)
        
        # Événements dans la période
        evt_dans_periode = EvenementFactory(
            date_debut=timezone.make_aware(
                timezone.datetime.combine(date_debut + timedelta(days=5), timezone.datetime.min.time())
            ),
            statut='publie'
        )
        
        # Événement hors période
        EvenementFactory(
            date_debut=timezone.make_aware(
                timezone.datetime.combine(date_debut + timedelta(days=40), timezone.datetime.min.time())
            )
        )
        
        stats = Evenement.objects.statistiques_periode(date_debut, date_fin)
        
        assert 'total_evenements' in stats
        assert 'evenements_publies' in stats
        assert stats['total_evenements'] >= 1


@pytest.mark.django_db
@pytest.mark.unit
class TestInscriptionEvenementManager:
    """Tests unitaires pour InscriptionEvenementManager"""

    def test_statuts_filtres(self):
        """Test filtres par statut"""
        inscr_attente = InscriptionEvenementFactory(statut='en_attente')
        inscr_confirmee = InscriptionEvenementFactory(statut='confirmee')
        inscr_liste = InscriptionEvenementFactory(statut='liste_attente')
        inscr_annulee = InscriptionEvenementFactory(statut='annulee')
        
        # Test filtres individuels
        assert inscr_attente in InscriptionEvenement.objects.en_attente()
        assert inscr_confirmee in InscriptionEvenement.objects.confirmees()
        assert inscr_liste in InscriptionEvenement.objects.liste_attente()
        assert inscr_annulee in InscriptionEvenement.objects.annulees()
        
        # Test filtres groupés
        actives = InscriptionEvenement.objects.actives()
        assert inscr_attente in actives
        assert inscr_confirmee in actives
        assert inscr_annulee not in actives

    def test_par_evenement_membre(self):
        """Test filtres par événement et membre"""
        evenement = EvenementFactory()
        membre = MembreFactory()
        
        inscr_target = InscriptionEvenementFactory(
            evenement=evenement,
            membre=membre
        )
        inscr_autre = InscriptionEvenementFactory()
        
        # Filtrage par événement
        inscr_evt = InscriptionEvenement.objects.par_evenement(evenement)
        assert inscr_target in inscr_evt
        assert inscr_autre not in inscr_evt
        
        # Filtrage par membre
        inscr_mbr = InscriptionEvenement.objects.par_membre(membre)
        assert inscr_target in inscr_mbr
        assert inscr_autre not in inscr_mbr

    def test_en_retard_confirmation(self):
        """Test inscriptions en retard de confirmation"""
        # Inscription en retard
        inscr_retard = InscriptionEvenementFactory(
            statut='en_attente',
            date_limite_confirmation=timezone.now() - timedelta(hours=1)
        )
        
        # Inscription dans les temps
        inscr_temps = InscriptionEvenementFactory(
            statut='en_attente',
            date_limite_confirmation=timezone.now() + timedelta(hours=1)
        )
        
        en_retard = InscriptionEvenement.objects.en_retard_confirmation()
        
        assert inscr_retard in en_retard
        assert inscr_temps not in en_retard

    def test_a_confirmer_dans(self):
        """Test inscriptions à confirmer dans X heures"""
        maintenant = timezone.now()
        
        # Inscription à confirmer dans 2h
        inscr_2h = InscriptionEvenementFactory(
            statut='en_attente',
            date_limite_confirmation=maintenant + timedelta(hours=2)
        )
        
        # Inscription à confirmer dans 48h
        inscr_48h = InscriptionEvenementFactory(
            statut='en_attente',
            date_limite_confirmation=maintenant + timedelta(hours=48)
        )
        
        a_confirmer_24h = InscriptionEvenement.objects.a_confirmer_dans(24)
        
        assert inscr_2h in a_confirmer_24h
        assert inscr_48h not in a_confirmer_24h

    def test_avec_sans_accompagnants(self):
        """Test filtres accompagnants"""
        inscr_avec = InscriptionEvenementFactory(nombre_accompagnants=2)
        inscr_sans = InscriptionEvenementFactory(nombre_accompagnants=0)
        
        avec_accompagnants = InscriptionEvenement.objects.avec_accompagnants()
        sans_accompagnants = InscriptionEvenement.objects.sans_accompagnants()
        
        assert inscr_avec in avec_accompagnants
        assert inscr_avec not in sans_accompagnants
        assert inscr_sans in sans_accompagnants
        assert inscr_sans not in avec_accompagnants

    def test_avec_details_paiement(self):
        """Test annotation détails paiement"""
        evenement = EvenementFactory(
            est_payant=True,
            tarif_membre=Decimal('50.00'),
            tarif_invite=Decimal('25.00')
        )
        
        inscription = InscriptionEvenementFactory(
            evenement=evenement,
            nombre_accompagnants=1,
            montant_paye=Decimal('30.00')
        )
        
        avec_details = InscriptionEvenement.objects.avec_details_paiement().get(
            id=inscription.id
        )
        
        assert hasattr(avec_details, 'montant_total_attendu')
        assert hasattr(avec_details, 'montant_restant_calculé')
        assert avec_details.montant_total_attendu == Decimal('75.00')  # 50 + 25
        assert avec_details.montant_restant_calculé == Decimal('45.00')  # 75 - 30

    def test_statistiques_membre(self):
        """Test statistiques pour un membre"""
        membre = MembreFactory()
        
        # Créer diverses inscriptions
        InscriptionEvenementFactory(
            membre=membre,
            statut='confirmee',
            nombre_accompagnants=2,
            montant_paye=Decimal('50.00')
        )
        InscriptionEvenementFactory(
            membre=membre,
            statut='annulee',
            nombre_accompagnants=1,
            montant_paye=Decimal('25.00')
        )
        
        stats = InscriptionEvenement.objects.statistiques_membre(membre)
        
        assert stats['total_inscriptions'] == 2
        assert stats['inscriptions_confirmees'] == 1
        assert stats['inscriptions_annulees'] == 1
        assert stats['total_accompagnants'] == 3
        assert stats['montant_total_paye'] == Decimal('75.00')

    def test_nettoyer_inscriptions_expirees(self):
        """Test nettoyage inscriptions expirées"""
        # Inscription expirée
        inscr_expiree = InscriptionEvenementFactory(
            statut='en_attente',
            date_limite_confirmation=timezone.now() - timedelta(hours=2)
        )
        
        # Inscription valide
        inscr_valide = InscriptionEvenementFactory(
            statut='en_attente',
            date_limite_confirmation=timezone.now() + timedelta(hours=2)
        )
        
        count = InscriptionEvenement.objects.nettoyer_inscriptions_expirees()
        
        assert count == 1
        
        inscr_expiree.refresh_from_db()
        inscr_valide.refresh_from_db()
        
        assert inscr_expiree.statut == 'expiree'
        assert inscr_valide.statut == 'en_attente'


@pytest.mark.django_db
@pytest.mark.unit
class TestValidationEvenementManager:
    """Tests unitaires pour ValidationEvenementManager"""

    def test_filtres_statut_validation(self):
        """Test filtres par statut de validation"""
        valid_attente = ValidationEvenementFactory(statut_validation='en_attente')
        valid_approuvee = ValidationEvenementFactory(statut_validation='approuve')
        valid_refusee = ValidationEvenementFactory(statut_validation='refuse')
        
        assert valid_attente in ValidationEvenement.objects.en_attente()
        assert valid_approuvee in ValidationEvenement.objects.approuvees()
        assert valid_refusee in ValidationEvenement.objects.refusees()

    def test_par_validateur(self):
        """Test filtre par validateur"""
        validateur = CustomUserFactory()
        autre_validateur = CustomUserFactory()
        
        valid_validateur = ValidationEvenementFactory(validateur=validateur)
        valid_autre = ValidationEvenementFactory(validateur=autre_validateur)
        
        validations_validateur = ValidationEvenement.objects.par_validateur(validateur)
        
        assert valid_validateur in validations_validateur
        assert valid_autre not in validations_validateur

    def test_urgentes(self):
        """Test validations urgentes"""
        # Événement dans 3 jours (urgent)
        evt_urgent = EvenementFactory(
            date_debut=timezone.now() + timedelta(days=3),
            statut='en_attente_validation'
        )
        valid_urgente = ValidationEvenementFactory(
            evenement=evt_urgent,
            statut_validation='en_attente'
        )
        
        # Événement dans 30 jours (non urgent)
        evt_normal = EvenementFactory(
            date_debut=timezone.now() + timedelta(days=30),
            statut='en_attente_validation'
        )
        valid_normale = ValidationEvenementFactory(
            evenement=evt_normal,
            statut_validation='en_attente'
        )
        
        urgentes = ValidationEvenement.objects.urgentes(jours=7)
        
        assert valid_urgente in urgentes
        assert valid_normale not in urgentes

    def test_statistiques_validateur(self):
        """Test statistiques pour un validateur"""
        validateur = CustomUserFactory()
        
        # Créer diverses validations
        ValidationEvenementFactory(
            validateur=validateur,
            statut_validation='approuve'
        )
        ValidationEvenementFactory(
            validateur=validateur,
            statut_validation='refuse'
        )
        ValidationEvenementFactory(
            validateur=validateur,
            statut_validation='en_attente'
        )
        
        stats = ValidationEvenement.objects.statistiques_validateur(validateur)
        
        assert stats['total_validations'] == 3
        assert stats['validations_approuvees'] == 1
        assert stats['validations_refusees'] == 1
        assert stats['validations_en_attente'] == 1