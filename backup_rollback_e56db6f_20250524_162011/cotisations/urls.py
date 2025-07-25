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
    path('rappels/<int:rappel_id>/envoyer/', views.envoyer_rappel, name='envoyer_rappel'),
    path('rappels/<int:pk>/modifier/', views.rappel_update, name='rappel_modifier'),
    path('rappels/<int:pk>/envoyer/', views.RappelEnvoyerView.as_view(), name='rappel_envoyer'),
    path('rappels/<int:rappel_id>/contenu/', views.rappel_contenu_ajax, name='rappel_contenu_ajax'),
    path('rappels/<int:rappel_id>/envoyer/', views.rappel_envoi_ajax, name='rappel_envoi_ajax'),
    path('rappels/<int:rappel_id>/supprimer-ajax/', views.rappel_supprimer_ajax, name='rappel_supprimer_ajax'),
    path('rappels/<int:pk>/supprimer/', views.RappelDeleteView.as_view(), name='rappel_supprimer'),
    
    # Fonctionnalités avancées
    path('corbeille/', views.corbeille, name='corbeille'),
    path('liste/', views.CotisationListView.as_view(), name='liste'),
    path('corbeille/', views.CotisationCorbeilleView.as_view(), name='corbeille'),
    path('restaurer/<int:pk>/', views.RestaurerCotisationView.as_view(), name='restaurer'),
    path('supprimer-definitivement/<int:pk>/', views.SupprimerDefinitivementCotisationView.as_view(), name='supprimer_definitivement'),
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
    path('api/types-membre-par-membre/', views.api_types_membre_par_membre, name='api_types_membre_par_membre'),
    path('api/rappel-templates/', views.api_rappel_templates, name='api_rappel_templates'),
    path('api/rappel-templates/<int:template_id>/', views.api_rappel_template_detail, name='api_rappel_template_detail'),
    path('api/rappel-templates/previsualiser/', views.api_rappel_template_previsualiser, name='api_rappel_template_previsualiser'),

    # APIs de VALIDATION INTELLIGENTE
    path('api/contraintes/<str:type_rappel>/', views.api_contraintes_type_rappel, name='api_contraintes_type_rappel'),
    path('api/validation/contenu/', views.api_valider_contenu_rappel, name='api_valider_contenu_rappel'),
    path('api/previsualisation/intelligente/', views.api_previsualiser_rappel_intelligent, name='api_previsualiser_rappel_intelligent'),
    path('api/suggestions/', views.api_suggestions_amelioration, name='api_suggestions_amelioration'),
    path('api/optimisation/automatique/', views.api_optimiser_contenu_automatique, name='api_optimiser_contenu_automatique'),
    path('api/contraintes/', views.api_contraintes_type_rappel, name='api_contraintes_get'),

    # Si vous voulez les vues d'administration des templates :
    path('templates-rappel/', views.RappelTemplateListView.as_view(), name='template_rappel_liste'),
    path('templates-rappel/nouveau/', views.RappelTemplateCreateView.as_view(), name='template_rappel_create'),
    path('templates-rappel/<int:pk>/modifier/', views.RappelTemplateUpdateView.as_view(), name='template_rappel_update'),

    # Cotisations
    path('<int:cotisation_id>/paiement/ajax/', views.paiement_create_ajax, name='paiement_create_ajax'),
    path('<int:cotisation_id>/rappel/ajax/', views.rappel_create_ajax, name='rappel_create_ajax'),

    # Fonctionnalités d'export
    path('export/cotisations/pdf/', views.export_cotisations_pdf, name='export_cotisations_pdf'),
    path('export/paiements/', views.export_paiements, name='export_paiements'),
    path('export/rappels/', views.export_rappels, name='export_rappels'),
]