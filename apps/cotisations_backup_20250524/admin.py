# apps/cotisations/admin.py
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.db.models import Sum, Count
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import RappelTemplate


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


@admin.register(RappelTemplate)
class RappelTemplateAdmin(admin.ModelAdmin):
    """
    Administration des templates de rappel.
    """
    list_display = [
        'nom', 'type_template_display', 'type_rappel_display', 
        'niveau_range', 'langue', 'actif_display', 'ordre_affichage',
        'actions_admin'
    ]
    list_filter = [
        'type_template', 'type_rappel', 'actif', 'langue', 
        'niveau_min', 'niveau_max'
    ]
    search_fields = ['nom', 'contenu', 'sujet']
    ordering = ['type_template', 'ordre_affichage', 'nom']
    
    fieldsets = (
        (_('Informations générales'), {
            'fields': ('nom', 'type_template', 'type_rappel', 'langue', 'actif')
        }),
        (_('Niveaux d\'application'), {
            'fields': ('niveau_min', 'niveau_max', 'ordre_affichage'),
            'description': _('Définit pour quels niveaux de rappel ce template est disponible')
        }),
        (_('Contenu du template'), {
            'fields': ('sujet', 'contenu'),
            'classes': ('wide',)
        }),
        (_('Paramètres avancés'), {
            'fields': ('variables_supplementaires',),
            'classes': ('collapse',),
            'description': _('Variables personnalisées au format JSON')
        }),
    )
    
    def type_template_display(self, obj):
        """Affichage coloré du type de template."""
        colors = {
            'standard': '#28a745',  # vert
            'urgent': '#ffc107',    # jaune
            'formal': '#dc3545',    # rouge
            'custom': '#6c757d'     # gris
        }
        color = colors.get(obj.type_template, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_type_template_display()
        )
    type_template_display.short_description = _('Type de template')
    type_template_display.admin_order_field = 'type_template'
    
    def type_rappel_display(self, obj):
        """Affichage avec icône du type de rappel."""
        icons = {
            'email': '📧',
            'sms': '📱',
            'courrier': '📮',
            'appel': '📞'
        }
        icon = icons.get(obj.type_rappel, '📄')
        return f"{icon} {obj.get_type_rappel_display()}"
    type_rappel_display.short_description = _('Type de rappel')
    type_rappel_display.admin_order_field = 'type_rappel'
    
    def niveau_range(self, obj):
        """Affichage de la plage de niveaux."""
        if obj.niveau_min == obj.niveau_max:
            return f"Niveau {obj.niveau_min}"
        return f"Niveaux {obj.niveau_min}-{obj.niveau_max}"
    niveau_range.short_description = _('Niveaux')
    
    def actif_display(self, obj):
        """Affichage visuel du statut actif."""
        if obj.actif:
            return format_html(
                '<span style="color: green;">✓ {}</span>',
                _('Actif')
            )
        else:
            return format_html(
                '<span style="color: red;">✗ {}</span>',
                _('Inactif')
            )
    actif_display.short_description = _('Statut')
    actif_display.admin_order_field = 'actif'
    
    def actions_admin(self, obj):
        """Liens d'actions personnalisées."""
        actions = []
        
        # Bouton de prévisualisation
        preview_url = reverse('admin:cotisations_rappeltemplate_preview', args=[obj.pk])
        actions.append(
            f'<a href="{preview_url}" class="button" target="_blank">Prévisualiser</a>'
        )
        
        # Bouton de duplication
        duplicate_url = reverse('admin:cotisations_rappeltemplate_duplicate', args=[obj.pk])
        actions.append(
            f'<a href="{duplicate_url}" class="button">Dupliquer</a>'
        )
        
        return mark_safe(' '.join(actions))
    actions_admin.short_description = _('Actions')
    
    def save_model(self, request, obj, form, change):
        """Surcharge pour ajouter des validations supplémentaires."""
        # Validation personnalisée
        if obj.niveau_max < obj.niveau_min:
            from django.contrib import messages
            messages.error(request, _("Le niveau maximum doit être supérieur ou égal au niveau minimum."))
            return
        
        # Sauvegarder
        super().save_model(request, obj, form, change)
        
        if not change:  # Nouveau template
            from django.contrib import messages
            messages.success(request, _("Template de rappel créé avec succès."))
    
    def duplicate_template(self, request, template_id):
        """Action personnalisée pour dupliquer un template."""
        template = RappelTemplate.objects.get(pk=template_id)
        
        # Créer une copie
        template.pk = None
        template.id = None
        template.nom = f"{template.nom} (Copie)"
        template.save()
        
        from django.contrib import messages
        messages.success(request, _("Template dupliqué avec succès."))
        
        from django.shortcuts import redirect
        return redirect('admin:cotisations_rappeltemplate_changelist')
    
    def get_urls(self):
        """Ajouter des URLs personnalisées pour l'admin."""
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:template_id>/duplicate/',
                self.admin_site.admin_view(self.duplicate_template),
                name='cotisations_rappeltemplate_duplicate',
            ),
            path(
                '<int:template_id>/preview/',
                self.admin_site.admin_view(self.preview_template),
                name='cotisations_rappeltemplate_preview',
            ),
        ]
        return custom_urls + urls
    
    def preview_template(self, request, template_id):
        """Prévisualisation d'un template."""
        template = RappelTemplate.objects.get(pk=template_id)
        
        # Données de test pour la prévisualisation
        test_data = {
            'prenom': 'Jean',
            'nom': 'Dupont',
            'email': 'jean.dupont@example.com',
            'reference': 'COT-202401-0001',
            'montant': '120.00',
            'date_echeance': '15/01/2024',
            'jours_retard': '10',
            'date_limite': '31/01/2024',
            'association_nom': 'Association Test'
        }
        
        # Remplacer les variables dans le contenu
        contenu_preview = template.contenu
        sujet_preview = template.sujet
        
        for var, valeur in test_data.items():
            contenu_preview = contenu_preview.replace(f'{{{var}}}', str(valeur))
            sujet_preview = sujet_preview.replace(f'{{{var}}}', str(valeur))
        
        from django.http import HttpResponse
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Prévisualisation - {template.nom}</title>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
                .content {{ background: white; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }}
                .meta {{ color: #666; font-size: 0.9em; margin-bottom: 15px; }}
                pre {{ white-space: pre-wrap; font-family: inherit; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Prévisualisation du template : {template.nom}</h1>
                <div class="meta">
                    Type: {template.get_type_template_display()} | 
                    Mode: {template.get_type_rappel_display()} | 
                    Niveaux: {template.niveau_min}-{template.niveau_max}
                </div>
            </div>
            
            {f'<div class="content"><h3>Sujet:</h3><p><strong>{sujet_preview}</strong></p></div>' if sujet_preview else ''}
            
            <div class="content">
                <h3>Contenu:</h3>
                <pre>{contenu_preview}</pre>
            </div>
            
            <div class="meta" style="margin-top: 20px;">
                <small>Aperçu généré avec des données de test</small>
            </div>
        </body>
        </html>
        """
        
        return HttpResponse(html_content)

# Actions globales pour l'admin
def activer_templates(modeladmin, request, queryset):
    """Action pour activer plusieurs templates à la fois."""
    count = queryset.update(actif=True)
    from django.contrib import messages
    messages.success(request, f"{count} template(s) activé(s) avec succès.")
activer_templates.short_description = _("Activer les templates sélectionnés")

def desactiver_templates(modeladmin, request, queryset):
    """Action pour désactiver plusieurs templates à la fois."""
    count = queryset.update(actif=False)
    from django.contrib import messages
    messages.success(request, f"{count} template(s) désactivé(s) avec succès.")
desactiver_templates.short_description = _("Désactiver les templates sélectionnés")

# Ajouter les actions personnalisées à l'admin
RappelTemplateAdmin.actions = [activer_templates, desactiver_templates]