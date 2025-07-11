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
    path('<int:pk>/dupliquer/', views.EvenementDuplicateView.as_view(), name='dupliquer'),
    
    # Gestion du statut des événements
    path('<int:pk>/publier/', views.PublierEvenementView.as_view(), name='publier'),
    path('<int:pk>/annuler/', views.AnnulerEvenementView.as_view(), name='annuler'),
    path('<int:pk>/reporter/', views.ReporterEvenementView.as_view(), name='reporter'),
    
    # Récurrence
    path('<int:pk>/recurrence/', views.ConfigurerRecurrenceView.as_view(), name='configurer_recurrence'),
    path('<int:pk>/generer-occurrences/', views.GenererOccurrencesView.as_view(), name='generer_occurrences'),
    
    # Sessions d'événements
    path('<int:evenement_pk>/sessions/', views.SessionListView.as_view(), name='sessions_liste'),
    path('<int:evenement_pk>/sessions/nouvelle/', views.SessionCreateView.as_view(), name='session_creer'),
    path('sessions/<int:pk>/', views.SessionDetailView.as_view(), name='session_detail'),
    path('sessions/<int:pk>/modifier/', views.SessionUpdateView.as_view(), name='session_modifier'),
    path('sessions/<int:pk>/supprimer/', views.SessionDeleteView.as_view(), name='session_supprimer'),
]

# URLs pour les inscriptions
inscriptions_patterns = [
    # Inscription à un événement
    path('evenements/<int:evenement_pk>/inscription/', views.InscriptionCreateView.as_view(), name='inscription_creer'),
    path('<int:pk>/', views.InscriptionDetailView.as_view(), name='detail'),
    path('<int:pk>/confirmer/', views.ConfirmerInscriptionView.as_view(), name='confirmer'),
    path('<int:pk>/annuler/', views.AnnulerInscriptionView.as_view(), name='annuler'),
    path('<int:pk>/modifier/', views.InscriptionUpdateView.as_view(), name='modifier'),
    
    # Confirmation par email (lien public)
    path('confirmer/<str:code>/', views.ConfirmerInscriptionEmailView.as_view(), name='confirmer_email'),
    
    # Gestion des accompagnants
    path('<int:inscription_pk>/accompagnants/', views.AccompagnantListView.as_view(), name='accompagnants_liste'),
    path('<int:inscription_pk>/accompagnants/ajouter/', views.AccompagnantCreateView.as_view(), name='accompagnant_ajouter'),
    path('accompagnants/<int:pk>/', views.AccompagnantDetailView.as_view(), name='accompagnant_detail'),
    path('accompagnants/<int:pk>/modifier/', views.AccompagnantUpdateView.as_view(), name='accompagnant_modifier'),
    path('accompagnants/<int:pk>/supprimer/', views.AccompagnantDeleteView.as_view(), name='accompagnant_supprimer'),
    
    # Paiements
    path('<int:pk>/paiement/', views.PaiementInscriptionView.as_view(), name='paiement'),
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
    path('<int:pk>/demander-modifications/', views.DemanderModificationsView.as_view(), name='demander_modifications'),
    
    # Validation en masse
    path('validation-masse/', views.ValidationMasseView.as_view(), name='validation_masse'),
    
    # Statistiques de validation
    path('statistiques/', views.ValidationStatsView.as_view(), name='statistiques'),
]

# URLs pour les types d'événements
types_patterns = [
    path('', views.TypeEvenementListView.as_view(), name='liste'),
    path('nouveau/', views.TypeEvenementCreateView.as_view(), name='creer'),
    path('<int:pk>/', views.TypeEvenementDetailView.as_view(), name='detail'),
    path('<int:pk>/modifier/', views.TypeEvenementUpdateView.as_view(), name='modifier'),
    path('<int:pk>/supprimer/', views.TypeEvenementDeleteView.as_view(), name='supprimer'),
]

# URLs pour les exports
export_patterns = [
    # Export événements
    path('evenements/', views.ExportEvenementsView.as_view(), name='evenements'),
    path('evenements/<int:pk>/', views.ExportEvenementView.as_view(), name='evenement'),
    
    # Export inscriptions
    path('inscriptions/', views.ExportInscriptionsView.as_view(), name='inscriptions'),
    path('evenements/<int:evenement_pk>/inscriptions/', views.ExportInscriptionsEvenementView.as_view(), name='inscriptions_evenement'),
    
    # Export badges/étiquettes
    path('evenements/<int:evenement_pk>/badges/', views.ExportBadgesView.as_view(), name='badges'),
    
    # Export calendrier
    path('calendrier.ics', views.ExportCalendrierView.as_view(), name='calendrier_ics'),
    path('evenements/<int:pk>/calendrier.ics', views.ExportEvenementCalendrierView.as_view(), name='evenement_ics'),
]

# URLs pour les rapports et statistiques
rapports_patterns = [
    # Dashboard général
    path('', views.RapportDashboardView.as_view(), name='dashboard'),
    
    # Rapports événements
    path('evenements/', views.RapportEvenementsView.as_view(), name='evenements'),
    path('evenements/frequentation/', views.RapportFrequentationView.as_view(), name='frequentation'),
    path('evenements/revenus/', views.RapportRevenusView.as_view(), name='revenus'),
    
    # Rapports membres
    path('membres/participation/', views.RapportParticipationMembresView.as_view(), name='participation_membres'),
    path('membres/fidélité/', views.RapportFideliteMembresView.as_view(), name='fidelite_membres'),
    
    # Rapports organisateurs
    path('organisateurs/', views.RapportOrganisateursView.as_view(), name='organisateurs'),
]

# URLs AJAX pour les fonctionnalités dynamiques
ajax_patterns = [
    # Vérification disponibilité
    path('evenements/<int:pk>/places-disponibles/', views.CheckPlacesDisponiblesView.as_view(), name='places_disponibles'),
    path('evenements/<int:pk>/peut-inscrire/', views.CheckPeutInscrireView.as_view(), name='peut_inscrire'),
    
    # Calculs dynamiques
    path('evenements/<int:pk>/calculer-tarif/', views.CalculerTarifView.as_view(), name='calculer_tarif'),
    path('inscriptions/<int:pk>/calculer-montant/', views.CalculerMontantInscriptionView.as_view(), name='calculer_montant'),
    
    # Auto-complétion
    path('recherche/organisateurs/', views.AutocompleteOrganisateursView.as_view(), name='autocomplete_organisateurs'),
    path('recherche/lieux/', views.AutocompleteLieuxView.as_view(), name='autocomplete_lieux'),
    
    # Notifications temps réel
    path('notifications/inscriptions/', views.NotificationsInscriptionsView.as_view(), name='notifications_inscriptions'),
    path('notifications/validations/', views.NotificationsValidationsView.as_view(), name='notifications_validations'),
    
    # Gestion liste d'attente
    path('inscriptions/<int:pk>/promouvoir/', views.PromouvoirListeAttenteView.as_view(), name='promouvoir_liste_attente'),
    
    # Preview événement
    path('evenements/preview/', views.PreviewEvenementView.as_view(), name='preview_evenement'),
]

# URLs pour la corbeille (suppression logique)
corbeille_patterns = [
    path('evenements/', views.CorbeilleEvenementsView.as_view(), name='evenements'),
    path('inscriptions/', views.CorbeilleInscriptionsView.as_view(), name='inscriptions'),
    path('evenements/<int:pk>/restaurer/', views.RestaurerEvenementView.as_view(), name='restaurer_evenement'),
    path('inscriptions/<int:pk>/restaurer/', views.RestaurerInscriptionView.as_view(), name='restaurer_inscription'),
    path('evenements/<int:pk>/supprimer-definitivement/', views.SupprimerDefinitivementEvenementView.as_view(), name='supprimer_definitivement_evenement'),
]

# URLs pour l'API publique (optionnel)
api_patterns = [
    # API événements publics
    path('evenements/', views.APIEvenementsPublicsView.as_view(), name='evenements_publics'),
    path('evenements/<int:pk>/', views.APIEvenementDetailView.as_view(), name='evenement_detail'),
    path('evenements/<int:pk>/places/', views.APIPlacesDisponiblesView.as_view(), name='api_places_disponibles'),
    
    # Flux RSS/Atom
    path('rss/', views.EvenementsFeedView(), name='rss'),
    path('atom/', views.EvenementsAtomFeedView(), name='atom'),
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
    path('api/', include(api_patterns)),
    
    # URLs spéciales
    path('aide/', views.AideEvenementsView.as_view(), name='aide'),
    path('documentation/', views.DocumentationView.as_view(), name='documentation'),
    
    # Import/Export de données
    path('import/', views.ImportEvenementsView.as_view(), name='import'),
    path('import/template/', views.DownloadImportTemplateView.as_view(), name='import_template'),
    
    # Configuration et paramétrage
    path('configuration/', views.ConfigurationEvenementsView.as_view(), name='configuration'),
    path('parametres/', views.ParametresEvenementsView.as_view(), name='parametres'),
    
    # Maintenance et utilitaires
    path('maintenance/nettoyer-inscriptions/', views.NettoyerInscriptionsView.as_view(), name='nettoyer_inscriptions'),
    path('maintenance/recalculer-stats/', views.RecalculerStatsView.as_view(), name='recalculer_stats'),
    
    # Webhooks et intégrations externes
    path('webhooks/paiement/', views.WebhookPaiementView.as_view(), name='webhook_paiement'),
    path('integrations/calendrier/', views.IntegrationCalendrierView.as_view(), name='integration_calendrier'),
    
    # URLs pour les tâches programmées (accessible uniquement en interne)
    path('cron/rappels/', views.CronRappelsView.as_view(), name='cron_rappels'),
    path('cron/nettoyage/', views.CronNettoyageView.as_view(), name='cron_nettoyage'),
    path('cron/statistiques/', views.CronStatistiquesView.as_view(), name='cron_statistiques'),
]

# URLs pour les vues publiques (sans authentification)
public_patterns = [
    # Événements publics
    path('public/evenements/', views.EvenementsPublicsView.as_view(), name='evenements_publics'),
    path('public/evenements/<int:pk>/', views.EvenementPublicDetailView.as_view(), name='evenement_public_detail'),
    path('public/calendrier/', views.CalendrierPublicView.as_view(), name='calendrier_public'),
    
    # Confirmation d'inscription publique
    path('public/confirmation/<str:code>/', views.ConfirmationPubliqueView.as_view(), name='confirmation_publique'),
    
    # Widget d'intégration
    path('widget/prochains-evenements/', views.WidgetProchainsEvenementsView.as_view(), name='widget_prochains'),
    path('widget/calendrier-mini/', views.WidgetCalendrierMiniView.as_view(), name='widget_calendrier'),
]

# Ajouter les patterns publics
urlpatterns += [
    path('public/', include(public_patterns)),
]

# Gestion des erreurs spécifiques à l'application
handler404 = 'apps.evenements.views.evenement_404'
handler500 = 'apps.evenements.views.evenement_500'