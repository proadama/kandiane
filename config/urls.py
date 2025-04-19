"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
# config/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

app_name = 'core'

# Gestionnaires d'erreurs personnalisés
handler404 = 'apps.core.views.error_404'
handler500 = 'apps.core.views.error_500'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.core.urls')),
    path('accounts/', include('apps.accounts.urls')),
    path('membres/', include('apps.membres.urls')),
    path('cotisations/', include('apps.cotisations.urls')),
    path('favicon.ico', RedirectView.as_view(url='/static/img/favicon.ico')),
]

# Ajouter les URLs pour les media et les fichiers statiques en développement
if settings.DEBUG:
    # Servir les fichiers media et static en développement
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    
    # Inclure la barre de débogage en développement
    if 'debug_toolbar' in settings.INSTALLED_APPS:
        try:
            import debug_toolbar
            urlpatterns = [
                path('__debug__/', include(debug_toolbar.urls)),
            ] + urlpatterns  # Ajouter au début pour éviter les conflits d'URL
        except ImportError:
            pass
