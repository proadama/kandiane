# apps/evenements/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from django.db.models import Count

from .models import (
    TypeEvenement, Evenement, EvenementRecurrence, SessionEvenement,
    InscriptionEvenement, AccompagnantInvite, ValidationEvenement
)


@admin.register(TypeEvenement)
class TypeEvenementAdmin(admin.ModelAdmin):
    """
    Interface d'administration pour les types d'événements
    """
    list_display = [
        'libelle', 'couleur_badge', 'necessite_validation', 
        'permet_accompagnants', 'ordre_affichage', 'created_at'
    ]
    list_filter = ['necessite_validation', 'permet_accompagnants', 'created_at']
    search_fields = ['libelle', 'description']
    ordering = ['ordre_affichage', 'libelle']
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('libelle', 'description', 'couleur_affichage', 'ordre_affichage')
        }),
        ('Configuration', {
            'fields': ('necessite_validation', 'permet_accompagnants')
        }),
        ('Comportements spécifiques', {
            'fields': ('comportements_specifiques',),
            'classes': ('collapse',),
            'description': 'Configuration JSON pour les comportements spécifiques à ce type d\'événement'
        })
    )
    
    def couleur_badge(self, obj):
        """Affiche un badge coloré avec la couleur du type"""
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 3px;">{}</span>',
            obj.couleur_affichage,
            obj.libelle
        )
    couleur_badge.short_description = 'Couleur'


class SessionEvenementInline(admin.TabularInline):
    """
    Inline pour les sessions d'événements
    """
    model = SessionEvenement
    extra = 0
    fields = [
        'ordre_session', 'titre_session', 'date_debut_session', 
        'date_fin_session', 'capacite_session', 'est_obligatoire', 'intervenant'
    ]
    ordering = ['ordre_session']


class EvenementRecurrenceInline(admin.StackedInline):
    """
    Inline pour la configuration de récurrence
    """
    model = EvenementRecurrence
    extra = 0
    max_num = 1
    fields = [
        'frequence', 'intervalle_recurrence', 'jours_semaine',
        'date_fin_recurrence', 'nombre_occurrences_max'
    ]


class ValidationEvenementInline(admin.StackedInline):
    """
    Inline pour la validation d'événements
    """
    model = ValidationEvenement
    extra = 0
    max_num = 1
    fields = [
        'statut_validation', 'validateur', 'date_validation',
        'commentaire_validation', 'modifications_demandees'
    ]
    readonly_fields = ['date_validation']


@admin.register(Evenement)
class EvenementAdmin(admin.ModelAdmin):
    """
    Interface d'administration pour les événements
    """
    list_display = [
        'titre', 'type_evenement', 'statut_badge', 'date_debut', 
        'organisateur', 'places_info', 'inscriptions_count', 'created_at'
    ]
    list_filter = [
        'statut', 'type_evenement', 'est_payant', 'permet_accompagnants',
        'inscriptions_ouvertes', 'date_debut', 'created_at'
    ]
    search_fields = [
        'titre', 'description', 'lieu', 'organisateur__first_name', 
        'organisateur__last_name', 'reference'
    ]
    date_hierarchy = 'date_debut'
    ordering = ['-date_debut']
    
    fieldsets = (
        ('Informations générales', {
            'fields': (
                'titre', 'description', 'type_evenement', 'organisateur',
                'reference', 'image'
            )
        }),
        ('Dates et lieu', {
            'fields': (
                'date_debut', 'date_fin', 'lieu', 'adresse_complete'
            )
        }),
        ('Inscriptions', {
            'fields': (
                'capacite_max', 'inscriptions_ouvertes',
                'date_ouverture_inscriptions', 'date_fermeture_inscriptions',
                'delai_confirmation'
            )
        }),
        ('Tarification', {
            'fields': (
                'est_payant', 'tarif_membre', 'tarif_salarie', 'tarif_invite'
            )
        }),
        ('Accompagnants', {
            'fields': (
                'permet_accompagnants', 'nombre_max_accompagnants'
            )
        }),
        ('Récurrence', {
            'fields': ('est_recurrent', 'evenement_parent'),
            'classes': ('collapse',)
        }),
        ('Informations complémentaires', {
            'fields': (
                'instructions_particulieres', 'materiel_requis'
            ),
            'classes': ('collapse',)
        }),
        ('Statut', {
            'fields': ('statut',)
        })
    )
    
    readonly_fields = ['reference']
    
    inlines = [SessionEvenementInline, EvenementRecurrenceInline, ValidationEvenementInline]
    
    actions = ['publier_evenements', 'annuler_evenements', 'dupliquer_evenements']
    
    def get_queryset(self, request):
        """Optimise les requêtes avec les relations"""
        return super().get_queryset(request).select_related(
            'type_evenement', 'organisateur'
        ).annotate(
            inscriptions_count=Count('inscriptions')
        )
    
    def statut_badge(self, obj):
        """Affiche un badge coloré selon le statut"""
        colors = {
            'brouillon': '#6c757d',
            'en_attente_validation': '#ffc107',
            'publie': '#28a745',
            'annule': '#dc3545',
            'termine': '#17a2b8',
            'reporte': '#fd7e14'
        }
        color = colors.get(obj.statut, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 3px;">{}</span>',
            color,
            obj.get_statut_display()
        )
    statut_badge.short_description = 'Statut'
    
    def places_info(self, obj):
        """Affiche les informations sur les places"""
        places_prises = obj.inscriptions.filter(statut__in=['confirmee', 'presente']).count()
        return f"{places_prises}/{obj.capacite_max}"
    places_info.short_description = 'Places (prises/total)'
    
    def inscriptions_count(self, obj):
        """Affiche le nombre total d'inscriptions"""
        return obj.inscriptions_count
    inscriptions_count.short_description = 'Inscriptions'
    inscriptions_count.admin_order_field = 'inscriptions_count'
    
    def publier_evenements(self, request, queryset):
        """Action pour publier des événements"""
        count = queryset.filter(statut='brouillon').update(statut='publie')
        self.message_user(request, f"{count} événement(s) publié(s).")
    publier_evenements.short_description = "Publier les événements sélectionnés"
    
    def annuler_evenements(self, request, queryset):
        """Action pour annuler des événements"""
        count = queryset.exclude(statut='annule').update(statut='annule')
        self.message_user(request, f"{count} événement(s) annulé(s).")
    annuler_evenements.short_description = "Annuler les événements sélectionnés"
    
    def dupliquer_evenements(self, request, queryset):
        """Action pour dupliquer des événements"""
        count = 0
        for evenement in queryset:
            # Créer une copie
            nouveau_titre = f"Copie de {evenement.titre}"
            evenement.pk = None
            evenement.titre = nouveau_titre
            evenement.statut = 'brouillon'
            evenement.reference = None  # Sera régénéré
            evenement.save()
            count += 1
        self.message_user(request, f"{count} événement(s) dupliqué(s).")
    dupliquer_evenements.short_description = "Dupliquer les événements sélectionnés"


class AccompagnantInviteInline(admin.TabularInline):
    """
    Inline pour les accompagnants
    """
    model = AccompagnantInvite
    extra = 0
    fields = [
        'nom', 'prenom', 'email', 'statut', 'est_accompagnant',
        'date_invitation', 'date_reponse'
    ]
    readonly_fields = ['date_invitation', 'date_reponse']


@admin.register(InscriptionEvenement)
class InscriptionEvenementAdmin(admin.ModelAdmin):
    """
    Interface d'administration pour les inscriptions
    """
    list_display = [
        'membre', 'evenement', 'statut_badge', 'date_inscription',
        'nombre_accompagnants', 'montant_info', 'date_limite_confirmation'
    ]
    list_filter = [
        'statut', 'evenement__type_evenement', 'date_inscription',
        'evenement__date_debut', 'mode_paiement'
    ]
    search_fields = [
        'membre__nom', 'membre__prenom', 'membre__email',
        'evenement__titre', 'code_confirmation'
    ]
    date_hierarchy = 'date_inscription'
    ordering = ['-date_inscription']
    
    fieldsets = (
        ('Inscription', {
            'fields': (
                'evenement', 'membre', 'statut', 'date_inscription',
                'date_confirmation', 'date_limite_confirmation'
            )
        }),
        ('Accompagnants', {
            'fields': (
                'nombre_accompagnants', 'details_accompagnants'
            )
        }),
        ('Paiement', {
            'fields': (
                'montant_paye', 'mode_paiement', 'reference_paiement'
            )
        }),
        ('Informations techniques', {
            'fields': (
                'code_confirmation', 'adresse_ip', 'commentaire'
            ),
            'classes': ('collapse',)
        })
    )
    
    readonly_fields = [
        'date_inscription', 'date_confirmation', 'code_confirmation'
    ]
    
    inlines = [AccompagnantInviteInline]
    
    actions = ['confirmer_inscriptions', 'annuler_inscriptions']
    
    def get_queryset(self, request):
        """Optimise les requêtes"""
        return super().get_queryset(request).select_related(
            'membre', 'evenement', 'mode_paiement'
        )
    
    def statut_badge(self, obj):
        """Affiche un badge coloré selon le statut"""
        colors = {
            'en_attente': '#ffc107',
            'confirmee': '#28a745',
            'liste_attente': '#fd7e14',
            'annulee': '#dc3545',
            'presente': '#17a2b8',
            'absente': '#6c757d',
            'expiree': '#dc3545'
        }
        color = colors.get(obj.statut, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 3px;">{}</span>',
            color,
            obj.get_statut_display()
        )
    statut_badge.short_description = 'Statut'
    
    def montant_info(self, obj):
        """Affiche les informations de paiement"""
        montant_total = obj.calculer_montant_total()
        if montant_total > 0:
            return f"{obj.montant_paye}€ / {montant_total}€"
        return "Gratuit"
    montant_info.short_description = 'Paiement (payé/total)'
    
    def confirmer_inscriptions(self, request, queryset):
        """Action pour confirmer des inscriptions"""
        count = 0
        for inscription in queryset.filter(statut='en_attente'):
            if inscription.confirmer_inscription():
                count += 1
        self.message_user(request, f"{count} inscription(s) confirmée(s).")
    confirmer_inscriptions.short_description = "Confirmer les inscriptions sélectionnées"
    
    def annuler_inscriptions(self, request, queryset):
        """Action pour annuler des inscriptions"""
        count = 0
        for inscription in queryset.filter(statut__in=['en_attente', 'confirmee']):
            if inscription.annuler_inscription("Annulation administrative"):
                count += 1
        self.message_user(request, f"{count} inscription(s) annulée(s).")
    annuler_inscriptions.short_description = "Annuler les inscriptions sélectionnées"


@admin.register(AccompagnantInvite)
class AccompagnantInviteAdmin(admin.ModelAdmin):
    """
    Interface d'administration pour les accompagnants
    """
    list_display = [
        'nom_complet', 'inscription', 'type_personne', 'statut_badge',
        'email', 'date_invitation', 'date_reponse'
    ]
    list_filter = [
        'statut', 'est_accompagnant', 'date_invitation',
        'inscription__evenement__type_evenement'
    ]
    search_fields = [
        'nom', 'prenom', 'email',
        'inscription__membre__nom', 'inscription__evenement__titre'
    ]
    date_hierarchy = 'date_invitation'
    ordering = ['-date_invitation']
    
    fieldsets = (
        ('Informations personnelles', {
            'fields': ('nom', 'prenom', 'email', 'telephone')
        }),
        ('Statut', {
            'fields': ('statut', 'est_accompagnant', 'date_invitation', 'date_reponse')
        }),
        ('Inscription liée', {
            'fields': ('inscription',)
        }),
        ('Informations complémentaires', {
            'fields': ('restrictions_alimentaires', 'commentaire'),
            'classes': ('collapse',)
        })
    )
    
    readonly_fields = ['date_invitation', 'date_reponse']
    
    def get_queryset(self, request):
        """Optimise les requêtes"""
        return super().get_queryset(request).select_related(
            'inscription__membre', 'inscription__evenement'
        )
    
    def nom_complet(self, obj):
        """Retourne le nom complet"""
        return obj.nom_complet
    nom_complet.short_description = 'Nom complet'
    
    def type_personne(self, obj):
        """Affiche le type de personne"""
        return "Accompagnant" if obj.est_accompagnant else "Invité externe"
    type_personne.short_description = 'Type'
    
    def statut_badge(self, obj):
        """Affiche un badge coloré selon le statut"""
        colors = {
            'invite': '#ffc107',
            'confirme': '#28a745',
            'refuse': '#dc3545',
            'present': '#17a2b8',
            'absent': '#6c757d'
        }
        color = colors.get(obj.statut, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 3px;">{}</span>',
            color,
            obj.get_statut_display()
        )
    statut_badge.short_description = 'Statut'


@admin.register(ValidationEvenement)
class ValidationEvenementAdmin(admin.ModelAdmin):
    """
    Interface d'administration pour les validations d'événements
    """
    list_display = [
        'evenement', 'statut_badge', 'validateur', 'date_validation',
        'evenement_date', 'urgence_badge'
    ]
    list_filter = [
        'statut_validation', 'date_validation', 'evenement__type_evenement'
    ]
    search_fields = [
        'evenement__titre', 'validateur__first_name', 'validateur__last_name',
        'commentaire_validation'
    ]
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    fieldsets = (
        ('Événement à valider', {
            'fields': ('evenement',)
        }),
        ('Validation', {
            'fields': (
                'statut_validation', 'validateur', 'date_validation',
                'commentaire_validation'
            )
        }),
        ('Historique des modifications', {
            'fields': ('modifications_demandees',),
            'classes': ('collapse',)
        })
    )
    
    readonly_fields = ['date_validation']
    
    actions = ['approuver_evenements', 'refuser_evenements']
    
    def get_queryset(self, request):
        """Optimise les requêtes"""
        return super().get_queryset(request).select_related(
            'evenement', 'validateur'
        )
    
    def statut_badge(self, obj):
        """Affiche un badge coloré selon le statut"""
        colors = {
            'en_attente': '#ffc107',
            'approuve': '#28a745',
            'refuse': '#dc3545'
        }
        color = colors.get(obj.statut_validation, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 3px;">{}</span>',
            color,
            obj.get_statut_validation_display()
        )
    statut_badge.short_description = 'Statut validation'
    
    def evenement_date(self, obj):
        """Affiche la date de l'événement"""
        return obj.evenement.date_debut.strftime('%d/%m/%Y %H:%M')
    evenement_date.short_description = 'Date événement'
    
    def urgence_badge(self, obj):
        """Affiche un badge d'urgence si l'événement est proche"""
        if obj.statut_validation == 'en_attente':
            jours_restants = (obj.evenement.date_debut.date() - timezone.now().date()).days
            if jours_restants <= 7:
                return format_html(
                    '<span style="background-color: #dc3545; color: white; padding: 2px 8px; border-radius: 3px;">URGENT (J-{})</span>',
                    jours_restants
                )
            elif jours_restants <= 14:
                return format_html(
                    '<span style="background-color: #ffc107; color: black; padding: 2px 8px; border-radius: 3px;">J-{}</span>',
                    jours_restants
                )
        return ""
    urgence_badge.short_description = 'Urgence'
    
    def approuver_evenements(self, request, queryset):
        """Action pour approuver des événements"""
        count = 0
        for validation in queryset.filter(statut_validation='en_attente'):
            validation.approuver(request.user, "Approbation en masse")
            count += 1
        self.message_user(request, f"{count} événement(s) approuvé(s).")
    approuver_evenements.short_description = "Approuver les événements sélectionnés"
    
    def refuser_evenements(self, request, queryset):
        """Action pour refuser des événements"""
        count = 0
        for validation in queryset.filter(statut_validation='en_attente'):
            validation.refuser(request.user, "Refus en masse - voir détails individuels")
            count += 1
        self.message_user(request, f"{count} événement(s) refusé(s).")
    refuser_evenements.short_description = "Refuser les événements sélectionnés"


@admin.register(EvenementRecurrence)
class EvenementRecurrenceAdmin(admin.ModelAdmin):
    """
    Interface d'administration pour les récurrences
    """
    list_display = [
        'evenement_parent', 'frequence', 'intervalle_recurrence',
        'date_fin_recurrence', 'nombre_occurrences_max', 'est_active'
    ]
    list_filter = ['frequence', 'date_fin_recurrence']
    search_fields = ['evenement_parent__titre']
    
    fieldsets = (
        ('Événement parent', {
            'fields': ('evenement_parent',)
        }),
        ('Configuration de récurrence', {
            'fields': (
                'frequence', 'intervalle_recurrence', 'jours_semaine'
            )
        }),
        ('Limites', {
            'fields': ('date_fin_recurrence', 'nombre_occurrences_max')
        })
    )
    
    def est_active(self, obj):
        """Indique si la récurrence est encore active"""
        if obj.date_fin_recurrence:
            return obj.date_fin_recurrence >= timezone.now().date()
        return True
    est_active.boolean = True
    est_active.short_description = 'Active'


@admin.register(SessionEvenement)
class SessionEvenementAdmin(admin.ModelAdmin):
    """
    Interface d'administration pour les sessions
    """
    list_display = [
        'evenement_parent', 'titre_session', 'ordre_session',
        'date_debut_session', 'capacite_session', 'est_obligatoire', 'intervenant'
    ]
    list_filter = [
        'est_obligatoire', 'evenement_parent__type_evenement',
        'date_debut_session'
    ]
    search_fields = [
        'titre_session', 'evenement_parent__titre', 'intervenant'
    ]
    date_hierarchy = 'date_debut_session'
    ordering = ['evenement_parent', 'ordre_session']
    
    fieldsets = (
        ('Événement parent', {
            'fields': ('evenement_parent',)
        }),
        ('Informations de session', {
            'fields': (
                'titre_session', 'description_session', 'ordre_session',
                'est_obligatoire', 'intervenant'
            )
        }),
        ('Dates et capacité', {
            'fields': (
                'date_debut_session', 'date_fin_session', 'capacite_session'
            )
        })
    )


# Configuration du site d'administration
admin.site.site_header = "Administration - Gestion d'Association"
admin.site.site_title = "Admin Association"
admin.site.index_title = "Gestion des Événements"