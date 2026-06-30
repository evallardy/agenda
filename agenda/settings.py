import os
from pathlib import Path

from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


DJANGO_ENV = os.getenv('DJANGO_ENV', 'development').strip().lower() or 'development'
ENV_FILE = os.getenv('DJANGO_ENV_FILE', '').strip()

if ENV_FILE:
    load_dotenv(BASE_DIR / ENV_FILE)
elif DJANGO_ENV == 'production':
    load_dotenv(BASE_DIR / '.env.production')
else:
    load_dotenv(BASE_DIR / '.env.development')

load_dotenv(BASE_DIR / '.env')


def env_bool(name, default=False):
    return env_str(name, str(default)).lower() == 'true'


def env_list(name, default=''):
    return [item.strip() for item in env_str(name, default).split(',') if item.strip()]


def env_str(name, default=''):
    value = os.getenv(name, default)
    if value is None:
        return ''
    value = str(value).strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        value = value[1:-1]
    return value


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/6.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-w9#gl_rm=uwi50&of&32b%#zs+8d*jq)c9=hjitau5at&5uvfl')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env_bool('DJANGO_DEBUG', True)
IS_PRODUCTION = DJANGO_ENV == 'production'

ALLOWED_HOSTS = env_list('DJANGO_ALLOWED_HOSTS', '127.0.0.1,localhost')
CSRF_TRUSTED_ORIGINS = env_list('DJANGO_CSRF_TRUSTED_ORIGINS', '')


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'core.apps.CoreConfig',
    'users.apps.UsersConfig',
    'citas.apps.CitasConfig',
    'clinico.apps.ClinicoConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

if env_bool('DJANGO_USE_WHITENOISE', IS_PRODUCTION):
    MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')

ROOT_URLCONF = 'agenda.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'agenda.wsgi.application'


# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.getenv('DB_NAME', 'agenda_consultorio'),
        'USER': os.getenv('DB_USER', 'root'),
        'PASSWORD': os.getenv('DB_PASSWORD', 'root'),
        'HOST': os.getenv('DB_HOST', '127.0.0.1'),
        'PORT': os.getenv('DB_PORT', '3306'),
        'OPTIONS': {
            'charset': 'utf8mb4',
        },
    }
}


# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators

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


# Internationalization
# https://docs.djangoproject.com/en/6.0/topics/i18n/

LANGUAGE_CODE = 'es-mx'

TIME_ZONE = 'America/Mexico_City'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.0/howto/static-files/

AUTH_USER_MODEL = 'users.User'
AUTHENTICATION_BACKENDS = ['users.backends.EmailOrUsernameBackend']

LOGIN_URL = 'users:login'
LOGIN_REDIRECT_URL = 'core:dashboard'
LOGOUT_REDIRECT_URL = 'core:home'

EMAIL_BACKEND = env_str('EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = env_str('EMAIL_HOST', 'sandbox.smtp.mailtrap.io')
EMAIL_PORT = int(env_str('EMAIL_PORT', '2525'))
EMAIL_HOST_USER = env_str('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = env_str('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = env_bool('EMAIL_USE_TLS', True)
#EMAIL_USE_SSL = False
#EMAIL_TIMEOUT = 20
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER or 'no-reply@consultorio.local'
#SERVER_EMAIL = DEFAULT_FROM_EMAIL

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

if env_bool('DJANGO_USE_WHITENOISE', IS_PRODUCTION):
    STORAGES = {
        'default': {
            'BACKEND': 'django.core.files.storage.FileSystemStorage',
        },
        'staticfiles': {
            'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
        },
    }

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

SECURE_SSL_REDIRECT = env_bool('DJANGO_SECURE_SSL_REDIRECT', not DEBUG)
SESSION_COOKIE_SECURE = env_bool('DJANGO_SESSION_COOKIE_SECURE', not DEBUG)
CSRF_COOKIE_SECURE = env_bool('DJANGO_CSRF_COOKIE_SECURE', not DEBUG)
SECURE_HSTS_SECONDS = int(os.getenv('DJANGO_SECURE_HSTS_SECONDS', '0' if DEBUG else '31536000'))
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool('DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS', not DEBUG)
SECURE_HSTS_PRELOAD = env_bool('DJANGO_SECURE_HSTS_PRELOAD', not DEBUG)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https') if env_bool('DJANGO_BEHIND_PROXY', False) else None
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_REFERRER_POLICY = 'same-origin'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
