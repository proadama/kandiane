# apps/cotisations/admin.py
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.db.models import Sum, Count

from .models import (
    Cotisation, Paiement, ModePaiement, BaremeCotisation,
    Rappel, HistoriqueCotisation, ConfigurationCotisation
)


class PaiementInline(admin.TabularInline):
    model = Paiement
    extra = 0
    fields = ('date_paiement', 'montant', 'mode_paiement', 'type_transaction', 'reference_paiement')
    readonly_fields = ('date_paiement',)


class RappelInline(admin.TabularInline):
    model = Rappel
    extra = 0
    fields = ('date_envoi', 'type_rappel', 'etat', 'niveau')
    readonly_fields = ('date_envoi',)


@admin.register(Cotisation)
class CotisationAdmin(admin.ModelAdmin):
    list_display = ('reference', 'membre', 'montant', 'date_emission', 'date_echeance', 
                    'statut_paiement', 'montant_restant', 'est_en_retard')
    list_filter = ('statut_paiement', 'date_emission', 'date_echeance', 'annee', 'statut')
    search_fields = ('reference', 'membre__nom', 'membre__prenom', 'membre__email')
    date_hierarchy = 'date_emission'
    inlines = [PaiementInline, RappelInline]
    readonly_fields = ('reference', 'created_at', 'updated_at', 'montant_restant', 'cree_par')
    fieldsets = (
        (_('Informations de base'), {
            'fields': ('reference', 'membre', 'montant', 'type_membre', 'bareme', 'statut')
        }),
        (_('Dates'), {
            'fields': ('date_emission', 'date_echeance', 'periode_debut', 'periode_fin')
        }),
        (_('Statut de paiement'), {
            'fields': ('statut_paiement', 'montant_restant')
        }),
        (_('Informations complémentaires'), {
            'fields': ('mois', 'annee', 'commentaire', 'metadata')
        }),
        (_('Audit'), {
            'fields': ('cree_par', 'modifie_par', 'created_at', 'updated_at')
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('membre', 'type_membre', 'statut')
    
    def save_model(self, request, obj, form, change):
        if not change:  # Si création
            obj.cree_par = request.user
        else:  # Si modification
            obj.modifie_par = request.user
        super().save_model(request, obj, form, change)
    
    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(self.readonly_fields)
        if obj:  # Si modification
            # Rendre certains champs non modifiables une fois la cotisation créée
            readonly_fields.extend(['membre', 'montant'])
        return readonly_fields


@admin.register(Paiement)
class PaiementAdmin(admin.ModelAdmin):
    list_display = ('cotisation', 'montant', 'date_paiement', 'mode_paiement', 'type_transaction')
    list_filter = ('type_transaction', 'mode_paiement', 'date_paiement')
    search_fields = ('cotisation__reference', 'cotisation__membre__nom', 'cotisation__membre__prenom')
    date_hierarchy = 'date_paiement'
    readonly_fields = ('created_at', 'updated_at', 'cree_par')
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('cotisation', 'cotisation__membre', 'mode_paiement')
    
    def save_model(self, request, obj, form, change):
        if not change:  # Si création
            obj.cree_par = request.user
        else:  # Si modification
            obj.modifie_par = request.user
        super().save_model(request, obj, form, change)


@admin.register(ModePaiement)
class ModePaiementAdmin(admin.ModelAdmin):
    list_display = ('libelle', 'actif')
    list_filter = ('actif',)
    search_fields = ('libelle', 'description')


@admin.register(BaremeCotisation)
class BaremeCotisationAdmin(admin.ModelAdmin):
    list_display = ('type_membre', 'montant', 'periodicite', 'date_debut_validite', 'date_fin_validite', 'est_actif')
    list_filter = ('periodicite', 'date_debut_validite')
    search_fields = ('type_membre__libelle', 'description')
    date_hierarchy = 'date_debut_validite'


@admin.register(Rappel)
class RappelAdmin(admin.ModelAdmin):
    list_display = ('membre', 'cotisation', 'type_rappel', 'date_envoi', 'etat', 'niveau')
    list_filter = ('type_rappel', 'etat', 'niveau', 'date_envoi')
    search_fields = ('membre__nom', 'membre__prenom', 'contenu')
    date_hierarchy = 'date_envoi'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('membre', 'cotisation')


@admin.register(HistoriqueCotisation)
class HistoriqueCotisationAdmin(admin.ModelAdmin):
    list_display = ('cotisation', 'action', 'date_action', 'utilisateur')
    list_filter = ('action', 'date_action')
    search_fields = ('cotisation__reference', 'details', 'commentaire')
    date_hierarchy = 'date_action'
    readonly_fields = ('cotisation', 'action', 'details', 'date_action', 'utilisateur', 'adresse_ip')
    
    def has_add_permission(self, request):
        return False  # Interdire l'ajout manuel d'historique
    
    def has_change_permission(self, request, obj=None):
        return False  # Interdire la modification manuelle d'historique


@admin.register(ConfigurationCotisation)
class ConfigurationCotisationAdmin(admin.ModelAdmin):
    list_display = ('cle', 'valeur')
    search_fields = ('cle', 'valeur', 'description')