# apps/core/admin.py
from django.contrib import admin
from .models import Statut

@admin.register(Statut)
class StatutAdmin(admin.ModelAdmin):
    list_display = ('nom', 'type_entite', 'description', 'created_at', 'updated_at')
    list_filter = ('type_entite',)
    search_fields = ('nom', 'description')