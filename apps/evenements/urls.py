# apps/evenements/urls.py
from django.urls import path, include
from . import views

app_name = 'evenements'

# URLs principales pour les événements
evenements_patterns = [
    # Liste et recherche d'événements
    path('', views.EvenementListView.as_view(), name='liste'),
    path('recherche/', views.EvenementSearchView.as_view(), name='recherche'),
    path('calendrier/', views.CalendrierEvenementView.as_view(), name='calendrier'),
    
    # CRUD événements
    path('nouveau/', views.EvenementCreateView.as_view(), name='creer'),
    path('<int:pk>/', views.EvenementDetailView.as_view(), name='detail'),
    path('<int:pk>/modifier/', views.EvenementUpdateView.as_view(), name='modifier'),
    path('<int:pk>/supprimer/', views.EvenementDeleteView.as_view(), name='supprimer'),
    
    # Récurrence
    path('<int:pk>/recurrence/', views.ConfigurerRecurrenceView.as_view(), name='configurer_recurrence'),
    
    # Sessions d'événements
    path('<int:evenement_pk>/sessions/', views.SessionListView.as_view(), name='sessions_liste'),
    path('<int:evenement_pk>/sessions/nouvelle/', views.SessionCreateView.as_view(), name='session_creer'),
]

# URLs pour les inscriptions
inscriptions_patterns = [
    # Inscription à un événement
    path('evenements/<int:evenement_pk>/inscription/', views.InscriptionCreateView.as_view(), name='inscription_creer'),
    path('<int:pk>/', views.InscriptionDetailView.as_view(), name='detail'),
    path('<int:pk>/confirmer/', views.ConfirmerInscriptionView.as_view(), name='confirmer'),
    path('<int:pk>/annuler/', views.AnnulerInscriptionView.as_view(), name='annuler'),
    
    # Confirmation par email (lien public)
    path('confirmer/<str:code>/', views.ConfirmerInscriptionEmailView.as_view(), name='confirmer_email'),
    
    # Paiements
    path('<int:pk>/recu/', views.GenererRecuView.as_view(), name='recu'),
    
    # Liste des inscriptions (pour les membres)
    path('mes-inscriptions/', views.MesInscriptionsView.as_view(), name='mes_inscriptions'),
]

# URLs pour la validation d'événements
validation_patterns = [
    # Liste des événements à valider
    path('', views.ValidationListView.as_view(), name='liste'),
    path('<int:pk>/', views.ValidationDetailView.as_view(), name='detail'),
    path('<int:pk>/approuver/', views.ApprouverEvenementView.as_view(), name='approuver'),
    path('<int:pk>/refuser/', views.RefuserEvenementView.as_view(), name='refuser'),
    
    # Validation en masse
    path('validation-masse/', views.ValidationMasseView.as_view(), name='validation_masse'),
]

# URLs pour les types d'événements
types_patterns = [
    path('', views.TypeEvenementListView.as_view(), name='liste'),
    path('nouveau/', views.TypeEvenementCreateView.as_view(), name='creer'),
]

# URLs pour les exports
export_patterns = [
    # Export inscriptions
    path('evenements/<int:evenement_pk>/inscriptions/', views.ExportInscritsView.as_view(), name='inscriptions_evenement'),
    
    # Export badges/étiquettes
    path('evenements/<int:evenement_pk>/badges/', views.ExportBadgesView.as_view(), name='badges'),
    
    # Export calendrier
    path('calendrier.ics', views.ExportCalendrierView.as_view(), name='calendrier_ics'),
]

# URLs pour les rapports et statistiques
rapports_patterns = [
    # Rapports événements
    path('evenements/', views.RapportEvenementsView.as_view(), name='evenements'),
]

# URLs AJAX pour les fonctionnalités dynamiques
ajax_patterns = [
    # Vérification disponibilité
    path('evenements/<int:pk>/places-disponibles/', views.CheckPlacesDisponiblesView.as_view(), name='places_disponibles'),
    path('evenements/<int:pk>/peut-inscrire/', views.CheckPeutInscrireView.as_view(), name='peut_inscrire'),
    
    # Calculs dynamiques
    path('evenements/<int:pk>/calculer-tarif/', views.CalculerTarifView.as_view(), name='calculer_tarif'),
    
    # Auto-complétion
    path('recherche/organisateurs/', views.AutocompleteOrganisateursView.as_view(), name='autocomplete_organisateurs'),
    path('recherche/lieux/', views.AutocompleteLieuxView.as_view(), name='autocomplete_lieux'),
    
    # Gestion liste d'attente
    path('inscriptions/<int:pk>/promouvoir/', views.PromouvoirListeAttenteView.as_view(), name='promouvoir_liste_attente'),
]

# URLs pour la corbeille (suppression logique)
corbeille_patterns = [
    path('evenements/', views.CorbeilleEvenementsView.as_view(), name='evenements'),
    path('evenements/<int:pk>/restaurer/', views.RestaurerEvenementView.as_view(), name='restaurer_evenement'),
]

# URLs principales avec inclusion des sous-patterns
urlpatterns = [
    # Dashboard principal
    path('', views.DashboardEvenementView.as_view(), name='dashboard'),
    
    # Sous-patterns organisés
    path('evenements/', include(evenements_patterns)),
    path('inscriptions/', include(inscriptions_patterns)),
    path('validation/', include(validation_patterns)),
    path('types/', include(types_patterns)),
    path('export/', include(export_patterns)),
    path('rapports/', include(rapports_patterns)),
    path('ajax/', include(ajax_patterns)),
    path('corbeille/', include(corbeille_patterns)),
    
    # Import/Export de données
    path('import/', views.ImportEvenementsView.as_view(), name='import'),
    
    # Maintenance et utilitaires
    path('maintenance/nettoyer-inscriptions/', views.NettoyerInscriptionsView.as_view(), name='nettoyer_inscriptions'),
]

# URLs pour les vues publiques (sans authentification)
public_patterns = [
    # Événements publics
    path('public/evenements/', views.EvenementsPublicsView.as_view(), name='evenements_publics'),
    path('public/evenements/<int:pk>/', views.EvenementPublicDetailView.as_view(), name='evenement_public_detail'),
    path('public/calendrier/', views.CalendrierPublicView.as_view(), name='calendrier_public'),
    
    # Confirmation d'inscription publique
    path('public/confirmation/<str:code>/', views.ConfirmationPubliqueView.as_view(), name='confirmation_publique'),
]

# Ajouter les patterns publics
urlpatterns += [
    path('public/', include(public_patterns)),
]