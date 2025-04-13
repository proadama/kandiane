from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count
from apps.membres.models import Membre, TypeMembre, MembreTypeMembre, HistoriqueMembre


class MembreTypeMembreInline(admin.TabularInline):
    """
    Inline pour afficher les types de membre associés à un membre
    """
    model = MembreTypeMembre
    extra = 0
    fields = ('type_membre', 'date_debut', 'date_fin', 'commentaire', 'modifie_par')
    readonly_fields = ('modifie_par',)
    autocomplete_fields = ('type_membre',)
    
    def has_delete_permission(self, request, obj=None):
        """Désactiver la suppression des associations dans l'admin"""
        return False


class HistoriqueMembreInline(admin.TabularInline):
    """
    Inline pour afficher l'historique des modifications d'un membre
    """
    model = HistoriqueMembre
    extra = 0
    fields = ('action', 'description', 'utilisateur', 'created_at')
    readonly_fields = ('action', 'description', 'utilisateur', 'created_at')
    can_delete = False
    max_num = 10  # Limiter le nombre d'entrées affichées
    
    def has_add_permission(self, request, obj=None):
        """Désactiver l'ajout d'historique dans l'admin"""
        return False


@admin.register(Membre)
class MembreAdmin(admin.ModelAdmin):
    """
    Administration des membres
    """
    list_display = ('nom_complet', 'email', 'telephone', 'date_adhesion', 'statut_display', 'types_liste', 'utilisateur_link', 'is_active', 'est_supprime')
    list_filter = ('statut', 'date_adhesion', 'types', 'langue', 'pays', 'accepte_mail', 'accepte_sms', 'deleted_at')
    search_fields = ('nom', 'prenom', 'email', 'telephone', 'adresse', 'code_postal', 'ville')
    ordering = ('nom', 'prenom')
    date_hierarchy = 'date_adhesion'
    
    readonly_fields = ('created_at', 'updated_at')
    autocomplete_fields = ('utilisateur', 'statut')
    
    fieldsets = (
        (_('Informations personnelles'), {
            'fields': ('nom', 'prenom', 'email', 'telephone', 'date_naissance', 'photo')
        }),
        (_('Adresse'), {
            'fields': ('adresse', 'code_postal', 'ville', 'pays')
        }),
        (_('Informations d\'adhésion'), {
            'fields': ('date_adhesion', 'statut', 'utilisateur')
        }),
        (_('Préférences'), {
            'fields': ('langue', 'accepte_mail', 'accepte_sms')
        }),
        (_('Commentaires'), {
            'fields': ('commentaires',)
        }),
        (_('Informations système'), {
            'fields': ('created_at', 'updated_at', 'deleted_at'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [MembreTypeMembreInline, HistoriqueMembreInline]
    
    actions = ['export_selected_as_csv', 'create_user_accounts', 'mark_as_deleted', 'unmark_as_deleted', 'restaurer_membres', 'supprimer_definitivement']
    
    def get_queryset(self, request):
        """Inclure les membres supprimés logiquement"""
        return Membre.objects.with_deleted().select_related(
            'statut', 'utilisateur'
        ).prefetch_related('types')
    
    # Ajouter un filtre pour voir les membres supprimés
    list_filter = ('deleted_at', 'statut', 'date_adhesion', 'types', 'langue', 'pays', 'accepte_mail', 'accepte_sms')
    
    def est_supprime(self, obj):
        return obj.deleted_at is not None
    est_supprime.boolean = True
    est_supprime.short_description = _('Supprimé')

    def restaurer_membres(self, request, queryset):
        count = 0
        for obj in queryset:
            if obj.deleted_at is not None:
                obj.restore(user=request.user)
                count += 1
        
        if count == 1:
            message = _("1 membre a été restauré.")
        else:
            message = _("{} membres ont été restaurés.").format(count)
        
        self.message_user(request, message)
    restaurer_membres.short_description = _("Restaurer les membres sélectionnés")
    
    def supprimer_definitivement(self, request, queryset):
        count = len(queryset)
        for obj in queryset:
            obj.delete(hard=True, user=request.user)
        
        if count == 1:
            message = _("1 membre a été supprimé définitivement.")
        else:
            message = _("{} membres ont été supprimés définitivement.").format(count)
        
        self.message_user(request, message)
    supprimer_definitivement.short_description = _("⚠️ Supprimer définitivement les membres sélectionnés")

    def nom_complet(self, obj):
        """Afficher le nom complet"""
        return f"{obj.prenom} {obj.nom}"
    nom_complet.short_description = _("Nom complet")
    nom_complet.admin_order_field = 'nom'
    
    def statut_display(self, obj):
        """Afficher le statut avec couleur"""
        if not obj.statut:
            return _("Aucun")
        
        return format_html(
            '<span style="color: {};">{}</span>',
            '#28a745' if obj.statut.nom in ['Actif', 'À jour'] else '#dc3545',
            obj.statut.nom
        )
    statut_display.short_description = _("Statut")
    statut_display.admin_order_field = 'statut__nom'
    
    def types_liste(self, obj):
        """Afficher la liste des types de membre actifs"""
        types = obj.get_types_actifs()
        if not types:
            return _("Aucun")
        
        return ", ".join([t.libelle for t in types])
    types_liste.short_description = _("Types de membre")
    
    def utilisateur_link(self, obj):
        """Lien vers l'utilisateur associé"""
        if not obj.utilisateur:
            return _("Aucun")
        
        url = reverse('admin:accounts_customuser_change', args=[obj.utilisateur.id])
        return format_html('<a href="{}">{}</a>', url, obj.utilisateur.username)
    utilisateur_link.short_description = _("Compte utilisateur")
    utilisateur_link.admin_order_field = 'utilisateur__username'
    
    def is_active(self, obj):
        """Indique si le membre est actif (non supprimé logiquement)"""
        return obj.deleted_at is None
    is_active.boolean = True
    is_active.short_description = _("Actif")
    
    def save_model(self, request, obj, form, change):
        """Enregistrer l'historique lors de la modification"""
        super().save_model(request, obj, form, change)
        
        if change and form.changed_data:
            HistoriqueMembre.objects.create(
                membre=obj,
                utilisateur=request.user,
                action='modification_admin',
                description=f"Modification des champs: {', '.join(form.changed_data)}",
                donnees_avant={
                    field: str(form.initial.get(field)) 
                    for field in form.changed_data 
                    if field in form.initial
                },
                donnees_apres={
                    field: str(form.cleaned_data.get(field))
                    for field in form.changed_data
                }
            )
    
    def delete_model(self, request, obj):
        """Enregistrer l'historique lors de la suppression"""
        HistoriqueMembre.objects.create(
            membre=obj,
            utilisateur=request.user,
            action='suppression_admin',
            description=_("Suppression du membre dans l'administration"),
            donnees_avant={
                'nom': obj.nom,
                'prenom': obj.prenom,
                'email': obj.email
            }
        )
        # Utiliser la suppression logique par défaut
        obj.delete()
    
    def save_formset(self, request, form, formset, change):
        """Enregistrer l'utilisateur qui modifie les associations de types"""
        instances = formset.save(commit=False)
        for instance in instances:
            if isinstance(instance, MembreTypeMembre) and not instance.modifie_par:
                instance.modifie_par = request.user
            instance.save()
        formset.save_m2m()
    
    def export_selected_as_csv(self, request, queryset):
        """Action pour exporter les membres sélectionnés en CSV"""
        import csv
        from django.http import HttpResponse
        from django.utils import timezone
        
        date_str = timezone.now().strftime('%Y-%m-%d_%H-%M-%S')
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="membres_export_{date_str}.csv"'
        
        writer = csv.writer(response)
        # En-tête
        writer.writerow([
            _('ID'), _('Nom'), _('Prénom'), _('Email'), _('Téléphone'), 
            _('Adresse'), _('Code postal'), _('Ville'), _('Pays'),
            _('Date d\'adhésion'), _('Date de naissance'),
            _('Statut'), _('Types de membre')
        ])
        
        # Données
        for membre in queryset:
            writer.writerow([
                membre.id, membre.nom, membre.prenom, membre.email, membre.telephone,
                membre.adresse, membre.code_postal, membre.ville, membre.pays,
                membre.date_adhesion, membre.date_naissance,
                membre.statut.nom if membre.statut else '',
                ", ".join([t.libelle for t in membre.get_types_actifs()])
            ])
        
        return response
    export_selected_as_csv.short_description = _("Exporter les membres sélectionnés en CSV")
    
    def create_user_accounts(self, request, queryset):
        """Action pour créer des comptes utilisateurs pour les membres sélectionnés"""
        created = 0
        skipped = 0
        
        for membre in queryset:
            if membre.utilisateur:
                skipped += 1
                continue
                
            # Créer un compte utilisateur
            try:
                membre.creer_compte_utilisateur()
                created += 1
            except Exception:
                skipped += 1
        
        if created:
            self.message_user(
                request, 
                _("%(created)d comptes utilisateurs ont été créés avec succès. %(skipped)d membres ont été ignorés.") % {
                    'created': created, 
                    'skipped': skipped
                }
            )
        else:
            self.message_user(
                request, 
                _("Aucun compte utilisateur n'a été créé. %(skipped)d membres ont été ignorés.") % {'skipped': skipped}
            )
    create_user_accounts.short_description = _("Créer des comptes utilisateurs")
    
    def mark_as_deleted(self, request, queryset):
        """Action pour marquer les membres sélectionnés comme supprimés"""
        updated = queryset.filter(deleted_at__isnull=True).update(deleted_at=timezone.now())
        
        if updated:
            self.message_user(
                request, 
                _("%(count)d membres ont été marqués comme supprimés.") % {'count': updated}
            )
        else:
            self.message_user(
                request, 
                _("Aucun membre n'a été marqué comme supprimé.")
            )
    mark_as_deleted.short_description = _("Marquer comme supprimés")
    
    def unmark_as_deleted(self, request, queryset):
        """Action pour restaurer les membres supprimés logiquement"""
        updated = queryset.filter(deleted_at__isnull=False).update(deleted_at=None)
        
        if updated:
            self.message_user(
                request, 
                _("%(count)d membres ont été restaurés.") % {'count': updated}
            )
        else:
            self.message_user(
                request, 
                _("Aucun membre n'a été restauré.")
            )
    unmark_as_deleted.short_description = _("Restaurer les membres supprimés")


@admin.register(TypeMembre)
class TypeMembreAdmin(admin.ModelAdmin):
    """
    Administration des types de membre
    """
    list_display = ('libelle', 'description', 'cotisation_requise', 'ordre_affichage', 'nb_membres', 'is_active')
    list_filter = ('cotisation_requise', 'deleted_at')
    search_fields = ('libelle', 'description')
    ordering = ('ordre_affichage', 'libelle')
    
    readonly_fields = ('created_at', 'updated_at', 'deleted_at')
    
    fieldsets = (
        (None, {
            'fields': ('libelle', 'description', 'cotisation_requise', 'ordre_affichage')
        }),
        (_('Informations système'), {
            'fields': ('created_at', 'updated_at', 'deleted_at'),
            'classes': ('collapse',)
        }),
    )

    def est_supprime(self, obj):
        return obj.deleted_at is not None
    est_supprime.boolean = True
    est_supprime.short_description = _('Supprimé')

    def restaurer_membres(self, request, queryset):
        # Action pour restaurer les membres supprimés
        updated = queryset.update(deleted_at=None)
        self.message_user(request, _(f"{updated} membre(s) restauré(s) avec succès."))
    restaurer_membres.short_description = _("Restaurer les membres sélectionnés")
    
    def get_queryset(self, request):
        """Inclure le nombre de membres dans la requête"""
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(
            members_count=Count('membres_historique__membre', distinct=True)
        )
        return queryset
    
    def nb_membres(self, obj):
        """Afficher le nombre de membres actifs"""
        if hasattr(obj, 'members_count'):
            return obj.members_count
        return obj.nb_membres_actifs()
    nb_membres.short_description = _("Membres")
    nb_membres.admin_order_field = 'members_count'
    
    def is_active(self, obj):
        """Indique si le type est actif (non supprimé logiquement)"""
        return obj.deleted_at is None
    is_active.boolean = True
    is_active.short_description = _("Actif")
    
    actions = ['mark_as_deleted', 'unmark_as_deleted']
    
    def mark_as_deleted(self, request, queryset):
        """Action pour marquer les types sélectionnés comme supprimés"""
        updated = queryset.filter(deleted_at__isnull=True).update(deleted_at=timezone.now())
        
        if updated:
            self.message_user(
                request, 
                _("%(count)d types de membre ont été marqués comme supprimés.") % {'count': updated}
            )
        else:
            self.message_user(
                request, 
                _("Aucun type de membre n'a été marqué comme supprimé.")
            )
    mark_as_deleted.short_description = _("Marquer comme supprimés")
    
    def unmark_as_deleted(self, request, queryset):
        """Action pour restaurer les types supprimés logiquement"""
        updated = queryset.filter(deleted_at__isnull=False).update(deleted_at=None)
        
        if updated:
            self.message_user(
                request, 
                _("%(count)d types de membre ont été restaurés.") % {'count': updated}
            )
        else:
            self.message_user(
                request, 
                _("Aucun type de membre n'a été restauré.")
            )
    unmark_as_deleted.short_description = _("Restaurer les types supprimés")


@admin.register(MembreTypeMembre)
class MembreTypeMembreAdmin(admin.ModelAdmin):
    """
    Administration des associations membre-type
    """
    list_display = ('membre', 'type_membre', 'date_debut', 'date_fin', 'est_actif', 'modifie_par')
    list_filter = ('type_membre', 'date_debut', 'date_fin')
    search_fields = ('membre__nom', 'membre__prenom', 'membre__email', 'type_membre__libelle', 'commentaire')
    ordering = ('-date_debut',)
    
    autocomplete_fields = ('membre', 'type_membre', 'modifie_par')
    
    fieldsets = (
        (None, {
            'fields': ('membre', 'type_membre', 'date_debut', 'date_fin', 'commentaire', 'modifie_par')
        }),
    )
    
    def est_actif(self, obj):
        """Indique si l'association est active"""
        return obj.est_actif
    est_actif.boolean = True
    est_actif.short_description = _("Actif")
    
    def save_model(self, request, obj, form, change):
        """Enregistrer l'utilisateur qui fait la modification"""
        if not obj.modifie_par:
            obj.modifie_par = request.user
        super().save_model(request, obj, form, change)
    
    def has_delete_permission(self, request, obj=None):
        """
        Désactiver la suppression pour préserver l'historique.
        Préférer l'ajout d'une date de fin.
        """
        return False
    
    actions = ['terminer_associations']
    
    def terminer_associations(self, request, queryset):
        """Action pour terminer les associations sélectionnées"""
        from django.utils import timezone
        
        # Ne traiter que les associations actives
        updated = queryset.filter(date_fin__isnull=True).update(
            date_fin=timezone.now().date(),
            modifie_par=request.user
        )
        
        if updated:
            self.message_user(
                request, 
                _("%(count)d associations ont été terminées.") % {'count': updated}
            )
        else:
            self.message_user(
                request, 
                _("Aucune association active n'a été terminée.")
            )
    terminer_associations.short_description = _("Terminer les associations sélectionnées")


@admin.register(HistoriqueMembre)
class HistoriqueMembreAdmin(admin.ModelAdmin):
    """
    Administration de l'historique des membres
    """
    list_display = ('membre', 'action', 'description_tronquee', 'utilisateur', 'created_at')
    list_filter = ('action', 'created_at', 'utilisateur')
    search_fields = ('membre__nom', 'membre__prenom', 'membre__email', 'description')
    ordering = ('-created_at',)
    
    readonly_fields = ('membre', 'utilisateur', 'action', 'description', 'donnees_avant', 'donnees_apres', 'created_at')
    
    fieldsets = (
        (None, {
            'fields': ('membre', 'action', 'description', 'utilisateur', 'created_at')
        }),
        (_('Données'), {
            'fields': ('donnees_avant', 'donnees_apres'),
            'classes': ('collapse',)
        }),
    )
    
    def description_tronquee(self, obj):
        """Tronquer la description pour l'affichage dans la liste"""
        max_length = 100
        if len(obj.description) > max_length:
            return f"{obj.description[:max_length]}..."
        return obj.description
    description_tronquee.short_description = _("Description")
    
    def has_add_permission(self, request):
        """Désactiver l'ajout manuel d'historique"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Désactiver la modification de l'historique"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Désactiver la suppression de l'historique"""
        return False