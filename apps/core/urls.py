# apps/core/urls.py
from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    path('maintenance/', views.maintenance_view, name='maintenance'),
    path('', views.HomeView.as_view(), name='home'),  # Assurez-vous que cette URL est définie
    # Pour le test uniquement
    #path('test-500/', lambda request: 1/0, name='test-500'),  # Division par zéro
]