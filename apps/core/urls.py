# apps/core/urls.py
from django.urls import path
from . import views

app_name = 'core'
app_name = 'core_test'  # Au lieu de 'core'

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    path('maintenance/', views.maintenance_view, name='maintenance'),
    path('', views.HomeView.as_view(), name='home'),  # Assurez-vous que cette URL est définie
    path('test-filters/', views.test_filters, name='test_filters'),
    # Pour le test uniquement
    #path('test-500/', lambda request: 1/0, name='test-500'),  # Division par zéro
]