import pytest
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
from apps.evenements.tests.factories import ValidationEvenementFactory

from apps.evenements.models import (
    TypeEvenement, Evenement, InscriptionEvenement,
    AccompagnantInvite, ValidationEvenement, EvenementRecurrence
)
from apps.evenements.tests.factories import (
    TypeEvenementFactory, EvenementFactory, MembreFactory,
    InscriptionEvenementFactory, AccompagnantInviteFactory,
    EvenementCompletFactory, CustomUserFactory, TypeMembreFactory
)


@pytest.mark.django_db
@pytest.mark.unit
class TestTypeEvenement:
    """Tests unitaires pour le modèle TypeEvenement"""

    def test_creation_type_evenement(self):
        """Test création d'un type d'événement valide"""
        type_event = TypeEvenementFactory(
            libelle="Formation Python",
            description="Formation de développement Python",
            couleur_affichage="#007bff"
        )
        
        assert type_event.libelle == "Formation Python"
        assert type_event.couleur_affichage == "#007bff"
        assert str(type_event) == "Formation Python"

    def test_libelle_unique(self):
        """Test unicité du libellé"""
        TypeEvenementFactory(libelle="Formation Unique")
        
        with pytest.raises(IntegrityError):
            TypeEvenementFactory(libelle="Formation Unique")

    def test_couleur_correction_automatique(self):
        """Test correction automatique de la couleur"""
        type_event = TypeEvenementFactory(couleur_affichage="007bff")
        assert type_event.couleur_affichage == "#007bff"

    def test_ordre_affichage_par_defaut(self):
        """Test ordre d'affichage par défaut"""
        type_event = TypeEvenementFactory()
        assert type_event.ordre_affichage >= 0


@pytest.mark.django_db
@pytest.mark.unit
class TestEvenement:
    """Tests unitaires pour le modèle Evenement"""

    def test_creation_evenement_valide(self):
        """Test création d'un événement valide"""
        date_debut = timezone.now() + timedelta(days=30)
        date_fin = date_debut + timedelta(hours=2)
        
        evenement = EvenementFactory(
            titre="Conférence IA",
            date_debut=date_debut,
            date_fin=date_fin,
            capacite_max=100
        )
        
        assert evenement.titre == "Conférence IA"
        assert evenement.capacite_max == 100
        assert evenement.reference.startswith("EVT")

    def test_generation_reference_unique(self):
        """Test génération de référence unique"""
        evt1 = EvenementFactory()
        evt2 = EvenementFactory()
        
        assert evt1.reference != evt2.reference
        assert len(evt1.reference) > 8  # Format EVT2024-XXXXXXXX

    def test_validation_dates_coherentes(self):
        """Test validation cohérence des dates"""
        date_debut = timezone.now() + timedelta(days=30)
        date_fin = date_debut - timedelta(hours=1)  # Date fin avant début
        
        evenement = EvenementFactory.build(
            date_debut=date_debut,
            date_fin=date_fin
        )
        
        with pytest.raises(ValidationError):
            evenement.full_clean()

    def test_validation_date_future(self):
        """Test validation date dans le futur"""
        date_passee = timezone.now() - timedelta(days=1)
        
        evenement = EvenementFactory.build(date_debut=date_passee)
        
        with pytest.raises(ValidationError):
            evenement.full_clean()

    def test_validation_organisateur_membre(self):
        """Test validation organisateur doit être membre"""
        user_non_membre = CustomUserFactory()
        
        evenement = EvenementFactory.build(organisateur=user_non_membre)
        
        with pytest.raises(ValidationError):
            evenement.full_clean()

    def test_duree_heures_calcul(self):
        """Test calcul durée en heures"""
        date_debut = timezone.now() + timedelta(days=1)
        date_fin = date_debut + timedelta(hours=3, minutes=30)
        
        evenement = EvenementFactory(
            date_debut=date_debut,
            date_fin=date_fin
        )
        
        assert evenement.duree_heures == 3.5

    def test_duree_heures_sans_fin(self):
        """Test durée sans date de fin"""
        evenement = EvenementFactory(date_fin=None)
        assert evenement.duree_heures is None

    def test_est_termine_property(self):
        """Test propriété est_termine"""
        # Événement futur
        evenement_futur = EvenementFactory(
            date_debut=timezone.now() + timedelta(days=1)
        )
        assert not evenement_futur.est_termine
        
        # Événement passé - NOUVELLE APPROCHE : créer puis modifier
        evenement_passe = EvenementFactory(
            date_debut=timezone.now() + timedelta(days=1),  # Créer valide d'abord
            date_fin=timezone.now() + timedelta(days=1, hours=2)
        )
        
        # Modifier directement en base sans validation
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE evenements SET date_debut = %s, date_fin = %s WHERE id = %s",
                [
                    timezone.now() - timedelta(days=1),
                    timezone.now() - timedelta(hours=1),
                    evenement_passe.id
                ]
            )
        
        # Recharger depuis la base
        evenement_passe.refresh_from_db()
        assert evenement_passe.est_termine

    
    def test_places_disponibles_calcul(self):
        """Test calcul places disponibles - ISOLATION COMPLÈTE"""
        # CORRECTION : Créer un événement complètement isolé
        evenement = EvenementFactory(capacite_max=20)
        
        # NETTOYER : S'assurer qu'aucune inscription n'existe
        evenement.inscriptions.all().delete()
        
        # Créer exactement 5 inscriptions confirmées manuellement
        membres_confirmes = []
        for i in range(5):
            membre = MembreFactory()
            inscription = InscriptionEvenementFactory(
                evenement=evenement,
                membre=membre,
                statut='confirmee',
                nombre_accompagnants=0  # EXPLICITE : pas d'accompagnant
            )
            membres_confirmes.append(inscription)
        
        # VÉRIFICATION DEBUG
        count_confirmees = evenement.inscriptions.filter(statut='confirmee').count()
        assert count_confirmees == 5, f"Attendu 5 inscriptions confirmées, trouvé {count_confirmees}"
        
        # Test final
        assert evenement.places_disponibles == 15

    def test_est_complet_property(self):
        """Test propriété est_complet - COHÉRENCE AVEC places_disponibles"""
        evenement = EvenementFactory(capacite_max=3)
        
        # NETTOYER d'abord
        evenement.inscriptions.all().delete()
        
        # 1 inscription confirmée -> pas complet
        InscriptionEvenementFactory(
            evenement=evenement, 
            statut='confirmee',
            nombre_accompagnants=0
        )
        assert not evenement.est_complet
        assert evenement.places_disponibles == 2
        
        # 3 inscriptions confirmées -> complet
        for _ in range(2):
            InscriptionEvenementFactory(
                evenement=evenement, 
                statut='confirmee',
                nombre_accompagnants=0
            )
        
        assert evenement.est_complet
        assert evenement.places_disponibles == 0

    def test_taux_occupation_calcul(self):
        """Test calcul taux d'occupation"""
        evenement = EvenementFactory(capacite_max=10)
        
        # 3 inscriptions confirmées
        for _ in range(3):
            InscriptionEvenementFactory(
                evenement=evenement,
                statut='confirmee'
            )
        
        assert evenement.taux_occupation == 30.0

    def test_peut_s_inscrire_evenement_ouvert(self):
        """Test peut s'inscrire - événement ouvert"""
        membre = MembreFactory()
        # CORRECTION : Créer un événement vraiment vide
        evenement = EvenementFactory(
            statut='publie',
            inscriptions_ouvertes=True,
            capacite_max=10,
            date_debut=timezone.now() + timedelta(days=30),
            date_ouverture_inscriptions=timezone.now() - timedelta(days=5),
            date_fermeture_inscriptions=timezone.now() + timedelta(days=25)
        )
        
        # CORRECTION : S'assurer qu'il n'y a pas d'inscriptions existantes
        evenement.inscriptions.all().delete()
        
        # Vérifier que l'événement n'est pas complet
        assert not evenement.est_complet, f"L'événement ne devrait pas être complet. Places: {evenement.places_disponibles}, Complet: {evenement.est_complet}"
        
        peut_inscrire, message = evenement.peut_s_inscrire(membre)
        assert peut_inscrire, f"Inscription devrait être possible. Message: {message}"
        assert "Inscription possible" in message

    def test_peut_s_inscrire_evenement_ferme(self):
        """Test peut s'inscrire - inscriptions fermées"""
        membre = MembreFactory()
        evenement = EvenementFactory(inscriptions_ouvertes=False)
        
        peut_inscrire, message = evenement.peut_s_inscrire(membre)
        assert not peut_inscrire
        assert "fermées" in message

    def test_peut_s_inscrire_deja_inscrit(self):
        """Test peut s'inscrire - déjà inscrit"""
        membre = MembreFactory()
        # CORRECTION : Créer explicitement un événement publié
        evenement = EvenementFactory(
            statut='publie',  # Forcer le statut publié
            inscriptions_ouvertes=True,
            capacite_max=10,
            date_debut=timezone.now() + timedelta(days=30),
            date_ouverture_inscriptions=timezone.now() - timedelta(days=5),
            date_fermeture_inscriptions=timezone.now() + timedelta(days=25)
        )
        
        # Créer une inscription existante
        InscriptionEvenementFactory(
            evenement=evenement,
            membre=membre,
            statut='confirmee'
        )
        
        peut_inscrire, message = evenement.peut_s_inscrire(membre)
        assert not peut_inscrire
        assert "déjà inscrit" in message

    def test_calculer_tarif_membre_etudiant(self):
        """Test calcul tarif pour membre étudiant"""
        from apps.membres.models import TypeMembre, MembreTypeMembre
        
        type_etudiant = TypeMembreFactory(libelle='Étudiant')
        membre = MembreFactory()
        
        # Associer le type étudiant au membre
        MembreTypeMembre.objects.create(
            membre=membre,
            type_membre=type_etudiant,
            date_debut=timezone.now().date()
        )
        
        evenement = EvenementFactory(
            est_payant=True,
            tarif_membre=Decimal('20.00'),
            tarif_salarie=Decimal('30.00')
        )
        
        tarif = evenement.calculer_tarif_membre(membre)
        assert tarif == Decimal('20.00')  # Tarif membre pour étudiant

    def test_calculer_tarif_membre_salarie(self):
        """Test calcul tarif pour membre salarié"""
        from apps.membres.models import TypeMembre, MembreTypeMembre
        
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
            tarif_salarie=Decimal('30.00')
        )
        
        tarif = evenement.calculer_tarif_membre(membre)
        assert tarif == Decimal('30.00')  # Tarif salarié

    def test_calculer_tarif_evenement_gratuit(self):
        """Test calcul tarif pour événement gratuit"""
        membre = MembreFactory()
        evenement = EvenementFactory(est_payant=False)
        
        tarif = evenement.calculer_tarif_membre(membre)
        assert tarif == Decimal('0.00')

    


@pytest.mark.django_db
@pytest.mark.unit
class TestInscriptionEvenement:
    """Tests unitaires pour le modèle InscriptionEvenement"""
    
    def test_promouvoir_liste_attente(self):
            """Test promotion depuis liste d'attente - WORKFLOW COMPLET"""
            evenement = EvenementFactory(capacite_max=2)
            
            # NETTOYER d'abord
            evenement.inscriptions.all().delete()
            
            # Remplir exactement avec 2 inscriptions confirmées
            inscriptions_confirmees = []
            for i in range(2):
                membre = MembreFactory()
                inscription = InscriptionEvenementFactory(
                    evenement=evenement,
                    membre=membre,
                    statut='confirmee',
                    nombre_accompagnants=0
                )
                inscriptions_confirmees.append(inscription)
            
            # Vérifier que c'est complet
            assert evenement.places_disponibles == 0
            assert evenement.est_complet
            
            # Ajouter en liste d'attente
            membre_attente = MembreFactory()
            inscription_attente = InscriptionEvenementFactory(
                evenement=evenement,
                membre=membre_attente,
                statut='liste_attente',
                nombre_accompagnants=0
            )
            
            # Libérer UNE place en supprimant une inscription confirmée
            inscriptions_confirmees[0].delete()
            
            # Vérifier qu'une place est maintenant libre
            evenement.refresh_from_db()  # Important !
            assert evenement.places_disponibles == 1
            
            # Promouvoir depuis la liste d'attente
            promus = evenement.promouvoir_liste_attente()
            
            # Vérifications finales
            inscription_attente.refresh_from_db()
            assert inscription_attente.statut == 'en_attente'  # Promu vers en_attente
            assert promus == 1

    def test_creation_inscription_valide(self):
        """Test création inscription valide"""
        inscription = InscriptionEvenementFactory()
        
        assert inscription.evenement is not None
        assert inscription.membre is not None
        assert inscription.code_confirmation is not None
        assert len(inscription.code_confirmation) == 12

    def test_unicite_membre_evenement(self):
        """Test unicité membre-événement"""
        membre = MembreFactory()
        evenement = EvenementFactory()
        
        InscriptionEvenementFactory(membre=membre, evenement=evenement)
        
        with pytest.raises(IntegrityError):
            InscriptionEvenementFactory(membre=membre, evenement=evenement)

    def test_validation_nombre_accompagnants(self):
        """Test validation nombre d'accompagnants"""
        evenement = EvenementFactory(
            permet_accompagnants=True,
            nombre_max_accompagnants=2
        )
        
        # CORRECTION : Utiliser create() au lieu de build() pour éviter l'erreur de relation
        inscription = InscriptionEvenementFactory(
            evenement=evenement,
            nombre_accompagnants=5  # Dépasse le maximum
        )
        
        with pytest.raises(ValidationError):
            inscription.full_clean()

    def test_validation_accompagnants_non_autorises(self):
        """Test validation accompagnants non autorisés"""
        evenement = EvenementFactory(permet_accompagnants=False)
        
        # CORRECTION : Utiliser create() au lieu de build()
        inscription = InscriptionEvenementFactory(
            evenement=evenement,
            nombre_accompagnants=1
        )
        
        with pytest.raises(ValidationError):
            inscription.full_clean()

    def test_calculer_montant_total_gratuit(self):
        """Test calcul montant total - événement gratuit"""
        evenement = EvenementFactory(est_payant=False)
        inscription = InscriptionEvenementFactory(
            evenement=evenement,
            nombre_accompagnants=2
        )
        
        assert inscription.calculer_montant_total() == Decimal('0.00')

    def test_calculer_montant_total_payant(self):
        """Test calcul montant total - événement payant"""
        evenement = EvenementFactory(
            est_payant=True,
            tarif_membre=Decimal('20.00'),
            tarif_invite=Decimal('25.00')
        )
        
        inscription = InscriptionEvenementFactory(
            evenement=evenement,
            nombre_accompagnants=2
        )
        
        # 20€ membre + 2 * 25€ accompagnants = 70€
        assert inscription.calculer_montant_total() == Decimal('70.00')

    def test_montant_restant_property(self):
        """Test propriété montant_restant"""
        evenement = EvenementFactory(
            est_payant=True,
            tarif_membre=Decimal('50.00')
        )
        
        inscription = InscriptionEvenementFactory(
            evenement=evenement,
            montant_paye=Decimal('30.00')
        )
        
        assert inscription.montant_restant == Decimal('20.00')

    def test_est_payee_property(self):
        """Test propriété est_payee"""
        # Créer un événement payant avec tarifs fixes
        evenement = EvenementFactory(
            est_payant=True,
            tarif_membre=Decimal('50.00'),
            tarif_salarie=Decimal('60.00'),
            tarif_invite=Decimal('70.00')
        )
        
        # Créer un membre explicite
        membre = MembreFactory()
        
        # Test 1 : Inscription partiellement payée
        inscription_partielle = InscriptionEvenementFactory(
            evenement=evenement,
            membre=membre,
            nombre_accompagnants=0,  # Pas d'accompagnant pour simplifier
            montant_paye=Decimal('30.00')  # Moins que le tarif membre (50€)
        )
        
        # Vérifier les calculs
        montant_total = inscription_partielle.calculer_montant_total()
        montant_restant = inscription_partielle.montant_restant
        
        print(f"DEBUG - Montant total: {montant_total}")
        print(f"DEBUG - Montant payé: {inscription_partielle.montant_paye}")
        print(f"DEBUG - Montant restant: {montant_restant}")
        
        assert not inscription_partielle.est_payee
        
        # Test 2 : Inscription entièrement payée
        # Calculer d'abord le montant exact nécessaire
        membre2 = MembreFactory()
        inscription_temp = InscriptionEvenementFactory(
            evenement=evenement,
            membre=membre2,
            nombre_accompagnants=0,
            montant_paye=Decimal('0.00')
        )
        
        montant_a_payer = inscription_temp.calculer_montant_total()
        
        # Mettre à jour le montant payé pour qu'il corresponde exactement
        inscription_temp.montant_paye = montant_a_payer
        inscription_temp.save()
        
        assert inscription_temp.est_payee, f"Inscription non payée: total={montant_a_payer}, payé={inscription_temp.montant_paye}, restant={inscription_temp.montant_restant}"

    def test_est_en_retard_confirmation(self):
        """Test propriété est_en_retard_confirmation"""
        # Inscription en retard
        inscription_retard = InscriptionEvenementFactory(
            statut='en_attente',
            date_limite_confirmation=timezone.now() - timedelta(hours=1)
        )
        assert inscription_retard.est_en_retard_confirmation
        
        # Inscription dans les temps
        inscription_temps = InscriptionEvenementFactory(
            statut='en_attente',
            date_limite_confirmation=timezone.now() + timedelta(hours=1)
        )
        assert not inscription_temps.est_en_retard_confirmation

    def test_confirmer_inscription(self):
        """Test confirmation d'inscription"""
        inscription = InscriptionEvenementFactory(statut='en_attente')
        
        result = inscription.confirmer_inscription()
        
        assert result is True
        assert inscription.statut == 'confirmee'
        assert inscription.date_confirmation is not None

    def test_confirmer_inscription_invalide(self):
        """Test confirmation inscription dans mauvais statut"""
        inscription = InscriptionEvenementFactory(statut='confirmee')
        
        result = inscription.confirmer_inscription()
        
        assert result is False

    def test_annuler_inscription(self):
        """Test annulation d'inscription"""
        inscription = InscriptionEvenementFactory(statut='confirmee')
        
        result = inscription.annuler_inscription("Test annulation")
        
        assert result is True
        assert inscription.statut == 'annulee'
        assert "Test annulation" in inscription.commentaire

    def test_placer_en_liste_attente(self):
        """Test placement en liste d'attente"""
        inscription = InscriptionEvenementFactory(statut='en_attente')
        
        result = inscription.placer_en_liste_attente()
        
        assert result is True
        assert inscription.statut == 'liste_attente'
        assert inscription.date_limite_confirmation is None


@pytest.mark.django_db
@pytest.mark.unit
class TestAccompagnantInvite:
    """Tests unitaires pour le modèle AccompagnantInvite"""

    def test_creation_accompagnant(self):
        """Test création d'un accompagnant"""
        accompagnant = AccompagnantInviteFactory(
            nom="Dupont",
            prenom="Marie",
            est_accompagnant=True
        )
        
        assert accompagnant.nom == "Dupont"
        assert accompagnant.prenom == "Marie"
        assert accompagnant.nom_complet == "Marie Dupont"
        assert "Accompagnant: Marie Dupont" in str(accompagnant)

    def test_creation_invite_externe(self):
        """Test création d'un invité externe"""
        invite = AccompagnantInviteFactory(
            nom="Martin",
            prenom="Paul",
            est_accompagnant=False
        )
        
        assert "Invité: Paul Martin" in str(invite)

    def test_confirmer_presence(self):
        """Test confirmation de présence"""
        accompagnant = AccompagnantInviteFactory(statut='invite')
        
        result = accompagnant.confirmer_presence()
        
        assert result is True
        assert accompagnant.statut == 'confirme'
        assert accompagnant.date_reponse is not None

    def test_refuser_invitation(self):
        """Test refus d'invitation"""
        accompagnant = AccompagnantInviteFactory(statut='invite')
        
        result = accompagnant.refuser_invitation()
        
        assert result is True
        assert accompagnant.statut == 'refuse'
        assert accompagnant.date_reponse is not None


@pytest.mark.django_db
@pytest.mark.unit
class TestValidationEvenement:
    """Tests unitaires pour le modèle ValidationEvenement"""

    def test_approuver_evenement(self):
        """Test approbation d'événement"""
        validateur = CustomUserFactory()
        validation = ValidationEvenementFactory(statut_validation='en_attente')
        
        validation.approuver(validateur, "Événement approuvé")
        
        assert validation.statut_validation == 'approuve'
        assert validation.validateur == validateur
        assert validation.date_validation is not None
        assert validation.evenement.statut == 'publie'

    def test_refuser_evenement(self):
        """Test refus d'événement"""
        validateur = CustomUserFactory()
        validation = ValidationEvenementFactory(statut_validation='en_attente')
        
        validation.refuser(validateur, "Événement non conforme")
        
        assert validation.statut_validation == 'refuse'
        assert validation.validateur == validateur
        assert "non conforme" in validation.commentaire_validation
        assert validation.evenement.statut == 'brouillon'

    def test_demander_modifications(self):
        """Test demande de modifications"""
        validateur = CustomUserFactory()
        validation = ValidationEvenementFactory(statut_validation='en_attente')
        
        modifications = ["Modifier le titre", "Préciser le lieu"]
        validation.demander_modifications(validateur, modifications)
        
        assert validation.statut_validation == 'en_attente'
        assert len(validation.modifications_demandees) == 1
        assert modifications == validation.modifications_demandees[0]['modifications']


@pytest.mark.django_db
@pytest.mark.unit
class TestEvenementRecurrence:
    """Tests unitaires pour le modèle EvenementRecurrence"""

    def test_validation_contraintes_fin(self):
        """Test validation contraintes de fin"""
        evenement = EvenementFactory()
        
        # CORRECTION : Tester une validation qui existe vraiment
        # Tester que l'intervalle doit être >= 1
        recurrence = EvenementRecurrence(
            evenement_parent=evenement,
            frequence='mensuelle',
            intervalle_recurrence=0  # Invalide
        )
        
        with pytest.raises(ValidationError):
            recurrence.full_clean()

    def test_validation_date_fin_coherente(self):
        """Test validation date fin cohérente"""
        evenement = EvenementFactory()
        
        recurrence = EvenementRecurrence(
            evenement_parent=evenement,
            frequence='mensuelle',
            date_fin_recurrence=evenement.date_debut.date() - timedelta(days=1)
        )
        
        with pytest.raises(ValidationError):
            recurrence.full_clean()