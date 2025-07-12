import factory
from factory.django import DjangoModelFactory
from factory import SubFactory, LazyAttribute, Iterator, LazyFunction
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import random

from apps.accounts.models import CustomUser
from apps.membres.models import Membre, TypeMembre
from apps.cotisations.models import ModePaiement
from apps.core.models import Statut
from apps.evenements.models import (
    TypeEvenement, Evenement, InscriptionEvenement, 
    AccompagnantInvite, ValidationEvenement, EvenementRecurrence,
    SessionEvenement
)

class CustomUserFactory(DjangoModelFactory):
    """Factory pour les utilisateurs"""
    class Meta:
        model = CustomUser
        django_get_or_create = ('username',)

    username = factory.Sequence(lambda n: f'user{n}')
    email = factory.LazyAttribute(lambda obj: f'{obj.username}@test.com')
    first_name = factory.Faker('first_name', locale='fr_FR')
    last_name = factory.Faker('last_name', locale='fr_FR')
    is_active = True
    is_staff = False


class StatutFactory(DjangoModelFactory):
    """Factory pour les statuts"""
    class Meta:
        model = Statut
        django_get_or_create = ('nom',)

    nom = Iterator(['Actif', 'Inactif', 'En attente', 'Validé', 'Refusé'])
    description = factory.LazyAttribute(lambda obj: f'Statut {obj.nom}')


class TypeMembreFactory(DjangoModelFactory):
    """Factory pour les types de membres"""
    class Meta:
        model = TypeMembre
        django_get_or_create = ('libelle',)

    libelle = Iterator(['Étudiant', 'Salarié', 'Retraité', 'Honoraire', 'Bienfaiteur'])
    description = factory.LazyAttribute(lambda obj: f'Type membre {obj.libelle}')


class MembreFactory(DjangoModelFactory):
    """Factory pour les membres"""
    class Meta:
        model = Membre

    nom = factory.Faker('last_name', locale='fr_FR')
    prenom = factory.Faker('first_name', locale='fr_FR')
    email = factory.LazyAttribute(lambda obj: f'{obj.prenom.lower()}.{obj.nom.lower()}@test.com')
    telephone = factory.Faker('phone_number', locale='fr_FR')
    adresse = factory.Faker('address', locale='fr_FR')
    date_adhesion = factory.LazyFunction(
        lambda: timezone.now().date() - timedelta(days=random.randint(1, 365))
    )
    date_naissance = factory.LazyFunction(
        lambda: timezone.now().date() - timedelta(days=random.randint(6570, 25550))  # 18-70 ans
    )
    utilisateur = SubFactory(CustomUserFactory)
    statut = SubFactory(StatutFactory, nom='Actif')


class ModePaiementFactory(DjangoModelFactory):
    """Factory pour les modes de paiement"""
    class Meta:
        model = ModePaiement
        django_get_or_create = ('libelle',)

    libelle = Iterator(['Espèces', 'Chèque', 'Virement', 'Carte bancaire', 'PayPal'])


class TypeEvenementFactory(DjangoModelFactory):
    """Factory pour les types d'événements"""
    class Meta:
        model = TypeEvenement

    libelle = Iterator([
        'Formation', 'Réunion', 'Sortie', 'Assemblée Générale', 
        'Séminaire', 'Webinaire', 'Conférence', 'Atelier'
    ])
    description = factory.LazyAttribute(lambda obj: f'Type d\'événement {obj.libelle}')
    couleur_affichage = Iterator(['#007bff', '#28a745', '#dc3545', '#ffc107', '#17a2b8'])
    necessite_validation = factory.Faker('boolean', chance_of_getting_true=30)
    permet_accompagnants = factory.Faker('boolean', chance_of_getting_true=70)
    ordre_affichage = factory.Sequence(lambda n: n)


class EvenementFactory(DjangoModelFactory):
    """Factory pour les événements"""
    class Meta:
        model = Evenement

    titre = factory.Faker('sentence', nb_words=4, locale='fr_FR')
    description = factory.Faker('text', max_nb_chars=500, locale='fr_FR')
    
    # Dates futures pour événements actifs
    date_debut = factory.LazyFunction(
        lambda: timezone.now() + timedelta(days=random.randint(1, 90))
    )
    date_fin = factory.LazyAttribute(
        lambda obj: obj.date_debut + timedelta(hours=random.randint(1, 8))
    )
    
    lieu = factory.Faker('city', locale='fr_FR')
    adresse_complete = factory.Faker('address', locale='fr_FR')
    capacite_max = factory.Faker('random_int', min=10, max=200)
    
    inscriptions_ouvertes = True
    date_ouverture_inscriptions = factory.LazyAttribute(
        lambda obj: obj.date_debut - timedelta(days=30)
    )
    date_fermeture_inscriptions = factory.LazyAttribute(
        lambda obj: obj.date_debut - timedelta(hours=2)
    )
    
    est_payant = factory.Faker('boolean', chance_of_getting_true=60)
    
    # CORRECTION DÉCIMALES : Utiliser Decimal avec exactement 2 décimales
    tarif_membre = factory.LazyAttribute(
        lambda obj: Decimal(f"{random.randint(0, 100)}.{random.randint(0, 99):02d}") if obj.est_payant else Decimal('0.00')
    )
    tarif_salarie = factory.LazyAttribute(
        lambda obj: Decimal(f"{random.randint(10, 150)}.{random.randint(0, 99):02d}") if obj.est_payant else Decimal('0.00')
    )
    tarif_invite = factory.LazyAttribute(
        lambda obj: Decimal(f"{random.randint(15, 200)}.{random.randint(0, 99):02d}") if obj.est_payant else Decimal('0.00')
    )
    
    permet_accompagnants = factory.LazyAttribute(lambda obj: obj.type_evenement.permet_accompagnants)
    nombre_max_accompagnants = factory.LazyAttribute(
        lambda obj: random.randint(1, 5) if obj.permet_accompagnants else 0
    )
    
    delai_confirmation = factory.Faker('random_int', min=24, max=72)
    
    type_evenement = SubFactory(TypeEvenementFactory)
    
    # CORRECTION FINALE : Créer un utilisateur qui EST un membre
    organisateur = factory.LazyFunction(lambda: MembreFactory().utilisateur)
    
    statut = 'publie'


class InscriptionEvenementFactory(DjangoModelFactory):
    """Factory pour les inscriptions"""
    class Meta:
        model = InscriptionEvenement

    evenement = SubFactory(EvenementFactory)
    membre = SubFactory(MembreFactory)
    
    statut = Iterator(['en_attente', 'confirmee', 'liste_attente', 'annulee'])
    date_inscription = factory.LazyFunction(lambda: timezone.now())
    
    nombre_accompagnants = factory.LazyAttribute(
        lambda obj: random.randint(0, obj.evenement.nombre_max_accompagnants) 
        if obj.evenement.permet_accompagnants else 0
    )
    
    # CORRECTION : Utiliser calculer_tarif_membre avec gestion des erreurs
    montant_paye = factory.LazyAttribute(
        lambda obj: obj.evenement.calculer_tarif_membre(obj.membre) 
        if obj.evenement.est_payant and hasattr(obj.evenement, 'calculer_tarif_membre') 
        else Decimal('0.00')
    )
    
    mode_paiement = factory.SubFactory(ModePaiementFactory)
    commentaire = factory.Faker('text', max_nb_chars=200, locale='fr_FR')


class AccompagnantInviteFactory(DjangoModelFactory):
    """Factory pour les accompagnants"""
    class Meta:
        model = AccompagnantInvite

    inscription = SubFactory(InscriptionEvenementFactory)
    nom = factory.Faker('last_name', locale='fr_FR')
    prenom = factory.Faker('first_name', locale='fr_FR')
    email = factory.LazyAttribute(lambda obj: f'{obj.prenom.lower()}.{obj.nom.lower()}@test.com')
    telephone = factory.Faker('phone_number', locale='fr_FR')
    statut = Iterator(['invite', 'confirme', 'refuse', 'present', 'absent'])
    est_accompagnant = True


class ValidationEvenementFactory(DjangoModelFactory):
    """Factory pour les validations d'événements"""
    class Meta:
        model = ValidationEvenement

    evenement = SubFactory(EvenementFactory, statut='en_attente_validation')
    validateur = SubFactory(MembreFactory)
    statut_validation = Iterator(['en_attente', 'approuve', 'refuse'])
    date_validation = factory.LazyAttribute(
        lambda obj: timezone.now() if obj.statut_validation in ['approuve', 'refuse'] else None
    )
    commentaires_validation = factory.Faker('text', max_nb_chars=300, locale='fr_FR')
    date_creation = factory.LazyFunction(lambda: timezone.now())
    date_modification = factory.LazyFunction(lambda: timezone.now())


class EvenementRecurrenceFactory(DjangoModelFactory):
    """Factory pour les récurrences"""
    class Meta:
        model = EvenementRecurrence

    evenement_parent = SubFactory(EvenementFactory, est_recurrent=True)
    frequence = Iterator(['hebdomadaire', 'mensuelle', 'annuelle'])
    intervalle_recurrence = factory.Faker('random_int', min=1, max=4)
    jours_semaine = factory.LazyAttribute(lambda obj: [1, 3, 5] if obj.frequence == 'hebdomadaire' else [])
    date_fin_recurrence = factory.LazyAttribute(
        lambda obj: obj.evenement_parent.date_debut.date() + timedelta(days=365)
    )


class SessionEvenementFactory(DjangoModelFactory):
    """Factory pour les sessions"""
    class Meta:
        model = SessionEvenement

    evenement_parent = SubFactory(EvenementFactory)
    titre_session = factory.Faker('sentence', nb_words=3, locale='fr_FR')
    description_session = factory.Faker('text', max_nb_chars=200, locale='fr_FR')
    
    date_debut_session = factory.LazyAttribute(
        lambda obj: obj.evenement_parent.date_debut + timedelta(minutes=random.randint(0, 360))
    )
    date_fin_session = factory.LazyAttribute(
        lambda obj: obj.date_debut_session + timedelta(hours=random.randint(1, 3))
    )
    
    capacite_session = factory.LazyAttribute(lambda obj: obj.evenement_parent.capacite_max)
    ordre_session = factory.Sequence(lambda n: n + 1)
    est_obligatoire = factory.Faker('boolean', chance_of_getting_true=70)
    intervenant = factory.Faker('name', locale='fr_FR')


# Factories de scénarios complexes
class EvenementCompletFactory(EvenementFactory):
    """Événement complet avec inscriptions"""
    
    @factory.post_generation
    def avec_inscriptions(self, create, extracted, **kwargs):
        if not create:
            return
            
        # Créer des inscriptions jusqu'à atteindre la capacité
        nombre_inscriptions = min(self.capacite_max, random.randint(5, 15))
        
        for i in range(nombre_inscriptions):
            statut = 'confirmee' if i < self.capacite_max * 0.8 else 'liste_attente'
            # Créer un membre différent pour chaque inscription
            membre = MembreFactory()
            InscriptionEvenementFactory(
                evenement=self,
                membre=membre,
                statut=statut
            )


class EvenementAvecSessionsFactory(EvenementFactory):
    """Événement avec sessions multiples"""
    
    @factory.post_generation
    def avec_sessions(self, create, extracted, **kwargs):
        if not create:
            return
            
        nombre_sessions = random.randint(2, 5)
        for i in range(nombre_sessions):
            SessionEvenementFactory(
                evenement_parent=self,
                ordre_session=i + 1
            )