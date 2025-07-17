# apps/evenements/validators.py
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from datetime import timedelta

from apps.membres.models import Membre


def validate_date_evenement(value):
    """
    Valide que la date de l'événement est dans le futur
    """
    if value <= timezone.now():
        raise ValidationError(
            _("La date de l'événement doit être dans le futur."),
            code='date_passee'
        )


def validate_date_fin_evenement(date_debut, date_fin):
    """
    Valide que la date de fin est postérieure à la date de début
    """
    if date_fin and date_debut >= date_fin:
        raise ValidationError(
            _("La date de fin doit être postérieure à la date de début."),
            code='date_fin_invalide'
        )


def validate_capacite_coherente(capacite, evenement_id=None):
    """
    Valide que la capacité est cohérente avec les inscriptions existantes
    """
    if capacite <= 0:
        raise ValidationError(
            _("La capacité doit être supérieure à 0."),
            code='capacite_invalide'
        )
    
    # Si on modifie un événement existant
    if evenement_id:
        from .models import InscriptionEvenement
        inscriptions_confirmees = InscriptionEvenement.objects.filter(
            evenement_id=evenement_id,
            statut__in=['confirmee', 'presente']
        ).count()
        
        if capacite < inscriptions_confirmees:
            raise ValidationError(
                _("La capacité ne peut pas être inférieure au nombre d'inscriptions confirmées (%(count)d)."),
                params={'count': inscriptions_confirmees},
                code='capacite_insuffisante'
            )


# CORRECTION FINALE pour apps/evenements/validators.py
# REMPLACER la fonction validate_organisateur_membre (lignes ~35-55):

def validate_organisateur_membre(user):
    """
    Valide que l'organisateur est un membre actif de l'association
    """
    if not user:
        raise ValidationError(
            _("Un organisateur doit être spécifié."),
            code='organisateur_requis'
        )
    
    # SOLUTION ROBUSTE : Vérifier d'abord les membres actifs, puis les supprimés
    try:
        # Vérifier s'il existe un membre actif
        membre = Membre.objects.get(utilisateur=user)
        # Si on arrive ici, le membre existe et est actif
        return
    except Membre.DoesNotExist:
        pass  # Continuer pour vérifier s'il existe mais est supprimé
    
    # Vérifier s'il existe un membre supprimé (suppression logique)
    # Utiliser une requête brute pour contourner le manager
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT deleted_at FROM membres_membre WHERE utilisateur_id = %s", 
            [user.id]
        )
        result = cursor.fetchone()
        
        if result:
            # Le membre existe mais est supprimé (deleted_at n'est pas NULL)
            if result[0] is not None:
                raise ValidationError(
                    _("L'organisateur doit être un membre actif de l'association."),
                    code='organisateur_inactif'
                )
            # Le membre existe et est actif (deleted_at est NULL)
            # Cela ne devrait pas arriver car le premier get() aurait dû réussir
            return
        else:
            # Aucun membre trouvé
            raise ValidationError(
                _("L'organisateur doit être un membre de l'association."),
                code='organisateur_non_membre'
            )


def validate_dates_inscriptions(date_ouverture, date_fermeture, date_debut_evenement):
    """
    Valide les dates d'ouverture et fermeture des inscriptions
    """
    errors = []
    
    if date_ouverture and date_ouverture >= date_debut_evenement:
        errors.append(ValidationError(
            _("L'ouverture des inscriptions doit être avant le début de l'événement."),
            code='ouverture_trop_tardive'
        ))
    
    if date_fermeture and date_fermeture >= date_debut_evenement:
        errors.append(ValidationError(
            _("La fermeture des inscriptions doit être avant le début de l'événement."),
            code='fermeture_trop_tardive'
        ))
    
    if date_ouverture and date_fermeture and date_ouverture >= date_fermeture:
        errors.append(ValidationError(
            _("L'ouverture des inscriptions doit être avant la fermeture."),
            code='dates_inscriptions_incoherentes'
        ))
    
    if errors:
        raise ValidationError(errors)


def validate_tarifs_coherents(est_payant, tarif_membre, tarif_salarie, tarif_invite):
    """
    Valide la cohérence des tarifs
    """
    if est_payant:
        if tarif_membre < 0 or tarif_salarie < 0 or tarif_invite < 0:
            raise ValidationError(
                _("Les tarifs ne peuvent pas être négatifs."),
                code='tarifs_negatifs'
            )
        
        if tarif_membre == 0 and tarif_salarie == 0 and tarif_invite == 0:
            raise ValidationError(
                _("Au moins un tarif doit être supérieur à 0 pour un événement payant."),
                code='tarifs_tous_nuls'
            )


def validate_accompagnants_coherents(permet_accompagnants, nombre_max_accompagnants, type_evenement=None):
    """
    Valide la cohérence des paramètres d'accompagnants
    """
    if type_evenement and not type_evenement.permet_accompagnants:
        if permet_accompagnants:
            raise ValidationError(
                _("Ce type d'événement n'autorise pas les accompagnants."),
                code='accompagnants_non_autorises'
            )
    
    if permet_accompagnants and nombre_max_accompagnants <= 0:
        raise ValidationError(
            _("Le nombre maximum d'accompagnants doit être supérieur à 0 si les accompagnants sont autorisés."),
            code='nombre_accompagnants_invalide'
        )
    
    if not permet_accompagnants and nombre_max_accompagnants > 0:
        raise ValidationError(
            _("Le nombre maximum d'accompagnants doit être 0 si les accompagnants ne sont pas autorisés."),
            code='accompagnants_incoherents'
        )


def validate_recurrence_coherente(est_recurrent, evenement_parent, recurrence_config=None):
    """
    Valide la cohérence des paramètres de récurrence
    """
    if est_recurrent and evenement_parent:
        raise ValidationError(
            _("Un événement ne peut pas être récurrent et être une occurrence d'un autre événement."),
            code='recurrence_incoherente'
        )
    
    if not est_recurrent and recurrence_config:
        raise ValidationError(
            _("La configuration de récurrence ne peut être définie que pour les événements récurrents."),
            code='config_recurrence_invalide'
        )


def validate_delai_confirmation(delai_heures):
    """
    Valide le délai de confirmation
    """
    if delai_heures <= 0:
        raise ValidationError(
            _("Le délai de confirmation doit être supérieur à 0 heures."),
            code='delai_invalide'
        )
    
    if delai_heures > 168:  # 7 jours
        raise ValidationError(
            _("Le délai de confirmation ne peut pas dépasser 7 jours (168 heures)."),
            code='delai_trop_long'
        )


def validate_inscription_possible(evenement, membre, nombre_accompagnants=0):
    """
    Valide qu'un membre peut s'inscrire à un événement
    """
    # Vérifier si l'inscription est possible
    peut_inscrire, message = evenement.peut_s_inscrire(membre)
    if not peut_inscrire:
        # CORRECTION : Vérifier le message spécifique pour la cohérence des tests
        if "complet" in message.lower():
            raise ValidationError(
                _("Il n'y a pas assez de places disponibles pour s'inscrire à cet événement."),
                code='places_insuffisantes'
            )
        else:
            raise ValidationError(message, code='inscription_impossible')
    
    # Vérifier les accompagnants
    if nombre_accompagnants > 0:
        if not evenement.permet_accompagnants:
            raise ValidationError(
                _("Cet événement n'autorise pas les accompagnants."),
                code='accompagnants_non_autorises'
            )
        
        if nombre_accompagnants > evenement.nombre_max_accompagnants:
            raise ValidationError(
                _("Le nombre d'accompagnants ne peut pas dépasser %(max)d."),
                params={'max': evenement.nombre_max_accompagnants},
                code='trop_accompagnants'
            )
        
        # Vérifier si assez de places pour le membre + accompagnants
        places_necessaires = 1 + nombre_accompagnants
        if places_necessaires > evenement.places_disponibles:
            raise ValidationError(
                _("Il n'y a pas assez de places disponibles (%(places)d) pour vous et vos accompagnants."),
                params={'places': evenement.places_disponibles},
                code='places_insuffisantes'
            )


def validate_sessions_coherentes(sessions, evenement):
    """
    Valide que les sessions sélectionnées sont cohérentes avec l'événement
    """
    if not sessions:
        return
    
    # Vérifier que toutes les sessions appartiennent à l'événement
    sessions_evenement = set(evenement.sessions.values_list('id', flat=True))
    sessions_selectionnees = set(session.id for session in sessions)
    
    if not sessions_selectionnees.issubset(sessions_evenement):
        raise ValidationError(
            _("Certaines sessions sélectionnées n'appartiennent pas à cet événement."),
            code='sessions_invalides'
        )
    
    # Vérifier que toutes les sessions obligatoires sont sélectionnées
    sessions_obligatoires = set(
        evenement.sessions.filter(est_obligatoire=True).values_list('id', flat=True)
    )
    
    if not sessions_obligatoires.issubset(sessions_selectionnees):
        raise ValidationError(
            _("Toutes les sessions obligatoires doivent être sélectionnées."),
            code='sessions_obligatoires_manquantes'
        )


def validate_montant_paiement(montant, montant_attendu):
    """
    Valide le montant d'un paiement
    """
    if montant < 0:
        raise ValidationError(
            _("Le montant ne peut pas être négatif."),
            code='montant_negatif'
        )
    
    if montant > montant_attendu:
        raise ValidationError(
            _("Le montant payé (%(paye)s€) ne peut pas dépasser le montant attendu (%(attendu)s€)."),
            params={'paye': montant, 'attendu': montant_attendu},
            code='montant_excessif'
        )


def validate_periode_recherche(date_debut, date_fin):
    """
    Valide une période pour la recherche d'événements
    """
    if date_debut and date_fin and date_debut > date_fin:
        raise ValidationError(
            _("La date de début doit être antérieure à la date de fin."),
            code='periode_invalide'
        )
    
    # Limiter la période de recherche à 2 ans maximum
    if date_debut and date_fin:
        delta = date_fin - date_debut
        if delta.days > 730:  # 2 ans
            raise ValidationError(
                _("La période de recherche ne peut pas dépasser 2 ans."),
                code='periode_trop_longue'
            )


def validate_code_couleur(couleur):
    """
    Valide un code couleur hexadécimal
    """
    import re
    
    if not re.match(r'^#[0-9A-Fa-f]{6}$', couleur):
        raise ValidationError(
            _("Le code couleur doit être au format hexadécimal (#RRGGBB)."),
            code='couleur_invalide'
        )


def validate_capacite_session(capacite_session, capacite_evenement):
    """
    Valide que la capacité d'une session n'excède pas celle de l'événement
    """
    if capacite_session and capacite_session > capacite_evenement:
        raise ValidationError(
            _("La capacité de la session ne peut pas dépasser celle de l'événement (%(max)d)."),
            params={'max': capacite_evenement},
            code='capacite_session_excessive'
        )


def validate_donnees_accompagnant(nom, prenom, email=None):
    """
    Valide les données d'un accompagnant
    """
    errors = []
    
    if not nom or not nom.strip():
        errors.append(ValidationError(
            _("Le nom de l'accompagnant est requis."),
            code='nom_requis'
        ))
    
    if not prenom or not prenom.strip():
        errors.append(ValidationError(
            _("Le prénom de l'accompagnant est requis."),
            code='prenom_requis'
        ))
    
    if email and '@' not in email:
        errors.append(ValidationError(
            _("L'adresse email de l'accompagnant n'est pas valide."),
            code='email_invalide'
        ))
    
    if errors:
        raise ValidationError(errors)