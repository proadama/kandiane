# apps/accounts/urls.py
from django.urls import path, re_path, reverse_lazy
from django.contrib.auth import views as auth_views
from . import views
from .forms import CustomAuthenticationForm, CustomPasswordResetForm, CustomSetPasswordForm

app_name = 'accounts'

urlpatterns = [
    # Authentification
    path('login/', views.CustomLoginView.as_view(
        form_class=CustomAuthenticationForm,
        template_name='accounts/login.html'
    ), name='login'),
    
    # Utiliser notre vue de déconnexion personnalisée à la place de LogoutView
    path('logout/', views.custom_logout, name='logout'),
    
    # Inscription et activation
    path('register/', views.RegisterView.as_view(), name='register'),
    path('activate/<str:activation_key>/', views.activate_account, name='activate'),
    path('resend-activation/', views.resend_activation, name='resend_activation'),
    
    # Profil utilisateur
    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('profile/change-password/', views.change_password, name='change_password'),
    
    # Réinitialisation du mot de passe
    path('password/reset/', auth_views.PasswordResetView.as_view(
        template_name='accounts/password_reset.html',
        form_class=CustomPasswordResetForm,
        email_template_name='accounts/email/password_reset_email.html',
        subject_template_name='accounts/email/password_reset_subject.txt',
        success_url='/accounts/password/reset/done/'
    ), name='password_reset'),
    
    path('password/reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='accounts/password_reset_done.html'
    ), name='password_reset_done'),
    
    path('password/reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='accounts/password_reset_confirm.html',
        form_class=CustomSetPasswordForm,
        success_url='/accounts/password/reset/complete/'
    ), name='password_reset_confirm'),
    
    path('password/reset/complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='accounts/password_reset_complete.html'
    ), name='password_reset_complete'),
    
    # Administration des rôles (pour les super-utilisateurs)
    path('roles/', views.RoleListView.as_view(), name='role_list'),
    path('roles/add/', views.RoleCreateView.as_view(), name='role_create'),
    path('roles/<int:pk>/edit/', views.RoleUpdateView.as_view(), name='role_update'),
    path('roles/<int:pk>/delete/', views.RoleDeleteView.as_view(), name='role_delete'),
    
    # API interne pour le middleware/JS
    path('api/check-session/', views.check_session, name='check_session'),

    # Page protégée
    path('protected/', views.ProtectedPageView.as_view(), name='protected_page'),

    # Termes CGU
    path('terms/', views.TermsView.as_view(), name='terms'),
]