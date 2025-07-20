import factory
from factory.django import DjangoModelFactory
from factory import SubFactory, LazyAttribute, Iterator, LazyFunction
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import random

from apps.accounts.models import CustomUser
from apps.membres.models import Membre, TypeMembre, MembreTypeMembre
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

class MembreFactory(DjangoModelFactory):
    """Factory pour les membres - CORRIGÉE"""
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
    
    # SUPPRESSION: type_membre n'est plus passé directement
    # Il sera ajouté via post_generation

    @factory.post_generation
    def ajouter_type_membre(obj, create, extracted, **kwargs):
        """Ajoute un type de membre après création"""
        if not create:
            return
            
        # Si un type spécifique est fourni
        if extracted:
            type_membre = extracted
        else:
            # Créer ou récupérer un type par défaut
            type_membre, created = TypeMembre.objects.get_or_create(
                libelle='Membre Standard',
                defaults={
                    'description': 'Type de membre par défaut',
                    'cotisation_requise': True
                }
            )
        
        # Utiliser la méthode du modèle pour ajouter le type
        obj.ajouter_type(type_membre, timezone.now().date())

class MembreAvecUserFactory(MembreFactory):
    """Factory pour créer un membre avec utilisateur simple (non-staff) - CORRIGÉE"""
    utilisateur = SubFactory(CustomUserFactory, is_staff=False)

    @factory.post_generation
    def ajouter_type_membre(obj, create, extracted, **kwargs):
        """Ajoute un type de membre après création"""
        if not create:
            return
            
        type_membre, created = TypeMembre.objects.get_or_create(
            libelle='Membre Standard',
            defaults={
                'description': 'Type de membre par défaut',
                'cotisation_requise': True
            }
        )
        obj.ajouter_type(type_membre, timezone.now().date())

class MembreAvecUserStaffFactory(MembreFactory):
    """Factory pour créer un membre avec utilisateur staff - CORRIGÉE"""
    utilisateur = SubFactory(CustomUserFactory, is_staff=True)

    @factory.post_generation
    def ajouter_type_membre(obj, create, extracted, **kwargs):
        """Ajoute un type de membre après création"""
        if not create:
            return
            
        type_membre, created = TypeMembre.objects.get_or_create(
            libelle='Membre Staff',
            defaults={
                'description': 'Type de membre staff',
                'cotisation_requise': False
            }
        )
        obj.ajouter_type(type_membre, timezone.now().date())


class TypeMembreFactory(DjangoModelFactory):
    """Factory pour les types de membres"""
    class Meta:
        model = TypeMembre
        django_get_or_create = ('libelle',)

    libelle = Iterator(['Étudiant', 'Salarié', 'Retraité', 'Honoraire', 'Bienfaiteur'])
    description = factory.LazyAttribute(lambda obj: f'Type membre {obj.libelle}')

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

    libelle = factory.Iterator([
        'Formation', 'Conférence', 'Atelier', 'Séminaire', 
        'Réunion', 'Sortie', 'Assemblée Générale'
    ])
    description = factory.Faker('text', max_nb_chars=200, locale='fr_FR')
    couleur_affichage = factory.LazyFunction(
        lambda: f"#{random.randint(0, 0xFFFFFF):06x}"
    )
    
    # CORRECTION : Par défaut, autoriser les accompagnants pour éviter les conflits dans les tests
    permet_accompagnants = True
    necessite_validation = False
    ordre_affichage = factory.Sequence(lambda n: n)


# CORRECTION 4: EvenementFactory - Cohérence accompagnants
class EvenementFactory(DjangoModelFactory):
    """Factory pour les événements - CORRIGÉE"""
    class Meta:
        model = Evenement

    titre = factory.Faker('sentence', nb_words=3, locale='fr_FR')
    description = factory.Faker('text', max_nb_chars=500, locale='fr_FR')

    # CORRECTION: S'assurer que le type permet les accompagnants
    type_evenement = SubFactory(
        TypeEvenementFactory, 
        permet_accompagnants=True,
        necessite_validation=False
    )
    
    # Dates futures
    date_debut = factory.LazyFunction(
        lambda: timezone.now() + timedelta(days=random.randint(1, 30))
    )
    date_fin = factory.LazyAttribute(
        lambda obj: obj.date_debut + timedelta(hours=random.randint(1, 8))
    )
    
    lieu = factory.Faker('city', locale='fr_FR')
    adresse_complete = factory.Faker('address', locale='fr_FR')
    capacite_max = factory.LazyFunction(lambda: random.randint(10, 100))
    
    # CORRECTION: Créer un membre avec utilisateur pour l'organisateur
    organisateur = factory.LazyAttribute(lambda obj: MembreAvecUserFactory().utilisateur)
    
    statut = 'publie'
    inscriptions_ouvertes = True
    
    # Par défaut événement gratuit
    est_payant = False
    tarif_membre = Decimal('0.00')
    tarif_salarie = Decimal('0.00') 
    tarif_invite = Decimal('0.00')
    
    # CORRECTION: Cohérence avec le type d'événement
    permet_accompagnants = factory.LazyAttribute(
        lambda obj: obj.type_evenement.permet_accompagnants
    )
    nombre_max_accompagnants = factory.LazyFunction(lambda: random.randint(1, 5))
    
    delai_confirmation = factory.LazyFunction(lambda: random.randint(24, 168))

# CORRECTION 5: Factory spécifique pour événements avec validation
class EvenementAvecValidationFactory(EvenementFactory):
    """Factory pour événements nécessitant validation - CORRIGÉE"""
    
    type_evenement = factory.SubFactory(
        TypeEvenementFactory,
        necessite_validation=True,
        permet_accompagnants=True  # CORRECTION: Cohérence
    )
    statut = 'en_attente_validation'
    
    @factory.post_generation
    def force_create_validation(obj, create, extracted, **kwargs):
        """Force la création de ValidationEvenement"""
        if create:
            from apps.evenements.models import ValidationEvenement
            
            ValidationEvenement.objects.get_or_create(
                evenement=obj,
                defaults={
                    'statut_validation': 'en_attente',
                    'commentaire_validation': f"Événement nécessitant validation - {obj.titre}"
                }
            )

class EvenementPayantFactory(EvenementFactory):
    """Factory pour créer des événements payants avec tarifs valides"""
    
    est_payant = True
    tarif_membre = Decimal('25.00')
    tarif_salarie = Decimal('35.00') 
    tarif_invite = Decimal('15.00')


class EvenementGratuitFactory(EvenementFactory):
    """Factory pour créer des événements gratuits explicitement"""
    
    est_payant = False
    tarif_membre = Decimal('0.00')
    tarif_salarie = Decimal('0.00') 
    tarif_invite = Decimal('0.00')
    
class InscriptionEvenementFactory(DjangoModelFactory):
    """Factory pour les inscriptions"""
    class Meta:
        model = InscriptionEvenement

    # CORRECTION : Créer un événement gratuit par défaut pour éviter les problèmes de paiement
    evenement = SubFactory(EvenementFactory, est_payant=False)
    membre = SubFactory(MembreFactory)
    
    statut = Iterator(['en_attente', 'confirmee', 'liste_attente', 'annulee'])
    date_inscription = factory.LazyFunction(lambda: timezone.now())
    
    nombre_accompagnants = factory.LazyAttribute(
        lambda obj: random.randint(0, obj.evenement.nombre_max_accompagnants) 
        if obj.evenement.permet_accompagnants else 0
    )
    
    # CORRECTION : Montant payé à 0 pour événements gratuits
    montant_paye = Decimal('0.00')
    
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
    validateur = SubFactory(CustomUserFactory)
    statut_validation = Iterator(['en_attente', 'approuve', 'refuse'])
    date_validation = factory.LazyAttribute(
        lambda obj: timezone.now() if obj.statut_validation in ['approuve', 'refuse'] else None
    )
    # CORRECTION : Nom correct de l'attribut
    commentaire_validation = factory.Faker('text', max_nb_chars=300, locale='fr_FR')
    
    # SUPPRIMER ces lignes qui n'existent pas dans le modèle :
    # date_creation = factory.LazyFunction(lambda: timezone.now())
    # date_modification = factory.LazyFunction(lambda: timezone.now())


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
            
        # CORRECTION : Créer exactement 5 inscriptions confirmées pour un événement de 20 places
        nombre_inscriptions = 5  # Au lieu de random.randint(5, 15)
        
        for i in range(nombre_inscriptions):
            statut = 'confirmee'  # Toutes confirmées
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

# Factory spéciale pour les tests de formulaires
class InscriptionEvenementTestFactory(DjangoModelFactory):
    """Factory pour les inscriptions - spéciale tests sans validation"""
    class Meta:
        model = InscriptionEvenement
        skip_postgeneration_save = True  # Éviter la validation automatique

    evenement = SubFactory(EvenementFactory)
    membre = SubFactory(MembreFactory)
    
    statut = 'en_attente'
    date_inscription = factory.LazyFunction(lambda: timezone.now())
    nombre_accompagnants = 0
    montant_paye = Decimal('0.00')
    commentaire = factory.Faker('text', max_nb_chars=100, locale='fr_FR')

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """Override create pour éviter la validation"""
        obj = model_class(**kwargs)
        obj.save(validate=False)  # Sauvegarder sans validation
        return obj


# Factory pour les récurrences sans validation
class EvenementRecurrenceTestFactory(DjangoModelFactory):
    """Factory pour les récurrences - spéciale tests"""
    class Meta:
        model = EvenementRecurrence

    evenement_parent = SubFactory(EvenementFactory, est_recurrent=True)
    frequence = 'mensuelle'
    intervalle_recurrence = 1
    date_fin_recurrence = factory.LazyAttribute(
        lambda obj: timezone.now().date() + timedelta(days=365)
    )

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """Override create pour éviter la validation"""
        obj = model_class(**kwargs)
        obj.save()
        return obj
    
# CORRECTION 6: Factory pour tests performance sans type_membre
class MembrePerformanceFactory(DjangoModelFactory):
    """Factory optimisée pour les tests de performance"""
    class Meta:
        model = Membre

    nom = factory.Sequence(lambda n: f'Nom{n}')
    prenom = factory.Sequence(lambda n: f'Prenom{n}')
    email = factory.Sequence(lambda n: f'user{n}@example.com')
    utilisateur = SubFactory(CustomUserFactory)
    date_adhesion = factory.LazyFunction(lambda: timezone.now().date())
    
    # Pas de post_generation pour la performance
    
    @classmethod
    def create_batch_with_type(cls, size, type_membre=None):
        """Crée un lot de membres avec type en une seule fois"""
        membres = cls.create_batch(size)
        
        if not type_membre:
            type_membre, _ = TypeMembre.objects.get_or_create(
                libelle='Membre Performance',
                defaults={'cotisation_requise': False}
            )
        
        # Créer les relations en masse
        relations = []
        for membre in membres:
            relations.append(MembreTypeMembre(
                membre=membre,
                type_membre=type_membre,
                date_debut=timezone.now().date()
            ))
        
        MembreTypeMembre.objects.bulk_create(relations)
        return membres