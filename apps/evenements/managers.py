# apps/evenements/managers.py
from django.db import models
from django.db.models import Q, Count, Sum, Case, When, IntegerField
from django.utils import timezone
from datetime import timedelta

from apps.core.managers import BaseManager


class TypeEvenementManager(BaseManager):
    """
    Gestionnaire pour le modèle TypeEvenement
    """
    
    def actifs(self):
        """Retourne les types d'événements actifs (non supprimés)"""
        return self.get_queryset()
    
    def necessitant_validation(self):
        """Retourne les types d'événements nécessitant une validation"""
        return self.get_queryset().filter(necessite_validation=True)
    
    def permettant_accompagnants(self):
        """Retourne les types d'événements permettant les accompagnants"""
        return self.get_queryset().filter(permet_accompagnants=True)
    
    def par_ordre_affichage(self):
        """Retourne les types triés par ordre d'affichage"""
        return self.get_queryset().order_by('ordre_affichage', 'libelle')


class EvenementQuerySet(models.QuerySet):
    """
    QuerySet personnalisé pour le modèle Evenement
    """
    
    def publies(self):
        """Événements publiés seulement"""
        return self.filter(statut='publie')
    
    def brouillons(self):
        """Événements en brouillon"""
        return self.filter(statut='brouillon')
    
    def en_attente_validation(self):
        """Événements en attente de validation"""
        return self.filter(statut='en_attente_validation')
    
    def annules(self):
        """Événements annulés"""
        return self.filter(statut='annule')
    
    def termines(self):
        """Événements terminés"""
        return self.filter(statut='termine')
    
    def a_venir(self):
        """Événements futurs (non terminés)"""
        now = timezone.now()
        return self.filter(
            Q(date_fin__gt=now) | Q(date_fin__isnull=True, date_debut__gt=now)
        )
    
    def en_cours(self):
        """Événements en cours"""
        now = timezone.now()
        return self.filter(
            date_debut__lte=now,
            Q(date_fin__gte=now) | Q(date_fin__isnull=True)
        )
    
    def passes(self):
        """Événements passés"""
        now = timezone.now()
        return self.filter(
            Q(date_fin__lt=now) | Q(date_fin__isnull=True, date_debut__lt=now)
        )
    
    def inscriptions_ouvertes(self):
        """Événements avec inscriptions ouvertes"""
        now = timezone.now()
        return self.filter(
            inscriptions_ouvertes=True,
            statut='publie'
        ).filter(
            Q(date_ouverture_inscriptions__isnull=True) | Q(date_ouverture_inscriptions__lte=now)
        ).filter(
            Q(date_fermeture_inscriptions__isnull=True) | Q(date_fermeture_inscriptions__gt=now)
        )
    
    def inscriptions_fermees(self):
        """Événements avec inscriptions fermées"""
        return self.exclude(pk__in=self.inscriptions_ouvertes().values_list('pk', flat=True))
    
    def avec_places_disponibles(self):
        """Événements ayant encore des places disponibles"""
        return self.annotate(
            inscriptions_confirmees=Count(
                'inscriptions',
                filter=Q(inscriptions__statut__in=['confirmee', 'presente'])
            )
        ).filter(
            inscriptions_confirmees__lt=models.F('capacite_max')
        )
    
    def complets(self):
        """Événements complets"""
        return self.annotate(
            inscriptions_confirmees=Count(
                'inscriptions',
                filter=Q(inscriptions__statut__in=['confirmee', 'presente'])
            )
        ).filter(
            inscriptions_confirmees__gte=models.F('capacite_max')
        )
    
    def par_type(self, type_evenement):
        """Filtrer par type d'événement"""
        if isinstance(type_evenement, str):
            return self.filter(type_evenement__libelle__icontains=type_evenement)
        return self.filter(type_evenement=type_evenement)
    
    def par_organisateur(self, organisateur):
        """Filtrer par organisateur"""
        return self.filter(organisateur=organisateur)
    
    def par_lieu(self, lieu):
        """Filtrer par lieu"""
        return self.filter(
            Q(lieu__icontains=lieu) | Q(adresse_complete__icontains=lieu)
        )
    
    def par_periode(self, date_debut=None, date_fin=None):
        """Filtrer par période"""
        queryset = self
        if date_debut:
            queryset = queryset.filter(date_debut__gte=date_debut)
        if date_fin:
            queryset = queryset.filter(date_debut__lte=date_fin)
        return queryset
    
    def payants(self):
        """Événements payants"""
        return self.filter(est_payant=True)
    
    def gratuits(self):
        """Événements gratuits"""
        return self.filter(est_payant=False)
    
    def recurrents(self):
        """Événements récurrents"""
        return self.filter(est_recurrent=True)
    
    def non_recurrents(self):
        """Événements non récurrents"""
        return self.filter(est_recurrent=False)
    
    def parents_recurrence(self):
        """Événements parents de récurrence (pas des occurrences)"""
        return self.filter(evenement_parent__isnull=True, est_recurrent=True)
    
    def occurrences_recurrence(self):
        """Occurrences d'événements récurrents"""
        return self.filter(evenement_parent__isnull=False)
    
    def permettant_accompagnants(self):
        """Événements permettant les accompagnants"""
        return self.filter(permet_accompagnants=True)
    
    def recherche(self, query):
        """Recherche textuelle dans titre, description et lieu"""
        if not query:
            return self
        
        return self.filter(
            Q(titre__icontains=query) |
            Q(description__icontains=query) |
            Q(lieu__icontains=query) |
            Q(adresse_complete__icontains=query) |
            Q(instructions_particulieres__icontains=query)
        ).distinct()
    
    def avec_statistiques(self):
        """Ajoute les statistiques d'inscriptions"""
        return self.annotate(
            total_inscriptions=Count('inscriptions'),
            inscriptions_confirmees=Count(
                'inscriptions',
                filter=Q(inscriptions__statut='confirmee')
            ),
            inscriptions_en_attente=Count(
                'inscriptions',
                filter=Q(inscriptions__statut='en_attente')
            ),
            inscriptions_liste_attente=Count(
                'inscriptions',
                filter=Q(inscriptions__statut='liste_attente')
            ),
            inscriptions_annulees=Count(
                'inscriptions',
                filter=Q(inscriptions__statut='annulee')
            ),
            total_accompagnants=Sum(
                'inscriptions__nombre_accompagnants',
                filter=Q(inscriptions__statut__in=['confirmee', 'presente'])
            ),
            taux_occupation=Case(
                When(capacite_max=0, then=0),
                default=(
                    Count(
                        'inscriptions',
                        filter=Q(inscriptions__statut__in=['confirmee', 'presente'])
                    ) * 100.0 / models.F('capacite_max')
                ),
                output_field=models.FloatField()
            )
        )


class EvenementManager(BaseManager):
    """
    Gestionnaire pour le modèle Evenement
    """
    
    def get_queryset(self):
        """Retourne le QuerySet personnalisé"""
        return EvenementQuerySet(self.model, using=self._db).filter(deleted_at__isnull=True)
    
    def publies(self):
        """Événements publiés seulement"""
        return self.get_queryset().publies()
    
    def a_venir(self):
        """Événements futurs"""
        return self.get_queryset().a_venir()
    
    def en_cours(self):
        """Événements en cours"""
        return self.get_queryset().en_cours()
    
    def passes(self):
        """Événements passés"""
        return self.get_queryset().passes()
    
    def inscriptions_ouvertes(self):
        """Événements avec inscriptions ouvertes"""
        return self.get_queryset().inscriptions_ouvertes()
    
    def avec_places_disponibles(self):
        """Événements ayant encore des places disponibles"""
        return self.get_queryset().avec_places_disponibles()
    
    def complets(self):
        """Événements complets"""
        return self.get_queryset().complets()
    
    def par_organisateur(self, organisateur):
        """Événements d'un organisateur"""
        return self.get_queryset().par_organisateur(organisateur)
    
    def recherche(self, query):
        """Recherche textuelle"""
        return self.get_queryset().recherche(query)
    
    def avec_statistiques(self):
        """Événements avec statistiques d'inscriptions"""
        return self.get_queryset().avec_statistiques()
    
    def necessitant_validation(self):
        """Événements nécessitant une validation"""
        return self.get_queryset().filter(
            type_evenement__necessite_validation=True,
            statut='en_attente_validation'
        )
    
    def prochains_pour_membre(self, membre, limite=5):
        """Prochains événements auxquels un membre peut s'inscrire"""
        from .models import InscriptionEvenement
        
        # Événements où le membre n'est pas déjà inscrit
        evenements_inscrits = InscriptionEvenement.objects.filter(
            membre=membre,
            statut__in=['en_attente', 'confirmee', 'liste_attente']
        ).values_list('evenement_id', flat=True)
        
        return self.get_queryset().publies().a_venir().inscriptions_ouvertes().exclude(
            id__in=evenements_inscrits
        ).order_by('date_debut')[:limite]
    
    def statistiques_periode(self, date_debut=None, date_fin=None):
        """Statistiques des événements sur une période"""
        queryset = self.get_queryset()
        
        if date_debut:
            queryset = queryset.filter(date_debut__gte=date_debut)
        if date_fin:
            queryset = queryset.filter(date_debut__lte=date_fin)
        
        return queryset.avec_statistiques().aggregate(
            total_evenements=Count('id'),
            evenements_publies=Count('id', filter=Q(statut='publie')),
            evenements_annules=Count('id', filter=Q(statut='annule')),
            total_inscriptions=Sum('total_inscriptions'),
            total_participants=Sum('inscriptions_confirmees'),
            taux_occupation_moyen=models.Avg('taux_occupation')
        )


class InscriptionEvenementQuerySet(models.QuerySet):
    """
    QuerySet personnalisé pour le modèle InscriptionEvenement
    """
    
    def en_attente(self):
        """Inscriptions en attente de confirmation"""
        return self.filter(statut='en_attente')
    
    def confirmees(self):
        """Inscriptions confirmées"""
        return self.filter(statut='confirmee')
    
    def liste_attente(self):
        """Inscriptions en liste d'attente"""
        return self.filter(statut='liste_attente')
    
    def annulees(self):
        """Inscriptions annulées"""
        return self.filter(statut='annulee')
    
    def presentes(self):
        """Participants présents"""
        return self.filter(statut='presente')
    
    def absentes(self):
        """Participants absents"""
        return self.filter(statut='absente')
    
    def expirees(self):
        """Inscriptions expirées"""
        return self.filter(statut='expiree')
    
    def actives(self):
        """Inscriptions actives (en attente ou confirmées)"""
        return self.filter(statut__in=['en_attente', 'confirmee'])
    
    def valides(self):
        """Inscriptions valides (confirmées ou présentes)"""
        return self.filter(statut__in=['confirmee', 'presente'])
    
    def par_evenement(self, evenement):
        """Inscriptions pour un événement"""
        return self.filter(evenement=evenement)
    
    def par_membre(self, membre):
        """Inscriptions d'un membre"""
        return self.filter(membre=membre)
    
    def en_retard_confirmation(self):
        """Inscriptions en retard de confirmation"""
        return self.filter(
            statut='en_attente',
            date_limite_confirmation__lt=timezone.now()
        )
    
    def a_confirmer_dans(self, heures=24):
        """Inscriptions à confirmer dans X heures"""
        limite = timezone.now() + timedelta(hours=heures)
        return self.filter(
            statut='en_attente',
            date_limite_confirmation__lte=limite,
            date_limite_confirmation__gt=timezone.now()
        )
    
    def avec_accompagnants(self):
        """Inscriptions avec accompagnants"""
        return self.filter(nombre_accompagnants__gt=0)
    
    def sans_accompagnants(self):
        """Inscriptions sans accompagnants"""
        return self.filter(nombre_accompagnants=0)
    
    def payees(self):
        """Inscriptions entièrement payées"""
        return self.filter(
            montant_paye__gte=models.F('evenement__tarif_membre')
        )
    
    def non_payees(self):
        """Inscriptions non payées ou partiellement payées"""
        return self.filter(
            montant_paye__lt=models.F('evenement__tarif_membre')
        )
    
    def par_periode_inscription(self, date_debut=None, date_fin=None):
        """Filtrer par période d'inscription"""
        queryset = self
        if date_debut:
            queryset = queryset.filter(date_inscription__gte=date_debut)
        if date_fin:
            queryset = queryset.filter(date_inscription__lte=date_fin)
        return queryset
    
    def avec_details_paiement(self):
        """Ajoute les détails de paiement calculés"""
        return self.annotate(
            montant_total_attendu=Case(
                When(evenement__est_payant=False, then=0),
                default=(
                    models.F('evenement__tarif_membre') +
                    (models.F('nombre_accompagnants') * models.F('evenement__tarif_invite'))
                ),
                output_field=models.DecimalField(max_digits=10, decimal_places=2)
            ),
            montant_restant_calculé=Case(
                When(evenement__est_payant=False, then=0),
                default=models.F('montant_total_attendu') - models.F('montant_paye'),
                output_field=models.DecimalField(max_digits=10, decimal_places=2)
            ),
            est_completement_payee=Case(
                When(montant_restant_calculé__lte=0, then=True),
                default=False,
                output_field=models.BooleanField()
            )
        )


class InscriptionEvenementManager(BaseManager):
    """
    Gestionnaire pour le modèle InscriptionEvenement
    """
    
    def get_queryset(self):
        """Retourne le QuerySet personnalisé"""
        return InscriptionEvenementQuerySet(self.model, using=self._db).filter(deleted_at__isnull=True)
    
    def confirmees(self):
        """Inscriptions confirmées"""
        return self.get_queryset().confirmees()
    
    def en_attente_confirmation(self):
        """Inscriptions en attente de confirmation"""
        return self.get_queryset().en_attente()
    
    def liste_attente(self):
        """Inscriptions en liste d'attente"""
        return self.get_queryset().liste_attente()
    
    def actives(self):
        """Inscriptions actives"""
        return self.get_queryset().actives()
    
    def valides(self):
        """Inscriptions valides"""
        return self.get_queryset().valides()
    
    def par_evenement(self, evenement):
        """Inscriptions pour un événement"""
        return self.get_queryset().par_evenement(evenement)
    
    def par_membre(self, membre):
        """Inscriptions d'un membre"""
        return self.get_queryset().par_membre(membre)
    
    def en_retard_confirmation(self):
        """Inscriptions en retard de confirmation"""
        return self.get_queryset().en_retard_confirmation()
    
    def a_traiter_urgence(self):
        """Inscriptions nécessitant une action urgente"""
        return self.get_queryset().en_retard_confirmation()
    
    def rappels_a_envoyer(self, heures_avant=24):
        """Inscriptions nécessitant un rappel"""
        return self.get_queryset().a_confirmer_dans(heures_avant)
    
    def avec_details_paiement(self):
        """Inscriptions avec détails de paiement"""
        return self.get_queryset().avec_details_paiement()
    
    def statistiques_membre(self, membre):
        """Statistiques d'inscription pour un membre"""
        queryset = self.get_queryset().par_membre(membre)
        
        return queryset.aggregate(
            total_inscriptions=Count('id'),
            inscriptions_confirmees=Count('id', filter=Q(statut='confirmee')),
            inscriptions_annulees=Count('id', filter=Q(statut='annulee')),
            inscriptions_presentes=Count('id', filter=Q(statut='presente')),
            total_accompagnants=Sum('nombre_accompagnants'),
            montant_total_paye=Sum('montant_paye')
        )
    
    def statistiques_evenement(self, evenement):
        """Statistiques d'inscription pour un événement"""
        queryset = self.get_queryset().par_evenement(evenement)
        
        return queryset.aggregate(
            total_inscriptions=Count('id'),
            inscriptions_confirmees=Count('id', filter=Q(statut='confirmee')),
            inscriptions_en_attente=Count('id', filter=Q(statut='en_attente')),
            inscriptions_liste_attente=Count('id', filter=Q(statut='liste_attente')),
            inscriptions_annulees=Count('id', filter=Q(statut='annulee')),
            total_accompagnants=Sum('nombre_accompagnants'),
            montant_total_collecte=Sum('montant_paye'),
            taux_confirmation=Case(
                When(total_inscriptions=0, then=0),
                default=(Count('id', filter=Q(statut='confirmee')) * 100.0 / Count('id')),
                output_field=models.FloatField()
            )
        )
    
    def nettoyer_inscriptions_expirees(self):
        """Marque comme expirées les inscriptions dépassant le délai"""
        inscriptions_expirees = self.en_retard_confirmation()
        
        for inscription in inscriptions_expirees:
            inscription.statut = 'expiree'
            inscription.save()
            
            # Promouvoir depuis la liste d'attente
            inscription.evenement.promouvoir_liste_attente()
        
        return inscriptions_expirees.count()


class AccompagnantInviteManager(BaseManager):
    """
    Gestionnaire pour le modèle AccompagnantInvite
    """
    
    def accompagnants(self):
        """Accompagnants seulement"""
        return self.get_queryset().filter(est_accompagnant=True)
    
    def invites_externes(self):
        """Invités externes seulement"""
        return self.get_queryset().filter(est_accompagnant=False)
    
    def confirmes(self):
        """Accompagnants/invités confirmés"""
        return self.get_queryset().filter(statut='confirme')
    
    def en_attente(self):
        """En attente de réponse"""
        return self.get_queryset().filter(statut='invite')
    
    def refuses(self):
        """Ayant refusé l'invitation"""
        return self.get_queryset().filter(statut='refuse')
    
    def presents(self):
        """Présents à l'événement"""
        return self.get_queryset().filter(statut='present')
    
    def par_inscription(self, inscription):
        """Accompagnants pour une inscription"""
        return self.get_queryset().filter(inscription=inscription)
    
    def par_evenement(self, evenement):
        """Accompagnants pour un événement"""
        return self.get_queryset().filter(inscription__evenement=evenement)
    
    def avec_restrictions_alimentaires(self):
        """Accompagnants avec restrictions alimentaires"""
        return self.get_queryset().exclude(restrictions_alimentaires='')


class ValidationEvenementManager(BaseManager):
    """
    Gestionnaire pour le modèle ValidationEvenement
    """
    
    def en_attente(self):
        """Validations en attente"""
        return self.get_queryset().filter(statut_validation='en_attente')
    
    def approuvees(self):
        """Validations approuvées"""
        return self.get_queryset().filter(statut_validation='approuve')
    
    def refusees(self):
        """Validations refusées"""
        return self.get_queryset().filter(statut_validation='refuse')
    
    def par_validateur(self, validateur):
        """Validations par un validateur"""
        return self.get_queryset().filter(validateur=validateur)
    
    def urgentes(self, jours=7):
        """Validations urgentes (événements dans X jours)"""
        limite = timezone.now() + timedelta(days=jours)
        return self.en_attente().filter(
            evenement__date_debut__lte=limite
        )
    
    def statistiques_validateur(self, validateur):
        """Statistiques de validation pour un validateur"""
        queryset = self.get_queryset().par_validateur(validateur)
        
        return queryset.aggregate(
            total_validations=Count('id'),
            validations_approuvees=Count('id', filter=Q(statut_validation='approuve')),
            validations_refusees=Count('id', filter=Q(statut_validation='refuse')),
            validations_en_attente=Count('id', filter=Q(statut_validation='en_attente'))
        )


class SessionEvenementManager(BaseManager):
    """
    Gestionnaire pour le modèle SessionEvenement
    """
    
    def par_evenement(self, evenement):
        """Sessions pour un événement"""
        return self.get_queryset().filter(evenement_parent=evenement)
    
    def obligatoires(self):
        """Sessions obligatoires"""
        return self.get_queryset().filter(est_obligatoire=True)
    
    def optionnelles(self):
        """Sessions optionnelles"""
        return self.get_queryset().filter(est_obligatoire=False)
    
    def par_intervenant(self, intervenant):
        """Sessions d'un intervenant"""
        return self.get_queryset().filter(intervenant__icontains=intervenant)
    
    def chronologique(self):
        """Sessions triées par ordre chronologique"""
        return self.get_queryset().order_by('date_debut_session')


class EvenementRecurrenceManager(BaseManager):
    """
    Gestionnaire pour le modèle EvenementRecurrence
    """
    
    def hebdomadaires(self):
        """Récurrences hebdomadaires"""
        return self.get_queryset().filter(frequence='hebdomadaire')
    
    def mensuelles(self):
        """Récurrences mensuelles"""
        return self.get_queryset().filter(frequence='mensuelle')
    
    def annuelles(self):
        """Récurrences annuelles"""
        return self.get_queryset().filter(frequence='annuelle')
    
    def actives(self):
        """Récurrences actives (non terminées)"""
        now = timezone.now().date()
        return self.get_queryset().filter(
            Q(date_fin_recurrence__isnull=True) | Q(date_fin_recurrence__gte=now)
        )
    
    def a_traiter(self):
        """Récurrences nécessitant la génération d'occurrences"""
        # Logique pour identifier les récurrences nécessitant de nouvelles occurrences
        return self.actives()