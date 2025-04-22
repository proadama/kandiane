# apps/cotisations/urls.py
from django.urls import path
from . import views

app_name = 'cotisations'

urlpatterns = [
    # URLs de base à implémenter dans la prochaine phase
    path('', views.dashboard, name='dashboard'),
    path('liste/', views.cotisation_list, name='cotisation_liste'),
    path('<int:pk>/', views.cotisation_detail, name='cotisation_detail'),
    path('nouvelle/', views.cotisation_create, name='cotisation_creer'),
    path('<int:pk>/modifier/', views.cotisation_update, name='cotisation_modifier'),
    path('<int:pk>/supprimer/', views.cotisation_delete, name='cotisation_supprimer'),
    
    # Paiements
    path('paiements/', views.paiement_list, name='paiement_liste'),
    path('paiements/<int:pk>/', views.paiement_detail, name='paiement_detail'),
    path('paiements/nouveau/<int:cotisation_id>/', views.paiement_create, name='paiement_creer'),
    path('paiements/<int:pk>/modifier/', views.paiement_update, name='paiement_modifier'),
    path('paiements/<int:pk>/supprimer/', views.paiement_delete, name='paiement_supprimer'),
    
    # Barèmes
    path('baremes/', views.bareme_list, name='bareme_liste'),
    path('baremes/<int:pk>/', views.bareme_detail, name='bareme_detail'),
    path('baremes/nouveau/', views.bareme_create, name='bareme_creer'),
    path('baremes/<int:pk>/modifier/', views.bareme_update, name='bareme_modifier'),
    path('baremes/<int:pk>/supprimer/', views.bareme_delete, name='bareme_supprimer'),
    path('api/verifier-bareme/', views.api_verifier_bareme, name='api_verifier_bareme'),
    path('baremes/reactive/', views.bareme_reactive, name='bareme_reactive'),
    
    # Rappels
    path('rappels/', views.rappel_list, name='rappel_liste'),
    path('rappels/<int:pk>/', views.rappel_detail, name='rappel_detail'),
    path('rappels/nouveau/<int:cotisation_id>/', views.rappel_create, name='rappel_creer'),
    path('rappels/<int:rappel_id>/contenu/', views.rappel_contenu_ajax, name='rappel_contenu_ajax'),
    path('rappels/<int:rappel_id>/envoyer/', views.rappel_envoi_ajax, name='rappel_envoi_ajax'),
    path('rappels/<int:rappel_id>/supprimer/', views.rappel_supprimer_ajax, name='rappel_supprimer_ajax'),
    
    # Fonctionnalités avancées
    path('corbeille/', views.corbeille, name='corbeille'),
    path('statistiques/', views.statistiques, name='statistiques'),
    path('export/', views.export, name='export'),
    path('import/', views.import_cotisations, name='import'),
    
    # API internes
    path('api/calculer-montant/', views.api_calculer_montant, name='api_calculer_montant'),
    path('api/baremes-par-type/', views.api_baremes_par_type, name='api_baremes_par_type'),
    path('api/generer-recu/<int:paiement_id>/', views.api_generer_recu, name='api_generer_recu'),
    path('api/marquer-paiement-recu/<int:paiement_id>/', views.api_marquer_paiement_recu, name='api_marquer_paiement_recu'),
    path('api/stats-cotisations/', views.api_stats_cotisations, name='api_stats_cotisations'),
    path('api/cotisations-en-retard/', views.api_cotisations_en_retard, name='api_cotisations_en_retard'),
    path('api/envoyer-rappels-automatiques/', views.api_envoyer_rappels_automatiques, name='api_envoyer_rappels_automatiques'),

    # Cotisations
    path('<int:cotisation_id>/paiement/ajax/', views.paiement_create_ajax, name='paiement_create_ajax'),
    path('<int:cotisation_id>/rappel/ajax/', views.rappel_create_ajax, name='rappel_create_ajax'),

    # Fonctionnalités d'export
    path('export/cotisations/pdf/', views.export_cotisations_pdf, name='export_cotisations_pdf'),
    path('export/paiements/', views.export_paiements, name='export_paiements'),
    path('export/rappels/', views.export_rappels, name='export_rappels'),
]