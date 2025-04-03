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
    # Redirection de la racine vers l'application core
    path('favicon.ico', RedirectView.as_view(url='/static/img/favicon.ico')),
]

# Ajouter les URLs pour les media et les fichiers statiques en développement
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    
    # Ajouter la debug toolbar seulement en mode développement
    try:
        import debug_toolbar
        urlpatterns.append(path('__debug__/', include(debug_toolbar.urls)))
    except ImportError:
        pass
