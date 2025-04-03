# apps/core/admin.py
from django.contrib import admin
from .models import Statut

@admin.register(Statut)
class StatutAdmin(admin.ModelAdmin):
    list_display = ('nom', 'description', 'created_at', 'updated_at')
    search_fields = ('nom', 'description')
    list_filter = ('created_at',)