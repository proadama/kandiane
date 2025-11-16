# apps/accounts/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from .models import CustomUser, Role, Permission, RolePermission, UserProfile, UserLoginHistory


class RolePermissionInline(admin.TabularInline):
    model = RolePermission
    extra = 1
    autocomplete_fields = ['permission']


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('nom', 'description', 'is_default', 'created_at')
    search_fields = ('nom', 'description')
    list_filter = ('is_default', 'created_at')
    inlines = [RolePermissionInline]


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ('code', 'nom', 'description', 'created_at')
    search_fields = ('code', 'nom', 'description')
    list_filter = ('created_at',)
    ordering = ('code',)


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name = _("Profil")
    verbose_name_plural = _("Profil")
    fk_name = 'user'


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ('email', 'username', 'get_full_name', 'role', 'is_active', 'is_staff', 'derniere_connexion')
    list_filter = ('is_active', 'is_staff', 'is_superuser', 'role', 'date_joined')
    search_fields = ('email', 'username', 'first_name', 'last_name')
    ordering = ('email',)
    readonly_fields = ('date_joined', 'derniere_connexion')
    inlines = [UserProfileInline]

    fieldsets = (
        (None, {'fields': ('email', 'username', 'password')}),
        (_('Informations personnelles'), {'fields': ('first_name', 'last_name', 'avatar', 'telephone')}),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'role', 'groups', 'user_permissions'),
        }),
        (_('Dates importantes'), {'fields': ('date_joined', 'derniere_connexion', 'date_desactivation')}),
        (_('Préférences'), {'fields': ('accepte_communications',)}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'password1', 'password2', 'first_name', 'last_name', 'telephone', 'is_staff', 'is_superuser'),
        }),
    )

    def save_model(self, request, obj, form, change):
        """
        Utilise le UserCreationService pour créer les utilisateurs techniques.
        """
        if not change:  # Nouvel utilisateur
            from apps.accounts.services import UserCreationService
            from django.contrib import messages

            try:
                # Extraire le mot de passe du formulaire
                password = form.cleaned_data.get('password1')

                # Utiliser le service pour créer l'utilisateur technique
                user, generated_password = UserCreationService.creer_utilisateur_technique(
                    username=form.cleaned_data['username'],
                    email=form.cleaned_data['email'],
                    password=password,
                    first_name=form.cleaned_data.get('first_name', ''),
                    last_name=form.cleaned_data.get('last_name', ''),
                    telephone=form.cleaned_data.get('telephone', ''),
                    is_staff=form.cleaned_data.get('is_staff', False),
                    is_superuser=form.cleaned_data.get('is_superuser', False),
                )

                # Copier l'objet créé par le service dans obj pour que Django l'utilise
                obj.pk = user.pk
                obj.id = user.id

                messages.success(
                    request,
                    _("Utilisateur technique %(username)s créé avec succès.") % {'username': user.username}
                )
            except Exception as e:
                messages.error(request, _("Erreur lors de la création de l'utilisateur: %(error)s") % {'error': str(e)})
                raise
        else:
            # Modification d'un utilisateur existant - utiliser le comportement par défaut
            super().save_model(request, obj, form, change)


@admin.register(UserLoginHistory)
class UserLoginHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'ip_address', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__email', 'user__username', 'ip_address')
    date_hierarchy = 'created_at'
    readonly_fields = ('user', 'ip_address', 'user_agent', 'session_key', 'status', 'created_at')
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False