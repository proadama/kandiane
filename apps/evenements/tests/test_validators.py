import pytest
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
from django.core.exceptions import ValidationError

from ..validators import (
    validate_date_evenement, validate_date_fin_evenement,
    validate_capacite_coherente, validate_organisateur_membre,
    validate_dates_inscriptions, validate_tarifs_coherents,
    validate_accompagnants_coherents, validate_recurrence_coherente,
    validate_delai_confirmation, validate_inscription_possible,
    validate_sessions_coherentes, validate_montant_paiement,
    validate_periode_recherche, validate_code_couleur,
    validate_capacite_session, validate_donnees_accompagnant
)
from .factories import (
    EvenementFactory, MembreFactory, CustomUserFactory,
    InscriptionEvenementFactory, TypeEvenementFactory,
    SessionEvenementFactory
)


@pytest.mark.django_db
@pytest.mark.unit
class TestValidateDateEvenement:
    """Tests pour validate_date_evenement"""

    def test_date_future_valide(self):
        """Test date future valide"""
        date_future = timezone.now() + timedelta(days=1)
        # Ne doit pas lever d'exception
        validate_date_evenement(date_future)

    def test_date_passee_invalide(self):
        """Test date passée invalide"""
        date_passee = timezone.now() - timedelta(days=1)
        
        with pytest.raises(ValidationError) as exc_info:
            validate_date_evenement(date_passee)
        
        assert 'futur' in str(exc_info.value)
        assert exc_info.value.code == 'date_passee'

    def test_date_maintenant_invalide(self):
        """Test date actuelle invalide"""
        maintenant = timezone.now()
        
        with pytest.raises(ValidationError):
            validate_date_evenement(maintenant)


@pytest.mark.django_db
@pytest.mark.unit
class TestValidateDateFinEvenement:
    """Tests pour validate_date_fin_evenement"""

    def test_date_fin_posterieure_valide(self):
        """Test date fin postérieure valide"""
        date_debut = timezone.now() + timedelta(days=1)
        date_fin = date_debut + timedelta(hours=2)
        
        # Ne doit pas lever d'exception
        validate_date_fin_evenement(date_debut, date_fin)

    def test_date_fin_anterieure_invalide(self):
        """Test date fin antérieure invalide"""
        date_debut = timezone.now() + timedelta(days=1)
        date_fin = date_debut - timedelta(hours=1)
        
        with pytest.raises(ValidationError) as exc_info:
            validate_date_fin_evenement(date_debut, date_fin)
        
        assert 'postérieure' in str(exc_info.value)
        assert exc_info.value.code == 'date_fin_invalide'

    def test_date_fin_egale_invalide(self):
        """Test date fin égale invalide"""
        date_debut = timezone.now() + timedelta(days=1)
        date_fin = date_debut
        
        with pytest.raises(ValidationError):
            validate_date_fin_evenement(date_debut, date_fin)

    def test_date_fin_none_valide(self):
        """Test date fin None valide"""
        date_debut = timezone.now() + timedelta(days=1)
        
        # Ne doit pas lever d'exception
        validate_date_fin_evenement(date_debut, None)


@pytest.mark.django_db
@pytest.mark.unit
class TestValidateCapaciteCoherente:
    """Tests pour validate_capacite_coherente"""

    def test_capacite_positive_valide(self):
        """Test capacité positive valide"""
        # Ne doit pas lever d'exception
        validate_capacite_coherente(50)

    def test_capacite_zero_invalide(self):
        """Test capacité zéro invalide"""
        with pytest.raises(ValidationError) as exc_info:
            validate_capacite_coherente(0)
        
        assert 'supérieure à 0' in str(exc_info.value)
        assert exc_info.value.code == 'capacite_invalide'

    def test_capacite_negative_invalide(self):
        """Test capacité négative invalide"""
        with pytest.raises(ValidationError):
            validate_capacite_coherente(-5)

    def test_capacite_avec_inscriptions_existantes(self):
        """Test capacité avec inscriptions existantes"""
        evenement = EvenementFactory(capacite_max=10)
        
        # Créer 5 inscriptions confirmées
        for _ in range(5):
            InscriptionEvenementFactory(
                evenement=evenement,
                statut='confirmee'
            )
        
        # Capacité >= inscriptions confirmées : OK
        validate_capacite_coherente(5, evenement.id)
        validate_capacite_coherente(10, evenement.id)
        
        # Capacité < inscriptions confirmées : Erreur
        with pytest.raises(ValidationError) as exc_info:
            validate_capacite_coherente(3, evenement.id)
        
        assert 'inscriptions confirmées' in str(exc_info.value)
        assert exc_info.value.code == 'capacite_insuffisante'


@pytest.mark.django_db
@pytest.mark.unit
class TestValidateOrganisateurMembre:
    """Tests pour validate_organisateur_membre"""

    def test_organisateur_membre_actif_valide(self):
        """Test organisateur membre actif valide"""
        user = CustomUserFactory()
        MembreFactory(utilisateur=user)  # Membre actif
        
        # Ne doit pas lever d'exception
        validate_organisateur_membre(user)

    def test_organisateur_non_membre_invalide(self):
        """Test organisateur non membre invalide"""
        user = CustomUserFactory()
        # Pas de membre associé
        
        with pytest.raises(ValidationError) as exc_info:
            validate_organisateur_membre(user)
        
        assert 'membre de l\'association' in str(exc_info.value)
        assert exc_info.value.code == 'organisateur_non_membre'

    def test_organisateur_membre_inactif_invalide(self):
        """Test organisateur membre inactif invalide"""
        user = CustomUserFactory()
        membre = MembreFactory(utilisateur=user)
        membre.delete()  # Membre supprimé
        
        with pytest.raises(ValidationError) as exc_info:
            validate_organisateur_membre(user)
        
        assert 'membre actif' in str(exc_info.value)
        assert exc_info.value.code == 'organisateur_inactif'

    def test_organisateur_none_invalide(self):
        """Test organisateur None invalide"""
        with pytest.raises(ValidationError) as exc_info:
            validate_organisateur_membre(None)
        
        assert 'organisateur doit être spécifié' in str(exc_info.value)
        assert exc_info.value.code == 'organisateur_requis'


@pytest.mark.django_db
@pytest.mark.unit
class TestValidateDatesInscriptions:
    """Tests pour validate_dates_inscriptions"""

    def test_dates_coherentes_valides(self):
        """Test dates cohérentes valides"""
        date_debut_evt = timezone.now() + timedelta(days=10)
        date_ouverture = timezone.now() + timedelta(days=1)
        date_fermeture = date_debut_evt - timedelta(hours=2)
        
        # Ne doit pas lever d'exception
        validate_dates_inscriptions(date_ouverture, date_fermeture, date_debut_evt)

    def test_ouverture_apres_evenement_invalide(self):
        """Test ouverture après événement invalide"""
        date_debut_evt = timezone.now() + timedelta(days=10)
        date_ouverture = date_debut_evt + timedelta(hours=1)  # Après l'événement
        
        with pytest.raises(ValidationError) as exc_info:
            validate_dates_inscriptions(date_ouverture, None, date_debut_evt)
        
        errors = exc_info.value.error_list
        assert any('ouverture' in str(error) and 'avant le début' in str(error) for error in errors)

    def test_fermeture_apres_evenement_invalide(self):
        """Test fermeture après événement invalide"""
        date_debut_evt = timezone.now() + timedelta(days=10)
        date_fermeture = date_debut_evt + timedelta(hours=1)  # Après l'événement
        
        with pytest.raises(ValidationError) as exc_info:
            validate_dates_inscriptions(None, date_fermeture, date_debut_evt)
        
        errors = exc_info.value.error_list
        assert any('fermeture' in str(error) and 'avant le début' in str(error) for error in errors)

    def test_ouverture_apres_fermeture_invalide(self):
        """Test ouverture après fermeture invalide"""
        date_debut_evt = timezone.now() + timedelta(days=10)
        date_ouverture = timezone.now() + timedelta(days=5)
        date_fermeture = timezone.now() + timedelta(days=2)  # Avant ouverture
        
        with pytest.raises(ValidationError) as exc_info:
            validate_dates_inscriptions(date_ouverture, date_fermeture, date_debut_evt)
        
        errors = exc_info.value.error_list
        assert any('ouverture' in str(error) and 'avant la fermeture' in str(error) for error in errors)


@pytest.mark.django_db
@pytest.mark.unit
class TestValidateTarifsCoherents:
    """Tests pour validate_tarifs_coherents"""

    def test_tarifs_payant_valides(self):
        """Test tarifs événement payant valides"""
        # Ne doit pas lever d'exception
        validate_tarifs_coherents(
            True, 
            Decimal('20.00'), 
            Decimal('30.00'), 
            Decimal('35.00')
        )

    def test_tarifs_gratuit_valides(self):
        """Test tarifs événement gratuit valides"""
        # Ne doit pas lever d'exception
        validate_tarifs_coherents(
            False, 
            Decimal('0.00'), 
            Decimal('0.00'), 
            Decimal('0.00')
        )

    def test_tarifs_negatifs_invalides(self):
        """Test tarifs négatifs invalides"""
        with pytest.raises(ValidationError) as exc_info:
            validate_tarifs_coherents(
                True, 
                Decimal('-10.00'),  # Négatif
                Decimal('30.00'), 
                Decimal('35.00')
            )
        
        assert 'négatifs' in str(exc_info.value)
        assert exc_info.value.code == 'tarifs_negatifs'

    def test_tarifs_tous_nuls_payant_invalide(self):
        """Test tous tarifs nuls pour événement payant invalide"""
        with pytest.raises(ValidationError) as exc_info:
            validate_tarifs_coherents(
                True,  # Payant
                Decimal('0.00'),  # Mais tous à zéro
                Decimal('0.00'), 
                Decimal('0.00')
            )
        
        # CORRECTION : Utiliser la bonne casse - "Au moins" avec majuscule
        assert 'Au moins un tarif' in str(exc_info.value)
        assert exc_info.value.code == 'tarifs_tous_nuls'


@pytest.mark.django_db
@pytest.mark.unit
class TestValidateAccompagnantsCoherents:
    """Tests pour validate_accompagnants_coherents"""

    def test_accompagnants_autorises_valides(self):
        """Test accompagnants autorisés valides"""
        type_evenement = TypeEvenementFactory(permet_accompagnants=True)
        
        # Ne doit pas lever d'exception
        validate_accompagnants_coherents(True, 3, type_evenement)

    def test_accompagnants_non_autorises_par_type(self):
        """Test accompagnants non autorisés par type"""
        type_evenement = TypeEvenementFactory(permet_accompagnants=False)
        
        with pytest.raises(ValidationError) as exc_info:
            validate_accompagnants_coherents(True, 2, type_evenement)
        
        assert 'n\'autorise pas les accompagnants' in str(exc_info.value)
        assert exc_info.value.code == 'accompagnants_non_autorises'

    def test_nombre_accompagnants_zero_avec_autorisation(self):
        """Test nombre accompagnants zéro avec autorisation"""
        with pytest.raises(ValidationError) as exc_info:
            validate_accompagnants_coherents(True, 0)  # Autorisé mais nombre = 0
        
        assert 'supérieur à 0' in str(exc_info.value)
        assert exc_info.value.code == 'nombre_accompagnants_invalide'

    def test_nombre_accompagnants_positif_sans_autorisation(self):
        """Test nombre positif sans autorisation"""
        with pytest.raises(ValidationError) as exc_info:
            validate_accompagnants_coherents(False, 2)  # Non autorisé mais nombre > 0
        
        assert 'doit être 0' in str(exc_info.value)
        assert exc_info.value.code == 'accompagnants_incoherents'


@pytest.mark.django_db
@pytest.mark.unit
class TestValidateDelaiConfirmation:
    """Tests pour validate_delai_confirmation"""

    def test_delai_valide(self):
        """Test délai valide"""
        # Ne doit pas lever d'exception
        validate_delai_confirmation(48)
        validate_delai_confirmation(24)
        validate_delai_confirmation(168)  # 7 jours

    def test_delai_zero_invalide(self):
        """Test délai zéro invalide"""
        with pytest.raises(ValidationError) as exc_info:
            validate_delai_confirmation(0)
        
        assert 'supérieur à 0' in str(exc_info.value)
        assert exc_info.value.code == 'delai_invalide'

    def test_delai_negatif_invalide(self):
        """Test délai négatif invalide"""
        with pytest.raises(ValidationError):
            validate_delai_confirmation(-5)

    def test_delai_trop_long_invalide(self):
        """Test délai trop long invalide"""
        with pytest.raises(ValidationError) as exc_info:
            validate_delai_confirmation(200)  # Plus de 7 jours
        
        assert '7 jours' in str(exc_info.value)
        assert exc_info.value.code == 'delai_trop_long'


@pytest.mark.django_db
@pytest.mark.unit
class TestValidateInscriptionPossible:
    """Tests pour validate_inscription_possible"""

    def test_inscription_possible_valide(self):
        """Test inscription possible valide"""
        evenement = EvenementFactory(
            statut='publie',
            inscriptions_ouvertes=True,
            permet_accompagnants=True,
            nombre_max_accompagnants=3,
            capacite_max=10
        )
        membre = MembreFactory()
        
        # Ne doit pas lever d'exception
        validate_inscription_possible(evenement, membre, 2)

    def test_inscription_impossible_evenement_ferme(self):
        """Test inscription impossible événement fermé"""
        evenement = EvenementFactory(inscriptions_ouvertes=False)
        membre = MembreFactory()
        
        with pytest.raises(ValidationError) as exc_info:
            validate_inscription_possible(evenement, membre, 0)
        
        assert exc_info.value.code == 'inscription_impossible'

    def test_trop_accompagnants_invalide(self):
        """Test trop d'accompagnants invalide"""
        evenement = EvenementFactory(
            statut='publie',
            inscriptions_ouvertes=True,
            permet_accompagnants=True,
            nombre_max_accompagnants=2
        )
        membre = MembreFactory()
        
        with pytest.raises(ValidationError) as exc_info:
            validate_inscription_possible(evenement, membre, 5)  # Trop
        
        assert 'ne peut pas dépasser' in str(exc_info.value)
        assert exc_info.value.code == 'trop_accompagnants'

    def test_accompagnants_non_autorises_invalide(self):
        """Test accompagnants non autorisés invalide"""
        evenement = EvenementFactory(
            statut='publie',
            inscriptions_ouvertes=True,
            permet_accompagnants=False
        )
        membre = MembreFactory()
        
        with pytest.raises(ValidationError) as exc_info:
            validate_inscription_possible(evenement, membre, 1)
        
        assert 'n\'autorise pas' in str(exc_info.value)
        assert exc_info.value.code == 'accompagnants_non_autorises'

    def test_places_insuffisantes_invalide(self):
        """Test places insuffisantes invalide"""
        evenement = EvenementFactory(
            statut='publie',
            inscriptions_ouvertes=True,
            capacite_max=2
        )
        
        # Remplir l'événement
        for _ in range(2):
            InscriptionEvenementFactory(
                evenement=evenement,
                statut='confirmee'
            )
        
        membre = MembreFactory()
        
        with pytest.raises(ValidationError) as exc_info:
            validate_inscription_possible(evenement, membre, 0)
        
        assert 'pas assez de places' in str(exc_info.value)
        assert exc_info.value.code == 'places_insuffisantes'


@pytest.mark.django_db
@pytest.mark.unit
class TestValidateMontantPaiement:
    """Tests pour validate_montant_paiement"""

    def test_montant_valide(self):
        """Test montant valide"""
        # Ne doit pas lever d'exception
        validate_montant_paiement(Decimal('25.00'), Decimal('50.00'))

    def test_montant_negatif_invalide(self):
        """Test montant négatif invalide"""
        with pytest.raises(ValidationError) as exc_info:
            validate_montant_paiement(Decimal('-10.00'), Decimal('50.00'))
        
        assert 'négatif' in str(exc_info.value)
        assert exc_info.value.code == 'montant_negatif'

    def test_montant_excessif_invalide(self):
        """Test montant excessif invalide"""
        with pytest.raises(ValidationError) as exc_info:
            validate_montant_paiement(Decimal('100.00'), Decimal('50.00'))
        
        assert 'ne peut pas dépasser' in str(exc_info.value)
        assert exc_info.value.code == 'montant_excessif'


@pytest.mark.django_db
@pytest.mark.unit
class TestValidatePeriodeRecherche:
    """Tests pour validate_periode_recherche"""

    def test_periode_valide(self):
        """Test période valide"""
        date_debut = timezone.now().date()
        date_fin = date_debut + timedelta(days=30)
        
        # Ne doit pas lever d'exception
        validate_periode_recherche(date_debut, date_fin)

    def test_periode_inversee_invalide(self):
        """Test période inversée invalide"""
        date_debut = timezone.now().date()
        date_fin = date_debut - timedelta(days=10)
        
        with pytest.raises(ValidationError) as exc_info:
            validate_periode_recherche(date_debut, date_fin)
        
        assert 'antérieure' in str(exc_info.value)
        assert exc_info.value.code == 'periode_invalide'

    def test_periode_trop_longue_invalide(self):
        """Test période trop longue invalide"""
        date_debut = timezone.now().date()
        date_fin = date_debut + timedelta(days=800)  # Plus de 2 ans
        
        with pytest.raises(ValidationError) as exc_info:
            validate_periode_recherche(date_debut, date_fin)
        
        assert '2 ans' in str(exc_info.value)
        assert exc_info.value.code == 'periode_trop_longue'


@pytest.mark.django_db
@pytest.mark.unit
class TestValidateCodeCouleur:
    """Tests pour validate_code_couleur"""

    def test_couleur_valide(self):
        """Test code couleur valide"""
        # Ne doit pas lever d'exception
        validate_code_couleur('#FF0000')
        validate_code_couleur('#00FF00')
        validate_code_couleur('#0000FF')
        validate_code_couleur('#123ABC')

    def test_couleur_sans_diese_invalide(self):
        """Test couleur sans # invalide"""
        with pytest.raises(ValidationError) as exc_info:
            validate_code_couleur('FF0000')
        
        assert 'hexadécimal' in str(exc_info.value)
        assert exc_info.value.code == 'couleur_invalide'

    def test_couleur_trop_courte_invalide(self):
        """Test couleur trop courte invalide"""
        with pytest.raises(ValidationError):
            validate_code_couleur('#FF00')

    def test_couleur_caracteres_invalides(self):
        """Test couleur avec caractères invalides"""
        with pytest.raises(ValidationError):
            validate_code_couleur('#GGGGGG')


@pytest.mark.django_db
@pytest.mark.unit
class TestValidateCapaciteSession:
    """Tests pour validate_capacite_session"""

    def test_capacite_session_valide(self):
        """Test capacité session valide"""
        # Ne doit pas lever d'exception
        validate_capacite_session(50, 100)
        validate_capacite_session(100, 100)  # Égale

    def test_capacite_session_excessive_invalide(self):
        """Test capacité session excessive invalide"""
        with pytest.raises(ValidationError) as exc_info:
            validate_capacite_session(150, 100)
        
        assert 'ne peut pas dépasser' in str(exc_info.value)
        assert exc_info.value.code == 'capacite_session_excessive'

    def test_capacite_session_none_valide(self):
        """Test capacité session None valide"""
        # Ne doit pas lever d'exception
        validate_capacite_session(None, 100)


@pytest.mark.django_db
@pytest.mark.unit
class TestValidateDonneesAccompagnant:
    """Tests pour validate_donnees_accompagnant"""

    def test_donnees_valides(self):
        """Test données accompagnant valides"""
        # Ne doit pas lever d'exception
        validate_donnees_accompagnant('Dupont', 'Marie', 'marie@test.com')

    def test_nom_manquant_invalide(self):
        """Test nom manquant invalide"""
        with pytest.raises(ValidationError) as exc_info:
            validate_donnees_accompagnant('', 'Marie', 'marie@test.com')
        
        errors = exc_info.value.error_list
        assert any('nom' in str(error) and 'requis' in str(error) for error in errors)

    def test_prenom_manquant_invalide(self):
        """Test prénom manquant invalide"""
        with pytest.raises(ValidationError) as exc_info:
            validate_donnees_accompagnant('Dupont', '', 'marie@test.com')
        
        errors = exc_info.value.error_list
        assert any('prénom' in str(error) and 'requis' in str(error) for error in errors)

    def test_email_invalide(self):
        """Test email invalide"""
        with pytest.raises(ValidationError) as exc_info:
            validate_donnees_accompagnant('Dupont', 'Marie', 'email_invalide')
        
        errors = exc_info.value.error_list
        assert any('email' in str(error) and 'valide' in str(error) for error in errors)

    def test_email_none_valide(self):
        """Test email None valide"""
        # Ne doit pas lever d'exception
        validate_donnees_accompagnant('Dupont', 'Marie', None)

    def test_nom_prenom_whitespace_invalides(self):
        """Test nom/prénom avec seulement espaces invalides"""
        with pytest.raises(ValidationError) as exc_info:
            validate_donnees_accompagnant('   ', '   ', None)
        
        errors = exc_info.value.error_list
        assert len(errors) == 2  # Nom et prénom requis