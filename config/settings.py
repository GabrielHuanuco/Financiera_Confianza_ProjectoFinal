from pathlib import Path

# ─────────────────────────────
# BASE
# ─────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent

# ⚠️ DESARROLLO (cambia a False en producción)
DEBUG = True

SECRET_KEY = 'django-insecure-a2n5v8xm9p0q-z-c3k8l-m-9n-0p-1q-2r-3s-4t-5u'

ALLOWED_HOSTS = ["127.0.0.1", "localhost", "testserver"]


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
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
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
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'postgres',
        'USER': 'postgres.pbggwtykouhjuoubzxzn',
        'PASSWORD': '60751132fghr',
        'HOST': 'aws-1-us-west-1.pooler.supabase.com',
        'PORT': '6543',
        'OPTIONS': {
            'sslmode': 'require',
        },
    }
}


# ─────────────────────────────
# PASSWORD VALIDATION
# ─────────────────────────────
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
LOGIN_URL = '/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/'