# config/settings/base.py
import os
from pathlib import Path
import environ

# Initialiser environ
env = environ.Env()

# Lire le fichier .env
environ.Env.read_env()

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Applications
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

]

THIRD_PARTY_APPS = [
    'django_extensions',
    
]

LOCAL_APPS = [
    'apps.core',
    'apps.accounts',
    'apps.membres',
    'apps.cotisations',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # Middlewares personnalisés
    'apps.accounts.middleware.LastUserActivityMiddleware',
    'apps.accounts.middleware.SessionExpiryMiddleware',
    'apps.accounts.middleware.RolePermissionMiddleware',
    'apps.core.middleware.MaintenanceModeMiddleware',
    'apps.core.middleware.NoCacheMiddleware',
]

ROOT_URLCONF = 'config.urls'

DEBUG = False
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'apps.core.context_processors.trash_counters',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Database
DATABASES = {
    'default': env.db('DATABASE_URL', default='sqlite:///db.sqlite3'),
}

# Configuration Django de base pour la sécurité des mots de passe
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
    {
        'NAME': 'apps.accounts.validators.StrongPasswordValidator',
        'OPTIONS': {
            'min_length': 8,
        }
    },
]

# Sécurité générale du site
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'
SECURE_CONTENT_TYPE_NOSNIFF = True

# Si vous êtes en production, activez ces paramètres (commentés pour développement)
# SECURE_SSL_REDIRECT = True  # Redirection vers HTTPS
# SESSION_COOKIE_SECURE = True  # Cookies de session uniquement via HTTPS
# CSRF_COOKIE_SECURE = True  # Cookies CSRF uniquement via HTTPS
# SECURE_HSTS_SECONDS = 31536000  # Un an
# SECURE_HSTS_INCLUDE_SUBDOMAINS = True
# SECURE_HSTS_PRELOAD = True

# Paramètres des sessions
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'  # Peut être 'Strict' en production
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_AGE = 7200  # 2 heures en secondes

# Taux de limitation pour les connexions
# Nécessite django-ratelimit (à ajouter aux requirements.txt)
RATELIMIT_ENABLE = True
RATELIMIT_LOGIN_ATTEMPTS = 5  # Nombre de tentatives autorisées
RATELIMIT_LOGIN_DURATION = 300  # Période de blocage en secondes (5 minutes)

# Email de vérification
ACCOUNT_EMAIL_VERIFICATION_REQUIRED = False
ACCOUNT_EMAIL_VERIFICATION_EXPIRY = 86400  # 24 heures en secondes

# Internationalization
LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Europe/Paris'
USE_I18N = True
USE_L10N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Email configuration
EMAIL_BACKEND = env('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='noreply@example.com')
EMAIL_HOST = env('EMAIL_HOST', default='')
EMAIL_PORT = env.int('EMAIL_PORT', default=587)
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=True)

# Site URL
SITE_URL = env('SITE_URL', default='http://localhost:8000')

# Modèle utilisateur personnalisé
AUTH_USER_MODEL = 'accounts.CustomUser'

# URLs d'authentification
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/accounts/login/'

# 8. Problème avec les URL login et l'authentification
LOGIN_URL = 'accounts:login'  # À ajuster selon votre application
LOGIN_REDIRECT_URL = 'core:home'

# Durée d'inactivité avant déconnexion (en secondes)
SESSION_IDLE_TIMEOUT = 1800  # 30 minutes

# Nom du site pour les emails
SITE_NAME = env('SITE_NAME', default='Nom de l\'association')

# Paramètres pour les photos des membres
THUMBNAIL_ALIASES = {
    '': {
        'small': {'size': (50, 50), 'crop': True},
        'medium': {'size': (100, 100), 'crop': True},
        'large': {'size': (250, 250), 'crop': True},
    },
}

# Paramètre pour le mode maintenance (False par défaut)
MAINTENANCE_MODE = False

# Pour les tests, définir une session très courte (30 secondes)
SESSION_COOKIE_AGE = 600  # en secondes

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'ERROR',
        },
    },
}