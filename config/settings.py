from pathlib import Path

import os


# ─────────────────────────────
# BASE
# ─────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent

# ⚠️ DESARROLLO (cambia a False en producción)

DEBUG = os.environ.get('DJANGO_DEBUG', 'True').lower() in ('true', '1', 'yes')

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-a2n5v8xm9p0q-z-c3k8l-m-9n-0p-1q-2r-3s-4t-5u')


ALLOWED_HOSTS = ["127.0.0.1", "localhost", "testserver", ".vercel.app", "*"]


# ─────────────────────────────
# APLICACIONES
# ─────────────────────────────
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'rest_framework',
    'rest_framework_simplejwt',

    # tus apps
    'authentication',
    'dashboard',
    'creditos',
    'ahorros',
    'seguros',
    'servicios',
    'transferencias',
    'core_bancario',
]


# ─────────────────────────────
# MIDDLEWARE
# ─────────────────────────────
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'authentication.middleware.JWTCookieMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


# ─────────────────────────────
# URL PRINCIPAL
# ─────────────────────────────
ROOT_URLCONF = 'config.urls'


# ─────────────────────────────
# TEMPLATES
# ─────────────────────────────
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]


# ─────────────────────────────
# BASE DE DATOS
# ─────────────────────────────
# OPCIÓN 1: PostgreSQL (Supabase)

DB_NAME = os.environ.get('DB_NAME', 'postgres')
DB_USER = os.environ.get('DB_USER', 'postgres.pbggwtykouhjuoubzxzn')
DB_PASSWORD = os.environ.get('DB_PASSWORD', '60751132fghr')
DB_HOST = os.environ.get('DB_HOST', 'aws-1-us-west-1.pooler.supabase.com')
DB_PORT = os.environ.get('DB_PORT', '6543')

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': DB_NAME,
        'USER': DB_USER,
        'PASSWORD': DB_PASSWORD,
        'HOST': DB_HOST,
        'PORT': DB_PORT,
        'OPTIONS': {
            'sslmode': 'require',
        },
    }
}



AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# ─────────────────────────────
# INTERNACIONALIZACIÓN
# ─────────────────────────────
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


# ─────────────────────────────
# STATIC FILES
# ─────────────────────────────
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'


# ─────────────────────────────
# MEDIA FILES
# ─────────────────────────────
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'


# ─────────────────────────────
# DEFAULT PRIMARY KEY
# ─────────────────────────────
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# ─────────────────────────────
# LOGIN / LOGOUT
# ─────────────────────────────
# Homebanking (clientes)
LOGIN_URL = '/auth/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/auth/'

# ─────────────────────────────
# REST FRAMEWORK & JWT
# ─────────────────────────────
from datetime import timedelta

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    )
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': False,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),

}

# ─────────────────────────────
# SEGURIDAD (Solo en Producción)
# ─────────────────────────────
if not DEBUG:
    # Redirigir todo el tráfico HTTP a HTTPS
    SECURE_SSL_REDIRECT = True
    
    # Cookies de sesión y CSRF marcadas como Secure (solo HTTPS)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    
    # Habilitar HSTS (HTTP Strict Transport Security)
    SECURE_HSTS_SECONDS = 31536000  # 1 año
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    
    # Prevenir ataques de detección automática de tipos MIME (X-Content-Type-Options)
    SECURE_CONTENT_TYPE_NOSNIFF = True
    
    # Cabecera X-Frame-Options para proteger contra clickjacking
    X_FRAME_OPTIONS = 'DENY'
    
    # Cabecera Referrer-Policy
    SECURE_REFERRER_POLICY = 'same-origin'
