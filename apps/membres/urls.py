from django.urls import path
from apps.membres import views

app_name = 'membres'

urlpatterns = [
    # Dashboard et statistiques
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('dashboard/', views.DashboardView.as_view(), name='dashboard_alt'),
    path('statistiques/', views.MembreStatistiquesView.as_view(), name='statistiques'),
    
    # Gestion des membres
    path('liste/', views.MembreListView.as_view(), name='membre_liste'),
    path('nouveau/', views.MembreCreateView.as_view(), name='membre_nouveau'),
    path('<int:pk>/', views.MembreDetailView.as_view(), name='membre_detail'),
    path('<int:pk>/modifier/', views.MembreUpdateView.as_view(), name='membre_modifier'),
    path('<int:pk>/supprimer/', views.MembreDeleteView.as_view(), name='membre_supprimer'),
    path('<int:pk>/historique/', views.MembreHistoriqueView.as_view(), name='membre_historique'),
    
    # Import/export de membres
    path('importer/', views.MembreImportView.as_view(), name='membre_importer'),
    path('exporter/', views.MembreExportView.as_view(), name='membre_exporter'),
    
    # Gestion des types de membre
    path('types/', views.TypeMembreListView.as_view(), name='type_membre_liste'),
    path('types/nouveau/', views.TypeMembreCreateView.as_view(), name='type_membre_nouveau'),
    path('types/<int:pk>/modifier/', views.TypeMembreUpdateView.as_view(), name='type_membre_modifier'),
    path('types/<int:pk>/supprimer/', views.TypeMembreDeleteView.as_view(), name='type_membre_supprimer'),
    
    # Gestion des associations membre-type
    path('<int:membre_id>/ajouter-type/', views.MembreTypeMembreCreateView.as_view(), name='membre_ajouter_type'),
    path('types-association/<int:pk>/modifier/', views.MembreTypeMembreUpdateView.as_view(), name='membre_type_modifier'),
    path('types-association/<int:pk>/terminer/', views.MembreTypeMembreTerminerView.as_view(), name='membre_type_terminer'),
]