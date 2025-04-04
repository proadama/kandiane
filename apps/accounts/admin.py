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
            'fields': ('email', 'username', 'password1', 'password2', 'role'),
        }),
    )


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